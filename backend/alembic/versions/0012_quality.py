"""
0012 - Quality.

Creates quality_reports and faculty_preferences tables.
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0012"
down_revision: str | None = "0011"
branch_labels: str | tuple[str, ...] | None = None
depends_on: str | tuple[str, ...] | None = None


def upgrade() -> None:
    # ── Create quality_reports Table ──────────────────────────────────────
    op.create_table(
        "quality_reports",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("content_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("content_type", sa.String(length=50), nullable=True),
        sa.Column("quality_score", sa.Float(), nullable=False),
        sa.Column("confidence_score", sa.Float(), nullable=False),
        sa.Column("validation_details", sa.JSON(), nullable=False),
        sa.Column("validation_timestamp", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_quality_reports_id"), "quality_reports", ["id"], unique=False)
    op.create_index(
        op.f("ix_quality_reports_content_id"), "quality_reports", ["content_id"], unique=False
    )
    op.create_index(
        op.f("ix_quality_reports_content_type"), "quality_reports", ["content_type"], unique=False
    )

    # ── Create faculty_preferences Table ──────────────────────────────────
    op.create_table(
        "faculty_preferences",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("faculty_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("teaching_style", sa.String(length=100), nullable=False),
        sa.Column("difficulty", sa.String(length=50), nullable=False),
        sa.Column("examples", sa.String(length=1000), nullable=True),
        sa.Column("content_length", sa.Integer(), nullable=False),
        sa.Column("formatting_preferences", sa.JSON(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["faculty_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("faculty_id"),
    )
    op.create_index(op.f("ix_faculty_preferences_id"), "faculty_preferences", ["id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_faculty_preferences_id"), table_name="faculty_preferences")
    op.drop_table("faculty_preferences")

    op.drop_index(op.f("ix_quality_reports_content_type"), table_name="quality_reports")
    op.drop_index(op.f("ix_quality_reports_content_id"), table_name="quality_reports")
    op.drop_index(op.f("ix_quality_reports_id"), table_name="quality_reports")
    op.drop_table("quality_reports")
