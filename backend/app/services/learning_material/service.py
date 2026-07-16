"""
Learning Material Generation Orchestrator Service.
"""

from typing import Any, Dict, Optional
import uuid
from loguru import logger
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.curriculum import Course, Topic, CourseOutcome
from app.models.learning_material import LearningMaterial
from app.services.retriever import RetrieverService
from app.services.prompt_builder import PromptBuilderService
from app.services.llm_orchestrator import LLMOrchestratorService
from app.services.learning_material.factory import GenerationStrategyFactory
from app.services.learning_material.validator import LearningMaterialValidator
from app.services.learning_material.formatter import LearningMaterialFormatter
from app.services.learning_material.cache_service import LearningMaterialCacheService
from app.services.learning_material.history_service import LearningMaterialHistoryService


class LearningMaterialService:
    """
    Orchestration service coordinating cache lookup, context retrieval,
    prompt validation, LLM generation, quality/educational validation,
    formatting, and revision history mapping.
    """

    def __init__(
        self,
        retriever_service: Optional[RetrieverService] = None,
        prompt_builder_service: Optional[PromptBuilderService] = None,
        llm_orchestrator_service: Optional[LLMOrchestratorService] = None,
        cache_service: Optional[LearningMaterialCacheService] = None,
        history_service: Optional[LearningMaterialHistoryService] = None,
    ) -> None:
        self.retriever_service = retriever_service
        self.prompt_builder_service = prompt_builder_service
        self.llm_orchestrator = llm_orchestrator_service or LLMOrchestratorService()
        self.cache_service = cache_service or LearningMaterialCacheService()
        self.history_service = history_service or LearningMaterialHistoryService()

    async def _resolve_dependencies(self, db: AsyncSession) -> None:
        """Resolve database-dependent services lazily."""
        if not self.retriever_service:
            self.retriever_service = RetrieverService(db)
        if not self.prompt_builder_service:
            self.prompt_builder_service = PromptBuilderService(db)

    async def generate_material(
        self,
        db: AsyncSession,
        course_id: uuid.UUID,
        topic_id: uuid.UUID,
        generator_type: str,
        bloom_level: Optional[str] = None,
        knowledge_level: Optional[str] = None,
        teaching_style: Optional[str] = None,
        pedagogical_approach: Optional[str] = None,
        difficulty: Optional[str] = None,
        faculty_preferences: Optional[str] = None,
        output_format: str = "markdown",
        created_by: Optional[uuid.UUID] = None,
    ) -> Dict[str, Any]:
        """
        Execute the learning material generation pipeline.
        """
        await self._resolve_dependencies(db)

        # ── 1. Query & Validate Curriculum metadata ───────────────────────────
        course_stmt = select(Course).where(Course.id == course_id)
        course_res = await db.execute(course_stmt)
        course = course_res.scalars().first()
        if not course:
            raise ValueError(f"Course not found for ID: {course_id}")

        topic_stmt = (
            select(Topic)
            .options(selectinload(Topic.unit))
            .where(Topic.id == topic_id)
        )
        topic_res = await db.execute(topic_stmt)
        topic = topic_res.scalars().first()
        if not topic:
            raise ValueError(f"Topic not found for ID: {topic_id}")
        
        unit = topic.unit
        if not unit:
            raise ValueError(f"Topic '{topic.topic_name}' is not assigned to a unit.")

        # Query Course Outcomes
        co_stmt = select(CourseOutcome).where(CourseOutcome.course_id == course_id)
        co_res = await db.execute(co_stmt)
        course_outcomes = list(co_res.scalars().all())
        co_strings = [f"CO{co.co_number}: {co.description}" for co in course_outcomes]
        co_joined = "; ".join(co_strings) if co_strings else "None configured"

        # Resolve generator strategy
        generator = GenerationStrategyFactory.get_generator(generator_type)

        # ── 2. Cache Lookup ───────────────────────────────────────────────────
        # Determine prompt version / templates mapping
        prompt_version = "v1.0"  # Default system default
        cache_key = self.cache_service.generate_cache_key(
            topic=topic.topic_name,
            teaching_style=teaching_style,
            pedagogy=pedagogical_approach,
            bloom_level=bloom_level,
            knowledge_level=knowledge_level,
            generation_type=generator_type,
            prompt_version=prompt_version,
        )

        cached = await self.cache_service.get(db, cache_key)
        if cached:
            # Format and return cached content
            formatted_text = LearningMaterialFormatter.format_content(
                cached.content, output_format
            )
            logger.info(
                "LearningMaterialService | Cache Hit | key={} type={} topic={!r}",
                cache_key,
                generator_type,
                topic.topic_name,
            )
            return {
                "content": formatted_text,
                "format": output_format,
                "cached": True,
                "generator_type": generator_type,
                "model": "cached",
                "prompt_version": prompt_version,
            }

        logger.info(
            "LearningMaterialService | Cache Miss | key={} type={} topic={!r}",
            cache_key,
            generator_type,
            topic.topic_name,
        )

        # ── 3. Retrieve Context from Knowledge Store ──────────────────────────
        # We apply filtering for target bloom/knowledge levels if they are mapped
        filters = {}
        if bloom_level:
            filters["bloom_level"] = bloom_level
        if knowledge_level:
            filters["knowledge_level"] = knowledge_level

        retrieval_query = f"{topic.topic_name} {topic.description or ''}".strip()
        retrieved_data = await self.retriever_service.retrieve_context(
            query=retrieval_query,
            limit=5,
            filters=filters if filters else None,
            relevance_threshold=0.1,  # Permissive threshold for testing
        )

        # Map chunks list structure for prompt builder
        chunks = []
        for c in retrieved_data.get("chunks", []):
            chunks.append({
                "chunk_id": str(c["chunk_id"]),
                "text": c["text"],
                "score": c.get("score", 0.9),
            })

        # ── 4. Build Optimized Prompt ─────────────────────────────────────────
        prompt_payload = await self.prompt_builder_service.build_prompt(
            generation_type=generator.get_generation_type(),
            retrieved_chunks=chunks,
            topic=topic.topic_name,
            course=course.course_title,
            course_outcomes=co_joined,
            unit=unit.title,
            bloom_distribution=bloom_level or "Understand",
            knowledge_level=knowledge_level,
            teaching_style=teaching_style,
            pedagogical_approach=pedagogical_approach,
            difficulty=difficulty,
            faculty_preferences=faculty_preferences,
        )

        # ── 5. Run LLM Generation ─────────────────────────────────────────────
        llm_response = await self.llm_orchestrator.generate(
            prompt=prompt_payload["full_prompt"],
            system_prompt=prompt_payload["system_prompt"],
            options={
                "temperature": 0.7,
            },
        )
        generated_raw_text = llm_response["text"]

        # ── 6. Quality & Educational Validation ──────────────────────────────
        LearningMaterialValidator.validate_content(generated_raw_text)
        LearningMaterialValidator.validate_educational_alignment(
            text=generated_raw_text,
            topic=topic.topic_name,
            bloom_level=bloom_level,
            course_outcomes=[co.description for co in course_outcomes] if course_outcomes else None,
        )

        # ── 7. Save Material to Database ──────────────────────────────────────
        new_material = LearningMaterial(
            course_id=course_id,
            topic_id=topic_id,
            generator_type=generator_type,
            prompt_version=prompt_version,
            model=llm_response.get("model", "gemma3:4b"),
            status="completed",
            content=generated_raw_text,
            format="markdown",
            created_by=created_by or uuid.UUID("00000000-0000-0000-0000-000000000000"),
        )
        db.add(new_material)
        await db.flush()

        # ── 8. Cache the Result ───────────────────────────────────────────────
        await self.cache_service.set(db, cache_key, generated_raw_text, "markdown")

        # ── 9. Format Output & Return Response ────────────────────────────────
        formatted_text = LearningMaterialFormatter.format_content(
            generated_raw_text, output_format
        )

        return {
            "id": new_material.id,
            "content": formatted_text,
            "format": output_format,
            "cached": False,
            "generator_type": generator_type,
            "model": new_material.model,
            "prompt_version": prompt_version,
        }

    async def regenerate_material(
        self,
        db: AsyncSession,
        material_id: uuid.UUID,
        faculty_preferences: Optional[str] = None,
        output_format: str = "markdown",
        changed_by_user_id: Optional[uuid.UUID] = None,
    ) -> Dict[str, Any]:
        """
        Regenerate an existing learning material with updated faculty preferences.
        """
        await self._resolve_dependencies(db)

        # 1. Fetch existing material
        stmt = select(LearningMaterial).where(LearningMaterial.id == material_id)
        res = await db.execute(stmt)
        material = res.scalars().first()
        if not material:
            raise ValueError(f"Learning material not found for ID: {material_id}")

        old_content = material.content

        # 2. Re-run pipeline for generation
        # Fetch topic name & course details
        topic_stmt = select(Topic).where(Topic.id == material.topic_id)
        topic_res = await db.execute(topic_stmt)
        topic = topic_res.scalars().first()

        # Generate fresh content
        result = await self.generate_material(
            db=db,
            course_id=material.course_id,
            topic_id=material.topic_id,
            generator_type=material.generator_type,
            faculty_preferences=faculty_preferences,
            output_format="markdown", # keep raw markdown in database
            created_by=material.created_by,
        )

        fresh_content = result["content"]

        # 3. Log historical revision
        material.content = fresh_content
        material.updated_at = datetime.utcnow()
        await self.history_service.log_revision(
            db=db,
            material=material,
            old_content=old_content,
            changed_by_user_id=changed_by_user_id or material.created_by,
            reason=f"Regenerated with preferences: {faculty_preferences}" if faculty_preferences else None,
        )

        # 4. Format output
        formatted_text = LearningMaterialFormatter.format_content(
            fresh_content, output_format
        )

        return {
            "id": material.id,
            "content": formatted_text,
            "format": output_format,
            "cached": False,
            "generator_type": material.generator_type,
            "model": material.model,
            "prompt_version": material.prompt_version,
        }
