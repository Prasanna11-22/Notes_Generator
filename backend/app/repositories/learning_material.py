"""
Learning Material Database Repository.
"""

import uuid
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.learning_material import LearningMaterial, LearningMaterialCache
from app.repositories.base import BaseRepository


class LearningMaterialRepository(BaseRepository[LearningMaterial]):
    """
    Repository handling database access for generated Learning Materials.
    """

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(LearningMaterial, session)

    async def get_by_topic(self, topic_id: uuid.UUID) -> list[LearningMaterial]:
        """
        Retrieve all materials generated for a specific topic.
        """
        stmt = select(LearningMaterial).where(LearningMaterial.topic_id == topic_id)
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def get_history_by_user(
        self,
        user_id: uuid.UUID,
        limit: int = 20,
        offset: int = 0,
    ) -> list[LearningMaterial]:
        """
        Retrieve generation history list for a specific faculty user.
        """
        stmt = (
            select(LearningMaterial)
            .where(LearningMaterial.created_by == user_id)
            .order_by(LearningMaterial.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def delete_material(self, id: uuid.UUID) -> bool:
        """
        Wipe a learning material record by its primary key.
        """
        material = await self.get(id)
        if not material:
            return False
        await self.delete(material)
        return True
