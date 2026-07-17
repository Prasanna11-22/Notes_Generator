"""
Cache Service for retrieved educational images.
"""

from typing import Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from loguru import logger

from app.models.image import Image


class ImageCacheService:
    """
    Handles database-backed caching for retrieved diagrams to avoid repeated API requests.
    """

    @classmethod
    def generate_cache_key(cls, topic: str, concept: str, provider: str) -> str:
        """
        Generate a unique, deterministic cache key.
        """
        t_clean = topic.strip().lower().replace(" ", "_")
        c_clean = concept.strip().lower().replace(" ", "_")
        p_clean = provider.strip().lower()
        return f"img_cache_{p_clean}_{t_clean}_{c_clean}"

    @classmethod
    async def get_cached_image(
        cls, db: AsyncSession, cache_key: str, max_age_days: int = 7
    ) -> Optional[Image]:
        """
        Lookup if a cached Image record exists matching the cache key.
        """
        # SQLite / PG JSON extraction
        stmt = select(Image)
        result = await db.execute(stmt)
        images = result.scalars().all()
        
        from datetime import datetime
        for img in images:
            meta = img.image_metadata
            if isinstance(meta, dict) and meta.get("cache_key") == cache_key:
                # Check expiration age
                age = datetime.utcnow() - img.retrieved_at
                if age.days > max_age_days:
                    logger.info("ImageCacheService | Cache Expired for key: {}", cache_key)
                    continue
                logger.info("ImageCacheService | Cache Hit for key: {}", cache_key)
                return img
                
        return None
