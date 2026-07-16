"""
Base interface for Vector Store Providers.
"""

from abc import ABC, abstractmethod


class VectorStoreProvider(ABC):
    """
    Abstract Base Class for vector storage indices.
    """

    @abstractmethod
    def create_index(self) -> None:
        """
        Initialize a new empty index and delete any existing index data on disk/memory.
        """
        pass

    @abstractmethod
    def insert(self, vector_id: str, vector: list[float]) -> None:
        """
        Insert a new vector linked to vector_id.

        :param vector_id: Unique identifier (e.g. UUID string).
        :param vector: List of floats representing the vector.
        """
        pass

    @abstractmethod
    def update(self, vector_id: str, vector: list[float]) -> None:
        """
        Update the vector associated with the given vector_id.

        :param vector_id: Unique identifier.
        :param vector: Updated list of floats representing the vector.
        """
        pass

    @abstractmethod
    def delete(self, vector_id: str) -> None:
        """
        Delete the vector linked to vector_id.

        :param vector_id: Unique identifier to remove.
        """
        pass

    @abstractmethod
    def exists(self, vector_id: str) -> bool:
        """
        Check if a vector with the given vector_id exists.

        :param vector_id: Unique identifier.
        :returns: True if exists, False otherwise.
        """
        pass

    @abstractmethod
    def search_by_chunk(self, vector: list[float], limit: int = 5) -> list[tuple[str, float]]:
        """
        Perform a vector similarity search (nearest neighbors).

        :param vector: Query vector.
        :param limit: Maximum number of search results to return.
        :returns: List of tuples (vector_id, similarity_score).
        """
        pass

    @abstractmethod
    def rebuild(self, vectors: dict[str, list[float]]) -> None:
        """
        Clear the index and rebuild it entirely using the provided ID-to-vector mapping.

        :param vectors: Dictionary of UUID/ID keys to vector values.
        """
        pass

    @abstractmethod
    def health_check(self) -> bool:
        """
        Perform health check on the vector store.
        """
        pass
