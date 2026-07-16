"""
Chunking engine base classes.

Defines the ``BaseChunker`` interface and ``RawChunk`` dataclass, which acts
as the internal representation of an extracted text chunk prior to database
persistance and metadata enrichment.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field


@dataclass
class RawChunk:
    """
    Intermediate chunk payload parsed out of a document.

    :param cleaned_text:    Cleaned segment text.
    :param raw_text:        Unmodified segment text.
    :param page_numbers:    String of page(s) this text originated from (e.g. "2" or "3-4").
    :param chapter_name:    Identified chapter header.
    :param section_heading: Parent structural header.
    :param subheading:      Child subheading.
    """

    cleaned_text: str
    raw_text: str
    page_numbers: str
    chapter_name: str | None = None
    section_heading: str | None = None
    subheading: str | None = None


class BaseChunker(ABC):
    """
    Abstract base class for all text chunking engines.

    Allows plugging in spaCy, NLTK, or Regex-based splitting strategies.
    All implementations MUST run synchronously (the service layer offloads
    execution to thread pools).
    """

    @abstractmethod
    def split_text(
        self,
        cleaned_text: str,
        raw_text: str,
        *,
        chunk_size: int = 1000,
        chunk_overlap: int = 200,
    ) -> list[RawChunk]:
        """
        Segment a document's full text into structured ``RawChunk`` parts.

        :param cleaned_text:  Cleaned text representation of the document.
        :param raw_text:      Uncleaned text representation of the document.
        :param chunk_size:    Target length of each chunk in characters.
        :param chunk_overlap: Overlapping characters to carry over between chunks.
        :returns:             List of parsed ``RawChunk`` segments.
        """
