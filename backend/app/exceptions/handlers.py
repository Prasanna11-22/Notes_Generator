"""
Global FastAPI exception handlers.

Every error — whether raised by our code, Pydantic, or FastAPI itself —
is caught here and returned in the standard envelope::

    {
        "success": false,
        "message": "Human-readable reason",
        "data": null
    }

Register all handlers via ``register_exception_handlers(app)`` in
``app.main``.
"""

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from loguru import logger

from app.exceptions.custom import AppBaseException


def _error_response(status_code: int, message: str) -> JSONResponse:
    """Return a consistent error envelope."""
    return JSONResponse(
        status_code=status_code,
        content={"success": False, "message": message, "data": None},
    )


def register_exception_handlers(app: FastAPI) -> None:
    """Attach all global exception handlers to *app*."""

    @app.exception_handler(AppBaseException)
    async def app_exception_handler(request: Request, exc: AppBaseException) -> JSONResponse:
        """Handle all domain-level exceptions raised in the service layer."""
        logger.warning(
            "AppException | {} {} | {} | {}",
            request.method,
            request.url.path,
            exc.status_code,
            exc.message,
        )
        return _error_response(exc.status_code, exc.message)

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        """Handle Pydantic validation errors (422 Unprocessable Entity)."""
        # Flatten all field errors into a single readable string
        errors = exc.errors()
        messages = []
        for err in errors:
            loc = " → ".join(str(loc_part) for loc_part in err["loc"] if loc_part != "body")
            messages.append(f"{loc}: {err['msg']}" if loc else err["msg"])
        message = " | ".join(messages) if messages else "Validation error."
        logger.info(
            "ValidationError | {} {} | {}",
            request.method,
            request.url.path,
            message,
        )
        return _error_response(status.HTTP_422_UNPROCESSABLE_ENTITY, message)

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        """
        Catch-all handler for unexpected errors.

        Always logs the full traceback; returns a safe generic message
        to the client so internal details are never exposed.
        """
        logger.exception(
            "UnhandledException | {} {} | {}",
            request.method,
            request.url.path,
            str(exc),
        )
        return _error_response(
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            "An unexpected error occurred.  Please try again later.",
        )
