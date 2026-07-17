"""
Unit and Integration Tests for Phase 13 Educational Image Retrieval & Diagram Engine.
"""

import json
import uuid
import pytest
from datetime import datetime
from unittest.mock import AsyncMock, patch
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import status
from httpx import AsyncClient

from app.models.curriculum import Course, Topic, Department, Program, Semester, Unit
from app.models.image import Image
from app.services.image.concept_extractor import EducationalConceptExtractor, KeywordExtractionService
from app.services.image.license_validator import LicenseValidationService
from app.services.image.ranking import ImageRankingService
from app.services.image.cache import ImageCacheService
from app.services.image.service import ImageRetrievalService
from app.services.image.providers import WikimediaProvider
from app.models.user import User


# ── 1. Keyword & Concept Extractor Tests ─────────────────────────────────

class TestConceptExtractorAndQueryOptimizer:
    """Tests topic analysis and search query optimization."""

    def test_analyze_concept_algorithm(self):
        analysis = EducationalConceptExtractor.analyze_concept("Binary Search Tree", "Syllabus topic for searching")
        assert analysis["category"] == "Algorithm"
        assert analysis["preferred_diagram"] == "Flowchart"
        assert "Search" in analysis["secondary_concepts"] or "Tree" in analysis["secondary_concepts"]

    def test_analyze_concept_protocol(self):
        analysis = EducationalConceptExtractor.analyze_concept("TCP Handshake", "Protocol description")
        assert analysis["category"] == "Network Protocol"
        assert analysis["preferred_diagram"] == "Network Diagram"

    def test_extract_optimized_queries(self):
        queries = KeywordExtractionService.extract_optimized_queries("Dijkstra Algorithm")
        assert len(queries) > 0
        assert any("Flowchart" in q for q in queries)
        assert any("Diagram" in q for q in queries)


# ── 2. License Validator Tests ───────────────────────────────────────────

class TestLicenseValidationService:
    """Tests open-license OER compliance checks."""

    def test_normalize_license_variations(self):
        assert LicenseValidationService.normalize_license("CC-BY-SA 4.0") == "CC BY-SA"
        assert LicenseValidationService.normalize_license("CC BY 3.0") == "CC BY"
        assert LicenseValidationService.normalize_license("CC0 1.0 Universal") == "CC0"
        assert LicenseValidationService.normalize_license("Public domain") == "Public Domain"
        assert LicenseValidationService.normalize_license("PD") == "Public Domain"
        assert LicenseValidationService.normalize_license("CC BY-NC-ND") == "CC BY-NC-ND"  # not normalized to valid categories

    def test_is_license_valid(self):
        assert LicenseValidationService.is_license_valid("CC BY-SA 4.0") is True
        assert LicenseValidationService.is_license_valid("CC0") is True
        assert LicenseValidationService.is_license_valid("Public Domain") is True
        assert LicenseValidationService.is_license_valid("CC BY-NC-ND") is False
        assert LicenseValidationService.is_license_valid("Copyrighted") is False


# ── 3. Image Ranking Tests ───────────────────────────────────────────────

class TestImageRankingService:
    """Tests scoring and candidate sorting weights."""

    def test_score_image_perfect_landscape(self):
        candidate = {
            "title": "File:Binary Search Algorithm Flowchart.png",
            "description": "Flowchart displaying binary search execution.",
            "width": 1200,
            "height": 800,  # aspect ratio 1.5 (landscape)
            "license": "CC0",
        }
        score = ImageRankingService.score_image(candidate, "Binary Search", "Flowchart")
        # High score because of matching keywords, resolution, landscape aspect ratio, and CC0
        assert score > 70.0

    def test_score_image_low_resolution(self):
        candidate = {
            "title": "Thumbnail.jpg",
            "description": "Simple diagram.",
            "width": 100,
            "height": 100,
            "license": "Copyrighted",
        }
        score = ImageRankingService.score_image(candidate, "Binary Search", "Flowchart")
        assert score < 30.0

    def test_rank_candidates(self):
        candidates = [
            {
                "title": "Low Res.png",
                "description": "Algorithm overview.",
                "width": 200,
                "height": 150,
                "license": "CC BY",
            },
            {
                "title": "High Res Diagram.png",
                "description": "Dijkstra algorithm flowchart visualization.",
                "width": 1200,
                "height": 800,
                "license": "CC0",
            }
        ]
        ranked = ImageRankingService.rank_candidates(candidates, "Dijkstra", "Flowchart")
        assert ranked[0]["title"] == "High Res Diagram.png"
        assert ranked[0]["ranking_score"] > ranked[1]["ranking_score"]


# ── 4. Cache Service Tests ───────────────────────────────────────────────

class TestImageCacheService:
    """Tests key generation and DB retrieval queries."""

    def test_generate_cache_key(self):
        key1 = ImageCacheService.generate_cache_key("Binary Search", "Binary", "Wikimedia")
        key2 = ImageCacheService.generate_cache_key("Binary Search", "Binary", "Wikimedia")
        assert key1 == key2
        assert "wikimedia" in key1
        assert "binary" in key1

    @pytest.mark.asyncio
    async def test_cache_hit_miss(self, db_session: AsyncSession):
        key = "img_cache_test_key"
        # Should be a cache miss first
        cached = await ImageCacheService.get_cached_image(db_session, key)
        assert cached is None

        # Insert a dummy record with the cache key
        dummy = Image(
            image_url="http://test.com/diagram.png",
            provider="Wikimedia",
            license="CC0",
            ranking_score=95.0,
            image_metadata={"cache_key": key, "title": "Test Title", "width": 800, "height": 600, "description": "Desc", "thumbnail": "thumb"},
        )
        db_session.add(dummy)
        await db_session.flush()

        # Should be a cache hit now
        cached = await ImageCacheService.get_cached_image(db_session, key)
        assert cached is not None
        assert cached.image_url == "http://test.com/diagram.png"

    @pytest.mark.asyncio
    async def test_cache_expiration(self, db_session: AsyncSession):
        key = "img_cache_expire_key"
        from datetime import datetime, timedelta
        
        # Insert an expired record (older than 7 days)
        expired_date = datetime.utcnow() - timedelta(days=10)
        dummy = Image(
            image_url="http://test.com/expired_diagram.png",
            provider="Wikimedia",
            license="CC0",
            ranking_score=90.0,
            image_metadata={"cache_key": key, "title": "Expired", "width": 800, "height": 600, "description": "Desc", "thumbnail": "thumb"},
        )
        dummy.retrieved_at = expired_date
        db_session.add(dummy)
        await db_session.flush()

        # Should treat as cache miss due to expiration check
        cached = await ImageCacheService.get_cached_image(db_session, key, max_age_days=7)
        assert cached is None


# ── 5. Integration Pipeline Tests ────────────────────────────────────────

class TestImageIntegrationPipeline:
    """Tests search -> validate -> rank -> save -> cache flow with mock client."""

    @pytest.mark.asyncio
    @patch("app.services.image.providers.WikimediaProvider.search_images", new_callable=AsyncMock)
    async def test_full_retrieval_flow(self, mock_search, db_session: AsyncSession, test_user: dict):
        # 1. Setup curriculum records in DB
        dept = Department(id=uuid.uuid4(), name="Computer Science", code="CS")
        db_session.add(dept)
        await db_session.flush()

        prog = Program(id=uuid.uuid4(), department_id=dept.id, name="B.Tech CS", duration_years=4)
        db_session.add(prog)
        await db_session.flush()

        sem = Semester(id=uuid.uuid4(), program_id=prog.id, number=3)
        db_session.add(sem)
        await db_session.flush()

        course = Course(id=uuid.uuid4(), semester_id=sem.id, course_code="CS301", course_title="Database Systems", credits=4)
        db_session.add(course)
        await db_session.flush()

        unit = Unit(id=uuid.uuid4(), course_id=course.id, unit_number=1, title="Unit 1: DB Intro")
        db_session.add(unit)
        await db_session.flush()

        topic = Topic(id=uuid.uuid4(), unit_id=unit.id, topic_name="SQL Joins", description="Inner and outer joins")
        db_session.add(topic)
        await db_session.flush()

        # 2. Setup mock search results
        mock_search.return_value = [
            {
                "title": "File:SQL Joins Flowchart.png",
                "url": "https://upload.wikimedia.org/wikipedia/commons/sql_joins.png",
                "description": "Syllabus flowchart displaying SQL outer and inner joins.",
                "width": 1200,
                "height": 800,
                "license": "CC BY-SA 4.0",
                "source": "Wikimedia Commons",
                "thumbnail": "https://upload.wikimedia.org/wikipedia/commons/thumb/sql_joins.png",
            }
        ]

        service = ImageRetrievalService()
        result = await service.retrieve_educational_image(
            db=db_session,
            topic=topic.topic_name,
            description=topic.description,
            course_id=course.id,
            topic_id=topic.id,
        )

        assert result is not None
        assert result.image_url == "https://upload.wikimedia.org/wikipedia/commons/sql_joins.png"
        assert result.provider == "Wikimedia"
        assert result.license == "CC BY-SA 4.0"
        assert result.ranking_score > 70.0
        assert result.image_metadata["width"] == 1200

        # Trigger again to verify cache hit
        cached_result = await service.retrieve_educational_image(
            db=db_session,
            topic=topic.topic_name,
            description=topic.description,
            course_id=course.id,
            topic_id=topic.id,
        )
        assert cached_result is not None
        assert cached_result.id == result.id  # Same record fetched from cache


# ── 6. REST API Endpoints Verification ───────────────────────────────────

class TestImageAPI:
    """Verifies REST route requests, validations, history, and status codes."""

    @pytest.mark.asyncio
    @patch("app.services.image.providers.WikimediaProvider.search_images", new_callable=AsyncMock)
    async def test_search_endpoint(self, mock_search, client: AsyncClient, auth_headers: dict):
        mock_search.return_value = [
            {
                "title": "Binary Tree.png",
                "url": "http://test.com/tree.png",
                "description": "Diagram of a tree",
                "width": 600,
                "height": 400,
                "license": "CC0",
                "source": "Wikimedia Commons",
                "thumbnail": "http://test.com/tree_thumb.png",
            }
        ]

        payload = {
            "topic": "Binary Search Tree",
            "description": "Data structures topic",
        }

        res = await client.post(
            "/api/v1/images/search",
            headers=auth_headers,
            json=payload,
        )
        assert res.status_code == 200
        data = res.json()["data"]
        assert len(data) == 1
        assert data[0]["url"] == "http://test.com/tree.png"

    @pytest.mark.asyncio
    async def test_validate_endpoint_valid(self, client: AsyncClient, auth_headers: dict):
        payload = {
            "image_url": "http://test.com/diagram.png",
            "width": 1024,
            "height": 768,
            "license": "CC BY-SA",
            "title": "SQL Schema",
            "description": "Schema layout",
        }
        res = await client.post(
            "/api/v1/images/validate",
            headers=auth_headers,
            json=payload,
        )
        assert res.status_code == 200
        data = res.json()["data"]
        assert data["success"] is True
        assert data["normalized_license"] == "CC BY-SA"

    @pytest.mark.asyncio
    async def test_validate_endpoint_invalid_resolution(self, client: AsyncClient, auth_headers: dict):
        payload = {
            "image_url": "http://test.com/diagram.png",
            "width": 200,
            "height": 100,  # too low
            "license": "CC BY-SA",
        }
        res = await client.post(
            "/api/v1/images/validate",
            headers=auth_headers,
            json=payload,
        )
        assert res.status_code == 200
        data = res.json()["data"]
        assert data["success"] is False
        assert "resolution too low" in data["message"]

    @pytest.mark.asyncio
    async def test_health_endpoint(self, client: AsyncClient, auth_headers: dict):
        res = await client.get("/api/v1/images/health", headers=auth_headers)
        assert res.status_code == 200
        assert res.json()["data"]["status"] == "healthy"

    @pytest.mark.asyncio
    @patch("app.api.v1.image.ImageRepository.get_by_id", new_callable=AsyncMock)
    @patch("app.api.v1.image.ImageRepository.delete", new_callable=AsyncMock)
    @patch("app.services.image.service.ImageRetrievalService.retrieve_educational_image", new_callable=AsyncMock)
    async def test_retrieve_and_delete_endpoints(
        self,
        mock_retrieve,
        mock_delete,
        mock_get,
        client: AsyncClient,
        auth_headers: dict,
    ):
        img_id = uuid.uuid4()
        now = datetime.utcnow()
        mock_image = Image(
            id=img_id,
            course_id=uuid.uuid4(),
            topic_id=uuid.uuid4(),
            image_url="https://upload.wikimedia.org/wikipedia/commons/sql.png",
            provider="Wikimedia",
            license="CC0",
            ranking_score=85.5,
            image_metadata={"title": "SQL", "width": 800, "height": 600, "description": "Desc", "thumbnail": "thumb"},
        )
        mock_image.retrieved_at = now
        mock_retrieve.return_value = mock_image
        mock_get.return_value = mock_image
        mock_delete.return_value = None

        # 1. Retrieve Endpoint
        payload = {
            "topic": "SQL",
            "description": "SQL joins",
        }
        res = await client.post(
            "/api/v1/images/retrieve",
            headers=auth_headers,
            json=payload,
        )
        assert res.status_code == 200
        assert res.json()["data"]["image_url"] == "https://upload.wikimedia.org/wikipedia/commons/sql.png"

        # 2. Get Details Endpoint
        res_get = await client.get(
            f"/api/v1/images/{img_id}",
            headers=auth_headers,
        )
        assert res_get.status_code == 200
        assert res_get.json()["data"]["ranking_score"] == 85.5

        # 3. Delete Endpoint
        res_del = await client.delete(
            f"/api/v1/images/{img_id}",
            headers=auth_headers,
        )
        assert res_del.status_code == 200
        assert res_del.json()["success"] is True
