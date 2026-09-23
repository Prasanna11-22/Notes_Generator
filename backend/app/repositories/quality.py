"""
Academic Quality and Faculty Preferences Repositories.
"""

import uuid
from datetime import datetime
from typing import Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.quality import QualityReport, FacultyPreference
from app.repositories.base import BaseRepository


class QualityReportRepository(BaseRepository[QualityReport]):
    """
    Repository for handling QualityReport records.
    """

    model = QualityReport

    async def get_by_content(self, content_id: uuid.UUID) -> list[QualityReport]:
        """
        Retrieve all reports logged for a specific target content ID.
        """
        stmt = select(QualityReport).where(QualityReport.content_id == content_id)
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def get_history(self, limit: int = 20, offset: int = 0) -> list[QualityReport]:
        """
        Retrieve chronological quality audit logs.
        """
        stmt = (
            select(QualityReport)
            .order_by(QualityReport.validation_timestamp.desc())
            .limit(limit)
            .offset(offset)
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())


class FacultyPreferenceRepository(BaseRepository[FacultyPreference]):
    """
    Repository for handling FacultyPreference profiles.
    """

    model = FacultyPreference

    async def get_by_faculty(self, faculty_id: uuid.UUID) -> FacultyPreference | None:
        """
        Retrieve preference profile stored for a specific instructor.
        """
        stmt = select(FacultyPreference).where(FacultyPreference.faculty_id == faculty_id)
        result = await self._session.execute(stmt)
        return result.scalars().first()

    async def save_preferences(
        self,
        faculty_id: uuid.UUID,
        teaching_style: str,
        difficulty: str,
        examples: Optional[str] = None,
        content_length: int = 1000,
        formatting_preferences: Optional[dict] = None,
    ) -> FacultyPreference:
        """
        Create or update a faculty preference profile.
        """
        pref = await self.get_by_faculty(faculty_id)
        if not pref:
            pref = FacultyPreference(
                faculty_id=faculty_id,
                teaching_style=teaching_style,
                difficulty=difficulty,
                examples=examples,
                content_length=content_length,
                formatting_preferences=formatting_preferences or {},
            )
            self._session.add(pref)
        else:
            pref.teaching_style = teaching_style
            pref.difficulty = difficulty
            pref.examples = examples
            pref.content_length = content_length
            pref.formatting_preferences = formatting_preferences or {}
            pref.updated_at = datetime.utcnow()

        await self._session.flush()
        return pref
