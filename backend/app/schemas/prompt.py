"""
Pydantic schemas for the Prompt Builder.

Schemas enforce input validation at the HTTP boundary so that the service
layer can operate on already-validated, well-typed data.
"""

from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, Field, field_validator


# ── Template Schemas ──────────────────────────────────────────────────────────


class PromptTemplateCreate(BaseModel):
    """Schema to create a custom prompt template."""

    name: str = Field(..., min_length=1, max_length=255)
    generation_type: str = Field(..., min_length=1, max_length=100)
    system_prompt: str = Field(..., min_length=1)
    instruction_prompt: str = Field(..., min_length=1)
    educational_constraints: str = Field(..., min_length=1)
    output_format: str = Field(..., min_length=1)


class PromptTemplateUpdate(BaseModel):
    """Schema to update an existing custom prompt template."""

    name: str | None = Field(None, min_length=1, max_length=255)
    generation_type: str | None = Field(None, min_length=1, max_length=100)
    system_prompt: str | None = Field(None, min_length=1)
    instruction_prompt: str | None = Field(None, min_length=1)
    educational_constraints: str | None = Field(None, min_length=1)
    output_format: str | None = Field(None, min_length=1)


class PromptTemplateRead(BaseModel):
    """Schema to represent a prompt template in JSON outputs."""

    id: UUID
    name: str
    generation_type: str
    system_prompt: str
    instruction_prompt: str
    educational_constraints: str
    output_format: str
    is_system_default: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ── Chunk Schema ──────────────────────────────────────────────────────────────


class RetrievedChunk(BaseModel):
    """Schema for an individual retrieved context chunk."""

    chunk_id: str = Field(..., description="Unique chunk identifier.")
    text: str = Field(..., min_length=1, description="Chunk text content.")
    score: float = Field(
        0.0,
        ge=0.0,
        le=1.0,
        description="Relevance score (0.0 – 1.0).",
    )


# ── Build Schemas ─────────────────────────────────────────────────────────────


class PromptBuildRequest(BaseModel):
    """Schema to build an educational prompt."""

    generation_type: str = Field(
        ...,
        min_length=1,
        description="The type of material to construct (e.g. MCQs, Learning Material).",
    )
    retrieved_chunks: list[RetrievedChunk] = Field(
        ...,
        min_length=1,
        description="Ordered list of retrieved context chunks (must include chunk_id, text, score).",
    )
    topic: str = Field(..., min_length=1, description="Target curriculum topic.")
    course: str = Field(..., min_length=1, description="Academic course identifier or name.")
    course_outcomes: str = Field(..., min_length=1, description="Course learning objectives (COs).")
    unit: str = Field(..., min_length=1, description="Course unit identifier.")
    bloom_distribution: str = Field(
        ..., min_length=1, description="Bloom taxonomy level requirements."
    )
    knowledge_level: str | None = Field(None, description="Target knowledge level.")
    teaching_style: str | None = Field(None, description="Instructor teaching style.")
    pedagogical_approach: str | None = Field(None, description="Pedagogical framework.")
    difficulty: str | None = Field(None, description="Difficulty tier (Easy, Medium, Hard).")
    faculty_preferences: str | None = Field(
        None,
        max_length=1000,
        description="Custom instructor requirements.",
    )
    max_tokens: int = Field(
        8192,
        ge=512,
        le=32768,
        description="Maximum token budget for the final prompt.",
    )

    @field_validator("retrieved_chunks", mode="before")
    @classmethod
    def coerce_chunks(cls, value: list) -> list:
        """Accept list[dict] for backwards compatibility; validate shape."""
        if not value:
            raise ValueError("retrieved_chunks must not be empty.")
        return value


class PromptBuildResponse(BaseModel):
    """Payload representing a finalized compiled prompt."""

    system_prompt: str
    instruction_prompt: str
    retrieved_context: str
    full_prompt: str
    generation_type: str
    metadata: dict
    estimated_tokens: int


# ── Validation Schemas ────────────────────────────────────────────────────────


class PromptValidationRequest(BaseModel):
    """Schema to validate prompt properties and size-constraint boundaries."""

    retrieved_context: str = Field(..., min_length=1)
    topic: str = Field(..., min_length=1)
    bloom_distribution: str = Field(..., min_length=1)
    educational_constraints: str = Field(..., min_length=1)
    course_outcomes: str | None = None
    faculty_preferences: str | None = Field(None, max_length=1000)
    full_prompt: str = Field(..., min_length=1)
    max_tokens: int = Field(16000, ge=1, le=65536)


class PromptValidationResponse(BaseModel):
    """Payload return for validation queries."""

    success: bool
    message: str
    estimated_tokens: int


# ── Estimation Schemas ────────────────────────────────────────────────────────


class PromptEstimationRequest(BaseModel):
    """Schema to request token-length count heuristics."""

    text: str = Field(..., min_length=1, description="Text to estimate token count for.")


class PromptEstimationResponse(BaseModel):
    """Payload return for token count estimations."""

    estimated_tokens: int
