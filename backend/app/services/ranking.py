"""
Ranking service for similarity scoring, normalization, deduplication, and thresholding.
"""

from uuid import UUID
from pydantic import BaseModel
from app.models.chunk import ChunkMapping


class RetrievalCandidate(BaseModel):
    """
    Structure representing a candidate chunk matched during retrieval.
    """

    chunk_id: UUID
    text: str
    score: float  # Normalized Cosine similarity score
    mapping: ChunkMapping

    model_config = {"arbitrary_types_allowed": True}


class RankingService:
    """
    Service responsible for converting search distances, sorting, thresholding, and deduplication.
    """

    @staticmethod
    def l2_to_cosine(l2_distance: float) -> float:
        """
        Convert Euclidean (L2) distance of normalized embeddings to Cosine Similarity.
        FAISS flat L2 search returns squared Euclidean distance directly, so:
        CosineSim = 1.0 - l2_distance / 2.0
        """
        cosine_sim = 1.0 - (l2_distance / 2.0)
        # Clamp to [-1.0, 1.0]
        return max(-1.0, min(1.0, cosine_sim))

    @staticmethod
    def normalize_score(score: float) -> float:
        """
        Normalize Cosine Similarity score from [-1.0, 1.0] range to [0.0, 1.0] range.
        Negative similarities are clamped to 0.0.
        """
        return max(0.0, score)

    def rank_candidates(
        self,
        raw_results: list[tuple[ChunkMapping, float]],
        relevance_threshold: float = 0.5,
    ) -> list[RetrievalCandidate]:
        """
        Rank raw vector search results:
        1. Convert L2 distance to Cosine Similarity.
        2. Normalize scores to [0.0, 1.0].
        3. Filter by relevance threshold.
        4. Sort candidates (highest score first).
        5. Deduplicate identical chunks, keeping the one with the highest score.
        """
        candidates = []

        # 1. Convert, normalize and wrap as candidates
        for mapping, l2_dist in raw_results:
            cosine_sim = self.l2_to_cosine(l2_dist)
            normalized_score = self.normalize_score(cosine_sim)

            # Apply relevance threshold
            if normalized_score >= relevance_threshold:
                candidates.append(
                    RetrievalCandidate(
                        chunk_id=mapping.chunk_id,
                        text=mapping.chunk.cleaned_text,
                        score=round(normalized_score, 4),
                        mapping=mapping,
                    )
                )

        # 2. Sort by score descending
        candidates.sort(key=lambda x: x.score, reverse=True)

        # 3. Deduplicate by chunk_id, preserving order (highest score is kept)
        seen_chunks = set()
        deduplicated = []
        for candidate in candidates:
            if candidate.chunk_id not in seen_chunks:
                seen_chunks.add(candidate.chunk_id)
                deduplicated.append(candidate)

        return deduplicated
