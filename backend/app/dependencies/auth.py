"""
Authentication dependencies for FastAPI ``Depends()``.

Provides reusable, composable dependencies that extract and validate the
current user from the incoming request's Authorization header.

Usage in a route::

    @router.get("/secure")
    async def secure_endpoint(
        current_user: User = Depends(get_current_user),
    ):
        ...
"""

from typing import Annotated

from fastapi import Depends, Security
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.session import get_db
from app.exceptions.custom import PermissionDeniedError
from app.models.user import User, UserRole
from app.services.auth import AuthService

# HTTP Bearer scheme — FastAPI will show a padlock icon in Swagger UI
_bearer_scheme = HTTPBearer(auto_error=True)


async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials, Security(_bearer_scheme)],
    db: AsyncSession = Depends(get_db),
) -> User:
    """
    Extract and validate the JWT from the ``Authorization: Bearer <token>``
    header, then return the corresponding ``User`` record.

    :raises InvalidTokenError: Token is missing, malformed, or expired.
    :raises InactiveUserError: The user's account has been deactivated.
    :raises NotFoundError:     The subject in the token no longer exists.
    """
    service = AuthService(db)
    return await service.get_current_user_by_token(credentials.credentials)


async def require_admin(
    current_user: Annotated[User, Depends(get_current_user)],
) -> User:
    """
    Dependency that restricts access to users with the ``admin`` role.

    :raises PermissionDeniedError: If the current user is not an admin.
    """
    if current_user.role != UserRole.ADMIN.value:
        raise PermissionDeniedError("Administrator privileges are required.")
    return current_user


async def require_faculty(
    current_user: Annotated[User, Depends(get_current_user)],
) -> User:
    """
    Dependency that restricts access to ``faculty`` or ``admin`` users.

    :raises PermissionDeniedError: If the current user has an unknown role.
    """
    if current_user.role not in {UserRole.FACULTY.value, UserRole.ADMIN.value}:
        raise PermissionDeniedError("Faculty privileges are required.")
    return current_user


# Convenient type aliases for route signatures
CurrentUser = Annotated[User, Depends(get_current_user)]
AdminUser = Annotated[User, Depends(require_admin)]
FacultyUser = Annotated[User, Depends(require_faculty)]
