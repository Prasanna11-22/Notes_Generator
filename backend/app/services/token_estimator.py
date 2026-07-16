"""
Token Estimator Service.

Provides fast, dependency-free token count approximations for prompt text.
Uses a heuristic of 1 token ≈ 4 characters (GPT-family standard).
Intended for budget-planning and prompt-truncation decisions — not for
billing-grade precision.
"""


class TokenEstimatorService:
    """
    Estimates token counts for prompt text inputs.

    Uses the standard character-to-token ratio heuristic (1 token ≈ 4 characters)
    employed by OpenAI documentation.  The +1 accounts for BOS/rounding.

    This estimator is stateless and all methods are class-level (no instantiation
    required), though the class form allows dependency injection and mocking.
    """

    @staticmethod
    def estimate_tokens(text: str | None) -> int:
        """
        Estimate token size of a string.

        :param text: Any string value, or ``None``.
        :returns: Estimated token count (>= 0).  Returns 0 for falsy inputs.
        """
        if not text:
            return 0
        if not isinstance(text, str):
            try:
                text = str(text)
            except Exception:
                return 0
        # Strip null bytes before measuring length
        text = text.replace("\x00", "")
        # Average English token is ~4 chars; +1 accounts for BOS/rounding overhead
        return max(0, int(len(text) / 4) + 1)

    @staticmethod
    def estimate_tokens_for_chunks(chunks: list[dict]) -> int:
        """
        Estimate the total token cost of a list of retrieved chunk dicts.

        :param chunks: List of dicts with at least a ``text`` key.
        :returns: Sum of token estimates across all chunk texts.
        """
        total = 0
        for chunk in chunks:
            text = chunk.get("text", "") or ""
            if text and isinstance(text, str):
                total += max(0, int(len(text) / 4) + 1)
        return total
