"""
Unit and Integration Tests for Curriculum Management Module.

Tests cover:
- Lookup tables (Bloom levels, Knowledge levels)
- CRUD operations for Department, Program, Semester, Course, Unit, Topic, Course Outcome, and mappings
- RBAC permissions (Faculty read-only, Admin full CRUD)
- Validations (duplicate course codes, invalid semesters, duplicates within course/unit)
- Paging, filtering, sorting, and search
- CSV Import validation and parsing
"""

import uuid

import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy import select

from app.models.curriculum import BloomLevel, KnowledgeLevel

pytestmark = pytest.mark.asyncio


# ── Seed Lookup Tables & User Fixtures ─────────────────────────────────────────
@pytest_asyncio.fixture(autouse=True)
async def seed_lookups(db_session):
    """Seed Bloom and Knowledge lookup tables for test database isolation."""
    res = await db_session.execute(select(BloomLevel))
    if not res.scalars().all():
        bloom_names = ["Remember", "Understand", "Apply", "Analyze", "Evaluate", "Create"]
        for name in bloom_names:
            db_session.add(BloomLevel(id=uuid.uuid4(), name=name))

        knowledge_names = ["Factual", "Conceptual", "Procedural", "Metacognitive"]
        for name in knowledge_names:
            db_session.add(KnowledgeLevel(id=uuid.uuid4(), name=name))

        await db_session.flush()


@pytest_asyncio.fixture
async def admin_headers(client: AsyncClient) -> dict[str, str]:
    """Register and log in as an Admin user, returning Auth headers."""
    res = await client.post(
        "/api/v1/auth/register",
        json={
            "full_name": "Admin User",
            "email": "admin.curriculum@university.edu",
            "password": "Str0ng!Admin1",
            "role": "admin",
        },
    )
    assert res.status_code == 201

    res = await client.post(
        "/api/v1/auth/login",
        json={"email": "admin.curriculum@university.edu", "password": "Str0ng!Admin1"},
    )
    assert res.status_code == 200
    token = res.json()["data"]["access_token"]
    return {"Authorization": f"Bearer {token}"}


# Helper fixture to create a complete base curriculum hierarchy
@pytest_asyncio.fixture
async def base_curriculum(client: AsyncClient, admin_headers):
    # Department
    dept_res = await client.post(
        "/api/v1/departments",
        json={"name": "Computer Science & Engineering", "code": "cse", "description": "CSE Dept"},
        headers=admin_headers,
    )
    dept_id = dept_res.json()["data"]["id"]

    # Program
    prog_res = await client.post(
        "/api/v1/programs",
        json={"department_id": dept_id, "name": "B.Tech. CSE", "duration_years": 4},
        headers=admin_headers,
    )
    prog_id = prog_res.json()["data"]["id"]

    # Semester
    sem_res = await client.post(
        "/api/v1/semesters",
        json={"program_id": prog_id, "number": 1},
        headers=admin_headers,
    )
    sem_id = sem_res.json()["data"]["id"]

    # Course
    course_res = await client.post(
        "/api/v1/courses",
        json={
            "semester_id": sem_id,
            "course_code": "CS101",
            "course_title": "Introduction to Programming",
            "credits": 3,
        },
        headers=admin_headers,
    )
    course_id = course_res.json()["data"]["id"]

    # Unit
    unit_res = await client.post(
        "/api/v1/units",
        json={"course_id": course_id, "unit_number": 1, "title": "Basics of C"},
        headers=admin_headers,
    )
    unit_id = unit_res.json()["data"]["id"]

    # Topic
    topic_res = await client.post(
        "/api/v1/topics",
        json={"unit_id": unit_id, "topic_name": "Variables and Data Types"},
        headers=admin_headers,
    )
    topic_id = topic_res.json()["data"]["id"]

    # Course Outcome
    co_res = await client.post(
        "/api/v1/course-outcomes",
        json={"course_id": course_id, "co_number": 1, "description": "Understand basic variables"},
        headers=admin_headers,
    )
    co_id = co_res.json()["data"]["id"]

    return {
        "dept_id": dept_id,
        "prog_id": prog_id,
        "sem_id": sem_id,
        "course_id": course_id,
        "unit_id": unit_id,
        "topic_id": topic_id,
        "co_id": co_id,
    }


# ── Lookups Tests ─────────────────────────────────────────────────────────────
class TestLookups:
    async def test_list_bloom_levels(self, client: AsyncClient, auth_headers):
        response = await client.get("/api/v1/bloom-levels", headers=auth_headers)
        assert response.status_code == 200
        assert len(response.json()["data"]) == 6

        # Detail lookup
        level_id = response.json()["data"][0]["id"]
        res = await client.get(f"/api/v1/bloom-levels/{level_id}", headers=auth_headers)
        assert res.status_code == 200
        assert res.json()["data"]["id"] == level_id

    async def test_list_knowledge_levels(self, client: AsyncClient, auth_headers):
        response = await client.get("/api/v1/knowledge-levels", headers=auth_headers)
        assert response.status_code == 200
        assert len(response.json()["data"]) == 4

        # Detail lookup
        level_id = response.json()["data"][0]["id"]
        res = await client.get(f"/api/v1/knowledge-levels/{level_id}", headers=auth_headers)
        assert res.status_code == 200
        assert res.json()["data"]["id"] == level_id


# ── Department Tests ──────────────────────────────────────────────────────────
class TestDepartment:
    async def test_department_crud(self, client: AsyncClient, admin_headers, auth_headers):
        # Create
        response = await client.post(
            "/api/v1/departments",
            json={
                "name": "Computer Science & Engineering",
                "code": "cse",
                "description": "CSE Dept",
            },
            headers=admin_headers,
        )
        assert response.status_code == 201
        dept_id = response.json()["data"]["id"]

        # Read detail
        res = await client.get(f"/api/v1/departments/{dept_id}", headers=auth_headers)
        assert res.status_code == 200
        assert res.json()["data"]["name"] == "Computer Science & Engineering"

        # Update
        res = await client.put(
            f"/api/v1/departments/{dept_id}",
            json={"name": "CS & Eng"},
            headers=admin_headers,
        )
        assert res.status_code == 200
        assert res.json()["data"]["name"] == "CS & Eng"

        # Delete
        res = await client.delete(f"/api/v1/departments/{dept_id}", headers=admin_headers)
        assert res.status_code == 200

        # Read deleted
        res = await client.get(f"/api/v1/departments/{dept_id}", headers=auth_headers)
        assert res.status_code == 404

    async def test_create_department_duplicate_code(self, client: AsyncClient, admin_headers):
        # First
        await client.post(
            "/api/v1/departments",
            json={"name": "Mechanical", "code": "MECH"},
            headers=admin_headers,
        )
        # Duplicate
        response = await client.post(
            "/api/v1/departments",
            json={"name": "Mechanical Second", "code": "mech"},
            headers=admin_headers,
        )
        assert response.status_code == 409

    async def test_list_departments(self, client: AsyncClient, auth_headers, admin_headers):
        await client.post(
            "/api/v1/departments",
            json={"name": "Civil Engineering", "code": "CIVIL"},
            headers=admin_headers,
        )
        response = await client.get("/api/v1/departments?search=civil", headers=auth_headers)
        assert response.status_code == 200
        assert response.json()["total"] == 1


# ── Program & Semester Tests ──────────────────────────────────────────────────
class TestProgramAndSemester:
    async def test_program_crud(
        self, client: AsyncClient, admin_headers, auth_headers, base_curriculum
    ):
        dept_id = base_curriculum["dept_id"]

        # Create
        res = await client.post(
            "/api/v1/programs",
            json={"department_id": dept_id, "name": "M.Tech. CS", "duration_years": 2},
            headers=admin_headers,
        )
        assert res.status_code == 201
        prog_id = res.json()["data"]["id"]

        # Read list
        res = await client.get("/api/v1/programs", headers=auth_headers)
        assert res.status_code == 200
        assert res.json()["total"] >= 2

        # Update
        res = await client.put(
            f"/api/v1/programs/{prog_id}",
            json={"name": "M.Tech. CSE"},
            headers=admin_headers,
        )
        assert res.status_code == 200
        assert res.json()["data"]["name"] == "M.Tech. CSE"

        # Delete
        res = await client.delete(f"/api/v1/programs/{prog_id}", headers=admin_headers)
        assert res.status_code == 200

    async def test_semester_bounds_and_crud(
        self, client: AsyncClient, admin_headers, auth_headers, base_curriculum
    ):
        prog_id = base_curriculum["prog_id"]

        # Create out of bounds (> 8 sem for 4 years)
        res = await client.post(
            "/api/v1/semesters",
            json={"program_id": prog_id, "number": 9},
            headers=admin_headers,
        )
        assert res.status_code == 422

        # Create duplicate semester
        res = await client.post(
            "/api/v1/semesters",
            json={"program_id": prog_id, "number": 1},
            headers=admin_headers,
        )
        assert res.status_code == 409

        # Create valid semester 2
        res = await client.post(
            "/api/v1/semesters",
            json={"program_id": prog_id, "number": 2},
            headers=admin_headers,
        )
        assert res.status_code == 201
        sem_id = res.json()["data"]["id"]

        # Read list
        res = await client.get(f"/api/v1/semesters?program_id={prog_id}", headers=auth_headers)
        assert res.status_code == 200
        assert len(res.json()["data"]) == 2

        # Update
        res = await client.put(
            f"/api/v1/semesters/{sem_id}",
            json={"number": 3},
            headers=admin_headers,
        )
        assert res.status_code == 200

        # Delete
        res = await client.delete(f"/api/v1/semesters/{sem_id}", headers=admin_headers)
        assert res.status_code == 200


# ── Course CRUD & Validation Tests ─────────────────────────────────────────────
class TestCourseCRUD:
    async def test_course_crud_and_sorting(
        self, client: AsyncClient, admin_headers, auth_headers, base_curriculum
    ):
        sem_id = base_curriculum["sem_id"]

        # Create duplicate code
        res = await client.post(
            "/api/v1/courses",
            json={
                "semester_id": sem_id,
                "course_code": "CS101",
                "course_title": "Duplicate Introduction",
            },
            headers=admin_headers,
        )
        assert res.status_code == 409

        # Create course 2
        res = await client.post(
            "/api/v1/courses",
            json={
                "semester_id": sem_id,
                "course_code": "CS102",
                "course_title": "Data Structures",
                "credits": 4,
            },
            headers=admin_headers,
        )
        assert res.status_code == 201
        course_id = res.json()["data"]["id"]

        # Update
        res = await client.put(
            f"/api/v1/courses/{course_id}",
            json={"credits": 3},
            headers=admin_headers,
        )
        assert res.status_code == 200
        assert res.json()["data"]["credits"] == 3

        # List sorting & pagination
        res = await client.get(
            "/api/v1/courses?sort_by=course_code&sort_order=desc", headers=auth_headers
        )
        assert res.status_code == 200
        assert res.json()["data"][0]["course_code"] == "CS102"

        # Delete
        res = await client.delete(f"/api/v1/courses/{course_id}", headers=admin_headers)
        assert res.status_code == 200


# ── Unit, Topic & Outcome CRUD Tests ───────────────────────────────────────────
class TestUnitTopicOutcome:
    async def test_unit_crud_and_duplicate(
        self, client: AsyncClient, admin_headers, auth_headers, base_curriculum
    ):
        course_id = base_curriculum["course_id"]

        # Duplicate unit number
        res = await client.post(
            "/api/v1/units",
            json={"course_id": course_id, "unit_number": 1, "title": "Unit 1 Copy"},
            headers=admin_headers,
        )
        assert res.status_code == 409

        # Valid create Unit 2
        res = await client.post(
            "/api/v1/units",
            json={"course_id": course_id, "unit_number": 2, "title": "Unit 2"},
            headers=admin_headers,
        )
        assert res.status_code == 201
        unit_id = res.json()["data"]["id"]

        # Update
        res = await client.put(
            f"/api/v1/units/{unit_id}",
            json={"title": "Unit 2 Updated"},
            headers=admin_headers,
        )
        assert res.status_code == 200

        # Delete
        res = await client.delete(f"/api/v1/units/{unit_id}", headers=admin_headers)
        assert res.status_code == 200

    async def test_topic_crud(
        self, client: AsyncClient, admin_headers, auth_headers, base_curriculum
    ):
        unit_id = base_curriculum["unit_id"]

        # Create
        res = await client.post(
            "/api/v1/topics",
            json={"unit_id": unit_id, "topic_name": "Conditionals"},
            headers=admin_headers,
        )
        assert res.status_code == 201
        topic_id = res.json()["data"]["id"]

        # Update
        res = await client.put(
            f"/api/v1/topics/{topic_id}",
            json={"description": "If-else statements"},
            headers=admin_headers,
        )
        assert res.status_code == 200

        # Delete
        res = await client.delete(f"/api/v1/topics/{topic_id}", headers=admin_headers)
        assert res.status_code == 200

    async def test_course_outcome_crud(
        self, client: AsyncClient, admin_headers, auth_headers, base_curriculum
    ):
        course_id = base_curriculum["course_id"]

        # Create
        res = await client.post(
            "/api/v1/course-outcomes",
            json={"course_id": course_id, "co_number": 2, "description": "Write basic functions"},
            headers=admin_headers,
        )
        assert res.status_code == 201
        co_id = res.json()["data"]["id"]

        # Update
        res = await client.put(
            f"/api/v1/course-outcomes/{co_id}",
            json={"description": "Write basic functions in C"},
            headers=admin_headers,
        )
        assert res.status_code == 200

        # Delete
        res = await client.delete(f"/api/v1/course-outcomes/{co_id}", headers=admin_headers)
        assert res.status_code == 200


# ── Topic Mapping Tests ───────────────────────────────────────────────────────
class TestTopicMapping:
    async def test_topic_mapping_crud(
        self, client: AsyncClient, admin_headers, auth_headers, base_curriculum
    ):
        topic_id = base_curriculum["topic_id"]
        co_id = base_curriculum["co_id"]

        # Get Bloom level & Knowledge level IDs
        bloom_res = await client.get("/api/v1/bloom-levels", headers=auth_headers)
        bloom_id = bloom_res.json()["data"][0]["id"]

        knowledge_res = await client.get("/api/v1/knowledge-levels", headers=auth_headers)
        knowledge_id = knowledge_res.json()["data"][0]["id"]

        # Create mapping
        res = await client.post(
            "/api/v1/topic-mappings",
            json={
                "topic_id": topic_id,
                "bloom_level_id": bloom_id,
                "knowledge_level_id": knowledge_id,
                "course_outcome_id": co_id,
            },
            headers=admin_headers,
        )
        assert res.status_code == 201
        mapping_id = res.json()["data"]["id"]

        # Read list
        res = await client.get(f"/api/v1/topic-mappings?topic_id={topic_id}", headers=auth_headers)
        assert res.status_code == 200
        assert len(res.json()["data"]) == 1

        # Delete mapping
        res = await client.delete(f"/api/v1/topic-mappings/{mapping_id}", headers=admin_headers)
        assert res.status_code == 200


# ── CSV Import Tests ──────────────────────────────────────────────────────────
class TestCurriculumImport:
    async def test_csv_import_success(self, client: AsyncClient, admin_headers):
        csv_content = (
            "department_name,department_code,program_name,program_duration,semester_number,course_code,course_title,course_credits,unit_number,unit_title,topic_name,topic_description,bloom_level,knowledge_level,co_number,co_description\n"
            "BioTechnology,BT,B.Tech. BioTech,4,2,BT201,Cell Biology,4,1,Cell Division,Mitosis,Cell cycle mitosis,Understand,Conceptual,1,Understand cells mitosis division\n"
            "BioTechnology,BT,B.Tech. BioTech,4,2,BT201,Cell Biology,4,1,Cell Division,Meiosis,Cell cycle meiosis,Remember,Factual,1,Understand cells mitosis division\n"
        )
        files = {"file": ("curriculum.csv", csv_content, "text/csv")}

        response = await client.post(
            "/api/v1/curriculum/import",
            files=files,
            headers=admin_headers,
        )
        assert response.status_code == 200
        body = response.json()
        assert body["success"] is True
        data = body["data"]
        assert data["rows_processed"] == 2
        assert data["departments_created"] == 1
        assert data["courses_created"] == 1
        assert data["topics_created"] == 2
        assert len(data["errors"]) == 0


# ── Negative ID tests ─────────────────────────────────────────────────────────
class TestNegativeIdLookups:
    async def test_get_invalid_ids(self, client: AsyncClient, auth_headers):
        rand_id = uuid.uuid4()
        endpoints = [
            f"/api/v1/departments/{rand_id}",
            f"/api/v1/programs/{rand_id}",
            f"/api/v1/semesters/{rand_id}",
            f"/api/v1/courses/{rand_id}",
            f"/api/v1/units/{rand_id}",
            f"/api/v1/topics/{rand_id}",
            f"/api/v1/course-outcomes/{rand_id}",
            f"/api/v1/topic-mappings/{rand_id}",
        ]
        for url in endpoints:
            res = await client.get(url, headers=auth_headers)
            assert res.status_code == 404

    async def test_update_invalid_ids(self, client: AsyncClient, admin_headers):
        rand_id = uuid.uuid4()
        # Department
        res = await client.put(
            f"/api/v1/departments/{rand_id}", json={"name": "No"}, headers=admin_headers
        )
        assert res.status_code == 404
        # Program
        res = await client.put(
            f"/api/v1/programs/{rand_id}", json={"name": "No"}, headers=admin_headers
        )
        assert res.status_code == 404
        # Semester
        res = await client.put(
            f"/api/v1/semesters/{rand_id}", json={"number": 2}, headers=admin_headers
        )
        assert res.status_code == 404
        # Course
        res = await client.put(
            f"/api/v1/courses/{rand_id}", json={"course_title": "No"}, headers=admin_headers
        )
        assert res.status_code == 404
        # Unit
        res = await client.put(
            f"/api/v1/units/{rand_id}", json={"title": "No"}, headers=admin_headers
        )
        assert res.status_code == 404
        # Topic
        res = await client.put(
            f"/api/v1/topics/{rand_id}", json={"topic_name": "No"}, headers=admin_headers
        )
        assert res.status_code == 404
        # Course Outcome
        res = await client.put(
            f"/api/v1/course-outcomes/{rand_id}",
            json={"description": "Valid description length"},
            headers=admin_headers,
        )
        assert res.status_code == 404
        # Mapping
        res = await client.put(
            f"/api/v1/topic-mappings/{rand_id}",
            json={"topic_id": str(rand_id)},
            headers=admin_headers,
        )
        assert res.status_code == 404

    async def test_delete_invalid_ids(self, client: AsyncClient, admin_headers):
        rand_id = uuid.uuid4()
        endpoints = [
            f"/api/v1/departments/{rand_id}",
            f"/api/v1/programs/{rand_id}",
            f"/api/v1/semesters/{rand_id}",
            f"/api/v1/courses/{rand_id}",
            f"/api/v1/units/{rand_id}",
            f"/api/v1/topics/{rand_id}",
            f"/api/v1/course-outcomes/{rand_id}",
            f"/api/v1/topic-mappings/{rand_id}",
        ]
        for url in endpoints:
            res = await client.delete(url, headers=admin_headers)
            assert res.status_code == 404
