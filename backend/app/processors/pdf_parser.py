"""
PDF Parser.

Uses PyMuPDF (``fitz``) as the primary extraction engine with ``pdfplumber``
as a fallback for PDFs that PyMuPDF cannot handle cleanly.

Scanned PDF Detection
---------------------
For each page the parser measures the ratio of extractable text characters
to total page area.  If the average across the whole document falls below
the threshold defined in ``settings.pdf_min_chars_per_page``, the PDF is
classified as image-only (scanned) and ``ParseResult.is_scanned`` is set
to ``True``.  No OCR is attempted at this stage — the processing service
will set the job status to ``OCR_REQUIRED``.
"""

from __future__ import annotations

import io

from loguru import logger

from app.core.config import settings
from app.processors.base import BaseParser, ParseResult

_SUPPORTED_MIME_TYPES = frozenset({"application/pdf"})


class PDFParser(BaseParser):
    """
    PDF text extractor with PyMuPDF primary + pdfplumber fallback.

    Both libraries are called synchronously; the service layer is responsible
    for offloading this call to a thread pool.
    """

    @property
    def supported_mime_types(self) -> frozenset[str]:
        return _SUPPORTED_MIME_TYPES

    # ── Public API ────────────────────────────────────────────────────────────

    def parse(self, file_bytes: bytes, filename: str) -> ParseResult:
        """Extract text from a PDF byte stream."""
        logger.debug("PDFParser: parsing '{}' ({} bytes)", filename, len(file_bytes))

        # Try PyMuPDF first (fast, handles most PDFs well)
        try:
            return self._parse_with_pymupdf(file_bytes, filename)
        except Exception as exc:
            logger.warning(
                "PDFParser: PyMuPDF failed for '{}': {} — falling back to pdfplumber",
                filename,
                exc,
            )

        # Fall back to pdfplumber
        try:
            return self._parse_with_pdfplumber(file_bytes, filename)
        except Exception as exc:
            logger.error(
                "PDFParser: pdfplumber also failed for '{}': {}", filename, exc
            )
            raise RuntimeError(
                f"All PDF parsers failed for '{filename}': {exc}"
            ) from exc

    # ── Private helpers ───────────────────────────────────────────────────────

    def _parse_with_pymupdf(self, file_bytes: bytes, filename: str) -> ParseResult:
        """Extract text via PyMuPDF (fitz)."""
        import fitz  # type: ignore[import-untyped]  # pymupdf

        doc = fitz.open(stream=file_bytes, filetype="pdf")
        try:
            pages_text: list[str] = []
            for page in doc:
                pages_text.append(page.get_text("text"))

            raw_text = "\n\n".join(pages_text)
            page_count = len(doc)
            is_scanned = self._detect_scanned(pages_text, page_count)

            metadata = self._extract_pymupdf_metadata(doc)
            metadata["page_count"] = page_count
            metadata["parser_backend"] = "pymupdf"

            return ParseResult(
                raw_text=raw_text,
                page_count=page_count,
                parser_name="PDFParser(pymupdf)",
                metadata=metadata,
                is_scanned=is_scanned,
            )
        finally:
            doc.close()

    def _parse_with_pdfplumber(
        self, file_bytes: bytes, filename: str
    ) -> ParseResult:
        """Extract text via pdfplumber (fallback)."""
        import pdfplumber  # type: ignore[import-untyped]

        with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
            pages_text: list[str] = []
            for page in pdf.pages:
                text = page.extract_text() or ""
                pages_text.append(text)

            raw_text = "\n\n".join(pages_text)
            page_count = len(pdf.pages)
            is_scanned = self._detect_scanned(pages_text, page_count)

            metadata: dict = {
                "page_count": page_count,
                "parser_backend": "pdfplumber",
            }
            if pdf.metadata:
                metadata.update(
                    {
                        k: v
                        for k, v in pdf.metadata.items()
                        if isinstance(v, str | int | float | bool)
                    }
                )

            return ParseResult(
                raw_text=raw_text,
                page_count=page_count,
                parser_name="PDFParser(pdfplumber)",
                metadata=metadata,
                is_scanned=is_scanned,
            )

    def _detect_scanned(
        self, pages_text: list[str], page_count: int
    ) -> bool:
        """
        Return ``True`` when the average characters per page is below the
        configured threshold, indicating an image-only (scanned) PDF.
        """
        if page_count == 0:
            return False
        total_chars = sum(len(t.strip()) for t in pages_text)
        avg_chars = total_chars / page_count
        is_scanned = avg_chars < settings.pdf_min_chars_per_page
        if is_scanned:
            logger.info(
                "PDFParser: scanned PDF detected "
                "(avg {:.1f} chars/page < threshold {})",
                avg_chars,
                settings.pdf_min_chars_per_page,
            )
        return is_scanned

    @staticmethod
    def _extract_pymupdf_metadata(doc: object) -> dict:
        """Pull structured metadata from a PyMuPDF document object."""
        try:
            import fitz  # type: ignore[import-untyped]

            raw: dict = doc.metadata  # type: ignore[attr-defined]
            result: dict = {}
            if raw:
                for key in ("title", "author", "subject", "keywords", "creator", "producer"):
                    if raw.get(key):
                        result[key] = raw[key]
                # PyMuPDF stores dates as "D:YYYYMMDDHHmmSS" strings
                for date_key in ("creationDate", "modDate"):
                    raw_date = raw.get(date_key, "")
                    if raw_date and raw_date.startswith("D:"):
                        result[date_key] = raw_date[2:16]  # keep "YYYYMMDDHHmmSS"
            return result
        except Exception:
            return {}
