"""
Educational Prompt Builder API Routes.

All endpoints require at minimum Faculty role access.
Template CRUD operations require Faculty+ role.
"""

from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.session import get_db
from app.dependencies.auth import FacultyUser, get_current_user
from app.models.user import User
from app.schemas.response import APIResponse
from app.schemas.prompt import (
    PromptBuildRequest,
    PromptBuildResponse,
    PromptEstimationRequest,
    PromptEstimationResponse,
    PromptTemplateCreate,
    PromptTemplateRead,
    PromptTemplateUpdate,
    PromptValidationRequest,
    PromptValidationResponse,
)
from app.services.prompt_builder import PromptBuilderService
from app.services.prompt_validation import PromptValidationService
from app.services.prompt_template_service import PromptTemplateService
from app.services.token_estimator import TokenEstimatorService

router = APIRouter(prefix="/prompt", tags=["Prompt Builder"])


@router.post("/build", response_model=APIResponse[PromptBuildResponse])
async def build_educational_prompt(
    payload: PromptBuildRequest,
    db: AsyncSession = Depends(get_db),
    _user: FacultyUser = None,  # noqa: B008  Annotated dep — default not used
) -> APIResponse[PromptBuildResponse]:
    """
    Build a hydrated, optimized, and token-truncated educational prompt payload.

    Requires Faculty+ role.  Validates all educational fields, detects prompt
    injection attempts, and enforces token budget constraints before returning
    the assembled prompt structure.
    """
    service = PromptBuilderService(db)
    try:
        result = await service.build_prompt(
            generation_type=payload.generation_type,
            retrieved_chunks=[c.model_dump() for c in payload.retrieved_chunks],
            topic=payload.topic,
            course=payload.course,
            course_outcomes=payload.course_outcomes,
            unit=payload.unit,
            bloom_distribution=payload.bloom_distribution,
            knowledge_level=payload.knowledge_level,
            teaching_style=payload.teaching_style,
            pedagogical_approach=payload.pedagogical_approach,
            difficulty=payload.difficulty,
            faculty_preferences=payload.faculty_preferences,
            max_tokens=payload.max_tokens,
        )
        return APIResponse(
            success=True,
            message="Prompt successfully generated.",
            data=PromptBuildResponse.model_validate(result),
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/validate", response_model=APIResponse[PromptValidationResponse])
async def validate_prompt_constraints(
    payload: PromptValidationRequest,
    _user: FacultyUser = None,
) -> APIResponse[PromptValidationResponse]:
    """
    Validate educational constraints and verify token size bounds.

    Checks presence of all required fields, scans for prompt injection patterns,
    and confirms the full_prompt fits within the specified token budget.
    Requires Faculty+ role.
    """
    validator = PromptValidationService()
    try:
        validator.validate_inputs(
            retrieved_context=payload.retrieved_context,
            topic=payload.topic,
            bloom_distribution=payload.bloom_distribution,
            educational_constraints=payload.educational_constraints,
            faculty_preferences=payload.faculty_preferences,
            course_outcomes=payload.course_outcomes,
        )
        tokens = validator.validate_size(payload.full_prompt, payload.max_tokens)
        return APIResponse(
            success=True,
            message="Prompt constraints validated successfully.",
            data=PromptValidationResponse(
                success=True,
                message="Valid prompt configuration.",
                estimated_tokens=tokens,
            ),
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/estimate", response_model=APIResponse[PromptEstimationResponse])
async def estimate_prompt_tokens(
    payload: PromptEstimationRequest,
    _user: FacultyUser = None,
) -> APIResponse[PromptEstimationResponse]:
    """
    Estimate token usage for a given text string.

    Uses the 1-token ≈ 4-characters heuristic.  Intended for pre-flight budget
    checks.  Requires Faculty+ role.
    """
    tokens = TokenEstimatorService.estimate_tokens(payload.text)
    return APIResponse(
        success=True,
        message="Token count estimated successfully.",
        data=PromptEstimationResponse(estimated_tokens=tokens),
    )


@router.get("/templates", response_model=APIResponse[list[PromptTemplateRead]])
async def list_prompt_templates(
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_user),
) -> APIResponse[list[PromptTemplateRead]]:
    """
    List all prompt templates (system defaults + custom).

    Accessible to any authenticated user.
    """
    svc = PromptTemplateService(db)
    templates = await svc.get_all_templates(limit=1000)
    return APIResponse(
        success=True,
        message="Templates retrieved successfully.",
        data=[PromptTemplateRead.model_validate(t) for t in templates],
    )


@router.post("/template", response_model=APIResponse[PromptTemplateRead])
async def create_custom_template(
    payload: PromptTemplateCreate,
    db: AsyncSession = Depends(get_db),
    _faculty: FacultyUser = None,
) -> APIResponse[PromptTemplateRead]:
    """
    Create a new custom prompt template.

    Requires Faculty+ role.  System defaults cannot be overridden via this
    endpoint — all templates created here have ``is_system_default=False``.
    """
    svc = PromptTemplateService(db)
    try:
        template = await svc.create_custom_template(
            name=payload.name,
            generation_type=payload.generation_type,
            system_prompt=payload.system_prompt,
            instruction_prompt=payload.instruction_prompt,
            educational_constraints=payload.educational_constraints,
            output_format=payload.output_format,
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    return APIResponse(
        success=True,
        message="Custom prompt template created successfully.",
        data=PromptTemplateRead.model_validate(template),
    )


@router.put("/template/{template_id}", response_model=APIResponse[PromptTemplateRead])
async def update_custom_template(
    template_id: UUID,
    payload: PromptTemplateUpdate,
    db: AsyncSession = Depends(get_db),
    _faculty: FacultyUser = None,
) -> APIResponse[PromptTemplateRead]:
    """
    Update an existing custom prompt template.

    Requires Faculty+ role.  System default templates cannot be modified.
    """
    svc = PromptTemplateService(db)
    update_data = payload.model_dump(exclude_unset=True)
    try:
        template = await svc.update_custom_template(template_id, update_data)
    except ValueError as e:
        detail = str(e)
        if "not found" in detail.lower():
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=detail)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=detail)

    return APIResponse(
        success=True,
        message="Prompt template updated successfully.",
        data=PromptTemplateRead.model_validate(template),
    )


@router.delete("/template/{template_id}", response_model=APIResponse[dict])
async def delete_custom_template(
    template_id: UUID,
    db: AsyncSession = Depends(get_db),
    _faculty: FacultyUser = None,
) -> APIResponse[dict]:
    """
    Delete a custom prompt template.

    Requires Faculty+ role.  System default templates cannot be deleted.
    """
    svc = PromptTemplateService(db)
    try:
        await svc.delete_custom_template(template_id)
    except ValueError as e:
        detail = str(e)
        if "not found" in detail.lower():
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=detail)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=detail)

    return APIResponse(
        success=True,
        message="Prompt template deleted successfully.",
        data={"deleted_id": str(template_id)},
    )


@router.get("/health", response_model=APIResponse[dict])
async def get_prompt_health(
    _user: User = Depends(get_current_user),
) -> APIResponse[dict]:
    """
    Health check endpoint verifying the prompt builder module is active.

    Accessible to any authenticated user.
    """
    return APIResponse(
        success=True,
        message="Prompt builder service is healthy and active.",
        data={"status": "healthy"},
    )
