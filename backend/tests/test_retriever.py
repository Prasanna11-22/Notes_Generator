"""
Phase 7 — Enterprise Retriever & Context Engine Tests.
"""

from __future__ import annotations

import os
import json
import uuid
from datetime import datetime, timezone, timedelta
import pytest
import pytest_asyncio
from unittest.mock import MagicMock, patch
import numpy as np
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
import app.ai.providers
from app.ai.providers.retriever.faiss_retriever import FAISSRetrieverProvider
from app.models.chunk import Chunk, ChunkMapping
from app.models.embedding import ChunkEmbedding
from app.models.resource import Resource
from app.models.curriculum import Department, Program, Semester, Course, Unit, Topic
from app.services.ranking import RankingService, RetrievalCandidate
from app.services.filtering import MetadataFilter
from app.services.assembler import ContextAssembler
from app.services.retriever import RetrieverService, validate_query


# ── Mocks & Test Fixtures ─────────────────────────────────────────────────────

class DummySentenceTransformer:
    def __init__(self, model_name=None):
        self.model_name = model_name

    def encode(self, texts, normalize_embeddings=True):
        count = len(texts)
        arr = np.zeros((count, 384), dtype=np.float32)
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
    app.ai.providers._embedding_provider = None
    app.ai.providers._vector_store_provider = None
    app.ai.providers._retriever_provider = None
    yield
    app.ai.providers._embedding_provider = None
    app.ai.providers._vector_store_provider = None
    app.ai.providers._retriever_provider = None


# ── 1. Unit Tests: Providers & Services ───────────────────────────────────────

class TestRetrieverProvider:
    def test_faiss_retriever_provider_retrieve(self):
        mock_embedding = MagicMock()
        mock_embedding.generate_embedding.return_value = [0.1] * 384

        mock_vs = MagicMock()
        mock_vs.search_by_chunk.return_value = [("vec-1", 0.4), ("vec-2", 0.8)]

        provider = FAISSRetrieverProvider(mock_embedding, mock_vs)
        results = provider.retrieve("test query", limit=2)

        assert len(results) == 2
        assert results[0][0] == "vec-1"
        mock_embedding.generate_embedding.assert_called_once_with("test query")
        mock_vs.search_by_chunk.assert_called_once_with(mock_embedding.generate_embedding.return_value, 2)


class TestRankingService:
    def test_l2_to_cosine_conversion(self):
        svc = RankingService()
        # FAISS flat L2 search returns squared Euclidean distance directly
        assert svc.l2_to_cosine(0.0) == 1.0  # Perfect match
        assert svc.l2_to_cosine(4.0) == -1.0 # Max distance (opposite vectors, d^2=4.0)
        assert 0.0 < svc.l2_to_cosine(1.0) < 1.0

    def test_normalize_score(self):
        svc = RankingService()
        assert svc.normalize_score(0.8) == 0.8
        assert svc.normalize_score(-0.3) == 0.0  # Clamped

    def test_rank_candidates_sorting_and_deduplication(self):
        svc = RankingService()

        # Dummy mappings
        m1 = MagicMock(spec=ChunkMapping)
        m1.chunk_id = uuid.uuid4()
        m1.chunk = MagicMock(cleaned_text="Text A")

        m2 = MagicMock(spec=ChunkMapping)
        m2.chunk_id = uuid.uuid4()
        m2.chunk = MagicMock(cleaned_text="Text B")

        # Duplicate of mapping 1 but with worse score
        m3 = MagicMock(spec=ChunkMapping)
        m3.chunk_id = m1.chunk_id
        m3.chunk = MagicMock(cleaned_text="Text A")

        # L2 distances (lower is better, meaning higher Cosine Similarity)
        raw_results = [(m1, 0.4), (m2, 0.2), (m3, 0.8)]

        ranked = svc.rank_candidates(raw_results, relevance_threshold=0.1)

        # Ranked should sort: m2 (L2=0.2, score=0.98), m1 (L2=0.4, score=0.92)
        # m3 is a duplicate of m1 and should be removed since m1 has higher score
        assert len(ranked) == 2
        assert ranked[0].chunk_id == m2.chunk_id
        assert ranked[1].chunk_id == m1.chunk_id


class TestMetadataFilter:
    def test_match_all_filters(self):
        # Mocks
        mapping = MagicMock(spec=ChunkMapping)
        mapping.course_id = uuid.UUID("11111111-1111-1111-1111-111111111111")
        mapping.unit_id = uuid.UUID("22222222-2222-2222-2222-222222222222")
        mapping.topic_id = uuid.UUID("33333333-3333-3333-3333-333333333333")
        mapping.resource_id = uuid.UUID("44444444-4444-4444-4444-444444444444")
        mapping.resource_type = "Textbook"
        mapping.bloom_level = "Apply"
        mapping.knowledge_level = "Procedural"
        mapping.difficulty = "Medium"
        mapping.created_at = datetime(2026, 7, 16, 12, 0, 0, tzinfo=timezone.utc)

        resource = MagicMock(spec=Resource)
        resource.uploaded_by = uuid.UUID("55555555-5555-5555-5555-555555555555")
        mapping.resource = resource

        # Match successfully
        criteria = {
            "course_id": mapping.course_id,
            "unit_id": mapping.unit_id,
            "topic_id": mapping.topic_id,
            "resource_id": mapping.resource_id,
            "uploaded_by": resource.uploaded_by,
            "resource_type": "textbook",
            "bloom_level": "apply",
            "knowledge_level": "procedural",
            "difficulty": "medium",
            "created_after": datetime(2026, 7, 16, 11, 0, 0, tzinfo=timezone.utc),
            "created_before": datetime(2026, 7, 16, 13, 0, 0, tzinfo=timezone.utc),
        }
        assert MetadataFilter.match(mapping, criteria) is True

        # Fails matching on one criterion
        bad_criteria = criteria.copy()
        bad_criteria["bloom_level"] = "Analyze"
        assert MetadataFilter.match(mapping, bad_criteria) is False


class TestContextAssembler:
    def test_assemble_context(self):
        assembler = ContextAssembler()

        resource = MagicMock(spec=Resource)
        resource.title = "Operating Systems Book"

        m = MagicMock(spec=ChunkMapping)
        m.course_id = uuid.uuid4()
        m.resource_id = uuid.uuid4()
        m.resource = resource
        m.page_numbers = "22"
        m.chapter_name = "Chapter 3"
        m.section_heading = "Scheduling"
        m.bloom_level = "Understand"
        m.chunk_title = "CPU Scheduler"
        m.subheading = None
        m.knowledge_level = "Conceptual"
        m.resource_type = "Textbook"

        candidate = RetrievalCandidate(
            chunk_id=uuid.uuid4(),
            text="CPU scheduling is the basis of multi-programmed operating systems.",
            score=0.85,
            mapping=m,
        )

        package = assembler.assemble("scheduling", [candidate])

        assert package["query"] == "scheduling"
        assert len(package["chunks"]) == 1
        assert package["chunks"][0]["resource_title"] == "Operating Systems Book"
        assert "[Source: Operating Systems Book, Page: 22, Chapter: Chapter 3, Section: Scheduling, Bloom Level: Understand]" in package["formatted_context"]
        assert "CPU scheduling is the basis" in package["formatted_context"]


class TestRetrieverValidation:
    def test_validate_query_rejects(self):
        with pytest.raises(ValueError, match="cannot be empty"):
            validate_query("")

        with pytest.raises(ValueError, match="whitespace-only"):
            validate_query("   ")

        with pytest.raises(ValueError, match="exceeds maximum"):
            validate_query("a" * 2005)


# ── 2. Integration & Endpoints Tests ──────────────────────────────────────────

class TestRetrieverIntegration:
    @pytest_asyncio.fixture(autouse=True)
    async def seed_data(self, db_session: AsyncSession):
        """Seed dummy curriculum and resource metadata for integration test."""
        # 1. Create course, unit, topic structure
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
            course_title="Intro to Programming",
            credits=4,
        )
        db_session.add(course)
        await db_session.flush()

        unit = Unit(id=uuid.uuid4(), course_id=course.id, unit_number=1, title="Variables")
        db_session.add(unit)
        await db_session.flush()

        topic = Topic(id=uuid.uuid4(), unit_id=unit.id, topic_name="Datatypes")
        db_session.add(topic)
        await db_session.flush()

        # 2. Create sample resource
        uploader_id = uuid.uuid4() # Mock user id
        res = Resource(
            id=uuid.uuid4(),
            course_id=course.id,
            uploaded_by=uploader_id,
            title="Programming Slides",
            file_name="prog.pdf",
            original_file_name="prog.pdf",
            file_size=2048,
            mime_type="application/pdf",
            storage_path="/tmp/prog.pdf",
            checksum="dummysum123",
        )
        db_session.add(res)
        await db_session.flush()

        # 3. Create Chunks, mappings, and embeddings
        chunk1 = Chunk(
            id=uuid.uuid4(),
            chunk_hash="hash1",
            cleaned_text="Python supports integers and floating point datatypes.",
            raw_text="Python supports integers and floating point datatypes.",
            char_count=50,
            word_count=8,
            estimated_reading_time=0.1,
        )
        chunk2 = Chunk(
            id=uuid.uuid4(),
            chunk_hash="hash2",
            cleaned_text="Variables hold references to values in computer memory.",
            raw_text="Variables hold references to values in computer memory.",
            char_count=55,
            word_count=9,
            estimated_reading_time=0.1,
        )
        db_session.add_all([chunk1, chunk2])
        await db_session.flush()

        map1 = ChunkMapping(
            id=uuid.uuid4(),
            chunk_id=chunk1.id,
            resource_id=res.id,
            course_id=course.id,
            unit_id=unit.id,
            topic_id=topic.id,
            chunk_index=0,
            page_numbers="1",
            bloom_level="Understand",
            knowledge_level="Conceptual",
            resource_type="Textbook",
        )
        map2 = ChunkMapping(
            id=uuid.uuid4(),
            chunk_id=chunk2.id,
            resource_id=res.id,
            course_id=course.id,
            unit_id=unit.id,
            topic_id=topic.id,
            chunk_index=1,
            page_numbers="2",
            bloom_level="Remember",
            knowledge_level="Factual",
            resource_type="Textbook",
        )
        db_session.add_all([map1, map2])
        await db_session.flush()

        # FAISS embedding IDs mapping to Chunk UUID
        emb1 = ChunkEmbedding(
            id=uuid.uuid4(),
            chunk_id=chunk1.id,
            model_name="BAAI/bge-small-en-v1.5",
            model_version="1.5",
            dimension=384,
            vector_store_id=str(chunk1.id),
            status="completed",
        )
        emb2 = ChunkEmbedding(
            id=uuid.uuid4(),
            chunk_id=chunk2.id,
            model_name="BAAI/bge-small-en-v1.5",
            model_version="1.5",
            dimension=384,
            vector_store_id=str(chunk2.id),
            status="completed",
        )
        db_session.add_all([emb1, emb2])
        await db_session.flush()

        self.course_id = course.id
        self.topic_id = topic.id
        self.unit_id = unit.id
        self.resource_id = res.id
        self.chunk1_id = chunk1.id
        self.chunk2_id = chunk2.id

    @pytest.mark.asyncio
    async def test_full_retrieval_flow(self, db_session: AsyncSession):
        # 1. Setup in-memory FAISS store containing our two vector IDs
        vs_provider = app.ai.providers.get_vector_store_provider()
        vs_provider.create_index()
        # Seed exact matches into mock FAISS index
        vs_provider.insert(str(self.chunk1_id), [0.0] * 384)
        vs_provider.insert(str(self.chunk2_id), [0.0] * 384)

        service = RetrieverService(db_session)

        # 2. Test general retrieval without filters
        context = await service.retrieve_context(query="Python datatypes", limit=5, relevance_threshold=0.1)
        assert context["query"] == "Python datatypes"
        assert len(context["chunks"]) == 2

        # 3. Test retrieval with specific metadata filters
        filtered_context = await service.retrieve_context(
            query="Python datatypes",
            limit=5,
            filters={"bloom_level": "Understand"},
            relevance_threshold=0.1,
        )
        # Only chunk1 should match Bloom level 'Understand'
        assert len(filtered_context["chunks"]) == 1
        assert filtered_context["chunks"][0]["chunk_id"] == self.chunk1_id

        # 4. Test retrieval with threshold filtering out everything
        with pytest.raises(ValueError, match="relevance threshold"):
            await service.retrieve_context(
                query="Python datatypes",
                limit=5,
                relevance_threshold=1.0, # Impossible threshold in mocked test environment
            )

    @pytest.mark.asyncio
    async def test_api_endpoints(self, client: AsyncClient, auth_headers: dict):
        # Setup FAISS database vectors
        vs_provider = app.ai.providers.get_vector_store_provider()
        vs_provider.create_index()
        vs_provider.insert(str(self.chunk1_id), [0.0] * 384)
        vs_provider.insert(str(self.chunk2_id), [0.0] * 384)

        # 1. POST /retrieve
        res = await client.post(
            "/api/v1/retrieve",
            headers=auth_headers,
            json={"query": "Variables and datatypes", "limit": 2, "relevance_threshold": 0.0},
        )
        assert res.status_code == 200
        payload = res.json()
        assert payload["success"] is True
        assert len(payload["data"]) == 2

        # 2. POST /retrieve/top-k
        res = await client.post(
            "/api/v1/retrieve/top-k",
            headers=auth_headers,
            json={"query": "Variables and datatypes", "k": 1},
        )
        assert res.status_code == 200
        payload = res.json()
        assert len(payload["data"]) == 1

        # 3. POST /retrieve/course
        res = await client.post(
            "/api/v1/retrieve/course",
            headers=auth_headers,
            json={"query": "Variables", "course_id": str(self.course_id), "limit": 2},
        )
        assert res.status_code == 200
        payload = res.json()
        assert len(payload["data"]) == 2

        # 4. POST /retrieve/topic
        res = await client.post(
            "/api/v1/retrieve/topic",
            headers=auth_headers,
            json={"query": "Variables", "topic_id": str(self.topic_id), "limit": 2},
        )
        assert res.status_code == 200
        payload = res.json()
        assert len(payload["data"]) == 2

        # 5. POST /retrieve/unit
        res = await client.post(
            "/api/v1/retrieve/unit",
            headers=auth_headers,
            json={"query": "Variables", "unit_id": str(self.unit_id), "limit": 2},
        )
        assert res.status_code == 200
        payload = res.json()
        assert len(payload["data"]) == 2

        # 6. POST /retrieve/context
        res = await client.post(
            "/api/v1/retrieve/context",
            headers=auth_headers,
            json={"query": "Python types", "limit": 2, "relevance_threshold": 0.0},
        )
        assert res.status_code == 200
        payload = res.json()
        assert "formatted_context" in payload["data"]
        assert len(payload["data"]["chunks"]) == 2

        # 7. GET /retrieve/health
        res = await client.get("/api/v1/retrieve/health", headers=auth_headers)
        assert res.status_code == 200
        assert res.json()["data"]["status"] == "healthy"
