"""
Pydantic Schemas for Phase 12 Assignment & Learning Activity Generation.
"""

import uuid
from datetime import datetime
from typing import Dict, List, Optional
from pydantic import BaseModel, Field, field_validator


class AssignmentGenerateRequest(BaseModel):
    """Schema representing assignment generation inputs."""

    course_id: uuid.UUID = Field(..., description="Target Course UUID mapping outcomes.")
    topic_id: uuid.UUID = Field(..., description="Target syllabus Topic UUID.")
    generator_type: str = Field(
        ...,
        description="Target assignment or activity type (Descriptive Questions, Programming Assignments, etc.).",
        examples=["Programming Assignments"],
    )
    bloom_level: str = Field(
        "Apply",
        description="Target cognitive Bloom level (Remember, Understand, Apply, Analyze, Evaluate, Create).",
        examples=["Apply"],
    )
    difficulty: str = Field(
        "Medium",
        description="Difficulty constraint level (Easy, Medium, Hard).",
        examples=["Medium"],
    )
    marks: int = Field(
        ...,
        description="Total maximum mark weight for the assignment.",
        ge=1,
        le=100,
        examples=[50],
    )
    knowledge_level: Optional[str] = Field(
        None,
        description="Target knowledge dimension category.",
        examples=["Conceptual"],
    )
    teaching_style: Optional[str] = Field(
        None,
        description="Target teaching style constraint.",
        examples=["Socratic"],
    )
    pedagogical_approach: Optional[str] = Field(
        None,
        description="Target pedagogical framework constraint.",
        examples=["Inquiry-based"],
    )
    faculty_preferences: Optional[str] = Field(
        None,
        description="Custom free-text faculty styling preferences.",
        max_length=1000,
        examples=["Focus on practical programming scenarios."],
    )

    @field_validator("difficulty")
    @classmethod
    def validate_difficulty(cls, v: str) -> str:
        cleaned = v.strip().capitalize()
        if cleaned not in ("Easy", "Medium", "Hard"):
            raise ValueError("Difficulty must be one of: Easy, Medium, Hard.")
        return cleaned

    @field_validator("bloom_level")
    @classmethod
    def validate_bloom_level(cls, v: str) -> str:
        allowed = {"Remember", "Understand", "Apply", "Analyze", "Evaluate", "Create"}
        cleaned = v.strip().capitalize()
        if cleaned not in allowed:
            raise ValueError(f"Invalid Bloom level category: '{v}'. Must be one of: {allowed}")
        return cleaned


class AssignmentRegenerateRequest(BaseModel):
    """Schema representing assignment regeneration inputs."""

    assignment_id: uuid.UUID = Field(..., description="Target Assignment UUID to regenerate.")
    faculty_preferences: Optional[str] = Field(
        None,
        description="Appended custom free-text faculty overrides.",
        max_length=1000,
        examples=["Add more programming requirements."],
    )


class AssignmentRead(BaseModel):
    """Schema representing assignment database state."""

    id: uuid.UUID
    course_id: uuid.UUID
    topic_id: uuid.UUID
    generator_type: str
    marks: int
    difficulty: str
    bloom_level: str
    prompt_version: str
    model_version: str
    content: str
    rubric: dict
    created_by: uuid.UUID
    history: List[dict]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class AssignmentValidationRequest(BaseModel):
    """Schema representing manual quality checks request for assignments."""

    content: str = Field(..., min_length=1, description="Generated assignment text.")
    topic: str = Field(..., description="Target topic name.")
    bloom_level: str = Field(..., description="Target Bloom taxonomy category.")
    difficulty: str = Field(..., description="Target difficulty tier.")
    rubric: dict = Field(..., description="Grading rubric dictionary.")
    pedagogical_approach: Optional[str] = Field(None, description="Target pedagogical approach name.")
    teaching_style: Optional[str] = Field(None, description="Target teaching style name.")


class AssignmentValidationResponse(BaseModel):
    """Schema representing assignment manual validation check outcomes."""

    success: bool
    message: str
