"""
Document Processing Pydantic v2 schemas.

Used as ``response_model`` types in API routes and for serialising
``DocumentProcessing`` / ``DocumentMetadata`` ORM records.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class DocumentProcessingRead(BaseModel):
    """
    Public representation of a document processing job.

    Returned by the status, details, enqueue, and reprocess endpoints.
    """

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    resource_id: uuid.UUID

    # Job state
    status: str = Field(
        description=(
            "Current status: pending | processing | completed | failed | ocr_required"
        )
    )
    parser_used: str | None = Field(
        default=None,
        description="Name of the parser that processed the document.",
    )

    # Timing
    started_at: datetime | None = None
    completed_at: datetime | None = None
    processing_duration_ms: int | None = Field(
        default=None,
        description="Wall-clock processing time in milliseconds.",
    )

    # Outcome
    page_count: int | None = None
    error_message: str | None = None

    # Audit
    created_at: datetime
    updated_at: datetime


class DocumentMetadataRead(BaseModel):
    """
    Public representation of extracted document metadata and text.

    The ``cleaned_text`` field is intentionally excluded from the default
    list-level response to keep payloads small; it is only exposed by the
    dedicated ``/text`` endpoint.
    """

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    resource_id: uuid.UUID
    processing_id: uuid.UUID

    # Document properties
    title: str | None = None
    author: str | None = None
    page_count: int | None = None
    language: str | None = Field(
        default=None, description="ISO 639-1 language code (e.g. 'en')."
    )
    word_count: int | None = None
    char_count: int | None = None

    # Document timestamps (from file metadata)
    document_created_at: datetime | None = None
    document_modified_at: datetime | None = None

    # Scanned flag
    is_scanned: bool = False

    # DB timestamps
    created_at: datetime
    updated_at: datetime


class DocumentTextRead(BaseModel):
    """
    Cleaned text payload returned by the ``/text`` endpoint.

    Kept separate from ``DocumentMetadataRead`` to avoid accidentally
    sending large text payloads on metadata-only queries.
    """

    model_config = ConfigDict(from_attributes=True)

    resource_id: uuid.UUID
    cleaned_text: str | None = None
    raw_text: str | None = None
    word_count: int | None = None
    char_count: int | None = None
    language: str | None = None
