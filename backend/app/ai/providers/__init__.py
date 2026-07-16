"""
Providers registry/factory.
"""

from app.ai.providers.embedding.base import EmbeddingProvider
from app.ai.providers.embedding.bge import BGEEmbeddingProvider
from app.ai.providers.vector_store.base import VectorStoreProvider
from app.ai.providers.vector_store.faiss import FAISSProvider
from app.ai.providers.retriever.base import RetrieverProvider
from app.ai.providers.retriever.faiss_retriever import FAISSRetrieverProvider
from app.ai.providers.llm.base import LLMProvider
from app.ai.providers.llm.ollama import OllamaProvider
from app.core.config import settings

_embedding_provider: EmbeddingProvider | None = None
_vector_store_provider: VectorStoreProvider | None = None
_retriever_provider: RetrieverProvider | None = None
_llm_provider: LLMProvider | None = None


def get_embedding_provider() -> EmbeddingProvider:
    """
    Get the cached singleton instance of the Embedding Provider.
    """
    global _embedding_provider
    if _embedding_provider is None:
        if settings.embedding_provider == "bge":
            _embedding_provider = BGEEmbeddingProvider(
                model_name=settings.embedding_model,
                dimension=settings.embedding_dimension,
            )
        else:
            raise ValueError(f"Unsupported embedding provider: {settings.embedding_provider}")
    return _embedding_provider


def get_vector_store_provider() -> VectorStoreProvider:
    """
    Get the cached singleton instance of the Vector Store Provider.
    """
    global _vector_store_provider
    if _vector_store_provider is None:
        if settings.vector_store == "faiss":
            _vector_store_provider = FAISSProvider(
                index_path=settings.faiss_index_path,
                dimension=settings.embedding_dimension,
            )
        else:
            raise ValueError(f"Unsupported vector store provider: {settings.vector_store}")
    return _vector_store_provider


def get_retriever_provider() -> RetrieverProvider:
    """
    Get the cached singleton instance of the Retriever Provider.
    """
    global _retriever_provider
    if _retriever_provider is None:
        if settings.retriever_provider == "faiss":
            _retriever_provider = FAISSRetrieverProvider(
                embedding_provider=get_embedding_provider(),
                vector_store_provider=get_vector_store_provider(),
            )
        else:
            raise ValueError(f"Unsupported retriever provider: {settings.retriever_provider}")
    return _retriever_provider


def get_llm_provider() -> LLMProvider:
    """
    Get the cached singleton instance of the LLM Provider.
    """
    global _llm_provider
    if _llm_provider is None:
        if settings.llm_provider == "ollama":
            _llm_provider = OllamaProvider(
                host=settings.ollama_host,
                default_model=settings.llm_model,
                timeout=settings.llm_timeout_seconds,
            )
        else:
            raise ValueError(f"Unsupported LLM provider: {settings.llm_provider}")
    return _llm_provider

