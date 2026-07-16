"""
Document Processing Repository.

Provides typed persistence operations for ``DocumentProcessing`` and
``DocumentMetadata`` records, extending ``BaseRepository`` with
domain-specific queries needed by the processing service.
"""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.document_processing import DocumentMetadata, DocumentProcessing
from app.repositories.base import BaseRepository


class DocumentProcessingRepository(BaseRepository[DocumentProcessing]):
    """Repository for ``DocumentProcessing`` records."""

    model = DocumentProcessing

    # ── Single-record lookups ─────────────────────────────────────────────────

    async def get_by_resource_id(
        self, resource_id: UUID
    ) -> DocumentProcessing | None:
        """
        Return the processing job for *resource_id*, or ``None``.

        There is at most one processing record per resource (UNIQUE constraint).
        """
        result = await self._session.execute(
            select(DocumentProcessing).where(
                DocumentProcessing.resource_id == resource_id
            )
        )
        return result.scalar_one_or_none()

    # ── Filtered list ─────────────────────────────────────────────────────────

    async def list_by_status(
        self,
        status: str,
        *,
        skip: int = 0,
        limit: int = 100,
    ) -> list[DocumentProcessing]:
        """Return all processing records with the given *status*."""
        result = await self._session.execute(
            select(DocumentProcessing)
            .where(DocumentProcessing.status == status)
            .offset(skip)
            .limit(limit)
        )
        return list(result.scalars().all())


class DocumentMetadataRepository(BaseRepository[DocumentMetadata]):
    """Repository for ``DocumentMetadata`` records."""

    model = DocumentMetadata

    async def get_by_resource_id(
        self, resource_id: UUID
    ) -> DocumentMetadata | None:
        """Return the metadata record for *resource_id*, or ``None``."""
        result = await self._session.execute(
            select(DocumentMetadata).where(
                DocumentMetadata.resource_id == resource_id
            )
        )
        return result.scalar_one_or_none()

    async def get_by_processing_id(
        self, processing_id: UUID
    ) -> DocumentMetadata | None:
        """Return the metadata record for *processing_id*, or ``None``."""
        result = await self._session.execute(
            select(DocumentMetadata).where(
                DocumentMetadata.processing_id == processing_id
            )
        )
        return result.scalar_one_or_none()
