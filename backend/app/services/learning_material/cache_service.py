"""
Persistent Caching Service for generated Learning Materials.
"""

import hashlib
from datetime import datetime
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.learning_material import LearningMaterialCache


class LearningMaterialCacheService:
    """
    Handles persistent, database-backed caching operations for generated educational materials.
    """

    @staticmethod
    def generate_cache_key(
        topic: str,
        teaching_style: str | None,
        pedagogy: str | None,
        bloom_level: str | None,
        knowledge_level: str | None,
        generation_type: str,
        prompt_version: str,
    ) -> str:
        """
        Generate a deterministic SHA-256 cache key based on the request parameters.
        """
        components = [
            topic.strip().lower(),
            (teaching_style or "").strip().lower(),
            (pedagogy or "").strip().lower(),
            (bloom_level or "").strip().lower(),
            (knowledge_level or "").strip().lower(),
            generation_type.strip().lower(),
            prompt_version.strip().lower(),
        ]
        raw_key = "|".join(components)
        return hashlib.sha256(raw_key.encode("utf-8")).hexdigest()

    async def get(self, db: AsyncSession, cache_key: str) -> LearningMaterialCache | None:
        """
        Retrieve a cached material by its key.
        """
        stmt = select(LearningMaterialCache).where(LearningMaterialCache.cache_key == cache_key)
        result = await db.execute(stmt)
        return result.scalars().first()

    async def set(
        self,
        db: AsyncSession,
        cache_key: str,
        content: str,
        output_format: str,
    ) -> LearningMaterialCache:
        """
        Write or update a cached material.
        """
        # Check if already exists to prevent duplicate key constraint failure
        existing = await self.get(db, cache_key)
        if existing:
            existing.content = content
            existing.format = output_format
            existing.created_at = datetime.utcnow()
            await db.flush()
            return existing
        
        new_cache = LearningMaterialCache(
            cache_key=cache_key,
            content=content,
            format=output_format,
        )
        db.add(new_cache)
        await db.flush()
        return new_cache

    async def list_all(self, db: AsyncSession) -> list[LearningMaterialCache]:
        """
        List all active cache entries in the system.
        """
        stmt = select(LearningMaterialCache).order_by(LearningMaterialCache.created_at.desc())
        result = await db.execute(stmt)
        return list(result.scalars().all())

    async def clear_all(self, db: AsyncSession) -> int:
        """
        Delete all cache entries. Returns the number of entries deleted.
        """
        stmt = delete(LearningMaterialCache)
        result = await db.execute(stmt)
        await db.flush()
        return result.rowcount
