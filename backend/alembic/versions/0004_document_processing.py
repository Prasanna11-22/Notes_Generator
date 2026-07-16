"""
0004 - Document Processing Pipeline.

Creates:
- ``document_processing``  — per-resource processing job tracker
- ``document_metadata``    — extracted text and document metadata store
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0004"
down_revision: str | None = "0003"
branch_labels: str | tuple[str, ...] | None = None
depends_on: str | tuple[str, ...] | None = None


def upgrade() -> None:
    # ── document_processing ───────────────────────────────────────────────────
    op.create_table(
        "document_processing",
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
        sa.Column(
            "status",
            sa.String(50),
            nullable=False,
            server_default="pending",
        ),
        sa.Column("parser_used", sa.String(100), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("processing_duration_ms", sa.Integer(), nullable=True),
        sa.Column("page_count", sa.Integer(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column(
            "processing_history",
            postgresql.JSON(astext_type=sa.Text()),
            nullable=True,
            server_default="[]",
        ),
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
    op.create_index("ix_document_processing_id", "document_processing", ["id"])
    op.create_index(
        "ix_document_processing_resource_id", "document_processing", ["resource_id"]
    )
    op.create_index(
        "ix_document_processing_status", "document_processing", ["status"]
    )

    # ── document_metadata ─────────────────────────────────────────────────────
    op.create_table(
        "document_metadata",
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
        sa.Column(
            "processing_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("document_processing.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("title", sa.String(500), nullable=True),
        sa.Column("author", sa.String(500), nullable=True),
        sa.Column("page_count", sa.Integer(), nullable=True),
        sa.Column("language", sa.String(20), nullable=True),
        sa.Column("word_count", sa.Integer(), nullable=True),
        sa.Column("char_count", sa.Integer(), nullable=True),
        sa.Column("document_created_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("document_modified_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("raw_text", sa.Text(), nullable=True),
        sa.Column("cleaned_text", sa.Text(), nullable=True),
        sa.Column(
            "raw_metadata",
            postgresql.JSON(astext_type=sa.Text()),
            nullable=True,
        ),
        sa.Column(
            "is_scanned",
            sa.Boolean(),
            nullable=False,
            server_default="false",
        ),
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
    op.create_index("ix_document_metadata_id", "document_metadata", ["id"])
    op.create_index(
        "ix_document_metadata_resource_id", "document_metadata", ["resource_id"]
    )
    op.create_index(
        "ix_document_metadata_processing_id", "document_metadata", ["processing_id"]
    )
    op.create_index(
        "ix_document_metadata_language", "document_metadata", ["language"]
    )


def downgrade() -> None:
    op.drop_index("ix_document_metadata_language", table_name="document_metadata")
    op.drop_index(
        "ix_document_metadata_processing_id", table_name="document_metadata"
    )
    op.drop_index(
        "ix_document_metadata_resource_id", table_name="document_metadata"
    )
    op.drop_index("ix_document_metadata_id", table_name="document_metadata")
    op.drop_table("document_metadata")

    op.drop_index("ix_document_processing_status", table_name="document_processing")
    op.drop_index(
        "ix_document_processing_resource_id", table_name="document_processing"
    )
    op.drop_index("ix_document_processing_id", table_name="document_processing")
    op.drop_table("document_processing")
