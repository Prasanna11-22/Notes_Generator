"""
Validation Service for Assignment and Activity Quality.
"""

import re
from typing import List


class AssignmentValidator:
    """
    Validates assignments and activities for structural integrity and curriculum alignment.
    """

    BLOOM_VERBS = {
        "remember": ["define", "recall", "list", "name", "state", "identify", "memorize", "repeat", "what", "which"],
        "understand": ["explain", "describe", "summarize", "discuss", "classify", "locate", "translate", "why", "how"],
        "apply": ["apply", "solve", "implement", "calculate", "use", "demonstrate", "illustrate", "run", "code"],
        "analyze": ["analyze", "compare", "contrast", "differentiate", "distinguish", "examine", "model", "diagram"],
        "evaluate": ["evaluate", "judge", "assess", "critique", "defend", "justify", "rate", "verify"],
        "create": ["create", "design", "construct", "develop", "generate", "write", "formulate", "build", "project"],
    }

    @classmethod
    def validate_educational_alignment(
        cls,
        content: str,
        topic: str,
        bloom_level: str,
        difficulty: str,
        course_outcomes: List[str] | None = None,
        pedagogical_approach: str | None = None,
        teaching_style: str | None = None,
    ) -> None:
        """
        Validate syllabus topic, Bloom, CO, pedagogy, and teaching style alignments.
        """
        if not content or not content.strip():
            raise ValueError("Assignment content is empty.")

        text_lower = content.lower()

        # 1. Topic coverage check
        topic_words = [w.lower() for w in re.findall(r"\w+", topic) if len(w) > 3]
        if topic_words:
            matched = False
            for w in topic_words:
                stem_w = w[:-1] if w.endswith("s") and len(w) > 4 else w
                if w in text_lower or stem_w in text_lower:
                    matched = True
                    break
            if not matched:
                raise ValueError(f"Content alignment check failed: The generated text does not reference key terms from topic '{topic}'.")

        # 2. Bloom verb alignment check
        level_key = bloom_level.lower().strip()
        if level_key in cls.BLOOM_VERBS:
            target_verbs = cls.BLOOM_VERBS[level_key]
            has_verb = False
            for verb in target_verbs:
                pattern = rf"\b{verb}\w*\b"
                if re.search(pattern, text_lower):
                    has_verb = True
                    break
            if not has_verb:
                raise ValueError(
                    f"Bloom taxonomy alignment check failed: Verb usage in assignment does not align "
                    f"with target cognitive level '{bloom_level}'."
                )

        # 3. Course Outcomes keyword overlap check
        if course_outcomes:
            for outcome in course_outcomes:
                outcome_words = [w.lower() for w in re.findall(r"\w+", outcome) if len(w) > 4]
                if outcome_words:
                    overlap = []
                    for w in outcome_words:
                        stem_w = w[:-1] if w.endswith("s") and len(w) >= 4 else w
                        if w in text_lower or stem_w in text_lower:
                            overlap.append(w)
                    if not overlap:
                        raise ValueError(
                            f"Course Outcome alignment check failed: Content does not exhibit keywords "
                            f"corresponding to CO: '{outcome}'."
                        )

        # 4. Pedagogy Alignment Check
        if pedagogical_approach:
            ped_lower = pedagogical_approach.lower().strip()
            # Check if pedagogical approach keywords are present (e.g. inquiry, think, pair, share, collaborative, team, project)
            ped_words = [w for w in re.findall(r"\w+", ped_lower) if len(w) > 3]
            if ped_words:
                has_ped = False
                for w in ped_words:
                    if w in text_lower:
                        has_ped = True
                        break
                if not has_ped:
                    raise ValueError(
                        f"Pedagogical alignment check failed: The content does not reflect the "
                        f"targeted pedagogical approach '{pedagogical_approach}'."
                    )

        # 5. Teaching Style Alignment Check
        if teaching_style:
            style_lower = teaching_style.lower().strip()
            style_words = [w for w in re.findall(r"\w+", style_lower) if len(w) > 3]
            if style_words:
                has_style = False
                for w in style_words:
                    if w in text_lower:
                        has_style = True
                        break
                if not has_style:
                    raise ValueError(
                        f"Teaching style alignment check failed: The content does not match the "
                        f"instructor's requested teaching style '{teaching_style}'."
                    )

    @classmethod
    def check_duplicate(cls, new_content: str, existing_contents: List[str], threshold: float = 0.6) -> None:
        """
        Compare newly generated assignment against existing assignments.
        """
        new_words = set(cls._tokenize(new_content))
        if not new_words:
            return

        for existing in existing_contents:
            existing_words = set(cls._tokenize(existing))
            if not existing_words:
                continue

            intersection = new_words.intersection(existing_words)
            union = new_words.union(existing_words)
            similarity = len(intersection) / len(union)

            if similarity > threshold:
                raise ValueError(
                    f"Duplicate check failed: Newly generated assignment is too similar to "
                    f"an existing assignment (similarity: {similarity:.2f})."
                )

    @staticmethod
    def _tokenize(text: str) -> List[str]:
        """Tokenize text into lowercased alphanumeric words, stripping punctuation."""
        return [w.lower() for w in re.findall(r"\w+", text) if len(w) > 2]
