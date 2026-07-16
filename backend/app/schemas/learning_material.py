"""
Pydantic Schemas for Phase 10 Learning Material Generation.
"""

import uuid
from datetime import datetime
from typing import Any, List, Optional
from pydantic import BaseModel, Field


class LearningMaterialGenerateRequest(BaseModel):
    """Schema representing learning material generation inputs."""

    course_id: uuid.UUID = Field(..., description="Target Course UUID mapping outcomes.")
    topic_id: uuid.UUID = Field(..., description="Target syllabus Topic UUID.")
    generator_type: str = Field(
        ...,
        description="Type of learning material (e.g. 'Concept Explanation', 'Worked Examples', etc.).",
        examples=["Concept Explanation"],
    )
    bloom_level: Optional[str] = Field(
        None,
        description="Target cognitive Bloom level (Remember, Understand, Apply, etc.).",
        examples=["Understand"],
    )
    knowledge_level: Optional[str] = Field(
        None,
        description="Target knowledge dimension (Factual, Conceptual, Procedural, Metacognitive).",
        examples=["Conceptual"],
    )
    teaching_style: Optional[str] = Field(
        None,
        description="Target faculty teaching style constraint.",
        examples=["Socratic"],
    )
    pedagogical_approach: Optional[str] = Field(
        None,
        description="Target pedagogical framework constraint.",
        examples=["Inquiry-based"],
    )
    difficulty: Optional[str] = Field(
        None,
        description="Difficulty level constraint (Easy, Medium, Hard).",
        examples=["Medium"],
    )
    faculty_preferences: Optional[str] = Field(
        None,
        description="Custom free-text faculty styling preferences.",
        max_length=1000,
        examples=["Explain it using analogies to standard web architectures."],
    )
    output_format: str = Field(
        "markdown",
        description="Format of the output generated content (markdown, html, text, json).",
        examples=["markdown"],
    )


class LearningMaterialRegenerateRequest(BaseModel):
    """Schema representing learning material regeneration modifications."""

    material_id: uuid.UUID = Field(..., description="Target Learning Material ID to regenerate.")
    faculty_preferences: Optional[str] = Field(
        None,
        description="Appended custom free-text faculty overrides.",
        max_length=1000,
        examples=["Add more code snippets showing dynamic polymorphism."],
    )
    output_format: str = Field(
        "markdown",
        description="Format of the output generated content (markdown, html, text, json).",
    )


class LearningMaterialRead(BaseModel):
    """Schema representing learning material database state."""

    id: uuid.UUID
    course_id: uuid.UUID
    topic_id: uuid.UUID
    generator_type: str
    prompt_version: str
    model: str
    status: str
    content: str
    format: str
    created_by: uuid.UUID
    history: List[dict]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class LearningMaterialValidationRequest(BaseModel):
    """Schema representing educational structure validation check request."""

    text: str = Field(..., min_length=1, description="Generated content block to validate.")
    topic: str = Field(..., min_length=1, description="Target topic name.")
    bloom_level: Optional[str] = Field(None, description="Expected Bloom cognitive level.")
    course_outcomes: Optional[List[str]] = Field(None, description="Target course outcomes.")


class LearningMaterialValidationResponse(BaseModel):
    """Schema representing results of curriculum validation checks."""

    success: bool = Field(..., description="True if output aligns with constraints.")
    message: str = Field(..., description="Reason details of pass or validation warnings.")


class LearningMaterialCacheDetails(BaseModel):
    """Schema representing persistent cache entries metadata."""

    id: uuid.UUID
    cache_key: str
    content: str
    format: str
    created_at: datetime

    class Config:
        from_attributes = True
