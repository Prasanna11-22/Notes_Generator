"""
Assignment and Learning Activity Generation Orchestrator Service.
"""

import json
import re
from typing import Any, Dict, List, Optional
import uuid
from loguru import logger
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.curriculum import Course, Topic, CourseOutcome
from app.models.assignment import Assignment
from app.services.retriever import RetrieverService
from app.services.prompt_builder import PromptBuilderService
from app.services.llm_orchestrator import LLMOrchestratorService
from app.services.assignment.factory import GenerationStrategyFactory
from app.services.assignment.validator import AssignmentValidator
from app.services.assignment.rubric import RubricPreparationService
from app.services.assignment.blueprint import AssignmentBlueprintService


class AssignmentOrchestratorService:
    """
    Main orchestration service coordinating the end-to-end assignment 
    and learning activity generation pipeline.
    """

    def __init__(
        self,
        retriever_service: Optional[RetrieverService] = None,
        prompt_builder_service: Optional[PromptBuilderService] = None,
        llm_orchestrator_service: Optional[LLMOrchestratorService] = None,
    ) -> None:
        self.retriever_service = retriever_service
        self.prompt_builder_service = prompt_builder_service
        self.llm_orchestrator = llm_orchestrator_service or LLMOrchestratorService()

    async def _resolve_dependencies(self, db: AsyncSession) -> None:
        """Resolve database-dependent services lazily."""
        if not self.retriever_service:
            self.retriever_service = RetrieverService(db)
        if not self.prompt_builder_service:
            self.prompt_builder_service = PromptBuilderService(db)

    async def generate_assignment(
        self,
        db: AsyncSession,
        course_id: uuid.UUID,
        topic_id: uuid.UUID,
        generator_type: str,
        bloom_level: str,
        difficulty: str,
        marks: int,
        knowledge_level: Optional[str] = None,
        teaching_style: Optional[str] = None,
        pedagogical_approach: Optional[str] = None,
        faculty_preferences: Optional[str] = None,
        created_by: Optional[uuid.UUID] = None,
    ) -> Assignment:
        """
        Execute the full assignment/activity generation pipeline.
        """
        await self._resolve_dependencies(db)

        # 1. Resolve generator strategy to validate input type
        generator = GenerationStrategyFactory.get_generator(generator_type)
        logger.info(
            "AssignmentOrchestratorService | Strategy resolved: {} for type: {}",
            generator.__class__.__name__,
            generator_type,
        )

        # Cache: Check if an identical assignment already exists in the database
        existing_cache_stmt = select(Assignment).where(
            Assignment.course_id == course_id,
            Assignment.topic_id == topic_id,
            Assignment.generator_type == generator_type,
            Assignment.bloom_level == bloom_level.capitalize(),
            Assignment.difficulty == difficulty.capitalize(),
            Assignment.marks == marks,
        )
        existing_cache_res = await db.execute(existing_cache_stmt)
        cached_assignment = existing_cache_res.scalars().first()
        if cached_assignment:
            logger.info("AssignmentOrchestratorService | Cache Hit | ID: {}", cached_assignment.id)
            return cached_assignment

        # 2. Query & Validate Curriculum metadata
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

        # Load existing assignments for duplicate detection Jaccard check
        existing_stmt = select(Assignment.content).where(Assignment.topic_id == topic_id)
        existing_res = await db.execute(existing_stmt)
        existing_contents = list(existing_res.scalars().all())

        # 3. Assessment Blueprint Calculation
        blueprint_dist = AssignmentBlueprintService.calculate_marks_distribution(marks, bloom_level)
        logger.info("AssignmentOrchestratorService | Blueprint calculated: {}", blueprint_dist)

        # 4. Retrieve Context from vector database
        retrieval_query = f"{topic.topic_name} {topic.description or ''}".strip()
        retrieved_data = await self.retriever_service.retrieve_context(
            query=retrieval_query,
            limit=5,
            filters={"bloom_level": bloom_level},
            relevance_threshold=0.1,
        )
        
        chunks = []
        for c in retrieved_data.get("chunks", []):
            chunks.append({
                "chunk_id": str(c["chunk_id"]),
                "text": c["text"],
                "score": c.get("score", 0.9),
            })

        # 5. Map default prompt seed type
        is_activity = "activity" in generator_type.lower() or "activities" in generator_type.lower()
        generation_type_key = "Class Activities" if is_activity else "Assignments"

        # Append JSON payload structure instructions into preferences to enforce standard formatting
        json_instructions = (
            "IMPORTANT: You MUST return a single JSON object. Do not include markdown code block formatting in your response. "
            "The JSON object must have exactly two root keys:\n"
            '1. "content": A markdown string representing the assignment question(s) or classroom activity guide.\n'
            '2. "rubric": A JSON object containing the grading criteria. It must have exactly these keys:\n'
            '   - "assessment_criteria": List of grading criteria strings.\n'
            '   - "expected_learning_outcomes": List of learning outcomes strings.\n'
            '   - "evaluation_guidelines": Detailed scoring instructions.\n'
            '   - "mark_distribution": Dict mapping task sections to integer marks.\n'
            '   - "suggested_solution_outline": List of solution outlines or suggested answers.\n'
            f"Please write the questions to sum to exactly {marks} marks matching this blueprint distribution: {blueprint_dist}."
        )
        combined_prefs = f"{json_instructions}\n{faculty_preferences or ''}".strip()

        # 6. Build hydrated prompt
        prompt_payload = await self.prompt_builder_service.build_prompt(
            generation_type=generation_type_key,
            retrieved_chunks=chunks,
            topic=topic.topic_name,
            course=course.course_title,
            course_outcomes=co_joined,
            unit=unit.title,
            bloom_distribution=bloom_level,
            knowledge_level=knowledge_level,
            teaching_style=teaching_style,
            pedagogical_approach=pedagogical_approach,
            difficulty=difficulty,
            faculty_preferences=combined_prefs,
        )

        # 7. Call LLM
        llm_response = await self.llm_orchestrator.generate(
            prompt=prompt_payload["full_prompt"],
            system_prompt=prompt_payload["system_prompt"],
            options={"temperature": 0.3},
            require_json=True,
        )
        raw_text = llm_response["text"]

        # Parse JSON output
        parsed_payload = self._parse_json_response(raw_text)
        content_text = parsed_payload.get("content") or ""
        rubric_dict = parsed_payload.get("rubric") or {}

        if not content_text:
            raise ValueError("LLM response did not generate 'content' text.")

        # 8. Perform educational validations
        AssignmentValidator.validate_educational_alignment(
            content=content_text,
            topic=topic.topic_name,
            bloom_level=bloom_level,
            difficulty=difficulty,
            course_outcomes=[co.description for co in course_outcomes] if course_outcomes else None,
            pedagogical_approach=pedagogical_approach,
            teaching_style=teaching_style,
        )
        RubricPreparationService.validate_rubric_structure(rubric_dict)
        AssignmentValidator.check_duplicate(content_text, existing_contents)

        # 9. Formatting: standard export format with embedded rubric block
        rubric_markdown = RubricPreparationService.format_rubric_to_markdown(rubric_dict)
        formatted_content = f"{content_text.strip()}\n\n---\n\n{rubric_markdown}"

        # 10. Create and persist the Assignment record
        new_assignment = Assignment(
            course_id=course_id,
            topic_id=topic_id,
            generator_type=generator_type,
            marks=marks,
            difficulty=difficulty.capitalize(),
            bloom_level=bloom_level.capitalize(),
            prompt_version="v1.0",
            model_version=llm_response.get("model", "gemma3:4b"),
            content=formatted_content,
            rubric=rubric_dict,
            created_by=created_by or uuid.UUID("00000000-0000-0000-0000-000000000000"),
        )
        db.add(new_assignment)
        await db.flush()

        return new_assignment

    def _parse_json_response(self, text: str) -> Dict[str, Any]:
        """Parse structured json output from LLM."""
        cleaned = text.strip()
        if cleaned.startswith("```json"):
            cleaned = cleaned[7:]
        elif cleaned.startswith("```"):
            cleaned = cleaned[3:]
        if cleaned.endswith("```"):
            cleaned = cleaned[:-3]
        cleaned = cleaned.strip()

        try:
            return json.loads(cleaned)
        except Exception as exc:
            # Fallback regex search for JSON block
            match = re.search(r"\{.*\}", cleaned, re.DOTALL)
            if match:
                try:
                    return json.loads(match.group(0))
                except Exception:
                    pass
            raise ValueError(f"Could not parse valid Assignment JSON response from LLM: {str(exc)}")
