"""
Assignment Database Model.
"""

import uuid
from sqlalchemy import ForeignKey, String, Text, JSON, Integer
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base, TimestampMixin


class Assignment(Base, TimestampMixin):
    """
    Represents a generated assignment or learning activity.
    """

    __tablename__ = "assignments"

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
    marks: Mapped[int] = mapped_column(Integer, nullable=False, default=100)
    difficulty: Mapped[str] = mapped_column(String(50), nullable=False)
    bloom_level: Mapped[str] = mapped_column(String(50), nullable=False)
    prompt_version: Mapped[str] = mapped_column(String(100), nullable=False)
    model_version: Mapped[str] = mapped_column(String(100), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    rubric: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
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
        return f"<Assignment id={self.id} type={self.generator_type!r} marks={self.marks}>"
