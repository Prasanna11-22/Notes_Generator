"""
Text Cleaning Pipeline.

Converts raw parser output into clean, semantically consistent text ready
for downstream chunking.  Every cleaning step is a discrete method so that
individual stages can be unit-tested and toggled independently.

Pipeline (in order)
-------------------
1. Unicode fixing (ftfy) — repairs mojibake and broken encodings.
2. Smart-quote / em-dash normalisation — replaces typographic characters
   with their ASCII equivalents.
3. Header / footer heuristic removal — drops lines that look like page
   numbers, running headers, or footers.
4. Hyphenated line-break rejoining — reunites words split across a line
   break by a soft hyphen.
5. Whitespace normalisation — collapses excessive blank lines and trims
   trailing spaces.
6. Duplicate consecutive line removal — removes exact-duplicate lines that
   sometimes appear due to text-layer artefacts.
"""

from __future__ import annotations

import re

from loguru import logger


class TextCleaningPipeline:
    """
    Stateless text cleaning pipeline.

    Usage::

        cleaner = TextCleaningPipeline()
        cleaned = cleaner.clean(raw_text)
    """

    # ── Compiled regexes ──────────────────────────────────────────────────────

    # Page-number-only line: digits (optionally surrounded by whitespace / dashes)
    _RE_PAGE_NUMBER = re.compile(r"^\s*[-–—]?\s*\d{1,4}\s*[-–—]?\s*$", re.MULTILINE)

    # Lines that are just dashes / underscores / equals (separator lines)
    _RE_SEPARATOR = re.compile(r"^\s*[-_=]{3,}\s*$", re.MULTILINE)

    # Hyphenated word break across a line boundary:  "hyphen-\nnext" → "hyphennext"
    _RE_HYPHEN_BREAK = re.compile(r"(\w)-\n(\w)")

    # Three or more consecutive blank lines → exactly two blank lines
    _RE_EXCESS_BLANK = re.compile(r"\n{3,}")

    # Smart quotation marks and typographic dashes
    _CHAR_MAP = str.maketrans(
        {
            "\u2018": "'",   # left single quote
            "\u2019": "'",   # right single quote
            "\u201c": '"',   # left double quote
            "\u201d": '"',   # right double quote
            "\u2013": "-",   # en-dash
            "\u2014": "--",  # em-dash
            "\u2026": "...", # horizontal ellipsis
            "\u00a0": " ",   # non-breaking space
            "\u200b": "",    # zero-width space
        }
    )

    # ── Public API ────────────────────────────────────────────────────────────

    def clean(self, text: str) -> str:
        """
        Run the full cleaning pipeline on *text*.

        :param text: Raw text from a document parser.
        :returns:    Cleaned and normalised text.
        """
        if not text or not text.strip():
            return ""

        logger.debug("TextCleaningPipeline: cleaning {} chars", len(text))

        text = self._fix_unicode(text)
        text = self._normalise_typographic_chars(text)
        text = self._remove_headers_footers(text)
        text = self._rejoin_hyphenated_breaks(text)
        text = self._normalise_whitespace(text)
        text = self._remove_duplicate_lines(text)

        logger.debug(
            "TextCleaningPipeline: cleaned to {} chars", len(text)
        )
        return text

    # ── Pipeline stages ───────────────────────────────────────────────────────

    @staticmethod
    def _fix_unicode(text: str) -> str:
        """Repair broken / mojibake Unicode sequences using ftfy."""
        try:
            import ftfy  # type: ignore[import-untyped]

            return ftfy.fix_text(text)
        except ImportError:
            return text

    def _normalise_typographic_chars(self, text: str) -> str:
        """Replace smart quotes and em/en-dashes with ASCII equivalents."""
        return text.translate(self._CHAR_MAP)

    def _remove_headers_footers(self, text: str) -> str:
        """Remove lines that are page numbers or pure separator lines."""
        text = self._RE_PAGE_NUMBER.sub("", text)
        text = self._RE_SEPARATOR.sub("", text)
        return text

    def _rejoin_hyphenated_breaks(self, text: str) -> str:
        """Reunite words that were split across a line break by a hyphen."""
        return self._RE_HYPHEN_BREAK.sub(r"\1\2", text)

    def _normalise_whitespace(self, text: str) -> str:
        """
        Collapse excessive blank lines and strip trailing whitespace from
        every line.
        """
        # Strip trailing spaces per line
        lines = [line.rstrip() for line in text.splitlines()]
        text = "\n".join(lines)
        # Reduce 3+ blank lines to 2
        text = self._RE_EXCESS_BLANK.sub("\n\n", text)
        return text.strip()

    @staticmethod
    def _remove_duplicate_lines(text: str) -> str:
        """
        Remove consecutive duplicate lines (text-layer copy artefacts).

        Only consecutive identical lines are removed — non-adjacent duplicates
        (e.g. repeated section headers) are left intact.
        """
        lines = text.splitlines()
        deduped: list[str] = []
        prev: str | None = None
        for line in lines:
            if line != prev:
                deduped.append(line)
            prev = line
        return "\n".join(deduped)
