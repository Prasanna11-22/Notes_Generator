"""
Pydantic schemas for the Enterprise LLM Orchestrator.
"""

from typing import Any
from pydantic import BaseModel, Field


class LLMGenerateRequest(BaseModel):
    """Schema representing LLM text generation request."""

    prompt: str = Field(
        ...,
        min_length=1,
        description="Hydrated instruction prompt context to execute.",
        examples=["Explain asynchronous processing in Python."],
    )
    system_prompt: str | None = Field(
        None,
        description="Optional system instruction mapping instructions.",
        examples=["You are a senior Software Engineering professor."],
    )
    options: dict[str, Any] | None = Field(
        None,
        description="Override runtime model configuration (temperature, top_p, top_k, max_tokens, etc.).",
        examples=[{"temperature": 0.5, "max_tokens": 1024}],
    )
    require_json: bool = Field(
        False,
        description="Instruct post-generator validator to parse and assert valid JSON.",
    )


class LLMGenerateResponse(BaseModel):
    """Schema representing the completed generation response."""

    text: str = Field(..., description="Generated text content.")
    prompt_tokens: int = Field(..., description="Estimated/measured prompt tokens count.")
    completion_tokens: int = Field(..., description="Estimated/measured completion response tokens count.")
    model: str = Field(..., description="The name/tag of the model used.")
    provider: str = Field(..., description="The execution provider used.")
    latency_seconds: float = Field(..., description="Total pipeline latency in seconds.")
    retries_count: int = Field(..., description="Total execution retry attempts.")


class LLMValidationRequest(BaseModel):
    """Schema representing validation parameters for an arbitrary text block."""

    text: str = Field(..., min_length=1, description="Generated output string to validate.")
    require_json: bool = Field(
        False,
        description="Assert text complies with standard JSON formatting structures.",
    )


class LLMValidationResponse(BaseModel):
    """Schema representing the results of validation query checks."""

    success: bool = Field(..., description="True if text complies with constraints.")
    message: str = Field(..., description="Explanation of validation success or failure notes.")


class LLMProviderDetails(BaseModel):
    """Schema representing configured active provider details."""

    provider: str = Field(..., description="Configure provider identifier (e.g. ollama).")
    default_model: str = Field(..., description="The default LLM model tag.")
    host: str = Field(..., description="The host endpoint of the provider service.")


class LLMModelListResponse(BaseModel):
    """Schema representing list of pulled available model tags."""

    models: list[str] = Field(..., description="Available model tags list.")


class LLMHealthResponse(BaseModel):
    """Schema representing provider operational health."""

    status: str = Field(..., description="Operational status: 'healthy' or 'unhealthy'.")
