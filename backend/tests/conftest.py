"""
pytest configuration and shared fixtures.

Provides:
- An in-memory SQLite async engine (no PostgreSQL needed for tests).
- An ``AsyncSession`` that is rolled back after every test (clean state).
- An ``AsyncClient`` (httpx) pointed at the FastAPI app.
- A pre-created ``test_user`` fixture with known credentials.

The DATABASE_URL is overridden via ``CAMPUSBOT_TEST_DATABASE_URL`` or
falls back to in-memory SQLite so tests are fully self-contained.
"""

import os
from collections.abc import AsyncGenerator

import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import StaticPool

# ── Patch settings BEFORE importing the app ───────────────────────────────────
# Override .env values so tests never need a real database or secret.
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///./test.db")
os.environ.setdefault("SECRET_KEY", "test_secret_key_please_do_not_use_in_production")
os.environ.setdefault("JWT_SECRET", "test_jwt_secret_please_do_not_use_in_production")
os.environ.setdefault("ENVIRONMENT", "development")
os.environ.setdefault("DEBUG", "true")

from app.database.base import Base
from app.database.session import get_db
from app.main import app

# ── SQLite async engine (in-process, no server needed) ────────────────────────
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

test_engine = create_async_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
    echo=False,
)

TestSessionLocal = async_sessionmaker(
    bind=test_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)


@pytest_asyncio.fixture(scope="session", autouse=True)
async def setup_database():
    """Create all tables once for the test session, then drop them."""
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await test_engine.dispose()


@pytest_asyncio.fixture
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Yield a test database session.

    Each test gets a fresh session that is rolled back at the end,
    ensuring test isolation without recreating tables.
    """
    async with TestSessionLocal() as session:
        yield session
        await session.rollback()


@pytest_asyncio.fixture
async def client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """
    Yield an httpx ``AsyncClient`` with the ``get_db`` dependency overridden
    to use the in-memory test session.
    """

    async def _override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = _override_get_db

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as ac:
        yield ac

    app.dependency_overrides.clear()


# ── Helper data ───────────────────────────────────────────────────────────────
TEST_USER_EMAIL = "test.faculty@university.edu"
TEST_USER_PASSWORD = "Str0ng!Test1"
TEST_USER_NAME = "Test Faculty"


@pytest_asyncio.fixture
async def test_user(client: AsyncClient):
    """
    Register a test faculty user and return the response JSON.

    Subsequent fixtures (e.g. ``auth_headers``) depend on this fixture.
    """
    response = await client.post(
        "/api/v1/auth/register",
        json={
            "full_name": TEST_USER_NAME,
            "email": TEST_USER_EMAIL,
            "password": TEST_USER_PASSWORD,
            "institution": "Test University",
            "department": "Computer Science",
            "role": "faculty",
        },
    )
    assert response.status_code == 201, response.text
    return response.json()["data"]


@pytest_asyncio.fixture
async def auth_headers(client: AsyncClient, test_user) -> dict[str, str]:
    """Login as the test user and return Bearer auth headers."""
    response = await client.post(
        "/api/v1/auth/login",
        json={"email": TEST_USER_EMAIL, "password": TEST_USER_PASSWORD},
    )
    assert response.status_code == 200, response.text
    token = response.json()["data"]["access_token"]
    return {"Authorization": f"Bearer {token}"}
