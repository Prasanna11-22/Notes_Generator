"""
Embedding service for generating, validating, and storing vectors.
"""

import asyncio
from datetime import datetime, timezone
import math
import time
from uuid import UUID, uuid4
from loguru import logger
import numpy as np
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.providers import get_embedding_provider, get_vector_store_provider
from app.core.config import settings
from app.models.embedding import ChunkEmbedding, DocumentEmbeddingJob
from app.repositories.chunk import ChunkMappingRepository
from app.repositories.embedding import ChunkEmbedding, DocumentEmbeddingJobRepository, EmbeddingRepository


def validate_chunk_text(text: str, max_length: int) -> None:
    """
    Validate chunk text to reject empty, whitespace-only, invalid Unicode, or oversized text.
    """
    if not text:
        raise ValueError("Rejecting empty text chunk.")
    if not text.strip():
        raise ValueError("Rejecting whitespace-only text chunk.")
    try:
        text.encode("utf-8").decode("utf-8")
    except UnicodeError as e:
        raise ValueError(f"Rejecting invalid Unicode characters in chunk: {str(e)}")
    if len(text) > max_length:
        raise ValueError(
            f"Rejecting oversized chunk of size {len(text)} (max limit: {max_length})"
        )


def validate_vector(vector: list[float], expected_dim: int) -> None:
    """
    Validate that a generated embedding vector is float32 only, has no NaN/Infinity, and is correct dimension.
    """
    if len(vector) != expected_dim:
        raise ValueError(
            f"Invalid vector dimension: got {len(vector)}, expected {expected_dim}"
        )

    # Convert to numpy array for fast checks
    vec_np = np.array(vector, dtype=np.float32)

    if np.isnan(vec_np).any():
        raise ValueError("Vector contains NaN values.")
    if np.isinf(vec_np).any():
        raise ValueError("Vector contains Infinity values.")


class EmbeddingService:
    """
    Service class managing the embedding generation pipeline.
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._embedding_repo = EmbeddingRepository(session)
        self._job_repo = DocumentEmbeddingJobRepository(session)
        self._mapping_repo = ChunkMappingRepository(session)
        self._embedding_provider = get_embedding_provider()
        self._vector_store_provider = get_vector_store_provider()

    async def get_job(self, job_id: UUID) -> DocumentEmbeddingJob | None:
        """Fetch an embedding job by its ID."""
        return await self._job_repo.get_by_id(job_id)

    async def get_job_by_resource(self, resource_id: UUID) -> DocumentEmbeddingJob | None:
        """Fetch an embedding job by its resource ID."""
        return await self._job_repo.get_by_resource_id(resource_id)

    async def delete_embeddings_for_resource(self, resource_id: UUID) -> None:
        """
        Delete all embeddings metadata and vectors associated with a resource.
        """
        logger.info("Deleting all embeddings for resource: {}", resource_id)
        # Find all mappings
        mappings = await self._mapping_repo.list_by_resource(resource_id, limit=10000)
        for mapping in mappings:
            emb = await self._embedding_repo.get_by_chunk_id(mapping.chunk_id)
            if emb:
                # Delete vector from Vector Store
                await asyncio.to_thread(self._vector_store_provider.delete, emb.vector_store_id)
                # Delete metadata from DB
                await self._embedding_repo.delete(emb)
        await self._session.flush()

    async def generate_embeddings_for_document(
        self, resource_id: UUID, force: bool = False
    ) -> DocumentEmbeddingJob:
        """
        Orchestrate generating embeddings for all unique chunks of a resource.
        Saves metadata in DB and inserts vectors into the vector store.
        """
        # Create or fetch tracking job
        job = await self._job_repo.get_by_resource_id(resource_id)
        if not job:
            job = DocumentEmbeddingJob(
                id=uuid4(),
                resource_id=resource_id,
                status="pending",
            )
            await self._job_repo.create(job)
        else:
            job.status = "pending"
            job.error_message = None
            job.started_at = None
            job.completed_at = None
            job.embeddings_count = None
            await self._session.flush()

        return job

    async def execute_embedding_job(self, job_id: UUID, force: bool = False) -> None:
        """
        Run the embedding generation job. Called from a background task.
        """
        job = await self._job_repo.get_by_id(job_id)
        if not job:
            logger.error("Embedding job not found: {}", job_id)
            return

        logger.info("Executing embedding generation for resource: {}", job.resource_id)
        job.status = "processing"
        job.started_at = datetime.now(timezone.utc)
        await self._session.flush()

        try:
            # 1. Fetch chunks for the resource
            mappings = await self._mapping_repo.list_by_resource(job.resource_id, limit=10000)
            if not mappings:
                raise ValueError("No text chunks found for the given resource. Chunking must run first.")

            # Identify unique chunks to process
            unique_chunks = {}
            for m in mappings:
                if m.chunk_id not in unique_chunks:
                    unique_chunks[m.chunk_id] = m.chunk

            logger.info(
                "Found {} total mapping(s) and {} unique chunk(s) to evaluate.",
                len(mappings),
                len(unique_chunks),
            )

            # Determine which chunks actually need embedding
            chunks_to_embed = []
            for chunk_id, chunk in unique_chunks.items():
                existing = await self._embedding_repo.get_by_chunk_id(chunk_id)
                # If forced, or embedding doesn't exist/is failed, or vector is missing in store
                vector_in_store = (
                    await asyncio.to_thread(self._vector_store_provider.exists, existing.vector_store_id)
                    if existing else False
                )

                if force or not existing or existing.status != "completed" or not vector_in_store:
                    # Validate text contents first
                    validate_chunk_text(chunk.cleaned_text, settings.max_chunk_char_length)
                    chunks_to_embed.append(chunk)
                    if existing:
                        # Clean up failed/stale DB entry and vector store entry
                        await asyncio.to_thread(self._vector_store_provider.delete, existing.vector_store_id)
                        await self._embedding_repo.delete(existing)
                else:
                    logger.debug("Embedding already exists and is healthy for chunk: {}", chunk_id)

            # 2. Batch process embeddings for chunks needing it
            processed_count = 0
            if chunks_to_embed:
                batch_size = settings.batch_size
                dim = self._embedding_provider.embedding_dimension()

                # Batch text generation
                for i in range(0, len(chunks_to_embed), batch_size):
                    batch = chunks_to_embed[i : i + batch_size]
                    texts = [c.cleaned_text for c in batch]

                    start_time = time.perf_counter()
                    vectors = await asyncio.to_thread(self._embedding_provider.generate_batch_embeddings, texts)
                    generation_duration = time.perf_counter() - start_time

                    per_chunk_time = generation_duration / len(batch)

                    for idx, chunk in enumerate(batch):
                        vector = vectors[idx]
                        validate_vector(vector, dim)

                        # Create metadata record
                        emb_id = uuid4()
                        emb = ChunkEmbedding(
                            id=emb_id,
                            chunk_id=chunk.id,
                            model_name=self._embedding_provider.model_name(),
                            model_version="1.5",  # BGE model version prefix
                            dimension=dim,
                            vector_store_id=str(emb_id),
                            status="completed",
                            processing_time=per_chunk_time,
                        )

                        # Write vector to store
                        await asyncio.to_thread(self._vector_store_provider.insert, str(emb_id), vector)
                        # Save metadata
                        await self._embedding_repo.create(emb)
                        processed_count += 1

                await self._session.flush()

            # Count total completed embeddings for this resource
            total_active_embeddings = 0
            for chunk_id in unique_chunks.keys():
                emb = await self._embedding_repo.get_by_chunk_id(chunk_id)
                if emb and emb.status == "completed":
                    total_active_embeddings += 1

            # 3. Mark completed
            job.status = "completed"
            job.embeddings_count = total_active_embeddings
            job.completed_at = datetime.now(timezone.utc)
            await self._session.flush()
            logger.info(
                "Embedding generation job completed successfully for resource: {}. Generated: {}, Total active: {}",
                job.resource_id,
                processed_count,
                total_active_embeddings,
            )

        except Exception as e:
            logger.exception("Error executing embedding generation job {}", job_id)
            job.status = "failed"
            job.error_message = str(e)
            job.completed_at = datetime.now(timezone.utc)
            await self._session.flush()
