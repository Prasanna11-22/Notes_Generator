"""
0005 - Chunking.

Creates the chunks and chunk_mappings tables for storing semantic chunks and
curriculum metadata mappings.
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0005"
down_revision: str | None = "0004"
branch_labels: str | tuple[str, ...] | None = None
depends_on: str | tuple[str, ...] | None = None


def upgrade() -> None:
    # ── chunks ───────────────────────────────────────────────────────────────
    op.create_table(
        "chunks",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
            primary_key=True,
        ),
        sa.Column("chunk_hash", sa.String(length=64), nullable=False, unique=True),
        sa.Column("cleaned_text", sa.Text(), nullable=False),
        sa.Column("raw_text", sa.Text(), nullable=False),
        sa.Column("char_count", sa.Integer(), nullable=False),
        sa.Column("word_count", sa.Integer(), nullable=False),
        sa.Column("estimated_reading_time", sa.Float(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index("ix_chunks_id", "chunks", ["id"])
    op.create_index("ix_chunks_chunk_hash", "chunks", ["chunk_hash"])

    # ── chunk_mappings ───────────────────────────────────────────────────────
    op.create_table(
        "chunk_mappings",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
            primary_key=True,
        ),
        sa.Column(
            "chunk_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("chunks.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "resource_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("resources.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "course_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("courses.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "unit_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("units.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "topic_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("topics.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "course_outcome_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("course_outcomes.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("chunk_index", sa.Integer(), nullable=False),
        sa.Column("page_numbers", sa.String(length=50), nullable=False),
        sa.Column("chunk_title", sa.String(length=255), nullable=True),
        sa.Column("bloom_level", sa.String(length=50), nullable=True),
        sa.Column("knowledge_level", sa.String(length=50), nullable=True),
        sa.Column("resource_type", sa.String(length=100), nullable=True),
        sa.Column("chapter_name", sa.String(length=255), nullable=True),
        sa.Column("section_heading", sa.String(length=255), nullable=True),
        sa.Column("subheading", sa.String(length=255), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.UniqueConstraint(
            "resource_id", "chunk_index", name="uq_resource_chunk_index"
        ),
    )
    op.create_index("ix_chunk_mappings_id", "chunk_mappings", ["id"])
    op.create_index("ix_chunk_mappings_chunk_id", "chunk_mappings", ["chunk_id"])
    op.create_index("ix_chunk_mappings_resource_id", "chunk_mappings", ["resource_id"])
    op.create_index("ix_chunk_mappings_course_id", "chunk_mappings", ["course_id"])
    op.create_index("ix_chunk_mappings_unit_id", "chunk_mappings", ["unit_id"])
    op.create_index("ix_chunk_mappings_topic_id", "chunk_mappings", ["topic_id"])
    op.create_index(
        "ix_chunk_mappings_course_outcome_id",
        "chunk_mappings",
        ["course_outcome_id"],
    )
    op.create_index("ix_chunk_mappings_chunk_index", "chunk_mappings", ["chunk_index"])


    # ── document_chunking_jobs ───────────────────────────────────────────────
    op.create_table(
        "document_chunking_jobs",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
            primary_key=True,
        ),
        sa.Column(
            "resource_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("resources.id", ondelete="CASCADE"),
            nullable=False,
            unique=True,
        ),
        sa.Column("status", sa.String(50), nullable=False, server_default="pending"),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("chunks_count", sa.Integer(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index(
        "ix_document_chunking_jobs_id", "document_chunking_jobs", ["id"]
    )
    op.create_index(
        "ix_document_chunking_jobs_resource_id",
        "document_chunking_jobs",
        ["resource_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_document_chunking_jobs_resource_id", table_name="document_chunking_jobs"
    )
    op.drop_index("ix_document_chunking_jobs_id", table_name="document_chunking_jobs")
    op.drop_table("document_chunking_jobs")

    op.drop_index("ix_chunk_mappings_chunk_index", table_name="chunk_mappings")
    op.drop_index("ix_chunk_mappings_course_outcome_id", table_name="chunk_mappings")
    op.drop_index("ix_chunk_mappings_topic_id", table_name="chunk_mappings")
    op.drop_index("ix_chunk_mappings_unit_id", table_name="chunk_mappings")
    op.drop_index("ix_chunk_mappings_course_id", table_name="chunk_mappings")
    op.drop_index("ix_chunk_mappings_resource_id", table_name="chunk_mappings")
    op.drop_index("ix_chunk_mappings_chunk_id", table_name="chunk_mappings")
    op.drop_index("ix_chunk_mappings_id", table_name="chunk_mappings")
    op.drop_table("chunk_mappings")

    op.drop_index("ix_chunks_chunk_hash", table_name="chunks")
    op.drop_index("ix_chunks_id", table_name="chunks")
    op.drop_table("chunks")
