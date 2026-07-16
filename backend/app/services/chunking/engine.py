"""
Chunking Strategy implementations.

Defines:
- ``SpaCyChunker``: Uses spaCy sentence splitting with block preservation.
- ``NLTKChunker``: Uses NLTK sentence tokenization with block preservation.
- ``RegexChunker``: Uses regex paragraph boundary split.
"""

from __future__ import annotations

import re
from loguru import logger

from app.core.config import settings
from app.services.chunking.base import BaseChunker, RawChunk


class BlockProtector:
    """
    Scans document text to locate contiguous block boundaries that should not
    be split.

    Supports:
    - Code blocks (``` fenced)
    - Markdown tables (| grid)
    - Contiguous Lists (bulleted/numbered)
    - Math formulas ($$, \\[)
    - Algorithms (Algorithm/Procedure blocks)
    """

    # Matches code blocks
    _RE_CODE = re.compile(r"```[\s\S]*?```")
    # Matches math blocks
    _RE_MATH = re.compile(r"\$\$[\s\S]*?\$\$|\\\[[\s\S]*?\\\]")
    # Matches standard pseudocode keywords for algorithms
    _RE_ALGORITHM = re.compile(
        r"(?:^|\n)\s*(?:Algorithm|Procedure|Function|Input|Output):?\s[\s\S]*?(?=\n\s*\n|$)",
        re.IGNORECASE,
    )

    @classmethod
    def get_protected_spans(cls, text: str) -> list[tuple[int, int]]:
        """Return a sorted list of (start, end) character spans to protect."""
        spans: list[tuple[int, int]] = []

        # 1. Code blocks
        for m in cls._RE_CODE.finditer(text):
            spans.append(m.span())

        # 2. Math blocks
        for m in cls._RE_MATH.finditer(text):
            spans.append(m.span())

        # 3. Algorithms
        for m in cls._RE_ALGORITHM.finditer(text):
            spans.append(m.span())

        # 4. Tables (contiguous lines containing '|')
        lines = text.splitlines(keepends=True)
        in_table = False
        table_start = 0
        current_idx = 0

        for line in lines:
            length = len(line)
            is_table_line = "|" in line
            if is_table_line:
                if not in_table:
                    in_table = True
                    table_start = current_idx
            else:
                if in_table:
                    in_table = False
                    spans.append((table_start, current_idx))
            current_idx += length
        if in_table:
            spans.append((table_start, current_idx))

        # 5. Lists (contiguous bulleted or numbered lines)
        in_list = False
        list_start = 0
        current_idx = 0
        re_list_item = re.compile(r"^\s*([-*+•]|\d+\.)\s+")

        for line in lines:
            length = len(line)
            is_list_line = bool(re_list_item.match(line))
            if is_list_line:
                if not in_list:
                    in_list = True
                    list_start = current_idx
            else:
                if in_list:
                    in_list = False
                    spans.append((list_start, current_idx))
            current_idx += length
        if in_list:
            spans.append((list_start, current_idx))

        # Merge overlapping or touching spans
        if not spans:
            return []

        spans.sort(key=lambda x: x[0])
        merged = [spans[0]]
        for current in spans[1:]:
            prev = merged[-1]
            if current[0] <= prev[1]:
                merged[-1] = (prev[0], max(prev[1], current[1]))
            else:
                merged.append(current)

        return merged

    @staticmethod
    def is_inside_protected_span(idx: int, spans: list[tuple[int, int]]) -> bool:
        """Check if character index falls inside any protected spans."""
        for start, end in spans:
            if start <= idx < end:
                return True
            if idx < start:
                break
        return False


# ── Sentence / Block Aggregation Helper ───────────────────────────────────────


def _aggregate_into_chunks(
    sentences_with_spans: list[tuple[str, int, int]],
    cleaned_text: str,
    raw_text: str,
    chunk_size: int,
    chunk_overlap: int,
) -> list[RawChunk]:
    """
    Takes tokenized sentences (with character start/end index mappings on
    cleaned_text) and joins them into raw chunks matching the target size
    and overlap.

    Also attempts to map structural headings located nearby the text spans.
    """
    chunks: list[RawChunk] = []
    current_sentences: list[tuple[str, int, int]] = []
    current_length = 0

    # Locate markdown headings (e.g. # Chapter, ## Section) for outline context
    heading_pattern = re.compile(r"^(#{1,6})\s+(.+)$", re.MULTILINE)
    headings = [(m.start(), len(m.group(1)), m.group(2).strip()) for m in heading_pattern.finditer(cleaned_text)]

    def get_context_headings(start_idx: int) -> tuple[str | None, str | None, str | None]:
        """Resolve current chapter, section, and subheading by looking backwards."""
        chapter, section, sub = None, None, None
        for idx, level, text in headings:
            if idx > start_idx:
                break
            if level == 1:
                chapter = text
                section, sub = None, None  # reset on new chapter
            elif level == 2:
                section = text
                sub = None
            elif level >= 3:
                sub = text
        return chapter, section, sub

    def create_chunk(sentence_group: list[tuple[str, int, int]]) -> RawChunk:
        """Create a RawChunk mapping cleaned boundaries back to raw text."""
        start_clean = sentence_group[0][1]
        end_clean = sentence_group[-1][2]

        cleaned_slice = cleaned_text[start_clean:end_clean]

        # Map to raw text using basic ratio approximation (or equal slicing)
        # to ensure raw matches the same boundary area.
        len_clean_total = len(cleaned_text)
        len_raw_total = len(raw_text)
        if len_clean_total > 0:
            ratio = len_raw_total / len_clean_total
            start_raw = int(start_clean * ratio)
            end_raw = int(end_clean * ratio)
            raw_slice = raw_text[start_raw:end_raw]
        else:
            raw_slice = cleaned_slice

        chapter, section, sub = get_context_headings(start_clean)

        # Estimate page number from page-indicator headers if available
        # e.g. "--- Page X ---" marker in text
        page_indicator = re.compile(r"--- Slide (\d+) ---|--- Page (\d+) ---")
        matches = page_indicator.findall(cleaned_text[:end_clean])
        pages = [m[0] or m[1] for m in matches if m[0] or m[1]]
        page_str = pages[-1] if pages else "1"

        return RawChunk(
            cleaned_text=cleaned_slice,
            raw_text=raw_slice,
            page_numbers=page_str,
            chapter_name=chapter,
            section_heading=section,
            subheading=sub,
        )

    for sent, start, end in sentences_with_spans:
        sent_len = len(sent)

        # If a single sentence exceeds the chunk size, we force flush
        # current buffer, and start this sentence in its own chunk.
        if current_length + sent_len > chunk_size and current_sentences:
            chunks.append(create_chunk(current_sentences))

            # Maintain overlap by rolling back sentences that fit within overlap limit
            overlap_sentences: list[tuple[str, int, int]] = []
            overlap_len = 0
            for osent, ostart, oend in reversed(current_sentences):
                olen = len(osent)
                if overlap_len + olen <= chunk_overlap:
                    overlap_sentences.insert(0, (osent, ostart, oend))
                    overlap_len += olen
                else:
                    break
            current_sentences = overlap_sentences
            current_length = overlap_len

        current_sentences.append((sent, start, end))
        current_length += sent_len

    if current_sentences:
        chunks.append(create_chunk(current_sentences))

    return chunks


# ── SpaCy Chunker Strategy ───────────────────────────────────────────────────


class SpaCyChunker(BaseChunker):
    """
    Splits text semantically using spaCy sentence boundaries.

    Ensures mathematical blocks, code blocks, lists, and tables are protected
    from sentence splits by combining them into singular text segments.
    """

    def split_text(
        self,
        cleaned_text: str,
        raw_text: str,
        *,
        chunk_size: int = 1000,
        chunk_overlap: int = 200,
    ) -> list[RawChunk]:
        import spacy

        nlp = spacy.load(settings.spacy_model, disable=["ner"])
        if "parser" not in nlp.pipe_names and "senter" not in nlp.pipe_names:
            nlp.add_pipe("sentencizer")

        protected_spans = BlockProtector.get_protected_spans(cleaned_text)
        doc = nlp(cleaned_text)

        sentences_with_spans: list[tuple[str, int, int]] = []

        # Iterate sentences from spaCy, but merge sentences if they lie
        # inside a protected span.
        current_span_text = ""
        current_span_start = -1
        current_span_end = -1

        for sent in doc.sents:
            start = sent.start_char
            end = sent.end_char
            text = sent.text

            is_protected = BlockProtector.is_inside_protected_span(start, protected_spans)

            if is_protected:
                # Find which specific span we belong to
                target_span = next(
                    (s for s in protected_spans if s[0] <= start < s[1]), None
                )
                if target_span:
                    span_start, span_end = target_span
                    if current_span_start == -1:
                        current_span_start = span_start
                        current_span_end = span_end
                        current_span_text = cleaned_text[span_start:span_end]
                    continue

            # We are outside protected spans. If we just exited one, flush it first
            if current_span_start != -1:
                sentences_with_spans.append(
                    (current_span_text, current_span_start, current_span_end)
                )
                current_span_start = -1
                current_span_text = ""

            sentences_with_spans.append((text, start, end))

        # Final flush
        if current_span_start != -1:
            sentences_with_spans.append(
                (current_span_text, current_span_start, current_span_end)
            )

        return _aggregate_into_chunks(
            sentences_with_spans,
            cleaned_text,
            raw_text,
            chunk_size,
            chunk_overlap,
        )


# ── NLTK Chunker Strategy ─────────────────────────────────────────────────────


class NLTKChunker(BaseChunker):
    """
    Splits text semantically using NLTK sentence tokenization.

    Acts as a fast fallback with matching block protection logic.
    """

    def split_text(
        self,
        cleaned_text: str,
        raw_text: str,
        *,
        chunk_size: int = 1000,
        chunk_overlap: int = 200,
    ) -> list[RawChunk]:
        from nltk.tokenize import sent_tokenize

        protected_spans = BlockProtector.get_protected_spans(cleaned_text)

        # To extract sentences while preserving indices, we tokenize and search
        # for character indices in the source text sequentially.
        raw_sentences = sent_tokenize(cleaned_text)

        sentences_with_spans: list[tuple[str, int, int]] = []
        search_cursor = 0

        # Pre-process NLTK sentences to group those inside protected spans
        grouped_sentences: list[tuple[str, int, int]] = []

        for sent in raw_sentences:
            start = cleaned_text.find(sent, search_cursor)
            if start == -1:
                start = cleaned_text.find(sent)  # backup search
            if start == -1:
                continue
            end = start + len(sent)
            search_cursor = end

            grouped_sentences.append((sent, start, end))

        current_span_text = ""
        current_span_start = -1
        current_span_end = -1

        for text, start, end in grouped_sentences:
            is_protected = BlockProtector.is_inside_protected_span(start, protected_spans)

            if is_protected:
                target_span = next(
                    (s for s in protected_spans if s[0] <= start < s[1]), None
                )
                if target_span:
                    span_start, span_end = target_span
                    if current_span_start == -1:
                        current_span_start = span_start
                        current_span_end = span_end
                        current_span_text = cleaned_text[span_start:span_end]
                    continue

            if current_span_start != -1:
                sentences_with_spans.append(
                    (current_span_text, current_span_start, current_span_end)
                )
                current_span_start = -1
                current_span_text = ""

            sentences_with_spans.append((text, start, end))

        if current_span_start != -1:
            sentences_with_spans.append(
                (current_span_text, current_span_start, current_span_end)
            )

        return _aggregate_into_chunks(
            sentences_with_spans,
            cleaned_text,
            raw_text,
            chunk_size,
            chunk_overlap,
        )


# ── Regex Paragraph Fallback Chunker Strategy ─────────────────────────────────


class RegexChunker(BaseChunker):
    """
    Simple chunker splitting on paragraph borders (\n\n) without NLP tools.

    Guarantees no splits on contiguous lines (meaning lists, tables,
    and code block fences remain unified within paragraph bounds).
    """

    def split_text(
        self,
        cleaned_text: str,
        raw_text: str,
        *,
        chunk_size: int = 1000,
        chunk_overlap: int = 200,
    ) -> list[RawChunk]:
        # Split on double newline (paragraphs)
        paragraphs = cleaned_text.split("\n\n")

        sentences_with_spans: list[tuple[str, int, int]] = []
        search_cursor = 0

        for para in paragraphs:
            para_stripped = para.strip()
            if not para_stripped:
                continue
            start = cleaned_text.find(para, search_cursor)
            if start == -1:
                start = cleaned_text.find(para)
            if start == -1:
                continue
            end = start + len(para)
            search_cursor = end

            sentences_with_spans.append((para_stripped, start, end))

        return _aggregate_into_chunks(
            sentences_with_spans,
            cleaned_text,
            raw_text,
            chunk_size,
            chunk_overlap,
        )


# ── Chunker Factory ───────────────────────────────────────────────────────────


class ChunkerFactory:
    """Instantiates the configured text chunking engine."""

    @staticmethod
    def get_chunker(strategy: str | None = None) -> BaseChunker:
        strat = strategy or settings.chunk_strategy
        if strat == "spacy":
            return SpaCyChunker()
        elif strat == "nltk":
            return NLTKChunker()
        elif strat == "regex":
            return RegexChunker()
        else:
            raise ValueError(f"Unknown chunking strategy '{strat}'")


def verify_nlp_resources(strategy: str, model_name: str) -> None:
    """
    On startup or invocation, verify that required spaCy/NLTK resources exist.
    Fails fast with a clear startup error, preventing dynamic downloads.
    """
    if strategy == "spacy":
        import spacy
        try:
            spacy.load(model_name)
        except Exception as exc:
            raise RuntimeError(
                f"Missing required spaCy model '{model_name}'. "
                f"Please ensure it is installed (e.g. run 'python -m spacy download {model_name}') "
                f"before running the application: {exc}"
            ) from exc

    if strategy in ("spacy", "nltk"):
        import nltk
        try:
            # Look for punkt tokenizer
            nltk.data.find("tokenizers/punkt")
        except LookupError as exc:
            try:
                nltk.data.find("tokenizers/punkt_tab")
            except LookupError:
                raise RuntimeError(
                    "Missing required NLTK resource 'punkt'. "
                    "Please ensure NLTK resources are pre-downloaded "
                    "(e.g. run 'python -m nltk.downloader punkt') "
                    "before running the application."
                ) from exc

