"""
Chunking Orchestrator.

Main service layer entrypoint for the semantic chunking module.
Executes the full pipeline: load text → split → enrich → validate → dedup → persist.
"""

from __future__ import annotations

import asyncio
import uuid
from datetime import UTC, datetime

from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.exceptions.custom import ConflictError, NotFoundError
from app.models.chunk import Chunk, ChunkMapping, DocumentChunkingJob
from app.models.document_processing import DocumentMetadata
from app.models.resource import Resource
from app.repositories.chunk import ChunkMappingRepository, ChunkRepository
from app.repositories.resource import ResourceRepository
from app.services.chunking.base import RawChunk
from app.services.chunking.deduplicator import ChunkDeduplicator
from app.services.chunking.engine import ChunkerFactory, verify_nlp_resources
from app.services.chunking.enrichment import MetadataEnricher
from app.services.chunking.validator import ChunkQualityValidator


class ChunkingOrchestrator:
    """
    Coordinates semantic chunking and curriculum enrichment for a resource.
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._chunk_repo = ChunkRepository(session)
        self._mapping_repo = ChunkMappingRepository(session)
        self._resource_repo = ResourceRepository(session)
        self._enricher = MetadataEnricher(session)
        self._validator = ChunkQualityValidator()
        self._dedup = ChunkDeduplicator()

    # ── Public API ─────────────────────────────────────────────────────────────

    async def enqueue_chunking(self, resource_id: uuid.UUID) -> DocumentChunkingJob:
        """
        Create a ``pending`` chunking job for *resource_id*.
        """
        resource = await self._get_resource_or_404(resource_id)

        # Verify document processing has completed successfully
        stmt = select(DocumentMetadata).where(DocumentMetadata.resource_id == resource_id)
        res = await self._session.execute(stmt)
        meta = res.scalar_one_or_none()
        if not meta or not meta.cleaned_text:
            raise ConflictError(
                f"Resource '{resource_id}' text extraction is not complete. "
                "Run document processing first."
            )

        existing = await self._get_chunking_job(resource_id)
        if existing and existing.status == "processing":
            raise ConflictError(
                f"Resource '{resource_id}' is already undergoing chunking."
            )

        if existing:
            job = await self._update_job_status(
                existing, "pending", error_message=None
            )
        else:
            job = DocumentChunkingJob(
                id=uuid.uuid4(),
                resource_id=resource_id,
                status="pending",
            )
            self._session.add(job)
            await self._session.flush()

        await self._session.commit()
        return job

    async def process_chunking(self, resource_id: uuid.UUID) -> DocumentChunkingJob:
        """
        Execute the chunking pipeline for *resource_id*.
        """
        resource = await self._get_resource_or_404(resource_id)
        job = await self._get_or_create_job(resource_id)

        # Verify NLP resources exist (fail-fast startup check)
        verify_nlp_resources(settings.chunk_strategy, settings.spacy_model)

        # Mark as processing
        job = await self._update_job_status(job, "processing")
        job.started_at = datetime.now(UTC)
        await self._session.commit()

        try:
            # 1. Load cleaned text metadata
            stmt = select(DocumentMetadata).where(DocumentMetadata.resource_id == resource_id)
            res = await self._session.execute(stmt)
            meta = res.scalar_one_or_none()
            if not meta or not meta.cleaned_text:
                raise RuntimeError(
                    "No cleaned text metadata available for this resource."
                )

            # Delete any existing chunk mappings for this resource (rechunk logic)
            await self._mapping_repo.delete_by_resource(resource_id)

            # 2. Run chunker engine (offloaded to thread)
            chunker = ChunkerFactory.get_chunker()
            raw_chunks = await asyncio.to_thread(
                chunker.split_text,
                meta.cleaned_text,
                meta.raw_text or meta.cleaned_text,
                chunk_size=settings.chunk_size,
                chunk_overlap=settings.chunk_overlap,
            )

            valid_mappings: list[ChunkMapping] = []
            chunk_index_counter = 0

            # 3. Iterate, enrich, validate, and deduplicate
            for raw_chunk in raw_chunks:
                # 3a. Quality Validation
                is_valid, reject_reason = self._validator.is_valid(raw_chunk)
                if not is_valid:
                    logger.warning(
                        "ChunkingOrchestrator: skipped low-quality chunk: {}",
                        reject_reason,
                    )
                    continue

                # 3b. Deduplication check
                chunk_hash = ChunkDeduplicator.calculate_hash(raw_chunk.cleaned_text)
                db_chunk = await self._chunk_repo.get_by_hash(chunk_hash)

                if db_chunk:
                    target_chunk = db_chunk
                else:
                    # Check near-duplicates in DB to avoid minor edits bloating DB
                    near_dup = await self._find_near_duplicate(raw_chunk.cleaned_text)
                    if near_dup:
                        target_chunk = near_dup
                    else:
                        # Construct a new unique Chunk row
                        word_cnt = len(raw_chunk.cleaned_text.split())
                        char_cnt = len(raw_chunk.cleaned_text)
                        est_reading = max(0.1, word_cnt / 200.0)  # approx 200 WPM

                        new_chunk = Chunk(
                            id=uuid.uuid4(),
                            chunk_hash=chunk_hash,
                            cleaned_text=raw_chunk.cleaned_text,
                            raw_text=raw_chunk.raw_text,
                            char_count=char_cnt,
                            word_count=word_cnt,
                            estimated_reading_time=round(est_reading, 2),
                        )
                        self._session.add(new_chunk)
                        await self._session.flush()
                        target_chunk = new_chunk

                # 3c. Curriculum Metadata Enrichment
                enrichment = await self._enricher.enrich_chunk(resource.course_id, raw_chunk)

                # 4. Construct Mapping Reference
                mapping = ChunkMapping(
                    id=uuid.uuid4(),
                    chunk_id=target_chunk.id,
                    resource_id=resource_id,
                    course_id=resource.course_id,
                    unit_id=enrichment.unit_id,
                    topic_id=enrichment.topic_id,
                    course_outcome_id=enrichment.course_outcome_id,
                    chunk_index=chunk_index_counter,
                    page_numbers=raw_chunk.page_numbers,
                    chunk_title=raw_chunk.chapter_name or raw_chunk.section_heading,
                    bloom_level=enrichment.bloom_level,
                    knowledge_level=enrichment.knowledge_level,
                    resource_type=resource.resource_type,
                    chapter_name=enrichment.chapter_name,
                    section_heading=enrichment.section_heading,
                    subheading=enrichment.subheading,
                )
                self._session.add(mapping)
                valid_mappings.append(mapping)
                chunk_index_counter += 1

            await self._session.flush()

            # Finalise job status
            job.status = "completed"
            job.error_message = None
            job.chunks_count = len(valid_mappings)
            job.completed_at = datetime.now(UTC)
            await self._session.commit()

            logger.info(
                "ChunkingOrchestrator: successfully chunked resource {} into {} chunks",
                resource_id,
                len(valid_mappings),
            )
            return job

        except Exception as exc:
            logger.exception("Chunking failed for resource {}: {}", resource_id, exc)
            try:
                job.status = "failed"
                job.error_message = str(exc)[:2000]
                job.completed_at = datetime.now(UTC)
                await self._session.commit()
            except Exception as inner:
                logger.error("Could not persist failed status for resource {}: {}", resource_id, inner)
            return job

    async def delete_chunks(self, resource_id: uuid.UUID) -> None:
        """
        Delete all chunks and mappings belonging to *resource_id*.
        """
        await self._get_resource_or_404(resource_id)
        await self._mapping_repo.delete_by_resource(resource_id)

        # Delete job status record if present
        job = await self._get_chunking_job(resource_id)
        if job:
            await self._session.delete(job)

        await self._session.commit()

    # ── Private helper methods ────────────────────────────────────────────────

    async def _get_resource_or_404(self, resource_id: uuid.UUID) -> Resource:
        resource = await self._resource_repo.get_by_id(resource_id)
        if not resource:
            raise NotFoundError("Resource", str(resource_id))
        return resource

    async def _get_chunking_job(self, resource_id: uuid.UUID) -> DocumentChunkingJob | None:
        stmt = select(DocumentChunkingJob).where(DocumentChunkingJob.resource_id == resource_id)
        res = await self._session.execute(stmt)
        return res.scalar_one_or_none()

    async def _get_or_create_job(self, resource_id: uuid.UUID) -> DocumentChunkingJob:
        job = await self._get_chunking_job(resource_id)
        if not job:
            job = DocumentChunkingJob(
                id=uuid.uuid4(),
                resource_id=resource_id,
                status="pending",
            )
            self._session.add(job)
            await self._session.flush()
        return job

    async def _update_job_status(
        self,
        job: DocumentChunkingJob,
        status: str,
        error_message: str | None = None,
    ) -> DocumentChunkingJob:
        job.status = status
        if error_message is not None:
            job.error_message = error_message
        self._session.add(job)
        await self._session.flush()
        return job

    async def _find_near_duplicate(self, text: str) -> Chunk | None:
        """
        Scan loaded chunks in database to check Jaccard token similarity for near-dups.
        """
        all_unique = await self._chunk_repo.get_all_unique_chunks()
        for chunk in all_unique:
            if self._dedup.is_near_duplicate(text, chunk.cleaned_text):
                return chunk
        return None
