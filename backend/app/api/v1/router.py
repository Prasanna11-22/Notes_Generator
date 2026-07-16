"""
API v1 root router.

All feature sub-routers are registered here and then included in
the FastAPI app with the ``/api/v1`` prefix defined in settings.
"""

from fastapi import APIRouter

from app.api.v1.auth import router as auth_router
from app.api.v1.chunk import router as chunk_router
from app.api.v1.curriculum import router as curriculum_router
from app.api.v1.document_processing import router as document_processing_router
from app.api.v1.resource import router as resource_router
from app.api.v1.embeddings import router as embeddings_router
from app.api.v1.retriever import router as retriever_router
from app.api.v1.prompt import router as prompt_router
from app.api.v1.llm import router as llm_router
from app.api.v1.learning_material import router as learning_material_router

api_router = APIRouter()

# ── v1 feature routers ────────────────────────────────────────────────────────
api_router.include_router(auth_router)
api_router.include_router(curriculum_router)
api_router.include_router(resource_router)
api_router.include_router(document_processing_router)
api_router.include_router(chunk_router)
api_router.include_router(embeddings_router)
api_router.include_router(retriever_router)
api_router.include_router(prompt_router)
api_router.include_router(llm_router)
api_router.include_router(learning_material_router)

