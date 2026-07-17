"""
API routes for Phase 12 Enterprise Assignment & Learning Activity Generation Engine.
"""

from typing import List
from datetime import datetime
import uuid
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.session import get_db
from app.dependencies.auth import FacultyUser, get_current_user
from app.models.user import User
from app.schemas.response import APIResponse
from app.schemas.assignment import (
    AssignmentGenerateRequest,
    AssignmentRegenerateRequest,
    AssignmentRead,
    AssignmentValidationRequest,
    AssignmentValidationResponse,
)
from app.services.assignment.service import AssignmentOrchestratorService
from app.services.assignment.validator import AssignmentValidator
from app.services.assignment.rubric import RubricPreparationService
from app.repositories.assignment import AssignmentRepository

router = APIRouter(prefix="/assignments", tags=["Assignment Generator"])


@router.post(
    "/generate",
    response_model=APIResponse[AssignmentRead],
    status_code=status.HTTP_200_OK,
    summary="Generate curriculum-aligned assignments or learning activities",
)
async def generate_assignment(
    payload: AssignmentGenerateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: FacultyUser = None,
) -> APIResponse[AssignmentRead]:
    service = AssignmentOrchestratorService()
    try:
        result = await service.generate_assignment(
            db=db,
            course_id=payload.course_id,
            topic_id=payload.topic_id,
            generator_type=payload.generator_type,
            bloom_level=payload.bloom_level,
            difficulty=payload.difficulty,
            marks=payload.marks,
            knowledge_level=payload.knowledge_level,
            teaching_style=payload.teaching_style,
            pedagogical_approach=payload.pedagogical_approach,
            faculty_preferences=payload.faculty_preferences,
            created_by=current_user.id if current_user else uuid.UUID("00000000-0000-0000-0000-000000000000"),
        )
        return APIResponse(
            success=True,
            message="Generated assignment successfully.",
            data=AssignmentRead.model_validate(result),
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Validation error during assignment generation: {str(exc)}",
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Assignment generation pipeline failed: {str(exc)}",
        )


@router.post(
    "/regenerate",
    response_model=APIResponse[AssignmentRead],
    status_code=status.HTTP_200_OK,
    summary="Regenerate a single assignment",
)
async def regenerate_assignment(
    payload: AssignmentRegenerateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: FacultyUser = None,
) -> APIResponse[AssignmentRead]:
    repo = AssignmentRepository(db)
    assignment = await repo.get_by_id(payload.assignment_id)
    if not assignment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Assignment not found for ID: {payload.assignment_id}",
        )

    service = AssignmentOrchestratorService()
    try:
        fresh_assignment = await service.generate_assignment(
            db=db,
            course_id=assignment.course_id,
            topic_id=assignment.topic_id,
            generator_type=assignment.generator_type,
            bloom_level=assignment.bloom_level,
            difficulty=assignment.difficulty,
            marks=assignment.marks,
            faculty_preferences=payload.faculty_preferences,
            created_by=assignment.created_by,
        )

        old_entry = {
            "content": assignment.content,
            "rubric": assignment.rubric,
            "timestamp": datetime.utcnow().isoformat(),
            "updated_by": str(current_user.id) if current_user else str(assignment.created_by),
        }
        
        current_history = list(assignment.history) if assignment.history else []
        current_history.append(old_entry)

        assignment.content = fresh_assignment.content
        assignment.rubric = fresh_assignment.rubric
        assignment.history = current_history
        assignment.updated_at = datetime.utcnow()
        
        await repo.delete(fresh_assignment)
        await db.flush()

        return APIResponse(
            success=True,
            message="Assignment regenerated successfully.",
            data=AssignmentRead.model_validate(assignment),
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Validation error during assignment regeneration: {str(exc)}",
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Assignment regeneration failed: {str(exc)}",
        )


@router.post(
    "/validate",
    response_model=APIResponse[AssignmentValidationResponse],
    summary="Validate assignment pedagogical and educational alignment",
)
async def validate_assignment(
    payload: AssignmentValidationRequest,
    _user: FacultyUser = None,
) -> APIResponse[AssignmentValidationResponse]:
    try:
        AssignmentValidator.validate_educational_alignment(
            content=payload.content,
            topic=payload.topic,
            bloom_level=payload.bloom_level,
            difficulty=payload.difficulty,
            pedagogical_approach=payload.pedagogical_approach,
            teaching_style=payload.teaching_style,
        )
        RubricPreparationService.validate_rubric_structure(payload.rubric)
        return APIResponse(
            success=True,
            message="Validation completed.",
            data=AssignmentValidationResponse(success=True, message="Validation passed successfully."),
        )
    except ValueError as exc:
        return APIResponse(
            success=True,
            message="Validation completed.",
            data=AssignmentValidationResponse(success=False, message=str(exc)),
        )


@router.get(
    "/history",
    response_model=APIResponse[List[AssignmentRead]],
    summary="Retrieve generated assignment history",
)
async def get_history(
    limit: int = 20,
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
    current_user: FacultyUser = None,
) -> APIResponse[List[AssignmentRead]]:
    repo = AssignmentRepository(db)
    user_id = current_user.id if current_user else uuid.UUID("00000000-0000-0000-0000-000000000000")
    history = await repo.get_history_by_user(user_id=user_id, limit=limit, offset=offset)
    return APIResponse(
        success=True,
        message="Assignment history retrieved.",
        data=[AssignmentRead.model_validate(a) for a in history],
    )


@router.get(
    "/health",
    response_model=APIResponse[dict],
    summary="Check Assignment Generator health",
)
async def check_health(
    _user: User = Depends(get_current_user),
) -> APIResponse[dict]:
    return APIResponse(
        success=True,
        message="Assignment generator service is active and operational.",
        data={"status": "healthy"},
    )


@router.get(
    "/{id}",
    response_model=APIResponse[AssignmentRead],
    summary="Retrieve generated assignment details",
)
async def get_assignment_details(
    id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _user: FacultyUser = None,
) -> APIResponse[AssignmentRead]:
    repo = AssignmentRepository(db)
    assignment = await repo.get_by_id(id)
    if not assignment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Assignment not found for ID: {id}",
        )
    return APIResponse(
        success=True,
        message="Assignment details retrieved.",
        data=AssignmentRead.model_validate(assignment),
    )


@router.delete(
    "/{id}",
    response_model=APIResponse[dict],
    summary="Wipe assignment record",
)
async def delete_assignment(
    id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _user: FacultyUser = None,
) -> APIResponse[dict]:
    repo = AssignmentRepository(db)
    deleted = await repo.delete_assignment(id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Assignment not found for ID: {id}",
        )
    return APIResponse(
        success=True,
        message="Assignment record wiped successfully.",
        data={},
    )
