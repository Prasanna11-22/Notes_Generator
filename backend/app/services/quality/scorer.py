"""
Quality and Confidence Scoring Services.
"""

from typing import Dict, Any


class EducationalQualityScoringService:
    """
    Computes a weighted overall quality score from individual sub-validation outcomes.
    """

    @classmethod
    def calculate_overall_score(cls, validation_results: Dict[str, Any]) -> float:
        """
        Aggregate scores with standard academic weight allocations:
        - Curriculum Score: 15%
        - Course Outcomes Score: 10%
        - Bloom Taxonomy Score: 10%
        - Difficulty Score: 10%
        - Faculty Preference Match: 15%
        - Readability Index: 10%
        - Consistency & Duplication: 10%
        - Educational Completeness: 10%
        - Terminology Accuracy: 5%
        - Image Relevance: 5%
        """
        weights = {
            "curriculum": 0.15,
            "course_outcomes": 0.10,
            "bloom": 0.10,
            "difficulty": 0.10,
            "preferences": 0.15,
            "readability": 0.10,
            "consistency": 0.10,
            "completeness": 0.10,
            "terminology": 0.05,
            "image_relevance": 0.05,
        }

        weighted_sum = 0.0
        total_weight = 0.0

        for key, weight in weights.items():
            result = validation_results.get(key, {})
            if not result:
                # If a sub-score is missing (e.g. image_relevance is optional), skip it
                continue
            
            score = result.get("score", 100.0)
            weighted_sum += score * weight
            total_weight += weight

        if total_weight == 0.0:
            return 100.0

        overall_score = weighted_sum / total_weight
        return round(max(0.0, min(100.0, overall_score)), 2)


class ConfidenceScoringService:
    """
    Evaluates confidence score based on the quantity and severity of validation failures.
    """

    @classmethod
    def calculate_confidence_score(cls, validation_results: Dict[str, Any]) -> float:
        """
        Confidence begins at 100.0 and decays based on failed validation blocks:
        - Critical failures (Curriculum, Bloom, Outcomes) reduce confidence by 20 points each.
        - Non-critical failures (Readability, Consistency, Preferences, Completeness, Terminology) reduce confidence by 10 points each.
        """
        confidence = 100.0

        critical_keys = ["curriculum", "course_outcomes", "bloom"]
        non_critical_keys = ["difficulty", "preferences", "consistency", "completeness", "terminology"]

        for key in critical_keys:
            res = validation_results.get(key, {})
            if res and not res.get("passed", True):
                confidence -= 20.0

        for key in non_critical_keys:
            res = validation_results.get(key, {})
            if res and not res.get("passed", True):
                confidence -= 10.0

        return max(0.0, min(100.0, confidence))
