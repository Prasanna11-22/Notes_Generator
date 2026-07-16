"""
Authentication service (business logic layer).

This class orchestrates user registration, login, token refresh, and
user lookup.  It **never** writes raw SQL; it delegates all data access to
:class:`~app.repositories.user.UserRepository` and all cryptographic work to
:mod:`app.core.security`.

Keeping business logic here (rather than in API route handlers) means the
service is independently testable without spinning up an HTTP server.
"""

from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)
from app.exceptions.custom import (
    AuthenticationError,
    ConflictError,
    InactiveUserError,
    InvalidTokenError,
    NotFoundError,
)
from app.models.user import User
from app.repositories.user import UserRepository
from app.schemas.auth import RefreshTokenRequest, TokenResponse
from app.schemas.user import UserCreate


class AuthService:
    """
    Service responsible for all authentication and user-management operations.

    Args:
        session: An :class:`~sqlalchemy.ext.asyncio.AsyncSession` injected
                 per-request.  All repository calls share this session so
                 they participate in the same transaction.
    """

    def __init__(self, session: AsyncSession) -> None:
        self._repo = UserRepository(session)

    async def register(self, payload: UserCreate) -> User:
        """
        Register a new faculty or admin user.

        Steps:
        1. Check that the email is not already in use.
        2. Hash the plain-text password with bcrypt.
        3. Persist the new ``User`` record via the repository.

        :param payload: Validated :class:`~app.schemas.user.UserCreate` data.
        :returns: The newly created :class:`~app.models.user.User`.
        :raises ConflictError: If the email is already registered.
        """
        if await self._repo.email_exists(payload.email):
            logger.warning("Registration blocked — email already exists: {}", payload.email)
            raise ConflictError(f"An account with the email '{payload.email}' already exists.")

        user = await self._repo.create_user(
            full_name=payload.full_name,
            email=payload.email,
            hashed_password=await hash_password(payload.password),
            institution=payload.institution,
            department=payload.department,
            role=payload.role.value,
        )
        logger.info("New user registered | id={} email={} role={}", user.id, user.email, user.role)
        return user

    async def login(self, email: str, password: str) -> TokenResponse:
        """
        Validate credentials and return a JWT token pair.

        :param email:    The email submitted by the client.
        :param password: The plain-text password submitted by the client.
        :returns: :class:`~app.schemas.auth.TokenResponse` containing
                  ``access_token`` and ``refresh_token``.
        :raises AuthenticationError: If the email/password combination is
                                     invalid.
        :raises InactiveUserError:   If the account has been deactivated.
        """
        user = await self._repo.get_by_email(email)

        if user is None or not await verify_password(password, user.hashed_password):
            logger.warning("Failed login attempt for email: {}", email)
            # Generic message — do not hint whether the email exists
            raise AuthenticationError("Invalid email or password.")

        if not user.is_active:
            logger.warning("Inactive user attempted login: {}", email)
            raise InactiveUserError()

        token_data = self._build_token_response(user)
        logger.info("User logged in | id={} email={}", user.id, user.email)
        return token_data

    async def refresh(self, payload: RefreshTokenRequest) -> TokenResponse:
        """
        Exchange a valid refresh token for a new access token (and a new
        refresh token to enable sliding expiry).

        :param payload: Contains the raw ``refresh_token`` string.
        :returns: A fresh :class:`~app.schemas.auth.TokenResponse`.
        :raises InvalidTokenError: If the token is malformed, expired, or
                                   not typed as a refresh token.
        :raises NotFoundError:     If the token's subject no longer exists.
        :raises InactiveUserError: If the account has been deactivated.
        """
        from jose import JWTError

        try:
            claims = decode_token(payload.refresh_token)
        except JWTError as exc:
            logger.warning("Invalid refresh token: {}", exc)
            raise InvalidTokenError("The refresh token is invalid or has expired.")

        if claims.get("type") != "refresh":
            raise InvalidTokenError("Token is not a refresh token.")

        user_id: str | None = claims.get("sub")
        if not user_id:
            raise InvalidTokenError("Token subject is missing.")

        import uuid

        user = await self._repo.get_by_id(uuid.UUID(user_id))
        if user is None:
            raise NotFoundError("User", user_id)
        if not user.is_active:
            raise InactiveUserError()

        token_data = self._build_token_response(user)
        logger.info("Tokens refreshed | id={}", user.id)
        return token_data

    async def get_current_user_by_token(self, token: str) -> User:
        """
        Decode an access token and return the associated ``User``.

        Intended for use by the ``get_current_user`` FastAPI dependency.

        :param token: Raw JWT access token string.
        :returns: The authenticated :class:`~app.models.user.User`.
        :raises InvalidTokenError: If the token is invalid/expired.
        :raises NotFoundError:     If the subject no longer exists.
        :raises InactiveUserError: If the account is deactivated.
        """
        from jose import JWTError

        try:
            claims = decode_token(token)
        except JWTError:
            raise InvalidTokenError("The access token is invalid or has expired.")

        if claims.get("type") != "access":
            raise InvalidTokenError("Token is not an access token.")

        user_id: str | None = claims.get("sub")
        if not user_id:
            raise InvalidTokenError("Token subject is missing.")

        import uuid

        user = await self._repo.get_by_id(uuid.UUID(user_id))
        if user is None:
            raise NotFoundError("User", user_id)
        if not user.is_active:
            raise InactiveUserError()

        return user

    # ── Private helpers ───────────────────────────────────────────────────────

    @staticmethod
    def _build_token_response(user: User) -> TokenResponse:
        """Construct a token pair for *user*."""
        return TokenResponse(
            access_token=create_access_token(
                subject=str(user.id),
                extra_claims={"role": user.role, "email": user.email},
            ),
            refresh_token=create_refresh_token(subject=str(user.id)),
        )
