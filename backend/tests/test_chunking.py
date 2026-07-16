"""
Phase 5 — Semantic Chunking & Metadata Enrichment Tests.

Test suite covering:
- BlockProtector block atomicity spans
- ChunkerEngine (spaCy, NLTK, Regex fallback strategies)
- ChunkQualityValidator parameters
- ChunkDeduplicator hash and Jaccard similarity metrics
- MetadataEnricher course units and topics matching
- ChunkingOrchestrator workflow processing
- API routes (enqueue, rechunk, status, list, details, delete, preview, stats, quality report)
- Fail-fast startup checks
"""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.config import settings
from app.exceptions.custom import ConflictError, NotFoundError, ValidationError
from app.models.chunk import Chunk, ChunkMapping, DocumentChunkingJob
from app.models.document_processing import DocumentMetadata
from app.models.resource import Resource
from app.models.curriculum import Department, Program, Semester, Course, Unit, Topic, TopicMapping
from app.services.chunking.base import RawChunk
from app.services.chunking.engine import BlockProtector, ChunkerFactory, verify_nlp_resources
from app.services.chunking.validator import ChunkQualityValidator
from app.services.chunking.deduplicator import ChunkDeduplicator
from app.services.chunking.enrichment import MetadataEnricher, EnrichedMetadata
from app.services.chunking.orchestrator import ChunkingOrchestrator

# ═══════════════════════════════════════════════════════════════════════════════
# BlockProtector and Engine Unit Tests
# ═══════════════════════════════════════════════════════════════════════════════


class TestBlockProtector:
    def test_protects_code_blocks(self):
        text = "Some text before.\n```python\ndef hello():\n    print('world')\n```\nSome text after."
        spans = BlockProtector.get_protected_spans(text)
        assert len(spans) == 1
        start, end = spans[0]
        assert "```python" in text[start:end]

    def test_protects_tables(self):
        text = "Header A | Header B\n---|---\nVal A | Val B\n"
        spans = BlockProtector.get_protected_spans(text)
        assert len(spans) == 1

    def test_protects_lists(self):
        text = "List begins:\n- Item 1\n- Item 2\n- Item 3\nEnd of list."
        spans = BlockProtector.get_protected_spans(text)
        assert len(spans) == 1
        start, end = spans[0]
        assert "- Item 1" in text[start:end]

    def test_protects_algorithms(self):
        text = "Intro.\nAlgorithm: BubbleSort\nInput: Array A\nOutput: Sorted Array A\nOutro."
        spans = BlockProtector.get_protected_spans(text)
        assert len(spans) == 1
        start, end = spans[0]
        assert "Algorithm: BubbleSort" in text[start:end]


class TestChunkerFactoryAndStrategies:
    def test_factory_resolves_all_strategies(self):
        assert ChunkerFactory.get_chunker("spacy").__class__.__name__ == "SpaCyChunker"
        assert ChunkerFactory.get_chunker("nltk").__class__.__name__ == "NLTKChunker"
        assert ChunkerFactory.get_chunker("regex").__class__.__name__ == "RegexChunker"

        with pytest.raises(ValueError):
            ChunkerFactory.get_chunker("invalid")

    def test_regex_chunker_splits_paragraphs(self):
        chunker = ChunkerFactory.get_chunker("regex")
        text = "Paragraph 1 is here.\n\nParagraph 2 is here. It is longer."
        chunks = chunker.split_text(text, text, chunk_size=50, chunk_overlap=10)
        assert len(chunks) == 2
        assert "Paragraph 1" in chunks[0].cleaned_text
        assert "Paragraph 2" in chunks[1].cleaned_text

    def test_nltk_chunker_splits_sentences(self):
        chunker = ChunkerFactory.get_chunker("nltk")
        text = "This is sentence one. This is sentence two. This is sentence three."
        chunks = chunker.split_text(text, text, chunk_size=40, chunk_overlap=5)
        assert len(chunks) >= 2

    def test_spacy_chunker_splits_sentences(self):
        chunker = ChunkerFactory.get_chunker("spacy")
        text = "First sentence of the text. Second sentence here. Third sentence."
        chunks = chunker.split_text(text, text, chunk_size=40, chunk_overlap=5)
        assert len(chunks) >= 2


# ═══════════════════════════════════════════════════════════════════════════════
# Validator and Deduplicator Unit Tests
# ═══════════════════════════════════════════════════════════════════════════════


class TestChunkQualityValidator:
    def test_rejects_empty_chunk(self):
        validator = ChunkQualityValidator(min_len=10)
        chunk = RawChunk(cleaned_text="", raw_text="", page_numbers="1")
        valid, reason = validator.is_valid(chunk)
        assert not valid
        assert "empty" in reason

    def test_rejects_too_short_chunk(self):
        validator = ChunkQualityValidator(min_len=20)
        chunk = RawChunk(cleaned_text="Short", raw_text="Short", page_numbers="1")
        valid, reason = validator.is_valid(chunk)
        assert not valid
        assert "minimum" in reason

    def test_rejects_excessive_symbols(self):
        validator = ChunkQualityValidator(min_len=5)
        chunk = RawChunk(cleaned_text="$$#@%^&*()_+{}[]|\\:;\"'<>,.?/~`", raw_text="", page_numbers="1")
        valid, reason = validator.is_valid(chunk)
        assert not valid
        assert "symbol" in reason

    def test_rejects_repeats(self):
        validator = ChunkQualityValidator(min_len=5)
        chunk = RawChunk(cleaned_text="aaaaaaaaaaaaaaaaaaaaaaaaa", raw_text="", page_numbers="1")
        valid, reason = validator.is_valid(chunk)
        assert not valid
        assert "Repeated" in reason


class TestChunkDeduplicator:
    def test_exact_hash_match(self):
        text_a = "Computer engineering processes."
        text_b = "  Computer   Engineering Processes.  "
        assert ChunkDeduplicator.calculate_hash(text_a) == ChunkDeduplicator.calculate_hash(text_b)

    def test_jaccard_similarity(self):
        dedup = ChunkDeduplicator(similarity_threshold=0.8)
        text_a = "Introduction to algorithms and data structures"
        text_b = "Introduction to algorithms and simple data structures"
        similarity = dedup.calculate_jaccard_similarity(text_a, text_b)
        assert similarity > 0.8
        assert dedup.is_near_duplicate(text_a, text_b) is True

        text_c = "Completely different text contents here."
        assert dedup.is_near_duplicate(text_a, text_c) is False


# ═══════════════════════════════════════════════════════════════════════════════
# Metadata Enrichment Unit Tests
# ═══════════════════════════════════════════════════════════════════════════════


class TestMetadataEnricher:
    @pytest.mark.asyncio
    async def test_enrich_matches_topics(self, db_session: AsyncSession):
        # Setup Course, Unit, and Topic
        dept = Department(id=uuid.uuid4(), name="CS", code="CS")
        db_session.add(dept)
        await db_session.flush()

        prog = Program(id=uuid.uuid4(), department_id=dept.id, name="B.E.")
        db_session.add(prog)
        await db_session.flush()

        sem = Semester(id=uuid.uuid4(), program_id=prog.id, number=1)
        db_session.add(sem)
        await db_session.flush()

        course = Course(id=uuid.uuid4(), semester_id=sem.id, course_title="Algorithms", course_code="AL1")
        db_session.add(course)
        await db_session.flush()

        unit = Unit(id=uuid.uuid4(), course_id=course.id, unit_number=1, title="Sorting Algorithms")
        db_session.add(unit)
        await db_session.flush()

        topic = Topic(id=uuid.uuid4(), unit_id=unit.id, topic_name="Bubble Sort")
        db_session.add(topic)
        await db_session.flush()

        enricher = MetadataEnricher(db_session)
        chunk = RawChunk(
            cleaned_text="Bubble sort is a simple sorting algorithm that repeatedly steps through the list.",
            raw_text="",
            page_numbers="1"
        )
        metadata = await enricher.enrich_chunk(course.id, chunk)
        assert metadata.unit_id == unit.id
        assert metadata.topic_id == topic.id


# ═══════════════════════════════════════════════════════════════════════════════
# API Integration & Background Queue Tests
# ═══════════════════════════════════════════════════════════════════════════════


@pytest_asyncio.fixture
async def admin_headers(client: AsyncClient) -> dict[str, str]:
    email = "admin.chunk@university.edu"
    password = "Admin!Str0ng1"

    await client.post(
        "/api/v1/auth/register",
        json={
            "full_name": "Admin User",
            "email": email,
            "password": password,
            "institution": "Test University",
            "department": "Administration",
            "role": "admin",
        },
    )
    login_resp = await client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": password},
    )
    assert login_resp.status_code == 200
    token = login_resp.json()["data"]["access_token"]
    return {"Authorization": f"Bearer {token}"}


class TestChunkingAPI:
    @pytest.mark.asyncio
    async def test_start_chunking_nonexistent_resource_404(
        self, client: AsyncClient, auth_headers: dict
    ):
        fake_id = uuid.uuid4()
        resp = await client.post(
            f"/api/v1/resources/{fake_id}/chunk",
            headers=auth_headers,
        )
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_get_status_nonexistent_resource_404(
        self, client: AsyncClient, auth_headers: dict
    ):
        fake_id = uuid.uuid4()
        resp = await client.get(
            f"/api/v1/resources/{fake_id}/chunking-status",
            headers=auth_headers,
        )
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_list_chunks_nonexistent_resource_returns_empty_paginated(
        self, client: AsyncClient, auth_headers: dict
    ):
        fake_id = uuid.uuid4()
        resp = await client.get(
            f"/api/v1/resources/{fake_id}/chunks",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        assert resp.json()["data"] == []

    @pytest.mark.asyncio
    async def test_preview_chunking(self, client: AsyncClient, auth_headers: dict):
        resp = await client.post(
            "/api/v1/resources/preview-chunk",
            headers=auth_headers,
            json={
                "text": "Paragraph one.\n\nParagraph two.\n\nParagraph three.",
                "strategy": "regex",
                "chunk_size": 10,
                "chunk_overlap": 0,
            }
        )
        assert resp.status_code == 200
        preview = resp.json()["data"]
        assert len(preview) == 3
        assert preview[0]["cleaned_text"] == "Paragraph one."

    @pytest.mark.asyncio
    async def test_admin_routes_rbac_faculty_blocked(
        self, client: AsyncClient, auth_headers: dict
    ):
        # Faculty user should be blocked from admin statistics & quality reports
        resp = await client.get("/api/v1/chunks/statistics", headers=auth_headers)
        assert resp.status_code == 403

        resp2 = await client.get("/api/v1/chunks/quality-report", headers=auth_headers)
        assert resp2.status_code == 403

    @pytest.mark.asyncio
    async def test_admin_routes_access_success(
        self, client: AsyncClient, admin_headers: dict
    ):
        resp = await client.get("/api/v1/chunks/statistics", headers=admin_headers)
        assert resp.status_code == 200
        assert "total_unique_chunks" in resp.json()["data"]

        resp2 = await client.get("/api/v1/chunks/quality-report", headers=admin_headers)
        assert resp2.status_code == 200
        assert isinstance(resp2.json()["data"], list)


# ═══════════════════════════════════════════════════════════════════════════════
# Full Pipeline Integration End-to-End Tests
# ═══════════════════════════════════════════════════════════════════════════════


class TestFullChunkingPipeline:
    @pytest.mark.asyncio
    async def test_chunking_orchestration_end_to_end(self, db_session: AsyncSession):
        from app.models.user import User, UserRole

        # 1. Setup base models
        user = User(
            id=uuid.uuid4(),
            full_name="Chunk Tester",
            email="chunk.tester@university.edu",
            hashed_password="x",
            role=UserRole.FACULTY.value,
        )
        db_session.add(user)
        await db_session.flush()

        dept = Department(id=uuid.uuid4(), name="CS Dept", code="CSDPT")
        db_session.add(dept)
        await db_session.flush()

        prog = Program(id=uuid.uuid4(), department_id=dept.id, name="B.Tech")
        db_session.add(prog)
        await db_session.flush()

        sem = Semester(id=uuid.uuid4(), program_id=prog.id, number=1)
        db_session.add(sem)
        await db_session.flush()

        course = Course(id=uuid.uuid4(), semester_id=sem.id, course_title="Database", course_code="AA001")
        db_session.add(course)
        await db_session.flush()

        resource = Resource(
            id=uuid.uuid4(),
            course_id=course.id,
            uploaded_by=user.id,
            title="Database Notes",
            file_name="db.txt",
            original_file_name="db.txt",
            file_size=200,
            mime_type="text/plain",
            storage_path="uploads/test/db.txt",
            checksum="abcde0000",
        )
        db_session.add(resource)
        await db_session.flush()

        # 2. Add processed document metadata
        meta = DocumentMetadata(
            id=uuid.uuid4(),
            resource_id=resource.id,
            processing_id=uuid.uuid4(),
            cleaned_text=(
                "Introduction to Databases. " * 30 + "\n\n"
                "A database is an organized collection of data. " * 30 + "\n\n"
                "SQL stands for Structured Query Language. " * 30 + "\n\n"
                "Normalization reduces data redundancy. " * 30
            ),
            raw_text="Intro",
        )
        db_session.add(meta)
        await db_session.flush()

        # 3. Trigger orchestrator process
        orchestrator = ChunkingOrchestrator(db_session)
        job = await orchestrator.process_chunking(resource.id)

        assert job.status == "completed"
        assert job.chunks_count >= 2

        # 4. Verify unique chunks and mappings exist
        chunks = await orchestrator._chunk_repo.get_all_unique_chunks()
        assert len(chunks) >= 2

        mappings = await orchestrator._mapping_repo.list_by_resource(resource.id)
        assert len(mappings) == job.chunks_count
        assert mappings[0].course_id == course.id

    def test_fail_fast_on_missing_spacy_model(self):
        """Startup validation should raise RuntimeError on missing model."""
        with pytest.raises(RuntimeError, match="Missing required spaCy model"):
            verify_nlp_resources("spacy", "nonexistent_spacy_model")
