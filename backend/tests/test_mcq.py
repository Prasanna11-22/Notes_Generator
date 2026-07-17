"""
Unit and Integration Tests for Phase 11 MCQ Generation Engine.
"""

import json
import uuid
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import status
from httpx import AsyncClient

from app.models.curriculum import Course, Topic, CourseOutcome, Department, Program, Semester, Unit
from app.models.mcq import MCQQuestion
from app.services.mcq.blueprint import AssessmentBlueprintService
from app.services.mcq.factory import GenerationStrategyFactory
from app.services.mcq.validator import MCQValidator
from app.services.mcq.distractor_analyzer import DistractorAnalyzer
from app.services.mcq.duplicate_detector import MCQDuplicateDetector
from app.services.mcq.difficulty_calibrator import DifficultyCalibrator
from app.services.mcq.service import MCQOrchestratorService


# ── 1. Unit Tests: Factory & Strategy Pattern ────────────────────────────────

class TestMCQGeneratorFactory:
    def test_factory_resolves_all_6_bloom_levels(self):
        levels = ["Remember", "Understand", "Apply", "Analyze", "Evaluate", "Create"]
        for lvl in levels:
            gen = GenerationStrategyFactory.get_generator(lvl)
            assert gen is not None
            assert gen.get_bloom_level() == lvl

    def test_factory_invalid_level_raises(self):
        with pytest.raises(ValueError, match="Unsupported Bloom level"):
            GenerationStrategyFactory.get_generator("InvalidBloom")


# ── 2. Unit Tests: Assessment Blueprint Service ──────────────────────────────

class TestAssessmentBlueprint:
    def test_calculate_distribution_clean_percentages(self):
        dist = {"Remember": 0.20, "Understand": 0.30, "Apply": 0.50}
        counts = AssessmentBlueprintService.calculate_distribution(10, dist)
        assert counts["Remember"] == 2
        assert counts["Understand"] == 3
        assert counts["Apply"] == 5
        assert sum(counts.values()) == 10

    def test_calculate_distribution_fractional_largest_remainder(self):
        # 10 questions with 25%, 25%, 50% -> 2.5, 2.5, 5.0
        # Largest Remainder should round one of the 2.5s up to 3 and the other to 2 (or 3, 3, 4)
        dist = {"Remember": 0.25, "Understand": 0.25, "Apply": 0.50}
        counts = AssessmentBlueprintService.calculate_distribution(10, dist)
        assert sum(counts.values()) == 10
        assert counts["Remember"] in (2, 3)
        assert counts["Understand"] in (2, 3)
        assert counts["Apply"] == 5

    def test_calculate_distribution_empty_fallback(self):
        counts = AssessmentBlueprintService.calculate_distribution(5, {})
        assert counts == {"Understand": 5}


# ── 3. Unit Tests: MCQ Validator ─────────────────────────────────────────────

class TestMCQValidator:
    def test_validate_structure_success(self):
        MCQValidator.validate_mcq_structure(
            question_text="What is 2 + 2?",
            options={"A": "3", "B": "4", "C": "5"},
            correct_answer="B"
        )

    def test_validate_structure_invalid_answer_key_raises(self):
        with pytest.raises(ValueError, match="Invalid answer key"):
            MCQValidator.validate_mcq_structure(
                question_text="What is 2 + 2?",
                options={"A": "3", "B": "4"},
                correct_answer="C"
            )

    def test_validate_educational_alignment_success(self):
        MCQValidator.validate_educational_alignment(
            question_text="Explain the concept of database normal form.",
            topic="Database normalization",
            bloom_level="Understand",
            course_outcomes=["Understand normal forms."]
        )

    def test_validate_educational_alignment_bloom_mismatch_raises(self):
        with pytest.raises(ValueError, match="does not align with cognitive Bloom level"):
            # Remember level verbs: define, recall, list (none are present here)
            MCQValidator.validate_educational_alignment(
                question_text="Critique the scalability limits of relational tables.",
                topic="relational tables",
                bloom_level="Remember"
            )


# ── 4. Unit Tests: Distractor Analyzer ────────────────────────────────────────

class TestDistractorAnalyzer:
    def test_analyze_distractors_success(self):
        options = {"A": "First Choice Text", "B": "Second Option Wording", "C": "Third Unique Statement"}
        # Should not raise
        DistractorAnalyzer.analyze_distractors(options)

    def test_analyze_distractors_duplicate_value_raises(self):
        options = {"A": "Same Wording", "B": "Same Wording", "C": "Unique Choice"}
        with pytest.raises(ValueError, match="Duplicate option choices found"):
            DistractorAnalyzer.analyze_distractors(options)

    def test_analyze_distractors_placeholder_raises(self):
        options = {"A": "Valid Option", "B": "None of the above", "C": "Unique Choice"}
        with pytest.raises(ValueError, match="low-quality distractor placeholder"):
            DistractorAnalyzer.analyze_distractors(options)

    def test_analyze_distractors_extreme_length_imbalance_raises(self):
        options = {
            "A": "Short choice.",
            "B": "An extremely long choice that contains detailed scenario information and descriptions, serving as an obvious giveaway compared to the others.",
            "C": "Another short."
        }
        with pytest.raises(ValueError, match="Obvious giveaway detected"):
            DistractorAnalyzer.analyze_distractors(options)


# ── 5. Unit Tests: Duplicate Detector ─────────────────────────────────────────

class TestMCQDuplicateDetector:
    def test_check_duplicate_different_success(self):
        existing = ["What is inheritance in programming?", "Explain database normal forms."]
        MCQDuplicateDetector.check_duplicate("Define what polymorphism means in Java.", existing)

    def test_check_duplicate_similar_raises(self):
        existing = ["What is inheritance in OOP programming?"]
        # Very high wording similarity (over threshold)
        with pytest.raises(ValueError, match="Duplicate detection failed"):
            MCQDuplicateDetector.check_duplicate("What is inheritance in object oriented programming?", existing, threshold=0.3)


# ── 6. Unit Tests: Difficulty Calibrator ──────────────────────────────────────

class TestDifficultyCalibrator:
    def test_calibrate_difficulty_easy(self):
        res = DifficultyCalibrator.calibrate_difficulty("Define list.", "Remember", "Easy")
        assert res == "Easy"

    def test_calibrate_difficulty_mismatch_raises(self):
        with pytest.raises(ValueError, match="Difficulty mismatch"):
            # Syntactically complex, hard Bloom level, but requesting Easy
            DifficultyCalibrator.calibrate_difficulty(
                "Evaluate the scenario where a critique of relational databases is required.",
                "Evaluate",
                "Easy"
            )


# ── 7. Integration Tests: Complete MCQ Generation Pipeline ───────────────────

@pytest.mark.asyncio
class TestMCQIntegrationPipeline:
    @pytest.fixture(autouse=True)
    async def seed_curriculum_details(self, db_session: AsyncSession):
        dept = Department(id=uuid.uuid4(), name="Computer Science", code="CS")
        db_session.add(dept)
        await db_session.flush()

        prog = Program(id=uuid.uuid4(), department_id=dept.id, name="B.Tech CS", duration_years=4)
        db_session.add(prog)
        await db_session.flush()

        sem = Semester(id=uuid.uuid4(), program_id=prog.id, number=3)
        db_session.add(sem)
        await db_session.flush()

        course = Course(
            id=uuid.uuid4(),
            semester_id=sem.id,
            course_code="CS202",
            course_title="Data Structures",
            credits=4,
        )
        db_session.add(course)
        await db_session.flush()

        unit = Unit(id=uuid.uuid4(), course_id=course.id, unit_number=1, title="Trees")
        db_session.add(unit)
        await db_session.flush()

        topic = Topic(id=uuid.uuid4(), unit_id=unit.id, topic_name="Heaps", description="Max and Min Heaps")
        db_session.add(topic)
        await db_session.flush()

        co = CourseOutcome(id=uuid.uuid4(), course_id=course.id, co_number=1, description="Implement heaps.")
        db_session.add(co)
        await db_session.flush()

        self.course_id = course.id
        self.topic_id = topic.id

    @patch("app.services.retriever.RetrieverService.retrieve_context")
    @patch("app.services.prompt_builder.PromptBuilderService.build_prompt")
    @patch("app.services.llm_orchestrator.LLMOrchestratorService.generate")
    async def test_full_mcq_generation_pipeline(
        self,
        mock_llm,
        mock_prompt_builder,
        mock_retriever,
        db_session: AsyncSession
    ):
        mock_retriever.return_value = {
            "query": "Heaps",
            "chunks": [{"chunk_id": uuid.uuid4(), "text": "Heaps store items.", "score": 0.9}],
            "formatted_context": "Heaps store items."
        }

        mock_prompt_builder.return_value = {
            "system_prompt": "System instructions.",
            "instruction_prompt": "Generate MCQs.",
            "full_prompt": "Full prompt payload."
        }

        remember_json = [
            {
                "question": "What is the primary structure used to implement a heap?",
                "options": {
                    "A": "Binary Tree Representation",
                    "B": "Hash Map Structure",
                    "C": "Linked List Chain",
                    "D": "Double Ended Queue"
                },
                "correct_answer": "A",
                "explanation": "Heaps are binary trees."
            }
        ]

        understand_json = [
            {
                "question": "Explain how the heapify up process restores heap order.",
                "options": {
                    "A": "It bubbles the element up by comparing with parent",
                    "B": "It shifts it to the root directly",
                    "C": "It rebuilds the entire binary tree structure",
                    "D": "It deletes all other keys in the node tree"
                },
                "correct_answer": "A",
                "explanation": "Explain how comparisons propagate upward."
            }
        ]

        mock_llm.side_effect = [
            {
                "text": json.dumps(remember_json),
                "prompt_tokens": 50,
                "completion_tokens": 200,
                "model": "gemma3:4b",
                "provider": "ollama"
            },
            {
                "text": json.dumps(understand_json),
                "prompt_tokens": 50,
                "completion_tokens": 200,
                "model": "gemma3:4b",
                "provider": "ollama"
            }
        ]

        service = MCQOrchestratorService()
        results = await service.generate_mcqs(
            db=db_session,
            course_id=self.course_id,
            topic_id=self.topic_id,
            bloom_distribution={"Remember": 0.5, "Understand": 0.5},
            difficulty="Medium",
            number_of_questions=2
        )

        assert len(results) == 2
        assert results[0].question_text == "What is the primary structure used to implement a heap?"
        assert results[0].correct_answer == "A"
        assert results[0].bloom_level == "Remember"
        assert results[1].question_text == "Explain how the heapify up process restores heap order."
        assert results[1].correct_answer == "A"
        assert results[1].bloom_level == "Understand"


# ── 8. Endpoint API Routes Tests ─────────────────────────────────────────────

@pytest.mark.asyncio
class TestMCQAPI:
    @patch("app.api.v1.mcq.MCQOrchestratorService.generate_mcqs")
    async def test_generate_endpoint_success(self, mock_generate, client: AsyncClient, auth_headers: dict):
        from datetime import datetime
        mock_generate.return_value = [
            MCQQuestion(
                id=uuid.uuid4(),
                course_id=uuid.uuid4(),
                topic_id=uuid.uuid4(),
                question_text="What is a heap?",
                options={"A": "Tree", "B": "Graph"},
                correct_answer="A",
                explanation="Explanation",
                bloom_level="Remember",
                difficulty="Easy",
                prompt_version="v1.0",
                model_version="gemma3",
                created_by=uuid.uuid4(),
                history=[],
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
        ]

        res = await client.post(
            "/api/v1/mcq/generate",
            headers=auth_headers,
            json={
                "course_id": str(uuid.uuid4()),
                "topic_id": str(uuid.uuid4()),
                "bloom_distribution": {"Remember": 1.0},
                "difficulty": "Easy",
                "number_of_questions": 1
            }
        )
        assert res.status_code == 200
        payload = res.json()
        assert payload["success"] is True
        assert len(payload["data"]) == 1
        assert payload["data"][0]["question_text"] == "What is a heap?"

    async def test_validate_endpoint(self, client: AsyncClient, auth_headers: dict):
        res = await client.post(
            "/api/v1/mcq/validate",
            headers=auth_headers,
            json={
                "question_text": "What is a heap structure?",
                "options": {"A": "A tree", "B": "A queue"},
                "correct_answer": "A",
                "topic": "Heaps",
                "bloom_level": "Remember"
            }
        )
        assert res.status_code == 200
        assert res.json()["data"]["success"] is True

    async def test_health_endpoint(self, client: AsyncClient, auth_headers: dict):
        res = await client.get("/api/v1/mcq/health", headers=auth_headers)
        assert res.status_code == 200
        assert res.json()["data"]["status"] == "healthy"

    @patch("app.api.v1.mcq.MCQRepository.get_by_id", new_callable=AsyncMock)
    @patch("app.api.v1.mcq.MCQRepository.delete", new_callable=AsyncMock)
    @patch("app.api.v1.mcq.MCQOrchestratorService.generate_mcqs", new_callable=AsyncMock)
    async def test_regenerate_endpoint_success(self, mock_generate, mock_delete, mock_get, client: AsyncClient, auth_headers: dict):
        from datetime import datetime
        q_id = uuid.uuid4()
        now = datetime.utcnow()
        existing = MCQQuestion(
            id=q_id,
            course_id=uuid.uuid4(),
            topic_id=uuid.uuid4(),
            question_text="Old Question Stem?",
            options={"A": "One", "B": "Two"},
            correct_answer="A",
            explanation="Old Explanation",
            bloom_level="Remember",
            difficulty="Easy",
            prompt_version="v1.0",
            model_version="gemma3",
            created_by=uuid.uuid4(),
            history=[],
        )
        # SQLAlchemy server_default columns are only populated by the DB;
        # directly assign them for use in offline unit tests.
        existing.created_at = now
        existing.updated_at = now
        mock_get.return_value = existing

        fresh = MCQQuestion(
            id=uuid.uuid4(),
            course_id=existing.course_id,
            topic_id=existing.topic_id,
            question_text="New Regenerated Question Stem?",
            options={"A": "One", "B": "Two"},
            correct_answer="B",
            explanation="New Explanation",
            bloom_level="Remember",
            difficulty="Easy",
            prompt_version="v1.0",
            model_version="gemma3",
            created_by=existing.created_by,
            history=[],
        )
        fresh.created_at = now
        fresh.updated_at = now
        mock_generate.return_value = [fresh]
        mock_delete.return_value = None

        res = await client.post(
            "/api/v1/mcq/regenerate",
            headers=auth_headers,
            json={
                "question_id": str(q_id),
                "faculty_preferences": "Make it harder"
            }
        )
        assert res.status_code == 200, f"Expected 200 but got {res.status_code}: {res.json()}"
        payload = res.json()
        assert payload["success"] is True
        assert payload["data"]["question_text"] == "New Regenerated Question Stem?"
        assert len(payload["data"]["history"]) == 1
        assert payload["data"]["history"][0]["question_text"] == "Old Question Stem?"
