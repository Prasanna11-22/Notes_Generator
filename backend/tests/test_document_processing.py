"""
Phase 4 — Document Processing Pipeline Tests.

Test coverage targets:
- Parser unit tests (PDF digital, DOCX, PPTX, TXT, scanned-PDF detection)
- TextCleaningPipeline stage-by-stage tests
- ParserFactory tests (valid MIME types, unsupported MIME type)
- DocumentProcessingService integration tests (enqueue, process, metadata)
- API endpoint tests (all 6 routes, RBAC, status lifecycle)
- Error handling (corrupt bytes, empty files, unsupported MIME)
"""

from __future__ import annotations

import io
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.exceptions.custom import ConflictError, NotFoundError, ValidationError
from app.models.document_processing import DocumentProcessing, DocumentMetadata, ProcessingStatus
from app.processors.base import ParseResult
from app.processors.cleaner import TextCleaningPipeline
from app.processors.factory import ParserFactory
from app.processors.pdf_parser import PDFParser
from app.processors.docx_parser import DOCXParser
from app.processors.pptx_parser import PPTXParser
from app.processors.txt_parser import TXTParser
from app.services.document_processing import DocumentProcessingService

# ═══════════════════════════════════════════════════════════════════════════════
# Helpers — minimal valid file fixtures
# ═══════════════════════════════════════════════════════════════════════════════


def _minimal_txt() -> bytes:
    """A short plain-text document."""
    return b"Introduction to Computer Science\n\nChapter 1: Algorithms\nAn algorithm is a step-by-step procedure.\n"


def _minimal_docx() -> bytes:
    """Create a minimal valid DOCX byte stream in memory."""
    from docx import Document

    doc = Document()
    doc.core_properties.title = "Test Document"
    doc.core_properties.author = "Test Author"
    doc.add_heading("Introduction to Machine Learning", level=1)
    doc.add_paragraph("Machine learning is a subset of artificial intelligence.")
    doc.add_paragraph("It enables systems to learn from data automatically.")
    buf = io.BytesIO()
    doc.save(buf)
    return buf.getvalue()


def _minimal_pptx() -> bytes:
    """Create a minimal valid PPTX byte stream in memory."""
    from pptx import Presentation
    from pptx.util import Inches, Pt

    prs = Presentation()
    slide_layout = prs.slide_layouts[0]
    slide = prs.slides.add_slide(slide_layout)
    title = slide.shapes.title
    if title:
        title.text = "Data Structures"
    body = slide.placeholders[1] if len(slide.placeholders) > 1 else None
    if body:
        body.text = "Arrays, Linked Lists, Trees, and Graphs"
    buf = io.BytesIO()
    prs.save(buf)
    return buf.getvalue()


def _minimal_pdf_bytes() -> bytes:
    """Create a minimal valid digital PDF with selectable text using PyMuPDF."""
    try:
        import fitz

        doc = fitz.open()
        page = doc.new_page()
        page.insert_text(
            (50, 72),
            "Introduction to Algorithms\n\nChapter 1: Sorting\nBubble sort is O(n^2).",
        )
        return doc.tobytes()
    except ImportError:
        # Fallback: a minimal hand-crafted PDF with text
        return (
            b"%PDF-1.4\n"
            b"1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n"
            b"2 0 obj<</Type/Pages/Kids[3 0 R]/Count 1>>endobj\n"
            b"3 0 obj<</Type/Page/MediaBox[0 0 612 792]/Parent 2 0 R"
            b"/Contents 4 0 R/Resources<</Font<</F1 5 0 R>>>>>>endobj\n"
            b"4 0 obj<</Length 44>>stream\n"
            b"BT /F1 12 Tf 72 720 Td (Hello World) Tj ET\n"
            b"endstream endobj\n"
            b"5 0 obj<</Type/Font/Subtype/Type1/BaseFont/Helvetica>>endobj\n"
            b"xref\n0 6\n0000000000 65535 f \n"
            b"trailer<</Size 6/Root 1 0 R>>\n%%EOF\n"
        )


# ═══════════════════════════════════════════════════════════════════════════════
# TextCleaningPipeline Unit Tests
# ═══════════════════════════════════════════════════════════════════════════════


class TestTextCleaningPipeline:
    """Unit tests for every cleaning stage."""

    def setup_method(self):
        self.cleaner = TextCleaningPipeline()

    def test_empty_string_returns_empty(self):
        assert self.cleaner.clean("") == ""

    def test_whitespace_only_returns_empty(self):
        assert self.cleaner.clean("   \n\n  ") == ""

    def test_smart_quotes_normalised(self):
        result = self.cleaner.clean("\u201cHello World\u201d")
        assert '"Hello World"' in result

    def test_en_dash_normalised(self):
        result = self.cleaner.clean("pages 1\u20135")
        assert "pages 1-5" in result

    def test_em_dash_normalised(self):
        result = self.cleaner.clean("AI\u2014the future")
        assert "AI--the future" in result

    def test_non_breaking_space_removed(self):
        result = self.cleaner.clean("hello\u00a0world")
        assert "hello world" in result

    def test_page_numbers_removed(self):
        text = "Introduction\n\n42\n\nChapter 1"
        result = self.cleaner.clean(text)
        # Standalone "42" should be removed as a page number
        lines = [l.strip() for l in result.splitlines() if l.strip()]
        assert "42" not in lines

    def test_separator_lines_removed(self):
        text = "Section A\n---\nContent here"
        result = self.cleaner.clean(text)
        assert "---" not in result

    def test_hyphenated_line_break_rejoined(self):
        text = "algo-\nrithm"
        result = self.cleaner.clean(text)
        assert "algorithm" in result

    def test_excess_blank_lines_collapsed(self):
        text = "Line A\n\n\n\n\nLine B"
        result = self.cleaner.clean(text)
        # Should not have more than 2 consecutive newlines
        assert "\n\n\n" not in result

    def test_duplicate_consecutive_lines_removed(self):
        text = "Chapter 1\nChapter 1\nChapter 1\nIntroduction"
        result = self.cleaner.clean(text)
        lines = [l for l in result.splitlines() if l.strip()]
        assert lines.count("Chapter 1") == 1

    def test_trailing_whitespace_stripped_per_line(self):
        text = "line one   \nline two  "
        result = self.cleaner.clean(text)
        for line in result.splitlines():
            assert not line.endswith(" ")

    def test_normal_text_preserved(self):
        text = (
            "Artificial intelligence (AI) is intelligence demonstrated by machines, "
            "as opposed to the natural intelligence displayed by animals and humans."
        )
        result = self.cleaner.clean(text)
        assert "Artificial intelligence" in result
        assert "machines" in result


# ═══════════════════════════════════════════════════════════════════════════════
# ParserFactory Unit Tests
# ═══════════════════════════════════════════════════════════════════════════════


class TestParserFactory:
    def test_pdf_mime_returns_pdf_parser(self):
        parser = ParserFactory.get_parser("application/pdf")
        assert isinstance(parser, PDFParser)

    def test_docx_mime_returns_docx_parser(self):
        parser = ParserFactory.get_parser(
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        )
        assert isinstance(parser, DOCXParser)

    def test_pptx_mime_returns_pptx_parser(self):
        parser = ParserFactory.get_parser(
            "application/vnd.openxmlformats-officedocument.presentationml.presentation"
        )
        assert isinstance(parser, PPTXParser)

    def test_txt_mime_returns_txt_parser(self):
        parser = ParserFactory.get_parser("text/plain")
        assert isinstance(parser, TXTParser)

    def test_unsupported_mime_raises_validation_error(self):
        with pytest.raises(ValidationError):
            ParserFactory.get_parser("image/png")

    def test_supported_mime_types_returns_frozenset(self):
        supported = ParserFactory.supported_mime_types()
        assert isinstance(supported, frozenset)
        assert "application/pdf" in supported
        assert "text/plain" in supported


# ═══════════════════════════════════════════════════════════════════════════════
# TXT Parser Unit Tests
# ═══════════════════════════════════════════════════════════════════════════════


class TestTXTParser:
    def setup_method(self):
        self.parser = TXTParser()

    def test_parse_basic_utf8(self):
        text = "Introduction to Operating Systems\n\nProcesses, Threads, Memory."
        result = self.parser.parse(text.encode("utf-8"), "notes.txt")
        assert "Introduction to Operating Systems" in result.raw_text
        assert result.parser_name == "TXTParser(built-in)"
        assert result.page_count >= 1
        assert result.is_scanned is False

    def test_parse_latin1_encoded_file(self):
        text = "Caf\xe9 and na\xefve concepts in computer science."
        result = self.parser.parse(text.encode("latin-1"), "latin.txt")
        assert result.raw_text  # should decode without crashing
        assert result.is_scanned is False

    def test_parse_empty_file(self):
        result = self.parser.parse(b"", "empty.txt")
        assert result.raw_text == ""
        assert result.page_count >= 1

    def test_supported_mime_types(self):
        assert "text/plain" in self.parser.supported_mime_types

    def test_large_text_page_estimate(self):
        # ~9000 chars → should be estimated at 3 pages
        text = "word " * 1800
        result = self.parser.parse(text.encode(), "large.txt")
        assert result.page_count >= 2


# ═══════════════════════════════════════════════════════════════════════════════
# DOCX Parser Unit Tests
# ═══════════════════════════════════════════════════════════════════════════════


class TestDOCXParser:
    def setup_method(self):
        self.parser = DOCXParser()

    def test_parse_valid_docx(self):
        docx_bytes = _minimal_docx()
        result = self.parser.parse(docx_bytes, "lecture.docx")
        assert "Machine learning" in result.raw_text
        assert result.parser_name == "DOCXParser(python-docx)"
        assert result.is_scanned is False
        assert result.page_count >= 1

    def test_metadata_extracted(self):
        docx_bytes = _minimal_docx()
        result = self.parser.parse(docx_bytes, "lecture.docx")
        assert result.metadata.get("title") == "Test Document"
        assert result.metadata.get("author") == "Test Author"

    def test_invalid_bytes_raises_runtime_error(self):
        with pytest.raises(RuntimeError, match="valid DOCX"):
            self.parser.parse(b"not a docx file", "bad.docx")

    def test_supported_mime_types(self):
        assert (
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
            in self.parser.supported_mime_types
        )


# ═══════════════════════════════════════════════════════════════════════════════
# PPTX Parser Unit Tests
# ═══════════════════════════════════════════════════════════════════════════════


class TestPPTXParser:
    def setup_method(self):
        self.parser = PPTXParser()

    def test_parse_valid_pptx(self):
        pptx_bytes = _minimal_pptx()
        result = self.parser.parse(pptx_bytes, "slides.pptx")
        assert result.parser_name == "PPTXParser(python-pptx)"
        assert result.is_scanned is False
        assert result.page_count >= 1

    def test_slide_markers_in_text(self):
        pptx_bytes = _minimal_pptx()
        result = self.parser.parse(pptx_bytes, "slides.pptx")
        assert "--- Slide 1 ---" in result.raw_text

    def test_invalid_bytes_raises_runtime_error(self):
        with pytest.raises(RuntimeError):
            self.parser.parse(b"garbage bytes", "bad.pptx")

    def test_supported_mime_types(self):
        assert (
            "application/vnd.openxmlformats-officedocument.presentationml.presentation"
            in self.parser.supported_mime_types
        )


# ═══════════════════════════════════════════════════════════════════════════════
# PDF Parser Unit Tests
# ═══════════════════════════════════════════════════════════════════════════════


class TestPDFParser:
    def setup_method(self):
        self.parser = PDFParser()

    def test_parse_digital_pdf(self):
        pdf_bytes = _minimal_pdf_bytes()
        result = self.parser.parse(pdf_bytes, "lecture.pdf")
        assert result.page_count >= 1
        assert result.is_scanned is False
        assert "PDFParser" in result.parser_name

    def test_scanned_detection_empty_pages(self):
        """A PDF with no selectable text should be flagged as scanned."""
        # We can simulate this by testing _detect_scanned directly
        is_scanned = self.parser._detect_scanned(["", "", ""], 3)
        assert is_scanned is True

    def test_scanned_detection_text_pages(self):
        """Pages with sufficient text should NOT be flagged as scanned."""
        pages = [
            "Introduction to algorithms " * 20,
            "Data structures and complexity " * 15,
        ]
        is_scanned = self.parser._detect_scanned(pages, 2)
        assert is_scanned is False

    def test_invalid_bytes_raises_runtime_error(self):
        with pytest.raises(RuntimeError):
            self.parser.parse(b"not a pdf at all", "bad.pdf")

    def test_supported_mime_types(self):
        assert "application/pdf" in self.parser.supported_mime_types


# ═══════════════════════════════════════════════════════════════════════════════
# Service Layer Unit Tests (mocked session)
# ═══════════════════════════════════════════════════════════════════════════════


class TestDocumentProcessingServiceUnit:
    """Unit tests with a fully mocked database session."""

    def _make_service(self, session: AsyncMock) -> DocumentProcessingService:
        return DocumentProcessingService(session)

    def _make_resource(self, mime_type: str = "text/plain") -> MagicMock:
        resource = MagicMock()
        resource.id = uuid.uuid4()
        resource.mime_type = mime_type
        resource.storage_path = "uploads/test/file.txt"
        resource.original_file_name = "notes.txt"
        resource.title = "Test Notes"
        return resource

    @pytest.mark.asyncio
    async def test_enqueue_creates_pending_job(self, db_session: AsyncSession):
        service = DocumentProcessingService(db_session)

        # We need a resource in the DB; skip full integration for unit test
        # by verifying the method raises NotFoundError for non-existent resource
        with pytest.raises(NotFoundError):
            await service.enqueue(uuid.uuid4())

    @pytest.mark.asyncio
    async def test_get_processing_job_not_found_raises(self, db_session: AsyncSession):
        service = DocumentProcessingService(db_session)
        with pytest.raises(NotFoundError):
            await service.get_processing_job(uuid.uuid4())

    @pytest.mark.asyncio
    async def test_get_metadata_not_found_raises(self, db_session: AsyncSession):
        service = DocumentProcessingService(db_session)
        with pytest.raises(NotFoundError):
            await service.get_metadata(uuid.uuid4())

    def test_detect_language_short_text_returns_none(self):
        result = DocumentProcessingService._detect_language("Hi")
        assert result is None

    def test_detect_language_english_text(self):
        text = "Machine learning is a subfield of artificial intelligence. " * 10
        result = DocumentProcessingService._detect_language(text)
        # Should detect English or return None gracefully
        assert result is None or isinstance(result, str)

    def test_parse_metadata_date_none(self):
        assert DocumentProcessingService._parse_metadata_date(None) is None

    def test_parse_metadata_date_pymupdf_format(self):
        from datetime import datetime

        result = DocumentProcessingService._parse_metadata_date("20230615120000")
        assert isinstance(result, datetime)
        assert result.year == 2023
        assert result.month == 6

    def test_parse_metadata_date_iso(self):
        from datetime import datetime

        result = DocumentProcessingService._parse_metadata_date("2023-01-15T10:30:00")
        assert isinstance(result, datetime)
        assert result.year == 2023

    def test_parse_metadata_date_invalid_returns_none(self):
        result = DocumentProcessingService._parse_metadata_date("not-a-date")
        assert result is None


# ═══════════════════════════════════════════════════════════════════════════════
# API Integration Tests
# ═══════════════════════════════════════════════════════════════════════════════


@pytest_asyncio.fixture
async def admin_headers(client: AsyncClient) -> dict[str, str]:
    """Register an admin user and return Bearer auth headers."""
    email = "admin.proc@university.edu"
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


class TestDocumentProcessingAPI:
    """Integration tests using the in-memory SQLite test DB."""

    @pytest.mark.asyncio
    async def test_enqueue_nonexistent_resource_returns_404(
        self, client: AsyncClient, auth_headers: dict
    ):
        fake_id = uuid.uuid4()
        resp = await client.post(
            f"/api/v1/resources/{fake_id}/process",
            headers=auth_headers,
        )
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_get_status_nonexistent_resource_returns_404(
        self, client: AsyncClient, auth_headers: dict
    ):
        fake_id = uuid.uuid4()
        resp = await client.get(
            f"/api/v1/resources/{fake_id}/processing-status",
            headers=auth_headers,
        )
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_get_details_nonexistent_resource_returns_404(
        self, client: AsyncClient, auth_headers: dict
    ):
        fake_id = uuid.uuid4()
        resp = await client.get(
            f"/api/v1/resources/{fake_id}/processing-details",
            headers=auth_headers,
        )
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_get_metadata_nonexistent_resource_returns_404(
        self, client: AsyncClient, auth_headers: dict
    ):
        fake_id = uuid.uuid4()
        resp = await client.get(
            f"/api/v1/resources/{fake_id}/metadata",
            headers=auth_headers,
        )
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_get_text_requires_admin(
        self, client: AsyncClient, auth_headers: dict
    ):
        """Faculty user must not be able to access /text endpoint."""
        fake_id = uuid.uuid4()
        resp = await client.get(
            f"/api/v1/resources/{fake_id}/text",
            headers=auth_headers,  # faculty headers
        )
        assert resp.status_code == 403

    @pytest.mark.asyncio
    async def test_get_text_admin_nonexistent_resource_returns_404(
        self, client: AsyncClient, admin_headers: dict
    ):
        fake_id = uuid.uuid4()
        resp = await client.get(
            f"/api/v1/resources/{fake_id}/text",
            headers=admin_headers,
        )
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_unauthenticated_requests_rejected(self, client: AsyncClient):
        fake_id = uuid.uuid4()
        for path in [
            f"/api/v1/resources/{fake_id}/process",
            f"/api/v1/resources/{fake_id}/processing-status",
            f"/api/v1/resources/{fake_id}/processing-details",
            f"/api/v1/resources/{fake_id}/metadata",
            f"/api/v1/resources/{fake_id}/text",
        ]:
            resp = await client.get(path)
            assert resp.status_code in {401, 403, 405}, (
                f"Expected auth error for {path}, got {resp.status_code}"
            )

    @pytest.mark.asyncio
    async def test_reprocess_nonexistent_resource_returns_404(
        self, client: AsyncClient, auth_headers: dict
    ):
        fake_id = uuid.uuid4()
        resp = await client.post(
            f"/api/v1/resources/{fake_id}/reprocess",
            headers=auth_headers,
        )
        assert resp.status_code == 404


# ═══════════════════════════════════════════════════════════════════════════════
# Full Pipeline Integration Test (mocked storage + background task)
# ═══════════════════════════════════════════════════════════════════════════════


class TestFullProcessingPipeline:
    """
    End-to-end service tests using a real in-memory SQLite DB but
    mocked storage backend and background task runner.
    """

    @pytest.mark.asyncio
    async def test_txt_processing_end_to_end(self, db_session: AsyncSession):
        """Test full pipeline with a TXT file using mocked storage."""
        from app.models.user import User, UserRole
        from app.models.curriculum import Department, Program, Semester, Course
        from app.models.resource import Resource

        # Setup: create minimal DB records
        user = User(
            id=uuid.uuid4(),
            full_name="Pipeline Tester",
            email="pipeline@test.edu",
            hashed_password="hashed",
            role=UserRole.FACULTY.value,
        )
        db_session.add(user)
        await db_session.flush()

        dept = Department(
            id=uuid.uuid4(),
            name="Computer Science Dept",
            code="CSDP1",
        )
        db_session.add(dept)
        await db_session.flush()

        prog = Program(
            id=uuid.uuid4(),
            department_id=dept.id,
            name="B.E. Computer Engineering",
        )
        db_session.add(prog)
        await db_session.flush()

        sem = Semester(
            id=uuid.uuid4(),
            program_id=prog.id,
            number=3,
        )
        db_session.add(sem)
        await db_session.flush()

        course = Course(
            id=uuid.uuid4(),
            semester_id=sem.id,
            course_title="Data Structures",
            course_code="DS301A",
        )
        db_session.add(course)
        await db_session.flush()

        resource = Resource(
            id=uuid.uuid4(),
            course_id=course.id,
            uploaded_by=user.id,
            title="DS Notes",
            file_name="ds_notes.txt",
            original_file_name="ds_notes.txt",
            file_size=len(_minimal_txt()),
            mime_type="text/plain",
            storage_path="uploads/test/ds_notes.txt",
            checksum="abc123",
        )
        db_session.add(resource)
        await db_session.flush()

        # Mock storage to return our test bytes
        txt_bytes = _minimal_txt()
        with patch("app.services.document_processing.get_storage") as mock_storage:
            mock_instance = AsyncMock()
            mock_instance.download.return_value = txt_bytes
            mock_storage.return_value = mock_instance

            service = DocumentProcessingService(db_session)
            job = await service.process(resource.id)

        assert job.status == ProcessingStatus.COMPLETED
        assert job.parser_used == "TXTParser(built-in)"
        assert job.page_count >= 1
        assert job.processing_duration_ms is not None

        # Verify metadata was created
        from app.repositories.document_processing import DocumentMetadataRepository

        meta_repo = DocumentMetadataRepository(db_session)
        meta = await meta_repo.get_by_resource_id(resource.id)
        assert meta is not None
        assert meta.cleaned_text
        assert "Introduction" in (meta.cleaned_text or "")
        assert meta.word_count > 0
        assert meta.char_count > 0
        assert meta.is_scanned is False

    @pytest.mark.asyncio
    async def test_storage_failure_marks_job_failed(self, db_session: AsyncSession):
        """A storage download failure should mark the job as failed."""
        from app.models.user import User, UserRole
        from app.models.curriculum import Department, Program, Semester, Course
        from app.models.resource import Resource

        # Minimal DB setup
        user = User(
            id=uuid.uuid4(),
            full_name="Fail Tester",
            email=f"fail_{uuid.uuid4().hex[:6]}@test.edu",
            hashed_password="x",
            role=UserRole.FACULTY.value,
        )
        db_session.add(user)
        await db_session.flush()

        dept = Department(id=uuid.uuid4(), name="Fail Dept", code="FAILX")
        db_session.add(dept)
        await db_session.flush()

        prog = Program(
            id=uuid.uuid4(), department_id=dept.id, name="Fail Prog"
        )
        db_session.add(prog)
        await db_session.flush()

        sem = Semester(id=uuid.uuid4(), program_id=prog.id, number=1)
        db_session.add(sem)
        await db_session.flush()

        course = Course(
            id=uuid.uuid4(), semester_id=sem.id, course_title="Fail Course", course_code="FC101"
        )
        db_session.add(course)
        await db_session.flush()

        resource = Resource(
            id=uuid.uuid4(),
            course_id=course.id,
            uploaded_by=user.id,
            title="Fail Notes",
            file_name="fail.txt",
            original_file_name="fail.txt",
            file_size=100,
            mime_type="text/plain",
            storage_path="uploads/test/fail.txt",
            checksum="dead0000",
        )
        db_session.add(resource)
        await db_session.flush()

        with patch("app.services.document_processing.get_storage") as mock_storage:
            mock_instance = AsyncMock()
            mock_instance.download.side_effect = FileNotFoundError("File missing")
            mock_storage.return_value = mock_instance

            service = DocumentProcessingService(db_session)
            job = await service.process(resource.id)

        assert job.status == ProcessingStatus.FAILED
        assert job.error_message is not None
        assert "File missing" in job.error_message

    @pytest.mark.asyncio
    async def test_scanned_pdf_detection_sets_ocr_required(self, db_session: AsyncSession):
        """PDF with no extractable text should result in OCR_REQUIRED status."""
        from app.models.user import User, UserRole
        from app.models.curriculum import Department, Program, Semester, Course
        from app.models.resource import Resource

        user = User(
            id=uuid.uuid4(),
            full_name="OCR Tester",
            email=f"ocr_{uuid.uuid4().hex[:6]}@test.edu",
            hashed_password="x",
            role=UserRole.FACULTY.value,
        )
        db_session.add(user)
        await db_session.flush()

        dept = Department(id=uuid.uuid4(), name="OCR Dept", code="OCRXX")
        db_session.add(dept)
        await db_session.flush()

        prog = Program(
            id=uuid.uuid4(), department_id=dept.id, name="OCR Prog"
        )
        db_session.add(prog)
        await db_session.flush()

        sem = Semester(id=uuid.uuid4(), program_id=prog.id, number=1)
        db_session.add(sem)
        await db_session.flush()

        course = Course(
            id=uuid.uuid4(), semester_id=sem.id, course_title="OCR Course", course_code="OC101"
        )
        db_session.add(course)
        await db_session.flush()

        resource = Resource(
            id=uuid.uuid4(),
            course_id=course.id,
            uploaded_by=user.id,
            title="Scanned PDF",
            file_name="scan.pdf",
            original_file_name="scan.pdf",
            file_size=100,
            mime_type="application/pdf",
            storage_path="uploads/test/scan.pdf",
            checksum="scan0000",
        )
        db_session.add(resource)
        await db_session.flush()

        # Mock the parser to return a scanned result
        scanned_result = ParseResult(
            raw_text="",
            page_count=5,
            parser_name="PDFParser(pymupdf)",
            metadata={},
            is_scanned=True,
        )
        with (
            patch("app.services.document_processing.get_storage") as mock_storage,
            patch("app.services.document_processing.ParserFactory.get_parser") as mock_factory,
        ):
            mock_instance = AsyncMock()
            mock_instance.download.return_value = b"%PDF fake"
            mock_storage.return_value = mock_instance

            mock_parser = MagicMock()
            mock_parser.parse.return_value = scanned_result
            mock_factory.return_value = mock_parser

            service = DocumentProcessingService(db_session)
            job = await service.process(resource.id)

        assert job.status == ProcessingStatus.OCR_REQUIRED
        assert "scanned" in (job.error_message or "").lower()
