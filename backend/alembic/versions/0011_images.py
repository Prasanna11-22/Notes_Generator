"""
0011 - Images.

Creates images table.
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0011"
down_revision: str | None = "0010"
branch_labels: str | tuple[str, ...] | None = None
depends_on: str | tuple[str, ...] | None = None


def upgrade() -> None:
    # ── Create images Table ───────────────────────────────────────────────
    op.create_table(
        "images",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("course_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("topic_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("image_url", sa.String(length=1000), nullable=False),
        sa.Column("provider", sa.String(length=100), nullable=False),
        sa.Column("license", sa.String(length=100), nullable=False),
        sa.Column("ranking_score", sa.Float(), nullable=False),
        sa.Column("image_metadata", sa.JSON(), nullable=False),
        sa.Column("retrieved_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["course_id"], ["courses.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["topic_id"], ["topics.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("image_url"),
    )
    op.create_index(op.f("ix_images_id"), "images", ["id"], unique=False)
    op.create_index(op.f("ix_images_course_id"), "images", ["course_id"], unique=False)
    op.create_index(op.f("ix_images_topic_id"), "images", ["topic_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_images_topic_id"), table_name="images")
    op.drop_index(op.f("ix_images_course_id"), table_name="images")
    op.drop_index(op.f("ix_images_id"), table_name="images")
    op.drop_table("images")
