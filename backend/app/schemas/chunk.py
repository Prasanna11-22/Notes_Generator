"""
Chunk and ChunkMapping Pydantic schemas.

Standardises request and response models for endpoints.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field


class ChunkRead(BaseModel):
    """Public representation of a unique text chunk."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    chunk_hash: str
    cleaned_text: str
    raw_text: str
    char_count: int
    word_count: int
    estimated_reading_time: float


class ChunkMappingRead(BaseModel):
    """Public representation of a specific resource chunk mapping."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    chunk_id: uuid.UUID
    resource_id: uuid.UUID
    course_id: uuid.UUID
    unit_id: uuid.UUID | None = None
    topic_id: uuid.UUID | None = None
    course_outcome_id: uuid.UUID | None = None

    chunk_index: int
    page_numbers: str
    chunk_title: str | None = None

    # Metadata enrichment values
    bloom_level: str | None = None
    knowledge_level: str | None = None
    resource_type: str | None = None

    # Headings
    chapter_name: str | None = None
    section_heading: str | None = None
    subheading: str | None = None

    created_at: datetime
    updated_at: datetime


class ChunkDetailsRead(BaseModel):
    """Detailed response combining mapping context and unique chunk content."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    chunk_index: int
    page_numbers: str
    chunk_title: str | None = None
    resource_id: uuid.UUID
    course_id: uuid.UUID
    unit_id: uuid.UUID | None = None
    topic_id: uuid.UUID | None = None
    course_outcome_id: uuid.UUID | None = None

    # Underlying chunk fields
    cleaned_text: str
    raw_text: str
    char_count: int
    word_count: int
    estimated_reading_time: float

    # Metadata
    bloom_level: str | None = None
    knowledge_level: str | None = None
    resource_type: str | None = None
    chapter_name: str | None = None
    section_heading: str | None = None
    subheading: str | None = None

    created_at: datetime
    updated_at: datetime


class ChunkPreviewItem(BaseModel):
    """Represents a chunk preview before saving it to the database."""

    chunk_index: int
    cleaned_text: str
    char_count: int
    word_count: int
    estimated_reading_time: float
    page_numbers: str
    chapter_name: str | None = None
    section_heading: str | None = None
    subheading: str | None = None


class ChunkStatistics(BaseModel):
    """Global database metrics for chunks."""

    total_unique_chunks: int
    total_mapped_instances: int
    compression_ratio: float
    average_chunk_characters: float


class ChunkQualityReportItem(BaseModel):
    """A quality warning entry for a specific chunk mapping."""

    type: str
    entity_id: str
    resource_id: str
    chunk_index: int
    message: str


class DocumentChunkingJobRead(BaseModel):
    """State of a resource's background chunking job."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    resource_id: uuid.UUID
    status: str
    chunks_count: int | None = None
    error_message: str | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None
    created_at: datetime
    updated_at: datetime
