"""
API routes for Phase 13 Enterprise Educational Image Retrieval & Diagram Engine.
"""

from typing import Any, Dict, List
import uuid
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.session import get_db
from app.dependencies.auth import FacultyUser, get_current_user
from app.models.user import User
from app.schemas.response import APIResponse
from app.schemas.image import (
    ImageSearchRequest,
    ImageRead,
    ImageValidationRequest,
    ImageValidationResponse,
)
from app.services.image.service import ImageRetrievalService
from app.services.image.license_validator import LicenseValidationService
from app.services.image.ranking import ImageRankingService
from app.services.image.concept_extractor import EducationalConceptExtractor
from app.repositories.image import ImageRepository

router = APIRouter(prefix="/images", tags=["Image Diagram Engine"])


@router.post(
    "/search",
    response_model=APIResponse[List[dict]],
    summary="Search for candidate educational images from provider",
)
async def search_images(
    payload: ImageSearchRequest,
    _user: FacultyUser = None,
) -> APIResponse[List[dict]]:
    service = ImageRetrievalService()
    # Resolve optimized preferred query terms
    analysis = EducationalConceptExtractor.analyze_concept(payload.topic, payload.description or "")
    concept = analysis["primary_concept"]
    pref = analysis["preferred_diagram"]
    query = f"{concept} {pref}"
    
    results = await service.provider.search_images(query, limit=10)
    return APIResponse(
        success=True,
        message=f"Search completed for query: {query}",
        data=results,
    )


@router.post(
    "/retrieve",
    response_model=APIResponse[ImageRead],
    summary="Retrieve, validate, rank, and attach educational image",
)
async def retrieve_image(
    payload: ImageSearchRequest,
    db: AsyncSession = Depends(get_db),
    _user: FacultyUser = None,
) -> APIResponse[ImageRead]:
    service = ImageRetrievalService()
    try:
        img = await service.retrieve_educational_image(
            db=db,
            topic=payload.topic,
            description=payload.description or "",
            course_id=payload.course_id,
            topic_id=payload.topic_id,
        )
        if not img:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No suitable educational diagram found for topic: {payload.topic}",
            )
        return APIResponse(
            success=True,
            message="Educational diagram retrieved and registered successfully.",
            data=ImageRead.model_validate(img),
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Image retrieval pipeline failed: {str(exc)}",
        )


@router.post(
    "/rank",
    response_model=APIResponse[List[dict]],
    summary="Rank a custom list of image candidates",
)
async def rank_candidates(
    topic: str,
    candidates: List[dict],
    _user: FacultyUser = None,
) -> APIResponse[List[dict]]:
    analysis = EducationalConceptExtractor.analyze_concept(topic, "")
    pref = analysis["preferred_diagram"]
    ranked = ImageRankingService.rank_candidates(candidates, topic, pref)
    return APIResponse(
        success=True,
        message="Candidates scored and ranked.",
        data=ranked,
    )


@router.post(
    "/validate",
    response_model=APIResponse[ImageValidationResponse],
    summary="Validate candidate license and resolution details",
)
async def validate_candidate(
    payload: ImageValidationRequest,
    _user: FacultyUser = None,
) -> APIResponse[ImageValidationResponse]:
    # 1. License Check
    norm = LicenseValidationService.normalize_license(payload.license)
    if not LicenseValidationService.is_license_valid(norm):
        return APIResponse(
            success=True,
            message="Validation completed.",
            data=ImageValidationResponse(
                success=False,
                message=f"Unsupported copyleft license: {payload.license} (normalized: {norm})",
                normalized_license=norm,
            ),
        )

    # 2. Resolution check
    if payload.width < 300 or payload.height < 200:
        return APIResponse(
            success=True,
            message="Validation completed.",
            data=ImageValidationResponse(
                success=False,
                message=f"Image resolution too low: {payload.width}x{payload.height} (min 300x200)",
                normalized_license=norm,
            ),
        )

    return APIResponse(
        success=True,
        message="Validation completed.",
        data=ImageValidationResponse(
            success=True,
            message="Validation passed successfully.",
            normalized_license=norm,
        ),
    )


@router.get(
    "/history",
    response_model=APIResponse[List[ImageRead]],
    summary="Retrieve chronological retrieved image history",
)
async def get_history(
    limit: int = 20,
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
    _user: FacultyUser = None,
) -> APIResponse[List[ImageRead]]:
    repo = ImageRepository(db)
    history = await repo.get_history(limit=limit, offset=offset)
    return APIResponse(
        success=True,
        message="Image history list retrieved.",
        data=[ImageRead.model_validate(img) for img in history],
    )


@router.get(
    "/health",
    response_model=APIResponse[dict],
    summary="Check Image Retrieval Engine health",
)
async def check_health(
    _user: User = Depends(get_current_user),
) -> APIResponse[dict]:
    return APIResponse(
        success=True,
        message="Educational image generator service is active and operational.",
        data={"status": "healthy"},
    )


@router.get(
    "/{id}",
    response_model=APIResponse[ImageRead],
    summary="Retrieve retrieved image details",
)
async def get_image_details(
    id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _user: FacultyUser = None,
) -> APIResponse[ImageRead]:
    repo = ImageRepository(db)
    img = await repo.get_by_id(id)
    if not img:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Image record not found for ID: {id}",
        )
    return APIResponse(
        success=True,
        message="Image record details retrieved.",
        data=ImageRead.model_validate(img),
    )


@router.delete(
    "/{id}",
    response_model=APIResponse[dict],
    summary="Wipe retrieved image record",
)
async def delete_image(
    id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _user: FacultyUser = None,
) -> APIResponse[dict]:
    repo = ImageRepository(db)
    deleted = await repo.delete_image(id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Image record not found for ID: {id}",
        )
    return APIResponse(
        success=True,
        message="Image record wiped successfully.",
        data={},
    )
