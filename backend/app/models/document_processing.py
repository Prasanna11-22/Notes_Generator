"""
Document Processing ORM models.

Two tables:

* ``document_processing``  — One-per-resource record tracking the current
  processing job status and runtime statistics.
* ``document_metadata``    — One-per-resource record storing the extracted
  raw and cleaned text together with document-level metadata.

Both tables use CASCADE-delete so that removing a resource automatically
cleans up all downstream processing artefacts.
"""

import uuid
from datetime import datetime
from enum import StrEnum

from sqlalchemy import Boolean, Float, ForeignKey, Integer, String, Text
from sqlalchemy import DateTime
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import JSON

from app.database.base import Base, TimestampMixin


# ── Processing Status Enum ────────────────────────────────────────────────────


class ProcessingStatus(StrEnum):
    """Lifecycle states of a single document-processing job."""

    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    # Returned when all PDF pages are image-only (no selectable text)
    # and OCR has not been enabled.
    OCR_REQUIRED = "ocr_required"


# ── DocumentProcessing Model ──────────────────────────────────────────────────


class DocumentProcessing(Base, TimestampMixin):
    """
    Tracks the lifecycle of a document-processing job.

    One record exists per resource (unique constraint on ``resource_id``).
    When a resource is reprocessed the same record is updated in-place so
    that there is always exactly one current status per resource.

    The ``processing_history`` column stores a JSON list of previous run
    summaries to preserve an audit trail without growing unbounded.
    """

    __tablename__ = "document_processing"

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
        unique=True,  # one processing record per resource
        index=True,
    )

    # ── Job state ────────────────────────────────────────────────────────────
    status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default=ProcessingStatus.PENDING.value,
        server_default=ProcessingStatus.PENDING.value,
        index=True,
    )
    parser_used: Mapped[str | None] = mapped_column(String(100), nullable=True)

    # ── Timing ───────────────────────────────────────────────────────────────
    started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    processing_duration_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # ── Outcome stats ────────────────────────────────────────────────────────
    page_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    # ── Audit trail — previous run summaries ─────────────────────────────────
    processing_history: Mapped[list | None] = mapped_column(
        JSON,
        nullable=True,
        default=list,
        server_default="[]",
    )

    # ── Relationships ────────────────────────────────────────────────────────
    resource = relationship("Resource", back_populates="processing_job")
    metadata_record: Mapped["DocumentMetadata | None"] = relationship(
        "DocumentMetadata",
        back_populates="processing_job",
        uselist=False,
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    def __repr__(self) -> str:
        return (
            f"<DocumentProcessing resource_id={self.resource_id} status={self.status}>"
        )


# ── DocumentMetadata Model ────────────────────────────────────────────────────


class DocumentMetadata(Base, TimestampMixin):
    """
    Stores the text content and metadata extracted from a processed document.

    Created (or updated) when processing completes successfully.
    Foreign-keyed to both ``document_processing`` and ``resources``.
    """

    __tablename__ = "document_metadata"

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
    processing_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("document_processing.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # ── Document-level properties ─────────────────────────────────────────────
    title: Mapped[str | None] = mapped_column(String(500), nullable=True)
    author: Mapped[str | None] = mapped_column(String(500), nullable=True)
    page_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    language: Mapped[str | None] = mapped_column(
        String(20), nullable=True, index=True
    )  # ISO 639-1
    word_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    char_count: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # ── Document timestamps (from file metadata, not DB timestamps) ───────────
    document_created_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    document_modified_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # ── Extracted text ────────────────────────────────────────────────────────
    raw_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    cleaned_text: Mapped[str | None] = mapped_column(Text, nullable=True)

    # ── Full raw metadata blob (parser-specific) ──────────────────────────────
    raw_metadata: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    # ── Scanned-PDF flag ──────────────────────────────────────────────────────
    is_scanned: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="false"
    )

    # ── Relationships ─────────────────────────────────────────────────────────
    resource = relationship("Resource")
    processing_job: Mapped["DocumentProcessing"] = relationship(
        "DocumentProcessing",
        back_populates="metadata_record",
    )

    def __repr__(self) -> str:
        return (
            f"<DocumentMetadata resource_id={self.resource_id} "
            f"lang={self.language} words={self.word_count}>"
        )
