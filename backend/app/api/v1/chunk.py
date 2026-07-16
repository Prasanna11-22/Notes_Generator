"""
Document Chunking and Metadata Enrichment API Routes.

All endpoints operate relative to a resource, with administrative stats and
reports nested globally.
"""

import uuid
from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Depends, Query, status
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.session import get_db
from app.dependencies.auth import AdminUser, FacultyUser
from app.exceptions.custom import NotFoundError
from app.models.chunk import ChunkMapping, DocumentChunkingJob
from app.schemas.chunk import (
    ChunkDetailsRead,
    ChunkMappingRead,
    ChunkPreviewItem,
    ChunkStatistics,
    ChunkQualityReportItem,
    DocumentChunkingJobRead,
)
from app.schemas.response import APIResponse, PaginatedResponse
from app.services.chunking.base import RawChunk
from app.services.chunking.engine import ChunkerFactory
from app.services.chunking.orchestrator import ChunkingOrchestrator
from app.services.chunking_queue import get_chunking_queue

router = APIRouter(tags=["Document Chunking"])


# ── Start Chunking ───────────────────────────────────────────────────────────


@router.post(
    "/resources/{resource_id}/chunk",
    response_model=APIResponse[DocumentChunkingJobRead],
    status_code=status.HTTP_202_ACCEPTED,
    summary="Start document chunking pipeline (Faculty/Admin only)",
)
async def start_chunking(
    resource_id: uuid.UUID,
    background_tasks: BackgroundTasks,
    _user: FacultyUser,
    db: AsyncSession = Depends(get_db),
) -> APIResponse[DocumentChunkingJobRead]:
    orchestrator = ChunkingOrchestrator(db)
    job = await orchestrator.enqueue_chunking(resource_id)

    # Schedule background execution
    get_chunking_queue().enqueue_chunking(resource_id, background_tasks)

    return APIResponse(
        success=True,
        message="Document chunking started in the background.",
        data=DocumentChunkingJobRead.model_validate(job),
    )


# ── Re-chunk ──────────────────────────────────────────────────────────────────


@router.post(
    "/resources/{resource_id}/rechunk",
    response_model=APIResponse[DocumentChunkingJobRead],
    status_code=status.HTTP_202_ACCEPTED,
    summary="Re-chunk a document (Faculty/Admin only)",
    description="Force re-chunking of a resource, deleting any prior chunks.",
)
async def rechunk_resource(
    resource_id: uuid.UUID,
    background_tasks: BackgroundTasks,
    _user: FacultyUser,
    db: AsyncSession = Depends(get_db),
) -> APIResponse[DocumentChunkingJobRead]:
    orchestrator = ChunkingOrchestrator(db)

    # Delete previous chunks and job record first
    await orchestrator.delete_chunks(resource_id)

    # Re-queue
    job = await orchestrator.enqueue_chunking(resource_id)
    get_chunking_queue().enqueue_chunking(resource_id, background_tasks)

    return APIResponse(
        success=True,
        message="Document re-chunking started in the background.",
        data=DocumentChunkingJobRead.model_validate(job),
    )


# ── Chunking Status ───────────────────────────────────────────────────────────


@router.get(
    "/resources/{resource_id}/chunking-status",
    response_model=APIResponse[DocumentChunkingJobRead],
    summary="Get chunking job status (Faculty/Admin only)",
)
async def get_chunking_status(
    resource_id: uuid.UUID,
    _user: FacultyUser,
    db: AsyncSession = Depends(get_db),
) -> APIResponse[DocumentChunkingJobRead]:
    orchestrator = ChunkingOrchestrator(db)
    stmt = select(DocumentChunkingJob).where(DocumentChunkingJob.resource_id == resource_id)
    res = await db.execute(stmt)
    job = res.scalar_one_or_none()

    if not job:
        raise NotFoundError("Chunking job", str(resource_id))

    return APIResponse(
        success=True,
        message="Chunking status retrieved.",
        data=DocumentChunkingJobRead.model_validate(job),
    )


# ── List Chunks ───────────────────────────────────────────────────────────────


@router.get(
    "/resources/{resource_id}/chunks",
    response_model=PaginatedResponse[ChunkMappingRead],
    summary="List chunks associated with a resource (Faculty/Admin only)",
)
async def list_chunks(
    resource_id: uuid.UUID,
    _user: FacultyUser,
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
) -> PaginatedResponse[ChunkMappingRead]:
    orchestrator = ChunkingOrchestrator(db)
    mappings = await orchestrator._mapping_repo.list_by_resource(
        resource_id, skip=skip, limit=limit
    )

    # Count total mappings
    cnt_stmt = select(func.count(ChunkMapping.id)).where(ChunkMapping.resource_id == resource_id)
    cnt_res = await db.execute(cnt_stmt)
    total = cnt_res.scalar_one()

    pages = (total + limit - 1) // limit

    return PaginatedResponse(
        success=True,
        message="Resource chunks retrieved successfully.",
        data=[ChunkMappingRead.model_validate(m) for m in mappings],
        total=total,
        page=(skip // limit) + 1,
        per_page=limit,
        pages=pages,
    )


# ── Admin endpoints ───────────────────────────────────────────────────────────


@router.get(
    "/chunks/statistics",
    response_model=APIResponse[ChunkStatistics],
    summary="Get global chunk database statistics (Admin only)",
)
async def get_chunk_statistics(
    _user: AdminUser,
    db: AsyncSession = Depends(get_db),
) -> APIResponse[ChunkStatistics]:
    orchestrator = ChunkingOrchestrator(db)
    stats = await orchestrator._mapping_repo.get_global_statistics()

    return APIResponse(
        success=True,
        message="Global statistics retrieved.",
        data=ChunkStatistics(**stats),
    )


@router.get(
    "/chunks/quality-report",
    response_model=APIResponse[list[ChunkQualityReportItem]],
    summary="Get chunk quality report (Admin only)",
)
async def get_chunk_quality_report(
    _user: AdminUser,
    db: AsyncSession = Depends(get_db),
) -> APIResponse[list[ChunkQualityReportItem]]:
    orchestrator = ChunkingOrchestrator(db)
    report = await orchestrator._mapping_repo.get_quality_report()

    return APIResponse(
        success=True,
        message="Quality report generated.",
        data=[ChunkQualityReportItem(**item) for item in report],
    )


# ── Chunk Details ─────────────────────────────────────────────────────────────



@router.get(
    "/chunks/{mapping_id}",
    response_model=APIResponse[ChunkDetailsRead],
    summary="Get specific chunk instance details (Faculty/Admin only)",
)
async def get_chunk_details(
    mapping_id: uuid.UUID,
    _user: FacultyUser,
    db: AsyncSession = Depends(get_db),
) -> APIResponse[ChunkDetailsRead]:
    orchestrator = ChunkingOrchestrator(db)
    mapping = await orchestrator._mapping_repo.get_mapping_with_details(mapping_id)

    if not mapping:
        raise NotFoundError("Chunk mapping", str(mapping_id))

    # Form the combined details response
    data = ChunkDetailsRead(
        id=mapping.id,
        chunk_index=mapping.chunk_index,
        page_numbers=mapping.page_numbers,
        chunk_title=mapping.chunk_title,
        resource_id=mapping.resource_id,
        course_id=mapping.course_id,
        unit_id=mapping.unit_id,
        topic_id=mapping.topic_id,
        course_outcome_id=mapping.course_outcome_id,
        cleaned_text=mapping.chunk.cleaned_text,
        raw_text=mapping.chunk.raw_text,
        char_count=mapping.chunk.char_count,
        word_count=mapping.chunk.word_count,
        estimated_reading_time=mapping.chunk.estimated_reading_time,
        bloom_level=mapping.bloom_level,
        knowledge_level=mapping.knowledge_level,
        resource_type=mapping.resource_type,
        chapter_name=mapping.chapter_name,
        section_heading=mapping.section_heading,
        subheading=mapping.subheading,
        created_at=mapping.created_at,
        updated_at=mapping.updated_at,
    )

    return APIResponse(
        success=True,
        message="Chunk details retrieved.",
        data=data,
    )


# ── Delete Chunks ─────────────────────────────────────────────────────────────


@router.delete(
    "/resources/{resource_id}/chunks",
    response_model=APIResponse[None],
    summary="Delete all chunks belonging to a resource (Faculty/Admin only)",
)
async def delete_chunks(
    resource_id: uuid.UUID,
    _user: FacultyUser,
    db: AsyncSession = Depends(get_db),
) -> APIResponse[None]:
    orchestrator = ChunkingOrchestrator(db)
    await orchestrator.delete_chunks(resource_id)

    return APIResponse(
        success=True,
        message="All chunks and mappings for this resource deleted successfully.",
        data=None,
    )


# ── Preview Chunking (mock) ───────────────────────────────────────────────────


class ChunkPreviewRequest(BaseModel):
    text: str
    strategy: str | None = None
    chunk_size: int = 1000
    chunk_overlap: int = 200


@router.post(
    "/resources/preview-chunk",
    response_model=APIResponse[list[ChunkPreviewItem]],
    summary="Preview chunking results on arbitrary text (Faculty/Admin only)",
)
async def preview_chunking(
    payload: ChunkPreviewRequest,
    _user: FacultyUser,
) -> APIResponse[list[ChunkPreviewItem]]:
    chunker = ChunkerFactory.get_chunker(payload.strategy)
    raw_chunks = chunker.split_text(
        payload.text,
        payload.text,
        chunk_size=payload.chunk_size,
        chunk_overlap=payload.chunk_overlap,
    )

    preview_items: list[ChunkPreviewItem] = []
    for idx, c in enumerate(raw_chunks):
        word_cnt = len(c.cleaned_text.split())
        char_cnt = len(c.cleaned_text)
        est_reading = max(0.1, word_cnt / 200.0)

        preview_items.append(
            ChunkPreviewItem(
                chunk_index=idx,
                cleaned_text=c.cleaned_text,
                char_count=char_cnt,
                word_count=word_cnt,
                estimated_reading_time=round(est_reading, 2),
                page_numbers=c.page_numbers,
                chapter_name=c.chapter_name,
                section_heading=c.section_heading,
                subheading=c.subheading,
            )
        )

    return APIResponse(
        success=True,
        message="Text chunking preview calculated.",
        data=preview_items,
    )
