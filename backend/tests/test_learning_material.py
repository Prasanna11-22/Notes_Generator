"""
Unit and Integration Tests for Phase 10 Learning Material Generation Engine.
"""

import uuid
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import status
from httpx import AsyncClient

from app.core.config import settings
from app.models.curriculum import Course, Topic, CourseOutcome, Department, Program, Semester, Unit
from app.models.learning_material import LearningMaterial, LearningMaterialCache
from app.services.learning_material.factory import GenerationStrategyFactory
from app.services.learning_material.formatter import LearningMaterialFormatter
from app.services.learning_material.validator import LearningMaterialValidator
from app.services.learning_material.cache_service import LearningMaterialCacheService
from app.services.learning_material.history_service import LearningMaterialHistoryService
from app.services.learning_material.service import LearningMaterialService


# ── 1. Unit Tests: Factory & Strategy Pattern ────────────────────────────────

class TestGeneratorFactory:
    def test_factory_resolves_all_11_types(self):
        strategy_types = [
            "Topic Notes", "Concept Explanation", "Worked Examples",
            "Summary Notes", "Revision Notes", "Discussion Questions",
            "Classroom Activities", "Learning Objectives", "Key Takeaways",
            "Common Mistakes", "Real-world Applications"
        ]
        for t in strategy_types:
            generator = GenerationStrategyFactory.get_generator(t)
            assert generator is not None
            assert len(generator.get_generation_type()) > 0
            assert len(generator.get_prompt_template_name()) > 0

    def test_factory_invalid_type_raises(self):
        with pytest.raises(ValueError, match="Unsupported generation type"):
            GenerationStrategyFactory.get_generator("Invalid Type Name")


# ── 2. Unit Tests: Formatter Service ─────────────────────────────────────────

class TestMaterialFormatter:
    def test_format_markdown_verbatim(self):
        content = "# Title\n\n- Item 1\n- Item 2"
        res = LearningMaterialFormatter.format_content(content, "markdown")
        assert res == content

    def test_format_html_conversion(self):
        content = "# Title\n\nSome text here with **bold** word."
        res = LearningMaterialFormatter.format_content(content, "html")
        assert "<h1>Title</h1>" in res
        assert "<strong>bold</strong>" in res

    def test_format_plain_text_strip(self):
        content = "# Title\n\nSome text with `code backticks` and **bold** formatting."
        res = LearningMaterialFormatter.format_content(content, "plain text")
        assert "#" not in res
        assert "`" not in res
        assert "**" not in res
        assert "Title" in res
        assert "code backticks" in res

    def test_format_json_wrapping(self):
        content = "# Notes"
        res = LearningMaterialFormatter.format_content(content, "json")
        import json
        parsed = json.loads(res)
        assert parsed["content"] == content
        assert parsed["paragraphs_count"] == 1


# ── 3. Unit Tests: Validator Service ─────────────────────────────────────────

class TestMaterialValidator:
    def test_validate_content_success(self):
        # Should not raise any error
        LearningMaterialValidator.validate_content("# Title\n\nThis is a complete and clean paragraph.")

    def test_validate_content_placeholder_rejected(self):
        with pytest.raises(ValueError, match="placeholder"):
            LearningMaterialValidator.validate_content("# Header\n\n[Insert topic here] information details.")

    def test_validate_content_duplicate_rejected(self):
        text = (
            "# Main Header\n\n"
            "This is a relatively long paragraph that will be duplicated in this document to test if the "
            "validator successfully catches duplicate text structures.\n\n"
            "This is a relatively long paragraph that will be duplicated in this document to test if the "
            "validator successfully catches duplicate text structures."
        )
        with pytest.raises(ValueError, match="Duplicate paragraph"):
            LearningMaterialValidator.validate_content(text)

    def test_validate_content_lack_of_structure_rejected(self):
        with pytest.raises(ValueError, match="lacks clean formatting"):
            LearningMaterialValidator.validate_content("Just plain text with no headers or lists in it.")

    def test_validate_educational_alignment_success(self):
        LearningMaterialValidator.validate_educational_alignment(
            text="Let's define the parameters clearly.",
            topic="Parameters",
            bloom_level="Remember",
            course_outcomes=["Understand variables and parameters."]
        )

    def test_validate_educational_alignment_topic_miss(self):
        with pytest.raises(ValueError, match="does not cover the requested topic"):
            LearningMaterialValidator.validate_educational_alignment(
                text="# Database Normalization\n\nWe explain tables.",
                topic="Calculus integration",
            )

    def test_validate_educational_alignment_bloom_miss(self):
        with pytest.raises(ValueError, match="do not align with Bloom level"):
            # Remember level verbs: define, recall, list (none are present here)
            LearningMaterialValidator.validate_educational_alignment(
                text="# Variables\n\nWe will examine, analyze, and construct new components.",
                topic="Variables",
                bloom_level="Remember",
            )

    def test_validate_educational_alignment_co_miss(self):
        with pytest.raises(ValueError, match="not aligned with Course Outcome"):
            LearningMaterialValidator.validate_educational_alignment(
                text="# Programming Basics\n\nWe write variables and print statements.",
                topic="Programming Basics",
                course_outcomes=["Calculate matrix determinants and eigenvalues."]
            )


# ── 4. Unit Tests: Cache & History Services ──────────────────────────────────

class TestCacheAndHistoryServices:
    def test_cache_key_generation_is_deterministic(self):
        k1 = LearningMaterialCacheService.generate_cache_key(
            "Topic", "Socratic", "Inquiry", "Apply", "Conceptual", "Worked Examples", "v1"
        )
        k2 = LearningMaterialCacheService.generate_cache_key(
            "Topic", "Socratic", "Inquiry", "Apply", "Conceptual", "Worked Examples", "v1"
        )
        assert k1 == k2
        
        # Changing one component changes key
        k3 = LearningMaterialCacheService.generate_cache_key(
            "Topic", "Lecturing", "Inquiry", "Apply", "Conceptual", "Worked Examples", "v1"
        )
        assert k1 != k3

    @pytest.mark.asyncio
    async def test_cache_get_set_clear_flow(self, db_session: AsyncSession):
        cache_service = LearningMaterialCacheService()
        key = "test_key_hash_123"
        
        # 1. Get (miss)
        res = await cache_service.get(db_session, key)
        assert res is None

        # 2. Set
        await cache_service.set(db_session, key, "Content body", "markdown")
        await db_session.flush()

        # 3. Get (hit)
        res = await cache_service.get(db_session, key)
        assert res is not None
        assert res.content == "Content body"

        # 4. Clear all
        count = await cache_service.clear_all(db_session)
        assert count == 1
        res = await cache_service.get(db_session, key)
        assert res is None

    @pytest.mark.asyncio
    async def test_history_logging(self, db_session: AsyncSession):
        history_service = LearningMaterialHistoryService()
        
        material = LearningMaterial(
            course_id=uuid.uuid4(),
            topic_id=uuid.uuid4(),
            generator_type="Worked Examples",
            prompt_version="v1.0",
            model="gemma3:4b",
            status="completed",
            content="Valid content block.",
            format="markdown",
            created_by=uuid.uuid4(),
            history=[]
        )
        db_session.add(material)
        await db_session.flush()

        # Log revision
        updated = await history_service.log_revision(
            db=db_session,
            material=material,
            old_content="Valid content block.",
            changed_by_user_id=uuid.uuid4(),
            reason="Regeneration adjustment"
        )
        assert len(updated.history) == 1
        assert updated.history[0]["content"] == "Valid content block."
        assert updated.history[0]["reason"] == "Regeneration adjustment"


# ── 5. Integration Tests: Complete Generation Pipeline ───────────────────────

@pytest.mark.asyncio
class TestLearningMaterialIntegration:
    @pytest.fixture(autouse=True)
    async def seed_curriculum_details(self, db_session: AsyncSession):
        """Seed curriculum structures for pipeline tests."""
        dept = Department(id=uuid.uuid4(), name="Math Dept", code="MATH")
        db_session.add(dept)
        await db_session.flush()

        prog = Program(id=uuid.uuid4(), department_id=dept.id, name="Math B.S.", duration_years=4)
        db_session.add(prog)
        await db_session.flush()

        sem = Semester(id=uuid.uuid4(), program_id=prog.id, number=2)
        db_session.add(sem)
        await db_session.flush()

        course = Course(
            id=uuid.uuid4(),
            semester_id=sem.id,
            course_code="MATH101",
            course_title="Calculus Integration",
            credits=3,
        )
        db_session.add(course)
        await db_session.flush()

        unit = Unit(id=uuid.uuid4(), course_id=course.id, unit_number=1, title="Integrals")
        db_session.add(unit)
        await db_session.flush()

        topic = Topic(id=uuid.uuid4(), unit_id=unit.id, topic_name="Limits", description="Intro to Limits")
        db_session.add(topic)
        await db_session.flush()

        co = CourseOutcome(id=uuid.uuid4(), course_id=course.id, co_number=1, description="Solve limits.")
        db_session.add(co)
        await db_session.flush()

        self.course_id = course.id
        self.topic_id = topic.id
        self.co_id = co.id

    @patch("app.services.retriever.RetrieverService.retrieve_context")
    @patch("app.services.prompt_builder.PromptBuilderService.build_prompt")
    @patch("app.services.llm_orchestrator.LLMOrchestratorService.generate")
    async def test_full_material_generation_pipeline(
        self,
        mock_llm,
        mock_prompt_builder,
        mock_retriever,
        db_session: AsyncSession
    ):
        mock_retriever.return_value = {
            "query": "Limits",
            "chunks": [{"chunk_id": uuid.uuid4(), "text": "Limits define parameters.", "score": 0.95}],
            "formatted_context": "Limits define parameters."
        }
        
        mock_prompt_builder.return_value = {
            "system_prompt": "You are a math tutor.",
            "instruction_prompt": "Explain limits.",
            "retrieved_context": "Limits define parameters.",
            "full_prompt": "Assembled full prompt.",
            "generation_type": "Concept Explanation"
        }

        mock_llm.return_value = {
            "text": "# Limits Concept\n\nWe will define variables and solve mathematical limits.",
            "prompt_tokens": 50,
            "completion_tokens": 120,
            "model": "gemma3:4b",
            "provider": "ollama"
        }

        # Clear cache first
        cache_service = LearningMaterialCacheService()
        await cache_service.clear_all(db_session)

        # Invoke Orchestration pipeline
        service = LearningMaterialService()
        result = await service.generate_material(
            db=db_session,
            course_id=self.course_id,
            topic_id=self.topic_id,
            generator_type="Concept Explanation",
            bloom_level="Remember",
            output_format="markdown"
        )

        assert result["id"] is not None
        assert "Limits Concept" in result["content"]
        assert result["format"] == "markdown"
        assert result["cached"] is False

        # ── Test Caching: Calling again should hit cache ──────────────────────
        cached_result = await service.generate_material(
            db=db_session,
            course_id=self.course_id,
            topic_id=self.topic_id,
            generator_type="Concept Explanation",
            bloom_level="Remember",
            output_format="markdown"
        )
        assert cached_result["cached"] is True
        assert "Limits Concept" in cached_result["content"]


# ── 6. Mocked Endpoint API Routes Tests ──────────────────────────────────────

@pytest.mark.asyncio
class TestLearningMaterialAPI:
    @patch("app.services.learning_material.service.LearningMaterialService.generate_material")
    async def test_generate_endpoint_success(self, mock_generate, client: AsyncClient, auth_headers: dict):
        mock_generate.return_value = {
            "id": str(uuid.uuid4()),
            "content": "# Generated content.",
            "format": "markdown",
            "cached": False,
            "generator_type": "Concept Explanation",
            "model": "gemma3:4b",
            "prompt_version": "v1.0"
        }

        res = await client.post(
            "/api/v1/learning-material/generate",
            headers=auth_headers,
            json={
                "course_id": str(uuid.uuid4()),
                "topic_id": str(uuid.uuid4()),
                "generator_type": "Concept Explanation",
                "bloom_level": "Understand",
                "knowledge_level": "Conceptual",
                "teaching_style": "Socratic",
                "pedagogical_approach": "Inquiry-based",
                "difficulty": "Medium",
                "output_format": "markdown"
            }
        )
        assert res.status_code == 200
        payload = res.json()
        assert payload["success"] is True
        assert "Generated content" in payload["data"]["content"]

    @patch("app.services.learning_material.service.LearningMaterialService.regenerate_material")
    async def test_regenerate_endpoint_success(self, mock_regenerate, client: AsyncClient, auth_headers: dict):
        mock_regenerate.return_value = {
            "id": str(uuid.uuid4()),
            "content": "# Regenerated content.",
            "format": "markdown",
            "cached": False,
            "generator_type": "Concept Explanation",
            "model": "gemma3:4b",
            "prompt_version": "v1.0"
        }

        res = await client.post(
            "/api/v1/learning-material/regenerate",
            headers=auth_headers,
            json={
                "material_id": str(uuid.uuid4()),
                "faculty_preferences": "More examples.",
                "output_format": "markdown"
            }
        )
        assert res.status_code == 200
        payload = res.json()
        assert payload["success"] is True
        assert "Regenerated content" in payload["data"]["content"]

    async def test_generate_endpoint_forbidden_for_students(self, client: AsyncClient, db_session: AsyncSession):
        """Standard student users must be forbidden from learning material generation endpoints."""
        from app.core.security import hash_password
        from app.models.user import User

        hashed_pwd = await hash_password("student123")
        student = User(
            email="student_active@college.edu",
            hashed_password=hashed_pwd,
            full_name="Student User",
            role="student",
            is_active=True
        )
        db_session.add(student)
        await db_session.flush()

        login_res = await client.post(
            "/api/v1/auth/login",
            json={"email": "student_active@college.edu", "password": "student123"}
        )
        token = login_res.json()["data"]["access_token"]
        student_headers = {"Authorization": f"Bearer {token}"}

        res = await client.post(
            "/api/v1/learning-material/generate",
            headers=student_headers,
            json={
                "course_id": str(uuid.uuid4()),
                "topic_id": str(uuid.uuid4()),
                "generator_type": "Concept Explanation"
            }
        )
        assert res.status_code == 403

    async def test_validate_endpoint(self, client: AsyncClient, auth_headers: dict):
        res = await client.post(
            "/api/v1/learning-material/validate",
            headers=auth_headers,
            json={
                "text": "# Limits Concept\n\nWe will define variables and solve mathematical limits.",
                "topic": "Limits",
                "bloom_level": "Remember"
            }
        )
        assert res.status_code == 200
        payload = res.json()
        assert payload["data"]["success"] is True

    async def test_health_endpoint(self, client: AsyncClient, auth_headers: dict):
        res = await client.get("/api/v1/learning-material/health", headers=auth_headers)
        assert res.status_code == 200
        assert res.json()["data"]["status"] == "healthy"
