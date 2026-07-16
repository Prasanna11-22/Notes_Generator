"""
Phase 6 — Enterprise Embedding Generation & Knowledge Store Tests.
"""

from __future__ import annotations

import os
import json
import uuid
import pytest
import pytest_asyncio
from unittest.mock import MagicMock, patch
import numpy as np
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.config import settings
from app.ai.providers import get_embedding_provider, get_vector_store_provider
from app.ai.providers.embedding.bge import BGEEmbeddingProvider
from app.ai.providers.vector_store.faiss import FAISSProvider
from app.models.chunk import Chunk, ChunkMapping
from app.models.embedding import ChunkEmbedding, DocumentEmbeddingJob
from app.models.resource import Resource
from app.models.curriculum import Department, Program, Semester, Course
from app.services.embedding import EmbeddingService, validate_chunk_text, validate_vector
from app.services.synchronization import EmbeddingSynchronizationService

# Mock for SentenceTransformer to allow offline and fast test runs
class DummySentenceTransformer:
    def __init__(self, model_name=None):
        self.model_name = model_name

    def encode(self, texts, normalize_embeddings=True):
        # Mock BGE dimension: 384
        count = len(texts)
        arr = np.zeros((count, 384), dtype=np.float32)
        # Add some variation to differentiate vectors if needed
        for i in range(count):
            arr[i, 0] = 0.5 + (i * 0.1)
        return arr


@pytest.fixture(autouse=True)
def mock_sentence_transformer():
    """Patch SentenceTransformer to avoid internet downloads and run fast."""
    with patch("app.ai.providers.embedding.bge.SentenceTransformer", return_value=DummySentenceTransformer()):
        yield


@pytest.fixture(autouse=True)
def reset_providers():
    """Reset cached singleton providers to prevent test pollution."""
    import app.ai.providers
    app.ai.providers._embedding_provider = None
    app.ai.providers._vector_store_provider = None
    yield
    app.ai.providers._embedding_provider = None
    app.ai.providers._vector_store_provider = None


@pytest.fixture
def temp_faiss_paths(tmp_path):
    """Provide paths for FAISS index and mappings."""
    idx_path = tmp_path / "test_faiss_index.bin"
    return str(idx_path)


# ═══════════════════════════════════════════════════════════════════════════════
# 1. Embedding Provider & Vector Store Provider Unit Tests
# ═══════════════════════════════════════════════════════════════════════════════

class TestEmbeddingProvider:
    def test_bge_provider_lifecycle_and_methods(self):
        provider = BGEEmbeddingProvider(
            model_name="BAAI/bge-small-en-v1.5",
            dimension=384
        )
        assert provider.model_name() == "BAAI/bge-small-en-v1.5"
        assert provider.embedding_dimension() == 384
        assert provider.health_check() is True

        # Generate single
        vector = provider.generate_embedding("hello")
        assert len(vector) == 384
        assert abs(vector[0] - 0.5) < 1e-5

        # Generate batch
        vectors = provider.generate_batch_embeddings(["hello", "world"])
        assert len(vectors) == 2
        assert len(vectors[0]) == 384
        assert len(vectors[1]) == 384

    def test_bge_provider_validation_rejects(self):
        provider = BGEEmbeddingProvider(
            model_name="BAAI/bge-small-en-v1.5",
            dimension=384
        )
        with pytest.raises(ValueError):
            provider.generate_embedding("")

        with pytest.raises(ValueError):
            provider.generate_embedding("   ")

        with pytest.raises(ValueError):
            provider.generate_batch_embeddings(["hello", ""])


class TestFAISSProvider:
    def test_faiss_provider_crud(self, temp_faiss_paths):
        # 1. Initialization
        provider = FAISSProvider(index_path=temp_faiss_paths, dimension=4)
        assert provider.health_check() is True
        assert provider.exists("vec_1") is False

        # 2. Insert
        provider.insert("vec_1", [0.1, 0.2, 0.3, 0.4])
        assert provider.exists("vec_1") is True
        assert provider.index.ntotal == 1

        # 3. Update
        provider.update("vec_1", [0.5, 0.6, 0.7, 0.8])
        assert provider.index.ntotal == 1

        # 4. Search
        results = provider.search_by_chunk([0.5, 0.6, 0.7, 0.8], limit=1)
        assert len(results) == 1
        assert results[0][0] == "vec_1"
        assert results[0][1] < 1e-4  # L2 distance close to 0

        # 5. Delete
        provider.delete("vec_1")
        assert provider.exists("vec_1") is False
        assert provider.index.ntotal == 0

    def test_faiss_provider_rebuild_and_persistence(self, temp_faiss_paths):
        provider = FAISSProvider(index_path=temp_faiss_paths, dimension=4)
        vectors_dict = {
            "u1": [0.1, 0.1, 0.1, 0.1],
            "u2": [0.2, 0.2, 0.2, 0.2],
        }
        provider.rebuild(vectors_dict)
        assert provider.index.ntotal == 2
        assert provider.exists("u1") is True
        assert provider.exists("u2") is True

        # Reload from disk
        provider_reloaded = FAISSProvider(index_path=temp_faiss_paths, dimension=4)
        assert provider_reloaded.index.ntotal == 2
        assert provider_reloaded.exists("u1") is True
        assert provider_reloaded.exists("u2") is True


# ═══════════════════════════════════════════════════════════════════════════════
# 2. Services Unit & Integration Tests
# ═══════════════════════════════════════════════════════════════════════════════

class TestValidationHelpers:
    def test_validate_chunk_text_rejects(self):
        with pytest.raises(ValueError, match="empty"):
            validate_chunk_text("", 10)
        with pytest.raises(ValueError, match="whitespace"):
            validate_chunk_text("   ", 10)
        with pytest.raises(ValueError, match="oversized"):
            validate_chunk_text("abcdefghijkl", 10)

    def test_validate_vector_rejects(self):
        with pytest.raises(ValueError, match="dimension"):
            validate_vector([0.1, 0.2], 3)
        with pytest.raises(ValueError, match="NaN"):
            validate_vector([0.1, float("nan"), 0.3], 3)
        with pytest.raises(ValueError, match="Infinity"):
            validate_vector([0.1, float("inf"), 0.3], 3)


@pytest_asyncio.fixture
async def sample_curriculum_data(db_session: AsyncSession):
    """Seed base curriculum, course, resource, and chunk mappings."""
    # 1. Base Department/Program
    dept = Department(id=uuid.uuid4(), name="Computer Science", code="CS")
    db_session.add(dept)
    await db_session.flush()

    prog = Program(id=uuid.uuid4(), department_id=dept.id, name="B.Tech CS", duration_years=4)
    db_session.add(prog)
    await db_session.flush()

    sem = Semester(id=uuid.uuid4(), program_id=prog.id, number=1)
    db_session.add(sem)
    await db_session.flush()

    course = Course(
        id=uuid.uuid4(),
        semester_id=sem.id,
        course_code="CS101",
        course_title="Intro to AI",
        credits=4,
    )
    db_session.add(course)
    await db_session.flush()

    # 2. Resource
    resource = Resource(
        id=uuid.uuid4(),
        course_id=course.id,
        title="AI Lecture Note 1",
        file_name="ai_note.pdf",
        original_file_name="ai_note.pdf",
        file_size=1024,
        mime_type="application/pdf",
        storage_path="uploads/ai_note.pdf",
        checksum="dummy_checksum_1",
        upload_status="completed",
        is_active=True,
    )
    db_session.add(resource)
    await db_session.flush()

    # 3. Chunks
    c1 = Chunk(
        id=uuid.uuid4(),
        chunk_hash="hash_c1",
        cleaned_text="Artificial intelligence is the intelligence of machines.",
        raw_text="Artificial intelligence is the intelligence of machines.",
        char_count=55,
        word_count=8,
        estimated_reading_time=1.0,
    )
    c2 = Chunk(
        id=uuid.uuid4(),
        chunk_hash="hash_c2",
        cleaned_text="Machine learning is a subset of artificial intelligence.",
        raw_text="Machine learning is a subset of artificial intelligence.",
        char_count=55,
        word_count=8,
        estimated_reading_time=1.0,
    )
    db_session.add_all([c1, c2])
    await db_session.flush()

    # 4. Chunk Mappings
    m1 = ChunkMapping(
        id=uuid.uuid4(),
        chunk_id=c1.id,
        resource_id=resource.id,
        course_id=course.id,
        chunk_index=0,
        page_numbers="1",
    )
    m2 = ChunkMapping(
        id=uuid.uuid4(),
        chunk_id=c2.id,
        resource_id=resource.id,
        course_id=course.id,
        chunk_index=1,
        page_numbers="1",
    )
    db_session.add_all([m1, m2])
    await db_session.flush()

    return {
        "resource_id": resource.id,
        "chunks": [c1, c2],
        "mappings": [m1, m2],
    }


class TestEmbeddingServiceAndSync:
    @pytest.mark.asyncio
    async def test_generate_embeddings_flow(
        self, db_session: AsyncSession, sample_curriculum_data, temp_faiss_paths
    ):
        # Override faiss path to clean temp path
        with patch.object(settings, "faiss_index_path", temp_faiss_paths):
            res_id = sample_curriculum_data["resource_id"]
            service = EmbeddingService(db_session)

            # Initiate
            job = await service.generate_embeddings_for_document(res_id)
            assert job.status == "pending"

            # Execute
            await service.execute_embedding_job(job.id)

            # Refresh job and verify completion
            await db_session.refresh(job)
            assert job.status == "completed"
            assert job.embeddings_count == 2

            # Check database metadata records
            for chunk in sample_curriculum_data["chunks"]:
                emb = await service._embedding_repo.get_by_chunk_id(chunk.id)
                assert emb is not None
                assert emb.status == "completed"
                assert emb.dimension == 384
                assert emb.processing_time is not None
                assert service._vector_store_provider.exists(emb.vector_store_id) is True

    @pytest.mark.asyncio
    async def test_synchronization_and_reconciliation(
        self, db_session: AsyncSession, sample_curriculum_data, temp_faiss_paths
    ):
        with patch.object(settings, "faiss_index_path", temp_faiss_paths):
            res_id = sample_curriculum_data["resource_id"]
            service = EmbeddingService(db_session)

            # Generate embeddings
            job = await service.generate_embeddings_for_document(res_id)
            await service.execute_embedding_job(job.id)

            sync_service = EmbeddingSynchronizationService(db_session)

            # Get sync report - initially synchronized
            report = await sync_service.get_synchronization_report()
            assert report["is_synchronized"] is True
            assert report["missing_vectors_count"] == 0
            assert report["missing_metadata_count"] == 0

            # Simulate inconsistency: Delete 1 vector from store
            all_embs = await service._embedding_repo.get_all()
            target_emb = all_embs[0]
            service._vector_store_provider.delete(target_emb.vector_store_id)

            # Report should detect discrepancy
            report = await sync_service.get_synchronization_report()
            assert report["is_synchronized"] is False
            assert report["missing_vectors_count"] == 1

            # Run reconcile
            reconcile_res = await sync_service.reconcile()
            assert reconcile_res["repaired_vectors_count"] == 1

            # Report should be healthy again
            report = await sync_service.get_synchronization_report()
            assert report["is_synchronized"] is True

            # Full index rebuild
            await sync_service.rebuild_index()
            report = await sync_service.get_synchronization_report()
            assert report["is_synchronized"] is True
            assert report["total_embeddings_in_db"] == report["total_chunks_in_db"]


# ═══════════════════════════════════════════════════════════════════════════════
# 3. API Integrations Tests
# ═══════════════════════════════════════════════════════════════════════════════

class TestEmbeddingAPI:
    @pytest.mark.asyncio
    async def test_api_generate_and_status(
        self, client: AsyncClient, auth_headers, sample_curriculum_data, temp_faiss_paths
    ):
        with patch.object(settings, "faiss_index_path", temp_faiss_paths):
            res_id = str(sample_curriculum_data["resource_id"])

            # 1. POST /embeddings/generate
            response = await client.post(
                "/api/v1/embeddings/generate",
                json={"resource_id": res_id},
                headers=auth_headers,
            )
            assert response.status_code == 202
            data = response.json()["data"]
            assert data["status"] == "pending"
            job_id = data["id"]

            # 2. GET /embeddings/status/{id}
            response = await client.get(
                f"/api/v1/embeddings/status/{job_id}",
                headers=auth_headers,
            )
            assert response.status_code == 200
            assert response.json()["data"]["status"] in ["pending", "processing", "completed"]

    @pytest.mark.asyncio
    async def test_vector_store_health_and_rebuild(
        self, client: AsyncClient, auth_headers, temp_faiss_paths
    ):
        with patch.object(settings, "faiss_index_path", temp_faiss_paths):
            # GET /vector-store/health
            response = await client.get(
                "/api/v1/vector-store/health",
                headers=auth_headers,
            )
            assert response.status_code == 200
            assert response.json()["data"]["status"] == "healthy"

            # POST /vector-store/rebuild
            response = await client.post(
                "/api/v1/vector-store/rebuild",
                headers=auth_headers,
            )
            assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_synchronization_endpoints(
        self, client: AsyncClient, auth_headers, temp_faiss_paths
    ):
        with patch.object(settings, "faiss_index_path", temp_faiss_paths):
            # GET /synchronization/report
            response = await client.get(
                "/api/v1/synchronization/report",
                headers=auth_headers,
            )
            assert response.status_code == 200
            assert "is_synchronized" in response.json()["data"]

            # POST /synchronization/reconcile
            response = await client.post(
                "/api/v1/synchronization/reconcile",
                headers=auth_headers,
            )
            assert response.status_code == 200
            assert response.json()["data"]["status"] == "reconciled"
