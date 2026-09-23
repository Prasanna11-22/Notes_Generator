"""
API routes for Phase 14 Academic Quality & Intelligence Engine.
"""

from typing import Any, Dict, List
import uuid
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.session import get_db
from app.dependencies.auth import FacultyUser, get_current_user
from app.models.user import User
from app.schemas.response import APIResponse
from app.schemas.quality import (
    QualityValidationRequest,
    QualityReportRead,
)
from app.services.quality.service import AcademicValidationService
from app.services.quality.analytics import AnalyticsService
from app.repositories.quality import QualityReportRepository

router = APIRouter(prefix="/quality", tags=["Academic Quality Assurance"])


@router.post(
    "/validate",
    response_model=APIResponse[dict],
    summary="Validate educational content parameters and compute scores",
)
async def validate_content(
    payload: QualityValidationRequest,
    _user: FacultyUser = None,
) -> APIResponse[dict]:
    results = AcademicValidationService.run_qa_pipeline(
        content=payload.content,
        topic_name=payload.topic_name,
        target_bloom=payload.target_bloom,
        target_difficulty=payload.target_difficulty,
        topic_description=payload.topic_description,
        unit_title=payload.unit_title,
        course_outcomes=payload.course_outcomes,
        teaching_style=payload.teaching_style,
        expected_length=payload.expected_length,
        preferred_examples=payload.preferred_examples,
    )
    return APIResponse(
        success=True,
        message="Educational QA validation completed successfully.",
        data=results,
    )


@router.post(
    "/report",
    response_model=APIResponse[QualityReportRead],
    summary="Run validation and persist quality audit report in database",
)
async def create_quality_report(
    payload: QualityValidationRequest,
    db: AsyncSession = Depends(get_db),
    _user: FacultyUser = None,
) -> APIResponse[QualityReportRead]:
    try:
        report = await AcademicValidationService.create_quality_report(
            db=db,
            content=payload.content,
            topic_name=payload.topic_name,
            target_bloom=payload.target_bloom,
            target_difficulty=payload.target_difficulty,
            content_id=payload.content_id,
            content_type=payload.content_type,
            topic_description=payload.topic_description,
            unit_title=payload.unit_title,
            course_outcomes=payload.course_outcomes,
            teaching_style=payload.teaching_style,
            expected_length=payload.expected_length,
            preferred_examples=payload.preferred_examples,
        )
        return APIResponse(
            success=True,
            message="Quality report compiled and saved successfully.",
            data=QualityReportRead.model_validate(report),
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate and save quality report: {str(exc)}",
        )


@router.get(
    "/analytics",
    response_model=APIResponse[dict],
    summary="Retrieve system-wide QA and generation analytics",
)
async def get_system_analytics(
    db: AsyncSession = Depends(get_db),
    _user: FacultyUser = None,
) -> APIResponse[dict]:
    stats = await AnalyticsService.get_dashboard_analytics(db)
    return APIResponse(
        success=True,
        message="System analytics aggregated successfully.",
        data=stats,
    )


@router.get(
    "/dashboard",
    response_model=APIResponse[dict],
    summary="Retrieve QA dashboard summary containing stats and recent history",
)
async def get_dashboard_summary(
    db: AsyncSession = Depends(get_db),
    _user: FacultyUser = None,
) -> APIResponse[dict]:
    stats = await AnalyticsService.get_dashboard_analytics(db)
    repo = QualityReportRepository(db)
    recent_reports = await repo.get_history(limit=5)
    
    dashboard_data = {
        "metrics": stats["average_system_metrics"],
        "statistics": stats["generation_statistics"],
        "bloom_distribution": stats["bloom_distribution"],
        "difficulty_distribution": stats["difficulty_distribution"],
        "recent_audits": [QualityReportRead.model_validate(r) for r in recent_reports],
    }
    return APIResponse(
        success=True,
        message="Dashboard summary loaded.",
        data=dashboard_data,
    )


@router.get(
    "/history",
    response_model=APIResponse[List[QualityReportRead]],
    summary="Retrieve chronological list of validation logs",
)
async def get_history_logs(
    limit: int = 20,
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
    _user: FacultyUser = None,
) -> APIResponse[List[QualityReportRead]]:
    repo = QualityReportRepository(db)
    history = await repo.get_history(limit=limit, offset=offset)
    return APIResponse(
        success=True,
        message="Quality report logs retrieved.",
        data=[QualityReportRead.model_validate(r) for r in history],
    )


@router.get(
    "/health",
    response_model=APIResponse[dict],
    summary="Check QA and Academic Intelligence health status",
)
async def get_qa_health(
    _user: User = Depends(get_current_user),
) -> APIResponse[dict]:
    return APIResponse(
        success=True,
        message="Quality Assurance engine is active and operational.",
        data={"status": "healthy"},
    )


@router.get(
    "/{id}",
    response_model=APIResponse[QualityReportRead],
    summary="Retrieve details of a saved quality report",
)
async def get_report_details(
    id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _user: FacultyUser = None,
) -> APIResponse[QualityReportRead]:
    repo = QualityReportRepository(db)
    report = await repo.get_by_id(id)
    if not report:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Quality report not found for ID: {id}",
        )
    return APIResponse(
        success=True,
        message="Quality report audit details retrieved.",
        data=QualityReportRead.model_validate(report),
    )
