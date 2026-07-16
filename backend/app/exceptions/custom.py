"""
Domain-specific exception classes.

These are raised by the service layer and caught by the global exception
handlers in ``app.exceptions.handlers``.  Using named exception types
(rather than raw HTTP exceptions) keeps the service layer free of FastAPI
concerns.
"""

from fastapi import status


class AppBaseException(Exception):
    """Base class for all application-level exceptions."""

    def __init__(self, message: str, status_code: int = status.HTTP_400_BAD_REQUEST) -> None:
        super().__init__(message)
        self.message = message
        self.status_code = status_code


# ── Authentication exceptions ─────────────────────────────────────────────────


class AuthenticationError(AppBaseException):
    """Raised when credentials are invalid or authentication fails."""

    def __init__(self, message: str = "Invalid credentials.") -> None:
        super().__init__(message, status_code=status.HTTP_401_UNAUTHORIZED)


class TokenExpiredError(AppBaseException):
    """Raised when a JWT has expired."""

    def __init__(self, message: str = "Token has expired.") -> None:
        super().__init__(message, status_code=status.HTTP_401_UNAUTHORIZED)


class InvalidTokenError(AppBaseException):
    """Raised when a JWT cannot be decoded or has been tampered with."""

    def __init__(self, message: str = "Invalid token.") -> None:
        super().__init__(message, status_code=status.HTTP_401_UNAUTHORIZED)


class InactiveUserError(AppBaseException):
    """Raised when an inactive user attempts to authenticate."""

    def __init__(self, message: str = "This account has been deactivated.") -> None:
        super().__init__(message, status_code=status.HTTP_403_FORBIDDEN)


# ── Authorisation exceptions ──────────────────────────────────────────────────


class PermissionDeniedError(AppBaseException):
    """Raised when an authenticated user lacks the required role or permission."""

    def __init__(self, message: str = "You do not have permission to perform this action.") -> None:
        super().__init__(message, status_code=status.HTTP_403_FORBIDDEN)


# ── Resource exceptions ───────────────────────────────────────────────────────


class NotFoundError(AppBaseException):
    """Raised when a requested resource does not exist."""

    def __init__(self, resource: str = "Resource", resource_id: str = "") -> None:
        detail = f"{resource} not found."
        if resource_id:
            detail = f"{resource} '{resource_id}' not found."
        super().__init__(detail, status_code=status.HTTP_404_NOT_FOUND)


class ConflictError(AppBaseException):
    """Raised when a create/update operation violates a uniqueness constraint."""

    def __init__(self, message: str = "A conflicting resource already exists.") -> None:
        super().__init__(message, status_code=status.HTTP_409_CONFLICT)


class ValidationError(AppBaseException):
    """Raised when business-layer validation fails (distinct from Pydantic)."""

    def __init__(self, message: str = "Validation failed.") -> None:
        super().__init__(message, status_code=status.HTTP_422_UNPROCESSABLE_ENTITY)
