"""
FastAPI route handlers for Phase 9 Enterprise LLM Orchestrator.
"""

import json
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse

from app.core.config import settings
from app.dependencies.auth import FacultyUser
from app.schemas.response import APIResponse
from app.schemas.llm import (
    LLMGenerateRequest,
    LLMGenerateResponse,
    LLMValidationRequest,
    LLMValidationResponse,
    LLMProviderDetails,
    LLMModelListResponse,
    LLMHealthResponse,
)
from app.services.llm_orchestrator import LLMOrchestratorService

router = APIRouter(prefix="/llm", tags=["LLM Orchestrator"])


@router.post(
    "/generate",
    response_model=APIResponse[LLMGenerateResponse],
    summary="Block LLM text generation",
    description=(
        "Executes a blocking request to the configured LLM provider (e.g. Ollama with gemma3:4b). "
        "Performs system prompt formatting, option overrides, exponential backoff retries, "
        "and strict response quality validations (UTF-8, Markdown fences, JSON structures, truncation)."
    ),
)
async def generate_text(
    payload: LLMGenerateRequest,
    _user: FacultyUser = None,
) -> APIResponse[LLMGenerateResponse]:
    orchestrator = LLMOrchestratorService()
    try:
        result = await orchestrator.generate(
            prompt=payload.prompt,
            system_prompt=payload.system_prompt,
            options=payload.options,
            require_json=payload.require_json,
        )
        return APIResponse(
            success=True,
            message="LLM text generation completed successfully.",
            data=LLMGenerateResponse.model_validate(result),
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Validation error during generation: {str(exc)}",
        )
    except RuntimeError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"LLM execution failed: {str(exc)}",
        )


@router.post(
    "/generate-stream",
    summary="Streaming LLM text generation",
    description=(
        "Streams LLM text generation chunk-by-chunk to the client. "
        "Supports client connection cancellation. Yields newline-separated JSON chunk strings."
    ),
)
async def generate_text_stream(
    payload: LLMGenerateRequest,
    _user: FacultyUser = None,
) -> StreamingResponse:
    orchestrator = LLMOrchestratorService()
    try:
        stream_iter = await orchestrator.generate_stream(
            prompt=payload.prompt,
            system_prompt=payload.system_prompt,
            options=payload.options,
        )

        async def chunk_sender():
            async for chunk in stream_iter:
                yield json.dumps(chunk) + "\n"

        return StreamingResponse(
            chunk_sender(),
            media_type="application/x-ndjson",
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Validation error: {str(exc)}",
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Failed to initialize stream: {str(exc)}",
        )


@router.get(
    "/models",
    response_model=APIResponse[LLMModelListResponse],
    summary="List available provider models",
    description="Queries the active LLM provider (e.g. Ollama) and returns list of locally pulled/available model tags.",
)
async def list_models(
    _user: FacultyUser = None,
) -> APIResponse[LLMModelListResponse]:
    orchestrator = LLMOrchestratorService()
    models = await orchestrator.available_models()
    return APIResponse(
        success=True,
        message="Available models retrieved successfully.",
        data=LLMModelListResponse(models=models),
    )


@router.get(
    "/provider",
    response_model=APIResponse[LLMProviderDetails],
    summary="Check configured provider details",
    description="Returns configuration settings of the current active LLM provider.",
)
async def get_provider_details(
    _user: FacultyUser = None,
) -> APIResponse[LLMProviderDetails]:
    return APIResponse(
        success=True,
        message="Configured LLM provider details retrieved.",
        data=LLMProviderDetails(
            provider=settings.llm_provider,
            default_model=settings.llm_model,
            host=settings.ollama_host,
        ),
    )


@router.get(
    "/health",
    response_model=APIResponse[LLMHealthResponse],
    summary="Check LLM provider health status",
    description="Sends a lightweight check request to verify if the configured LLM endpoint is operational.",
)
async def check_health(
    _user: FacultyUser = None,
) -> APIResponse[LLMHealthResponse]:
    orchestrator = LLMOrchestratorService()
    healthy = await orchestrator.health_check()
    status_str = "healthy" if healthy else "unhealthy"
    return APIResponse(
        success=True,
        message="LLM provider health check completed.",
        data=LLMHealthResponse(status=status_str),
    )


@router.post(
    "/validate",
    response_model=APIResponse[LLMValidationResponse],
    summary="Perform post-generation validations",
    description=(
        "Utility endpoint to perform post-generation quality validations "
        "on arbitrary text blocks without running an active LLM generation."
    ),
)
async def validate_text_response(
    payload: LLMValidationRequest,
    _user: FacultyUser = None,
) -> APIResponse[LLMValidationResponse]:
    orchestrator = LLMOrchestratorService()
    try:
        orchestrator.validate_response(payload.text, require_json=payload.require_json)
        return APIResponse(
            success=True,
            message="Text successfully validated.",
            data=LLMValidationResponse(success=True, message="Validation passed."),
        )
    except ValueError as exc:
        return APIResponse(
            success=True,
            message="Text validation failed.",
            data=LLMValidationResponse(success=False, message=str(exc)),
        )
