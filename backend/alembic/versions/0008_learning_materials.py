"""
0008 - Learning Materials and Caches.

Creates learning_materials and learning_material_caches tables.
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0008"
down_revision: str | None = "0007"
branch_labels: str | tuple[str, ...] | None = None
depends_on: str | tuple[str, ...] | None = None


def upgrade() -> None:
    # ── Create learning_materials Table ───────────────────────────────────────
    op.create_table(
        "learning_materials",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("course_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("topic_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("generator_type", sa.String(length=100), nullable=False),
        sa.Column("prompt_version", sa.String(length=100), nullable=False),
        sa.Column("model", sa.String(length=100), nullable=False),
        sa.Column("status", sa.String(length=50), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("format", sa.String(length=20), nullable=False),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("history", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["course_id"], ["courses.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["topic_id"], ["topics.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_learning_materials_id"), "learning_materials", ["id"], unique=False)
    op.create_index(op.f("ix_learning_materials_course_id"), "learning_materials", ["course_id"], unique=False)
    op.create_index(op.f("ix_learning_materials_topic_id"), "learning_materials", ["topic_id"], unique=False)

    # ── Create learning_material_caches Table ─────────────────────────────────
    op.create_table(
        "learning_material_caches",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("cache_key", sa.String(length=255), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("format", sa.String(length=20), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_learning_material_caches_id"), "learning_material_caches", ["id"], unique=False)
    op.create_index(op.f("ix_learning_material_caches_cache_key"), "learning_material_caches", ["cache_key"], unique=True)

    # ── Seed Additional Prompt Templates ──────────────────────────────────────
    import uuid
    prompt_templates_table = sa.table(
        "prompt_templates",
        sa.column("id", postgresql.UUID(as_uuid=True)),
        sa.column("name", sa.String),
        sa.column("generation_type", sa.String),
        sa.column("system_prompt", sa.String),
        sa.column("instruction_prompt", sa.String),
        sa.column("educational_constraints", sa.String),
        sa.column("output_format", sa.String),
        sa.column("is_system_default", sa.Boolean),
    )

    op.bulk_insert(
        prompt_templates_table,
        [
            {
                "id": uuid.UUID("a1111111-1111-1111-1111-111111111129"),
                "name": "System Default: Learning Objectives",
                "generation_type": "Learning Objectives",
                "system_prompt": "You are an expert curriculum designer. You write clear, measurable learning objectives based on Bloom's taxonomy.",
                "instruction_prompt": "Generate learning objectives for topic '{topic}' in course '{course}', unit '{unit}'.",
                "educational_constraints": "Align with course outcomes: {course_outcomes}. Bloom level: {bloom_distribution}. Pedagogical approach: {pedagogical_approach}.",
                "output_format": "Return markdown listing 3-5 bulleted learning objectives using active verbs.",
                "is_system_default": True,
            },
            {
                "id": uuid.UUID("a1111111-1111-1111-1111-111111111130"),
                "name": "System Default: Key Takeaways",
                "generation_type": "Key Takeaways",
                "system_prompt": "You are an expert study supervisor. You summarize the core insights and essential takeaways of academic topics.",
                "instruction_prompt": "Generate key takeaways for topic '{topic}' in course '{course}', unit '{unit}'.",
                "educational_constraints": "Align with Bloom level: {bloom_distribution}. Difficulty: {difficulty}.",
                "output_format": "Return markdown listing 3-5 bulleted key takeaways with brief explanations.",
                "is_system_default": True,
            },
            {
                "id": uuid.UUID("a1111111-1111-1111-1111-111111111131"),
                "name": "System Default: Common Mistakes",
                "generation_type": "Common Mistakes",
                "system_prompt": "You are an experienced academic instructor. You identify common misconceptions, mistakes, and pitfalls that students encounter.",
                "instruction_prompt": "Identify common mistakes and misconceptions for topic '{topic}' in course '{course}', unit '{unit}'.",
                "educational_constraints": "Match knowledge level: {knowledge_level}. Faculty preference details: {faculty_preferences}.",
                "output_format": "Return markdown containing a list of common mistakes, why students make them, and how to avoid or correct them.",
                "is_system_default": True,
            },
            {
                "id": uuid.UUID("a1111111-1111-1111-1111-111111111132"),
                "name": "System Default: Real-world Applications",
                "generation_type": "Real-world Applications",
                "system_prompt": "You are an industry expert and professor. You explain how theoretical concepts are applied in industry and real-world scenarios.",
                "instruction_prompt": "Generate real-world applications for topic '{topic}' in course '{course}', unit '{unit}'.",
                "educational_constraints": "Align with pedagogical approach: {pedagogical_approach}. Teaching style: {teaching_style}.",
                "output_format": "Return markdown with 2-3 case examples or applications showing the concept in action.",
                "is_system_default": True,
            },
        ],
    )


def downgrade() -> None:
    # Delete seeded templates
    op.execute(
        "DELETE FROM prompt_templates WHERE id IN ("
        "'a1111111-1111-1111-1111-111111111129',"
        "'a1111111-1111-1111-1111-111111111130',"
        "'a1111111-1111-1111-1111-111111111131',"
        "'a1111111-1111-1111-1111-111111111132'"
        ")"
    )

    op.drop_index(op.f("ix_learning_material_caches_cache_key"), table_name="learning_material_caches")
    op.drop_index(op.f("ix_learning_material_caches_id"), table_name="learning_material_caches")
    op.drop_table("learning_material_caches")

    op.drop_index(op.f("ix_learning_materials_topic_id"), table_name="learning_materials")
    op.drop_index(op.f("ix_learning_materials_course_id"), table_name="learning_materials")
    op.drop_index(op.f("ix_learning_materials_id"), table_name="learning_materials")
    op.drop_table("learning_materials")
