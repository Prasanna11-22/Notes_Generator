"""
Processing Queue — Background Task Adapter.

This module provides a thin abstraction over the background task mechanism.
Currently uses FastAPI's ``BackgroundTasks`` (no external dependencies),
but the ``AbstractProcessingQueue`` interface allows the implementation to
be swapped for Celery, RQ, or any other task queue without changing the
API routes or service layer.

Swap Guide (future migration to Celery)
----------------------------------------
1. Create ``CeleryProcessingQueue(AbstractProcessingQueue)`` in this file.
2. Implement ``enqueue_processing`` to call ``celery_app.send_task(…)``.
3. Register the concrete class in the DI provider in ``app/dependencies/``.
4. Remove the ``FastAPIProcessingQueue`` registration.

No API routes or service logic need to change.
"""

from __future__ import annotations

import uuid
from abc import ABC, abstractmethod

from fastapi import BackgroundTasks
from loguru import logger

from app.database.session import AsyncSessionLocal
from app.services.document_processing import DocumentProcessingService


# ── Abstract interface ────────────────────────────────────────────────────────


class AbstractProcessingQueue(ABC):
    """
    Queue abstraction for document processing jobs.

    Concrete implementations decide *how* the job is executed
    (inline thread, Celery worker, cloud function, etc.).
    """

    @abstractmethod
    def enqueue_processing(
        self, resource_id: uuid.UUID, background_tasks: BackgroundTasks
    ) -> None:
        """
        Enqueue a document-processing job for *resource_id*.

        :param resource_id:      UUID of the resource to process.
        :param background_tasks: FastAPI ``BackgroundTasks`` instance from
                                 the current request — used by the default
                                 implementation; may be ignored by others.
        """


# ── FastAPI BackgroundTasks implementation ────────────────────────────────────


class FastAPIProcessingQueue(AbstractProcessingQueue):
    """
    Runs document processing as a FastAPI ``BackgroundTask``.

    The task is executed in the same process after the HTTP response is
    sent.  Each invocation opens a fresh ``AsyncSession`` so the processing
    job is not coupled to the request session.

    This is ideal for development and low-to-medium traffic.  Replace with
    ``CeleryProcessingQueue`` when horizontal scalability is required.
    """

    def enqueue_processing(
        self, resource_id: uuid.UUID, background_tasks: BackgroundTasks
    ) -> None:
        """Add the processing coroutine to FastAPI's background task queue."""
        background_tasks.add_task(self._run, resource_id)
        logger.info(
            "FastAPIProcessingQueue: scheduled processing for resource {}", resource_id
        )

    @staticmethod
    async def _run(resource_id: uuid.UUID) -> None:
        """
        Execute the processing pipeline inside a fresh database session.

        Errors are caught, logged, and recorded on the job record —
        they are never re-raised so FastAPI's background task runner
        does not crash the worker.
        """
        logger.info(
            "FastAPIProcessingQueue: starting background task for resource {}",
            resource_id,
        )
        try:
            async with AsyncSessionLocal() as session:
                service = DocumentProcessingService(session)
                await service.process(resource_id)
        except Exception as exc:
            # Broad catch here because we have no outer exception boundary
            # in a background task — log and continue.
            logger.exception(
                "FastAPIProcessingQueue: unhandled error for resource {}: {}",
                resource_id,
                exc,
            )


# ── Default queue singleton ───────────────────────────────────────────────────

#: Module-level default queue instance.  Override in tests or when switching
#: to a production task queue.
processing_queue: AbstractProcessingQueue = FastAPIProcessingQueue()


def get_processing_queue() -> AbstractProcessingQueue:
    """Return the configured processing queue instance (DI hook)."""
    return processing_queue
