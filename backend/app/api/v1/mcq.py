"""
API routes for Phase 11 Enterprise MCQ Generation Engine.
"""

from typing import List
import uuid
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.session import get_db
from app.dependencies.auth import FacultyUser, get_current_user
from app.models.user import User
from app.schemas.response import APIResponse
from app.schemas.mcq import (
    MCQGenerateRequest,
    MCQRegenerateRequest,
    MCQQuestionRead,
    MCQValidationRequest,
    MCQValidationResponse,
)
from app.services.mcq.service import MCQOrchestratorService
from app.services.mcq.validator import MCQValidator
from app.repositories.mcq import MCQRepository

router = APIRouter(prefix="/mcq", tags=["MCQ Generator"])


@router.post(
    "/generate",
    response_model=APIResponse[List[MCQQuestionRead]],
    status_code=status.HTTP_200_OK,
    summary="Generate curriculum-aligned MCQs",
)
async def generate_mcqs(
    payload: MCQGenerateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: FacultyUser = None,
) -> APIResponse[List[MCQQuestionRead]]:
    service = MCQOrchestratorService()
    try:
        results = await service.generate_mcqs(
            db=db,
            course_id=payload.course_id,
            topic_id=payload.topic_id,
            bloom_distribution=payload.bloom_distribution,
            difficulty=payload.difficulty,
            number_of_questions=payload.number_of_questions,
            faculty_preferences=payload.faculty_preferences,
            created_by=current_user.id if current_user else uuid.UUID("00000000-0000-0000-0000-000000000000"),
        )
        return APIResponse(
            success=True,
            message=f"Generated {len(results)} MCQs successfully.",
            data=[MCQQuestionRead.model_validate(q) for q in results],
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Validation error during MCQ generation: {str(exc)}",
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"MCQ generation pipeline failed: {str(exc)}",
        )


@router.post(
    "/regenerate",
    response_model=APIResponse[MCQQuestionRead],
    status_code=status.HTTP_200_OK,
    summary="Regenerate a single MCQ",
)
async def regenerate_mcq(
    payload: MCQRegenerateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: FacultyUser = None,
) -> APIResponse[MCQQuestionRead]:
    repo = MCQRepository(db)
    question = await repo.get(payload.question_id)
    if not question:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"MCQ question not found for ID: {payload.question_id}",
        )

    service = MCQOrchestratorService()
    try:
        # Re-run pipeline for a single question with the exact same parameters but updated preferences
        # We define a 100% Bloom distribution for the question's specific Bloom level
        bloom_dist = {question.bloom_level: 1.0}
        results = await service.generate_mcqs(
            db=db,
            course_id=question.course_id,
            topic_id=question.topic_id,
            bloom_distribution=bloom_dist,
            difficulty=question.difficulty,
            number_of_questions=1,
            faculty_preferences=payload.faculty_preferences,
            created_by=question.created_by,
        )

        if not results:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="MCQ regeneration pipeline returned zero questions.",
            )

        fresh_q = results[0]

        # Log history revision before saving
        old_entry = {
            "question_text": question.question_text,
            "options": question.options,
            "correct_answer": question.correct_answer,
            "explanation": question.explanation,
            "timestamp": datetime.utcnow().isoformat(),
            "updated_by": str(current_user.id) if current_user else str(question.created_by),
        }
        
        current_history = list(question.history) if question.history else []
        current_history.append(old_entry)

        # Overwrite values of the existing question to maintain history version lineage
        question.question_text = fresh_q.question_text
        question.options = fresh_q.options
        question.correct_answer = fresh_q.correct_answer
        question.explanation = fresh_q.explanation
        question.history = current_history
        question.updated_at = datetime.utcnow()
        
        # Remove the freshly added redundant question to keep table normalized
        await repo.delete(fresh_q)
        await db.flush()

        return APIResponse(
            success=True,
            message="MCQ question regenerated successfully.",
            data=MCQQuestionRead.model_validate(question),
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Validation error during MCQ regeneration: {str(exc)}",
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"MCQ regeneration failed: {str(exc)}",
        )


@router.post(
    "/validate",
    response_model=APIResponse[MCQValidationResponse],
    summary="Validate manual MCQ alignment and distractors",
)
async def validate_mcq(
    payload: MCQValidationRequest,
    _user: FacultyUser = None,
) -> APIResponse[MCQValidationResponse]:
    try:
        MCQValidator.validate_mcq_structure(payload.question_text, payload.options, payload.correct_answer)
        MCQValidator.validate_educational_alignment(
            question_text=payload.question_text,
            topic=payload.topic,
            bloom_level=payload.bloom_level,
        )
        return APIResponse(
            success=True,
            message="Validation completed.",
            data=MCQValidationResponse(success=True, message="Validation passed successfully."),
        )
    except ValueError as exc:
        return APIResponse(
            success=True,
            message="Validation completed.",
            data=MCQValidationResponse(success=False, message=str(exc)),
        )


@router.get(
    "/history",
    response_model=APIResponse[List[MCQQuestionRead]],
    summary="Retrieve generated MCQ history",
)
async def get_history(
    limit: int = 20,
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
    current_user: FacultyUser = None,
) -> APIResponse[List[MCQQuestionRead]]:
    repo = MCQRepository(db)
    user_id = current_user.id if current_user else uuid.UUID("00000000-0000-0000-0000-000000000000")
    history = await repo.get_history_by_user(user_id=user_id, limit=limit, offset=offset)
    return APIResponse(
        success=True,
        message="MCQ generation history retrieved.",
        data=[MCQQuestionRead.model_validate(q) for q in history],
    )


@router.get(
    "/health",
    response_model=APIResponse[dict],
    summary="Check MCQ Generator Engine health",
)
async def check_health(
    _user: User = Depends(get_current_user),
) -> APIResponse[dict]:
    return APIResponse(
        success=True,
        message="MCQ generation service is active and operational.",
        data={"status": "healthy"},
    )


@router.get(
    "/{id}",
    response_model=APIResponse[MCQQuestionRead],
    summary="Retrieve generated MCQ details",
)
async def get_mcq_details(
    id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _user: FacultyUser = None,
) -> APIResponse[MCQQuestionRead]:
    repo = MCQRepository(db)
    question = await repo.get(id)
    if not question:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"MCQ question not found for ID: {id}",
        )
    return APIResponse(
        success=True,
        message="MCQ question details retrieved.",
        data=MCQQuestionRead.model_validate(question),
    )


@router.delete(
    "/{id}",
    response_model=APIResponse[dict],
    summary="Wipe MCQ record",
)
async def delete_mcq(
    id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _user: FacultyUser = None,
) -> APIResponse[dict]:
    repo = MCQRepository(db)
    deleted = await repo.delete_question(id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"MCQ question not found for ID: {id}",
        )
    return APIResponse(
        success=True,
        message="MCQ question wiped successfully.",
        data={},
    )
