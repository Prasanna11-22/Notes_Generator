"""
PromptTemplate database model for storing LLM prompt generation contexts.
"""

import uuid
from sqlalchemy import Boolean, String, Text, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base, TimestampMixin


class PromptTemplate(Base, TimestampMixin):
    """
    Represents an LLM prompt template context defining instructions,
    educational constraints, and output format formatting specifications.
    """

    __tablename__ = "prompt_templates"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    generation_type: Mapped[str] = mapped_column(String(100), nullable=False, index=True)

    system_prompt: Mapped[str] = mapped_column(Text, nullable=False)
    instruction_prompt: Mapped[str] = mapped_column(Text, nullable=False)
    educational_constraints: Mapped[str] = mapped_column(Text, nullable=False)
    output_format: Mapped[str] = mapped_column(Text, nullable=False)

    is_system_default: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="false"
    )

    def __repr__(self) -> str:
        return f"<PromptTemplate id={self.id} name={self.name!r} type={self.generation_type!r}>"
