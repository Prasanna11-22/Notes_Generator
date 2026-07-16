"""
Resource ORM model.

Maps to the ``resources`` table in PostgreSQL, representing uploaded documents.
Supports self-referencing lineage mapping for multi-version histories.
"""

import uuid
from enum import StrEnum

from sqlalchemy import Boolean, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base, TimestampMixin


class ResourceType(StrEnum):
    """Supported academic resource types."""

    TEXTBOOK = "Textbook"
    REFERENCE_BOOK = "Reference Book"
    FACULTY_NOTES = "Faculty Notes"
    OTHER = "Other"


class Resource(Base, TimestampMixin):
    """
    Represents an uploaded academic document.

    Supports linear versioning via a self-referencing ``parent_id`` lineage key.
    """

    __tablename__ = "resources"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        index=True,
    )
    course_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("courses.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    uploaded_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    parent_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("resources.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    resource_type: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        default=ResourceType.OTHER.value,
        server_default=ResourceType.OTHER.value,
    )
    file_name: Mapped[str] = mapped_column(String(255), nullable=False)
    original_file_name: Mapped[str] = mapped_column(String(255), nullable=False)
    file_size: Mapped[int] = mapped_column(Integer, nullable=False)
    mime_type: Mapped[str] = mapped_column(String(100), nullable=False)
    storage_path: Mapped[str] = mapped_column(String(500), nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    checksum: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    upload_status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="completed",
        server_default="completed",
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default="true",
    )

    # Relationships
    course = relationship("Course")
    uploader = relationship("User")

    # Self-referencing version history lineage
    versions: Mapped[list["Resource"]] = relationship(
        "Resource",
        back_populates="parent",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    parent: Mapped["Resource | None"] = relationship(
        "Resource",
        back_populates="versions",
        remote_side=[id],
    )

    # Processing pipeline back-reference
    processing_job: Mapped["DocumentProcessing | None"] = relationship(  # type: ignore[name-defined]  # noqa: F821
        "DocumentProcessing",
        back_populates="resource",
        uselist=False,
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    def __repr__(self) -> str:
        return f"<Resource id={self.id} title={self.title!r} version={self.version} status={self.upload_status}>"

