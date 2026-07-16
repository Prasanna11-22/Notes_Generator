"""
Enterprise LLM Orchestrator Service.
"""

import asyncio
import json
import time
from typing import Any, AsyncIterator
from loguru import logger
import httpx

from app.ai.providers import get_llm_provider
from app.ai.providers.llm.base import LLMProvider
from app.core.config import settings


class LLMOrchestratorService:
    """
    Orchestration service coordinating prompt validation, LLM routing, 
    exponential backoff retries, response validation, and secure logging.
    """

    def __init__(
        self,
        provider: LLMProvider | None = None,
        max_retries: int | None = None,
        timeout: float | None = None,
    ) -> None:
        """
        Initialize the orchestrator service.

        :param provider: LLM provider adapter (defaults to configured system singleton).
        :param max_retries: Maximum validation/network retries (defaults to settings.llm_max_retries).
        :param timeout: Connection timeout in seconds.
        """
        self.provider = provider or get_llm_provider()
        self.max_retries = max_retries if max_retries is not None else settings.llm_max_retries
        self.timeout = timeout if timeout is not None else settings.llm_timeout_seconds

    def validate_prompt(self, prompt: str, system_prompt: str | None = None) -> None:
        """
        Validate prompt text inputs before forwarding to LLM provider.
        Rejects empty, whitespace-only, or injection-suspicious prompts.
        """
        if not prompt or not prompt.strip():
            raise ValueError("Prompt cannot be empty or whitespace-only.")
        if system_prompt is not None and not system_prompt.strip():
            raise ValueError("System prompt cannot be empty if provided.")

        # Check for prompt injection using Phase 8 validation service
        from app.services.prompt_validation import PromptValidationService
        validator = PromptValidationService()
        validator.sanitize_and_check(prompt, "prompt")
        if system_prompt:
            validator.sanitize_and_check(system_prompt, "system_prompt")

    def validate_response(self, text: str, require_json: bool = False) -> None:
        """
        Perform post-generation validations to ensure response quality.

        - Verifies non-empty response.
        - Verifies UTF-8 string integrity.
        - Verifies JSON structure (if require_json is set to True).
        - Verifies no unclosed markdown code block fences.
        - Verifies no obvious truncation at the end.
        """
        if not text or not text.strip():
            raise ValueError("Validation failed: Generated response is empty.")

        # String encode-decode test to check UTF-8 compliance
        try:
            text.encode("utf-8").decode("utf-8")
        except UnicodeError as exc:
            raise ValueError(f"Validation failed: Invalid UTF-8 sequence: {str(exc)}") from exc

        # JSON parsing validation
        if require_json:
            clean_text = text.strip()
            # If the response was wrapped in markdown code fences, strip them
            if clean_text.startswith("```"):
                # Strip markdown code blocks e.g. ```json ... ```
                lines = clean_text.splitlines()
                if len(lines) >= 2 and lines[0].startswith("```"):
                    if lines[-1].startswith("```"):
                        clean_text = "\n".join(lines[1:-1]).strip()
                    else:
                        clean_text = "\n".join(lines[1:]).strip()

            try:
                json.loads(clean_text)
            except json.JSONDecodeError as exc:
                raise ValueError(f"Validation failed: Response is not valid JSON: {str(exc)}") from exc

        # Markdown formatting validation (unclosed code fences)
        if text.count("```") % 2 != 0:
            raise ValueError("Validation failed: Malformed markdown detected (unclosed code block fences).")

        # Basic sentence truncation validation
        # If response ends in a word without terminal punctuation or is cut off
        stripped = text.strip()
        if len(stripped) > 0:
            # We check if it ends with common terminal punctuation or closing markers
            terminal_chars = (".", "!", "?", '"', "'", "}", "]", ")", "`", "*", "_")
            if not stripped.endswith(terminal_chars):
                # Check if it ends mid-word (alphanumeric character)
                if stripped[-1].isalnum():
                    raise ValueError("Validation failed: Response appears to be truncated mid-sentence.")

    async def generate(
        self,
        prompt: str,
        system_prompt: str | None = None,
        options: dict[str, Any] | None = None,
        require_json: bool = False,
    ) -> dict[str, Any]:
        """
        Execute blocking text generation with exponential backoff retries.

        :param prompt: User instruction prompt.
        :param system_prompt: Optional system-level prompt context.
        :param options: Optional overrides.
        :param require_json: Assert output structure matches JSON.
        :returns: Execution metadata & text content.
        """
        self.validate_prompt(prompt, system_prompt)

        # Merge defaults hyper-parameters from settings, then override with options
        runtime_options = {
            "temperature": settings.llm_temperature,
            "top_p": settings.llm_top_p,
            "top_k": settings.llm_top_k,
            "max_tokens": settings.llm_max_tokens,
            "repeat_penalty": settings.llm_repeat_penalty,
            "num_ctx": settings.llm_num_ctx,
        }
        if options:
            for k, v in options.items():
                if v is not None:
                    runtime_options[k] = v

        retries = 0
        backoff = 1.0
        start_time = time.perf_counter()

        while True:
            attempt_start = time.perf_counter()
            try:
                # Call provider
                response = await self.provider.generate(
                    prompt=prompt,
                    system_prompt=system_prompt,
                    options=runtime_options,
                )

                # Validate response
                self.validate_response(response["text"], require_json=require_json)

                # Successfully completed
                latency = time.perf_counter() - start_time
                response_size = len(response["text"].encode("utf-8"))

                # Secure Logging: Never log prompts or generated educational content!
                logger.info(
                    "LLM Generation Success | provider={} model={} latency={:.4f}s "
                    "prompt_tokens={} completion_tokens={} retries={} size={} bytes",
                    response["provider"],
                    response["model"],
                    latency,
                    response["prompt_tokens"],
                    response["completion_tokens"],
                    retries,
                    response_size,
                )
                
                response["latency_seconds"] = latency
                response["retries_count"] = retries
                return response

            except (httpx.HTTPError, ValueError, RuntimeError) as exc:
                latency = time.perf_counter() - attempt_start
                retries += 1
                
                logger.warning(
                    "LLM Generation Attempt {} failed | provider={} latency={:.4f}s error={}",
                    retries,
                    settings.llm_provider,
                    latency,
                    str(exc),
                )

                if retries > self.max_retries:
                    logger.error(
                        "LLM Generation failed after max retries | total_latency={:.4f}s | error={}",
                        time.perf_counter() - start_time,
                        str(exc),
                    )
                    raise RuntimeError(f"LLM Generation failed after {self.max_retries} retries: {str(exc)}") from exc

                await asyncio.sleep(backoff)
                backoff *= 2.0

    async def generate_stream(
        self,
        prompt: str,
        system_prompt: str | None = None,
        options: dict[str, Any] | None = None,
    ) -> AsyncIterator[dict[str, Any]]:
        """
        Execute streaming text generation. Retries are applied for initial connection.

        :param prompt: User instruction prompt.
        :param system_prompt: Optional system-level prompt context.
        :param options: Optional overrides.
        :returns: Async iterator yielding text chunks.
        """
        self.validate_prompt(prompt, system_prompt)

        # Merge defaults hyper-parameters from settings, then override with options
        runtime_options = {
            "temperature": settings.llm_temperature,
            "top_p": settings.llm_top_p,
            "top_k": settings.llm_top_k,
            "max_tokens": settings.llm_max_tokens,
            "repeat_penalty": settings.llm_repeat_penalty,
            "num_ctx": settings.llm_num_ctx,
        }
        if options:
            for k, v in options.items():
                if v is not None:
                    runtime_options[k] = v

        retries = 0
        backoff = 1.0
        start_time = time.perf_counter()
        stream_iter = None

        # Retry loop for connection initialization
        while True:
            try:
                stream_iter = await self.provider.generate_stream(
                    prompt=prompt,
                    system_prompt=system_prompt,
                    options=runtime_options,
                )
                break
            except (httpx.HTTPError, RuntimeError) as exc:
                retries += 1
                logger.warning(
                    "LLM Stream Connection attempt {} failed | error={}",
                    retries,
                    str(exc),
                )
                if retries > self.max_retries:
                    logger.error("LLM Stream Connection failed after max retries")
                    raise RuntimeError(f"LLM Stream Connection failed: {str(exc)}") from exc
                await asyncio.sleep(backoff)
                backoff *= 2.0

        # Generator proxy yielding chunks
        async def response_generator() -> AsyncIterator[dict[str, Any]]:
            total_text = []
            prompt_tokens = 0
            completion_tokens = 0
            model_used = settings.llm_model
            provider_used = settings.llm_provider

            try:
                async for chunk in stream_iter:
                    text_chunk = chunk.get("text", "")
                    total_text.append(text_chunk)
                    
                    if chunk.get("done", False):
                        prompt_tokens = chunk.get("prompt_tokens") or 0
                        completion_tokens = chunk.get("completion_tokens") or 0
                        model_used = chunk.get("model", model_used)
                        provider_used = chunk.get("provider", provider_used)
                        
                        # Validate full accumulated stream response
                        self.validate_response("".join(total_text))

                    yield {
                        "text": text_chunk,
                        "done": chunk.get("done", False),
                    }
            except asyncio.CancelledError:
                logger.info("LLM Generation Stream cancelled by client request.")
                raise
            except Exception as exc:
                logger.error("LLM Generation Stream error during consumption: {}", str(exc))
                raise RuntimeError(f"Stream generation error: {str(exc)}") from exc
            finally:
                # Log completion metrics (without logging content)
                latency = time.perf_counter() - start_time
                full_text = "".join(total_text)
                response_size = len(full_text.encode("utf-8"))

                logger.info(
                    "LLM Stream Finished | provider={} model={} latency={:.4f}s "
                    "prompt_tokens={} completion_tokens={} size={} bytes",
                    provider_used,
                    model_used,
                    latency,
                    prompt_tokens,
                    completion_tokens,
                    response_size,
                )

        return response_generator()

    async def health_check(self) -> bool:
        """Check provider operational status."""
        return await self.provider.health_check()

    async def available_models(self) -> list[str]:
        """Query pulled models list from provider."""
        return await self.provider.available_models()

    async def model_information(self, model_name: str) -> dict[str, Any]:
        """Query metadata of model from provider."""
        return await self.provider.model_information(model_name)
