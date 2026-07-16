"""
Chunk Quality Validator.

Evaluates raw chunk segments against specific length and heuristic quality rules
to reject noise, fragments, or garbage content.
"""

from __future__ import annotations

from app.core.config import settings
from app.services.chunking.base import RawChunk


class ChunkQualityValidator:
    """
    Validates chunk quality based on text characteristics.

    Checks:
    - Minimum character length.
    - Maximum character length.
    - Non-empty content.
    - Symbol/punctuation density.
    - Meaningless repeat patterns.
    """

    def __init__(
        self,
        min_len: int | None = None,
        max_len: int | None = None,
    ) -> None:
        self._min_len = min_len or settings.min_chunk_char_length
        self._max_len = max_len or settings.max_chunk_char_length

    def is_valid(self, chunk: RawChunk) -> tuple[bool, str | None]:
        """
        Run validation on *chunk*.

        :returns: Tuple of (is_valid: bool, reject_reason: str | None).
        """
        text = chunk.cleaned_text.strip()

        # 1. Reject empty
        if not text:
            return False, "Chunk text is empty."

        # 2. Reject excessively short (fragments)
        char_len = len(text)
        if char_len < self._min_len:
            return (
                False,
                f"Chunk character length ({char_len}) is below minimum limit ({self._min_len}).",
            )

        # 3. Reject excessively long
        if char_len > self._max_len:
            return (
                False,
                f"Chunk character length ({char_len}) exceeds maximum limit ({self._max_len}).",
            )

        # 4. Reject chunks that consist only of punctuation / whitespaces
        words = text.split()
        if not words:
            return False, "Chunk contains no word characters."

        # 5. Density check: reject chunks with excessive symbols (likely formatting/code noise)
        alphabetic_chars = sum(1 for c in text if c.isalnum())
        symbol_ratio = 1.0 - (alphabetic_chars / char_len)
        if symbol_ratio > 0.70:  # >70% punctuation or control chars
            return (
                False,
                f"Excessive symbol density ({symbol_ratio:.1%}). Likely parsing noise.",
            )

        # 6. Repetition check: check for repetition of the same character
        # e.g., "xxxxxxxxxxxxxxxx"
        if len(set(text)) <= 3 and char_len > 15:
            return False, "Repeated character sequence detected."

        return True, None
