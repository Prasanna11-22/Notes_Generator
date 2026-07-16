"""
Curriculum Metadata Enrichment Service.

Scans chunk text to match it against Course Units and Topics in the database,
using TF-IDF / token intersection scores.  Resolves associated Course Outcomes,
Bloom Levels, and Knowledge Levels from curriculum mappings.
"""

from __future__ import annotations

import re
from uuid import UUID
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.curriculum import Course, CourseOutcome, Topic, TopicMapping, Unit
from app.services.chunking.base import RawChunk


class EnrichedMetadata:
    """Enriched curriculum-placement parameters for a chunk."""

    def __init__(self) -> None:
        self.unit_id: UUID | None = None
        self.topic_id: UUID | None = None
        self.course_outcome_id: UUID | None = None
        self.bloom_level: str | None = None
        self.knowledge_level: str | None = None
        self.chapter_name: str | None = None
        self.section_heading: str | None = None
        self.subheading: str | None = None


class MetadataEnricher:
    """
    Enriches text chunks with curriculum placements.

    Queries all Units and Topics registered under the target course and
    computes text similarity scores to link each chunk contextually.
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def enrich_chunk(
        self,
        course_id: UUID,
        chunk: RawChunk,
    ) -> EnrichedMetadata:
        """
        Scan *chunk* against the curriculum of *course_id* to resolve metadata.
        """
        enriched = EnrichedMetadata()

        # Carry over structural headings detected during splitting
        enriched.chapter_name = chunk.chapter_name
        enriched.section_heading = chunk.section_heading
        enriched.subheading = chunk.subheading

        # Fetch all units and topics in the course
        units = await self._get_course_units(course_id)

        best_score = 0.0
        best_unit: Unit | None = None
        best_topic: Topic | None = None

        text_lower = chunk.cleaned_text.lower()
        chunk_tokens = set(re.findall(r"\w+", text_lower))

        for unit in units:
            # 1. Score the unit title against the chunk
            unit_title_tokens = set(re.findall(r"\w+", unit.title.lower()))
            if not unit_title_tokens:
                continue

            # Calculate intersection ratio
            overlap = len(chunk_tokens.intersection(unit_title_tokens))
            unit_score = overlap / len(unit_title_tokens)

            # If unit score is high, scan its child topics
            if unit_score > best_score:
                best_score = unit_score
                best_unit = unit
                best_topic = None

            for topic in unit.topics:
                topic_tokens = set(re.findall(r"\w+", topic.topic_name.lower()))
                if not topic_tokens:
                    continue

                topic_overlap = len(chunk_tokens.intersection(topic_tokens))
                topic_score = topic_overlap / len(topic_tokens)

                # Weight topic score slightly higher than raw unit score
                combined_score = (unit_score * 0.4) + (topic_score * 0.6)

                if combined_score > best_score:
                    best_score = combined_score
                    best_unit = unit
                    best_topic = topic

        # If we have a matching unit, assign it
        if best_unit:
            enriched.unit_id = best_unit.id

        # If we have a matching topic, map it and check for TopicMappings
        if best_topic:
            enriched.topic_id = best_topic.id
            await self._map_topic_enrichments(best_topic.id, enriched)

        return enriched

    # ── Private DB helpers ────────────────────────────────────────────────────

    async def _get_course_units(self, course_id: UUID) -> list[Unit]:
        """Fetch all units and eager-load child topics for *course_id*."""
        from sqlalchemy.orm import selectinload

        stmt = (
            select(Unit)
            .where(Unit.course_id == course_id)
            .options(selectinload(Unit.topics))
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def _map_topic_enrichments(self, topic_id: UUID, enriched: EnrichedMetadata) -> None:
        """Query TopicMapping database records to find CO, Bloom, and Knowledge levels."""
        from sqlalchemy.orm import selectinload

        stmt = (
            select(TopicMapping)
            .where(TopicMapping.topic_id == topic_id)
            .options(
                selectinload(TopicMapping.bloom_level),
                selectinload(TopicMapping.knowledge_level),
                selectinload(TopicMapping.course_outcome),
            )
        )
        result = await self._session.execute(stmt)
        mapping = result.scalar_one_or_none()

        if mapping:
            enriched.bloom_level = mapping.bloom_level.name
            enriched.knowledge_level = mapping.knowledge_level.name
            if mapping.course_outcome:
                enriched.course_outcome_id = mapping.course_outcome.id
