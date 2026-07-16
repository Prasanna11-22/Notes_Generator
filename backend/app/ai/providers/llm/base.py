"""
Abstract Base Class for LLM Providers.
"""

from abc import ABC, abstractmethod
from typing import Any, AsyncIterator


class LLMProvider(ABC):
    """
    Defines the contract for LLM provider adapters.
    
    The orchestrator and downstream services interact exclusively through this
    interface, decoupling business logic from third-party vendor clients.
    """

    @abstractmethod
    async def generate(
        self,
        prompt: str,
        system_prompt: str | None = None,
        options: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """
        Execute a blocking text generation request.

        :param prompt: Hydrated user instruction string.
        :param system_prompt: Optional system-level context.
        :param options: Optional overrides (temperature, top_p, top_k, max_tokens, repeat_penalty, num_ctx).
        :returns: A dictionary containing:
            - "text": str (Generated text response)
            - "prompt_tokens": int (Evaluated prompt tokens count)
            - "completion_tokens": int (Generated response tokens count)
            - "model": str (Name/tag of model used)
            - "provider": str (Identifier of the provider)
        """
        pass

    @abstractmethod
    async def generate_stream(
        self,
        prompt: str,
        system_prompt: str | None = None,
        options: dict[str, Any] | None = None,
    ) -> AsyncIterator[dict[str, Any]]:
        """
        Execute a streaming text generation request.

        :param prompt: Hydrated user instruction string.
        :param system_prompt: Optional system-level context.
        :param options: Optional overrides (temperature, top_p, top_k, max_tokens, repeat_penalty, num_ctx).
        :yields: Dictionaries representing text chunks containing:
            - "text": str (Chunk text snippet)
            - "done": bool (Flag indicating completion)
            - "prompt_tokens": int | None (Evaluated prompt tokens count, sent in final chunk)
            - "completion_tokens": int | None (Generated response tokens count, sent in final chunk)
        """
        pass

    @abstractmethod
    async def health_check(self) -> bool:
        """
        Verify connection status with the LLM API provider.

        :returns: True if the provider is fully operational, False otherwise.
        """
        pass

    @abstractmethod
    async def available_models(self) -> list[str]:
        """
        Retrieve list of locally pulled/available model tags.

        :returns: A list of available model tags.
        """
        pass

    @abstractmethod
    async def model_information(self, model_name: str) -> dict[str, Any]:
        """
        Query provider metadata of a model (parameter count, architecture, family).

        :param model_name: The name/tag of the model.
        :returns: A dictionary containing model details.
        """
        pass

    @abstractmethod
    def estimate_cost(self, prompt_tokens: int, completion_tokens: int) -> float:
        """
        Calculate execution cost. Returns 0.0 for local providers (Ollama).

        :param prompt_tokens: Tokens evaluated in the request.
        :param completion_tokens: Tokens generated in the response.
        :returns: Cost in USD.
        """
        pass

    @abstractmethod
    def estimate_tokens(self, text: str) -> int:
        """
        Estimate character token count based on provider specific heuristic.

        :param text: The text to estimate token count for.
        :returns: The estimated token count.
        """
        pass
