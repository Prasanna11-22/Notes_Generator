"""
Embedding Pydantic schemas.
"""

from datetime import datetime
import uuid
from pydantic import BaseModel, ConfigDict, Field


class ChunkEmbeddingRead(BaseModel):
    """
    Public representation of a chunk's generated embedding metadata.
    """

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    chunk_id: uuid.UUID
    model_name: str
    model_version: str
    dimension: int
    vector_store_id: str
    status: str
    processing_time: float | None = None
    created_at: datetime
    updated_at: datetime


class DocumentEmbeddingJobRead(BaseModel):
    """
    State of a resource's background embedding generation job.
    """

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    resource_id: uuid.UUID
    status: str
    error_message: str | None = None
    embeddings_count: int | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None
    created_at: datetime
    updated_at: datetime


class EmbeddingGenerateRequest(BaseModel):
    """
    Payload to trigger embedding generation for a resource.
    """

    resource_id: uuid.UUID = Field(..., description="The ID of the document/resource to generate embeddings for.")


class EmbeddingRegenerateRequest(BaseModel):
    """
    Payload to trigger forced regeneration of embeddings for a resource.
    """

    resource_id: uuid.UUID = Field(..., description="The ID of the document/resource to regenerate embeddings for.")


class VectorStoreHealthRead(BaseModel):
    """
    Health check response from the Vector Store.
    """

    status: str
    index_loaded: bool
    total_vectors: int
    dimension: int


class SynchronizationReport(BaseModel):
    """
    Represents the detailed status comparing database metadata and the vector store index.
    """

    total_chunks_in_db: int
    total_embeddings_in_db: int
    total_vectors_in_faiss: int
    missing_vectors_count: int
    missing_metadata_count: int
    inconsistent_embeddings_count: int
    is_synchronized: bool
    missing_vectors: list[str] = Field(default_factory=list, description="IDs present in DB but missing in vector store.")
    missing_metadata: list[str] = Field(default_factory=list, description="IDs present in vector store but missing in DB.")
    inconsistent_embeddings: list[str] = Field(default_factory=list, description="IDs with wrong dimension or model info.")


class ReconcileResult(BaseModel):
    """
    Summary of the repair actions executed.
    """

    status: str
    repaired_vectors_count: int
    deleted_vectors_count: int
    repaired_metadata_count: int
