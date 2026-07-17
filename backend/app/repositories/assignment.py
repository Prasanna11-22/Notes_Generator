"""
Assignment Database Repository.
"""

import uuid
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.assignment import Assignment
from app.repositories.base import BaseRepository


class AssignmentRepository(BaseRepository[Assignment]):
    """
    Repository handling database access for generated Assignments and Activities.
    """

    model = Assignment

    async def get_by_topic(self, topic_id: uuid.UUID) -> list[Assignment]:
        """
        Retrieve all assignments generated for a specific topic.
        """
        stmt = select(Assignment).where(Assignment.topic_id == topic_id)
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def get_history_by_user(
        self,
        user_id: uuid.UUID,
        limit: int = 20,
        offset: int = 0,
    ) -> list[Assignment]:
        """
        Retrieve generation history list for a specific faculty user.
        """
        stmt = (
            select(Assignment)
            .where(Assignment.created_by == user_id)
            .order_by(Assignment.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def delete_assignment(self, id: uuid.UUID) -> bool:
        """
        Wipe an assignment record by its primary key.
        """
        assignment = await self.get_by_id(id)
        if not assignment:
            return False
        await self.delete(assignment)
        return True
