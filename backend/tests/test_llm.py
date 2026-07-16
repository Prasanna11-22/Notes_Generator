"""
Unit and Integration Tests for Phase 9 Enterprise LLM Orchestrator.
"""

import json
from typing import AsyncIterator
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi import status
from httpx import AsyncClient, HTTPError, Response

from app.ai.providers import get_llm_provider
from app.ai.providers.llm.base import LLMProvider
from app.ai.providers.llm.ollama import OllamaProvider
from app.core.config import settings
from app.schemas.llm import LLMGenerateRequest
from app.services.llm_orchestrator import LLMOrchestratorService


# ── 1. Unit Tests (Strictly Mocked, No Network) ──────────────────────────────


class DummyLLMProvider(LLMProvider):
    """A dummy provider implementation for orchestrator testing."""

    def __init__(self, response_text: str = "Hello.", fail_count: int = 0) -> None:
        self.response_text = response_text
        self.fail_count = fail_count
        self.attempts = 0

    async def generate(self, prompt: str, system_prompt: str | None = None, options: dict | None = None) -> dict:
        self.attempts += 1
        if self.attempts <= self.fail_count:
            raise HTTPError("Mocked connection failure")
        return {
            "text": self.response_text,
            "prompt_tokens": 10,
            "completion_tokens": 20,
            "model": "dummy",
            "provider": "dummy",
            "done_reason": "stop",
        }

    async def generate_stream(self, prompt: str, system_prompt: str | None = None, options: dict | None = None) -> AsyncIterator[dict]:
        self.attempts += 1
        if self.attempts <= self.fail_count:
            raise HTTPError("Mocked stream connection failure")

        async def generator():
            yield {"text": self.response_text, "done": True, "prompt_tokens": 10, "completion_tokens": 20}
        return generator()

    async def health_check(self) -> bool:
        return True

    async def available_models(self) -> list[str]:
        return ["dummy-model"]

    async def model_information(self, model_name: str) -> dict:
        return {"name": model_name}

    def estimate_cost(self, prompt_tokens: int, completion_tokens: int) -> float:
        return 0.0

    def estimate_tokens(self, text: str) -> int:
        return len(text) // 4 + 1


class TestTokenEstimator:
    def test_estimate_tokens(self):
        provider = DummyLLMProvider()
        assert provider.estimate_tokens("abcd") == 2
        assert provider.estimate_tokens("") == 1  # 0 // 4 + 1


class TestResponseValidation:
    def test_validate_response_success(self):
        orchestrator = LLMOrchestratorService(DummyLLMProvider())
        # Should not raise any error
        orchestrator.validate_response("This is a valid response.")
        orchestrator.validate_response("```python\nprint('hello')\n```")

    def test_validate_response_empty(self):
        orchestrator = LLMOrchestratorService(DummyLLMProvider())
        with pytest.raises(ValueError, match="Generated response is empty"):
            orchestrator.validate_response("   ")

    def test_validate_response_json(self):
        orchestrator = LLMOrchestratorService(DummyLLMProvider())
        # Valid JSON
        orchestrator.validate_response('{"status": "ok"}', require_json=True)
        # Markdown JSON code fence
        orchestrator.validate_response('```json\n{"status": "ok"}\n```', require_json=True)
        # Invalid JSON
        with pytest.raises(ValueError, match="Response is not valid JSON"):
            orchestrator.validate_response('{"status": "ok"', require_json=True)

    def test_validate_response_unclosed_markdown(self):
        orchestrator = LLMOrchestratorService(DummyLLMProvider())
        with pytest.raises(ValueError, match="unclosed code block fences"):
            orchestrator.validate_response("Here is code: ```python print('hello')")

    def test_validate_response_truncation(self):
        orchestrator = LLMOrchestratorService(DummyLLMProvider())
        with pytest.raises(ValueError, match="truncated mid-sentence"):
            # Ends in a letter instead of terminal punctuation
            orchestrator.validate_response("The answer to the question is simple")


class TestOrchestratorRetryLogic:
    @pytest.mark.asyncio
    async def test_retry_on_network_failure(self):
        # Fails once, succeeds on the second try
        provider = DummyLLMProvider(response_text="Success.", fail_count=1)
        orchestrator = LLMOrchestratorService(provider, max_retries=2)
        
        # Patch sleep to keep tests fast
        with patch("asyncio.sleep", return_value=None):
            res = await orchestrator.generate("Test prompt")
            assert res["text"] == "Success."
            assert provider.attempts == 2

    @pytest.mark.asyncio
    async def test_retry_exhausted_raises(self):
        # Fails 3 times, but we only allow 2 retries (3 attempts total)
        provider = DummyLLMProvider(response_text="Success.", fail_count=3)
        orchestrator = LLMOrchestratorService(provider, max_retries=2)
        
        with patch("asyncio.sleep", return_value=None):
            with pytest.raises(RuntimeError, match="failed after 2 retries"):
                await orchestrator.generate("Test prompt")
            assert provider.attempts == 3

    @pytest.mark.asyncio
    async def test_retry_on_validation_failure(self):
        # Returns truncated text first, then valid text
        class TruncatingProvider(DummyLLMProvider):
            async def generate(self, prompt: str, system_prompt: str | None = None, options: dict | None = None) -> dict:
                self.attempts += 1
                text = "Truncated answer" if self.attempts == 1 else "Valid answer."
                return {
                    "text": text,
                    "prompt_tokens": 10,
                    "completion_tokens": 20,
                    "model": "dummy",
                    "provider": "dummy",
                    "done_reason": "stop",
                }

        provider = TruncatingProvider()
        orchestrator = LLMOrchestratorService(provider, max_retries=2)

        with patch("asyncio.sleep", return_value=None):
            res = await orchestrator.generate("Test prompt")
            assert res["text"] == "Valid answer."
            assert provider.attempts == 2


class TestOllamaProviderUnit:
    @pytest.mark.asyncio
    @patch("httpx.AsyncClient.post")
    async def test_generate_success(self, mock_post):
        mock_response = MagicMock(spec=Response)
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "model": "gemma3:4b",
            "message": {"role": "assistant", "content": "Hello there!"},
            "prompt_eval_count": 12,
            "eval_count": 8,
            "done_reason": "stop",
        }
        mock_post.return_value = mock_response

        provider = OllamaProvider(host="http://test:11434", default_model="gemma3:4b")
        res = await provider.generate("Hi")
        assert res["text"] == "Hello there!"
        assert res["prompt_tokens"] == 12
        assert res["completion_tokens"] == 8
        assert res["model"] == "gemma3:4b"

    @pytest.mark.asyncio
    @patch("httpx.AsyncClient.post")
    async def test_generate_error(self, mock_post):
        mock_post.side_effect = HTTPError("Network down")
        provider = OllamaProvider(host="http://test:11434", default_model="gemma3:4b")
        with pytest.raises(RuntimeError, match="Ollama provider connection error"):
            await provider.generate("Hi")

    @pytest.mark.asyncio
    @patch("httpx.AsyncClient.get")
    async def test_health_check_healthy(self, mock_get):
        mock_response = MagicMock(spec=Response)
        mock_response.status_code = 200
        mock_get.return_value = mock_response

        provider = OllamaProvider(host="http://test:11434", default_model="gemma3:4b")
        assert await provider.health_check() is True

    @pytest.mark.asyncio
    @patch("httpx.AsyncClient.get")
    async def test_health_check_unhealthy(self, mock_get):
        mock_get.side_effect = Exception("Connection refused")
        provider = OllamaProvider(host="http://test:11434", default_model="gemma3:4b")
        assert await provider.health_check() is False


# ── 2. Mocked Endpoint API Tests (Faculty Role) ──────────────────────────────


@pytest.mark.asyncio
class TestLLMAPI:
    @patch("app.services.llm_orchestrator.LLMOrchestratorService.generate")
    async def test_generate_endpoint_success(self, mock_orchestrator, client: AsyncClient, auth_headers: dict):
        mock_orchestrator.return_value = {
            "text": "This is generated educational content.",
            "prompt_tokens": 15,
            "completion_tokens": 30,
            "model": settings.llm_model,
            "provider": settings.llm_provider,
            "latency_seconds": 1.25,
            "retries_count": 0,
        }

        res = await client.post(
            "/api/v1/llm/generate",
            headers=auth_headers,
            json={
                "prompt": "Create learning notes for unit 1",
                "system_prompt": "You are a teacher",
                "require_json": False,
            },
        )
        assert res.status_code == 200
        payload = res.json()
        assert payload["success"] is True
        assert "latency_seconds" in payload["data"]
        assert payload["data"]["text"] == "This is generated educational content."

    async def test_generate_endpoint_forbidden_for_students(self, client: AsyncClient, db_session: AsyncSession):
        """Standard student users must be blocked from LLM query invocation."""
        from app.core.security import hash_password
        from app.models.user import User
        
        hashed_pwd = await hash_password("pwd123")
        student_user = User(
            email="student@univ.edu",
            hashed_password=hashed_pwd,
            full_name="Student",
            role="student",
            is_active=True,
        )
        db_session.add(student_user)
        await db_session.flush()

        login_res = await client.post(
            "/api/v1/auth/login",
            json={"email": "student@univ.edu", "password": "pwd123"},
        )
        token = login_res.json()["data"]["access_token"]
        student_headers = {"Authorization": f"Bearer {token}"}

        res = await client.post(
            "/api/v1/llm/generate",
            headers=student_headers,
            json={"prompt": "Explain math"},
        )
        assert res.status_code == 403

    @patch("app.services.llm_orchestrator.LLMOrchestratorService.available_models")
    async def test_list_models_endpoint(self, mock_available_models, client: AsyncClient, auth_headers: dict):
        mock_available_models.return_value = [settings.llm_model]
        res = await client.get("/api/v1/llm/models", headers=auth_headers)
        assert res.status_code == 200
        payload = res.json()
        assert settings.llm_model in payload["data"]["models"]

    async def test_get_provider_details_endpoint(self, client: AsyncClient, auth_headers: dict):
        res = await client.get("/api/v1/llm/provider", headers=auth_headers)
        assert res.status_code == 200
        payload = res.json()
        assert payload["data"]["provider"] == settings.llm_provider

    @patch("app.services.llm_orchestrator.LLMOrchestratorService.health_check")
    async def test_health_endpoint(self, mock_health, client: AsyncClient, auth_headers: dict):
        mock_health.return_value = True
        res = await client.get("/api/v1/llm/health", headers=auth_headers)
        assert res.status_code == 200
        assert res.json()["data"]["status"] == "healthy"

    async def test_validate_response_endpoint_success(self, client: AsyncClient, auth_headers: dict):
        res = await client.post(
            "/api/v1/llm/validate",
            headers=auth_headers,
            json={
                "text": "This is a completed sentence.",
                "require_json": False,
            },
        )
        assert res.status_code == 200
        assert res.json()["data"]["success"] is True

    async def test_validate_response_endpoint_failure(self, client: AsyncClient, auth_headers: dict):
        res = await client.post(
            "/api/v1/llm/validate",
            headers=auth_headers,
            json={
                "text": "This text is obviously truncated",
                "require_json": False,
            },
        )
        assert res.status_code == 200
        assert res.json()["data"]["success"] is False
        assert "truncated" in res.json()["data"]["message"]


# ── 3. Integration Tests (Queries Live Ollama Server, Graceful Skip) ──────────


@pytest.mark.asyncio
class TestLLMIntegration:
    async def test_live_ollama_pipeline(self):
        """
        Integrates with the live OLLAMA_HOST from environment.
        Skips gracefully if the local service is not reachable.
        """
        provider = get_llm_provider()
        is_healthy = await provider.health_check()
        
        if not is_healthy:
            pytest.skip(f"Ollama server is not active at {settings.ollama_host}. Skipping integration check.")

        # If healthy, verify available models lists pulled models
        models = await provider.available_models()
        assert isinstance(models, list)

        # Skip if the target model is not pulled/available in local Ollama
        target_model = settings.llm_model
        model_available = False
        for m in models:
            if m == target_model or m.split(":")[0] == target_model.split(":")[0]:
                model_available = True
                break

        if not model_available:
            pytest.skip(f"Model {target_model} is not pulled/available in Ollama. Skipping integration check.")

        # Run a simple check request
        orchestrator = LLMOrchestratorService(provider, max_retries=1)
        try:
            res = await orchestrator.generate(
                prompt="Say 'Hello' in exactly one word.",
                system_prompt="You are a helpful assistant.",
            )
            assert "text" in res
            assert len(res["text"].strip()) > 0
            assert res["prompt_tokens"] >= 0
            assert res["completion_tokens"] >= 0
        except Exception as exc:
            pytest.fail(f"Live Ollama generation failed despite successful health check: {str(exc)}")
