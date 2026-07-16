"""Models package — import all models here so Alembic can discover them."""

from app.models.curriculum import (
    BloomLevel,
    Course,
    CourseOutcome,
    Department,
    KnowledgeLevel,
    Program,
    Semester,
    Topic,
    TopicMapping,
    Unit,
)
from app.models.chunk import Chunk, ChunkMapping, DocumentChunkingJob
from app.models.embedding import ChunkEmbedding, DocumentEmbeddingJob
from app.models.prompt_template import PromptTemplate
from app.models.document_processing import DocumentMetadata, DocumentProcessing, ProcessingStatus
from app.models.resource import Resource
from app.models.user import User, UserRole

__all__ = [
    "User",
    "UserRole",
    "BloomLevel",
    "KnowledgeLevel",
    "Department",
    "Program",
    "Semester",
    "Course",
    "Unit",
    "Topic",
    "CourseOutcome",
    "TopicMapping",
    "Resource",
    "ProcessingStatus",
    "DocumentProcessing",
    "DocumentMetadata",
    "Chunk",
    "ChunkMapping",
    "DocumentChunkingJob",
    "ChunkEmbedding",
    "DocumentEmbeddingJob",
    "PromptTemplate",
]


