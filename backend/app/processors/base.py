"""
Parser abstraction layer.

All document parsers implement ``BaseParser`` and return a ``ParseResult``
dataclass.  The ``DocumentProcessingService`` receives a ``BaseParser``
instance from ``ParserFactory`` and never interacts with a concrete class
directly — enabling future parser additions without any service changes.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class ParseResult:
    """
    Structured output of a single parsing operation.

    :param raw_text:   Full unprocessed text extracted from the document.
    :param page_count: Number of pages / slides in the source document.
    :param parser_name: Human-readable identifier of the parser that produced this result.
    :param metadata:   Document-level properties (author, title, dates, etc.).
    :param is_scanned: ``True`` when a PDF consists entirely of image-based pages
                       and no selectable text could be extracted.
    """

    raw_text: str
    page_count: int
    parser_name: str
    metadata: dict = field(default_factory=dict)
    is_scanned: bool = False


class BaseParser(ABC):
    """
    Abstract base class for all document parsers.

    Each concrete parser targets a specific MIME type / file format.
    All I/O operations MUST be synchronous (the service layer wraps calls
    in ``asyncio.to_thread`` to avoid blocking the event loop).
    """

    @abstractmethod
    def parse(self, file_bytes: bytes, filename: str) -> ParseResult:
        """
        Extract text and metadata from *file_bytes*.

        :param file_bytes: Raw binary content of the document.
        :param filename:   Original filename (used for format hints and metadata).
        :returns:          A ``ParseResult`` containing raw text and metadata.
        :raises:           Any exception on unrecoverable parse failure — the
                           service layer will catch and record it.
        """

    @property
    @abstractmethod
    def supported_mime_types(self) -> frozenset[str]:
        """Return the set of MIME types this parser handles."""

    def _safe_datetime(self, value: object) -> datetime | None:
        """
        Coerce a parser-returned date value to a ``datetime`` or ``None``.

        Different libraries return dates as strings, date objects, or
        datetimes — this helper normalises all three.
        """
        if value is None:
            return None
        if isinstance(value, datetime):
            return value
        from datetime import date

        if isinstance(value, date):
            return datetime(value.year, value.month, value.day)
        if isinstance(value, str):
            for fmt in ("%Y-%m-%dT%H:%M:%S", "%Y-%m-%d", "%Y%m%d"):
                try:
                    return datetime.strptime(value, fmt)
                except ValueError:
                    continue
        return None
