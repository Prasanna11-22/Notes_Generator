"""
Generic API response envelope schema.

All API endpoints return a consistent JSON structure::

    {
        "success": true | false,
        "message": "Human-readable status message",
        "data": <payload> | null
    }

Using a typed generic ``APIResponse[T]`` allows FastAPI to generate correct
OpenAPI schemas for each endpoint's response model.
"""

from typing import TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")


class APIResponse[T](BaseModel):
    """
    Standard response envelope used by every endpoint.

    :param success: ``True`` on success, ``False`` on any error.
    :param message: Short human-readable description of the outcome.
    :param data: The actual payload (typed generically) or ``None``.
    """

    success: bool = Field(..., description="Whether the operation succeeded.")
    message: str = Field(..., description="Human-readable status message.")
    data: T | None = Field(default=None, description="Response payload.")

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "success": True,
                    "message": "Operation completed successfully.",
                    "data": {},
                }
            ]
        }
    }


class PaginatedResponse[T](BaseModel):
    """
    Paginated list response envelope.

    Wraps a list payload with pagination metadata so callers know
    how to request the next/previous page.
    """

    success: bool = True
    message: str = "Records retrieved successfully."
    data: list[T] = Field(default_factory=list)
    total: int = Field(0, description="Total number of records matching the query.")
    page: int = Field(1, description="Current page number (1-indexed).")
    per_page: int = Field(20, description="Number of records per page.")
    pages: int = Field(1, description="Total number of pages.")
