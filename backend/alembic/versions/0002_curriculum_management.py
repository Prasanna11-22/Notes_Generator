"""
0002 - Curriculum Management.

Creates all tables for Curriculum Management Module:
- bloom_levels (lookup, seeded)
- knowledge_levels (lookup, seeded)
- departments
- programs
- semesters
- courses
- units
- topics
- course_outcomes
- topic_mappings
"""

import uuid
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0002"
down_revision: str | None = "0001"
branch_labels: str | tuple[str, ...] | None = None
depends_on: str | tuple[str, ...] | None = None


def upgrade() -> None:
    # ── bloom_levels ──────────────────────────────────────────────────────────
    op.create_table(
        "bloom_levels",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False, primary_key=True),
        sa.Column("name", sa.String(50), nullable=False, unique=True),
    )
    op.create_index("ix_bloom_levels_id", "bloom_levels", ["id"])

    # ── knowledge_levels ───────────────────────────────────────────────────────
    op.create_table(
        "knowledge_levels",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False, primary_key=True),
        sa.Column("name", sa.String(50), nullable=False, unique=True),
    )
    op.create_index("ix_knowledge_levels_id", "knowledge_levels", ["id"])

    # Seed lookup values
    bloom_table = sa.table("bloom_levels", sa.column("id"), sa.column("name"))
    op.bulk_insert(
        bloom_table,
        [
            {"id": uuid.uuid4(), "name": "Remember"},
            {"id": uuid.uuid4(), "name": "Understand"},
            {"id": uuid.uuid4(), "name": "Apply"},
            {"id": uuid.uuid4(), "name": "Analyze"},
            {"id": uuid.uuid4(), "name": "Evaluate"},
            {"id": uuid.uuid4(), "name": "Create"},
        ],
    )

    knowledge_table = sa.table("knowledge_levels", sa.column("id"), sa.column("name"))
    op.bulk_insert(
        knowledge_table,
        [
            {"id": uuid.uuid4(), "name": "Factual"},
            {"id": uuid.uuid4(), "name": "Conceptual"},
            {"id": uuid.uuid4(), "name": "Procedural"},
            {"id": uuid.uuid4(), "name": "Metacognitive"},
        ],
    )

    # ── departments ───────────────────────────────────────────────────────────
    op.create_table(
        "departments",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False, primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("code", sa.String(50), nullable=False, unique=True),
        sa.Column("description", sa.String(1000), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_departments_id", "departments", ["id"])
    op.create_index("ix_departments_code", "departments", ["code"], unique=True)

    # ── programs ──────────────────────────────────────────────────────────────
    op.create_table(
        "programs",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False, primary_key=True),
        sa.Column("department_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("duration_years", sa.Integer(), nullable=False, server_default="4"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["department_id"], ["departments.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_programs_id", "programs", ["id"])

    # ── semesters ─────────────────────────────────────────────────────────────
    op.create_table(
        "semesters",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False, primary_key=True),
        sa.Column("program_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("number", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["program_id"], ["programs.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("program_id", "number", name="uq_program_semester_number"),
    )
    op.create_index("ix_semesters_id", "semesters", ["id"])

    # ── courses ───────────────────────────────────────────────────────────────
    op.create_table(
        "courses",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False, primary_key=True),
        sa.Column("semester_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("course_code", sa.String(50), nullable=False, unique=True),
        sa.Column("course_title", sa.String(255), nullable=False),
        sa.Column("credits", sa.Integer(), nullable=False, server_default="3"),
        sa.Column("description", sa.String(2000), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["semester_id"], ["semesters.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_courses_id", "courses", ["id"])
    op.create_index("ix_courses_course_code", "courses", ["course_code"], unique=True)

    # ── units ─────────────────────────────────────────────────────────────────
    op.create_table(
        "units",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False, primary_key=True),
        sa.Column("course_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("unit_number", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["course_id"], ["courses.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("course_id", "unit_number", name="uq_course_unit_number"),
        sa.UniqueConstraint("course_id", "title", name="uq_course_unit_title"),
    )
    op.create_index("ix_units_id", "units", ["id"])

    # ── topics ────────────────────────────────────────────────────────────────
    op.create_table(
        "topics",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False, primary_key=True),
        sa.Column("unit_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("topic_name", sa.String(255), nullable=False),
        sa.Column("description", sa.String(1000), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["unit_id"], ["units.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("unit_id", "topic_name", name="uq_unit_topic_name"),
    )
    op.create_index("ix_topics_id", "topics", ["id"])

    # ── course_outcomes ───────────────────────────────────────────────────────
    op.create_table(
        "course_outcomes",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False, primary_key=True),
        sa.Column("course_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("co_number", sa.Integer(), nullable=False),
        sa.Column("description", sa.String(1000), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["course_id"], ["courses.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("course_id", "co_number", name="uq_course_co_number"),
    )
    op.create_index("ix_course_outcomes_id", "course_outcomes", ["id"])

    # ── topic_mappings ────────────────────────────────────────────────────────
    op.create_table(
        "topic_mappings",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False, primary_key=True),
        sa.Column("topic_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("bloom_level_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("knowledge_level_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("course_outcome_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["topic_id"], ["topics.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["bloom_level_id"], ["bloom_levels.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["knowledge_level_id"], ["knowledge_levels.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["course_outcome_id"], ["course_outcomes.id"], ondelete="SET NULL"),
    )
    op.create_index("ix_topic_mappings_id", "topic_mappings", ["id"])


def downgrade() -> None:
    op.drop_index("ix_topic_mappings_id", table_name="topic_mappings")
    op.drop_table("topic_mappings")
    op.drop_index("ix_course_outcomes_id", table_name="course_outcomes")
    op.drop_table("course_outcomes")
    op.drop_index("ix_topics_id", table_name="topics")
    op.drop_table("topics")
    op.drop_index("ix_units_id", table_name="units")
    op.drop_table("units")
    op.drop_index("ix_courses_course_code", table_name="courses")
    op.drop_index("ix_courses_id", table_name="courses")
    op.drop_table("courses")
    op.drop_index("ix_semesters_id", table_name="semesters")
    op.drop_table("semesters")
    op.drop_index("ix_programs_id", table_name="programs")
    op.drop_table("programs")
    op.drop_index("ix_departments_code", table_name="departments")
    op.drop_index("ix_departments_id", table_name="departments")
    op.drop_table("departments")
    op.drop_index("ix_knowledge_levels_id", table_name="knowledge_levels")
    op.drop_table("knowledge_levels")
    op.drop_index("ix_bloom_levels_id", table_name="bloom_levels")
    op.drop_table("bloom_levels")
