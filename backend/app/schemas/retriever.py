"""
Pydantic schemas for context retrieval input requests and output payloads.
"""

from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, Field


class MetadataFilterModel(BaseModel):
    """
    Metadata filter rules to restrict vector store semantic queries.
    """

    course_id: UUID | None = Field(default=None, description="Restrict to a specific Course ID.")
    unit_id: UUID | None = Field(default=None, description="Restrict to a specific Unit ID.")
    topic_id: UUID | None = Field(default=None, description="Restrict to a specific Topic ID.")
    resource_id: UUID | None = Field(default=None, description="Restrict to a specific Resource/Document ID.")
    uploaded_by: UUID | None = Field(default=None, description="Restrict to resources uploaded by a specific Faculty ID.")
    resource_type: str | None = Field(default=None, description="Type of resource (e.g. Textbook, Notes).")
    bloom_level: str | None = Field(default=None, description="Bloom learning level taxonomy match.")
    knowledge_level: str | None = Field(default=None, description="Curriculum outcome knowledge level matches.")
    difficulty: str | None = Field(default=None, description="Course materials difficulty filter.")
    created_after: datetime | None = Field(default=None, description="Exclude mappings created before this timestamp.")
    created_before: datetime | None = Field(default=None, description="Exclude mappings created after this timestamp.")


class RetrieveRequest(BaseModel):
    """
    Request model for general context retrieval.
    """

    query: str = Field(..., min_length=1, max_length=2000, description="Semantic search query.")
    limit: int | None = Field(default=None, ge=1, le=100, description="Number of results to retrieve.")
    filters: MetadataFilterModel | None = Field(default=None, description="Metadata filtering constraints.")
    relevance_threshold: float | None = Field(default=None, ge=0.0, le=1.0, description="Similarity threshold limit.")


class RetrieveTopKRequest(BaseModel):
    """
    Request model for simple top-K retrieval.
    """

    query: str = Field(..., min_length=1, max_length=2000)
    k: int = Field(default=5, ge=1, le=100)


class RetrieveCourseRequest(BaseModel):
    """
    Request model for course-specific context retrieval.
    """

    query: str = Field(..., min_length=1, max_length=2000)
    course_id: UUID
    limit: int = Field(default=5, ge=1, le=100)


class RetrieveTopicRequest(BaseModel):
    """
    Request model for topic-specific context retrieval.
    """

    query: str = Field(..., min_length=1, max_length=2000)
    topic_id: UUID
    limit: int = Field(default=5, ge=1, le=100)


class RetrieveUnitRequest(BaseModel):
    """
    Request model for unit-specific context retrieval.
    """

    query: str = Field(..., min_length=1, max_length=2000)
    unit_id: UUID
    limit: int = Field(default=5, ge=1, le=100)


class ContextChunkRead(BaseModel):
    """
    Structured representation of a single matching retrieved text chunk.
    """

    chunk_id: UUID
    text: str
    score: float
    course_id: UUID
    resource_id: UUID
    resource_title: str
    page_numbers: str | None
    chunk_title: str | None
    chapter_name: str | None
    section_heading: str | None
    subheading: str | None
    bloom_level: str | None
    knowledge_level: str | None
    resource_type: str | None


class ContextPackageRead(BaseModel):
    """
    Complete assembled context response containing all metadata chunks and combined markdown prompt.
    """

    query: str
    chunks: list[ContextChunkRead]
    formatted_context: str
