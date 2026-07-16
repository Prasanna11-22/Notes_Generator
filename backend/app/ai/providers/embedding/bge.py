"""
BGE Embedding Provider implementation.
"""

import time
from loguru import logger
from sentence_transformers import SentenceTransformer

from app.ai.providers.embedding.base import EmbeddingProvider


class BGEEmbeddingProvider(EmbeddingProvider):
    """
    Embedding provider that utilizes the SentenceTransformers library
    with a BGE model (e.g. BAAI/bge-small-en-v1.5) running locally.
    """

    def __init__(self, model_name: str, dimension: int) -> None:
        self._model_name = model_name
        self._dimension = dimension
        self._model = None
        self._load_model()

    def _load_model(self) -> None:
        """Loads the sentence transformer model into memory."""
        try:
            logger.info("Loading SentenceTransformer model: {}", self._model_name)
            start_time = time.perf_counter()
            self._model = SentenceTransformer(self._model_name)
            duration = time.perf_counter() - start_time
            logger.info(
                "Model {} loaded successfully in {:.2f}s",
                self._model_name,
                duration,
            )
        except Exception as e:
            logger.error("Failed to load model {}: {}", self._model_name, str(e))
            raise

    def generate_embedding(self, text: str) -> list[float]:
        """
        Generate a single vector embedding.
        """
        if not text or not text.strip():
            raise ValueError("Cannot generate embedding for empty or whitespace-only text.")

        start_time = time.perf_counter()
        # Clean text validation inside service but double-guarded here.
        embeddings = self._model.encode([text], normalize_embeddings=True)
        duration = time.perf_counter() - start_time

        logger.debug(
            "Generated 1 embedding. Dimension: {}. Duration: {:.4f}s",
            self._dimension,
            duration,
        )
        return embeddings[0].tolist()

    def generate_batch_embeddings(self, texts: list[str]) -> list[list[float]]:
        """
        Generate embeddings for a batch of texts.
        """
        if not texts:
            return []

        # Validate that no text is empty/whitespace
        for idx, text in enumerate(texts):
            if not text or not text.strip():
                raise ValueError(f"Text at index {idx} is empty or whitespace-only.")

        start_time = time.perf_counter()
        logger.info(
            "Starting batch embedding generation. Batch size: {}",
            len(texts),
        )

        embeddings = self._model.encode(texts, normalize_embeddings=True)
        duration = time.perf_counter() - start_time

        logger.info(
            "Batch embedding generation completed. Count: {}. Duration: {:.4f}s",
            len(texts),
            duration,
        )

        return [vector.tolist() for vector in embeddings]

    def embedding_dimension(self) -> int:
        return self._dimension

    def model_name(self) -> str:
        return self._model_name

    def health_check(self) -> bool:
        """
        Runs a quick inference health check to confirm model is responsive.
        """
        if self._model is None:
            return False
        try:
            # Short test text
            test_vector = self.generate_embedding("health check")
            return len(test_vector) == self._dimension
        except Exception as e:
            logger.error("BGEEmbeddingProvider health check failed: {}", str(e))
            return False
