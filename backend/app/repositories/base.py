"""
Generic base repository.

Provides CRUD operations that concrete repositories inherit.
The database session is injected, keeping this class stateless and
independently testable.
"""

from typing import Any, TypeVar
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.base import Base

ModelT = TypeVar("ModelT", bound=Base)


class BaseRepository[ModelT: Base]:
    """
    Generic async CRUD repository.

    Sub-classes only need to declare ``model = YourModel``.
    All database I/O goes through the ``AsyncSession`` passed to each
    method so that transaction control stays with the caller (service layer).
    """

    model: type[ModelT]

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, record_id: UUID) -> ModelT | None:
        """Return a single record by its UUID primary key, or ``None``."""
        return await self._session.get(self.model, record_id)

    async def get_all(self, *, skip: int = 0, limit: int = 100) -> list[ModelT]:
        """Return a paginated list of all records."""
        result = await self._session.execute(select(self.model).offset(skip).limit(limit))
        return list(result.scalars().all())

    async def create(self, obj: ModelT) -> ModelT:
        """
        Persist a new record.

        The caller is responsible for constructing the ORM object and
        managing the enclosing transaction.
        """
        self._session.add(obj)
        await self._session.flush()  # write to DB; let caller commit
        await self._session.refresh(obj)
        return obj

    async def update(self, obj: ModelT, data: dict[str, Any]) -> ModelT:
        """Apply *data* as attribute updates on *obj* and flush."""
        for key, value in data.items():
            setattr(obj, key, value)
        self._session.add(obj)
        await self._session.flush()
        await self._session.refresh(obj)
        return obj

    async def delete(self, obj: ModelT) -> None:
        """Delete *obj* from the database and flush."""
        await self._session.delete(obj)
        await self._session.flush()

    async def count(self) -> int:
        """Return the total number of records in the table."""
        from sqlalchemy import func, select  # local to avoid circular

        result = await self._session.execute(select(func.count()).select_from(self.model))
        return result.scalar_one()
