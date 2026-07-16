"""
SQLAlchemy declarative base.

All ORM models must inherit from ``Base``.  The ``TimestampMixin`` provides
``created_at`` / ``updated_at`` columns that are populated automatically.
"""

from datetime import datetime

from sqlalchemy import DateTime, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """Shared declarative base for all SQLAlchemy ORM models."""

    # All tables will be created in the default schema unless overridden.
    pass


class TimestampMixin:
    """
    Mixin that adds ``created_at`` and ``updated_at`` columns.

    - ``created_at`` is set once at INSERT time via the DB server clock.
    - ``updated_at`` is refreshed on every UPDATE.
    """

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
