"""
Tests for authentication endpoints.

Covers:
- POST /auth/register   (success, duplicate, bad payload)
- POST /auth/login      (success, bad password, bad email)
- POST /auth/refresh    (success, invalid token)
- POST /auth/logout     (success, no token)
- GET  /auth/me         (success, no token, bad token)
"""

import pytest
from httpx import AsyncClient

from tests.conftest import TEST_USER_EMAIL, TEST_USER_NAME, TEST_USER_PASSWORD

pytestmark = pytest.mark.asyncio


# ═══════════════════════════════════════════════════════════════════════════════
# Registration
# ═══════════════════════════════════════════════════════════════════════════════


class TestRegister:
    async def test_register_success(self, client: AsyncClient):
        """A new user can register with valid credentials."""
        response = await client.post(
            "/api/v1/auth/register",
            json={
                "full_name": "Prof. New User",
                "email": "new.user@university.edu",
                "password": "Str0ng!Pass1",
                "institution": "Test Uni",
                "department": "Engineering",
                "role": "faculty",
            },
        )
        assert response.status_code == 201
        body = response.json()
        assert body["success"] is True
        assert body["data"]["email"] == "new.user@university.edu"
        assert body["data"]["full_name"] == "Prof. New User"
        assert "hashed_password" not in body["data"]

    async def test_register_duplicate_email(self, client: AsyncClient, test_user):
        """Registering with an already-used email returns 409."""
        response = await client.post(
            "/api/v1/auth/register",
            json={
                "full_name": "Duplicate User",
                "email": TEST_USER_EMAIL,
                "password": "Str0ng!Pass1",
                "role": "faculty",
            },
        )
        assert response.status_code == 409
        assert response.json()["success"] is False

    async def test_register_weak_password_no_uppercase(self, client: AsyncClient):
        """Password without uppercase is rejected with 422."""
        response = await client.post(
            "/api/v1/auth/register",
            json={
                "full_name": "Weak Pass User",
                "email": "weak@university.edu",
                "password": "weakpassword1",
                "role": "faculty",
            },
        )
        assert response.status_code == 422

    async def test_register_weak_password_no_digit(self, client: AsyncClient):
        """Password without a digit is rejected with 422."""
        response = await client.post(
            "/api/v1/auth/register",
            json={
                "full_name": "Weak Pass User",
                "email": "weak2@university.edu",
                "password": "WeakPassNoDigit",
                "role": "faculty",
            },
        )
        assert response.status_code == 422

    async def test_register_invalid_email(self, client: AsyncClient):
        """An invalid email format is rejected with 422."""
        response = await client.post(
            "/api/v1/auth/register",
            json={
                "full_name": "Bad Email",
                "email": "not-an-email",
                "password": "Str0ng!Pass1",
                "role": "faculty",
            },
        )
        assert response.status_code == 422

    async def test_register_missing_fields(self, client: AsyncClient):
        """Missing required fields return 422."""
        response = await client.post("/api/v1/auth/register", json={})
        assert response.status_code == 422


# ═══════════════════════════════════════════════════════════════════════════════
# Login
# ═══════════════════════════════════════════════════════════════════════════════


class TestLogin:
    async def test_login_success(self, client: AsyncClient, test_user):
        """Valid credentials return access + refresh tokens."""
        response = await client.post(
            "/api/v1/auth/login",
            json={"email": TEST_USER_EMAIL, "password": TEST_USER_PASSWORD},
        )
        assert response.status_code == 200
        body = response.json()
        assert body["success"] is True
        assert "access_token" in body["data"]
        assert "refresh_token" in body["data"]
        assert body["data"]["token_type"] == "bearer"

    async def test_login_wrong_password(self, client: AsyncClient, test_user):
        """Wrong password returns 401."""
        response = await client.post(
            "/api/v1/auth/login",
            json={"email": TEST_USER_EMAIL, "password": "WrongPass1!"},
        )
        assert response.status_code == 401
        assert response.json()["success"] is False

    async def test_login_nonexistent_email(self, client: AsyncClient):
        """Login with unknown email returns 401 (not 404 — to avoid user enumeration)."""
        response = await client.post(
            "/api/v1/auth/login",
            json={"email": "ghost@university.edu", "password": "Str0ng!Pass1"},
        )
        assert response.status_code == 401

    async def test_login_missing_email(self, client: AsyncClient):
        """Login without email returns 422."""
        response = await client.post(
            "/api/v1/auth/login",
            json={"password": "Str0ng!Pass1"},
        )
        assert response.status_code == 422


# ═══════════════════════════════════════════════════════════════════════════════
# Token refresh
# ═══════════════════════════════════════════════════════════════════════════════


class TestRefreshToken:
    async def test_refresh_success(self, client: AsyncClient, test_user):
        """A valid refresh token returns a new token pair."""
        # First, log in to get tokens
        login_resp = await client.post(
            "/api/v1/auth/login",
            json={"email": TEST_USER_EMAIL, "password": TEST_USER_PASSWORD},
        )
        refresh_token = login_resp.json()["data"]["refresh_token"]

        response = await client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": refresh_token},
        )
        assert response.status_code == 200
        body = response.json()
        assert body["success"] is True
        assert "access_token" in body["data"]

    async def test_refresh_invalid_token(self, client: AsyncClient):
        """An invalid/garbage refresh token returns 401."""
        response = await client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": "this.is.not.a.valid.jwt"},
        )
        assert response.status_code == 401

    async def test_refresh_access_token_as_refresh(self, client: AsyncClient, auth_headers):
        """Using an access token as a refresh token returns 401."""
        # Extract access token from auth header
        access_token = auth_headers["Authorization"].split(" ")[1]
        response = await client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": access_token},
        )
        assert response.status_code == 401


# ═══════════════════════════════════════════════════════════════════════════════
# Me endpoint
# ═══════════════════════════════════════════════════════════════════════════════


class TestGetMe:
    async def test_get_me_success(self, client: AsyncClient, auth_headers):
        """Authenticated user receives their own profile."""
        response = await client.get("/api/v1/auth/me", headers=auth_headers)
        assert response.status_code == 200
        body = response.json()
        assert body["success"] is True
        assert body["data"]["email"] == TEST_USER_EMAIL
        assert body["data"]["full_name"] == TEST_USER_NAME
        assert body["data"]["role"] == "faculty"
        assert "hashed_password" not in body["data"]

    async def test_get_me_no_token(self, client: AsyncClient):
        """Request without auth header returns 401."""
        response = await client.get("/api/v1/auth/me")
        assert response.status_code == 401

    async def test_get_me_invalid_token(self, client: AsyncClient):
        """Request with a garbage token returns 401."""
        response = await client.get(
            "/api/v1/auth/me",
            headers={"Authorization": "Bearer garbage.token.here"},
        )
        assert response.status_code == 401


# ═══════════════════════════════════════════════════════════════════════════════
# Logout
# ═══════════════════════════════════════════════════════════════════════════════


class TestLogout:
    async def test_logout_success(self, client: AsyncClient, auth_headers):
        """Authenticated user can log out."""
        response = await client.post("/api/v1/auth/logout", headers=auth_headers)
        assert response.status_code == 200
        assert response.json()["success"] is True

    async def test_logout_without_token(self, client: AsyncClient):
        """Logout without a token returns 401."""
        response = await client.post("/api/v1/auth/logout")
        assert response.status_code == 401


# ═══════════════════════════════════════════════════════════════════════════════
# Health check
# ═══════════════════════════════════════════════════════════════════════════════


class TestHealth:
    async def test_health_check(self, client: AsyncClient):
        """Health endpoint returns 200 with service info."""
        response = await client.get("/health")
        assert response.status_code == 200
        body = response.json()
        assert body["status"] == "healthy"
        assert "version" in body
