"""
FastAPI application factory.

This module creates and configures the ``FastAPI`` instance.  It deliberately
contains **no business logic** — its only job is wiring together:
- Logging
- Middleware (CORS, request logging, trusted hosts)
- Global exception handlers
- API routers
- Startup / shutdown lifecycle hooks

Following the application-factory pattern keeps the app testable
(the test suite imports and uses the same ``app`` object) and avoids
circular imports.
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from loguru import logger

from app.api.v1.router import api_router
from app.core.config import settings
from app.core.logging import setup_logging
from app.database.session import engine, seed_lookup_tables
from app.exceptions.handlers import register_exception_handlers
from app.middleware.logging import RequestLoggingMiddleware


# ── Lifespan context manager ──────────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan handler.

    Code before ``yield`` runs on startup; code after runs on shutdown.
    This replaces the deprecated ``@app.on_event`` decorators.
    """
    # Startup
    setup_logging()
    logger.info(
        "Starting {} v{} | env={}",
        settings.app_name,
        settings.app_version,
        settings.environment,
    )

    # Fail fast on startup if configured spaCy/NLTK models are missing
    try:
        from app.services.chunking.engine import verify_nlp_resources
        verify_nlp_resources(settings.chunk_strategy, settings.spacy_model)
        logger.info("NLP models verified successfully (fail-fast checks passed).")
    except Exception as e:
        logger.critical(f"NLP startup validation failed: {str(e)}")
        # Raise to block startup and fail-fast
        raise RuntimeError(f"NLP validation failed: {str(e)}") from e

    # Automatically seed the lookup tables if they are empty
    try:
        await seed_lookup_tables()
        logger.info("Lookup tables seeded successfully (if not already seeded).")
    except Exception as e:
        logger.error(f"Error seeding lookup tables on startup: {str(e)}")

    yield
    # Shutdown
    logger.info("Application shutting down. Disposing database engine.")
    await engine.dispose()


# ── Application factory ───────────────────────────────────────────────────────
def create_app() -> FastAPI:
    """
    Construct and configure the FastAPI application.

    :returns: A fully configured ``FastAPI`` instance ready to be served.
    """
    application = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        description=(
            "**CampusBot AI** — AI-Powered Academic Content, Assessment, and "
            "Question Generation System.\n\n"
            "Phase 1 provides the backend foundation: authentication, user "
            "management, and core infrastructure that future phases will build upon."
        ),
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
        lifespan=lifespan,
        contact={
            "name": "CampusBot AI Team",
            "url": "https://github.com/prasanna11-22/campus-bot",
        },
        license_info={"name": "MIT"},
    )

    # ── Middleware (order matters — first added = outermost wrapper) ──────────

    # 1. Trusted hosts (security)
    trusted_hosts = (
        settings.allowed_hosts_list + ["*"]
        if settings.environment == "development"
        else settings.allowed_hosts_list
    )
    application.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=trusted_hosts,
    )

    # 2. CORS
    application.add_middleware(
        CORSMiddleware,
        allow_origins=settings.allowed_origins_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["X-Response-Time"],
    )

    # 3. Request / response timing + logging
    application.add_middleware(RequestLoggingMiddleware)

    # ── Exception handlers ────────────────────────────────────────────────────
    register_exception_handlers(application)

    # ── Routers ───────────────────────────────────────────────────────────────
    application.include_router(api_router, prefix=settings.api_v1_prefix)

    # ── Health check (no auth required) ──────────────────────────────────────
    @application.get(
        "/health",
        tags=["Health"],
        summary="Health check",
        description="Returns 200 OK if the service is running.",
        include_in_schema=True,
    )
    async def health_check() -> dict:
        return {
            "status": "healthy",
            "service": settings.app_name,
            "version": settings.app_version,
            "environment": settings.environment,
        }

    return application


# ── Module-level app instance ─────────────────────────────────────────────────
app = create_app()
