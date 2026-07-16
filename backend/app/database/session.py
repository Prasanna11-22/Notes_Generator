"""
Database session management.

Provides:
- Async SQLAlchemy engine
- ``AsyncSession`` factory
- ``get_db()`` FastAPI dependency that yields a session per request
"""

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.config import settings

# ── Engine ──────────────────────────────────────────────────────────────────
engine_kwargs = {
    "echo": settings.debug,
    "pool_pre_ping": True,
}

if not settings.database_url.startswith("sqlite"):
    engine_kwargs["pool_size"] = 10
    engine_kwargs["max_overflow"] = 20

engine = create_async_engine(
    settings.database_url,
    **engine_kwargs
)

# ── Session factory ──────────────────────────────────────────────────────────
AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,  # keep objects accessible after commit
    autoflush=False,
)


# ── FastAPI dependency ───────────────────────────────────────────────────────
async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Yield an ``AsyncSession`` for the duration of a single request.

    The session is committed on success and rolled back + closed on any
    unhandled exception, ensuring the connection is always returned to the
    pool.

    Usage::

        @router.get("/items")
        async def list_items(db: AsyncSession = Depends(get_db)):
            ...
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def seed_lookup_tables() -> None:
    """
    Seed BloomLevel and KnowledgeLevel tables if they are empty.
    Runs during lifespan startup.
    """
    import uuid

    from sqlalchemy import select

    from app.models.curriculum import BloomLevel, KnowledgeLevel

    async with AsyncSessionLocal() as session:
        try:
            # Seed Bloom levels
            bloom_res = await session.execute(select(BloomLevel))
            if not bloom_res.scalars().all():
                bloom_names = ["Remember", "Understand", "Apply", "Analyze", "Evaluate", "Create"]
                for name in bloom_names:
                    session.add(BloomLevel(id=uuid.uuid4(), name=name))

            # Seed Knowledge levels
            knowledge_res = await session.execute(select(KnowledgeLevel))
            if not knowledge_res.scalars().all():
                knowledge_names = ["Factual", "Conceptual", "Procedural", "Metacognitive"]
                for name in knowledge_names:
                    session.add(KnowledgeLevel(id=uuid.uuid4(), name=name))

            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
