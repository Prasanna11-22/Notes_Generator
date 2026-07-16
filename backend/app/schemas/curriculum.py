"""
Curriculum Management Pydantic v2 Schemas.
"""

import uuid
from datetime import datetime

from pydantic import BaseModel, Field, field_validator


# ── BloomLevel Schemas ────────────────────────────────────────────────────────
class BloomLevelBase(BaseModel):
    name: str = Field(..., max_length=50, examples=["Remember"])


class BloomLevelCreate(BloomLevelBase):
    pass


class BloomLevelRead(BloomLevelBase):
    id: uuid.UUID

    class Config:
        from_attributes = True


# ── KnowledgeLevel Schemas ───────────────────────────────────────────────────
class KnowledgeLevelBase(BaseModel):
    name: str = Field(..., max_length=50, examples=["Factual"])


class KnowledgeLevelCreate(KnowledgeLevelBase):
    pass


class KnowledgeLevelRead(KnowledgeLevelBase):
    id: uuid.UUID

    class Config:
        from_attributes = True


# ── Department Schemas ────────────────────────────────────────────────────────
class DepartmentBase(BaseModel):
    name: str = Field(
        ..., min_length=2, max_length=255, examples=["Computer Science & Engineering"]
    )
    code: str = Field(..., min_length=2, max_length=50, examples=["CSE"])
    description: str | None = Field(default=None, max_length=1000)

    @field_validator("name", "code")
    @classmethod
    def strip_whitespace(cls, v: str) -> str:
        return v.strip()

    @field_validator("code")
    @classmethod
    def uppercase_code(cls, v: str) -> str:
        return v.upper()


class DepartmentCreate(DepartmentBase):
    pass


class DepartmentUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=255)
    code: str | None = Field(default=None, min_length=2, max_length=50)
    description: str | None = Field(default=None, max_length=1000)

    @field_validator("name", "code")
    @classmethod
    def strip_whitespace(cls, v: str | None) -> str | None:
        return v.strip() if v is not None else None

    @field_validator("code")
    @classmethod
    def uppercase_code(cls, v: str | None) -> str | None:
        return v.upper() if v is not None else None


class DepartmentRead(DepartmentBase):
    id: uuid.UUID
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ── Program Schemas ───────────────────────────────────────────────────────────
class ProgramBase(BaseModel):
    department_id: uuid.UUID
    name: str = Field(..., min_length=2, max_length=255, examples=["B.Tech. Computer Science"])
    duration_years: int = Field(default=4, ge=1, le=7, examples=[4])

    @field_validator("name")
    @classmethod
    def strip_name(cls, v: str) -> str:
        return v.strip()


class ProgramCreate(ProgramBase):
    pass


class ProgramUpdate(BaseModel):
    department_id: uuid.UUID | None = None
    name: str | None = Field(default=None, min_length=2, max_length=255)
    duration_years: int | None = Field(default=None, ge=1, le=7)

    @field_validator("name")
    @classmethod
    def strip_name(cls, v: str | None) -> str | None:
        return v.strip() if v is not None else None


class ProgramRead(ProgramBase):
    id: uuid.UUID
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ── Semester Schemas ──────────────────────────────────────────────────────────
class SemesterBase(BaseModel):
    program_id: uuid.UUID
    number: int = Field(..., ge=1, le=14, examples=[1])


class SemesterCreate(SemesterBase):
    pass


class SemesterUpdate(BaseModel):
    program_id: uuid.UUID | None = None
    number: int | None = Field(default=None, ge=1, le=14)


class SemesterRead(SemesterBase):
    id: uuid.UUID
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ── Course Outcome (CO) Schemas ───────────────────────────────────────────────
class CourseOutcomeBase(BaseModel):
    course_id: uuid.UUID
    co_number: int = Field(..., ge=1, le=20, examples=[1])
    description: str = Field(
        ..., min_length=5, max_length=1000, examples=["Understand database normalization rules"]
    )

    @field_validator("description")
    @classmethod
    def strip_desc(cls, v: str) -> str:
        return v.strip()


class CourseOutcomeCreate(CourseOutcomeBase):
    pass


class CourseOutcomeUpdate(BaseModel):
    course_id: uuid.UUID | None = None
    co_number: int | None = Field(default=None, ge=1, le=20)
    description: str | None = Field(default=None, min_length=5, max_length=1000)

    @field_validator("description")
    @classmethod
    def strip_desc(cls, v: str | None) -> str | None:
        return v.strip() if v is not None else None


class CourseOutcomeRead(CourseOutcomeBase):
    id: uuid.UUID
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ── Course Schemas ────────────────────────────────────────────────────────────
class CourseBase(BaseModel):
    semester_id: uuid.UUID
    course_code: str = Field(..., min_length=2, max_length=50, examples=["CS201"])
    course_title: str = Field(
        ..., min_length=2, max_length=255, examples=["Database Management Systems"]
    )
    credits: int = Field(default=3, ge=1, le=6, examples=[3])
    description: str | None = Field(default=None, max_length=2000)

    @field_validator("course_code", "course_title")
    @classmethod
    def strip_whitespace(cls, v: str) -> str:
        return v.strip()

    @field_validator("course_code")
    @classmethod
    def uppercase_code(cls, v: str) -> str:
        return v.upper()


class CourseCreate(CourseBase):
    pass


class CourseUpdate(BaseModel):
    semester_id: uuid.UUID | None = None
    course_code: str | None = Field(default=None, min_length=2, max_length=50)
    course_title: str | None = Field(default=None, min_length=2, max_length=255)
    credits: int | None = Field(default=None, ge=1, le=6)
    description: str | None = Field(default=None, max_length=2000)

    @field_validator("course_code", "course_title")
    @classmethod
    def strip_whitespace(cls, v: str | None) -> str | None:
        return v.strip() if v is not None else None

    @field_validator("course_code")
    @classmethod
    def uppercase_code(cls, v: str | None) -> str | None:
        return v.upper() if v is not None else None


class CourseRead(CourseBase):
    id: uuid.UUID
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ── Unit Schemas ──────────────────────────────────────────────────────────────
class UnitBase(BaseModel):
    course_id: uuid.UUID
    unit_number: int = Field(..., ge=1, le=20, examples=[1])
    title: str = Field(..., min_length=2, max_length=255, examples=["Relational Model and SQL"])

    @field_validator("title")
    @classmethod
    def strip_title(cls, v: str) -> str:
        return v.strip()


class UnitCreate(UnitBase):
    pass


class UnitUpdate(BaseModel):
    course_id: uuid.UUID | None = None
    unit_number: int | None = Field(default=None, ge=1, le=20)
    title: str | None = Field(default=None, min_length=2, max_length=255)

    @field_validator("title")
    @classmethod
    def strip_title(cls, v: str | None) -> str | None:
        return v.strip() if v is not None else None


class UnitRead(UnitBase):
    id: uuid.UUID
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ── Topic Schemas ─────────────────────────────────────────────────────────────
class TopicBase(BaseModel):
    unit_id: uuid.UUID
    topic_name: str = Field(..., min_length=2, max_length=255, examples=["Subqueries and Joins"])
    description: str | None = Field(default=None, max_length=1000)

    @field_validator("topic_name")
    @classmethod
    def strip_name(cls, v: str) -> str:
        return v.strip()


class TopicCreate(TopicBase):
    pass


class TopicUpdate(BaseModel):
    unit_id: uuid.UUID | None = None
    topic_name: str | None = Field(default=None, min_length=2, max_length=255)
    description: str | None = Field(default=None, max_length=1000)

    @field_validator("topic_name")
    @classmethod
    def strip_name(cls, v: str | None) -> str | None:
        return v.strip() if v is not None else None


class TopicRead(TopicBase):
    id: uuid.UUID
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ── TopicMapping Schemas ──────────────────────────────────────────────────────
class TopicMappingBase(BaseModel):
    topic_id: uuid.UUID
    bloom_level_id: uuid.UUID
    knowledge_level_id: uuid.UUID
    course_outcome_id: uuid.UUID | None = Field(default=None)


class TopicMappingCreate(TopicMappingBase):
    pass


class TopicMappingUpdate(BaseModel):
    topic_id: uuid.UUID | None = None
    bloom_level_id: uuid.UUID | None = None
    knowledge_level_id: uuid.UUID | None = None
    course_outcome_id: uuid.UUID | None = None


class TopicMappingRead(TopicMappingBase):
    id: uuid.UUID
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ── Import Feature Schemas ────────────────────────────────────────────────────
class ImportReportItem(BaseModel):
    rows_processed: int
    departments_created: int
    programs_created: int
    courses_created: int
    units_created: int
    topics_created: int
    mappings_created: int
    errors: list[str] = Field(default_factory=list)
