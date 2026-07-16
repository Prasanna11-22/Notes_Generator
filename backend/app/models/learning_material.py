"""
Learning Material Database Models.
"""

import uuid
from datetime import datetime
from sqlalchemy import ForeignKey, String, Text, DateTime, JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base, TimestampMixin


class LearningMaterial(Base, TimestampMixin):
    """
    Represents generated academic learning material.
    
    Stores the final validated text output, generation parameters,
    and revision history.
    """

    __tablename__ = "learning_materials"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True
    )
    course_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("courses.id", ondelete="CASCADE"), nullable=False
    )
    topic_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("topics.id", ondelete="CASCADE"), nullable=False
    )
    generator_type: Mapped[str] = mapped_column(String(100), nullable=False)
    prompt_version: Mapped[str] = mapped_column(String(100), nullable=False)
    model: Mapped[str] = mapped_column(String(100), nullable=False)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="completed")
    content: Mapped[str] = mapped_column(Text, nullable=False)
    format: Mapped[str] = mapped_column(String(20), nullable=False, default="markdown")
    created_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    history: Mapped[list[dict]] = mapped_column(
        JSON, nullable=False, default=list, server_default="{}"
    )

    # Relationships
    course = relationship("Course")
    topic = relationship("Topic")
    author = relationship("User")

    def __repr__(self) -> str:
        return f"<LearningMaterial id={self.id} type={self.generator_type!r} topic_id={self.topic_id}>"


class LearningMaterialCache(Base):
    """
    Represents database-backed persistent cache for generated learning materials.
    """

    __tablename__ = "learning_material_caches"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True
    )
    cache_key: Mapped[str] = mapped_column(
        String(255), unique=True, nullable=False, index=True
    )
    content: Mapped[str] = mapped_column(Text, nullable=False)
    format: Mapped[str] = mapped_column(String(20), nullable=False, default="markdown")
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.utcnow
    )

    def __repr__(self) -> str:
        return f"<LearningMaterialCache key={self.cache_key!r}>"
