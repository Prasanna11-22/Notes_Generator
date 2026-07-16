"""
Resource Pydantic v2 Schemas.
"""

import uuid
from datetime import datetime

from pydantic import BaseModel, Field, field_validator

from app.models.resource import ResourceType


class ResourceBase(BaseModel):
    title: str = Field(..., min_length=2, max_length=255, examples=["Course Syllabus"])
    description: str | None = Field(default=None, max_length=1000)
    resource_type: str = Field(
        default=ResourceType.OTHER.value,
        examples=[ResourceType.TEXTBOOK.value],
    )

    @field_validator("title", "resource_type")
    @classmethod
    def strip_whitespace(cls, v: str) -> str:
        return v.strip()


class ResourceUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=2, max_length=255)
    description: str | None = Field(default=None, max_length=1000)
    resource_type: str | None = Field(default=None)

    @field_validator("title", "resource_type")
    @classmethod
    def strip_whitespace(cls, v: str | None) -> str | None:
        return v.strip() if v is not None else None


class ResourceRead(ResourceBase):
    id: uuid.UUID
    course_id: uuid.UUID
    uploaded_by: uuid.UUID | None
    parent_id: uuid.UUID | None
    file_name: str
    original_file_name: str
    file_size: int
    mime_type: str
    storage_path: str
    version: int
    checksum: str
    upload_status: str
    is_active: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
