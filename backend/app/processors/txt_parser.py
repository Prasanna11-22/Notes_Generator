"""
TXT Parser.

Reads plain-text files with automatic encoding detection via ``chardet``.
Falls back to UTF-8 (with ``errors='replace'``) when detection fails.
"""

from __future__ import annotations

from loguru import logger

from app.processors.base import BaseParser, ParseResult

_SUPPORTED_MIME_TYPES = frozenset({"text/plain"})

# Minimum confidence threshold for chardet encoding detection (0–1).
_MIN_CONFIDENCE = 0.6


class TXTParser(BaseParser):
    """Extract text from plain-text (``.txt``) files."""

    @property
    def supported_mime_types(self) -> frozenset[str]:
        return _SUPPORTED_MIME_TYPES

    def parse(self, file_bytes: bytes, filename: str) -> ParseResult:
        """Decode a plain-text byte stream into a ``ParseResult``."""
        logger.debug("TXTParser: parsing '{}' ({} bytes)", filename, len(file_bytes))

        encoding = self._detect_encoding(file_bytes)
        try:
            raw_text = file_bytes.decode(encoding, errors="replace")
        except (UnicodeDecodeError, LookupError):
            raw_text = file_bytes.decode("utf-8", errors="replace")
            encoding = "utf-8"

        # Rough page estimate: ~3 000 chars per page (approx. 500 words)
        char_count = len(raw_text)
        approx_pages = max(1, char_count // 3000)

        metadata: dict = {
            "encoding": encoding,
            "approx_page_count": approx_pages,
            "parser_backend": "built-in",
        }

        return ParseResult(
            raw_text=raw_text,
            page_count=approx_pages,
            parser_name="TXTParser(built-in)",
            metadata=metadata,
            is_scanned=False,
        )

    # ── Private helpers ───────────────────────────────────────────────────────

    @staticmethod
    def _detect_encoding(file_bytes: bytes) -> str:
        """
        Attempt chardet encoding detection.

        Returns the detected encoding when confidence exceeds
        ``_MIN_CONFIDENCE``, otherwise falls back to ``"utf-8"``.
        """
        try:
            import chardet  # type: ignore[import-untyped]

            result = chardet.detect(file_bytes)
            confidence: float = result.get("confidence") or 0.0
            encoding: str | None = result.get("encoding")
            if encoding and confidence >= _MIN_CONFIDENCE:
                logger.debug(
                    "TXTParser: detected encoding '{}' (confidence {:.0%})",
                    encoding,
                    confidence,
                )
                return encoding
        except ImportError:
            pass
        return "utf-8"
