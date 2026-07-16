"""
Embedding and DocumentEmbeddingJob repositories.
"""

from uuid import UUID
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.embedding import ChunkEmbedding, DocumentEmbeddingJob
from app.repositories.base import BaseRepository


class EmbeddingRepository(BaseRepository[ChunkEmbedding]):
    """
    Repository operations for unique ChunkEmbedding records.
    """

    model = ChunkEmbedding

    async def get_by_chunk_id(self, chunk_id: UUID) -> ChunkEmbedding | None:
        """
        Find an embedding metadata record by the chunk's UUID.
        """
        result = await self._session.execute(
            select(ChunkEmbedding).where(ChunkEmbedding.chunk_id == chunk_id)
        )
        return result.scalar_one_or_none()

    async def get_by_vector_store_id(self, vector_store_id: str) -> ChunkEmbedding | None:
        """
        Find an embedding metadata record by the vector store ID (UUID string).
        """
        result = await self._session.execute(
            select(ChunkEmbedding).where(ChunkEmbedding.vector_store_id == vector_store_id)
        )
        return result.scalar_one_or_none()


class DocumentEmbeddingJobRepository(BaseRepository[DocumentEmbeddingJob]):
    """
    Repository operations for tracking document embedding jobs.
    """

    model = DocumentEmbeddingJob

    async def get_by_resource_id(self, resource_id: UUID) -> DocumentEmbeddingJob | None:
        """
        Find a document embedding job tracking record by its resource UUID.
        """
        result = await self._session.execute(
            select(DocumentEmbeddingJob).where(DocumentEmbeddingJob.resource_id == resource_id)
        )
        return result.scalar_one_or_none()
