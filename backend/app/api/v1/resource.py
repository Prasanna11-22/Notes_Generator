"""
Resource Management API Routes.
"""

import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, File, Form, Query, UploadFile, status
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.session import get_db
from app.dependencies.auth import FacultyUser
from app.schemas.resource import ResourceRead, ResourceUpdate
from app.schemas.response import APIResponse, PaginatedResponse
from app.services.resource import ResourceService

router = APIRouter(prefix="/resources", tags=["Resource Management"])


# ── Upload Resource ───────────────────────────────────────────────────────────
@router.post(
    "",
    response_model=APIResponse[ResourceRead],
    status_code=status.HTTP_201_CREATED,
    summary="Upload a new course resource (Faculty/Admin only)",
)
async def upload_resource(
    user: FacultyUser,
    course_id: uuid.UUID = Form(...),
    title: str = Form(...),
    description: str | None = Form(None),
    resource_type: str = Form("Other"),
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
) -> APIResponse[ResourceRead]:
    service = ResourceService(db)
    content_bytes = await file.read()

    resource = await service.upload_resource(
        course_id=course_id,
        uploaded_by=user.id,
        title=title,
        description=description,
        resource_type=resource_type,
        file_content=content_bytes,
        original_file_name=file.filename or "unknown_file",
        mime_type=file.content_type or "application/octet-stream",
    )

    return APIResponse(
        success=True,
        message="Resource uploaded successfully.",
        data=ResourceRead.model_validate(resource),
    )


# ── Upload New Version ────────────────────────────────────────────────────────
@router.post(
    "/{resource_id}/versions",
    response_model=APIResponse[ResourceRead],
    status_code=status.HTTP_201_CREATED,
    summary="Upload a new version of an existing resource (Faculty/Admin only)",
)
async def upload_version(
    resource_id: uuid.UUID,
    user: FacultyUser,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
) -> APIResponse[ResourceRead]:
    service = ResourceService(db)
    content_bytes = await file.read()

    new_version = await service.upload_new_version(
        resource_id=resource_id,
        uploaded_by=user.id,
        file_content=content_bytes,
        original_file_name=file.filename or "unknown_file",
        mime_type=file.content_type or "application/octet-stream",
    )

    return APIResponse(
        success=True,
        message="New version uploaded successfully.",
        data=ResourceRead.model_validate(new_version),
    )


# ── Restore Version ───────────────────────────────────────────────────────────
@router.post(
    "/{resource_id}/restore",
    response_model=APIResponse[ResourceRead],
    summary="Restore a previous version to active status (Faculty/Admin only)",
)
async def restore_version(
    resource_id: uuid.UUID,
    user: FacultyUser,
    version: int = Query(..., ge=1),
    db: AsyncSession = Depends(get_db),
) -> APIResponse[ResourceRead]:
    service = ResourceService(db)
    restored = await service.restore_version(
        resource_id=resource_id,
        version_number=version,
        current_user=user,
    )
    return APIResponse(
        success=True,
        message=f"Version {version} restored as the active version.",
        data=ResourceRead.model_validate(restored),
    )


# ── List Resources ────────────────────────────────────────────────────────────
@router.get(
    "",
    response_model=PaginatedResponse[ResourceRead],
    summary="List resources (with search, pagination, and multi-level filters)",
)
async def list_resources(
    _user: FacultyUser,
    course_id: uuid.UUID | None = Query(None),
    resource_type: str | None = Query(None),
    uploaded_by: uuid.UUID | None = Query(None),
    search: str | None = Query(None),
    start_date: datetime | None = Query(None),
    end_date: datetime | None = Query(None),
    is_active: bool | None = Query(True),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
) -> PaginatedResponse[ResourceRead]:
    service = ResourceService(db)
    resources, total = await service.repo.list_resources(
        skip=skip,
        limit=limit,
        course_id=course_id,
        resource_type=resource_type,
        uploaded_by=uploaded_by,
        search=search,
        start_date=start_date,
        end_date=end_date,
        is_active=is_active,
    )
    pages = (total + limit - 1) // limit
    return PaginatedResponse(
        success=True,
        message="Resources retrieved successfully.",
        data=[ResourceRead.model_validate(r) for r in resources],
        total=total,
        page=(skip // limit) + 1,
        per_page=limit,
        pages=pages,
    )


# ── Resource Details ──────────────────────────────────────────────────────────
@router.get(
    "/{resource_id}",
    response_model=APIResponse[ResourceRead],
    summary="Get resource details by ID",
)
async def get_resource(
    resource_id: uuid.UUID,
    _user: FacultyUser,
    db: AsyncSession = Depends(get_db),
) -> APIResponse[ResourceRead]:
    service = ResourceService(db)
    resource = await service.get_resource(resource_id)
    return APIResponse(
        success=True,
        message="Resource retrieved.",
        data=ResourceRead.model_validate(resource),
    )


# ── Version History ───────────────────────────────────────────────────────────
@router.get(
    "/{resource_id}/history",
    response_model=APIResponse[list[ResourceRead]],
    summary="Get version history of a resource lineage",
)
async def get_resource_history(
    resource_id: uuid.UUID,
    _user: FacultyUser,
    db: AsyncSession = Depends(get_db),
) -> APIResponse[list[ResourceRead]]:
    service = ResourceService(db)
    history = await service.get_resource_history(resource_id)
    return APIResponse(
        success=True,
        message="Resource version history retrieved.",
        data=[ResourceRead.model_validate(r) for r in history],
    )


# ── Download Resource ─────────────────────────────────────────────────────────
@router.get(
    "/{resource_id}/download",
    summary="Download resource file (Faculty/Admin only)",
)
async def download_resource(
    resource_id: uuid.UUID,
    _user: FacultyUser,
    db: AsyncSession = Depends(get_db),
) -> StreamingResponse:
    service = ResourceService(db)
    stream, filename, mime_type, size = await service.download_resource_stream(resource_id)

    # Encode filename to protect against non-ASCII characters
    content_disposition = f'attachment; filename="{filename}"'

    return StreamingResponse(
        stream,
        media_type=mime_type,
        headers={
            "Content-Disposition": content_disposition,
            "Content-Length": str(size),
            "X-Content-Type-Options": "nosniff",
        },
    )


# ── Update Metadata ───────────────────────────────────────────────────────────
@router.put(
    "/{resource_id}",
    response_model=APIResponse[ResourceRead],
    summary="Update resource metadata (Faculty/Admin only)",
)
async def update_metadata(
    resource_id: uuid.UUID,
    payload: ResourceUpdate,
    user: FacultyUser,
    db: AsyncSession = Depends(get_db),
) -> APIResponse[ResourceRead]:
    service = ResourceService(db)
    updated = await service.update_metadata(
        resource_id=resource_id,
        current_user=user,
        title=payload.title,
        description=payload.description,
        resource_type=payload.resource_type,
    )
    return APIResponse(
        success=True,
        message="Resource metadata updated successfully.",
        data=ResourceRead.model_validate(updated),
    )


# ── Delete Resource ───────────────────────────────────────────────────────────
@router.delete(
    "/{resource_id}",
    response_model=APIResponse[None],
    summary="Delete a resource and all its version files (Faculty/Admin only)",
)
async def delete_resource(
    resource_id: uuid.UUID,
    user: FacultyUser,
    db: AsyncSession = Depends(get_db),
) -> APIResponse[None]:
    service = ResourceService(db)
    await service.delete_resource(resource_id=resource_id, current_user=user)
    return APIResponse(
        success=True,
        message="Resource and all versions deleted successfully.",
        data=None,
    )
