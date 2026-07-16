"""
Enterprise Embedding & Vector Store API routes.
"""

import uuid
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.session import get_db
from app.dependencies.auth import FacultyUser
from app.exceptions.custom import NotFoundError
from app.schemas.embedding import (
    ChunkEmbeddingRead,
    DocumentEmbeddingJobRead,
    EmbeddingGenerateRequest,
    EmbeddingRegenerateRequest,
    ReconcileResult,
    SynchronizationReport,
    VectorStoreHealthRead,
)
from app.schemas.response import APIResponse
from app.services.embedding import EmbeddingService
from app.services.embedding_queue import get_embedding_queue
from app.services.synchronization import EmbeddingSynchronizationService

router = APIRouter(tags=["Enterprise Embeddings"])


@router.post(
    "/embeddings/generate",
    response_model=APIResponse[DocumentEmbeddingJobRead],
    status_code=status.HTTP_202_ACCEPTED,
    summary="Generate embeddings for a chunked document",
    description=(
        "Triggers the vector embedding generation pipeline for a resource. "
        "The resource must have already been successfully chunked. "
        "Processes text chunks, creates vectors, inserts them into the FAISS store, "
        "and saves metadata inside PostgreSQL."
    ),
)
async def generate_embeddings(
    payload: EmbeddingGenerateRequest,
    background_tasks: BackgroundTasks,
    _user: FacultyUser,
    db: AsyncSession = Depends(get_db),
) -> APIResponse[DocumentEmbeddingJobRead]:
    service = EmbeddingService(db)

    # 1. Enqueue/Create job in database
    job = await service.generate_embeddings_for_document(payload.resource_id, force=False)

    # 2. Trigger asynchronous BackgroundTask
    get_embedding_queue().enqueue_embedding(payload.resource_id, background_tasks, force=False)

    return APIResponse(
        success=True,
        message="Embedding generation job successfully enqueued in background.",
        data=DocumentEmbeddingJobRead.model_validate(job),
    )


@router.get(
    "/embeddings/status/{id}",
    response_model=APIResponse[DocumentEmbeddingJobRead],
    summary="Get embedding generation job status",
    description="Check the current status (pending, processing, completed, failed) of an embedding job using its ID or Resource ID.",
)
async def get_embedding_job_status(
    id: uuid.UUID,
    _user: FacultyUser,
    db: AsyncSession = Depends(get_db),
) -> APIResponse[DocumentEmbeddingJobRead]:
    service = EmbeddingService(db)
    # Check by Job ID first, then by Resource ID
    job = await service.get_job(id)
    if not job:
        job = await service.get_job_by_resource(id)

    if not job:
        raise NotFoundError(f"Embedding job or resource with ID {id} not found.")

    return APIResponse(
        success=True,
        message="Embedding job status retrieved.",
        data=DocumentEmbeddingJobRead.model_validate(job),
    )


@router.get(
    "/embeddings/{id}",
    response_model=APIResponse[ChunkEmbeddingRead],
    summary="Get chunk embedding metadata",
    description="Retrieve the database metadata of a specific chunk embedding by its UUID.",
)
async def get_chunk_embedding(
    id: uuid.UUID,
    _user: FacultyUser,
    db: AsyncSession = Depends(get_db),
) -> APIResponse[ChunkEmbeddingRead]:
    service = EmbeddingService(db)
    emb = await service._embedding_repo.get_by_id(id)
    if not emb:
        raise NotFoundError(f"Chunk embedding metadata with ID {id} not found.")

    return APIResponse(
        success=True,
        message="Chunk embedding metadata retrieved.",
        data=ChunkEmbeddingRead.model_validate(emb),
    )


@router.delete(
    "/embeddings/{id}",
    response_model=APIResponse[None],
    summary="Delete a chunk embedding",
    description="Delete a chunk's embedding vector from the vector store and its metadata from PostgreSQL.",
)
async def delete_chunk_embedding(
    id: uuid.UUID,
    _user: FacultyUser,
    db: AsyncSession = Depends(get_db),
) -> APIResponse[None]:
    service = EmbeddingService(db)
    emb = await service._embedding_repo.get_by_id(id)
    if not emb:
        raise NotFoundError(f"Chunk embedding metadata with ID {id} not found.")

    # Remove vector from store
    service._vector_store_provider.delete(emb.vector_store_id)

    # Remove metadata from DB
    await service._embedding_repo.delete(emb)
    await db.flush()

    return APIResponse(
        success=True,
        message="Chunk embedding deleted successfully from database and vector store.",
        data=None,
    )


@router.post(
    "/embeddings/regenerate",
    response_model=APIResponse[DocumentEmbeddingJobRead],
    status_code=status.HTTP_202_ACCEPTED,
    summary="Force regenerate embeddings for a document",
    description=(
        "Invalidates and deletes all existing embeddings for the given resource, "
        "and triggers a full embedding regeneration pipeline in the background."
    ),
)
async def regenerate_embeddings(
    payload: EmbeddingRegenerateRequest,
    background_tasks: BackgroundTasks,
    _user: FacultyUser,
    db: AsyncSession = Depends(get_db),
) -> APIResponse[DocumentEmbeddingJobRead]:
    service = EmbeddingService(db)

    # Delete existing embeddings
    await service.delete_embeddings_for_resource(payload.resource_id)

    # Enqueue new job
    job = await service.generate_embeddings_for_document(payload.resource_id, force=True)

    # Trigger BackgroundTask
    get_embedding_queue().enqueue_embedding(payload.resource_id, background_tasks, force=True)

    return APIResponse(
        success=True,
        message="Forced embedding regeneration job successfully enqueued in background.",
        data=DocumentEmbeddingJobRead.model_validate(job),
    )


@router.get(
    "/vector-store/health",
    response_model=APIResponse[VectorStoreHealthRead],
    summary="Vector database health check",
    description="Query the operational status, total loaded vectors, and dimensions of the vector store (FAISS).",
)
async def get_vector_store_health(
    _user: FacultyUser,
    db: AsyncSession = Depends(get_db),
) -> APIResponse[VectorStoreHealthRead]:
    service = EmbeddingService(db)
    provider = service._vector_store_provider
    is_healthy = provider.health_check()

    # Duck-typing index queries to check size
    index_size = 0
    if hasattr(provider, "index") and provider.index:
        index_size = provider.index.ntotal

    return APIResponse(
        success=True,
        message="Vector store health retrieved.",
        data=VectorStoreHealthRead(
            status="healthy" if is_healthy else "unhealthy",
            index_loaded=provider.index is not None,
            total_vectors=index_size,
            dimension=provider.dimension,
        ),
    )


@router.post(
    "/vector-store/rebuild",
    response_model=APIResponse[None],
    summary="Rebuild vector database index from database metadata",
    description=(
        "Clears the vector store index and rebuilds all vector embeddings "
        "by pulling text chunks from PostgreSQL and running embedding generation."
    ),
)
async def rebuild_vector_store(
    _user: FacultyUser,
    db: AsyncSession = Depends(get_db),
) -> APIResponse[None]:
    sync_service = EmbeddingSynchronizationService(db)
    await sync_service.rebuild_index()
    return APIResponse(
        success=True,
        message="Vector store index rebuild complete.",
        data=None,
    )


@router.get(
    "/synchronization/report",
    response_model=APIResponse[SynchronizationReport],
    summary="Get PostgreSQL vs Vector Store synchronization report",
    description="Scans the database metadata and vector store index to detect any orphaned records or missing vector embeddings.",
)
async def get_sync_report(
    _user: FacultyUser,
    db: AsyncSession = Depends(get_db),
) -> APIResponse[SynchronizationReport]:
    sync_service = EmbeddingSynchronizationService(db)
    report_data = await sync_service.get_synchronization_report()
    return APIResponse(
        success=True,
        message="Synchronization report generated.",
        data=SynchronizationReport(**report_data),
    )


@router.post(
    "/synchronization/reconcile",
    response_model=APIResponse[ReconcileResult],
    summary="Reconcile and repair Postgres vs Vector Store discrepancies",
    description=(
        "Automatically heals alignment discrepancies: deletes orphaned vectors from vector store, "
        "and regenerates missing vector embeddings for database chunks."
    ),
)
async def reconcile_store(
    _user: FacultyUser,
    db: AsyncSession = Depends(get_db),
) -> APIResponse[ReconcileResult]:
    sync_service = EmbeddingSynchronizationService(db)
    result = await sync_service.reconcile()
    return APIResponse(
        success=True,
        message="Reconciliation pipeline executed successfully.",
        data=ReconcileResult(**result),
    )
