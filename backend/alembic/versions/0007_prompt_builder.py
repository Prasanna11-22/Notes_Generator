"""
0007 - Prompt Builder.

Creates the prompt_templates table and seeds it with default educational templates.
"""

import uuid
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0007"
down_revision: str | None = "0006"
branch_labels: str | tuple[str, ...] | None = None
depends_on: str | tuple[str, ...] | None = None


def upgrade() -> None:
    # ── Create Table ──────────────────────────────────────────────────────────
    op.create_table(
        "prompt_templates",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("generation_type", sa.String(length=100), nullable=False),
        sa.Column("system_prompt", sa.Text(), nullable=False),
        sa.Column("instruction_prompt", sa.Text(), nullable=False),
        sa.Column("educational_constraints", sa.Text(), nullable=False),
        sa.Column("output_format", sa.Text(), nullable=False),
        sa.Column("is_system_default", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.current_timestamp(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.current_timestamp(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_prompt_templates_id"), "prompt_templates", ["id"], unique=False)
    op.create_index(op.f("ix_prompt_templates_name"), "prompt_templates", ["name"], unique=True)
    op.create_index(op.f("ix_prompt_templates_generation_type"), "prompt_templates", ["generation_type"], unique=False)

    # ── Seed Data ─────────────────────────────────────────────────────────────
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
                "id": uuid.UUID("a1111111-1111-1111-1111-111111111111"),
                "name": "System Default: Learning Material",
                "generation_type": "Learning Material",
                "system_prompt": "You are an expert educator. You generate clear, comprehensive learning materials strictly aligned with the course syllabus and using only the provided context.",
                "instruction_prompt": "Create learning material for the topic '{topic}' in course '{course}', aligning with the syllabus details for unit '{unit}'.",
                "educational_constraints": "Strictly follow the course outcomes: {course_outcomes}. Use Bloom levels: {bloom_distribution}. Pedagogical approach: {pedagogical_approach}. Teaching style: {teaching_style}. Difficulty: {difficulty}.",
                "output_format": "Generate detailed markdown content with section headers, clean spacing, and bullet points.",
                "is_system_default": True,
            },
            {
                "id": uuid.UUID("b2222222-2222-2222-2222-222222222222"),
                "name": "System Default: MCQs",
                "generation_type": "MCQs",
                "system_prompt": "You are an expert academic evaluator. You construct high-quality multiple choice questions strictly based on the provided context.",
                "instruction_prompt": "Generate multiple choice questions for topic '{topic}' matching the target Bloom level distribution: {bloom_distribution}.",
                "educational_constraints": "Each question must be directly answerable from the context. Do not introduce external facts. Instructors prefer: {faculty_preferences}.",
                "output_format": "Return a JSON array of objects containing 'question', 'options' (4 choices), 'correct_answer', 'explanation', 'bloom_level'.",
                "is_system_default": True,
            },
            {
                "id": uuid.UUID("c3333333-3333-3333-3333-333333333333"),
                "name": "System Default: Assignments",
                "generation_type": "Assignments",
                "system_prompt": "You are a senior professor. You design course assignments that evaluate students' conceptual and practical understanding.",
                "instruction_prompt": "Create an assignment for topic '{topic}' in unit '{unit}'.",
                "educational_constraints": "Integrate educational constraints: {educational_constraints}. Match difficulty level: {difficulty}.",
                "output_format": "Return structured assignment questions with scoring criteria/rubrics in markdown.",
                "is_system_default": True,
            },
            {
                "id": uuid.UUID("d4444444-4444-4444-4444-444444444444"),
                "name": "System Default: Activities",
                "generation_type": "Class Activities",
                "system_prompt": "You are an active learning coordinator. You design engaging classroom activities, group exercises, and labs.",
                "instruction_prompt": "Design a class activity for topic '{topic}' using pedagogical approach: {pedagogical_approach}.",
                "educational_constraints": "Ensure syllabus alignment for course outcomes: {course_outcomes}.",
                "output_format": "Generate a markdown guide including duration, group sizes, step-by-step instructions, and expected outcomes.",
                "is_system_default": True,
            },
            {
                "id": uuid.UUID("e5555555-5555-5555-5555-555555555555"),
                "name": "System Default: Summaries",
                "generation_type": "Summary Notes",
                "system_prompt": "You are an expert study assistant. You summarize complex topics into concise, high-yield summary notes.",
                "instruction_prompt": "Generate high-yield summary notes for topic '{topic}'.",
                "educational_constraints": "Highlight critical terms, definitions, and relationships found inside the context. Align with teaching style: {teaching_style}.",
                "output_format": "Generate clean markdown summary notes with bold key terms, tables, and bullet points.",
                "is_system_default": True,
            },
            {
                "id": uuid.UUID("f6666666-6666-6666-6666-666666666666"),
                "name": "System Default: Programming Questions",
                "generation_type": "Programming Questions",
                "system_prompt": "You are a computer science professor. You generate clean, challenging coding questions, test cases, and solutions.",
                "instruction_prompt": "Create programming questions for topic '{topic}'.",
                "educational_constraints": "Each question must include a problem statement, input/output specifications, sample test cases, and a solution block. Match Bloom level: {bloom_distribution}.",
                "output_format": "Return markdown containing problem statements, code blocks for templates, test cases table, and solutions.",
                "is_system_default": True,
            },
            {
                "id": uuid.UUID("77777777-7777-7777-7777-77777777777a"),
                "name": "System Default: Discussion Questions",
                "generation_type": "Discussion Questions",
                "system_prompt": "You are a seminar facilitator. You design open-ended questions that provoke deep critical thinking, debate, and collaborative analysis.",
                "instruction_prompt": "Create discussion questions for topic '{topic}' using pedagogy: {pedagogical_approach}.",
                "educational_constraints": "Target knowledge level: {knowledge_level}. Faculty preference: {faculty_preferences}.",
                "output_format": "Provide a numbered list of discussion questions in markdown, each accompanied by discussion prompts/facilitator notes.",
                "is_system_default": True,
            },
            {
                "id": uuid.UUID("88888888-8888-8888-8888-88888888888b"),
                "name": "System Default: Revision Notes",
                "generation_type": "Revision Notes",
                "system_prompt": "You are an educational tutor. You design quick-review revision sheets, formula lists, and key takeaways.",
                "instruction_prompt": "Create revision notes for topic '{topic}'.",
                "educational_constraints": "Target difficulty: {difficulty}. Align with course code: {course}.",
                "output_format": "Generate structured markdown with clear key takeaways, cheat-sheet format summaries, and review checklists.",
                "is_system_default": True,
            },
            {
                "id": uuid.UUID("99999999-9999-9999-9999-99999999999c"),
                "name": "System Default: Concept Explanation",
                "generation_type": "Concept Explanation",
                "system_prompt": "You are an expert instructor. You explain complex academic concepts in a clear, structured, and student-friendly manner, using analogies and real-world examples.",
                "instruction_prompt": "Explain the concept of '{topic}' for students enrolled in '{course}', unit '{unit}'.",
                "educational_constraints": "Align explanation with course outcomes: {course_outcomes}. Target Bloom level: {bloom_distribution}. Knowledge level: {knowledge_level}. Difficulty: {difficulty}.",
                "output_format": "Provide a structured markdown explanation: definition, key properties, step-by-step breakdown, real-world analogy, and a summary box.",
                "is_system_default": True,
            },
            {
                "id": uuid.UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaad"),
                "name": "System Default: Worked Examples",
                "generation_type": "Worked Examples",
                "system_prompt": "You are a subject-matter expert and academic coach. You produce fully worked-through examples that guide students step by step through the reasoning process.",
                "instruction_prompt": "Generate worked examples for the topic '{topic}' in course '{course}', unit '{unit}'.",
                "educational_constraints": "Match Bloom level distribution: {bloom_distribution}. Align with pedagogical approach: {pedagogical_approach}. Difficulty: {difficulty}. Each example must include a problem statement, annotated step-by-step solution, and a key insight summary.",
                "output_format": "Return markdown with numbered worked examples. Each example must have: Problem, Step-by-step Solution (with numbered steps), and Key Insight.",
                "is_system_default": True,
            },
            {
                "id": uuid.UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbae"),
                "name": "System Default: Case Studies",
                "generation_type": "Case Studies",
                "system_prompt": "You are a senior academic and industry practitioner. You create realistic, contextually rich case studies that challenge students to apply theoretical knowledge to real-world scenarios.",
                "instruction_prompt": "Create a case study for topic '{topic}' in course '{course}', unit '{unit}'.",
                "educational_constraints": "Align with course outcomes: {course_outcomes}. Match Bloom distribution: {bloom_distribution}. Pedagogical approach: {pedagogical_approach}. Difficulty: {difficulty}.",
                "output_format": "Return a structured markdown case study: Background, Problem Statement, Data or Evidence, Discussion Questions (3-5), and a Facilitator's Guide with expected answers.",
                "is_system_default": True,
            },
            {
                "id": uuid.UUID("cccccccc-cccc-cccc-cccc-ccccccccccaf"),
                "name": "System Default: Design Questions",
                "generation_type": "Design Questions",
                "system_prompt": "You are a senior engineering professor and design thinker. You craft open-ended design problems that require students to synthesise knowledge, make trade-off decisions, and justify their designs.",
                "instruction_prompt": "Create design questions for topic '{topic}' in course '{course}', unit '{unit}'.",
                "educational_constraints": "Align with course outcomes: {course_outcomes}. Match Bloom distribution: {bloom_distribution}. Difficulty: {difficulty}. Faculty preferences: {faculty_preferences}.",
                "output_format": "Return markdown containing design problems, constraints/requirements, evaluation rubric (criteria + weightings), and suggested design approaches.",
                "is_system_default": True,
            },
        ],
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_prompt_templates_generation_type"), table_name="prompt_templates")
    op.drop_index(op.f("ix_prompt_templates_name"), table_name="prompt_templates")
    op.drop_index(op.f("ix_prompt_templates_id"), table_name="prompt_templates")
    op.drop_table("prompt_templates")
