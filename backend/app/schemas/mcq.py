"""
Pydantic Schemas for Phase 11 MCQ Generation.
"""

import uuid
from datetime import datetime
from typing import Dict, List, Optional
from pydantic import BaseModel, Field, field_validator


class MCQGenerateRequest(BaseModel):
    """Schema representing MCQ generation inputs."""

    course_id: uuid.UUID = Field(..., description="Target Course UUID mapping outcomes.")
    topic_id: uuid.UUID = Field(..., description="Target syllabus Topic UUID.")
    bloom_distribution: Dict[str, float] = Field(
        ...,
        description="Target Bloom taxonomy percentage distribution (keys: Remember, Understand, Apply, Analyze, Evaluate, Create).",
        examples=[{"Remember": 0.3, "Understand": 0.4, "Apply": 0.3}],
    )
    difficulty: str = Field(
        "Medium",
        description="Difficulty level constraint (Easy, Medium, Hard).",
        examples=["Medium"],
    )
    number_of_questions: int = Field(
        ...,
        description="Total number of questions to generate (integer count).",
        ge=1,
        le=50,
        examples=[5],
    )
    faculty_preferences: Optional[str] = Field(
        None,
        description="Custom free-text styling preferences or guidelines.",
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

    @field_validator("bloom_distribution")
    @classmethod
    def validate_bloom_dist(cls, v: Dict[str, float]) -> Dict[str, float]:
        allowed = {"Remember", "Understand", "Apply", "Analyze", "Evaluate", "Create"}
        for k in v.keys():
            if k.strip().capitalize() not in allowed:
                raise ValueError(f"Invalid Bloom level category: '{k}'. Must be one of: {allowed}")
        return v


class MCQRegenerateRequest(BaseModel):
    """Schema representing MCQ regeneration inputs."""

    question_id: uuid.UUID = Field(..., description="Target MCQ UUID to regenerate.")
    faculty_preferences: Optional[str] = Field(
        None,
        description="Appended custom free-text faculty overrides.",
        max_length=1000,
        examples=["Change distractors to be more challenging."],
    )


class MCQQuestionRead(BaseModel):
    """Schema representing MCQ question database state."""

    id: uuid.UUID
    course_id: uuid.UUID
    topic_id: uuid.UUID
    question_text: str
    options: dict
    correct_answer: str
    explanation: str
    bloom_level: str
    difficulty: str
    prompt_version: str
    model_version: str
    created_by: uuid.UUID
    history: List[dict]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class MCQValidationRequest(BaseModel):
    """Schema representing manual MCQ quality checks request."""

    question_text: str = Field(..., min_length=1, description="Question stem text.")
    options: Dict[str, str] = Field(..., description="Choices mapping keys to values.")
    correct_answer: str = Field(..., description="Correct option key choice index.")
    topic: str = Field(..., description="Target topic name.")
    bloom_level: str = Field(..., description="Target Bloom taxonomy category.")


class MCQValidationResponse(BaseModel):
    """Schema representing manual MCQ checks outcomes."""

    success: bool
    message: str
