"""
Chunk Deduplicator.

Computes text hashes for deterministic deduplication, and performs Jaccard
token similarity checks to capture near-duplicate chunk contents.
"""

from __future__ import annotations

import hashlib
from app.core.config import settings


class ChunkDeduplicator:
    """
    Deduplication helper.

    Tracks SHA-256 hashes for exact duplicate matching and Jaccard token
    similarity for near-duplicate checking.
    """

    def __init__(self, similarity_threshold: float | None = None) -> None:
        self._threshold = (
            similarity_threshold or settings.near_duplicate_similarity_threshold
        )

    @staticmethod
    def calculate_hash(text: str) -> str:
        """Compute SHA-256 checksum of cleaned chunk text."""
        normalized = " ".join(text.strip().lower().split())
        return hashlib.sha256(normalized.encode("utf-8")).hexdigest()

    def calculate_jaccard_similarity(self, text_a: str, text_b: str) -> float:
        """
        Compute token-level Jaccard similarity coefficient between two strings.

        Ranges from 0.0 (entirely disjoint) to 1.0 (identical tokens).
        """
        # Tokenize by alphanumeric words
        words_a = set(re.findall(r"\w+", text_a.lower()))
        words_b = set(re.findall(r"\w+", text_b.lower()))

        if not words_a and not words_b:
            return 1.0
        if not words_a or not words_b:
            return 0.0

        intersection = len(words_a.intersection(words_b))
        union = len(words_a.union(words_b))

        return intersection / union

    def is_near_duplicate(self, text_a: str, text_b: str) -> bool:
        """Return True if Jaccard similarity exceeds the threshold."""
        similarity = self.calculate_jaccard_similarity(text_a, text_b)
        return similarity >= self._threshold


# Compile regex for Jaccard tokenizer locally inside the class
import re
