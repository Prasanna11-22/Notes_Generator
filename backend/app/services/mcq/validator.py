"""
Validation Service for MCQ Quality.
"""

import re
from typing import Dict, List


class MCQValidator:
    """
    Validates MCQ structures, answer keys, option mapping, and syllabus alignment.
    """

    BLOOM_VERBS = {
        "remember": ["define", "recall", "list", "name", "state", "identify", "memorize", "repeat", "what", "which"],
        "understand": ["explain", "describe", "summarize", "discuss", "classify", "locate", "translate", "why", "how"],
        "apply": ["apply", "solve", "implement", "calculate", "use", "demonstrate", "illustrate", "run", "code"],
        "analyze": ["analyze", "compare", "contrast", "differentiate", "distinguish", "examine", "model", "diagram"],
        "evaluate": ["evaluate", "judge", "assess", "critique", "defend", "justify", "rate", "verify"],
        "create": ["create", "design", "construct", "develop", "generate", "write", "formulate", "build"],
    }

    @classmethod
    def validate_mcq_structure(cls, question_text: str, options: Dict[str, str], correct_answer: str) -> None:
        """
        Validate basic structural layout of an MCQ.
        """
        if not question_text or not question_text.strip():
            raise ValueError("MCQ stem is empty.")

        if not options or len(options) < 2:
            raise ValueError("MCQ must have at least 2 options (choices).")

        # Check options aren't empty
        for key, val in options.items():
            if not val or not val.strip():
                raise ValueError(f"Option choice '{key}' is empty.")

        # Check correct answer is present in options keys
        if correct_answer not in options:
            raise ValueError(
                f"Invalid answer key: '{correct_answer}'. "
                f"Must match one of the options keys: {list(options.keys())}."
            )

    @classmethod
    def validate_educational_alignment(
        cls,
        question_text: str,
        topic: str,
        bloom_level: str,
        course_outcomes: List[str] | None = None,
    ) -> None:
        """
        Validate syllabus topic coverage and active Bloom verb alignment.
        """
        text_lower = question_text.lower()

        # 1. Topic coverage
        topic_words = [w.lower() for w in re.findall(r"\w+", topic) if len(w) > 3]
        if topic_words:
            matched = False
            for w in topic_words:
                stem_w = w[:-1] if w.endswith("s") and len(w) > 4 else w
                if w in text_lower or stem_w in text_lower:
                    matched = True
                    break
            if not matched:
                raise ValueError(f"MCQ validation failed: Stem does not cover the requested topic '{topic}'.")

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
                    f"MCQ validation failed: Verb usage in question does not align "
                    f"with cognitive Bloom level '{bloom_level}'."
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
                            f"MCQ validation failed: Question is not aligned "
                            f"with Course Outcome: '{outcome}'."
                        )
