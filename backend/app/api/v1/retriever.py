"""
Semantic Retrieval and Context Engine API Routes.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.session import get_db
from app.dependencies.auth import get_current_user
from app.models.user import User
from app.schemas.response import APIResponse
from app.schemas.retriever import (
    ContextChunkRead,
    ContextPackageRead,
    RetrieveCourseRequest,
    RetrieveRequest,
    RetrieveTopKRequest,
    RetrieveTopicRequest,
    RetrieveUnitRequest,
)
from app.services.retriever import RetrieverService
from app.core.config import settings

router = APIRouter(prefix="/retrieve", tags=["Retrieval"])


@router.post("", response_model=APIResponse[list[ContextChunkRead]])
async def retrieve_chunks(
    payload: RetrieveRequest,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_user),
) -> APIResponse[list[ContextChunkRead]]:
    """
    Search and retrieve matching educational context chunks, applying optional metadata filters.
    """
    service = RetrieverService(db)
    filter_dict = payload.filters.model_dump() if payload.filters else None

    try:
        context = await service.retrieve_context(
            query=payload.query,
            limit=payload.limit,
            filters=filter_dict,
            relevance_threshold=payload.relevance_threshold,
        )
        return APIResponse(
            success=True,
            message="Successfully retrieved semantically relevant chunks.",
            data=[ContextChunkRead.model_validate(c) for c in context["chunks"]],
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/top-k", response_model=APIResponse[list[ContextChunkRead]])
async def retrieve_top_k(
    payload: RetrieveTopKRequest,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_user),
) -> APIResponse[list[ContextChunkRead]]:
    """
    Simpler retrieval endpoint returning the top-K relevant chunks without metadata filters.
    """
    service = RetrieverService(db)
    try:
        context = await service.retrieve_context(
            query=payload.query,
            limit=payload.k,
        )
        return APIResponse(
            success=True,
            message=f"Successfully retrieved top {payload.k} chunks.",
            data=[ContextChunkRead.model_validate(c) for c in context["chunks"]],
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/course", response_model=APIResponse[list[ContextChunkRead]])
async def retrieve_by_course(
    payload: RetrieveCourseRequest,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_user),
) -> APIResponse[list[ContextChunkRead]]:
    """
    Retrieve relevant chunks filtered strictly by a specific Course ID.
    """
    service = RetrieverService(db)
    try:
        context = await service.retrieve_context(
            query=payload.query,
            limit=payload.limit,
            filters={"course_id": payload.course_id},
        )
        return APIResponse(
            success=True,
            message="Successfully retrieved chunks matching course criteria.",
            data=[ContextChunkRead.model_validate(c) for c in context["chunks"]],
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/topic", response_model=APIResponse[list[ContextChunkRead]])
async def retrieve_by_topic(
    payload: RetrieveTopicRequest,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_user),
) -> APIResponse[list[ContextChunkRead]]:
    """
    Retrieve relevant chunks filtered strictly by a specific Topic ID.
    """
    service = RetrieverService(db)
    try:
        context = await service.retrieve_context(
            query=payload.query,
            limit=payload.limit,
            filters={"topic_id": payload.topic_id},
        )
        return APIResponse(
            success=True,
            message="Successfully retrieved chunks matching topic criteria.",
            data=[ContextChunkRead.model_validate(c) for c in context["chunks"]],
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/unit", response_model=APIResponse[list[ContextChunkRead]])
async def retrieve_by_unit(
    payload: RetrieveUnitRequest,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_user),
) -> APIResponse[list[ContextChunkRead]]:
    """
    Retrieve relevant chunks filtered strictly by a specific Unit ID.
    """
    service = RetrieverService(db)
    try:
        context = await service.retrieve_context(
            query=payload.query,
            limit=payload.limit,
            filters={"unit_id": payload.unit_id},
        )
        return APIResponse(
            success=True,
            message="Successfully retrieved chunks matching unit criteria.",
            data=[ContextChunkRead.model_validate(c) for c in context["chunks"]],
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/context", response_model=APIResponse[ContextPackageRead])
async def retrieve_context_package(
    payload: RetrieveRequest,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_user),
) -> APIResponse[ContextPackageRead]:
    """
    Return a structured retrieval package, including a pre-formatted markdown context prompt.
    """
    service = RetrieverService(db)
    filter_dict = payload.filters.model_dump() if payload.filters else None

    try:
        context = await service.retrieve_context(
            query=payload.query,
            limit=payload.limit,
            filters=filter_dict,
            relevance_threshold=payload.relevance_threshold,
        )
        return APIResponse(
            success=True,
            message="Successfully assembled context package.",
            data=ContextPackageRead.model_validate(context),
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("/health", response_model=APIResponse[dict])
async def get_retriever_health(
    _user: User = Depends(get_current_user),
) -> APIResponse[dict]:
    """
    Health check endpoint verifying the retrieval engine state and provider config.
    """
    return APIResponse(
        success=True,
        message="Retriever service is healthy and active.",
        data={
            "status": "healthy",
            "provider": settings.retriever_provider,
        },
    )
