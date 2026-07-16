"""
Database models for Chunk Embeddings and Embedding Jobs.
"""

import uuid
from datetime import datetime
from sqlalchemy import ForeignKey, Integer, String, Text, DateTime, Float
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base, TimestampMixin


class ChunkEmbedding(Base, TimestampMixin):
    """
    Metadata for a chunk's generated embedding vector stored in the vector index.
    The high-dimensional vector itself is persisted inside FAISS/Vector Store.
    """

    __tablename__ = "chunk_embeddings"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        index=True,
    )
    chunk_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("chunks.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )
    model_name: Mapped[str] = mapped_column(String(255), nullable=False)
    model_version: Mapped[str] = mapped_column(String(50), nullable=False)
    dimension: Mapped[int] = mapped_column(Integer, nullable=False)
    vector_store_id: Mapped[str] = mapped_column(String(255), nullable=False, unique=True, index=True)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="completed")
    processing_time: Mapped[float | None] = mapped_column(Float, nullable=True)

    # Relationships
    chunk = relationship("Chunk", back_populates="embedding")

    def __repr__(self) -> str:
        return f"<ChunkEmbedding id={self.id} chunk_id={self.chunk_id} model={self.model_name}>"


class DocumentEmbeddingJob(Base, TimestampMixin):
    """
    Tracks the background job execution state for generating embeddings for a resource.
    """

    __tablename__ = "document_embedding_jobs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        index=True,
    )
    resource_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("resources.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="pending")
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    embeddings_count: Mapped[int | None] = mapped_column(Integer, nullable=True)

    started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    resource = relationship("Resource")

    def __repr__(self) -> str:
        return f"<DocumentEmbeddingJob resource_id={self.resource_id} status={self.status}>"
