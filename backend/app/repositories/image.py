"""
Educational Image Database Repository.
"""

import uuid
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.image import Image
from app.repositories.base import BaseRepository


class ImageRepository(BaseRepository[Image]):
    """
    Repository handling database access for educational diagrams and illustrations.
    """

    model = Image

    async def get_by_topic(self, topic_id: uuid.UUID) -> list[Image]:
        """
        Retrieve all images stored for a specific topic.
        """
        stmt = select(Image).where(Image.topic_id == topic_id)
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def get_by_url(self, url: str) -> Image | None:
        """
        Lookup an image record by its unique URL.
        """
        stmt = select(Image).where(Image.image_url == url)
        result = await self._session.execute(stmt)
        return result.scalars().first()

    async def delete_image(self, id: uuid.UUID) -> bool:
        """
        Wipe an image record by its primary key.
        """
        img = await self.get_by_id(id)
        if not img:
            return False
        await self.delete(img)
        return True

    async def get_history(self, limit: int = 20, offset: int = 0) -> list[Image]:
        """
        Retrieve chronological retrieval history.
        """
        stmt = (
            select(Image)
            .order_by(Image.retrieved_at.desc())
            .limit(limit)
            .offset(offset)
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())
