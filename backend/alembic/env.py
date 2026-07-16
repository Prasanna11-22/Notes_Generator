"""
Alembic environment configuration.

Reads DATABASE_URL from the application settings so that we never hard-code
connection strings in migration scripts.

Supports **async** SQLAlchemy engines (asyncpg) by running migrations via
``run_sync`` inside an async context.
"""

import asyncio
from logging.config import fileConfig

from alembic import context
from sqlalchemy import pool
from sqlalchemy.ext.asyncio import async_engine_from_config

# Import the shared declarative Base so Alembic can auto-generate migrations
# from the ORM model metadata.
from app.database.base import Base

# Import all models here so their tables are registered with ``Base.metadata``.
# Add future model imports as new phases are implemented.
import app.models  # noqa: F401  — registers User, etc.

from app.core.config import settings

# The Alembic Config object (wraps alembic.ini)
config = context.config

# Set DATABASE_URL from our Pydantic Settings (overrides alembic.ini value)
config.set_main_option("sqlalchemy.url", settings.database_url)

# Interpret the alembic.ini logging configuration
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Metadata object for ``--autogenerate`` support
target_metadata = Base.metadata


# ── Offline migrations ────────────────────────────────────────────────────────
def run_migrations_offline() -> None:
    """
    Run migrations without connecting to the database.

    Emits SQL to stdout.  Useful for generating migration scripts to review
    or apply manually.
    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


# ── Online (async) migrations ─────────────────────────────────────────────────
def do_run_migrations(connection) -> None:
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    """Create an async engine and run migrations inside a sync adapter."""
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await connectable.dispose()


def run_migrations_online() -> None:
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
