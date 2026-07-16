"""
Difficulty Calibration Service for MCQs.
"""

import re


class DifficultyCalibrator:
    """
    Calibrates and validates the cognitive/syntactic difficulty level of generated MCQs.
    """

    EASY_VERBS = ["define", "recall", "list", "name", "state", "identify"]
    HARD_VERBS = ["evaluate", "judge", "critique", "justify", "design", "construct", "formulate", "synthesize"]

    @classmethod
    def calibrate_difficulty(cls, question_text: str, bloom_level: str, requested_difficulty: str) -> str:
        """
        Assess syntactic and cognitive features to determine difficulty (Easy, Medium, Hard).
        
        Verifies consistency with faculty request, raising an error if there is a severe mismatch.
        """
        text_lower = question_text.lower()
        word_count = len(text_lower.split())

        # Determine cognitive complexity score based on Bloom level
        bloom_val = bloom_level.lower().strip()
        
        # Easy triggers: Short question, low-level Bloom
        has_easy_verb = any(v in text_lower for v in cls.EASY_VERBS)
        has_hard_verb = any(v in text_lower for v in cls.HARD_VERBS)
        
        # Calculate calculated difficulty
        if word_count < 15 and (bloom_val in ("remember", "understand") or has_easy_verb) and not has_hard_verb:
            calculated = "Easy"
        elif word_count > 30 or bloom_val in ("evaluate", "create") or has_hard_verb or "scenario" in text_lower:
            calculated = "Hard"
        else:
            calculated = "Medium"

        # Validate consistency with requested difficulty
        # We allow adjacent mismatch (e.g. calculated Medium when requested Easy or Hard is acceptable),
        # but block severe mismatch (e.g. calculated Hard when requested Easy, or calculated Easy when requested Hard).
        req = requested_difficulty.strip().capitalize()
        if (req == "Easy" and calculated == "Hard") or (req == "Hard" and calculated == "Easy"):
            raise ValueError(
                f"Difficulty mismatch: Requested '{requested_difficulty}' but question complexity "
                f"calibrates as '{calculated}' (Word count: {word_count}, Bloom: {bloom_level})."
            )

        return calculated
