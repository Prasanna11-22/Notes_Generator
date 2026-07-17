"""
Image Retrieval & Diagram Orchestrator Service.
"""

import time
import uuid
from typing import Any, Dict, List, Optional
from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.image import Image
from app.services.image.providers import WikimediaProvider
from app.services.image.concept_extractor import KeywordExtractionService, EducationalConceptExtractor
from app.services.image.license_validator import LicenseValidationService
from app.services.image.ranking import ImageRankingService
from app.services.image.cache import ImageCacheService


class ImageRetrievalService:
    """
    Orchestration service coordinating educational image search, licensing checks, 
    aspect/resolution ranking, and database persistence.
    """

    def __init__(self, provider: Optional[WikimediaProvider] = None) -> None:
        self.provider = provider or WikimediaProvider()

    async def retrieve_educational_image(
        self,
        db: AsyncSession,
        topic: str,
        description: str = "",
        course_id: Optional[uuid.UUID] = None,
        topic_id: Optional[uuid.UUID] = None,
    ) -> Optional[Image]:
        """
        Execute the full educational diagram retrieval and ranking pipeline.
        """
        start_time = time.perf_counter()

        # 1. Concept Extraction & Query Optimization
        analysis = EducationalConceptExtractor.analyze_concept(topic, description)
        concept = analysis["primary_concept"]
        pref_diagram = analysis["preferred_diagram"]
        
        # Optimize search query candidates
        optimized_queries = KeywordExtractionService.extract_optimized_queries(topic, description)

        # 2. Cache Lookup
        cache_key = ImageCacheService.generate_cache_key(topic, concept, self.provider.get_provider_name())
        cached_img = await ImageCacheService.get_cached_image(db, cache_key)
        
        if cached_img:
            duration = time.perf_counter() - start_time
            logger.info(
                "ImageRetrievalService | Cache Hit | Key: {} | Time: {:.2f}ms",
                cache_key,
                duration * 1000,
            )
            return cached_img

        logger.info(
            "ImageRetrievalService | Cache Miss | Query candidates: {}",
            optimized_queries,
        )

        candidates: List[Dict[str, Any]] = []

        # 3. Retrieve Candidate Images (Iterate optimized queries until we find valid items)
        retrieval_start = time.perf_counter()
        for query in optimized_queries:
            results = await self.provider.search_images(query, limit=10)
            if results:
                candidates.extend(results)
                # If we get enough candidates, break early to save API latency
                if len(candidates) >= 10:
                    break
        retrieval_duration = time.perf_counter() - retrieval_start

        if not candidates:
            logger.info("ImageRetrievalService | Zero candidates retrieved for topic: {}", topic)
            return None

        # 4. License and Quality Validation
        validation_start = time.perf_counter()
        valid_candidates: List[Dict[str, Any]] = []
        
        # Fetch already retrieved URLs to prevent duplicates
        stmt = select(Image.image_url)
        res = await db.execute(stmt)
        existing_urls = set(res.scalars().all())

        for c in candidates:
            url = c.get("url", "")
            
            # Reject duplicates
            if url in existing_urls:
                continue
                
            # License Validation
            if not LicenseValidationService.is_license_valid(c.get("license", "")):
                continue

            # Resolution Check (Must not be low resolution)
            if c.get("width", 0) < 300 or c.get("height", 0) < 200:
                continue

            # Watermark / Unsafe terms check
            desc_title_lower = f"{c.get('title', '')} {c.get('description', '')}".lower()
            if any(term in desc_title_lower for term in ("watermark", "shutterstock", "stock photo", "depositphotos")):
                continue

            valid_candidates.append(c)

        validation_duration = time.perf_counter() - validation_start

        if not valid_candidates:
            logger.info("ImageRetrievalService | No candidate passed validation checks for topic: {}", topic)
            return None

        # 5. Image Ranking
        ranking_start = time.perf_counter()
        ranked = ImageRankingService.rank_candidates(valid_candidates, topic, pref_diagram)
        ranking_duration = time.perf_counter() - ranking_start

        # Select the highest-scoring candidate
        best_candidate = ranked[0]
        
        # 6. Save image details in DB
        db_metadata = {
            "title": best_candidate["title"],
            "artist": best_candidate.get("artist", "Unknown"),
            "width": best_candidate["width"],
            "height": best_candidate["height"],
            "description": best_candidate["description"],
            "thumbnail": best_candidate["thumbnail"],
            "cache_key": cache_key,
        }

        new_image = Image(
            course_id=course_id,
            topic_id=topic_id,
            image_url=best_candidate["url"],
            provider=self.provider.get_provider_name(),
            license=best_candidate["license"],
            ranking_score=best_candidate["ranking_score"],
            image_metadata=db_metadata,
        )

        db.add(new_image)
        await db.flush()

        total_duration = time.perf_counter() - start_time
        logger.info(
            "ImageRetrievalService | Completed | Provider: {} | SearchTime: {:.2f}s | "
            "RankingTime: {:.2f}ms | ValidationTime: {:.2f}ms | Score: {} | Cache: Miss",
            self.provider.get_provider_name(),
            retrieval_duration,
            ranking_duration * 1000,
            validation_duration * 1000,
            best_candidate["ranking_score"],
        )

        return new_image
