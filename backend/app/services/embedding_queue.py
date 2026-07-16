"""
Embedding Queue — Background Task Adapter.

Abstraction over background tasks to generate vector embeddings.
"""

from __future__ import annotations

import uuid
from abc import ABC, abstractmethod

from fastapi import BackgroundTasks
from loguru import logger

from app.database.session import AsyncSessionLocal
from app.services.embedding import EmbeddingService


class AbstractEmbeddingQueue(ABC):
    """
    Queue interface for embedding generation tasks.
    """

    @abstractmethod
    def enqueue_embedding(
        self, resource_id: uuid.UUID, background_tasks: BackgroundTasks, force: bool = False
    ) -> None:
        """
        Enqueue an embedding job for *resource_id*.
        """
        pass


class FastAPIEmbeddingQueue(AbstractEmbeddingQueue):
    """
    Runs embedding generation asynchronously inside a FastAPI BackgroundTask.
    """

    def enqueue_embedding(
        self, resource_id: uuid.UUID, background_tasks: BackgroundTasks, force: bool = False
    ) -> None:
        background_tasks.add_task(self._run, resource_id, force)
        logger.info(
            "FastAPIEmbeddingQueue: scheduled embedding generation for resource {}", resource_id
        )

    @staticmethod
    async def _run(resource_id: uuid.UUID, force: bool = False) -> None:
        """
        Execute embedding generation in a fresh database session context.
        """
        logger.info(
            "FastAPIEmbeddingQueue: starting background embedding generation for resource {}",
            resource_id,
        )
        try:
            async with AsyncSessionLocal() as session:
                service = EmbeddingService(session)
                job = await service.generate_embeddings_for_document(resource_id, force=force)
                await service.execute_embedding_job(job.id, force=force)
                await session.commit()
        except Exception as exc:
            logger.exception(
                "FastAPIEmbeddingQueue: unhandled error for resource {}: {}",
                resource_id,
                exc,
            )


# Default queue singleton
embedding_queue: AbstractEmbeddingQueue = FastAPIEmbeddingQueue()


def get_embedding_queue() -> AbstractEmbeddingQueue:
    """Return the active embedding queue (DI hook)."""
    return embedding_queue
