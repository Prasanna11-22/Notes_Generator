"""
User Pydantic schemas.

Separates the API contract (what clients send / receive) from the
SQLAlchemy ORM model (internal DB representation).

Schemas:
- ``UserCreate``  — fields required to register a new user
- ``UserRead``    — fields safe to return in API responses (no password)
- ``UserUpdate``  — fields allowed when updating a user profile
"""

import uuid
from datetime import datetime

from pydantic import BaseModel, EmailStr, Field, field_validator

from app.models.user import UserRole


class UserCreate(BaseModel):
    """
    Payload expected from a client registering a new account.

    Validates email format, enforces minimum password strength,
    and trims whitespace from name fields.
    """

    full_name: str = Field(
        ...,
        min_length=2,
        max_length=255,
        examples=["Dr. Prasanna Kumar"],
        description="Full display name of the faculty member.",
    )
    email: EmailStr = Field(
        ...,
        examples=["prasanna.k@university.edu"],
        description="Institutional email address (used as login).",
    )
    password: str = Field(
        ...,
        min_length=8,
        max_length=128,
        examples=["Str0ng!Pass"],
        description="Plain-text password (min 8 chars).  Never stored.",
    )
    institution: str | None = Field(
        default=None,
        max_length=255,
        examples=["National Institute of Technology"],
        description="University or institution name.",
    )
    department: str | None = Field(
        default=None,
        max_length=255,
        examples=["Computer Science & Engineering"],
        description="Academic department.",
    )
    role: UserRole = Field(
        default=UserRole.FACULTY,
        description="User role.  Defaults to ``faculty``.",
    )

    @field_validator("full_name", mode="before")
    @classmethod
    def strip_name(cls, v: str) -> str:
        """Strip leading/trailing whitespace from the name."""
        return v.strip()

    @field_validator("email", mode="before")
    @classmethod
    def lower_email(cls, v: str) -> str:
        """Normalise the email to lowercase."""
        return v.strip().lower()

    @field_validator("password")
    @classmethod
    def validate_password_strength(cls, v: str) -> str:
        """
        Enforce basic password strength rules:
        - At least 8 characters
        - At least one uppercase letter
        - At least one digit
        """
        if not any(c.isupper() for c in v):
            raise ValueError("Password must contain at least one uppercase letter.")
        if not any(c.isdigit() for c in v):
            raise ValueError("Password must contain at least one digit.")
        return v

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "full_name": "Dr. Prasanna Kumar",
                    "email": "prasanna.k@university.edu",
                    "password": "Str0ng!Pass",
                    "institution": "NIT Trichy",
                    "department": "Computer Science & Engineering",
                    "role": "faculty",
                }
            ]
        }
    }


class UserRead(BaseModel):
    """
    Fields returned in API responses.

    Deliberately excludes ``hashed_password`` to prevent accidental exposure.
    """

    id: uuid.UUID
    full_name: str
    email: EmailStr
    institution: str | None
    department: str | None
    role: str
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class UserUpdate(BaseModel):
    """
    Fields a user may update in their own profile.

    All fields are optional — only provided fields will be persisted.
    Password updates require the dedicated change-password endpoint.
    """

    full_name: str | None = Field(default=None, min_length=2, max_length=255)
    institution: str | None = Field(default=None, max_length=255)
    department: str | None = Field(default=None, max_length=255)

    model_config = {
        "json_schema_extra": {
            "examples": [
                {"full_name": "Prof. Prasanna Kumar", "department": "Information Technology"}
            ]
        }
    }
