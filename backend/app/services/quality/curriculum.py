"""
Curriculum and Course Outcome Validation Services.
"""

from typing import List, Optional


class CurriculumValidationService:
    """
    Validates alignment of generated materials with Course, Unit, and Topic metadata.
    """

    @classmethod
    def validate_curriculum_coverage(
        cls,
        content: str,
        topic_name: str,
        topic_description: Optional[str] = None,
        unit_title: Optional[str] = None,
    ) -> dict:
        """
        Analyze coverage of target curriculum topics within the generated content.
        """
        content_lower = content.lower()
        topic_words = [w.lower() for w in topic_name.split() if len(w) > 3]
        
        # Calculate coverage ratio
        matched_words = sum(1 for w in topic_words if w in content_lower)
        coverage_score = (matched_words / len(topic_words) * 100.0) if topic_words else 100.0
        
        # Unit references
        unit_matched = False
        if unit_title:
            unit_words = [w.lower() for w in unit_title.split() if len(w) > 3]
            unit_matched = any(w in content_lower for w in unit_words) if unit_words else True

        passed = coverage_score >= 60.0
        
        return {
            "passed": passed,
            "score": coverage_score,
            "details": {
                "matched_topic_keywords": matched_words,
                "total_topic_keywords": len(topic_words),
                "unit_referenced": unit_matched,
            }
        }


class CourseOutcomeValidationService:
    """
    Validates Course Outcome (CO) mapping and overlap within educational content.
    """

    @classmethod
    def validate_course_outcome_overlap(cls, content: str, course_outcomes: List[str]) -> dict:
        """
        Calculate semantic mapping alignment against course outcome statements.
        """
        if not course_outcomes:
            return {"passed": True, "score": 100.0, "details": "No course outcomes configured."}

        content_lower = content.lower()
        matched_cos = []
        scores = []

        for co in course_outcomes:
            co_lower = co.lower()
            co_words = [w for w in co_lower.split() if len(w) > 4]
            if not co_words:
                scores.append(100.0)
                continue
            matches = sum(1 for w in co_words if w in content_lower)
            overlap_pct = (matches / len(co_words)) * 100.0
            scores.append(overlap_pct)
            if overlap_pct >= 20.0:  # threshold for partial overlap
                matched_cos.append(co)

        avg_score = sum(scores) / len(scores) if scores else 100.0
        passed = any(s >= 30.0 for s in scores)  # passes if at least one outcome is actively referenced

        return {
            "passed": passed,
            "score": avg_score,
            "details": {
                "total_configured_cos": len(course_outcomes),
                "matched_cos_count": len(matched_cos),
                "matched_cos": matched_cos,
            }
        }
