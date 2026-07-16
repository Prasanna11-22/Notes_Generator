"""
API routes for Phase 10 Enterprise Learning Material Generation Engine.
"""

from typing import List
import uuid
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.session import get_db
from app.dependencies.auth import FacultyUser, get_current_user
from app.models.user import User
from app.schemas.response import APIResponse
from app.schemas.learning_material import (
    LearningMaterialGenerateRequest,
    LearningMaterialRegenerateRequest,
    LearningMaterialRead,
    LearningMaterialValidationRequest,
    LearningMaterialValidationResponse,
    LearningMaterialCacheDetails,
)
from app.services.learning_material.service import LearningMaterialService
from app.services.learning_material.validator import LearningMaterialValidator
from app.services.learning_material.cache_service import LearningMaterialCacheService
from app.repositories.learning_material import LearningMaterialRepository

router = APIRouter(prefix="/learning-material", tags=["Learning Material Generator"])


@router.post(
    "/generate",
    response_model=APIResponse[dict],
    status_code=status.HTTP_200_OK,
    summary="Generate curriculum-aligned learning materials",
    description="Invokes the RAG generation pipeline to create educational content based on curriculum metadata.",
)
async def generate_material(
    payload: LearningMaterialGenerateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: FacultyUser = None,
) -> APIResponse[dict]:
    service = LearningMaterialService()
    try:
        result = await service.generate_material(
            db=db,
            course_id=payload.course_id,
            topic_id=payload.topic_id,
            generator_type=payload.generator_type,
            bloom_level=payload.bloom_level,
            knowledge_level=payload.knowledge_level,
            teaching_style=payload.teaching_style,
            pedagogical_approach=payload.pedagogical_approach,
            difficulty=payload.difficulty,
            faculty_preferences=payload.faculty_preferences,
            output_format=payload.output_format,
            created_by=current_user.id if current_user else uuid.UUID("00000000-0000-0000-0000-000000000000"),
        )
        return APIResponse(
            success=True,
            message="Learning material generated successfully.",
            data=result,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Validation error during generation: {str(exc)}",
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Generation pipeline failed: {str(exc)}",
        )


@router.post(
    "/regenerate",
    response_model=APIResponse[dict],
    status_code=status.HTTP_200_OK,
    summary="Regenerate learning materials with updated preferences",
)
async def regenerate_material(
    payload: LearningMaterialRegenerateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: FacultyUser = None,
) -> APIResponse[dict]:
    service = LearningMaterialService()
    try:
        result = await service.regenerate_material(
            db=db,
            material_id=payload.material_id,
            faculty_preferences=payload.faculty_preferences,
            output_format=payload.output_format,
            changed_by_user_id=current_user.id if current_user else None,
        )
        return APIResponse(
            success=True,
            message="Learning material regenerated successfully.",
            data=result,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Validation error during regeneration: {str(exc)}",
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Regeneration pipeline failed: {str(exc)}",
        )


@router.post(
    "/validate",
    response_model=APIResponse[LearningMaterialValidationResponse],
    summary="Validate learning material alignment and layout",
)
async def validate_material(
    payload: LearningMaterialValidationRequest,
    _user: FacultyUser = None,
) -> APIResponse[LearningMaterialValidationResponse]:
    try:
        LearningMaterialValidator.validate_content(payload.text)
        LearningMaterialValidator.validate_educational_alignment(
            text=payload.text,
            topic=payload.topic,
            bloom_level=payload.bloom_level,
            course_outcomes=payload.course_outcomes,
        )
        return APIResponse(
            success=True,
            message="Validation completed.",
            data=LearningMaterialValidationResponse(success=True, message="Validation passed successfully."),
        )
    except ValueError as exc:
        return APIResponse(
            success=True,
            message="Validation completed.",
            data=LearningMaterialValidationResponse(success=False, message=str(exc)),
        )


@router.get(
    "/history",
    response_model=APIResponse[List[LearningMaterialRead]],
    summary="Retrieve generated history",
)
async def get_history(
    limit: int = 20,
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
    current_user: FacultyUser = None,
) -> APIResponse[List[LearningMaterialRead]]:
    repo = LearningMaterialRepository(db)
    user_id = current_user.id if current_user else uuid.UUID("00000000-0000-0000-0000-000000000000")
    history = await repo.get_history_by_user(user_id=user_id, limit=limit, offset=offset)
    return APIResponse(
        success=True,
        message="Revision history retrieved.",
        data=[LearningMaterialRead.model_validate(h) for h in history],
    )


@router.get(
    "/cache",
    response_model=APIResponse[List[LearningMaterialCacheDetails]],
    summary="Retrieve persistent cache entries",
)
async def get_cache_entries(
    db: AsyncSession = Depends(get_db),
    _user: FacultyUser = None,
) -> APIResponse[List[LearningMaterialCacheDetails]]:
    cache_service = LearningMaterialCacheService()
    entries = await cache_service.list_all(db)
    return APIResponse(
        success=True,
        message="Active cache entries retrieved.",
        data=[LearningMaterialCacheDetails.model_validate(e) for e in entries],
    )


@router.delete(
    "/cache",
    response_model=APIResponse[dict],
    summary="Purge persistent cache entries",
)
async def clear_cache(
    db: AsyncSession = Depends(get_db),
    _user: FacultyUser = None,
) -> APIResponse[dict]:
    cache_service = LearningMaterialCacheService()
    count = await cache_service.clear_all(db)
    return APIResponse(
        success=True,
        message=f"Cache cleared successfully. Purged {count} entries.",
        data={"purged_count": count},
    )


@router.get(
    "/health",
    response_model=APIResponse[dict],
    summary="Check Learning Material Engine health",
)
async def check_health(
    _user: User = Depends(get_current_user),
) -> APIResponse[dict]:
    return APIResponse(
        success=True,
        message="Learning Material generation service is active and operational.",
        data={"status": "healthy"},
    )


@router.get(
    "/{id}",
    response_model=APIResponse[LearningMaterialRead],
    summary="Retrieve generated learning material details",
)
async def get_material_details(
    id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _user: FacultyUser = None,
) -> APIResponse[LearningMaterialRead]:
    repo = LearningMaterialRepository(db)
    material = await repo.get(id)
    if not material:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Learning material not found for ID: {id}",
        )
    return APIResponse(
        success=True,
        message="Learning material details retrieved.",
        data=LearningMaterialRead.model_validate(material),
    )


@router.delete(
    "/{id}",
    response_model=APIResponse[dict],
    summary="Wipe learning material record",
)
async def delete_material(
    id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _user: FacultyUser = None,
) -> APIResponse[dict]:
    repo = LearningMaterialRepository(db)
    deleted = await repo.delete_material(id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Learning material not found for ID: {id}",
        )
    return APIResponse(
        success=True,
        message="Learning material wiped successfully.",
        data={},
    )
