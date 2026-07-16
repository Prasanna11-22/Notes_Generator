"""
Parser Factory.

Maps document MIME types to their concrete ``BaseParser`` implementations.
The factory is the single registration point — adding support for a new
format only requires adding an entry here; no service or route changes needed.
"""

from __future__ import annotations

from app.exceptions.custom import ValidationError
from app.processors.base import BaseParser
from app.processors.docx_parser import DOCXParser
from app.processors.pdf_parser import PDFParser
from app.processors.pptx_parser import PPTXParser
from app.processors.txt_parser import TXTParser

# ── Registry: MIME type → parser class ───────────────────────────────────────
_REGISTRY: dict[str, type[BaseParser]] = {
    "application/pdf": PDFParser,
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": DOCXParser,
    "application/vnd.openxmlformats-officedocument.presentationml.presentation": PPTXParser,
    "text/plain": TXTParser,
}


class ParserFactory:
    """
    Factory that instantiates the correct ``BaseParser`` for a given MIME type.

    Usage::

        parser = ParserFactory.get_parser("application/pdf")
        result = parser.parse(file_bytes, "lecture.pdf")
    """

    @staticmethod
    def get_parser(mime_type: str) -> BaseParser:
        """
        Return a fresh parser instance for *mime_type*.

        :param mime_type: The MIME type of the file to be parsed.
        :raises ValidationError: When no parser is registered for *mime_type*.
        """
        parser_class = _REGISTRY.get(mime_type)
        if parser_class is None:
            supported = ", ".join(sorted(_REGISTRY))
            raise ValidationError(
                f"No parser available for MIME type '{mime_type}'. "
                f"Supported types: {supported}."
            )
        return parser_class()

    @staticmethod
    def supported_mime_types() -> frozenset[str]:
        """Return all MIME types for which a parser is registered."""
        return frozenset(_REGISTRY)
