"""
Academic Quality Report and Faculty Preference Models.
"""

import uuid
from datetime import datetime
from sqlalchemy import ForeignKey, String, Float, DateTime, Integer, JSON, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base


class QualityReport(Base):
    """
    ORM model storing academic validation audit details for generated resources.
    """

    __tablename__ = "quality_reports"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True
    )
    content_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True, index=True
    )
    content_type: Mapped[str | None] = mapped_column(String(50), nullable=True, index=True)
    quality_score: Mapped[float] = mapped_column(Float, nullable=False)
    confidence_score: Mapped[float] = mapped_column(Float, nullable=False)
    validation_details: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    validation_timestamp: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.utcnow
    )

    def __repr__(self) -> str:
        return f"<QualityReport id={self.id} score={self.quality_score} confidence={self.confidence_score}>"


class FacultyPreference(Base):
    """
    ORM model containing stored reuse profiles for individual faculty preferences.
    """

    __tablename__ = "faculty_preferences"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True
    )
    faculty_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False
    )
    teaching_style: Mapped[str] = mapped_column(String(100), nullable=False)
    difficulty: Mapped[str] = mapped_column(String(50), nullable=False)
    examples: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    content_length: Mapped[int] = mapped_column(Integer, nullable=False, default=1000)
    formatting_preferences: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    # Relationships
    faculty = relationship("User")

    def __repr__(self) -> str:
        return f"<FacultyPreference id={self.id} faculty_id={self.faculty_id} style={self.teaching_style!r}>"
