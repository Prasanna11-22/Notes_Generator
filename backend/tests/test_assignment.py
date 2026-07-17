"""
Unit and Integration Tests for Phase 12 Assignment & Learning Activity Generation Engine.
"""

import json
import uuid
import pytest
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import status
from httpx import AsyncClient

from app.models.curriculum import Course, Topic, CourseOutcome, Department, Program, Semester, Unit
from app.models.assignment import Assignment
from app.services.assignment.factory import GenerationStrategyFactory
from app.services.assignment.validator import AssignmentValidator
from app.services.assignment.rubric import RubricPreparationService
from app.services.assignment.blueprint import AssignmentBlueprintService
from app.services.assignment.service import AssignmentOrchestratorService
from app.models.user import User


# ── 1. Strategy & Factory Tests ──────────────────────────────────────────

class TestAssignmentGeneratorFactory:
    """Tests strategy resolution from the factory."""

    def test_factory_resolves_all_major_types(self):
        types = [
            "Descriptive Questions",
            "Programming Assignments",
            "Case Studies",
            "Problem Solving Questions",
            "Analytical Questions",
            "Design-Based Questions",
            "Mini Projects",
            "Group Activities",
            "Individual Activities",
            "Think-Pair-Share Activities",
            "Collaborative Learning Activities",
            "Inquiry-Based Activities",
            "Learning Activities",
        ]
        for t in types:
            generator = GenerationStrategyFactory.get_generator(t)
            assert generator is not None
            assert callable(generator.get_generator_type)

    def test_factory_invalid_type_raises(self):
        with pytest.raises(ValueError, match="Unsupported generator type"):
            GenerationStrategyFactory.get_generator("Invalid Type")


# ── 2. Assessment Blueprint Tests ─────────────────────────────────────────

class TestAssignmentBlueprint:
    """Tests marks distribution calculation based on Bloom level."""

    def test_blueprint_marks_distribution_remember(self):
        dist = AssignmentBlueprintService.calculate_marks_distribution(50, "Remember")
        assert sum(dist.values()) == 50
        assert "Conceptual Recall & Definition" in dist

    def test_blueprint_marks_distribution_create(self):
        dist = AssignmentBlueprintService.calculate_marks_distribution(100, "Create")
        assert sum(dist.values()) == 100
        assert "Design & Architecture Formulation" in dist

    def test_blueprint_marks_distribution_invalid(self):
        dist = AssignmentBlueprintService.calculate_marks_distribution(30, "Unknown")
        assert sum(dist.values()) == 30
        assert "Part A: Theory & Concept" in dist


# ── 3. Rubric Service Tests ───────────────────────────────────────────────

class TestRubricPreparationService:
    """Tests validation and formatting of grading rubrics."""

    @pytest.fixture
    def valid_rubric(self) -> dict:
        return {
            "assessment_criteria": ["Correct execution", "Code structure"],
            "expected_learning_outcomes": ["Understand async programming"],
            "evaluation_guidelines": "Score out of 10 points.",
            "mark_distribution": {"Part A": 5, "Part B": 5},
            "suggested_solution_outline": ["Use asyncio.gather"],
        }

    def test_validate_rubric_success(self, valid_rubric):
        # Should not raise any exceptions
        RubricPreparationService.validate_rubric_structure(valid_rubric)

    def test_validate_rubric_missing_keys_raises(self, valid_rubric):
        del valid_rubric["assessment_criteria"]
        with pytest.raises(ValueError, match="Rubric is missing required sections"):
            RubricPreparationService.validate_rubric_structure(valid_rubric)

    def test_format_rubric_to_markdown(self, valid_rubric):
        markdown = RubricPreparationService.format_rubric_to_markdown(valid_rubric)
        assert "# Grading Rubric & Evaluation Guide" in markdown
        assert "## Assessment Criteria" in markdown
        assert "## Expected Learning Outcomes" in markdown
        assert "## Evaluation Guidelines" in markdown
        assert "## Mark Distribution" in markdown
        assert "## Suggested Solution Outline" in markdown


# ── 4. Validator Tests ────────────────────────────────────────────────────

class TestAssignmentValidator:
    """Tests pedagogical alignment, topic coverage, and duplicate checks."""

    def test_validate_educational_alignment_success(self):
        content = "Create a new database structure. Solve the problem by designing a database with an inquiry-based standard academic style."
        topic = "Database Designing"
        bloom_level = "Create"
        difficulty = "Medium"
        course_outcomes = ["Understand and design databases."]
        pedagogy = "Inquiry-based"
        style = "Standard Academic"

        # Should pass
        AssignmentValidator.validate_educational_alignment(
            content=content,
            topic=topic,
            bloom_level=bloom_level,
            difficulty=difficulty,
            course_outcomes=course_outcomes,
            pedagogical_approach=pedagogy,
            teaching_style=style,
        )

    def test_validate_educational_alignment_bloom_mismatch_raises(self):
        content = "Recall the definition of a database."
        topic = "Database"
        bloom_level = "Create"  # Target verbs: create, design, construct, build, project

        with pytest.raises(ValueError, match="Bloom taxonomy alignment check failed"):
            AssignmentValidator.validate_educational_alignment(
                content=content,
                topic=topic,
                bloom_level=bloom_level,
                difficulty="Easy",
            )

    def test_validate_educational_alignment_topic_mismatch_raises(self):
        content = "Implement a sorting algorithm using quicksort."
        topic = "Database Design"

        with pytest.raises(ValueError, match="Content alignment check failed"):
            AssignmentValidator.validate_educational_alignment(
                content=content,
                topic=topic,
                bloom_level="Apply",
                difficulty="Hard",
            )

    def test_check_duplicate_different_success(self):
        new_content = "Build a microservice architectural pipeline."
        existing = ["Create a multiple-choice question database system."]
        # Should pass Jaccard similarity check
        AssignmentValidator.check_duplicate(new_content, existing)

    def test_check_duplicate_similar_raises(self):
        new_content = "Design and build a database schema for an online bookstore."
        existing = ["Design and build a database schema for a library bookstore."]
        with pytest.raises(ValueError, match="Duplicate check failed"):
            AssignmentValidator.check_duplicate(new_content, existing)


# ── 5. Orchestration Pipeline Integration Tests ─────────────────────────

class TestAssignmentIntegrationPipeline:
    """Tests the orchestrator pipeline end-to-end with mock LLM and database."""

    @pytest.mark.asyncio
    @patch("app.services.retriever.RetrieverService.retrieve_context", new_callable=AsyncMock)
    @patch("app.services.prompt_builder.PromptBuilderService.build_prompt", new_callable=AsyncMock)
    @patch("app.services.llm_orchestrator.LLMOrchestratorService.generate", new_callable=AsyncMock)
    async def test_full_assignment_generation_pipeline(
        self,
        mock_llm,
        mock_prompt,
        mock_retrieve,
        db_session: AsyncSession,
        test_user: dict,
    ):
        # 1. Setup curriculum records in DB
        dept = Department(id=uuid.uuid4(), name="Computer Science", code="CS")
        db_session.add(dept)
        await db_session.flush()

        prog = Program(id=uuid.uuid4(), department_id=dept.id, name="B.Tech CS", duration_years=4)
        db_session.add(prog)
        await db_session.flush()

        sem = Semester(id=uuid.uuid4(), program_id=prog.id, number=3)
        db_session.add(sem)
        await db_session.flush()

        course = Course(id=uuid.uuid4(), semester_id=sem.id, course_code="CS301", course_title="Database Systems", credits=4)
        db_session.add(course)
        await db_session.flush()

        unit = Unit(id=uuid.uuid4(), course_id=course.id, unit_number=1, title="Unit 1: DB Intro")
        db_session.add(unit)
        await db_session.flush()

        topic = Topic(id=uuid.uuid4(), unit_id=unit.id, topic_name="SQL Joins", description="Inner and outer joins")
        db_session.add(topic)
        await db_session.flush()

        co = CourseOutcome(id=uuid.uuid4(), course_id=course.id, co_number=1, description="Apply SQL Joins in real-world scenarios.")
        db_session.add(co)
        await db_session.flush()

        # 2. Setup mocks
        mock_retrieve.return_value = {
            "chunks": [
                {
                    "chunk_id": uuid.uuid4(),
                    "text": "SQL Joins are used to combine rows from multiple tables.",
                    "score": 0.95,
                }
            ]
        }
        mock_prompt.return_value = {
            "system_prompt": "System instructions",
            "full_prompt": "Assembled full prompt text",
        }
        
        # Structure the exact expected JSON response from the LLM
        mock_llm_json = {
            "content": "Create a design for an online store database using SQL Joins. Build a database layout using an inquiry-based socratic method.",
            "rubric": {
                "assessment_criteria": ["Correct database normalisation"],
                "expected_learning_outcomes": ["Outcomes listed"],
                "evaluation_guidelines": "Scoring details",
                "mark_distribution": {"Design": 50},
                "suggested_solution_outline": ["Setup relationships"],
            }
        }
        mock_llm.return_value = {
            "text": json.dumps(mock_llm_json),
            "model": "gemma3:4b",
        }

        # 3. Trigger generate service
        orchestrator = AssignmentOrchestratorService()
        result = await orchestrator.generate_assignment(
            db=db_session,
            course_id=course.id,
            topic_id=topic.id,
            generator_type="Programming Assignments",
            bloom_level="Create",
            difficulty="Medium",
            marks=50,
            pedagogical_approach="Inquiry-based",
            teaching_style="Socratic",
            created_by=uuid.UUID(test_user["id"]),
        )

        # 4. Verify assertions
        assert result.id is not None
        assert "SQL Joins" in result.content
        assert "# Grading Rubric & Evaluation Guide" in result.content
        assert result.marks == 50
        assert result.bloom_level == "Create"
        assert result.difficulty == "Medium"
        assert "assessment_criteria" in result.rubric


# ── 6. REST API Endpoints Verification ───────────────────────────────────

class TestAssignmentAPI:
    """Verifies REST route requests, inputs, history, and status codes."""

    @pytest.mark.asyncio
    async def test_generate_endpoint_success(
        self,
        client: AsyncClient,
        auth_headers: dict,
        db_session: AsyncSession,
    ):
        # 1. Setup curriculum records in DB
        dept = Department(id=uuid.uuid4(), name="Computer Science", code="CS")
        db_session.add(dept)
        await db_session.flush()

        prog = Program(id=uuid.uuid4(), department_id=dept.id, name="B.Tech CS", duration_years=4)
        db_session.add(prog)
        await db_session.flush()

        sem = Semester(id=uuid.uuid4(), program_id=prog.id, number=3)
        db_session.add(sem)
        await db_session.flush()

        course = Course(id=uuid.uuid4(), semester_id=sem.id, course_code="CS301", course_title="Database Systems", credits=4)
        db_session.add(course)
        await db_session.flush()

        unit = Unit(id=uuid.uuid4(), course_id=course.id, unit_number=1, title="Unit 1: DB Intro")
        db_session.add(unit)
        await db_session.flush()

        topic = Topic(id=uuid.uuid4(), unit_id=unit.id, topic_name="SQL Joins", description="Inner and outer joins")
        db_session.add(topic)
        await db_session.flush()

        # 2. Patch orchestrator generation
        with patch("app.services.assignment.service.AssignmentOrchestratorService.generate_assignment", new_callable=AsyncMock) as mock_service:
            now = datetime.utcnow()
            mock_assignment = Assignment(
                id=uuid.uuid4(),
                course_id=course.id,
                topic_id=topic.id,
                generator_type="Programming Assignments",
                marks=50,
                difficulty="Medium",
                bloom_level="Apply",
                prompt_version="v1.0",
                model_version="gemma3",
                content="Create code matching the requirements. Apply concepts.",
                rubric={
                    "assessment_criteria": ["Correct database normalisation"],
                    "expected_learning_outcomes": ["Outcomes listed"],
                    "evaluation_guidelines": "Scoring details",
                    "mark_distribution": {"Design": 50},
                    "suggested_solution_outline": ["Setup relationships"],
                },
                created_by=uuid.uuid4(),
                history=[],
            )
            # Direct assignment bypasses SQLAlchemy server_default timestamp limitations in tests
            mock_assignment.created_at = now
            mock_assignment.updated_at = now

            mock_service.return_value = mock_assignment

            payload = {
                "course_id": str(course.id),
                "topic_id": str(topic.id),
                "generator_type": "Programming Assignments",
                "bloom_level": "Apply",
                "difficulty": "Medium",
                "marks": 50,
                "pedagogical_approach": "Inquiry-based",
                "teaching_style": "Socratic",
            }

            res = await client.post(
                "/api/v1/assignments/generate",
                headers=auth_headers,
                json=payload,
            )
            assert res.status_code == 200
            data = res.json()["data"]
            assert data["content"] == "Create code matching the requirements. Apply concepts."
            assert data["marks"] == 50

    @pytest.mark.asyncio
    async def test_validate_endpoint(self, client: AsyncClient, auth_headers: dict):
        payload = {
            "content": "Create a database architecture. Design a layout using an inquiry-based approach and standard academic style.",
            "topic": "Database Architecture",
            "bloom_level": "Create",
            "difficulty": "Medium",
            "rubric": {
                "assessment_criteria": ["Correct database normalisation"],
                "expected_learning_outcomes": ["Outcomes listed"],
                "evaluation_guidelines": "Scoring details",
                "mark_distribution": {"Design": 50},
                "suggested_solution_outline": ["Setup relationships"],
            },
            "pedagogical_approach": "Inquiry-based",
            "teaching_style": "Standard Academic",
        }

        res = await client.post(
            "/api/v1/assignments/validate",
            headers=auth_headers,
            json=payload,
        )
        assert res.status_code == 200
        assert res.json()["data"]["success"] is True

    @pytest.mark.asyncio
    async def test_health_endpoint(self, client: AsyncClient, auth_headers: dict):
        res = await client.get("/api/v1/assignments/health", headers=auth_headers)
        assert res.status_code == 200
        assert res.json()["data"]["status"] == "healthy"

    @pytest.mark.asyncio
    @patch("app.api.v1.assignment.AssignmentRepository.get_by_id", new_callable=AsyncMock)
    @patch("app.api.v1.assignment.AssignmentRepository.delete", new_callable=AsyncMock)
    @patch("app.services.assignment.service.AssignmentOrchestratorService.generate_assignment", new_callable=AsyncMock)
    async def test_regenerate_endpoint_success(
        self,
        mock_generate,
        mock_delete,
        mock_get,
        client: AsyncClient,
        auth_headers: dict,
    ):
        now = datetime.utcnow()
        q_id = uuid.uuid4()
        existing = Assignment(
            id=q_id,
            course_id=uuid.uuid4(),
            topic_id=uuid.uuid4(),
            generator_type="Programming Assignments",
            marks=50,
            difficulty="Medium",
            bloom_level="Apply",
            prompt_version="v1.0",
            model_version="gemma3",
            content="Old Assignment Content. Apply concepts.",
            rubric={
                "assessment_criteria": ["Criteria"],
                "expected_learning_outcomes": ["Outcomes"],
                "evaluation_guidelines": "Guidelines",
                "mark_distribution": {"Part A": 50},
                "suggested_solution_outline": ["Solution"],
            },
            created_by=uuid.uuid4(),
            history=[],
        )
        existing.created_at = now
        existing.updated_at = now
        mock_get.return_value = existing

        fresh = Assignment(
            id=uuid.uuid4(),
            course_id=existing.course_id,
            topic_id=existing.topic_id,
            generator_type="Programming Assignments",
            marks=50,
            difficulty="Medium",
            bloom_level="Apply",
            prompt_version="v1.0",
            model_version="gemma3",
            content="New Regenerated Assignment Content. Apply concepts.",
            rubric=existing.rubric,
            created_by=existing.created_by,
            history=[],
        )
        fresh.created_at = now
        fresh.updated_at = now
        mock_generate.return_value = fresh
        mock_delete.return_value = None

        res = await client.post(
            "/api/v1/assignments/regenerate",
            headers=auth_headers,
            json={
                "assignment_id": str(q_id),
                "faculty_preferences": "Add more coding",
            }
        )
        assert res.status_code == 200, f"Expected 200 but got {res.status_code}: {res.json()}"
        payload = res.json()
        assert payload["success"] is True
        assert payload["data"]["content"] == "New Regenerated Assignment Content. Apply concepts."
        assert len(payload["data"]["history"]) == 1
        assert payload["data"]["history"][0]["content"] == "Old Assignment Content. Apply concepts."
