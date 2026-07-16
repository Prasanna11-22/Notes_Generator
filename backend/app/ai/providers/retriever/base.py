"""
Base interface for Retriever Providers.
"""

from abc import ABC, abstractmethod


class RetrieverProvider(ABC):
    """
    Abstract Base Class for vector database context retrievers.
    """

    @abstractmethod
    def retrieve(self, query: str, limit: int = 5) -> list[tuple[str, float]]:
        """
        Search the vector index for chunks matching the query string.

        :param query: User search query text.
        :param limit: Maximum number of candidate vectors to fetch.
        :returns: List of tuples containing (vector_store_id, distance/score).
        """
        pass
