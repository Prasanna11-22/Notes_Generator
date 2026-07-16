"""
Curriculum Management API Routes.
"""

import uuid
from typing import Literal

from fastapi import APIRouter, Depends, File, Query, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.session import get_db
from app.dependencies.auth import AdminUser, FacultyUser
from app.schemas.curriculum import (
    BloomLevelRead,
    CourseCreate,
    CourseOutcomeCreate,
    CourseOutcomeRead,
    CourseOutcomeUpdate,
    CourseRead,
    CourseUpdate,
    DepartmentCreate,
    DepartmentRead,
    DepartmentUpdate,
    ImportReportItem,
    KnowledgeLevelRead,
    ProgramCreate,
    ProgramRead,
    ProgramUpdate,
    SemesterCreate,
    SemesterRead,
    SemesterUpdate,
    TopicCreate,
    TopicMappingCreate,
    TopicMappingRead,
    TopicMappingUpdate,
    TopicRead,
    TopicUpdate,
    UnitCreate,
    UnitRead,
    UnitUpdate,
)
from app.schemas.response import APIResponse, PaginatedResponse
from app.services.curriculum import CurriculumService

router = APIRouter(tags=["Curriculum Management"])


# ── Bloom Levels Lookup (Read-only) ──────────────────────────────────────────
@router.get(
    "/bloom-levels",
    response_model=APIResponse[list[BloomLevelRead]],
    summary="Get all Bloom Taxonomy levels",
)
async def list_bloom_levels(
    _user: FacultyUser,
    db: AsyncSession = Depends(get_db),
) -> APIResponse[list[BloomLevelRead]]:
    service = CurriculumService(db)
    levels = await service.bloom_repo.get_all()
    return APIResponse(
        success=True,
        message="Bloom levels retrieved.",
        data=[BloomLevelRead.model_validate(level) for level in levels],
    )


@router.get(
    "/bloom-levels/{level_id}",
    response_model=APIResponse[BloomLevelRead],
    summary="Get a Bloom level by ID",
)
async def get_bloom_level(
    level_id: uuid.UUID,
    _user: FacultyUser,
    db: AsyncSession = Depends(get_db),
) -> APIResponse[BloomLevelRead]:
    service = CurriculumService(db)
    level = await service.bloom_repo.get_by_id(level_id)
    return APIResponse(
        success=True,
        message="Bloom level retrieved.",
        data=BloomLevelRead.model_validate(level),
    )


# ── Knowledge Levels Lookup (Read-only) ───────────────────────────────────────
@router.get(
    "/knowledge-levels",
    response_model=APIResponse[list[KnowledgeLevelRead]],
    summary="Get all Knowledge levels",
)
async def list_knowledge_levels(
    _user: FacultyUser,
    db: AsyncSession = Depends(get_db),
) -> APIResponse[list[KnowledgeLevelRead]]:
    service = CurriculumService(db)
    levels = await service.knowledge_repo.get_all()
    return APIResponse(
        success=True,
        message="Knowledge levels retrieved.",
        data=[KnowledgeLevelRead.model_validate(k) for k in levels],
    )


@router.get(
    "/knowledge-levels/{level_id}",
    response_model=APIResponse[KnowledgeLevelRead],
    summary="Get a Knowledge level by ID",
)
async def get_knowledge_level(
    level_id: uuid.UUID,
    _user: FacultyUser,
    db: AsyncSession = Depends(get_db),
) -> APIResponse[KnowledgeLevelRead]:
    service = CurriculumService(db)
    level = await service.knowledge_repo.get_by_id(level_id)
    return APIResponse(
        success=True,
        message="Knowledge level retrieved.",
        data=KnowledgeLevelRead.model_validate(level),
    )


# ── Departments ──────────────────────────────────────────────────────────────
@router.post(
    "/departments",
    response_model=APIResponse[DepartmentRead],
    status_code=status.HTTP_201_CREATED,
    summary="Create a new Department (Admin only)",
)
async def create_department(
    payload: DepartmentCreate,
    _admin: AdminUser,
    db: AsyncSession = Depends(get_db),
) -> APIResponse[DepartmentRead]:
    service = CurriculumService(db)
    dept = await service.create_department(payload)
    return APIResponse(
        success=True,
        message="Department created successfully.",
        data=DepartmentRead.model_validate(dept),
    )


@router.get(
    "/departments",
    response_model=PaginatedResponse[DepartmentRead],
    summary="List all Departments",
)
async def list_departments(
    _user: FacultyUser,
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    search: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
) -> PaginatedResponse[DepartmentRead]:
    service = CurriculumService(db)
    depts, total = await service.dept_repo.list_departments(skip=skip, limit=limit, search=search)
    pages = (total + limit - 1) // limit
    return PaginatedResponse(
        success=True,
        message="Departments retrieved successfully.",
        data=[DepartmentRead.model_validate(d) for d in depts],
        total=total,
        page=(skip // limit) + 1,
        per_page=limit,
        pages=pages,
    )


@router.get(
    "/departments/{dept_id}",
    response_model=APIResponse[DepartmentRead],
    summary="Get Department by ID",
)
async def get_department(
    dept_id: uuid.UUID,
    _user: FacultyUser,
    db: AsyncSession = Depends(get_db),
) -> APIResponse[DepartmentRead]:
    service = CurriculumService(db)
    dept = await service.get_department(dept_id)
    return APIResponse(
        success=True,
        message="Department retrieved.",
        data=DepartmentRead.model_validate(dept),
    )


@router.put(
    "/departments/{dept_id}",
    response_model=APIResponse[DepartmentRead],
    summary="Update Department (Admin only)",
)
async def update_department(
    dept_id: uuid.UUID,
    payload: DepartmentUpdate,
    _admin: AdminUser,
    db: AsyncSession = Depends(get_db),
) -> APIResponse[DepartmentRead]:
    service = CurriculumService(db)
    dept = await service.update_department(dept_id, payload)
    return APIResponse(
        success=True,
        message="Department updated successfully.",
        data=DepartmentRead.model_validate(dept),
    )


@router.delete(
    "/departments/{dept_id}",
    response_model=APIResponse[None],
    summary="Delete Department (Admin only)",
)
async def delete_department(
    dept_id: uuid.UUID,
    _admin: AdminUser,
    db: AsyncSession = Depends(get_db),
) -> APIResponse[None]:
    service = CurriculumService(db)
    await service.delete_department(dept_id)
    return APIResponse(
        success=True,
        message="Department deleted successfully.",
        data=None,
    )


# ── Programs ─────────────────────────────────────────────────────────────────
@router.post(
    "/programs",
    response_model=APIResponse[ProgramRead],
    status_code=status.HTTP_201_CREATED,
    summary="Create a new Program (Admin only)",
)
async def create_program(
    payload: ProgramCreate,
    _admin: AdminUser,
    db: AsyncSession = Depends(get_db),
) -> APIResponse[ProgramRead]:
    service = CurriculumService(db)
    prog = await service.create_program(payload)
    return APIResponse(
        success=True,
        message="Program created successfully.",
        data=ProgramRead.model_validate(prog),
    )


@router.get(
    "/programs",
    response_model=PaginatedResponse[ProgramRead],
    summary="List all Programs",
)
async def list_programs(
    _user: FacultyUser,
    department_id: uuid.UUID | None = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    search: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
) -> PaginatedResponse[ProgramRead]:
    service = CurriculumService(db)
    progs, total = await service.prog_repo.list_programs(
        skip=skip, limit=limit, department_id=department_id, search=search
    )
    pages = (total + limit - 1) // limit
    return PaginatedResponse(
        success=True,
        message="Programs retrieved successfully.",
        data=[ProgramRead.model_validate(p) for p in progs],
        total=total,
        page=(skip // limit) + 1,
        per_page=limit,
        pages=pages,
    )


@router.get(
    "/programs/{program_id}",
    response_model=APIResponse[ProgramRead],
    summary="Get Program by ID",
)
async def get_program(
    program_id: uuid.UUID,
    _user: FacultyUser,
    db: AsyncSession = Depends(get_db),
) -> APIResponse[ProgramRead]:
    service = CurriculumService(db)
    prog = await service.get_program(program_id)
    return APIResponse(
        success=True,
        message="Program retrieved.",
        data=ProgramRead.model_validate(prog),
    )


@router.put(
    "/programs/{program_id}",
    response_model=APIResponse[ProgramRead],
    summary="Update Program (Admin only)",
)
async def update_program(
    program_id: uuid.UUID,
    payload: ProgramUpdate,
    _admin: AdminUser,
    db: AsyncSession = Depends(get_db),
) -> APIResponse[ProgramRead]:
    service = CurriculumService(db)
    prog = await service.update_program(program_id, payload)
    return APIResponse(
        success=True,
        message="Program updated successfully.",
        data=ProgramRead.model_validate(prog),
    )


@router.delete(
    "/programs/{program_id}",
    response_model=APIResponse[None],
    summary="Delete Program (Admin only)",
)
async def delete_program(
    program_id: uuid.UUID,
    _admin: AdminUser,
    db: AsyncSession = Depends(get_db),
) -> APIResponse[None]:
    service = CurriculumService(db)
    await service.delete_program(program_id)
    return APIResponse(
        success=True,
        message="Program deleted successfully.",
        data=None,
    )


# ── Semesters ────────────────────────────────────────────────────────────────
@router.post(
    "/semesters",
    response_model=APIResponse[SemesterRead],
    status_code=status.HTTP_201_CREATED,
    summary="Create a new Semester (Admin only)",
)
async def create_semester(
    payload: SemesterCreate,
    _admin: AdminUser,
    db: AsyncSession = Depends(get_db),
) -> APIResponse[SemesterRead]:
    service = CurriculumService(db)
    sem = await service.create_semester(payload)
    return APIResponse(
        success=True,
        message="Semester created successfully.",
        data=SemesterRead.model_validate(sem),
    )


@router.get(
    "/semesters",
    response_model=PaginatedResponse[SemesterRead],
    summary="List all Semesters",
)
async def list_semesters(
    _user: FacultyUser,
    program_id: uuid.UUID | None = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
) -> PaginatedResponse[SemesterRead]:
    service = CurriculumService(db)
    sems, total = await service.sem_repo.list_semesters(
        skip=skip, limit=limit, program_id=program_id
    )
    pages = (total + limit - 1) // limit
    return PaginatedResponse(
        success=True,
        message="Semesters retrieved successfully.",
        data=[SemesterRead.model_validate(s) for s in sems],
        total=total,
        page=(skip // limit) + 1,
        per_page=limit,
        pages=pages,
    )


@router.get(
    "/semesters/{semester_id}",
    response_model=APIResponse[SemesterRead],
    summary="Get Semester by ID",
)
async def get_semester(
    semester_id: uuid.UUID,
    _user: FacultyUser,
    db: AsyncSession = Depends(get_db),
) -> APIResponse[SemesterRead]:
    service = CurriculumService(db)
    sem = await service.get_semester(semester_id)
    return APIResponse(
        success=True,
        message="Semester retrieved.",
        data=SemesterRead.model_validate(sem),
    )


@router.put(
    "/semesters/{semester_id}",
    response_model=APIResponse[SemesterRead],
    summary="Update Semester (Admin only)",
)
async def update_semester(
    semester_id: uuid.UUID,
    payload: SemesterUpdate,
    _admin: AdminUser,
    db: AsyncSession = Depends(get_db),
) -> APIResponse[SemesterRead]:
    service = CurriculumService(db)
    sem = await service.update_semester(semester_id, payload)
    return APIResponse(
        success=True,
        message="Semester updated successfully.",
        data=SemesterRead.model_validate(sem),
    )


@router.delete(
    "/semesters/{semester_id}",
    response_model=APIResponse[None],
    summary="Delete Semester (Admin only)",
)
async def delete_semester(
    semester_id: uuid.UUID,
    _admin: AdminUser,
    db: AsyncSession = Depends(get_db),
) -> APIResponse[None]:
    service = CurriculumService(db)
    await service.delete_semester(semester_id)
    return APIResponse(
        success=True,
        message="Semester deleted successfully.",
        data=None,
    )


# ── Courses ──────────────────────────────────────────────────────────────────
@router.post(
    "/courses",
    response_model=APIResponse[CourseRead],
    status_code=status.HTTP_201_CREATED,
    summary="Create a new Course (Admin only)",
)
async def create_course(
    payload: CourseCreate,
    _admin: AdminUser,
    db: AsyncSession = Depends(get_db),
) -> APIResponse[CourseRead]:
    service = CurriculumService(db)
    course = await service.create_course(payload)
    return APIResponse(
        success=True,
        message="Course created successfully.",
        data=CourseRead.model_validate(course),
    )


@router.get(
    "/courses",
    response_model=PaginatedResponse[CourseRead],
    summary="List all Courses (with search, pagination, and multi-level filters)",
)
async def list_courses(
    _user: FacultyUser,
    semester_id: uuid.UUID | None = Query(None),
    program_id: uuid.UUID | None = Query(None),
    department_id: uuid.UUID | None = Query(None),
    search: str | None = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    sort_by: Literal["course_title", "course_code", "credits"] = Query("course_title"),
    sort_order: Literal["asc", "desc"] = Query("asc"),
    db: AsyncSession = Depends(get_db),
) -> PaginatedResponse[CourseRead]:
    service = CurriculumService(db)
    courses, total = await service.course_repo.list_courses(
        skip=skip,
        limit=limit,
        semester_id=semester_id,
        program_id=program_id,
        department_id=department_id,
        search=search,
        sort_by=sort_by,
        sort_order=sort_order,
    )
    pages = (total + limit - 1) // limit
    return PaginatedResponse(
        success=True,
        message="Courses retrieved successfully.",
        data=[CourseRead.model_validate(c) for c in courses],
        total=total,
        page=(skip // limit) + 1,
        per_page=limit,
        pages=pages,
    )


@router.get(
    "/courses/{course_id}",
    response_model=APIResponse[CourseRead],
    summary="Get Course by ID",
)
async def get_course(
    course_id: uuid.UUID,
    _user: FacultyUser,
    db: AsyncSession = Depends(get_db),
) -> APIResponse[CourseRead]:
    service = CurriculumService(db)
    course = await service.get_course(course_id)
    return APIResponse(
        success=True,
        message="Course retrieved.",
        data=CourseRead.model_validate(course),
    )


@router.put(
    "/courses/{course_id}",
    response_model=APIResponse[CourseRead],
    summary="Update Course (Admin only)",
)
async def update_course(
    course_id: uuid.UUID,
    payload: CourseUpdate,
    _admin: AdminUser,
    db: AsyncSession = Depends(get_db),
) -> APIResponse[CourseRead]:
    service = CurriculumService(db)
    course = await service.update_course(course_id, payload)
    return APIResponse(
        success=True,
        message="Course updated successfully.",
        data=CourseRead.model_validate(course),
    )


@router.delete(
    "/courses/{course_id}",
    response_model=APIResponse[None],
    summary="Delete Course (Admin only)",
)
async def delete_course(
    course_id: uuid.UUID,
    _admin: AdminUser,
    db: AsyncSession = Depends(get_db),
) -> APIResponse[None]:
    service = CurriculumService(db)
    await service.delete_course(course_id)
    return APIResponse(
        success=True,
        message="Course deleted successfully.",
        data=None,
    )


# ── Units ────────────────────────────────────────────────────────────────────
@router.post(
    "/units",
    response_model=APIResponse[UnitRead],
    status_code=status.HTTP_201_CREATED,
    summary="Create a new Unit (Admin only)",
)
async def create_unit(
    payload: UnitCreate,
    _admin: AdminUser,
    db: AsyncSession = Depends(get_db),
) -> APIResponse[UnitRead]:
    service = CurriculumService(db)
    unit = await service.create_unit(payload)
    return APIResponse(
        success=True,
        message="Unit created successfully.",
        data=UnitRead.model_validate(unit),
    )


@router.get(
    "/units",
    response_model=PaginatedResponse[UnitRead],
    summary="List all Units",
)
async def list_units(
    _user: FacultyUser,
    course_id: uuid.UUID | None = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
) -> PaginatedResponse[UnitRead]:
    service = CurriculumService(db)
    units, total = await service.unit_repo.list_units(skip=skip, limit=limit, course_id=course_id)
    pages = (total + limit - 1) // limit
    return PaginatedResponse(
        success=True,
        message="Units retrieved successfully.",
        data=[UnitRead.model_validate(u) for u in units],
        total=total,
        page=(skip // limit) + 1,
        per_page=limit,
        pages=pages,
    )


@router.get(
    "/units/{unit_id}",
    response_model=APIResponse[UnitRead],
    summary="Get Unit by ID",
)
async def get_unit(
    unit_id: uuid.UUID,
    _user: FacultyUser,
    db: AsyncSession = Depends(get_db),
) -> APIResponse[UnitRead]:
    service = CurriculumService(db)
    unit = await service.get_unit(unit_id)
    return APIResponse(
        success=True,
        message="Unit retrieved.",
        data=UnitRead.model_validate(unit),
    )


@router.put(
    "/units/{unit_id}",
    response_model=APIResponse[UnitRead],
    summary="Update Unit (Admin only)",
)
async def update_unit(
    unit_id: uuid.UUID,
    payload: UnitUpdate,
    _admin: AdminUser,
    db: AsyncSession = Depends(get_db),
) -> APIResponse[UnitRead]:
    service = CurriculumService(db)
    unit = await service.update_unit(unit_id, payload)
    return APIResponse(
        success=True,
        message="Unit updated successfully.",
        data=UnitRead.model_validate(unit),
    )


@router.delete(
    "/units/{unit_id}",
    response_model=APIResponse[None],
    summary="Delete Unit (Admin only)",
)
async def delete_unit(
    unit_id: uuid.UUID,
    _admin: AdminUser,
    db: AsyncSession = Depends(get_db),
) -> APIResponse[None]:
    service = CurriculumService(db)
    await service.delete_unit(unit_id)
    return APIResponse(
        success=True,
        message="Unit deleted successfully.",
        data=None,
    )


# ── Topics ───────────────────────────────────────────────────────────────────
@router.post(
    "/topics",
    response_model=APIResponse[TopicRead],
    status_code=status.HTTP_201_CREATED,
    summary="Create a new Topic (Admin only)",
)
async def create_topic(
    payload: TopicCreate,
    _admin: AdminUser,
    db: AsyncSession = Depends(get_db),
) -> APIResponse[TopicRead]:
    service = CurriculumService(db)
    topic = await service.create_topic(payload)
    return APIResponse(
        success=True,
        message="Topic created successfully.",
        data=TopicRead.model_validate(topic),
    )


@router.get(
    "/topics",
    response_model=PaginatedResponse[TopicRead],
    summary="List all Topics",
)
async def list_topics(
    _user: FacultyUser,
    unit_id: uuid.UUID | None = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
) -> PaginatedResponse[TopicRead]:
    service = CurriculumService(db)
    topics, total = await service.topic_repo.list_topics(skip=skip, limit=limit, unit_id=unit_id)
    pages = (total + limit - 1) // limit
    return PaginatedResponse(
        success=True,
        message="Topics retrieved successfully.",
        data=[TopicRead.model_validate(t) for t in topics],
        total=total,
        page=(skip // limit) + 1,
        per_page=limit,
        pages=pages,
    )


@router.get(
    "/topics/{topic_id}",
    response_model=APIResponse[TopicRead],
    summary="Get Topic by ID",
)
async def get_topic(
    topic_id: uuid.UUID,
    _user: FacultyUser,
    db: AsyncSession = Depends(get_db),
) -> APIResponse[TopicRead]:
    service = CurriculumService(db)
    topic = await service.get_topic(topic_id)
    return APIResponse(
        success=True,
        message="Topic retrieved.",
        data=TopicRead.model_validate(topic),
    )


@router.put(
    "/topics/{topic_id}",
    response_model=APIResponse[TopicRead],
    summary="Update Topic (Admin only)",
)
async def update_topic(
    topic_id: uuid.UUID,
    payload: TopicUpdate,
    _admin: AdminUser,
    db: AsyncSession = Depends(get_db),
) -> APIResponse[TopicRead]:
    service = CurriculumService(db)
    topic = await service.update_topic(topic_id, payload)
    return APIResponse(
        success=True,
        message="Topic updated successfully.",
        data=TopicRead.model_validate(topic),
    )


@router.delete(
    "/topics/{topic_id}",
    response_model=APIResponse[None],
    summary="Delete Topic (Admin only)",
)
async def delete_topic(
    topic_id: uuid.UUID,
    _admin: AdminUser,
    db: AsyncSession = Depends(get_db),
) -> APIResponse[None]:
    service = CurriculumService(db)
    await service.delete_topic(topic_id)
    return APIResponse(
        success=True,
        message="Topic deleted successfully.",
        data=None,
    )


# ── Course Outcomes (CO) ──────────────────────────────────────────────────────
@router.post(
    "/course-outcomes",
    response_model=APIResponse[CourseOutcomeRead],
    status_code=status.HTTP_201_CREATED,
    summary="Create a new Course Outcome (Admin only)",
)
async def create_co(
    payload: CourseOutcomeCreate,
    _admin: AdminUser,
    db: AsyncSession = Depends(get_db),
) -> APIResponse[CourseOutcomeRead]:
    service = CurriculumService(db)
    co = await service.create_co(payload)
    return APIResponse(
        success=True,
        message="Course Outcome created successfully.",
        data=CourseOutcomeRead.model_validate(co),
    )


@router.get(
    "/course-outcomes",
    response_model=PaginatedResponse[CourseOutcomeRead],
    summary="List all Course Outcomes",
)
async def list_course_outcomes(
    _user: FacultyUser,
    course_id: uuid.UUID | None = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
) -> PaginatedResponse[CourseOutcomeRead]:
    service = CurriculumService(db)
    cos, total = await service.co_repo.list_course_outcomes(
        skip=skip, limit=limit, course_id=course_id
    )
    pages = (total + limit - 1) // limit
    return PaginatedResponse(
        success=True,
        message="Course Outcomes retrieved successfully.",
        data=[CourseOutcomeRead.model_validate(c) for c in cos],
        total=total,
        page=(skip // limit) + 1,
        per_page=limit,
        pages=pages,
    )


@router.get(
    "/course-outcomes/{co_id}",
    response_model=APIResponse[CourseOutcomeRead],
    summary="Get Course Outcome by ID",
)
async def get_co(
    co_id: uuid.UUID,
    _user: FacultyUser,
    db: AsyncSession = Depends(get_db),
) -> APIResponse[CourseOutcomeRead]:
    service = CurriculumService(db)
    co = await service.get_co(co_id)
    return APIResponse(
        success=True,
        message="Course Outcome retrieved.",
        data=CourseOutcomeRead.model_validate(co),
    )


@router.put(
    "/course-outcomes/{co_id}",
    response_model=APIResponse[CourseOutcomeRead],
    summary="Update Course Outcome (Admin only)",
)
async def update_co(
    co_id: uuid.UUID,
    payload: CourseOutcomeUpdate,
    _admin: AdminUser,
    db: AsyncSession = Depends(get_db),
) -> APIResponse[CourseOutcomeRead]:
    service = CurriculumService(db)
    co = await service.update_co(co_id, payload)
    return APIResponse(
        success=True,
        message="Course Outcome updated successfully.",
        data=CourseOutcomeRead.model_validate(co),
    )


@router.delete(
    "/course-outcomes/{co_id}",
    response_model=APIResponse[None],
    summary="Delete Course Outcome (Admin only)",
)
async def delete_co(
    co_id: uuid.UUID,
    _admin: AdminUser,
    db: AsyncSession = Depends(get_db),
) -> APIResponse[None]:
    service = CurriculumService(db)
    await service.delete_co(co_id)
    return APIResponse(
        success=True,
        message="Course Outcome deleted successfully.",
        data=None,
    )


# ── Topic Mappings ────────────────────────────────────────────────────────────
@router.post(
    "/topic-mappings",
    response_model=APIResponse[TopicMappingRead],
    status_code=status.HTTP_201_CREATED,
    summary="Create a new Topic Mapping (Admin only)",
)
async def create_mapping(
    payload: TopicMappingCreate,
    _admin: AdminUser,
    db: AsyncSession = Depends(get_db),
) -> APIResponse[TopicMappingRead]:
    service = CurriculumService(db)
    mapping = await service.create_mapping(payload)
    return APIResponse(
        success=True,
        message="Topic Mapping created successfully.",
        data=TopicMappingRead.model_validate(mapping),
    )


@router.get(
    "/topic-mappings",
    response_model=PaginatedResponse[TopicMappingRead],
    summary="List all Topic Mappings",
)
async def list_mappings(
    _user: FacultyUser,
    topic_id: uuid.UUID | None = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
) -> PaginatedResponse[TopicMappingRead]:
    service = CurriculumService(db)
    mappings, total = await service.mapping_repo.list_mappings(
        skip=skip, limit=limit, topic_id=topic_id
    )
    pages = (total + limit - 1) // limit
    return PaginatedResponse(
        success=True,
        message="Topic Mappings retrieved successfully.",
        data=[TopicMappingRead.model_validate(m) for m in mappings],
        total=total,
        page=(skip // limit) + 1,
        per_page=limit,
        pages=pages,
    )


@router.get(
    "/topic-mappings/{mapping_id}",
    response_model=APIResponse[TopicMappingRead],
    summary="Get Topic Mapping by ID",
)
async def get_mapping(
    mapping_id: uuid.UUID,
    _user: FacultyUser,
    db: AsyncSession = Depends(get_db),
) -> APIResponse[TopicMappingRead]:
    service = CurriculumService(db)
    mapping = await service.get_mapping(mapping_id)
    return APIResponse(
        success=True,
        message="Topic Mapping retrieved.",
        data=TopicMappingRead.model_validate(mapping),
    )


@router.put(
    "/topic-mappings/{mapping_id}",
    response_model=APIResponse[TopicMappingRead],
    summary="Update Topic Mapping (Admin only)",
)
async def update_mapping(
    mapping_id: uuid.UUID,
    payload: TopicMappingUpdate,
    _admin: AdminUser,
    db: AsyncSession = Depends(get_db),
) -> APIResponse[TopicMappingRead]:
    service = CurriculumService(db)
    mapping = await service.update_mapping(mapping_id, payload)
    return APIResponse(
        success=True,
        message="Topic Mapping updated successfully.",
        data=TopicMappingRead.model_validate(mapping),
    )


@router.delete(
    "/topic-mappings/{mapping_id}",
    response_model=APIResponse[None],
    summary="Delete Topic Mapping (Admin only)",
)
async def delete_mapping(
    mapping_id: uuid.UUID,
    _admin: AdminUser,
    db: AsyncSession = Depends(get_db),
) -> APIResponse[None]:
    service = CurriculumService(db)
    await service.delete_mapping(mapping_id)
    return APIResponse(
        success=True,
        message="Topic Mapping deleted successfully.",
        data=None,
    )


# ── CSV Import ───────────────────────────────────────────────────────────────
@router.post(
    "/curriculum/import",
    response_model=APIResponse[ImportReportItem],
    summary="Import complete curriculum via flat CSV file (Admin only)",
)
async def import_curriculum(
    _admin: AdminUser,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
) -> APIResponse[ImportReportItem]:
    service = CurriculumService(db)
    content_bytes = await file.read()
    content_str = content_bytes.decode("utf-8")
    report = await service.import_from_csv(content_str)
    return APIResponse(
        success=True,
        message="CSV Curriculum Import process finished.",
        data=report,
    )
