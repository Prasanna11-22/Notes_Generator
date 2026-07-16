"""
Authentication API routes.

Endpoints:
    POST /auth/register   — Register a new user account.
    POST /auth/login      — Authenticate and receive a JWT pair.
    POST /auth/refresh    — Exchange a refresh token for a new access token.
    POST /auth/logout     — Invalidate session (client-side token discard).
    GET  /auth/me         — Return the currently authenticated user's profile.

All responses use the standard envelope:
    { "success": bool, "message": str, "data": ... | null }
"""

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.session import get_db
from app.dependencies.auth import CurrentUser
from app.schemas.auth import RefreshTokenRequest, TokenResponse, UserLogin
from app.schemas.response import APIResponse
from app.schemas.user import UserCreate, UserRead
from app.services.auth import AuthService

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post(
    "/register",
    response_model=APIResponse[UserRead],
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user account",
    description=(
        "Create a new **faculty** or **admin** account.  "
        "The plain-text password is hashed with bcrypt before being stored.  "
        "Duplicate email addresses are rejected with a ``409 Conflict``."
    ),
)
async def register(
    payload: UserCreate,
    db: AsyncSession = Depends(get_db),
) -> APIResponse[UserRead]:
    """Register endpoint — creates and returns the new user profile."""
    service = AuthService(db)
    user = await service.register(payload)
    return APIResponse(
        success=True,
        message="Account created successfully.",
        data=UserRead.model_validate(user),
    )


@router.post(
    "/login",
    response_model=APIResponse[TokenResponse],
    summary="Authenticate and receive JWT tokens",
    description=(
        "Submit email and password to receive a short-lived **access token** "
        "and a long-lived **refresh token**.  "
        "Include the access token as ``Authorization: Bearer <token>`` on "
        "subsequent requests."
    ),
)
async def login(
    payload: UserLogin,
    db: AsyncSession = Depends(get_db),
) -> APIResponse[TokenResponse]:
    """Login endpoint — returns an access + refresh token pair."""
    service = AuthService(db)
    tokens = await service.login(payload.email, payload.password)
    return APIResponse(
        success=True,
        message="Login successful.",
        data=tokens,
    )


@router.post(
    "/refresh",
    response_model=APIResponse[TokenResponse],
    summary="Refresh an access token",
    description=(
        "Exchange a valid refresh token for a **new access token** "
        "(and a new refresh token for sliding-window expiry)."
    ),
)
async def refresh_token(
    payload: RefreshTokenRequest,
    db: AsyncSession = Depends(get_db),
) -> APIResponse[TokenResponse]:
    """Refresh endpoint — issues a new token pair from a valid refresh token."""
    service = AuthService(db)
    tokens = await service.refresh(payload)
    return APIResponse(
        success=True,
        message="Tokens refreshed successfully.",
        data=tokens,
    )


@router.post(
    "/logout",
    response_model=APIResponse[None],
    summary="Log out (client-side token discard)",
    description=(
        "Signals a logout intent.  Because JWTs are stateless, the actual "
        "invalidation happens on the **client** by discarding the stored tokens.  "
        "A future phase may add a server-side deny-list."
    ),
)
async def logout(
    _current_user: CurrentUser,
) -> APIResponse[None]:
    """Logout endpoint — acknowledges the logout request."""
    return APIResponse(
        success=True,
        message="Logged out successfully.  Please discard your tokens.",
        data=None,
    )


@router.get(
    "/me",
    response_model=APIResponse[UserRead],
    summary="Get the current authenticated user",
    description="Return the profile of the user identified by the Bearer access token.",
)
async def get_me(
    current_user: CurrentUser,
) -> APIResponse[UserRead]:
    """Me endpoint — returns the caller's own profile."""
    return APIResponse(
        success=True,
        message="User profile retrieved.",
        data=UserRead.model_validate(current_user),
    )
