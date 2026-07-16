"""
Authentication-related Pydantic schemas.

Includes request bodies and response models for:
- Login
- Token pair (access + refresh)
- Refresh-token exchange
"""

from pydantic import BaseModel, EmailStr, Field


class UserLogin(BaseModel):
    """Credentials submitted by a user attempting to log in."""

    email: EmailStr = Field(
        ...,
        examples=["prasanna.k@university.edu"],
        description="Registered email address.",
    )
    password: str = Field(
        ...,
        min_length=1,
        examples=["Str0ng!Pass"],
        description="Plain-text password.",
    )

    model_config = {
        "json_schema_extra": {
            "examples": [{"email": "prasanna.k@university.edu", "password": "Str0ng!Pass"}]
        }
    }


class TokenResponse(BaseModel):
    """
    Token pair returned on successful authentication.

    The ``access_token`` should be sent as a Bearer token in the
    ``Authorization`` header for subsequent requests.

    The ``refresh_token`` can be exchanged for a new access token at
    ``POST /auth/refresh``.
    """

    access_token: str = Field(..., description="Short-lived JWT access token.")
    refresh_token: str = Field(..., description="Long-lived JWT refresh token.")
    token_type: str = Field(default="bearer", description="Token type (always 'bearer').")

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "access_token": "eyJhbGci...",
                    "refresh_token": "eyJhbGci...",
                    "token_type": "bearer",
                }
            ]
        }
    }


class RefreshTokenRequest(BaseModel):
    """Body sent to ``POST /auth/refresh`` to obtain a new access token."""

    refresh_token: str = Field(
        ...,
        description="A valid, non-expired refresh token.",
        examples=["eyJhbGci..."],
    )
