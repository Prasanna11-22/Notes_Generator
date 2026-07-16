"""
Document Processing API Routes.

All endpoints are nested under ``/resources/{resource_id}`` to make it
clear they operate on an existing resource.

Endpoints
---------
POST   /resources/{resource_id}/process             — Enqueue a job (Faculty+)
POST   /resources/{resource_id}/reprocess           — Re-enqueue (Faculty+)
GET    /resources/{resource_id}/processing-status   — Status summary (Faculty+)
GET    /resources/{resource_id}/processing-details  — Full job details (Faculty+)
GET    /resources/{resource_id}/metadata            — Extracted metadata (Faculty+)
GET    /resources/{resource_id}/text                — Cleaned text (Admin only)
"""

import uuid

from fastapi import APIRouter, BackgroundTasks, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.session import get_db
from app.dependencies.auth import AdminUser, FacultyUser
from app.exceptions.custom import ConflictError
from app.models.document_processing import ProcessingStatus
from app.schemas.document_processing import (
    DocumentMetadataRead,
    DocumentProcessingRead,
    DocumentTextRead,
)
from app.schemas.response import APIResponse
from app.services.document_processing import DocumentProcessingService
from app.services.processing_queue import get_processing_queue

router = APIRouter(prefix="/resources", tags=["Document Processing"])


# ── Enqueue Processing ────────────────────────────────────────────────────────


@router.post(
    "/{resource_id}/process",
    response_model=APIResponse[DocumentProcessingRead],
    status_code=status.HTTP_202_ACCEPTED,
    summary="Enqueue document processing (Faculty/Admin only)",
    description=(
        "Creates a processing job for the specified resource and starts it "
        "asynchronously in the background.  Returns 409 if a job is already running."
    ),
)
async def enqueue_processing(
    resource_id: uuid.UUID,
    background_tasks: BackgroundTasks,
    _user: FacultyUser,
    db: AsyncSession = Depends(get_db),
) -> APIResponse[DocumentProcessingRead]:
    service = DocumentProcessingService(db)

    # Create / reset the processing record
    job = await service.enqueue(resource_id)

    # Schedule background execution
    get_processing_queue().enqueue_processing(resource_id, background_tasks)

    return APIResponse(
        success=True,
        message="Document processing started in the background.",
        data=DocumentProcessingRead.model_validate(job),
    )


# ── Re-process ────────────────────────────────────────────────────────────────


@router.post(
    "/{resource_id}/reprocess",
    response_model=APIResponse[DocumentProcessingRead],
    status_code=status.HTTP_202_ACCEPTED,
    summary="Re-process a document (Faculty/Admin only)",
    description=(
        "Force re-processing even if a completed or failed job exists.  "
        "Returns 409 if a job is currently in the ``processing`` state."
    ),
)
async def reprocess(
    resource_id: uuid.UUID,
    background_tasks: BackgroundTasks,
    _user: FacultyUser,
    db: AsyncSession = Depends(get_db),
) -> APIResponse[DocumentProcessingRead]:
    service = DocumentProcessingService(db)

    # Check if already processing — block concurrent runs
    try:
        existing = await service.get_processing_job(resource_id)
        if existing.status == ProcessingStatus.PROCESSING:
            raise ConflictError(
                f"Resource '{resource_id}' is currently being processed. "
                "Wait for the current job to complete before reprocessing."
            )
    except Exception as exc:
        from app.exceptions.custom import NotFoundError

        if isinstance(exc, NotFoundError):
            pass  # no prior job; proceed normally
        else:
            raise

    job = await service.enqueue(resource_id)
    get_processing_queue().enqueue_processing(resource_id, background_tasks)

    return APIResponse(
        success=True,
        message="Document re-processing started in the background.",
        data=DocumentProcessingRead.model_validate(job),
    )


# ── Processing Status (lightweight) ──────────────────────────────────────────


@router.get(
    "/{resource_id}/processing-status",
    response_model=APIResponse[dict],
    summary="Get processing status (Faculty/Admin only)",
    description="Returns a lightweight status summary — useful for polling.",
)
async def get_processing_status(
    resource_id: uuid.UUID,
    _user: FacultyUser,
    db: AsyncSession = Depends(get_db),
) -> APIResponse[dict]:
    service = DocumentProcessingService(db)
    job = await service.get_processing_job(resource_id)

    return APIResponse(
        success=True,
        message="Processing status retrieved.",
        data={
            "resource_id": str(resource_id),
            "status": job.status,
            "started_at": job.started_at.isoformat() if job.started_at else None,
            "completed_at": job.completed_at.isoformat() if job.completed_at else None,
            "processing_duration_ms": job.processing_duration_ms,
            "error_message": job.error_message,
        },
    )


# ── Processing Details (full) ─────────────────────────────────────────────────


@router.get(
    "/{resource_id}/processing-details",
    response_model=APIResponse[DocumentProcessingRead],
    summary="Get full processing job details (Faculty/Admin only)",
)
async def get_processing_details(
    resource_id: uuid.UUID,
    _user: FacultyUser,
    db: AsyncSession = Depends(get_db),
) -> APIResponse[DocumentProcessingRead]:
    service = DocumentProcessingService(db)
    job = await service.get_processing_job(resource_id)

    return APIResponse(
        success=True,
        message="Processing job details retrieved.",
        data=DocumentProcessingRead.model_validate(job),
    )


# ── Extracted Metadata ────────────────────────────────────────────────────────


@router.get(
    "/{resource_id}/metadata",
    response_model=APIResponse[DocumentMetadataRead],
    summary="Get extracted document metadata (Faculty/Admin only)",
    description=(
        "Returns structured metadata extracted from the document "
        "(title, author, language, word count, etc.)."
    ),
)
async def get_document_metadata(
    resource_id: uuid.UUID,
    _user: FacultyUser,
    db: AsyncSession = Depends(get_db),
) -> APIResponse[DocumentMetadataRead]:
    service = DocumentProcessingService(db)
    meta = await service.get_metadata(resource_id)

    return APIResponse(
        success=True,
        message="Document metadata retrieved.",
        data=DocumentMetadataRead.model_validate(meta),
    )


# ── Extracted Text (Admin only) ───────────────────────────────────────────────


@router.get(
    "/{resource_id}/text",
    response_model=APIResponse[DocumentTextRead],
    summary="Get extracted and cleaned text (Admin only)",
    description=(
        "Returns the raw and cleaned text extracted from the document.  "
        "Restricted to administrators because the full text may contain "
        "proprietary or sensitive academic content."
    ),
)
async def get_document_text(
    resource_id: uuid.UUID,
    _user: AdminUser,
    db: AsyncSession = Depends(get_db),
) -> APIResponse[DocumentTextRead]:
    service = DocumentProcessingService(db)
    meta = await service.get_metadata(resource_id)

    return APIResponse(
        success=True,
        message="Document text retrieved.",
        data=DocumentTextRead(
            resource_id=meta.resource_id,
            cleaned_text=meta.cleaned_text,
            raw_text=meta.raw_text,
            word_count=meta.word_count,
            char_count=meta.char_count,
            language=meta.language,
        ),
    )
