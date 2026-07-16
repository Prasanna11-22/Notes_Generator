"""
Retriever orchestration service.
"""

import asyncio
import time
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.providers import get_retriever_provider
from app.ai.providers.retriever.base import RetrieverProvider
from app.core.config import settings
from app.repositories.retriever import RetrieverRepository
from app.services.filtering import MetadataFilter
from app.services.ranking import RankingService, RetrievalCandidate
from app.services.assembler import ContextAssembler


def validate_query(query: str, max_length: int = 2000) -> str:
    """
    Validate query text to reject empty, whitespace, invalid Unicode, or oversized queries.
    Strips null bytes to ensure SQL/DB security.
    """
    # Sanitize null bytes
    query = query.replace("\x00", "")

    if not query:
        raise ValueError("Query cannot be empty.")
    if not query.strip():
        raise ValueError("Query cannot be whitespace-only.")
    try:
        query.encode("utf-8").decode("utf-8")
    except UnicodeError as e:
        raise ValueError(f"Query contains invalid Unicode characters: {str(e)}")

    if len(query) > max_length:
        raise ValueError(
            f"Query exceeds maximum character limit: got {len(query)}, max allowed {max_length}"
        )
    return query


class RetrieverService:
    """
    Main orchestrator coordinating query encoding, FAISS lookup, filtering, ranking, and assembly.
    """

    def __init__(
        self,
        session: AsyncSession,
        retriever_provider: RetrieverProvider | None = None,
        filter_service: MetadataFilter | None = None,
        ranking_service: RankingService | None = None,
        assembler_service: ContextAssembler | None = None,
    ) -> None:
        self._session = session
        self._retriever_repo = RetrieverRepository(session)
        self._retriever_provider = retriever_provider or get_retriever_provider()
        self._filter_service = filter_service or MetadataFilter()
        self._ranking_service = ranking_service or RankingService()
        self._assembler_service = assembler_service or ContextAssembler()

    async def retrieve_context(
        self,
        query: str,
        limit: int | None = None,
        filters: dict | None = None,
        relevance_threshold: float | None = None,
    ) -> dict:
        """
        Orchestrate context retrieval pipeline:
        1. Validate query query text.
        2. Encode and search FAISS in background thread.
        3. Retrieve eager DB records.
        4. Apply metadata filtering.
        5. Convert scoring, threshold, deduplicate.
        6. Assemble final context package.
        """
        start_time = time.perf_counter()
        limit = limit or settings.default_retrieval_limit
        relevance_threshold = relevance_threshold if relevance_threshold is not None else settings.default_relevance_threshold

        # 1. Validation
        query = validate_query(query)

        # 2. Vector search via provider (offloaded to thread executor)
        logger.info("Executing retrieval for query: '{}' (limit: {})", query, limit)
        # Fetch extra results to allow post-search metadata filtering
        search_limit = limit * 4 if filters else limit
        search_results = await asyncio.to_thread(
            self._retriever_provider.retrieve, query, search_limit
        )

        if not search_results:
            raise ValueError("No search results returned from vector database.")

        # 3. Retrieve DB records
        vector_ids = [vs_id for vs_id, _ in search_results]
        embeddings = await self._retriever_repo.get_embeddings_by_vector_ids(vector_ids)
        embedding_map = {emb.vector_store_id: emb for emb in embeddings}

        # Match DB mapping records with search scores, preserving FAISS priority order
        raw_results = []
        for vs_id, dist in search_results:
            emb = embedding_map.get(vs_id)
            if emb and emb.chunk:
                for mapping in emb.chunk.mappings:
                    raw_results.append((mapping, dist))

        if not raw_results:
            raise ValueError("No matching metadata embeddings found in DB.")

        # 4. Metadata Filtering
        filtered_results = self._filter_service.filter_mappings(raw_results, filters)

        # 5. Ranking and deduplication
        ranked_candidates = self._ranking_service.rank_candidates(
            filtered_results, relevance_threshold
        )

        if not ranked_candidates:
            raise ValueError("No search results satisfied the metadata filters and relevance threshold.")

        # Truncate to desired limit
        final_candidates = ranked_candidates[:limit]

        # 6. Context Assembly
        context_package = self._assembler_service.assemble(query, final_candidates)

        duration = time.perf_counter() - start_time
        logger.info(
            "Retrieval complete in {:.4f}s. Retrieved candidates: {}, Provider: {}",
            duration,
            len(final_candidates),
            settings.retriever_provider,
        )

        return context_package
