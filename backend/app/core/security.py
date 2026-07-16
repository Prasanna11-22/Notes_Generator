"""
Security utilities.

Handles:
- Password hashing / verification with bcrypt
- JWT access token creation and decoding
- Refresh token creation
"""

import asyncio
from datetime import UTC, datetime, timedelta
from typing import Any

import bcrypt
from jose import JWTError, jwt

from app.core.config import settings

# ── Password hashing context ─────────────────────────────────────────────────
# Direct bcrypt usage is preferred over passlib because passlib is deprecated and has compatibility issues on Python 3.14/bcrypt 4.x+.


async def hash_password(plain_password: str) -> str:
    """
    Return a bcrypt-hashed version of *plain_password*.

    The result is safe to store in the database.
    """
    pwd_bytes = plain_password.encode("utf-8")
    salt = await asyncio.to_thread(bcrypt.gensalt)
    hashed = await asyncio.to_thread(bcrypt.hashpw, pwd_bytes, salt)
    return hashed.decode("utf-8")


async def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Return ``True`` if *plain_password* matches *hashed_password*.

    Uses constant-time comparison to prevent timing attacks.
    """
    try:
        pwd_bytes = plain_password.encode("utf-8")
        hashed_bytes = hashed_password.encode("utf-8")
        return await asyncio.to_thread(bcrypt.checkpw, pwd_bytes, hashed_bytes)
    except Exception:
        return False


# ── JWT helpers ──────────────────────────────────────────────────────────────


def _create_token(payload: dict[str, Any], expires_delta: timedelta) -> str:
    """Internal helper — encode a JWT with an expiry claim."""
    to_encode = payload.copy()
    expire = datetime.now(UTC) + expires_delta
    to_encode.update({"exp": expire, "iat": datetime.now(UTC)})
    return jwt.encode(to_encode, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def create_access_token(subject: str, extra_claims: dict[str, Any] | None = None) -> str:
    """
    Create a short-lived JWT access token.

    :param subject: The unique identifier of the authenticated entity
                    (typically the user UUID string).
    :param extra_claims: Optional additional claims to embed in the token
                         (e.g., ``{"role": "admin"}``).
    :returns: Signed JWT string.
    """
    payload: dict[str, Any] = {"sub": subject, "type": "access"}
    if extra_claims:
        payload.update(extra_claims)
    return _create_token(
        payload,
        timedelta(minutes=settings.access_token_expire_minutes),
    )


def create_refresh_token(subject: str) -> str:
    """
    Create a long-lived JWT refresh token.

    :param subject: The unique identifier of the authenticated entity.
    :returns: Signed JWT string.
    """
    payload: dict[str, Any] = {"sub": subject, "type": "refresh"}
    return _create_token(
        payload,
        timedelta(days=settings.refresh_token_expire_days),
    )


def decode_token(token: str) -> dict[str, Any]:
    """
    Decode and validate a JWT token.

    :param token: The raw JWT string.
    :returns: The decoded payload dictionary.
    :raises JWTError: If the token is invalid, expired, or tampered with.
    """
    return jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])


def get_token_subject(token: str) -> str | None:
    """
    Safely extract the ``sub`` claim from a JWT.

    :returns: Subject string or ``None`` if the token is invalid.
    """
    try:
        payload = decode_token(token)
        return payload.get("sub")
    except JWTError:
        return None
