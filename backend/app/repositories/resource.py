"""
Resource database repository.
"""

import uuid
from collections.abc import Sequence
from datetime import datetime

from sqlalchemy import and_, func, or_, select

from app.models.resource import Resource
from app.repositories.base import BaseRepository


class ResourceRepository(BaseRepository[Resource]):
    """
    Handles all queries and CRUD operations for the ``Resource`` model.
    """

    model = Resource

    async def get_by_checksum_in_course(
        self, course_id: uuid.UUID, checksum: str
    ) -> Resource | None:
        """
        Check if a file with the identical checksum is already registered under this course.
        """
        result = await self._session.execute(
            select(Resource).where(
                and_(
                    Resource.course_id == course_id,
                    Resource.checksum == checksum.strip(),
                    Resource.is_active,
                )
            )
        )
        return result.scalar_one_or_none()

    async def get_latest_version(self, parent_id: uuid.UUID) -> int:
        """
        Return the highest version counter associated with the lineage tree.
        """
        result = await self._session.execute(
            select(func.max(Resource.version)).where(
                or_(Resource.parent_id == parent_id, Resource.id == parent_id)
            )
        )
        version = result.scalar_one_or_none()
        return version if version is not None else 0

    async def get_active_version(self, parent_id: uuid.UUID) -> Resource | None:
        """
        Retrieve the currently marked active version of the lineage tree.
        """
        result = await self._session.execute(
            select(Resource).where(
                and_(
                    or_(Resource.parent_id == parent_id, Resource.id == parent_id),
                    Resource.is_active,
                )
            )
        )
        return result.scalar_one_or_none()

    async def get_version_history(self, parent_id: uuid.UUID) -> Sequence[Resource]:
        """
        Return all versions of a resource sorted by version number ascending.
        """
        result = await self._session.execute(
            select(Resource)
            .where(or_(Resource.parent_id == parent_id, Resource.id == parent_id))
            .order_by(Resource.version.asc())
        )
        return result.scalars().all()

    async def list_resources(
        self,
        *,
        skip: int = 0,
        limit: int = 100,
        course_id: uuid.UUID | None = None,
        resource_type: str | None = None,
        uploaded_by: uuid.UUID | None = None,
        search: str | None = None,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
        is_active: bool | None = True,
    ) -> tuple[Sequence[Resource], int]:
        """
        List resources applying paginated, search, category, and creation date range constraints.
        """
        query = select(Resource)

        # Filters
        if course_id:
            query = query.where(Resource.course_id == course_id)
        if resource_type:
            query = query.where(Resource.resource_type == resource_type)
        if uploaded_by:
            query = query.where(Resource.uploaded_by == uploaded_by)
        if is_active is not None:
            query = query.where(Resource.is_active == is_active)

        # Date range filters on created_at
        if start_date:
            query = query.where(Resource.created_at >= start_date)
        if end_date:
            query = query.where(Resource.created_at <= end_date)

        # Search matching title or filename
        if search:
            query = query.where(
                (Resource.title.ilike(f"%{search}%"))
                | (Resource.original_file_name.ilike(f"%{search}%"))
            )

        # Default sort by created_at desc (newest first)
        query = query.order_by(Resource.created_at.desc())

        # Count total matches
        count_query = select(func.count()).select_from(query.subquery())
        total_result = await self._session.execute(count_query)
        total = total_result.scalar_one()

        # Run paginated select
        result = await self._session.execute(query.offset(skip).limit(limit))
        return result.scalars().all(), total
