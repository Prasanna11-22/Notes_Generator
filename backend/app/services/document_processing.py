"""
Document Processing Service.

Orchestrates the full document-processing pipeline for a single resource:

1. Load file bytes from storage.
2. Validate the resource exists and is eligible for processing.
3. Create / update a ``DocumentProcessing`` record (status=processing).
4. Delegate to the correct ``BaseParser`` via ``ParserFactory``.
5. Detect scanned PDFs and set status to ``OCR_REQUIRED`` when applicable.
6. Run ``TextCleaningPipeline`` on extracted text.
7. Detect language with ``langdetect``.
8. Persist ``DocumentMetadata``.
9. Update ``DocumentProcessing`` to ``completed`` (or ``failed``).

All synchronous I/O (file parsing, text cleaning) is offloaded to a thread
pool via ``asyncio.to_thread`` to avoid blocking the event loop.

The service is invoked either directly from an API route (via
``BackgroundTasks``) or can be called by any future task queue adapter
without changes to this class.
"""

from __future__ import annotations

import asyncio
import uuid
from datetime import UTC, datetime

from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.exceptions.custom import ConflictError, NotFoundError
from app.models.document_processing import DocumentMetadata, DocumentProcessing, ProcessingStatus
from app.models.resource import Resource
from app.processors.cleaner import TextCleaningPipeline
from app.processors.factory import ParserFactory
from app.repositories.document_processing import (
    DocumentMetadataRepository,
    DocumentProcessingRepository,
)
from app.repositories.resource import ResourceRepository
from app.storage import get_storage


class DocumentProcessingService:
    """
    Orchestrates the document processing pipeline for a single resource.

    :param session: The active ``AsyncSession`` for the current request or
                    background task.  Callers must manage the transaction
                    lifecycle (commit / rollback).
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._proc_repo = DocumentProcessingRepository(session)
        self._meta_repo = DocumentMetadataRepository(session)
        self._resource_repo = ResourceRepository(session)
        self._cleaner = TextCleaningPipeline()

    # ── Public API ─────────────────────────────────────────────────────────────

    async def enqueue(self, resource_id: uuid.UUID) -> DocumentProcessing:
        """
        Create a ``pending`` processing record for *resource_id*.

        :raises NotFoundError:  Resource does not exist.
        :raises ConflictError:  A job is already in the ``processing`` state.
        :returns: The newly created ``DocumentProcessing`` record.
        """
        resource = await self._get_resource_or_404(resource_id)

        existing = await self._proc_repo.get_by_resource_id(resource_id)
        if existing and existing.status == ProcessingStatus.PROCESSING:
            raise ConflictError(
                f"Resource '{resource_id}' is already being processed."
            )

        if existing:
            # Reset existing record for re-processing
            job = await self._proc_repo.update(
                existing,
                {
                    "status": ProcessingStatus.PENDING.value,
                    "error_message": None,
                    "started_at": None,
                    "completed_at": None,
                    "processing_duration_ms": None,
                    "parser_used": None,
                    "page_count": None,
                },
            )
        else:
            job = await self._proc_repo.create(
                DocumentProcessing(
                    resource_id=resource.id,
                    status=ProcessingStatus.PENDING.value,
                )
            )

        await self._session.commit()
        logger.info("Enqueued processing job {} for resource {}", job.id, resource_id)
        return job

    async def process(self, resource_id: uuid.UUID) -> DocumentProcessing:
        """
        Execute the full document processing pipeline for *resource_id*.

        This method is designed to be safe to call from a background task.
        It opens its own session-level transaction guard and always leaves
        the ``DocumentProcessing`` record in a terminal state
        (``completed``, ``failed``, or ``ocr_required``).

        :param resource_id: UUID of the resource to process.
        :returns: The updated ``DocumentProcessing`` record.
        """
        resource = await self._get_resource_or_404(resource_id)
        job = await self._get_or_create_job(resource_id)

        start_time = datetime.now(UTC)

        # Mark as processing
        job = await self._proc_repo.update(
            job,
            {
                "status": ProcessingStatus.PROCESSING.value,
                "started_at": start_time,
            },
        )
        await self._session.commit()

        try:
            # ── 1. Load file from storage ─────────────────────────────────────
            logger.info(
                "Processing resource {} ({})", resource_id, resource.mime_type
            )
            file_bytes = await get_storage().download(resource.storage_path)

            # ── 2. Parse (offloaded to thread pool) ───────────────────────────
            parser = ParserFactory.get_parser(resource.mime_type)
            parse_result = await asyncio.to_thread(
                parser.parse, file_bytes, resource.original_file_name
            )

            # ── 3. Handle scanned PDFs ────────────────────────────────────────
            if parse_result.is_scanned:
                logger.warning(
                    "Resource {} is a scanned PDF — OCR required", resource_id
                )
                elapsed_ms = int(
                    (datetime.now(UTC) - start_time).total_seconds() * 1000
                )
                job = await self._finalise_job(
                    job=job,
                    status=ProcessingStatus.OCR_REQUIRED,
                    parser_used=parse_result.parser_name,
                    page_count=parse_result.page_count,
                    elapsed_ms=elapsed_ms,
                    error_message=(
                        "This PDF appears to consist of scanned images only. "
                        "No selectable text could be extracted. "
                        "OCR processing will be available in a future update."
                    ),
                )
                await self._session.commit()
                return job

            # ── 4. Clean text (offloaded to thread pool) ──────────────────────
            cleaned_text = await asyncio.to_thread(
                self._cleaner.clean, parse_result.raw_text
            )

            # ── 5. Detect language ────────────────────────────────────────────
            language = await asyncio.to_thread(
                self._detect_language, cleaned_text
            )

            # ── 6. Extract document-level metadata ────────────────────────────
            doc_title = (
                parse_result.metadata.get("title")
                or resource.title
            )
            doc_author = parse_result.metadata.get("author")
            doc_created = self._parse_metadata_date(
                parse_result.metadata.get("created")
                or parse_result.metadata.get("creationDate")
            )
            doc_modified = self._parse_metadata_date(
                parse_result.metadata.get("modified")
                or parse_result.metadata.get("modDate")
            )

            word_count = len(cleaned_text.split()) if cleaned_text else 0
            char_count = len(cleaned_text) if cleaned_text else 0

            # ── 7. Guard against excessively large text ───────────────────────
            raw_text_to_store = parse_result.raw_text
            cleaned_to_store = cleaned_text
            if len(cleaned_text.encode()) > settings.max_extracted_text_bytes:
                logger.warning(
                    "Resource {} cleaned text exceeds {} bytes; truncating",
                    resource_id,
                    settings.max_extracted_text_bytes,
                )
                cleaned_to_store = cleaned_text[: settings.max_extracted_text_bytes // 4]

            # ── 8. Persist DocumentMetadata ───────────────────────────────────
            existing_meta = await self._meta_repo.get_by_resource_id(resource_id)
            meta_data = {
                "resource_id": resource.id,
                "processing_id": job.id,
                "title": str(doc_title)[:500] if doc_title else None,
                "author": str(doc_author)[:500] if doc_author else None,
                "page_count": parse_result.page_count,
                "language": language,
                "word_count": word_count,
                "char_count": char_count,
                "document_created_at": doc_created,
                "document_modified_at": doc_modified,
                "raw_text": raw_text_to_store,
                "cleaned_text": cleaned_to_store,
                "raw_metadata": parse_result.metadata,
                "is_scanned": False,
            }
            if existing_meta:
                await self._meta_repo.update(existing_meta, meta_data)
            else:
                await self._meta_repo.create(DocumentMetadata(**meta_data))

            # ── 9. Finalise job as completed ──────────────────────────────────
            elapsed_ms = int(
                (datetime.now(UTC) - start_time).total_seconds() * 1000
            )
            job = await self._finalise_job(
                job=job,
                status=ProcessingStatus.COMPLETED,
                parser_used=parse_result.parser_name,
                page_count=parse_result.page_count,
                elapsed_ms=elapsed_ms,
            )
            await self._session.commit()
            logger.info(
                "Resource {} processed successfully in {}ms (parser={})",
                resource_id,
                elapsed_ms,
                parse_result.parser_name,
            )
            return job

        except Exception as exc:
            logger.exception(
                "Processing failed for resource {}: {}", resource_id, exc
            )
            elapsed_ms = int(
                (datetime.now(UTC) - start_time).total_seconds() * 1000
            )
            try:
                job = await self._finalise_job(
                    job=job,
                    status=ProcessingStatus.FAILED,
                    elapsed_ms=elapsed_ms,
                    error_message=str(exc)[:2000],
                )
                await self._session.commit()
            except Exception as inner:
                logger.error(
                    "Could not persist failed status for resource {}: {}",
                    resource_id,
                    inner,
                )
            return job

    async def get_processing_job(
        self, resource_id: uuid.UUID
    ) -> DocumentProcessing:
        """
        Return the processing job for *resource_id*.

        :raises NotFoundError: No job exists for this resource.
        """
        await self._get_resource_or_404(resource_id)
        job = await self._proc_repo.get_by_resource_id(resource_id)
        if not job:
            raise NotFoundError("Processing job", str(resource_id))
        return job

    async def get_metadata(self, resource_id: uuid.UUID) -> DocumentMetadata:
        """
        Return extracted metadata for *resource_id*.

        :raises NotFoundError: Resource or metadata record not found.
        """
        await self._get_resource_or_404(resource_id)
        meta = await self._meta_repo.get_by_resource_id(resource_id)
        if not meta:
            raise NotFoundError(
                "Document metadata",
                str(resource_id),
            )
        return meta

    # ── Private helpers ────────────────────────────────────────────────────────

    async def _get_resource_or_404(self, resource_id: uuid.UUID) -> Resource:
        resource = await self._resource_repo.get_by_id(resource_id)
        if not resource:
            raise NotFoundError("Resource", str(resource_id))
        return resource

    async def _get_or_create_job(
        self, resource_id: uuid.UUID
    ) -> DocumentProcessing:
        """Return existing job or create a new ``pending`` one."""
        job = await self._proc_repo.get_by_resource_id(resource_id)
        if not job:
            job = await self._proc_repo.create(
                DocumentProcessing(
                    resource_id=resource_id,
                    status=ProcessingStatus.PENDING.value,
                )
            )
        return job

    async def _finalise_job(
        self,
        *,
        job: DocumentProcessing,
        status: ProcessingStatus,
        parser_used: str | None = None,
        page_count: int | None = None,
        elapsed_ms: int | None = None,
        error_message: str | None = None,
    ) -> DocumentProcessing:
        """Update the job record and append a history entry."""
        now = datetime.now(UTC)

        # Build history entry from the *previous* run's data
        history_entry = {
            "status": job.status,
            "parser_used": job.parser_used,
            "page_count": job.page_count,
            "processing_duration_ms": job.processing_duration_ms,
            "started_at": job.started_at.isoformat() if job.started_at else None,
            "completed_at": job.completed_at.isoformat() if job.completed_at else None,
            "error_message": job.error_message,
        }
        history: list = list(job.processing_history or [])
        # Keep at most 20 history entries
        if len(history) >= 20:
            history = history[-19:]
        history.append(history_entry)

        updates: dict = {
            "status": status.value,
            "completed_at": now,
            "processing_history": history,
        }
        if parser_used is not None:
            updates["parser_used"] = parser_used
        if page_count is not None:
            updates["page_count"] = page_count
        if elapsed_ms is not None:
            updates["processing_duration_ms"] = elapsed_ms
        if error_message is not None:
            updates["error_message"] = error_message

        return await self._proc_repo.update(job, updates)

    @staticmethod
    def _detect_language(text: str) -> str | None:
        """Return ISO 639-1 language code for *text*, or ``None`` on failure."""
        if not text or len(text.strip()) < 50:
            return None
        try:
            from langdetect import LangDetectException, detect  # type: ignore[import-untyped]

            return detect(text)
        except Exception:
            return None

    @staticmethod
    def _parse_metadata_date(value: object) -> datetime | None:
        """
        Parse a date string from document metadata into a ``datetime``.

        Handles PyMuPDF's "YYYYMMDDHHmmSS" format as well as ISO 8601.
        """
        if value is None:
            return None
        s = str(value).strip()
        if not s:
            return None
        # PyMuPDF: "YYYYMMDDHHmmSS"
        if len(s) >= 14 and s[:14].isdigit():
            try:
                return datetime.strptime(s[:14], "%Y%m%d%H%M%S")
            except ValueError:
                pass
        # ISO 8601
        for fmt in ("%Y-%m-%dT%H:%M:%S", "%Y-%m-%dT%H:%M:%S%z", "%Y-%m-%d"):
            try:
                return datetime.strptime(s[:19], fmt)
            except ValueError:
                continue
        return None
