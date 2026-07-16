"""
Retriever database repository.
"""

from uuid import UUID
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.embedding import ChunkEmbedding
from app.models.chunk import Chunk, ChunkMapping
from app.repositories.base import BaseRepository


class RetrieverRepository(BaseRepository[ChunkEmbedding]):
    """
    Repository operations for retrieving chunks and mapping details.
    """

    model = ChunkEmbedding

    async def get_embeddings_by_vector_ids(self, vector_ids: list[str]) -> list[ChunkEmbedding]:
        """
        Query ChunkEmbedding metadata by their FAISS vector_store_ids.
        Eagerly loads Chunk, ChunkMappings, and Resource models.
        """
        if not vector_ids:
            return []

        stmt = (
            select(ChunkEmbedding)
            .where(ChunkEmbedding.vector_store_id.in_(vector_ids))
            .options(
                selectinload(ChunkEmbedding.chunk)
                .selectinload(Chunk.mappings)
                .selectinload(ChunkMapping.resource)
            )
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())
