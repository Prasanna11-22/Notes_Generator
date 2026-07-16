"""
Embedding synchronization service to manage integrity between PostgreSQL and Vector Store.
"""

import asyncio
from datetime import datetime, timezone
import time
from uuid import uuid4
from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.ai.providers import get_embedding_provider, get_vector_store_provider
from app.core.config import settings
from app.models.chunk import Chunk
from app.models.embedding import ChunkEmbedding
from app.repositories.chunk import ChunkRepository
from app.repositories.embedding import EmbeddingRepository
from app.services.embedding import validate_chunk_text, validate_vector


class EmbeddingSynchronizationService:
    """
    Service responsible for keeping PostgreSQL chunk metadata and the vector store synchronized.
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._embedding_repo = EmbeddingRepository(session)
        self._chunk_repo = ChunkRepository(session)
        self._embedding_provider = get_embedding_provider()
        self._vector_store_provider = get_vector_store_provider()

    async def get_synchronization_report(self) -> dict:
        """
        Scan database chunk embeddings and FAISS index to generate a synchronization report.
        """
        logger.info("Generating embedding synchronization report...")

        # 1. Fetch all unique chunks from database
        chunks_result = await self._session.execute(select(Chunk))
        db_chunks = chunks_result.scalars().all()
        total_chunks = len(db_chunks)

        # 2. Fetch all metadata records from DB
        all_embeddings = await self._embedding_repo.get_all(skip=0, limit=1000000)
        db_embeddings_map = {emb.vector_store_id: emb for emb in all_embeddings}
        db_chunk_to_emb = {emb.chunk_id: emb for emb in all_embeddings}

        # 3. Fetch all vector IDs from Vector Store (FAISS)
        # We cast get_all_ids to FAISSProvider's method (duck typing)
        vector_store_ids = getattr(self._vector_store_provider, "get_all_ids", lambda: [])()
        vs_ids_set = set(vector_store_ids)

        missing_vectors = []
        inconsistent_embeddings = []

        # Find missing vectors and inconsistent metadata
        for emb in all_embeddings:
            if emb.vector_store_id not in vs_ids_set:
                missing_vectors.append(str(emb.vector_store_id))
            elif (
                emb.dimension != settings.embedding_dimension
                or emb.model_name != settings.embedding_model
            ):
                inconsistent_embeddings.append(str(emb.vector_store_id))

        # Find missing metadata (vectors in vector store but no metadata in DB)
        missing_metadata = []
        for vs_id in vs_ids_set:
            if vs_id not in db_embeddings_map:
                missing_metadata.append(vs_id)

        is_synced = (
            len(missing_vectors) == 0
            and len(missing_metadata) == 0
            and len(inconsistent_embeddings) == 0
        )

        report = {
            "total_chunks_in_db": total_chunks,
            "total_embeddings_in_db": len(all_embeddings),
            "total_vectors_in_faiss": len(vs_ids_set),
            "missing_vectors_count": len(missing_vectors),
            "missing_metadata_count": len(missing_metadata),
            "inconsistent_embeddings_count": len(inconsistent_embeddings),
            "is_synchronized": is_synced,
            "missing_vectors": missing_vectors,
            "missing_metadata": missing_metadata,
            "inconsistent_embeddings": inconsistent_embeddings,
        }

        logger.info(
            "Sync report: total_chunks={}, total_embeddings={}, total_vectors={}, is_synchronized={}",
            total_chunks,
            len(all_embeddings),
            len(vs_ids_set),
            is_synced,
        )
        return report

    async def reconcile(self) -> dict:
        """
        Repair inconsistencies between PostgreSQL and the vector store:
        1. Regenerate missing vectors (metadata in DB but no vector in FAISS).
        2. Delete orphaned vectors (vector in FAISS but no metadata in DB).
        3. Delete and regenerate inconsistent vectors.
        """
        logger.info("Starting embedding reconciliation...")
        report = await self.get_synchronization_report()

        repaired_vectors_count = 0
        deleted_vectors_count = 0
        repaired_metadata_count = 0

        # 1. Clean up orphaned vectors in vector store (missing metadata)
        for vs_id in report["missing_metadata"]:
            await asyncio.to_thread(self._vector_store_provider.delete, vs_id)
            deleted_vectors_count += 1
            logger.info("Deleted orphaned vector ID: {} from vector store", vs_id)

        # 2. Delete and clean up inconsistent embeddings (so they get regenerated)
        for vs_id in report["inconsistent_embeddings"]:
            # Delete vector from store
            await asyncio.to_thread(self._vector_store_provider.delete, vs_id)
            deleted_vectors_count += 1

            # Delete metadata from DB
            emb = await self._embedding_repo.get_by_vector_store_id(vs_id)
            if emb:
                await self._embedding_repo.delete(emb)
                repaired_metadata_count += 1
            logger.info("Removed inconsistent embedding ID: {}", vs_id)

        await self._session.flush()

        # Gather all ChunkEmbeddings that need vectors regenerated
        # This includes missing vectors plus the inconsistent ones we just deleted
        re_report = await self.get_synchronization_report()

        # 3. Regenerate missing vectors
        dim = self._embedding_provider.embedding_dimension()
        for vs_id in re_report["missing_vectors"]:
            emb = await self._embedding_repo.get_by_vector_store_id(vs_id)
            if emb:
                chunk = await self._chunk_repo.get_by_id(emb.chunk_id)
                if chunk:
                    try:
                        validate_chunk_text(chunk.cleaned_text, settings.max_chunk_char_length)
                        start_time = time.perf_counter()
                        vector = await asyncio.to_thread(self._embedding_provider.generate_embedding, chunk.cleaned_text)
                        duration = time.perf_counter() - start_time
                        validate_vector(vector, dim)

                        # Re-insert into Vector Store
                        await asyncio.to_thread(self._vector_store_provider.insert, emb.vector_store_id, vector)
                        emb.status = "completed"
                        emb.processing_time = duration
                        emb.model_name = self._embedding_provider.model_name()
                        emb.dimension = dim
                        emb.updated_at = datetime.now(timezone.utc)
                        repaired_vectors_count += 1
                        logger.info("Regenerated and inserted vector for chunk: {}", chunk.id)
                    except Exception as e:
                        logger.error("Failed to regenerate vector for chunk {}: {}", chunk.id, str(e))
                        emb.status = "failed"

        await self._session.flush()

        logger.info(
            "Reconciliation finished. Repaired vectors: {}, Deleted vectors: {}, Repaired metadata: {}",
            repaired_vectors_count,
            deleted_vectors_count,
            repaired_metadata_count,
        )

        return {
            "status": "reconciled",
            "repaired_vectors_count": repaired_vectors_count,
            "deleted_vectors_count": deleted_vectors_count,
            "repaired_metadata_count": repaired_metadata_count,
        }

    async def rebuild_index(self) -> None:
        """
        Rebuild the entire FAISS index from scratch:
        1. Recreate the empty FAISS index on disk/memory.
        2. Delete all ChunkEmbedding metadata.
        3. Regenerate embeddings for all chunks in the DB in batches.
        """
        logger.warning("Initiating full FAISS vector store and metadata rebuild...")

        # 1. Clear vector store
        await asyncio.to_thread(self._vector_store_provider.create_index)

        # 2. Delete all existing chunk embeddings in database
        all_embeddings = await self._embedding_repo.get_all(skip=0, limit=1000000)
        for emb in all_embeddings:
            await self._embedding_repo.delete(emb)
        await self._session.flush()

        # 3. Retrieve all unique chunks in database
        chunks = await self._chunk_repo.get_all_unique_chunks()
        if not chunks:
            logger.info("No chunks in database. Index cleared and rebuild finished.")
            return

        logger.info("Regenerating embeddings for {} unique chunks in batches...", len(chunks))

        # 4. Generate batch embeddings
        batch_size = settings.batch_size
        dim = self._embedding_provider.embedding_dimension()

        for i in range(0, len(chunks), batch_size):
            batch = chunks[i : i + batch_size]
            texts = [c.cleaned_text for c in batch]

            start_time = time.perf_counter()
            vectors = await asyncio.to_thread(self._embedding_provider.generate_batch_embeddings, texts)
            generation_duration = time.perf_counter() - start_time
            per_chunk_time = generation_duration / len(batch)

            for idx, chunk in enumerate(batch):
                vector = vectors[idx]
                validate_vector(vector, dim)

                emb_id = uuid4()
                emb = ChunkEmbedding(
                    id=emb_id,
                    chunk_id=chunk.id,
                    model_name=self._embedding_provider.model_name(),
                    model_version="1.5",
                    dimension=dim,
                    vector_store_id=str(emb_id),
                    status="completed",
                    processing_time=per_chunk_time,
                )

                # Store in vector database
                await asyncio.to_thread(self._vector_store_provider.insert, str(emb_id), vector)
                # Store metadata
                await self._embedding_repo.create(emb)

        await self._session.flush()
        logger.info("Rebuild complete. Loaded {} embeddings.", len(chunks))
