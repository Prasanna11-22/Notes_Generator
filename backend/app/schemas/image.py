"""
Pydantic Schemas for Phase 13 Image Retrieval Engine.
"""

import uuid
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class ImageSearchRequest(BaseModel):
    """Schema representing image search input parameters."""

    topic: str = Field(..., min_length=1, description="Topic keyword to search diagram for.")
    description: Optional[str] = Field(None, description="Detailed syllabus topic description.")
    course_id: Optional[uuid.UUID] = Field(None, description="Optional Course UUID mapping.")
    topic_id: Optional[uuid.UUID] = Field(None, description="Optional Topic UUID mapping.")


class ImageRead(BaseModel):
    """Schema representing retrieved image details."""

    id: uuid.UUID
    course_id: Optional[uuid.UUID]
    topic_id: Optional[uuid.UUID]
    image_url: str
    provider: str
    license: str
    ranking_score: float
    image_metadata: dict
    retrieved_at: datetime

    class Config:
        from_attributes = True


class ImageValidationRequest(BaseModel):
    """Schema representing image candidate verification details."""

    image_url: str = Field(..., description="Target image file URL.")
    width: int = Field(..., ge=0, description="Image width resolution.")
    height: int = Field(..., ge=0, description="Image height resolution.")
    license: str = Field(..., description="Copyleft/copyright license descriptor.")
    title: Optional[str] = Field(None, description="Candidate image title.")
    description: Optional[str] = Field(None, description="Candidate description text.")


class ImageValidationResponse(BaseModel):
    """Schema representing validation outputs."""

    success: bool
    message: str
    normalized_license: Optional[str] = None
