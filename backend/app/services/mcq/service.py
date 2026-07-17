"""
MCQ Generation Orchestrator Service.
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
from app.models.mcq import MCQQuestion
from app.services.retriever import RetrieverService
from app.services.prompt_builder import PromptBuilderService
from app.services.llm_orchestrator import LLMOrchestratorService
from app.services.mcq.blueprint import AssessmentBlueprintService
from app.services.mcq.factory import GenerationStrategyFactory
from app.services.mcq.validator import MCQValidator
from app.services.mcq.distractor_analyzer import DistractorAnalyzer
from app.services.mcq.duplicate_detector import MCQDuplicateDetector
from app.services.mcq.difficulty_calibrator import DifficultyCalibrator


class MCQOrchestratorService:
    """
    Main orchestration service coordinating the end-to-end multiple choice question 
    generation pipeline.
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

    async def generate_mcqs(
        self,
        db: AsyncSession,
        course_id: uuid.UUID,
        topic_id: uuid.UUID,
        bloom_distribution: Dict[str, float],
        difficulty: str,
        number_of_questions: int,
        faculty_preferences: Optional[str] = None,
        created_by: Optional[uuid.UUID] = None,
    ) -> List[MCQQuestion]:
        """
        Execute the full MCQ generation pipeline.
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

        # ── 2. Assessment Blueprint Calculation ───────────────────────────────
        blueprint = AssessmentBlueprintService.calculate_distribution(
            total_questions=number_of_questions,
            distribution=bloom_distribution
        )
        logger.info(
            "MCQOrchestratorService | Blueprint calculated: {} | total={}",
            blueprint,
            number_of_questions,
        )

        # Load existing questions for duplicate detection
        stmt = select(MCQQuestion.question_text).where(MCQQuestion.topic_id == topic_id)
        res = await db.execute(stmt)
        existing_stems = list(res.scalars().all())

        generated_questions: List[MCQQuestion] = []
        prompt_version = "v1.0"

        # ── 3. Generation Loop per Bloom Level ────────────────────────────────
        for bloom_level, count in blueprint.items():
            if count <= 0:
                continue

            # Resolve generator strategy (verifies Bloom level validity)
            generator = GenerationStrategyFactory.get_generator(bloom_level)

            # Retrieve context from Knowledge Store
            retrieval_query = f"{topic.topic_name} {topic.description or ''}".strip()
            retrieved_data = await self.retriever_service.retrieve_context(
                query=retrieval_query,
                limit=5,
                filters={"bloom_level": bloom_level},
                relevance_threshold=0.1,
            )

            # Map chunks list for prompt builder
            chunks = []
            for c in retrieved_data.get("chunks", []):
                chunks.append({
                    "chunk_id": str(c["chunk_id"]),
                    "text": c["text"],
                    "score": c.get("score", 0.9),
                })

            # Hydrate prompt template. 
            # We append the exact count instructions into faculty preferences to force correct generation size.
            count_instruction = f"Generate exactly {count} distinct questions."
            combined_prefs = f"{count_instruction} {faculty_preferences or ''}".strip()

            prompt_payload = await self.prompt_builder_service.build_prompt(
                generation_type="MCQs",
                retrieved_chunks=chunks,
                topic=topic.topic_name,
                course=course.course_title,
                course_outcomes=co_joined,
                unit=unit.title,
                bloom_distribution=bloom_level,
                faculty_preferences=combined_prefs,
            )

            # Call LLM Orchestrator
            llm_response = await self.llm_orchestrator.generate(
                prompt=prompt_payload["full_prompt"],
                system_prompt=prompt_payload["system_prompt"],
                options={
                    "temperature": 0.5,
                },
                require_json=True
            )
            raw_text = llm_response["text"]

            # Parse questions
            parsed_questions = self._parse_json_questions(raw_text)
            
            # If the LLM generated fewer questions than requested, we log a warning but process what we got.
            for q_obj in parsed_questions:
                # Normalize keys to lowercase for robust lookup
                normalized_keys = {k.lower().replace("_", ""): k for k in q_obj.keys()}
                
                # Extract question stem
                stem = None
                for stem_key in ("question", "questiontext", "stem"):
                    if stem_key in normalized_keys:
                        stem = q_obj[normalized_keys[stem_key]]
                        break
                if not stem:
                    stem = q_obj.get("question") or q_obj.get("question_text")
                
                # Extract options
                opts = None
                for opts_key in ("options", "choices", "distractors"):
                    if opts_key in normalized_keys:
                        opts = q_obj[normalized_keys[opts_key]]
                        break
                if not opts:
                    opts = q_obj.get("options")
                        
                # Extract correct answer
                correct = None
                for correct_key in ("correctanswer", "answer", "correctkey"):
                    if correct_key in normalized_keys:
                        correct = q_obj[normalized_keys[correct_key]]
                        break
                if not correct:
                    correct = q_obj.get("correct_answer") or q_obj.get("answer")

                # Extract explanation
                explanation = ""
                for exp_key in ("explanation", "rationale", "reason"):
                    if exp_key in normalized_keys:
                        explanation = q_obj[normalized_keys[exp_key]]
                        break
                if not explanation:
                    explanation = q_obj.get("explanation") or ""

                # Perform pipeline validation checks
                MCQValidator.validate_mcq_structure(stem, opts, correct)
                MCQValidator.validate_educational_alignment(
                    question_text=stem,
                    topic=topic.topic_name,
                    bloom_level=bloom_level,
                    course_outcomes=[co.description for co in course_outcomes] if course_outcomes else None
                )
                DistractorAnalyzer.analyze_distractors(opts)
                MCQDuplicateDetector.check_duplicate(stem, existing_stems)
                DifficultyCalibrator.calibrate_difficulty(stem, bloom_level, difficulty)

                # Prevent duplicate generation in the same batch
                existing_stems.append(stem)

                # Save new question object to session
                new_q = MCQQuestion(
                    course_id=course_id,
                    topic_id=topic_id,
                    question_text=stem,
                    options=opts,
                    correct_answer=correct,
                    explanation=explanation,
                    bloom_level=bloom_level,
                    difficulty=difficulty.capitalize(),
                    prompt_version=prompt_version,
                    model_version=llm_response.get("model", "gemma3:4b"),
                    created_by=created_by or uuid.UUID("00000000-0000-0000-0000-000000000000"),
                )
                db.add(new_q)
                generated_questions.append(new_q)

        await db.flush()
        return generated_questions

    def _parse_json_questions(self, text: str) -> List[Dict[str, Any]]:
        """
        Extract and parse a JSON array of questions from raw LLM text.
        """
        # Clean text
        cleaned = text.strip()
        
        # Strip markdown code fencing if present
        if cleaned.startswith("```json"):
            cleaned = cleaned[7:]
        elif cleaned.startswith("```"):
            cleaned = cleaned[3:]
        if cleaned.endswith("```"):
            cleaned = cleaned[:-3]
        cleaned = cleaned.strip()

        try:
            parsed = json.loads(cleaned)
            if isinstance(parsed, list):
                return parsed
            elif isinstance(parsed, dict):
                # If the LLM returned a single question object, wrap it
                if "question" in parsed or "question_text" in parsed:
                    return [parsed]
                # If wrapped inside an envelope, e.g. {"questions": [...]}
                for k, v in parsed.items():
                    if isinstance(v, list):
                        return v
            return []
        except Exception as exc:
            logger.error("MCQOrchestratorService | JSON parsing failed: {}. Raw: {}", str(exc), text)
            # Try to regex-extract a JSON array block
            match = re.search(r"\[\s*\{.*\}\s*\]", cleaned, re.DOTALL)
            if match:
                try:
                    return json.loads(match.group(0))
                except Exception:
                    pass
            raise ValueError(f"Could not parse valid MCQ questions JSON from LLM: {str(exc)}")
