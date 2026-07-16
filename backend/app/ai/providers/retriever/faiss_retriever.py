"""
FAISS Retriever Provider implementation.
"""

from app.ai.providers.embedding.base import EmbeddingProvider
from app.ai.providers.vector_store.base import VectorStoreProvider
from app.ai.providers.retriever.base import RetrieverProvider


class FAISSRetrieverProvider(RetrieverProvider):
    """
    Retriever provider that performs query encoding via the EmbeddingProvider
    and similarity search in FAISS via the VectorStoreProvider.
    """

    def __init__(
        self,
        embedding_provider: EmbeddingProvider,
        vector_store_provider: VectorStoreProvider,
    ) -> None:
        self.embedding_provider = embedding_provider
        self.vector_store_provider = vector_store_provider

    def retrieve(self, query: str, limit: int = 5) -> list[tuple[str, float]]:
        """
        Encode query to embedding vector and query the local FAISS index.
        """
        # Generate the query vector
        query_vector = self.embedding_provider.generate_embedding(query)

        # Query the FAISS store index
        return self.vector_store_provider.search_by_chunk(query_vector, limit)
