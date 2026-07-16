"""
Prompt Optimization Service.

Responsible for compressing, cleaning, and deduplicating prompt text context.
Operates as a pure-function service with no I/O or external dependencies.
"""

import re


class PromptOptimizationService:
    """
    Service responsible for compressing, cleaning, and deduplicating prompt text context.

    Each public method is a single-responsibility transformation.  ``optimize_context``
    runs the full pipeline in the correct order.
    """

    @staticmethod
    def cleanup_whitespace(text: str) -> str:
        """
        Collapse consecutive whitespace/tabs to a single space and limit
        consecutive blank lines to at most one blank line (paragraph separator).

        Does NOT remove intentional single blank lines between paragraphs.
        """
        if not text:
            return ""
        # Strip each line's internal horizontal whitespace runs to one space
        lines = [re.sub(r"[ \t]+", " ", line).strip() for line in text.splitlines()]
        # Suppress runs of more than one blank line, keep one blank line max
        result_lines: list[str] = []
        for line in lines:
            if line:
                result_lines.append(line)
            else:
                # Only append a blank separator if last emitted line was non-empty
                if result_lines and result_lines[-1] != "":
                    result_lines.append("")
        # Remove trailing blank line if present
        if result_lines and result_lines[-1] == "":
            result_lines.pop()
        return "\n".join(result_lines).strip()

    @staticmethod
    def remove_duplicate_sentences(text: str) -> str:
        """
        Remove exact-duplicate sentences from text while preserving paragraph
        structure.

        Splits on sentence-terminal punctuation followed by whitespace, then
        reconstructs using a space separator (matching standard prose flow).
        Case-insensitive deduplication — the first occurrence is kept verbatim.
        """
        if not text:
            return ""
        # Split by sentence-terminal boundaries (lookbehind for .!?)
        sentences = re.split(r"(?<=[.!?])\s+", text)
        seen: set[str] = set()
        unique_sentences: list[str] = []
        for s in sentences:
            s_key = s.strip().lower()
            if s_key not in seen:
                seen.add(s_key)
                unique_sentences.append(s)
        # Re-join with a single space — original punctuation provides visual breaks
        return " ".join(unique_sentences)

    @staticmethod
    def strip_metadata_artifacts(text: str) -> str:
        """
        Remove common document-parser metadata artifacts from chunk text:

        - Document-scanner page markers (e.g. ``[Page 12]``)
        - File-path remnants (e.g. ``/tmp/upload_xxxx.pdf``)
        - Excess hash/rule separator lines (``----``, ``====``)
        """
        if not text:
            return ""
        # Remove [Page N] / (Page N) markers
        text = re.sub(r"\[?Page\s+\d+\]?", "", text, flags=re.IGNORECASE)
        # Remove file path fragments
        text = re.sub(r"\S+\.(?:pdf|docx?|pptx?|txt)\b", "", text, flags=re.IGNORECASE)
        # Collapse lines consisting only of dashes/equals/underscores (3+)
        text = re.sub(r"^[-=_]{3,}$", "", text, flags=re.MULTILINE)
        return text.strip()

    def optimize_context(self, context: str) -> str:
        """
        Run the complete context-optimization pipeline:

        1. Strip metadata artifacts.
        2. Clean up whitespace.
        3. Deduplicate redundant sentences.
        """
        if not context:
            return ""
        context = self.strip_metadata_artifacts(context)
        context = self.cleanup_whitespace(context)
        context = self.remove_duplicate_sentences(context)
        return context
