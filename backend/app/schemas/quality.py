"""
Pydantic schemas for Phase 14 Academic Quality & Intelligence Engine.
"""

import uuid
from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field


class QualityValidationRequest(BaseModel):
    """Payload schema representing content parameters to validate."""

    content: str = Field(..., min_length=1, description="Generated educational content text.")
    topic_name: str = Field(..., min_length=1, description="Curriculum topic name.")
    target_bloom: str = Field(..., description="Target Bloom level (e.g. Apply).")
    target_difficulty: str = Field(..., description="Target difficulty (e.g. Medium).")
    topic_description: Optional[str] = Field(None, description="Detailed topic syllabus text.")
    unit_title: Optional[str] = Field(None, description="Unit name.")
    course_outcomes: Optional[List[str]] = Field(None, description="Active course outcomes descriptions.")
    teaching_style: Optional[str] = Field(None, description="Target teaching style.")
    expected_length: Optional[int] = Field(None, description="Expected content length word count.")
    preferred_examples: Optional[str] = Field(None, description="Preferred examples context keywords.")
    content_id: Optional[uuid.UUID] = Field(None, description="Reference content ID if already saved.")
    content_type: Optional[str] = Field(None, description="Type of reference content (e.g. material, mcq).")


class QualityReportRead(BaseModel):
    """Schema representing validation quality audit details."""

    id: uuid.UUID
    content_id: Optional[uuid.UUID]
    content_type: Optional[str]
    quality_score: float
    confidence_score: float
    validation_details: dict
    validation_timestamp: datetime

    class Config:
        from_attributes = True


class FacultyPreferenceCreate(BaseModel):
    """Payload schema to save faculty preferences."""

    teaching_style: str = Field(..., min_length=1)
    difficulty: str = Field(..., min_length=1)
    examples: Optional[str] = None
    content_length: Optional[int] = 1000
    formatting_preferences: Optional[dict] = None


class FacultyPreferenceRead(BaseModel):
    """Schema representing faculty preference details."""

    id: uuid.UUID
    faculty_id: uuid.UUID
    teaching_style: str
    difficulty: str
    examples: Optional[str]
    content_length: int
    formatting_preferences: dict
    updated_at: datetime

    class Config:
        from_attributes = True
