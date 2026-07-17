"""
0010 - Assignments.

Creates assignments table.
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0010"
down_revision: str | None = "0009"
branch_labels: str | tuple[str, ...] | None = None
depends_on: str | tuple[str, ...] | None = None


def upgrade() -> None:
    # ── Create assignments Table ──────────────────────────────────────────
    op.create_table(
        "assignments",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("course_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("topic_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("generator_type", sa.String(length=100), nullable=False),
        sa.Column("marks", sa.Integer(), nullable=False, server_default="100"),
        sa.Column("difficulty", sa.String(length=50), nullable=False),
        sa.Column("bloom_level", sa.String(length=50), nullable=False),
        sa.Column("prompt_version", sa.String(length=100), nullable=False),
        sa.Column("model_version", sa.String(length=100), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("rubric", sa.JSON(), nullable=False),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("history", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["course_id"], ["courses.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["topic_id"], ["topics.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_assignments_id"), "assignments", ["id"], unique=False)
    op.create_index(op.f("ix_assignments_course_id"), "assignments", ["course_id"], unique=False)
    op.create_index(op.f("ix_assignments_topic_id"), "assignments", ["topic_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_assignments_topic_id"), table_name="assignments")
    op.drop_index(op.f("ix_assignments_course_id"), table_name="assignments")
    op.drop_index(op.f("ix_assignments_id"), table_name="assignments")
    op.drop_table("assignments")
