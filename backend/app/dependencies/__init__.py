"""Dependencies package."""

from app.dependencies.auth import (
    AdminUser,
    CurrentUser,
    FacultyUser,
    get_current_user,
    require_admin,
    require_faculty,
)

__all__ = [
    "get_current_user",
    "require_admin",
    "require_faculty",
    "CurrentUser",
    "AdminUser",
    "FacultyUser",
]
