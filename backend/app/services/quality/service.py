"""
Academic Validation and QA Orchestration Service.
"""

import re
import uuid
from typing import Any, Dict, List, Optional
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.quality import QualityReport
from app.services.quality.curriculum import CurriculumValidationService, CourseOutcomeValidationService
from app.services.quality.bloom import BloomValidationService, DifficultyValidationService
from app.services.quality.style import FacultyPreferenceValidationService
from app.services.quality.metrics import ReadabilityAnalysisService, ConsistencyValidationService
from app.services.quality.scorer import EducationalQualityScoringService, ConfidenceScoringService


class AcademicValidationService:
    """
    Main orchestration service running the entire QA validation pipeline.
    """

    @classmethod
    def validate_completeness(cls, content: str) -> dict:
        """
        Evaluate educational completeness: checks word count, heading structures, 
        and interactive markdown lists.
        """
        words = len(content.split())
        headings = len(re.findall(r"^#+\s+", content, re.MULTILINE))
        lists = len(re.findall(r"^(\*|-|\d+\.)\s+", content, re.MULTILINE))

        score = 0.0
        # 1. Word Count check (Max 40 points)
        if words >= 300:
            score += 40.0
        elif words >= 100:
            score += 20.0
        else:
            score += 5.0

        # 2. Heading presence (Max 30 points)
        if headings >= 3:
            score += 30.0
        elif headings >= 1:
            score += 15.0

        # 3. Interactive lists/bullet formatting (Max 30 points)
        if lists >= 3:
            score += 30.0
        elif lists >= 1:
            score += 15.0

        return {
            "passed": score >= 50.0,
            "score": score,
            "details": {
                "word_count": words,
                "headings_count": headings,
                "markdown_list_items": lists,
            }
        }

    @classmethod
    def validate_terminology_accuracy(cls, content: str, topic_name: str) -> dict:
        """
        Ensure terminology accuracy: checks for placeholder developer strings, 
        and topic keyword consistency.
        """
        content_lower = content.lower()
        score = 100.0

        # Flag placeholder text
        placeholders = ["lorem ipsum", "todo", "placeholder", "fixme", "xyz", "abc"]
        detected = [p for p in placeholders if p in content_lower]
        
        # Deduct points per placeholder occurrence
        score -= len(detected) * 20.0

        # Verify topic name terms are spelled cleanly (no concatenated strings)
        topic_words = [w.lower() for w in topic_name.split() if len(w) > 3]
        misspellings = []
        for word in topic_words:
            # Simple check to verify it isn't embedded incorrectly
            if word not in content_lower:
                misspellings.append(word)
                score -= 10.0

        score = max(0.0, score)
        return {
            "passed": score >= 80.0,
            "score": score,
            "details": {
                "placeholders_found": detected,
                "missing_topic_terms": misspellings,
            }
        }

    @classmethod
    def validate_image_relevance(cls, content: str, image_metadata: Optional[dict] = None) -> dict:
        """
        Analyze image diagram relevance based on overlap with textual notes context.
        """
        if not image_metadata:
            # Default fallback when no image metadata is linked to this run
            return {
                "passed": True,
                "score": 100.0,
                "details": "No image metadata provided for analysis; defaults to pass."
            }

        content_lower = content.lower()
        img_title = image_metadata.get("title", "").lower()
        img_desc = image_metadata.get("description", "").lower()

        img_words = set(re.findall(r"\w+", f"{img_title} {img_desc}"))
        content_words = set(re.findall(r"\w+", content_lower))

        if not img_words:
            return {"passed": True, "score": 100.0, "details": "Image contains no textual metadata."}

        # Calculate overlap
        intersection = img_words.intersection(content_words)
        ratio = len(intersection) / len(img_words)
        score = min(100.0, ratio * 200.0)  # scale factor for overlap

        return {
            "passed": score >= 50.0,
            "score": score,
            "details": {
                "shared_keywords_count": len(intersection),
                "relevance_percentage": score,
            }
        }

    @classmethod
    def run_qa_pipeline(
        cls,
        content: str,
        topic_name: str,
        target_bloom: str,
        target_difficulty: str,
        topic_description: Optional[str] = None,
        unit_title: Optional[str] = None,
        course_outcomes: Optional[List[str]] = None,
        teaching_style: Optional[str] = None,
        expected_length: Optional[int] = None,
        preferred_examples: Optional[str] = None,
        image_metadata: Optional[dict] = None,
    ) -> Dict[str, Any]:
        """
        Execute all validators sequentially and compile scores.
        """
        # 1. Run individual sub-validation checkers
        curriculum_res = CurriculumValidationService.validate_curriculum_coverage(
            content=content,
            topic_name=topic_name,
            topic_description=topic_description,
            unit_title=unit_title,
        )

        co_res = CourseOutcomeValidationService.validate_course_outcome_overlap(
            content=content,
            course_outcomes=course_outcomes or [],
        )

        bloom_res = BloomValidationService.validate_bloom_alignment(
            content=content,
            target_bloom=target_bloom,
        )

        diff_res = DifficultyValidationService.validate_difficulty_alignment(
            content=content,
            target_difficulty=target_difficulty,
        )

        pref_res = FacultyPreferenceValidationService.validate_preference_alignment(
            content=content,
            teaching_style=teaching_style,
            expected_length=expected_length,
            preferred_examples=preferred_examples,
        )

        readability_res = ReadabilityAnalysisService.analyze_readability(content)

        duplicates_res = ConsistencyValidationService.detect_duplicate_paragraphs(content)
        inconsistencies_res = ConsistencyValidationService.detect_inconsistencies(content)
        
        # Combine consistency checks into one node
        consistency_passed = duplicates_res["passed"] and inconsistencies_res["passed"]
        consistency_score = (duplicates_res["score"] + inconsistencies_res["score"]) / 2.0
        consistency_res = {
            "passed": consistency_passed,
            "score": consistency_score,
            "details": {
                "paragraph_redundancies": duplicates_res["details"],
                "logical_inconsistencies": inconsistencies_res["details"],
            }
        }

        # New Checks for Phase 14 validation
        completeness_res = cls.validate_completeness(content)
        terminology_res = cls.validate_terminology_accuracy(content, topic_name)
        image_relevance_res = cls.validate_image_relevance(content, image_metadata)

        # 2. Score overall metrics
        sub_results = {
            "curriculum": curriculum_res,
            "course_outcomes": co_res,
            "bloom": bloom_res,
            "difficulty": diff_res,
            "preferences": pref_res,
            "readability": readability_res,
            "consistency": consistency_res,
            "completeness": completeness_res,
            "terminology": terminology_res,
            "image_relevance": image_relevance_res,
        }

        overall_score = EducationalQualityScoringService.calculate_overall_score(sub_results)
        confidence_score = ConfidenceScoringService.calculate_confidence_score(sub_results)

        return {
            "quality_score": overall_score,
            "confidence_score": confidence_score,
            "validation_results": sub_results,
        }

    @classmethod
    async def create_quality_report(
        cls,
        db: AsyncSession,
        content: str,
        topic_name: str,
        target_bloom: str,
        target_difficulty: str,
        content_id: Optional[uuid.UUID] = None,
        content_type: Optional[str] = None,
        topic_description: Optional[str] = None,
        unit_title: Optional[str] = None,
        course_outcomes: Optional[List[str]] = None,
        teaching_style: Optional[str] = None,
        expected_length: Optional[int] = None,
        preferred_examples: Optional[str] = None,
        image_metadata: Optional[dict] = None,
    ) -> QualityReport:
        """
        Execute QA pipeline and persist audit results in quality_reports database.
        """
        qa_data = cls.run_qa_pipeline(
            content=content,
            topic_name=topic_name,
            target_bloom=target_bloom,
            target_difficulty=target_difficulty,
            topic_description=topic_description,
            unit_title=unit_title,
            course_outcomes=course_outcomes,
            teaching_style=teaching_style,
            expected_length=expected_length,
            preferred_examples=preferred_examples,
            image_metadata=image_metadata,
        )

        new_report = QualityReport(
            content_id=content_id,
            content_type=content_type,
            quality_score=qa_data["quality_score"],
            confidence_score=qa_data["confidence_score"],
            validation_details=qa_data["validation_results"],
        )

        db.add(new_report)
        await db.flush()

        return new_report
