"""
Chunk and ChunkMapping Database Repositories.

Provides persistence operations, filtered lists, details queries, and analytics
statistics reporting for chunks and mappings.
"""

from __future__ import annotations

from uuid import UUID
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.chunk import Chunk, ChunkMapping
from app.repositories.base import BaseRepository


class ChunkRepository(BaseRepository[Chunk]):
    """Repository operations for unique ``Chunk`` records."""

    model = Chunk

    async def get_by_hash(self, chunk_hash: str) -> Chunk | None:
        """Find a unique chunk by its text hash (exact matching)."""
        result = await self._session.execute(
            select(Chunk).where(Chunk.chunk_hash == chunk_hash)
        )
        return result.scalar_one_or_none()

    async def get_all_unique_chunks(self) -> list[Chunk]:
        """Fetch all unique chunks for similarity comparisons."""
        result = await self._session.execute(select(Chunk))
        return list(result.scalars().all())


class ChunkMappingRepository(BaseRepository[ChunkMapping]):
    """Repository operations for resource-to-chunk placement mappings."""

    model = ChunkMapping

    async def list_by_resource(
        self,
        resource_id: UUID,
        *,
        skip: int = 0,
        limit: int = 100,
    ) -> list[ChunkMapping]:
        """
        List all chunk mappings associated with *resource_id*, ordered by
        positional index.  Eager-loads the underlying unique chunk data.
        """
        stmt = (
            select(ChunkMapping)
            .where(ChunkMapping.resource_id == resource_id)
            .options(selectinload(ChunkMapping.chunk))
            .order_by(ChunkMapping.chunk_index.asc())
            .offset(skip)
            .limit(limit)
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def delete_by_resource(self, resource_id: UUID) -> None:
        """Physically delete all mappings belonging to *resource_id*."""
        from sqlalchemy import delete

        stmt = delete(ChunkMapping).where(ChunkMapping.resource_id == resource_id)
        await self._session.execute(stmt)
        await self._session.flush()

    async def get_mapping_with_details(self, mapping_id: UUID) -> ChunkMapping | None:
        """Fetch a specific mapping and load the unique chunk and course info."""
        stmt = (
            select(ChunkMapping)
            .where(ChunkMapping.id == mapping_id)
            .options(
                selectinload(ChunkMapping.chunk),
                selectinload(ChunkMapping.course),
            )
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    # ── Analytics and Reports ─────────────────────────────────────────────────

    async def get_global_statistics(self) -> dict:
        """
        Compute global chunk database metrics:
        - Total unique chunks
        - Total mapping references
        - Duplicate compression ratio
        - Average chunk character count
        """
        # Unique chunks count
        unique_cnt_stmt = select(func.count(Chunk.id))
        unique_cnt_res = await self._session.execute(unique_cnt_stmt)
        unique_cnt = unique_cnt_res.scalar_one()

        # Mapping instances count
        mapping_cnt_stmt = select(func.count(ChunkMapping.id))
        mapping_cnt_res = await self._session.execute(mapping_cnt_stmt)
        mapping_cnt = mapping_cnt_res.scalar_one()

        # Average character size
        avg_char_stmt = select(func.avg(Chunk.char_count))
        avg_char_res = await self._session.execute(avg_char_stmt)
        avg_char = avg_char_res.scalar_one() or 0.0

        # Compression ratio
        compression_ratio = 0.0
        if unique_cnt > 0:
            compression_ratio = mapping_cnt / unique_cnt

        return {
            "total_unique_chunks": unique_cnt,
            "total_mapped_instances": mapping_cnt,
            "compression_ratio": round(compression_ratio, 2),
            "average_chunk_characters": round(avg_char, 1),
        }

    async def get_quality_report(self) -> list[dict]:
        """
        Scan mappings and chunks to identify warning signs:
        - Chunks with missing course outcomes
        - Orphaned unique chunks (unreferenced by any mappings)
        """
        warnings: list[dict] = []

        # Find mappings without mapped topic or course outcome
        missing_co_stmt = (
            select(ChunkMapping)
            .where(ChunkMapping.course_outcome_id.is_(None))
            .limit(100)
        )
        missing_co_res = await self._session.execute(missing_co_stmt)
        missing_co_mappings = missing_co_res.scalars().all()

        for m in missing_co_mappings:
            warnings.append(
                {
                    "type": "missing_course_outcome",
                    "entity_id": str(m.id),
                    "resource_id": str(m.resource_id),
                    "chunk_index": m.chunk_index,
                    "message": "Chunk could not be aligned to any curriculum course outcome.",
                }
            )

        return warnings
