"""
User ORM model.

Maps to the ``users`` table in PostgreSQL.  UUID primary key, bcrypt-hashed
password, role-based access control, and automatic timestamps.
"""

import uuid
from enum import StrEnum

from sqlalchemy import Boolean, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base, TimestampMixin


class UserRole(StrEnum):
    """Allowed role values for a User account."""

    ADMIN = "admin"
    FACULTY = "faculty"


class User(Base, TimestampMixin):
    """
    Represents an authenticated system user.

    Attributes:
        id:               UUID v4 primary key.
        full_name:        Display name of the user.
        email:            Unique, lower-cased email address (login identifier).
        hashed_password:  bcrypt-hashed password — never stored in plain text.
        institution:      University / college the user belongs to.
        department:       Academic department (e.g. "Computer Science & Eng.").
        role:             RBAC role — ``admin`` or ``faculty``.
        is_active:        Soft-disable flag; inactive users cannot authenticate.
        created_at:       Set once at INSERT (from ``TimestampMixin``).
        updated_at:       Updated on every UPDATE (from ``TimestampMixin``).
    """

    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        index=True,
    )
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    email: Mapped[str] = mapped_column(
        String(320),
        unique=True,
        nullable=False,
        index=True,
    )
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    institution: Mapped[str | None] = mapped_column(String(255), nullable=True)
    department: Mapped[str | None] = mapped_column(String(255), nullable=True)
    role: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default=UserRole.FACULTY.value,
        server_default=UserRole.FACULTY.value,
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default="true",
    )

    def __repr__(self) -> str:
        return f"<User id={self.id} email={self.email!r} role={self.role!r}>"
