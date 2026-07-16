"""
Prompt Builder Service.

Orchestrates hydration, optimization, truncation, validation, and assembly
of production-grade educational prompts.

Prompt assembly order (deterministic):
    System Prompt
    ↓ Instruction Block
    ↓ Educational Constraints
    ↓ Retrieved Context
    ↓ Faculty Preferences
    ↓ Output Format
"""

from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.prompt_template import PromptTemplateRepository
from app.services.token_estimator import TokenEstimatorService
from app.services.prompt_optimization import PromptOptimizationService
from app.services.prompt_validation import PromptValidationService


class PromptBuilderService:
    """
    Orchestrator that compiles, validates, optimizes, and trims LLM prompts.

    Responsibilities (each delegated to a focused sub-service):
    - Template hydration via ``PromptTemplateRepository``.
    - Context prioritisation and token-budget truncation.
    - Whitespace / duplicate-sentence optimisation.
    - Security scanning (injection detection, control-char sanitisation).
    - Token estimation and size validation.
    """

    def __init__(
        self,
        session: AsyncSession,
        template_repo: PromptTemplateRepository | None = None,
        estimator: TokenEstimatorService | None = None,
        optimizer: PromptOptimizationService | None = None,
        validator: PromptValidationService | None = None,
    ) -> None:
        self._session = session
        self._template_repo = template_repo or PromptTemplateRepository(session)
        self._estimator = estimator or TokenEstimatorService()
        self._optimizer = optimizer or PromptOptimizationService()
        self._validator = validator or PromptValidationService(self._estimator)

    async def build_prompt(
        self,
        generation_type: str,
        retrieved_chunks: list[dict],
        topic: str,
        course: str,
        course_outcomes: str,
        unit: str,
        bloom_distribution: str,
        knowledge_level: str | None = None,
        teaching_style: str | None = None,
        pedagogical_approach: str | None = None,
        difficulty: str | None = None,
        faculty_preferences: str | None = None,
        max_tokens: int = 8192,
    ) -> dict:
        """
        Hydrate templates, compress/trim context chunks according to token budget,
        validate structures, and return a finalized payload suitable for the LLM.

        :param generation_type: Generation type key that maps to a ``PromptTemplate``.
        :param retrieved_chunks: Ordered list of retrieved context dicts
            (``chunk_id``, ``text``, ``score``).
        :param topic: Topic to generate content for.
        :param course: Course name/code (metadata only, used for hydration).
        :param course_outcomes: Course-level learning outcomes (COs).
        :param unit: Syllabus unit identifier.
        :param bloom_distribution: Bloom taxonomy distribution string.
        :param knowledge_level: Optional knowledge level label.
        :param teaching_style: Optional instructor teaching-style label.
        :param pedagogical_approach: Optional pedagogical framework label.
        :param difficulty: Optional difficulty tier (Easy / Medium / Hard).
        :param faculty_preferences: Optional free-text faculty customisations.
        :param max_tokens: Hard cap on total prompt token budget.
        :returns: Structured prompt payload dict.
        :raises ValueError: On missing template, validation failure, or
            security violation.
        """
        logger.info(
            "PromptBuilderService.build_prompt | type={} topic={!r} course={!r} "
            "unit={!r} max_tokens={}",
            generation_type,
            topic,
            course,
            unit,
            max_tokens,
        )

        # ── 0. Security: sanitize and scan free-text inputs before any use ────
        topic = self._validator.sanitize_and_check(topic, "topic")
        course_outcomes = self._validator.sanitize_and_check(course_outcomes, "course_outcomes")
        bloom_distribution = self._validator.sanitize_and_check(
            bloom_distribution, "bloom_distribution"
        )
        if faculty_preferences:
            faculty_preferences = self._validator.sanitize_and_check(
                faculty_preferences, "faculty_preferences"
            )

        # ── 1. Retrieve template ──────────────────────────────────────────────
        template = await self._template_repo.get_by_generation_type(generation_type)
        if not template:
            raise ValueError(
                f"No prompt template found for generation type: '{generation_type}'"
            )
        logger.debug("PromptBuilderService | using template: {!r}", template.name)

        # ── 2. Apply defaults for optional parameters ─────────────────────────
        knowledge_level = knowledge_level or "General"
        teaching_style = teaching_style or "Standard Academic"
        pedagogical_approach = pedagogical_approach or "Constructivist"
        difficulty = difficulty or "Medium"
        faculty_preferences = faculty_preferences or "None"

        # ── 3. Prioritise & optimise retrieved chunks (score-descending) ──────
        sorted_chunks = sorted(
            retrieved_chunks, key=lambda x: x.get("score", 0.0), reverse=True
        )
        optimized_chunks = []
        for chunk in sorted_chunks:
            raw_text = chunk.get("text", "") or ""
            text_opt = self._optimizer.optimize_context(raw_text)
            optimized_chunks.append(
                {
                    "chunk_id": chunk.get("chunk_id"),
                    "text": text_opt,
                    "score": chunk.get("score", 0.0),
                    "original": chunk,
                }
            )

        # ── 4. Hydrate template variables ─────────────────────────────────────
        base_variables = {
            "topic": topic,
            "course": course,
            "course_outcomes": course_outcomes,
            "unit": unit,
            "bloom_distribution": bloom_distribution,
            "knowledge_level": knowledge_level,
            "teaching_style": teaching_style,
            "pedagogical_approach": pedagogical_approach,
            "difficulty": difficulty,
            "faculty_preferences": faculty_preferences,
            "educational_constraints": template.educational_constraints,
        }

        def safe_format(template_str: str) -> str:
            """Substitute only keys that are present in the template string.
            Falls back to manual string replacement on any format error."""
            fmt_dict = {
                k: v for k, v in base_variables.items() if f"{{{k}}}" in template_str
            }
            try:
                return template_str.format(**fmt_dict)
            except Exception:
                result = template_str
                for k, v in fmt_dict.items():
                    result = result.replace(f"{{{k}}}", str(v))
                return result

        sys_hydrated = safe_format(template.system_prompt)
        inst_hydrated = safe_format(template.instruction_prompt)
        const_hydrated = safe_format(template.educational_constraints)
        format_hydrated = safe_format(template.output_format)

        # ── 5. Measure base-prompt token footprint ────────────────────────────
        base_prompt_text = (
            f"{sys_hydrated}\n"
            f"Instructions:\n{inst_hydrated}\n"
            f"Educational Constraints:\n{const_hydrated}\n"
            f"Faculty Preferences: {faculty_preferences}\n"
            f"Output Format:\n{format_hydrated}"
        )
        base_tokens = self._estimator.estimate_tokens(base_prompt_text)
        logger.debug(
            "PromptBuilderService | base_tokens={} budget_remaining={}",
            base_tokens,
            max_tokens - base_tokens,
        )

        # ── 6. Fit context within remaining token budget (priority truncation) ─
        selected_chunks: list[dict] = []
        context_segments: list[str] = []

        for item in optimized_chunks:
            candidate_segment = (
                f"--- Chunk {len(selected_chunks) + 1} ---\n{item['text']}\n"
            )
            prospective_context = "\n".join(context_segments + [candidate_segment])
            prospective_tokens = base_tokens + self._estimator.estimate_tokens(
                prospective_context
            )
            if prospective_tokens <= max_tokens:
                selected_chunks.append(item["original"])
                context_segments.append(candidate_segment)
            else:
                logger.debug(
                    "PromptBuilderService | token budget exhausted at chunk index {}",
                    len(selected_chunks),
                )
                break

        final_context_string = "\n".join(context_segments)
        logger.info(
            "PromptBuilderService | chunks_selected={} / chunks_available={}",
            len(selected_chunks),
            len(optimized_chunks),
        )

        # ── 7. Validate inputs (including CO check and injection scan) ─────────
        self._validator.validate_inputs(
            retrieved_context=final_context_string,
            topic=topic,
            bloom_distribution=bloom_distribution,
            educational_constraints=const_hydrated,
            faculty_preferences=faculty_preferences,
            course_outcomes=course_outcomes,
        )

        # ── 8. Assemble final prompt in deterministic order ────────────────────
        full_prompt = (
            f"{sys_hydrated}\n"
            f"Instructions:\n{inst_hydrated}\n"
            f"Educational Constraints:\n{const_hydrated}\n"
            f"Retrieved Context:\n{final_context_string}\n"
            f"Faculty Preferences: {faculty_preferences}\n"
            f"Output Format:\n{format_hydrated}"
        )

        estimated_tokens = self._validator.validate_size(full_prompt, max_tokens)
        logger.info(
            "PromptBuilderService | prompt assembled | estimated_tokens={} template={!r}",
            estimated_tokens,
            template.name,
        )

        return {
            "system_prompt": sys_hydrated,
            "instruction_prompt": inst_hydrated,
            "retrieved_context": final_context_string,
            "full_prompt": full_prompt,
            "generation_type": generation_type,
            "metadata": {
                "topic": topic,
                "course": course,
                "course_outcomes": course_outcomes,
                "unit": unit,
                "bloom_level_distribution": bloom_distribution,
                "knowledge_level": knowledge_level,
                "teaching_style": teaching_style,
                "pedagogical_approach": pedagogical_approach,
                "difficulty": difficulty,
                "faculty_preferences": faculty_preferences,
                "used_template": template.name,
                "chunks_count": len(selected_chunks),
            },
            "estimated_tokens": estimated_tokens,
        }
