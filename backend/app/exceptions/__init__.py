"""Exceptions package."""

from app.exceptions.custom import (
    AppBaseException,
    AuthenticationError,
    ConflictError,
    InactiveUserError,
    InvalidTokenError,
    NotFoundError,
    PermissionDeniedError,
    TokenExpiredError,
    ValidationError,
)
from app.exceptions.handlers import register_exception_handlers

__all__ = [
    "AppBaseException",
    "AuthenticationError",
    "TokenExpiredError",
    "InvalidTokenError",
    "InactiveUserError",
    "PermissionDeniedError",
    "NotFoundError",
    "ConflictError",
    "ValidationError",
    "register_exception_handlers",
]
