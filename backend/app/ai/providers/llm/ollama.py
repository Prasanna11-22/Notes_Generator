"""
Concrete implementation of Ollama LLM provider.
"""

import json
from typing import Any, AsyncIterator
import httpx
from loguru import logger

from app.ai.providers.llm.base import LLMProvider


class OllamaProvider(LLMProvider):
    """
    Adapter for local/containerized Ollama service.
    
    Communicates via Ollama HTTP REST API (/api/chat, /api/tags, /api/show).
    """

    def __init__(self, host: str, default_model: str, timeout: float = 60.0) -> None:
        """
        Initialize the Ollama provider.

        :param host: Base URL of the Ollama host (e.g. http://ollama:11434).
        :param default_model: Default model tag (e.g. gemma3:4b).
        :param timeout: Connection timeout in seconds.
        """
        self.host = host.rstrip("/")
        self.default_model = default_model
        self.timeout = timeout

    def _build_payload(
        self,
        prompt: str,
        system_prompt: str | None = None,
        options: dict[str, Any] | None = None,
        stream: bool = False,
    ) -> dict[str, Any]:
        """Format messages and runtime parameters for Ollama /api/chat payload."""
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        # Base configuration from settings/options
        runtime_options = {}
        if options:
            # Map common option names to Ollama option naming convention
            for key in ["temperature", "top_p", "top_k", "repeat_penalty", "num_ctx"]:
                if key in options:
                    runtime_options[key] = options[key]
            # Max tokens translates to num_predict in Ollama
            if "max_tokens" in options:
                runtime_options["num_predict"] = options["max_tokens"]

        payload = {
            "model": options.get("model", self.default_model) if options else self.default_model,
            "messages": messages,
            "stream": stream,
        }
        if runtime_options:
            payload["options"] = runtime_options

        return payload

    async def generate(
        self,
        prompt: str,
        system_prompt: str | None = None,
        options: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Execute block text generation request via Ollama /api/chat."""
        url = f"{self.host}/api/chat"
        payload = self._build_payload(prompt, system_prompt, options, stream=False)
        model_name = payload["model"]

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                response = await client.post(url, json=payload)
                response.raise_for_status()
                data = response.json()
            except httpx.HTTPError as exc:
                logger.error("Ollama connection failed: url={} error={}", url, str(exc))
                raise RuntimeError(f"Ollama provider connection error: {str(exc)}") from exc

        # Extract text content and metadata
        message = data.get("message", {})
        text = message.get("content", "")
        
        # Ollama evaluation metrics
        prompt_tokens = data.get("prompt_eval_count", 0)
        completion_tokens = data.get("eval_count", 0)

        return {
            "text": text,
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "model": model_name,
            "provider": "ollama",
            "done_reason": data.get("done_reason"),
        }

    async def generate_stream(
        self,
        prompt: str,
        system_prompt: str | None = None,
        options: dict[str, Any] | None = None,
    ) -> AsyncIterator[dict[str, Any]]:
        """Execute streaming text generation request via Ollama /api/chat."""
        url = f"{self.host}/api/chat"
        payload = self._build_payload(prompt, system_prompt, options, stream=True)
        model_name = payload["model"]

        async def stream_generator() -> AsyncIterator[dict[str, Any]]:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                try:
                    async with client.stream("POST", url, json=payload) as response:
                        response.raise_for_status()
                        async for line in response.aiter_lines():
                            if not line:
                                continue
                            try:
                                data = json.loads(line)
                            except json.JSONDecodeError:
                                logger.warning("Failed to decode stream line: {}", line)
                                continue

                            chunk_text = data.get("message", {}).get("content", "")
                            done = data.get("done", False)

                            yield {
                                "text": chunk_text,
                                "done": done,
                                "prompt_tokens": data.get("prompt_eval_count") if done else None,
                                "completion_tokens": data.get("eval_count") if done else None,
                                "model": model_name,
                                "provider": "ollama",
                                "done_reason": data.get("done_reason") if done else None,
                            }
                except httpx.HTTPError as exc:
                    logger.error("Ollama stream connection failed: url={} error={}", url, str(exc))
                    raise RuntimeError(f"Ollama stream connection error: {str(exc)}") from exc

        return stream_generator()

    async def health_check(self) -> bool:
        """Verify connection status with the Ollama service."""
        url = f"{self.host}/api/tags"
        async with httpx.AsyncClient(timeout=5.0) as client:
            try:
                response = await client.get(url)
                return response.status_code == 200
            except Exception:
                return False

    async def available_models(self) -> list[str]:
        """Query pulled models list from /api/tags."""
        url = f"{self.host}/api/tags"
        async with httpx.AsyncClient(timeout=5.0) as client:
            try:
                response = await client.get(url)
                response.raise_for_status()
                data = response.json()
                models = data.get("models", [])
                return [m.get("name") for m in models if m.get("name")]
            except Exception as exc:
                logger.error("Ollama available_models failed: url={} error={}", url, str(exc))
                return []

    async def model_information(self, model_name: str) -> dict[str, Any]:
        """Query detailed model metadata from /api/show."""
        url = f"{self.host}/api/show"
        payload = {"name": model_name}
        async with httpx.AsyncClient(timeout=5.0) as client:
            try:
                response = await client.post(url, json=payload)
                response.raise_for_status()
                return response.json()
            except Exception as exc:
                logger.error("Ollama model_information failed for model={} error={}", model_name, str(exc))
                return {}

    def estimate_cost(self, prompt_tokens: int, completion_tokens: int) -> float:
        """Cost is 0.0 for locally hosted open-source models."""
        return 0.0

    def estimate_tokens(self, text: str) -> int:
        """Uses 1-token approx. 4 characters heuristic for Ollama."""
        if not text:
            return 0
        return int(len(text) / 4) + 1
