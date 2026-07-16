"""
Resource management service.
"""

import hashlib
import os
import re
import uuid
from collections.abc import AsyncGenerator

from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.exceptions.custom import (
    ConflictError,
    NotFoundError,
    PermissionDeniedError,
    ValidationError,
)
from app.models.curriculum import Course, Department, Program, Semester
from app.models.resource import Resource, ResourceType
from app.models.user import User, UserRole
from app.repositories.resource import ResourceRepository
from app.storage import get_storage


class ResourceService:
    """
    Orchestrates resource file uploads, downloads, metadata updates,
    version history lineages, and physical storage syncs.
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self.repo = ResourceRepository(session)
        self.storage = get_storage()

    def _sanitize_filename(self, filename: str) -> str:
        """
        Sanitize filenames to prevent path injection and remove illegal characters.
        """
        name = os.path.basename(filename)
        # Keep alphanumeric characters, dots, underscores, and dashes
        name = re.sub(r"[^a-zA-Z0-9_\.\-]", "_", name)
        return name

    async def _get_course_context(self, course_id: uuid.UUID) -> tuple[Course, str]:
        """
        Fetch Course and parent Department code in a single optimized query.
        """
        result = await self._session.execute(
            select(Course, Department.code)
            .join(Semester, Course.semester_id == Semester.id)
            .join(Program, Semester.program_id == Program.id)
            .join(Department, Program.department_id == Department.id)
            .where(Course.id == course_id)
        )
        row = result.first()
        if not row:
            raise NotFoundError("Course", str(course_id))
        return row[0], row[1]

    def _validate_file_metadata(
        self, file_content: bytes, original_file_name: str, mime_type: str
    ) -> None:
        """
        Enforce strict validation constraints (file size, extension, MIME type, empty payloads).
        """
        # Empty check
        if not file_content or len(file_content) == 0:
            raise ValidationError("File content is empty.")

        # File size constraint
        if len(file_content) > settings.max_upload_size_bytes:
            limit_mb = settings.max_upload_size_bytes / (1024 * 1024)
            raise ValidationError(f"File size exceeds the limit of {limit_mb:.1f}MB.")

        # File extension validation
        _, ext = os.path.splitext(original_file_name.lower())
        if ext not in settings.allowed_extensions:
            allowed_exts_str = ", ".join(settings.allowed_extensions)
            raise ValidationError(
                f"Unsupported file extension '{ext}'. Supported: {allowed_exts_str}"
            )

        # MIME type validation
        if mime_type.lower() not in settings.allowed_mime_types:
            allowed_mimes_str = ", ".join(settings.allowed_mime_types)
            raise ValidationError(
                f"Unsupported MIME type '{mime_type}'. Supported: {allowed_mimes_str}"
            )

    def _calculate_checksum(self, file_content: bytes) -> str:
        """
        Calculate SHA-256 checksum of the file bytes.
        """
        sha = hashlib.sha256()
        sha.update(file_content)
        return sha.hexdigest()

    async def upload_resource(
        self,
        *,
        course_id: uuid.UUID,
        uploaded_by: uuid.UUID,
        title: str,
        description: str | None = None,
        resource_type: str = ResourceType.OTHER.value,
        file_content: bytes,
        original_file_name: str,
        mime_type: str,
    ) -> Resource:
        """
        Validate, save to disk, and register a new resource in the database.
        """
        # 1. Validate
        self._validate_file_metadata(file_content, original_file_name, mime_type)
        checksum = self._calculate_checksum(file_content)

        # 2. Check for duplicate checksum in this course
        duplicate = await self.repo.get_by_checksum_in_course(course_id, checksum)
        if duplicate:
            raise ConflictError(
                f"A resource with identical content already exists in this course: '{duplicate.title}' (version {duplicate.version})."
            )

        # 3. Retrieve Department/Course context to build storage structure
        course, dept_code = await self._get_course_context(course_id)

        # 4. Synthesize paths and names
        resource_id = uuid.uuid4()
        safe_filename = self._sanitize_filename(original_file_name)
        unique_filename = f"{resource_id}_{safe_filename}"
        version = 1

        # Example: uploads/CSE/CS101/Textbook/v1/{uuid}_book.pdf
        relative_path = (
            f"{dept_code}/{course.course_code}/{resource_type}/v{version}/{unique_filename}"
        )

        logger.info(
            "Uploading resource: title={}, type={}, filename={}, size={} bytes",
            title,
            resource_type,
            original_file_name,
            len(file_content),
        )

        # 5. Write to storage
        try:
            await self.storage.upload(file_content, relative_path)
        except Exception as e:
            logger.error("Storage upload failed for resource {}: {}", title, str(e))
            raise ValidationError(f"File upload failed: {str(e)}")

        # 6. Save DB metadata
        resource = Resource(
            id=resource_id,
            course_id=course_id,
            uploaded_by=uploaded_by,
            parent_id=None,  # Root version
            title=title.strip(),
            description=description.strip() if description else None,
            resource_type=resource_type,
            file_name=unique_filename,
            original_file_name=original_file_name,
            file_size=len(file_content),
            mime_type=mime_type,
            storage_path=relative_path,
            version=version,
            checksum=checksum,
            upload_status="completed",
            is_active=True,
        )

        await self.repo.create(resource)
        return resource

    async def upload_new_version(
        self,
        *,
        resource_id: uuid.UUID,
        uploaded_by: uuid.UUID,
        file_content: bytes,
        original_file_name: str,
        mime_type: str,
    ) -> Resource:
        """
        Upload a new version of an existing resource lineage.
        """
        # 1. Fetch original root resource
        original = await self.repo.get_by_id(resource_id)
        if not original:
            raise NotFoundError("Resource", str(resource_id))

        root_id = original.parent_id or original.id

        # 2. Validate file metadata
        self._validate_file_metadata(file_content, original_file_name, mime_type)
        checksum = self._calculate_checksum(file_content)

        # 3. Check duplicate checksums in the course
        duplicate = await self.repo.get_by_checksum_in_course(original.course_id, checksum)
        if duplicate:
            raise ConflictError(
                f"A resource version with identical content already exists: '{duplicate.title}' (version {duplicate.version})."
            )

        # 4. Resolve latest version index
        latest_version = await self.repo.get_latest_version(root_id)
        next_version = latest_version + 1

        # 5. Retrieve Course/Department context
        course, dept_code = await self._get_course_context(original.course_id)

        # 6. Generate filename and path
        new_resource_id = uuid.uuid4()
        safe_filename = self._sanitize_filename(original_file_name)
        unique_filename = f"{new_resource_id}_{safe_filename}"
        relative_path = f"{dept_code}/{course.course_code}/{original.resource_type}/v{next_version}/{unique_filename}"

        logger.info(
            "Uploading new version {} for resource lineage root_id={}: size={} bytes",
            next_version,
            root_id,
            len(file_content),
        )

        # 7. Upload
        try:
            await self.storage.upload(file_content, relative_path)
        except Exception as e:
            logger.error("Storage upload failed for resource version lineage: {}", str(e))
            raise ValidationError(f"File upload failed: {str(e)}")

        # 8. Deactivate current active version in this lineage
        active_version = await self.repo.get_active_version(root_id)
        if active_version:
            active_version.is_active = False
            await self.repo.update(active_version, {"is_active": False})

        # 9. Save new version record
        new_version = Resource(
            id=new_resource_id,
            course_id=original.course_id,
            uploaded_by=uploaded_by,
            parent_id=root_id,
            title=original.title,
            description=original.description,
            resource_type=original.resource_type,
            file_name=unique_filename,
            original_file_name=original_file_name,
            file_size=len(file_content),
            mime_type=mime_type,
            storage_path=relative_path,
            version=next_version,
            checksum=checksum,
            upload_status="completed",
            is_active=True,
        )

        await self.repo.create(new_version)
        return new_version

    async def restore_version(
        self,
        *,
        resource_id: uuid.UUID,
        version_number: int,
        current_user: User,
    ) -> Resource:
        """
        Mark a previous version as the active version.
        """
        resource = await self.repo.get_by_id(resource_id)
        if not resource:
            raise NotFoundError("Resource", str(resource_id))

        root_id = resource.parent_id or resource.id

        # RBAC Check
        if current_user.role != UserRole.ADMIN.value and resource.uploaded_by != current_user.id:
            raise PermissionDeniedError(
                "You do not have permission to modify this resource lineage."
            )

        # Find target version record
        history = await self.repo.get_version_history(root_id)
        target = next((v for v in history if v.version == version_number), None)
        if not target:
            raise NotFoundError("Resource version", f"{version_number} of root {root_id}")

        logger.info(
            "Restoring version {} as active for resource lineage root_id={}",
            version_number,
            root_id,
        )

        # Deactivate all and activate target
        for v in history:
            if v.is_active:
                v.is_active = False
                await self.repo.update(v, {"is_active": False})

        target.is_active = True
        await self.repo.update(target, {"is_active": True})

        return target

    async def get_resource(self, resource_id: uuid.UUID) -> Resource:
        """
        Retrieve a single resource record by ID.
        """
        resource = await self.repo.get_by_id(resource_id)
        if not resource:
            raise NotFoundError("Resource", str(resource_id))
        return resource

    async def get_resource_history(self, resource_id: uuid.UUID) -> list[Resource]:
        """
        Retrieve the version history list of a resource lineage.
        """
        resource = await self.repo.get_by_id(resource_id)
        if not resource:
            raise NotFoundError("Resource", str(resource_id))
        root_id = resource.parent_id or resource.id
        history = await self.repo.get_version_history(root_id)
        return list(history)

    async def download_resource_stream(
        self, resource_id: uuid.UUID
    ) -> tuple[AsyncGenerator[bytes, None], str, str, int]:
        """
        Retrieve a streaming download generator for the resource.
        """
        resource = await self.repo.get_by_id(resource_id)
        if not resource:
            raise NotFoundError("Resource", str(resource_id))

        logger.info("Downloading resource: id={}, title={}", resource.id, resource.title)

        stream = await self.storage.download_stream(resource.storage_path)
        return stream, resource.original_file_name, resource.mime_type, resource.file_size

    async def update_metadata(
        self,
        *,
        resource_id: uuid.UUID,
        current_user: User,
        title: str | None = None,
        description: str | None = None,
        resource_type: str | None = None,
    ) -> Resource:
        """
        Update the user-configurable metadata of a resource.
        """
        resource = await self.repo.get_by_id(resource_id)
        if not resource:
            raise NotFoundError("Resource", str(resource_id))

        # RBAC Check
        if current_user.role != UserRole.ADMIN.value and resource.uploaded_by != current_user.id:
            raise PermissionDeniedError("You do not have permission to edit this resource.")

        # Update values
        updates = {}
        if title is not None:
            updates["title"] = title.strip()
        if description is not None:
            updates["description"] = description.strip()
        if resource_type is not None:
            if resource_type not in [r.value for r in ResourceType]:
                raise ValidationError(f"Invalid resource type '{resource_type}'.")
            updates["resource_type"] = resource_type

        # Propagate title/description/type updates to ALL versions in lineage to keep it consistent
        root_id = resource.parent_id or resource.id
        history = await self.repo.get_version_history(root_id)
        for v in history:
            await self.repo.update(v, updates)

        await self._session.flush()
        # Return updated current record
        await self._session.refresh(resource)
        return resource

    async def delete_resource(self, resource_id: uuid.UUID, current_user: User) -> None:
        """
        Delete a resource and all related versions from the database and storage.
        """
        resource = await self.repo.get_by_id(resource_id)
        if not resource:
            raise NotFoundError("Resource", str(resource_id))

        # RBAC Check: Admins can delete anything; Faculty can only delete their own uploads
        if current_user.role != UserRole.ADMIN.value and resource.uploaded_by != current_user.id:
            raise PermissionDeniedError("You do not have permission to delete this resource.")

        root_id = resource.parent_id or resource.id

        # 1. Retrieve all versions in lineage
        versions = await self.repo.get_version_history(root_id)

        logger.info(
            "Deleting resource lineage root_id={} (contains {} versions) by user_id={}",
            root_id,
            len(versions),
            current_user.id,
        )

        # 2. Delete all physical files from disk
        for v in versions:
            try:
                await self.storage.delete(v.storage_path)
            except Exception as e:
                logger.error("Failed to delete physical file {}: {}", v.storage_path, str(e))

        # 3. Delete root resource in DB (cascades automatically to children)
        root_resource = await self.repo.get_by_id(root_id)
        if root_resource:
            await self.repo.delete(root_resource)
        await self._session.flush()
