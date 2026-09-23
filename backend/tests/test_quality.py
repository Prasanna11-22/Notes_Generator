"""
Unit and Integration Tests for Phase 14 Academic Quality & Intelligence Engine.
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
from app.models.quality import QualityReport, FacultyPreference
from app.services.quality.curriculum import CurriculumValidationService, CourseOutcomeValidationService
from app.services.quality.bloom import BloomValidationService, DifficultyValidationService
from app.services.quality.style import FacultyPreferenceValidationService
from app.services.quality.metrics import ReadabilityAnalysisService, ConsistencyValidationService
from app.services.quality.scorer import EducationalQualityScoringService, ConfidenceScoringService
from app.services.quality.analytics import AnalyticsService
from app.services.quality.service import AcademicValidationService
from app.models.user import User


# ── 1. Curriculum & Course Outcome Validator Tests ──────────────────────

class TestCurriculumAndCourseOutcomeValidators:
    """Tests curriculum alignment coverage checks."""

    def test_curriculum_coverage_success(self):
        content = "This syllabus notes document explains Binary Search algorithms."
        res = CurriculumValidationService.validate_curriculum_coverage(content, "Binary Search", "Searching description", "Unit 1")
        assert res["passed"] is True
        assert res["score"] == 100.0

    def test_curriculum_coverage_low_score(self):
        content = "General unrelated software engineering concepts."
        res = CurriculumValidationService.validate_curriculum_coverage(content, "Binary Search Tree Traversal", None, None)
        assert res["passed"] is False
        assert res["score"] < 50.0

    def test_course_outcome_overlap(self):
        content = "Design custom relational database schemas."
        outcomes = ["Design database schema solutions for applications.", "Apply SQL joins."]
        res = CourseOutcomeValidationService.validate_course_outcome_overlap(content, outcomes)
        assert res["passed"] is True
        assert res["score"] > 20.0


# ── 2. Bloom & Difficulty Validator Tests ─────────────────────────────────

class TestBloomAndDifficultyValidators:
    """Tests Bloom cognitive verbs and difficulty indicators."""

    def test_bloom_validation_remember(self):
        content = "Please define what a binary search is and list all elements."
        res = BloomValidationService.validate_bloom_alignment(content, "Remember")
        assert res["passed"] is True
        assert "define" in res["details"]["matched_target_verbs"]

    def test_bloom_validation_mismatch(self):
        content = "Please list the items."
        res = BloomValidationService.validate_bloom_alignment(content, "Create")
        assert res["passed"] is False

    def test_difficulty_validation_easy(self):
        content = "This is a tree. It has nodes. Nodes hold data."
        res = DifficultyValidationService.validate_difficulty_alignment(content, "Easy")
        assert res["passed"] is True
        assert res["details"]["detected_difficulty"] == "Easy"


# ── 3. Readability & Consistency Analyzers ────────────────────────────────

class TestReadabilityAndConsistencyAnalyzers:
    """Tests readability indexes and duplicate concepts detection."""

    def test_syllable_counter(self):
        assert ReadabilityAnalysisService.count_syllables_in_word("define") == 2
        assert ReadabilityAnalysisService.count_syllables_in_word("algorithm") == 3

    def test_readability_analysis(self):
        content = "In computer science, a binary search tree is a rooted binary tree data structure with nodes."
        res = ReadabilityAnalysisService.analyze_readability(content)
        assert res["reading_ease"] > 0.0
        assert "metrics" in res

    def test_consistency_duplicate_paragraphs(self):
        content = (
            "Design custom relational database schemas for high performance.\n\n"
            "Design custom relational database schemas for high performance."
        )
        res = ConsistencyValidationService.detect_duplicate_paragraphs(content)
        assert res["passed"] is False
        assert res["details"]["redundancies_detected_count"] == 1

    def test_broken_cross_references(self):
        content = "Please refer to table database_info for validation details."
        res = ConsistencyValidationService.detect_inconsistencies(content)
        assert len(res["details"]["broken_references_found"]) == 1


# ── 4. Scorer & Confidence Estimators ─────────────────────────────────────

class TestScoringServices:
    """Tests overall quality weights and confidence decay rules."""

    def test_overall_quality_scorer(self):
        sub_results = {
            "curriculum": {"score": 90.0},
            "course_outcomes": {"score": 85.0},
            "bloom": {"score": 95.0},
            "difficulty": {"score": 100.0},
            "preferences": {"score": 80.0},
            "readability": {"score": 75.0},
            "consistency": {"score": 90.0},
            "completeness": {"score": 100.0},
            "terminology": {"score": 100.0},
            "image_relevance": {"score": 100.0},
        }
        score = EducationalQualityScoringService.calculate_overall_score(sub_results)
        assert 80.0 < score < 95.0

    def test_confidence_decay_rules(self):
        sub_results = {
            "curriculum": {"passed": False},  # critical -20
            "course_outcomes": {"passed": True},
            "bloom": {"passed": False},  # critical -20
            "difficulty": {"passed": False},  # non-critical -10
        }
        confidence = ConfidenceScoringService.calculate_confidence_score(sub_results)
        assert confidence == 50.0


# ── 5. Completeness, Terminology & Image Relevance Tests ──────────────────

class TestNewQAEngineValidators:
    """Tests Phase 14 new completeness, terminology, and image relevance validators."""

    def test_validate_completeness(self):
        content = (
            "# Introduction\n\n"
            "Here is the database detail explanation block.\n\n"
            "- Item A\n"
            "- Item B\n"
            "- Item C\n\n"
            "# Summary\n\n"
            "This completes the notes structure."
        )
        res = AcademicValidationService.validate_completeness(content)
        assert res["passed"] is True
        assert res["score"] >= 50.0

    def test_validate_terminology_placeholder_fail(self):
        content = "This todo layout has lorem ipsum placeholders."
        res = AcademicValidationService.validate_terminology_accuracy(content, "Layout")
        assert res["passed"] is False
        assert len(res["details"]["placeholders_found"]) >= 2

    def test_validate_image_relevance(self):
        content = "Inner and outer SQL joins are used to merge datasets."
        img_metadata = {
            "title": "SQL Joins Diagram",
            "description": "Flowchart representing inner joins",
        }
        res = AcademicValidationService.validate_image_relevance(content, img_metadata)
        assert res["passed"] is True
        assert res["score"] > 20.0


# ── 6. Integration QA Pipeline Tests ─────────────────────────────────────

class TestQualityIntegrationPipeline:
    """Tests full QA orchestrator pipeline execution and DB logging."""

    @pytest.mark.asyncio
    async def test_full_validation_pipeline_flow(self, db_session: AsyncSession):
        content = "Create a database layout. Solve the issues matching database guidelines."
        report = await AcademicValidationService.create_quality_report(
            db=db_session,
            content=content,
            topic_name="Database Layout",
            target_bloom="Create",
            target_difficulty="Medium",
            course_outcomes=["Design database schema layouts."],
            teaching_style="Inquiry-based",
            expected_length=200,
        )

        assert report.id is not None
        assert report.quality_score > 50.0
        assert report.confidence_score >= 50.0
        assert "bloom" in report.validation_details
        assert "curriculum" in report.validation_details


# ── 7. REST API Endpoints Verification ───────────────────────────────────

class TestQualityAPI:
    """Verifies REST route requests, dashboard statistics, and health checks."""

    @pytest.mark.asyncio
    async def test_validate_endpoint(self, client: AsyncClient, auth_headers: dict):
        payload = {
            "content": "State the definition of standard recursion algorithm.",
            "topic_name": "Recursion",
            "target_bloom": "Remember",
            "target_difficulty": "Easy",
            "course_outcomes": ["State algorithms properties."],
            "teaching_style": "Standard Academic",
            "expected_length": 50,
        }

        res = await client.post(
            "/api/v1/quality/validate",
            headers=auth_headers,
            json=payload,
        )
        assert res.status_code == 200
        data = res.json()["data"]
        assert "quality_score" in data
        assert "confidence_score" in data

    @pytest.mark.asyncio
    async def test_report_endpoint(self, client: AsyncClient, auth_headers: dict):
        payload = {
            "content": "Explain the TCP handshake process.",
            "topic_name": "TCP Protocol",
            "target_bloom": "Understand",
            "target_difficulty": "Medium",
        }

        res = await client.post(
            "/api/v1/quality/report",
            headers=auth_headers,
            json=payload,
        )
        assert res.status_code == 200
        data = res.json()["data"]
        assert data["quality_score"] > 0.0

    @pytest.mark.asyncio
    async def test_dashboard_endpoint(self, client: AsyncClient, auth_headers: dict):
        res = await client.get("/api/v1/quality/dashboard", headers=auth_headers)
        assert res.status_code == 200
        data = res.json()["data"]
        assert "metrics" in data
        assert "statistics" in data

    @pytest.mark.asyncio
    async def test_health_endpoint(self, client: AsyncClient, auth_headers: dict):
        res = await client.get("/api/v1/quality/health", headers=auth_headers)
        assert res.status_code == 200
        assert res.json()["data"]["status"] == "healthy"

    @pytest.mark.asyncio
    @patch("app.api.v1.quality.QualityReportRepository.get_by_id", new_callable=AsyncMock)
    async def test_get_report_by_id(self, mock_get, client: AsyncClient, auth_headers: dict):
        report_id = uuid.uuid4()
        now = datetime.utcnow()
        mock_report = QualityReport(
            id=report_id,
            content_id=uuid.uuid4(),
            content_type="material",
            quality_score=92.5,
            confidence_score=100.0,
            validation_details={},
        )
        mock_report.validation_timestamp = now
        mock_get.return_value = mock_report

        res = await client.get(f"/api/v1/quality/{report_id}", headers=auth_headers)
        assert res.status_code == 200
        assert res.json()["data"]["quality_score"] == 92.5
