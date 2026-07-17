"""
Educational Image Database Model.
"""

import uuid
from datetime import datetime
from sqlalchemy import ForeignKey, String, Float, DateTime, JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base


class Image(Base):
    """
    Represents retrieved educational diagrams and illustrations.
    """

    __tablename__ = "images"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True
    )
    course_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("courses.id", ondelete="SET NULL"), nullable=True
    )
    topic_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("topics.id", ondelete="SET NULL"), nullable=True
    )
    image_url: Mapped[str] = mapped_column(String(1000), unique=True, nullable=False)
    provider: Mapped[str] = mapped_column(String(100), nullable=False)
    license: Mapped[str] = mapped_column(String(100), nullable=False)
    ranking_score: Mapped[float] = mapped_column(Float, nullable=False)
    image_metadata: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    retrieved_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.utcnow
    )

    # Relationships
    course = relationship("Course")
    topic = relationship("Topic")

    def __repr__(self) -> str:
        return f"<Image id={self.id} url={self.image_url!r} score={self.ranking_score}>"
