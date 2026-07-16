"""
FAISS Vector Store Provider implementation.
"""

import os
import json
import threading
from loguru import logger
import faiss
import numpy as np

from app.ai.providers.vector_store.base import VectorStoreProvider


class FAISSProvider(VectorStoreProvider):
    """
    FAISS-cpu based vector store provider with local disk persistence.
    """

    def __init__(self, index_path: str, dimension: int) -> None:
        self.index_path = index_path
        self.mapping_path = index_path + ".json"
        self.dimension = dimension
        self.lock = threading.Lock()

        self.index = None
        self.uuid_to_id = {}
        self.id_to_uuid = {}
        self.next_id = 0

        self._load_or_initialize()

    def _load_or_initialize(self) -> None:
        """
        Load index and mappings from disk if they exist, else initialize a new one.
        """
        with self.lock:
            if os.path.exists(self.index_path) and os.path.exists(self.mapping_path):
                try:
                    logger.info("Loading existing FAISS index from: {}", self.index_path)
                    self.index = faiss.read_index(self.index_path)

                    logger.info("Loading ID mappings from: {}", self.mapping_path)
                    with open(self.mapping_path, "r") as f:
                        data = json.load(f)
                        self.uuid_to_id = data.get("uuid_to_id", {})
                        self.id_to_uuid = {int(k): v for k, v in data.get("id_to_uuid", {}).items()}
                        self.next_id = data.get("next_id", 0)

                    logger.info("FAISS index loaded. Total vectors: {}", self.index.ntotal)
                    return
                except Exception as e:
                    logger.error("Failed to load FAISS index from disk: {}. Initializing empty index.", str(e))

            # If load fails or files do not exist, initialize a new index
            logger.info("Initializing a new empty FAISS index.")
            sub_index = faiss.IndexFlatL2(self.dimension)
            self.index = faiss.IndexIDMap(sub_index)
            self.uuid_to_id = {}
            self.id_to_uuid = {}
            self.next_id = 0

    def create_index(self) -> None:
        """
        Initialize a new empty index and delete any existing index files.
        """
        with self.lock:
            logger.warning("Recreating/Resetting FAISS index at {}", self.index_path)
            sub_index = faiss.IndexFlatL2(self.dimension)
            self.index = faiss.IndexIDMap(sub_index)
            self.uuid_to_id = {}
            self.id_to_uuid = {}
            self.next_id = 0
            self._save_to_disk_unlocked()

    def insert(self, vector_id: str, vector: list[float]) -> None:
        """
        Insert a new vector linked to vector_id. Overwrites if exists.
        """
        if len(vector) != self.dimension:
            raise ValueError(
                f"Vector dimension {len(vector)} does not match expected dimension {self.dimension}"
            )

        with self.lock:
            if vector_id in self.uuid_to_id:
                # Update if already exists
                self._update_unlocked(vector_id, vector)
                return

            int_id = self.next_id
            self.next_id += 1

            vec_np = np.array([vector], dtype=np.float32)
            id_np = np.array([int_id], dtype=np.int64)

            self.index.add_with_ids(vec_np, id_np)

            self.uuid_to_id[vector_id] = int_id
            self.id_to_uuid[int_id] = vector_id

            self._save_to_disk_unlocked()
            logger.debug("Inserted vector id: {} mapped to FAISS id: {}", vector_id, int_id)

    def update(self, vector_id: str, vector: list[float]) -> None:
        """
        Update vector associated with given vector_id.
        """
        if len(vector) != self.dimension:
            raise ValueError(
                f"Vector dimension {len(vector)} does not match expected dimension {self.dimension}"
            )

        with self.lock:
            self._update_unlocked(vector_id, vector)

    def _update_unlocked(self, vector_id: str, vector: list[float]) -> None:
        """Helper update method assuming lock is already held."""
        if vector_id not in self.uuid_to_id:
            # Insert if it doesn't exist
            int_id = self.next_id
            self.next_id += 1
            self.uuid_to_id[vector_id] = int_id
            self.id_to_uuid[int_id] = vector_id
        else:
            int_id = self.uuid_to_id[vector_id]
            # Remove old ID from FAISS index before inserting new vector
            self.index.remove_ids(np.array([int_id], dtype=np.int64))

        vec_np = np.array([vector], dtype=np.float32)
        id_np = np.array([int_id], dtype=np.int64)
        self.index.add_with_ids(vec_np, id_np)

        self._save_to_disk_unlocked()
        logger.debug("Updated vector id: {} at FAISS id: {}", vector_id, int_id)

    def delete(self, vector_id: str) -> None:
        """
        Delete vector linked to vector_id.
        """
        with self.lock:
            if vector_id not in self.uuid_to_id:
                logger.debug("Attempted to delete non-existent vector id: {}", vector_id)
                return

            int_id = self.uuid_to_id[vector_id]
            self.index.remove_ids(np.array([int_id], dtype=np.int64))

            del self.uuid_to_id[vector_id]
            del self.id_to_uuid[int_id]

            self._save_to_disk_unlocked()
            logger.debug("Deleted vector id: {} / FAISS id: {}", vector_id, int_id)

    def exists(self, vector_id: str) -> bool:
        """
        Check if a vector with the given vector_id exists.
        """
        with self.lock:
            return vector_id in self.uuid_to_id

    def search_by_chunk(self, vector: list[float], limit: int = 5) -> list[tuple[str, float]]:
        """
        Perform nearest neighbors search.
        """
        with self.lock:
            if self.index is None or self.index.ntotal == 0:
                return []

            vec_np = np.array([vector], dtype=np.float32)
            distances, ids = self.index.search(vec_np, limit)

            results = []
            for dist, int_id in zip(distances[0], ids[0]):
                # FAISS returns -1 for empty slots
                if int_id == -1:
                    continue
                uuid_str = self.id_to_uuid.get(int(int_id))
                if uuid_str:
                    results.append((uuid_str, float(dist)))
            return results

    def rebuild(self, vectors: dict[str, list[float]]) -> None:
        """
        Clear and rebuild index from scratch.
        """
        with self.lock:
            logger.info("Rebuilding FAISS index with {} vectors", len(vectors))
            sub_index = faiss.IndexFlatL2(self.dimension)
            self.index = faiss.IndexIDMap(sub_index)
            self.uuid_to_id = {}
            self.id_to_uuid = {}
            self.next_id = 0

            if not vectors:
                self._save_to_disk_unlocked()
                return

            vec_list = []
            id_list = []

            for uuid_str, vector in vectors.items():
                if len(vector) != self.dimension:
                    raise ValueError(
                        f"Vector dimension {len(vector)} does not match {self.dimension}"
                    )
                int_id = self.next_id
                self.next_id += 1

                self.uuid_to_id[uuid_str] = int_id
                self.id_to_uuid[int_id] = uuid_str

                vec_list.append(vector)
                id_list.append(int_id)

            vec_np = np.array(vec_list, dtype=np.float32)
            id_np = np.array(id_list, dtype=np.int64)

            self.index.add_with_ids(vec_np, id_np)
            self._save_to_disk_unlocked()
            logger.info("FAISS index rebuild complete. Total vectors: {}", self.index.ntotal)

    def health_check(self) -> bool:
        """
        Health check to confirm FAISS index is initialized.
        """
        with self.lock:
            return self.index is not None

    def _save_to_disk_unlocked(self) -> None:
        """
        Save the FAISS index and mappings files to disk (assumes lock is held).
        """
        try:
            # Create folder if it doesn't exist
            parent_dir = os.path.dirname(self.index_path)
            if parent_dir:
                os.makedirs(parent_dir, exist_ok=True)

            faiss.write_index(self.index, self.index_path)

            with open(self.mapping_path, "w") as f:
                json.dump(
                    {
                        "uuid_to_id": self.uuid_to_id,
                        "id_to_uuid": {str(k): v for k, v in self.id_to_uuid.items()},
                        "next_id": self.next_id,
                    },
                    f,
                    indent=2,
                )
            logger.debug("FAISS index and mappings written to disk successfully.")
        except Exception as e:
            logger.error("Failed to save FAISS index to disk: {}", str(e))
            raise

    # Auxiliary method for synchronization reporting
    def get_all_ids(self) -> list[str]:
        """
        Return all vector UUID keys currently present in the index mapping.
        """
        with self.lock:
            return list(self.uuid_to_id.keys())
