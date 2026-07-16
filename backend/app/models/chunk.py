"""
Chunk and ChunkMapping database models.

Follows a split normalization design to prevent duplicate text contents
from bloating database storage:
- ``chunks``: stores unique text contents and statistical metadata.
- ``chunk_mappings``: stores structural references connecting a unique chunk
  to a resource, page number, and its location inside the curriculum.
"""

import uuid
from datetime import datetime

from sqlalchemy import Boolean, Float, ForeignKey, Integer, String, Text, DateTime, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base, TimestampMixin


class Chunk(Base, TimestampMixin):
    """
    Represents a unique piece of text content extracted from document resources.

    Identified by a SHA-256 hash of its cleaned text to prevent duplicate
    text rows.
    """

    __tablename__ = "chunks"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        index=True,
    )
    chunk_hash: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        unique=True,
        index=True,
    )
    cleaned_text: Mapped[str] = mapped_column(Text, nullable=False)
    raw_text: Mapped[str] = mapped_column(Text, nullable=False)

    # Statistical analytics
    char_count: Mapped[int] = mapped_column(Integer, nullable=False)
    word_count: Mapped[int] = mapped_column(Integer, nullable=False)
    estimated_reading_time: Mapped[float] = mapped_column(Float, nullable=False)  # in minutes

    # Relationships
    mappings: Mapped[list["ChunkMapping"]] = relationship(
        "ChunkMapping",
        back_populates="chunk",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    embedding = relationship(
        "ChunkEmbedding",
        back_populates="chunk",
        uselist=False,
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    def __repr__(self) -> str:
        return f"<Chunk id={self.id} hash={self.chunk_hash[:8]} chars={self.char_count}>"


class ChunkMapping(Base, TimestampMixin):
    """
    Connects a unique text chunk to its resource and curriculum location.

    Maps to resource, course, unit, topic, and course outcomes, while storing
    page numbers, index ordering, and section headers.
    """

    __tablename__ = "chunk_mappings"
    __table_args__ = (
        UniqueConstraint("resource_id", "chunk_index", name="uq_resource_chunk_index"),
    )

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
        index=True,
    )
    resource_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("resources.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    course_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("courses.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    unit_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("units.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    topic_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("topics.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    course_outcome_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("course_outcomes.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # Document details
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    page_numbers: Mapped[str] = mapped_column(String(50), nullable=False)  # e.g., "1" or "3-4"
    chunk_title: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # Educational Metadata Context
    bloom_level: Mapped[str | None] = mapped_column(String(50), nullable=True)
    knowledge_level: Mapped[str | None] = mapped_column(String(50), nullable=True)
    resource_type: Mapped[str | None] = mapped_column(String(100), nullable=True)

    # Structural Placement Metadata
    chapter_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    section_heading: Mapped[str | None] = mapped_column(String(255), nullable=True)
    subheading: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # Relationships
    chunk: Mapped[Chunk] = relationship("Chunk", back_populates="mappings")
    resource = relationship("Resource")
    course = relationship("Course")
    unit = relationship("Unit")
    topic = relationship("Topic")
    course_outcome = relationship("CourseOutcome")

    def __repr__(self) -> str:
        return (
            f"<ChunkMapping id={self.id} resource_id={self.resource_id} "
            f"chunk_id={self.chunk_id} index={self.chunk_index}>"
        )


class DocumentChunkingJob(Base, TimestampMixin):
    """
    Tracks the background job state for splitting a resource.
    """

    __tablename__ = "document_chunking_jobs"

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
    chunks_count: Mapped[int | None] = mapped_column(Integer, nullable=True)

    started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    resource = relationship("Resource")

    def __repr__(self) -> str:
        return f"<DocumentChunkingJob resource_id={self.resource_id} status={self.status}>"

