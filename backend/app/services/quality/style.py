"""
Faculty Preferences and Style Validation Service.
"""

from typing import Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.quality import FacultyPreference


class FacultyPreferenceValidationService:
    """
    Enforces compliance with reusable instructor preference profiles.
    """

    @classmethod
    def validate_preference_alignment(
        cls,
        content: str,
        teaching_style: Optional[str] = None,
        expected_length: Optional[int] = None,
        preferred_examples: Optional[str] = None,
    ) -> dict:
        """
        Check if the generated content respects style, length, and examples configurations.
        """
        content_lower = content.lower()
        score = 100.0
        details = {}

        # 1. Teaching Style Match
        if teaching_style:
            style_lower = teaching_style.lower()
            style_words = [w for w in style_lower.split() if len(w) > 4]
            if style_words:
                style_match = any(w in content_lower for w in style_words)
                details["teaching_style_matched"] = style_match
                if not style_match:
                    score -= 30.0

        # 2. Content Length Check
        word_count = len(content.split())
        details["actual_word_count"] = word_count
        if expected_length:
            details["target_word_count"] = expected_length
            diff = abs(word_count - expected_length) / expected_length
            # Warn/penalize if difference exceeds 40%
            if diff > 0.4:
                score -= min(30.0, diff * 50.0)

        # 3. Preferred Examples Check
        if preferred_examples:
            ex_words = [w.lower() for w in preferred_examples.split() if len(w) > 4]
            if ex_words:
                ex_match = sum(1 for w in ex_words if w in content_lower)
                ratio = ex_match / len(ex_words)
                details["preferred_examples_ratio"] = ratio
                if ratio < 0.2:  # penalty if less than 20% keywords match
                    score -= 20.0

        score = max(0.0, score)
        return {
            "passed": score >= 70.0,
            "score": score,
            "details": details,
        }

    @classmethod
    async def get_or_create_preferences(
        cls,
        db: AsyncSession,
        faculty_id: str,
        default_style: str = "Standard Academic",
        default_difficulty: str = "Medium",
    ) -> FacultyPreference:
        """
        Retrieve existing preferences or instantiate defaults.
        """
        stmt = select(FacultyPreference).where(FacultyPreference.faculty_id == faculty_id)
        result = await db.execute(stmt)
        pref = result.scalars().first()

        if not pref:
            pref = FacultyPreference(
                faculty_id=faculty_id,
                teaching_style=default_style,
                difficulty=default_difficulty,
                content_length=1000,
                formatting_preferences={"bold_keywords": True, "use_lists": True},
            )
            db.add(pref)
            await db.flush()

        return pref
