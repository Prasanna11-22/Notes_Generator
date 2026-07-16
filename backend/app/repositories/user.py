"""
UserRepository — data-access layer for the ``users`` table.

All SQL queries live here.  The service layer calls these methods; it
never writes raw SQLAlchemy queries itself.
"""

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.repositories.base import BaseRepository


class UserRepository(BaseRepository[User]):
    """Concrete repository for :class:`~app.models.user.User` records."""

    model = User

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session)

    async def get_by_email(self, email: str) -> User | None:
        """
        Return the User whose email matches *email* (case-insensitive),
        or ``None`` if not found.
        """
        result = await self._session.execute(select(User).where(User.email == email.lower()))
        return result.scalar_one_or_none()

    async def email_exists(self, email: str) -> bool:
        """Return ``True`` if *email* is already registered."""
        user = await self.get_by_email(email)
        return user is not None

    async def create_user(
        self,
        *,
        full_name: str,
        email: str,
        hashed_password: str,
        institution: str | None = None,
        department: str | None = None,
        role: str = "faculty",
    ) -> User:
        """
        Construct and persist a new :class:`User`.

        :param full_name:        Display name.
        :param email:            Normalised (lowercase) email.
        :param hashed_password:  bcrypt hash — plain-text is NEVER stored.
        :param institution:      Optional institution name.
        :param department:       Optional department name.
        :param role:             ``"faculty"`` (default) or ``"admin"``.
        :returns:                The newly created, database-refreshed User.
        """
        user = User(
            id=uuid.uuid4(),
            full_name=full_name,
            email=email.lower(),
            hashed_password=hashed_password,
            institution=institution,
            department=department,
            role=role,
            is_active=True,
        )
        return await self.create(user)

    async def deactivate(self, user: User) -> User:
        """Set ``is_active = False`` on *user* (soft-delete / ban)."""
        return await self.update(user, {"is_active": False})

    async def activate(self, user: User) -> User:
        """Re-enable a previously deactivated *user*."""
        return await self.update(user, {"is_active": True})
