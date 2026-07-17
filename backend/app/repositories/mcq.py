"""
MCQ Database Repository.
"""

import uuid
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.mcq import MCQQuestion
from app.repositories.base import BaseRepository


class MCQRepository(BaseRepository[MCQQuestion]):
    """
    Repository handling database access for generated MCQs.
    """

    model = MCQQuestion

    async def get_by_topic(self, topic_id: uuid.UUID) -> list[MCQQuestion]:
        """
        Retrieve all MCQs generated for a specific topic.
        """
        stmt = select(MCQQuestion).where(MCQQuestion.topic_id == topic_id)
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def get_history_by_user(
        self,
        user_id: uuid.UUID,
        limit: int = 20,
        offset: int = 0,
    ) -> list[MCQQuestion]:
        """
        Retrieve generation history list for a specific faculty user.
        """
        stmt = (
            select(MCQQuestion)
            .where(MCQQuestion.created_by == user_id)
            .order_by(MCQQuestion.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def delete_question(self, id: uuid.UUID) -> bool:
        """
        Wipe an MCQ record by its primary key.
        """
        question = await self.get_by_id(id)
        if not question:
            return False
        await self.delete(question)
        return True
