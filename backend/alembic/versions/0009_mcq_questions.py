"""
0009 - MCQ Questions.

Creates mcq_questions table.
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0009"
down_revision: str | None = "0008"
branch_labels: str | tuple[str, ...] | None = None
depends_on: str | tuple[str, ...] | None = None


def upgrade() -> None:
    # ── Create mcq_questions Table ───────────────────────────────────────
    op.create_table(
        "mcq_questions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("course_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("topic_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("question_text", sa.Text(), nullable=False),
        sa.Column("options", sa.JSON(), nullable=False),
        sa.Column("correct_answer", sa.String(length=50), nullable=False),
        sa.Column("explanation", sa.Text(), nullable=False),
        sa.Column("bloom_level", sa.String(length=50), nullable=False),
        sa.Column("difficulty", sa.String(length=50), nullable=False),
        sa.Column("prompt_version", sa.String(length=100), nullable=False),
        sa.Column("model_version", sa.String(length=100), nullable=False),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("history", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["course_id"], ["courses.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["topic_id"], ["topics.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_mcq_questions_id"), "mcq_questions", ["id"], unique=False)
    op.create_index(op.f("ix_mcq_questions_course_id"), "mcq_questions", ["course_id"], unique=False)
    op.create_index(op.f("ix_mcq_questions_topic_id"), "mcq_questions", ["topic_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_mcq_questions_topic_id"), table_name="mcq_questions")
    op.drop_index(op.f("ix_mcq_questions_course_id"), table_name="mcq_questions")
    op.drop_index(op.f("ix_mcq_questions_id"), table_name="mcq_questions")
    op.drop_table("mcq_questions")
