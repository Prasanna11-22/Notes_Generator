"""
Bloom's Taxonomy and Difficulty Validation Services.
"""

import re
from typing import List, Dict


class BloomValidationService:
    """
    Validates alignment of cognitive verbs matching Bloom's taxonomy.
    """

    BLOOM_VERBS: Dict[str, List[str]] = {
        "Remember": ["define", "list", "state", "recall", "repeat", "name", "identify", "retrieve"],
        "Understand": ["explain", "describe", "discuss", "summarize", "interpret", "classify", "locate"],
        "Apply": ["apply", "solve", "use", "demonstrate", "illustrate", "execute", "implement", "calculate"],
        "Analyze": ["analyze", "compare", "contrast", "distinguish", "examine", "differentiate", "inspect"],
        "Evaluate": ["evaluate", "judge", "critique", "justify", "defend", "assess", "rate", "appraise"],
        "Create": ["create", "design", "construct", "build", "formulate", "devise", "generate", "project"],
    }

    @classmethod
    def validate_bloom_alignment(cls, content: str, target_bloom: str) -> dict:
        """
        Check if target cognitive level verbs appear in the generated content.
        """
        target = target_bloom.strip().capitalize()
        content_lower = content.lower()

        if target not in cls.BLOOM_VERBS:
            return {"passed": True, "score": 100.0, "details": f"Unknown target Bloom level: {target_bloom}"}

        expected_verbs = cls.BLOOM_VERBS[target]
        matched_verbs = [v for v in expected_verbs if re.search(rf"\b{v}\w*", content_lower)]
        
        # Calculate coverage score
        score = (len(matched_verbs) / len(expected_verbs) * 100.0) if expected_verbs else 100.0
        
        # If any matching cognitive verbs are present, we consider it aligned!
        passed = len(matched_verbs) > 0

        # Map distribution of all bloom levels
        distribution = {}
        for level, verbs in cls.BLOOM_VERBS.items():
            count = sum(1 for v in verbs if re.search(rf"\b{v}\w*", content_lower))
            distribution[level] = count

        return {
            "passed": passed,
            "score": 100.0 if passed else score,
            "details": {
                "matched_target_verbs": matched_verbs,
                "total_target_verbs": len(expected_verbs),
                "bloom_verb_counts": distribution,
            }
        }


class DifficultyValidationService:
    """
    Validates structural and complexity metrics against target difficulty levels.
    """

    @classmethod
    def validate_difficulty_alignment(cls, content: str, target_difficulty: str) -> dict:
        """
        Check indicators of complexity (avg sentence length, sentence count).
        Easy: Short sentences (<15 words), simple verbs.
        Medium: Average sentence length (15-25 words).
        Hard: Long sentences (>25 words), nested structures.
        """
        difficulty = target_difficulty.strip().capitalize()
        
        sentences = [s.strip() for s in re.split(r"[.!?]+", content) if s.strip()]
        if not sentences:
            return {"passed": True, "score": 100.0, "details": "Empty content."}

        word_counts = [len(s.split()) for s in sentences]
        avg_sentence_len = sum(word_counts) / len(sentences)

        # Mapping heuristics
        detected_difficulty = "Medium"
        if avg_sentence_len < 15.0:
            detected_difficulty = "Easy"
        elif avg_sentence_len > 25.0:
            detected_difficulty = "Hard"

        passed = detected_difficulty == difficulty
        # Calculate matching proximity score
        diff_score = 100.0 if passed else 50.0

        return {
            "passed": passed,
            "score": diff_score,
            "details": {
                "average_sentence_length": avg_sentence_len,
                "detected_difficulty": detected_difficulty,
                "target_difficulty": difficulty,
            }
        }
