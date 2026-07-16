"""
Unit and integration tests for Phase 3 — Resource Management & Document Upload Module.
"""

import os
import shutil

import pytest
import pytest_asyncio
from httpx import AsyncClient

from app.core.config import settings
from app.exceptions.custom import ValidationError
from app.models.curriculum import Course, Department, Program, Semester
from app.storage.local import LocalStorage

pytestmark = pytest.mark.asyncio


# ── Configuration & Workspace Cleanup ──────────────────────────────────────────
@pytest_asyncio.fixture(scope="module", autouse=True)
def configure_test_upload_directory():
    """Override standard upload directory to a test-isolated sandbox."""
    settings.upload_dir = "test_uploads"
    os.makedirs(settings.upload_dir, exist_ok=True)
    yield
    if os.path.exists(settings.upload_dir):
        shutil.rmtree(settings.upload_dir)


# ── Fixtures for Admin Users & Academic Entities ─────────────────────────────
@pytest_asyncio.fixture
async def admin_headers(client: AsyncClient) -> dict[str, str]:
    """Register and log in as an Admin user, returning Auth headers."""
    # Register
    res = await client.post(
        "/api/v1/auth/register",
        json={
            "full_name": "Admin Tester",
            "email": "admin.resources@university.edu",
            "password": "Str0ng!Admin1",
            "role": "admin",
        },
    )
    assert res.status_code == 201

    # Login
    res = await client.post(
        "/api/v1/auth/login",
        json={"email": "admin.resources@university.edu", "password": "Str0ng!Admin1"},
    )
    assert res.status_code == 200
    token = res.json()["data"]["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest_asyncio.fixture
async def secondary_faculty_headers(client: AsyncClient) -> dict[str, str]:
    """Register and log in as another Faculty user, returning Auth headers."""
    # Register
    res = await client.post(
        "/api/v1/auth/register",
        json={
            "full_name": "Faculty Secondary",
            "email": "faculty.secondary@university.edu",
            "password": "Str0ng!Faculty1",
            "role": "faculty",
        },
    )
    assert res.status_code == 201

    # Login
    res = await client.post(
        "/api/v1/auth/login",
        json={"email": "faculty.secondary@university.edu", "password": "Str0ng!Faculty1"},
    )
    assert res.status_code == 200
    token = res.json()["data"]["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest_asyncio.fixture
async def test_course(db_session) -> Course:
    """Create a default Course and all parent relationships for resource uploads."""
    dept = Department(name="Computer Science & Engineering", code="CS")
    db_session.add(dept)
    await db_session.flush()

    prog = Program(department_id=dept.id, name="B.Tech. CSE", duration_years=4)
    db_session.add(prog)
    await db_session.flush()

    sem = Semester(program_id=prog.id, number=1)
    db_session.add(sem)
    await db_session.flush()

    course = Course(
        semester_id=sem.id,
        course_code="CS101",
        course_title="Introduction to Programming",
        credits=3,
    )
    db_session.add(course)
    await db_session.flush()
    return course


# ── Storage Abstraction & Path Traversal Security Tests ────────────────────────
class TestStorageSecurity:
    async def test_path_traversal_detection(self):
        """LocalStorage must reject paths that try to escape the base directory."""
        storage = LocalStorage(base_dir="test_uploads")

        # Absolute paths escaping or Relative back-traversals
        bad_paths = [
            "../secret.txt",
            "/absolute/outside/path.pdf",
            "folder/../../outside.docx",
        ]

        for p in bad_paths:
            with pytest.raises(ValidationError) as exc_info:
                storage._resolve_and_verify_path(p)
            assert "traversal" in str(exc_info.value).lower()


# ── CRUD Operations & Upload Tests ─────────────────────────────────────────────
class TestResourceCRUD:
    async def test_upload_resource_success(self, client: AsyncClient, auth_headers, test_course):
        """Faculty can successfully upload a valid PDF document."""
        # 1. Mock file upload
        file_payload = {"file": ("syllabus.pdf", b"%PDF-1.4 mock content here", "application/pdf")}
        form_payload = {
            "course_id": str(test_course.id),
            "title": "Course Syllabus",
            "description": "CSE 101 course syllabus file",
            "resource_type": "Textbook",
        }

        res = await client.post(
            "/api/v1/resources",
            data=form_payload,
            files=file_payload,
            headers=auth_headers,
        )
        assert res.status_code == 201
        data = res.json()["data"]
        assert data["title"] == "Course Syllabus"
        assert data["original_file_name"] == "syllabus.pdf"
        assert data["mime_type"] == "application/pdf"
        assert data["version"] == 1
        assert data["is_active"] is True

        # Verify file is physically created in test_uploads
        storage_path = data["storage_path"]
        target_path = os.path.join("test_uploads", storage_path)
        assert os.path.exists(target_path) is True

    async def test_upload_validation_limits(self, client: AsyncClient, auth_headers, test_course):
        """Ensure file size limits and extension constraints are strictly enforced."""
        # Test 1: Size limit (exceeds default or custom limit)
        large_content = b"a" * (settings.max_upload_size_bytes + 1)
        res = await client.post(
            "/api/v1/resources",
            data={
                "course_id": str(test_course.id),
                "title": "Large File",
                "resource_type": "Other",
            },
            files={"file": ("large.pdf", large_content, "application/pdf")},
            headers=auth_headers,
        )
        assert res.status_code == 422
        assert "exceeds" in res.json()["message"].lower()

        # Test 2: Unsupported Extension
        res = await client.post(
            "/api/v1/resources",
            data={
                "course_id": str(test_course.id),
                "title": "Bad File",
                "resource_type": "Other",
            },
            files={"file": ("virus.exe", b"malware content", "application/octet-stream")},
            headers=auth_headers,
        )
        assert res.status_code == 422
        assert "extension" in res.json()["message"].lower()

        # Test 3: Empty file
        res = await client.post(
            "/api/v1/resources",
            data={
                "course_id": str(test_course.id),
                "title": "Empty File",
                "resource_type": "Other",
            },
            files={"file": ("empty.pdf", b"", "application/pdf")},
            headers=auth_headers,
        )
        assert res.status_code == 422
        assert "empty" in res.json()["message"].lower()

    async def test_upload_duplicate_checksum_rejected(
        self, client: AsyncClient, auth_headers, test_course
    ):
        """Uploading identical content within the same course must throw 409 Conflict."""
        file_payload = ("dup.txt", b"Identical contents for checksum test", "text/plain")

        # First upload
        res = await client.post(
            "/api/v1/resources",
            data={"course_id": str(test_course.id), "title": "First Upload"},
            files={"file": file_payload},
            headers=auth_headers,
        )
        assert res.status_code == 201

        # Duplicate upload
        res_dup = await client.post(
            "/api/v1/resources",
            data={"course_id": str(test_course.id), "title": "Duplicate Upload"},
            files={"file": file_payload},
            headers=auth_headers,
        )
        assert res_dup.status_code == 409
        assert "already exists" in res_dup.json()["message"].lower()


# ── Versioning & Rollback Tests ───────────────────────────────────────────────
class TestResourceVersioning:
    async def test_version_lineage_and_restore(
        self, client: AsyncClient, auth_headers, test_course
    ):
        """Faculty can upload new versions and restore back to older ones."""
        # 1. Primary Upload
        res = await client.post(
            "/api/v1/resources",
            data={"course_id": str(test_course.id), "title": "Versioned Doc"},
            files={"file": ("doc.txt", b"Version 1 content", "text/plain")},
            headers=auth_headers,
        )
        original_data = res.json()["data"]
        original_id = original_data["id"]

        # 2. Upload Version 2
        res_v2 = await client.post(
            f"/api/v1/resources/{original_id}/versions",
            files={"file": ("doc.txt", b"Version 2 content update", "text/plain")},
            headers=auth_headers,
        )
        assert res_v2.status_code == 201
        v2_data = res_v2.json()["data"]
        assert v2_data["version"] == 2
        assert v2_data["parent_id"] == original_id
        assert v2_data["is_active"] is True

        # Verify old version is deactivated
        res_orig_check = await client.get(f"/api/v1/resources/{original_id}", headers=auth_headers)
        assert res_orig_check.json()["data"]["is_active"] is False

        # 3. View Lineage History
        res_history = await client.get(
            f"/api/v1/resources/{original_id}/history", headers=auth_headers
        )
        assert res_history.status_code == 200
        history_list = res_history.json()["data"]
        assert len(history_list) == 2

        # 4. Restore Version 1
        res_restore = await client.post(
            f"/api/v1/resources/{original_id}/restore?version=1",
            headers=auth_headers,
        )
        assert res_restore.status_code == 200
        restored_data = res_restore.json()["data"]
        assert restored_data["version"] == 1
        assert restored_data["is_active"] is True

        # Check v2 is deactivated now
        res_v2_check = await client.get(f"/api/v1/resources/{v2_data['id']}", headers=auth_headers)
        assert res_v2_check.json()["data"]["is_active"] is False


# ── Metadata Update & Search/Filtering Tests ──────────────────────────────────
class TestResourceMetadataAndSearch:
    async def test_update_metadata_and_search(self, client: AsyncClient, auth_headers, test_course):
        # Create resource
        res_setup = await client.post(
            "/api/v1/resources",
            data={"course_id": str(test_course.id), "title": "Initial Title"},
            files={"file": ("search.txt", b"content for search", "text/plain")},
            headers=auth_headers,
        )
        res_data = res_setup.json()["data"]
        res_id = res_data["id"]

        # 1. Update Title and description
        res_put = await client.put(
            f"/api/v1/resources/{res_id}",
            json={"title": "Updated Title", "description": "New description"},
            headers=auth_headers,
        )
        assert res_put.status_code == 200
        assert res_put.json()["data"]["title"] == "Updated Title"

        # 2. Search by Title
        res_search = await client.get(
            f"/api/v1/resources?search=Updated&course_id={test_course.id}",
            headers=auth_headers,
        )
        assert res_search.status_code == 200
        assert res_search.json()["total"] == 1


# ── Security & RBAC Access Gates Tests ─────────────────────────────────────────
class TestResourceSecurityAndRBAC:
    async def test_rbac_ownership_controls(
        self,
        client: AsyncClient,
        auth_headers,
        secondary_faculty_headers,
        admin_headers,
        test_course,
    ):
        """Ensure Faculty cannot delete other's files, while Admins can delete anything."""
        # 1. Faculty A uploads a file
        res = await client.post(
            "/api/v1/resources",
            data={"course_id": str(test_course.id), "title": "Faculty A Doc"},
            files={"file": ("facA.txt", b"Faculty A content description", "text/plain")},
            headers=auth_headers,
        )
        resource_id = res.json()["data"]["id"]

        # 2. Faculty B tries to update it -> 403 Forbidden
        res_edit = await client.put(
            f"/api/v1/resources/{resource_id}",
            json={"title": "Hacked Title"},
            headers=secondary_faculty_headers,
        )
        assert res_edit.status_code == 403

        # 3. Faculty B tries to delete it -> 403 Forbidden
        res_del_bad = await client.delete(
            f"/api/v1/resources/{resource_id}",
            headers=secondary_faculty_headers,
        )
        assert res_del_bad.status_code == 403

        # 4. Admin deletes it successfully -> 200 OK
        res_del_admin = await client.delete(
            f"/api/v1/resources/{resource_id}",
            headers=admin_headers,
        )
        assert res_del_admin.status_code == 200

        # Verify resource is gone from DB
        res_verify = await client.get(f"/api/v1/resources/{resource_id}", headers=auth_headers)
        assert res_verify.status_code == 404
