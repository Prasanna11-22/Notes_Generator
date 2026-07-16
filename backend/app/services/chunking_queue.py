"""
Chunking Queue — Background Task Adapter.

Thin abstraction over the background execution queue for chunking tasks.
Similar to Phase 4's processing queue.
"""

from __future__ import annotations

import uuid
from abc import ABC, abstractmethod

from fastapi import BackgroundTasks
from loguru import logger

from app.database.session import AsyncSessionLocal
from app.services.chunking.orchestrator import ChunkingOrchestrator


class AbstractChunkingQueue(ABC):
    """
    Queue interface for chunking tasks.
    """

    @abstractmethod
    def enqueue_chunking(
        self, resource_id: uuid.UUID, background_tasks: BackgroundTasks
    ) -> None:
        """
        Enqueue a chunking job for *resource_id*.
        """


class FastAPIChunkingQueue(AbstractChunkingQueue):
    """
    Runs chunking asynchronously inside a FastAPI BackgroundTask.
    """

    def enqueue_chunking(
        self, resource_id: uuid.UUID, background_tasks: BackgroundTasks
    ) -> None:
        background_tasks.add_task(self._run, resource_id)
        logger.info(
            "FastAPIChunkingQueue: scheduled chunking for resource {}", resource_id
        )

    @staticmethod
    async def _run(resource_id: uuid.UUID) -> None:
        """
        Execute chunking in a fresh database session context.
        """
        logger.info(
            "FastAPIChunkingQueue: starting background chunking for resource {}",
            resource_id,
        )
        try:
            async with AsyncSessionLocal() as session:
                orchestrator = ChunkingOrchestrator(session)
                await orchestrator.process_chunking(resource_id)
        except Exception as exc:
            logger.exception(
                "FastAPIChunkingQueue: unhandled error for resource {}: {}",
                resource_id,
                exc,
            )


# Default queue singleton
chunking_queue: AbstractChunkingQueue = FastAPIChunkingQueue()


def get_chunking_queue() -> AbstractChunkingQueue:
    """Return the active chunking queue (DI hook)."""
    return chunking_queue
