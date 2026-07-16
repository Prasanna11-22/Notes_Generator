"""
Curriculum Management Service.
"""

import csv
import io
import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.exceptions.custom import ConflictError, NotFoundError, ValidationError
from app.models.curriculum import (
    Course,
    CourseOutcome,
    Department,
    Program,
    Semester,
    Topic,
    TopicMapping,
    Unit,
)
from app.repositories.curriculum import (
    BloomLevelRepository,
    CourseOutcomeRepository,
    CourseRepository,
    DepartmentRepository,
    KnowledgeLevelRepository,
    ProgramRepository,
    SemesterRepository,
    TopicMappingRepository,
    TopicRepository,
    UnitRepository,
)
from app.schemas.curriculum import (
    CourseCreate,
    CourseOutcomeCreate,
    CourseOutcomeUpdate,
    CourseUpdate,
    DepartmentCreate,
    DepartmentUpdate,
    ImportReportItem,
    ProgramCreate,
    ProgramUpdate,
    SemesterCreate,
    SemesterUpdate,
    TopicCreate,
    TopicMappingCreate,
    TopicMappingUpdate,
    TopicUpdate,
    UnitCreate,
    UnitUpdate,
)


class CurriculumService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self.bloom_repo = BloomLevelRepository(session)
        self.knowledge_repo = KnowledgeLevelRepository(session)
        self.dept_repo = DepartmentRepository(session)
        self.prog_repo = ProgramRepository(session)
        self.sem_repo = SemesterRepository(session)
        self.course_repo = CourseRepository(session)
        self.unit_repo = UnitRepository(session)
        self.topic_repo = TopicRepository(session)
        self.co_repo = CourseOutcomeRepository(session)
        self.mapping_repo = TopicMappingRepository(session)

    # ── Department CRUD ───────────────────────────────────────────────────────
    async def create_department(self, payload: DepartmentCreate) -> Department:
        if await self.dept_repo.get_by_code(payload.code):
            raise ConflictError(f"Department with code '{payload.code}' already exists.")
        dept = Department(
            id=uuid.uuid4(), name=payload.name, code=payload.code, description=payload.description
        )
        return await self.dept_repo.create(dept)

    async def update_department(self, dept_id: uuid.UUID, payload: DepartmentUpdate) -> Department:
        dept = await self.dept_repo.get_by_id(dept_id)
        if not dept:
            raise NotFoundError("Department", str(dept_id))

        update_data = payload.model_dump(exclude_unset=True)
        if "code" in update_data and update_data["code"] != dept.code:
            if await self.dept_repo.get_by_code(update_data["code"]):
                raise ConflictError(f"Department with code '{update_data['code']}' already exists.")

        return await self.dept_repo.update(dept, update_data)

    async def get_department(self, dept_id: uuid.UUID) -> Department:
        dept = await self.dept_repo.get_by_id(dept_id)
        if not dept:
            raise NotFoundError("Department", str(dept_id))
        return dept

    async def delete_department(self, dept_id: uuid.UUID) -> None:
        dept = await self.dept_repo.get_by_id(dept_id)
        if not dept:
            raise NotFoundError("Department", str(dept_id))
        await self.dept_repo.delete(dept)

    # ── Program CRUD ──────────────────────────────────────────────────────────
    async def create_program(self, payload: ProgramCreate) -> Program:
        dept = await self.dept_repo.get_by_id(payload.department_id)
        if not dept:
            raise NotFoundError("Department", str(payload.department_id))
        prog = Program(
            id=uuid.uuid4(),
            department_id=payload.department_id,
            name=payload.name,
            duration_years=payload.duration_years,
        )
        return await self.prog_repo.create(prog)

    async def update_program(self, program_id: uuid.UUID, payload: ProgramUpdate) -> Program:
        prog = await self.prog_repo.get_by_id(program_id)
        if not prog:
            raise NotFoundError("Program", str(program_id))

        update_data = payload.model_dump(exclude_unset=True)
        if "department_id" in update_data and update_data["department_id"] != prog.department_id:
            dept = await self.dept_repo.get_by_id(update_data["department_id"])
            if not dept:
                raise NotFoundError("Department", str(update_data["department_id"]))

        return await self.prog_repo.update(prog, update_data)

    async def get_program(self, program_id: uuid.UUID) -> Program:
        prog = await self.prog_repo.get_by_id(program_id)
        if not prog:
            raise NotFoundError("Program", str(program_id))
        return prog

    async def delete_program(self, program_id: uuid.UUID) -> None:
        prog = await self.prog_repo.get_by_id(program_id)
        if not prog:
            raise NotFoundError("Program", str(program_id))
        await self.prog_repo.delete(prog)

    # ── Semester CRUD ─────────────────────────────────────────────────────────
    async def create_semester(self, payload: SemesterCreate) -> Semester:
        prog = await self.prog_repo.get_by_id(payload.program_id)
        if not prog:
            raise NotFoundError("Program", str(payload.program_id))

        max_semesters = prog.duration_years * 2
        if payload.number < 1 or payload.number > max_semesters:
            raise ValidationError(
                f"Invalid semester number {payload.number}. Must be between 1 and {max_semesters} (duration: {prog.duration_years} years)."
            )

        existing = await self.sem_repo.get_by_program_and_number(payload.program_id, payload.number)
        if existing:
            raise ConflictError(f"Semester {payload.number} already exists for this program.")

        sem = Semester(id=uuid.uuid4(), program_id=payload.program_id, number=payload.number)
        return await self.sem_repo.create(sem)

    async def update_semester(self, semester_id: uuid.UUID, payload: SemesterUpdate) -> Semester:
        sem = await self.sem_repo.get_by_id(semester_id)
        if not sem:
            raise NotFoundError("Semester", str(semester_id))

        update_data = payload.model_dump(exclude_unset=True)
        prog_id = update_data.get("program_id", sem.program_id)
        prog = await self.prog_repo.get_by_id(prog_id)
        if not prog:
            raise NotFoundError("Program", str(prog_id))

        number = update_data.get("number", sem.number)
        max_semesters = prog.duration_years * 2
        if number < 1 or number > max_semesters:
            raise ValidationError(
                f"Invalid semester number {number}. Must be between 1 and {max_semesters}."
            )

        if (prog_id != sem.program_id) or (number != sem.number):
            existing = await self.sem_repo.get_by_program_and_number(prog_id, number)
            if existing and existing.id != semester_id:
                raise ConflictError(f"Semester {number} already exists for this program.")

        return await self.sem_repo.update(sem, update_data)

    async def get_semester(self, semester_id: uuid.UUID) -> Semester:
        sem = await self.sem_repo.get_by_id(semester_id)
        if not sem:
            raise NotFoundError("Semester", str(semester_id))
        return sem

    async def delete_semester(self, semester_id: uuid.UUID) -> None:
        sem = await self.sem_repo.get_by_id(semester_id)
        if not sem:
            raise NotFoundError("Semester", str(semester_id))
        await self.sem_repo.delete(sem)

    # ── Course CRUD ───────────────────────────────────────────────────────────
    async def create_course(self, payload: CourseCreate) -> Course:
        sem = await self.sem_repo.get_by_id(payload.semester_id)
        if not sem:
            raise NotFoundError("Semester", str(payload.semester_id))

        if await self.course_repo.get_by_code(payload.course_code):
            raise ConflictError(f"Course with code '{payload.course_code}' already exists.")

        course = Course(
            id=uuid.uuid4(),
            semester_id=payload.semester_id,
            course_code=payload.course_code,
            course_title=payload.course_title,
            credits=payload.credits,
            description=payload.description,
        )
        return await self.course_repo.create(course)

    async def update_course(self, course_id: uuid.UUID, payload: CourseUpdate) -> Course:
        course = await self.course_repo.get_by_id(course_id)
        if not course:
            raise NotFoundError("Course", str(course_id))

        update_data = payload.model_dump(exclude_unset=True)
        if "semester_id" in update_data and update_data["semester_id"] != course.semester_id:
            sem = await self.sem_repo.get_by_id(update_data["semester_id"])
            if not sem:
                raise NotFoundError("Semester", str(update_data["semester_id"]))

        if "course_code" in update_data and update_data["course_code"] != course.course_code:
            if await self.course_repo.get_by_code(update_data["course_code"]):
                raise ConflictError(
                    f"Course with code '{update_data['course_code']}' already exists."
                )

        return await self.course_repo.update(course, update_data)

    async def get_course(self, course_id: uuid.UUID) -> Course:
        course = await self.course_repo.get_by_id(course_id)
        if not course:
            raise NotFoundError("Course", str(course_id))
        return course

    async def delete_course(self, course_id: uuid.UUID) -> None:
        course = await self.course_repo.get_by_id(course_id)
        if not course:
            raise NotFoundError("Course", str(course_id))
        await self.course_repo.delete(course)

    # ── Unit CRUD ─────────────────────────────────────────────────────────────
    async def create_unit(self, payload: UnitCreate) -> Unit:
        course = await self.course_repo.get_by_id(payload.course_id)
        if not course:
            raise NotFoundError("Course", str(payload.course_id))

        if await self.unit_repo.get_by_course_and_number(payload.course_id, payload.unit_number):
            raise ConflictError(f"Unit {payload.unit_number} already exists for this course.")
        if await self.unit_repo.get_by_course_and_title(payload.course_id, payload.title):
            raise ConflictError(
                f"Unit with title '{payload.title}' already exists for this course."
            )

        unit = Unit(
            id=uuid.uuid4(),
            course_id=payload.course_id,
            unit_number=payload.unit_number,
            title=payload.title,
        )
        return await self.unit_repo.create(unit)

    async def update_unit(self, unit_id: uuid.UUID, payload: UnitUpdate) -> Unit:
        unit = await self.unit_repo.get_by_id(unit_id)
        if not unit:
            raise NotFoundError("Unit", str(unit_id))

        update_data = payload.model_dump(exclude_unset=True)
        course_id = update_data.get("course_id", unit.course_id)
        course = await self.course_repo.get_by_id(course_id)
        if not course:
            raise NotFoundError("Course", str(course_id))

        unit_number = update_data.get("unit_number", unit.unit_number)
        title = update_data.get("title", unit.title)

        if (course_id != unit.course_id) or (unit_number != unit.unit_number):
            existing = await self.unit_repo.get_by_course_and_number(course_id, unit_number)
            if existing and existing.id != unit_id:
                raise ConflictError(f"Unit {unit_number} already exists for this course.")

        if (course_id != unit.course_id) or (title != unit.title):
            existing = await self.unit_repo.get_by_course_and_title(course_id, title)
            if existing and existing.id != unit_id:
                raise ConflictError(f"Unit with title '{title}' already exists for this course.")

        return await self.unit_repo.update(unit, update_data)

    async def get_unit(self, unit_id: uuid.UUID) -> Unit:
        unit = await self.unit_repo.get_by_id(unit_id)
        if not unit:
            raise NotFoundError("Unit", str(unit_id))
        return unit

    async def delete_unit(self, unit_id: uuid.UUID) -> None:
        unit = await self.unit_repo.get_by_id(unit_id)
        if not unit:
            raise NotFoundError("Unit", str(unit_id))
        await self.unit_repo.delete(unit)

    # ── Topic CRUD ────────────────────────────────────────────────────────────
    async def create_topic(self, payload: TopicCreate) -> Topic:
        unit = await self.unit_repo.get_by_id(payload.unit_id)
        if not unit:
            raise NotFoundError("Unit", str(payload.unit_id))

        if await self.topic_repo.get_by_unit_and_name(payload.unit_id, payload.topic_name):
            raise ConflictError(f"Topic '{payload.topic_name}' already exists in this unit.")

        topic = Topic(
            id=uuid.uuid4(),
            unit_id=payload.unit_id,
            topic_name=payload.topic_name,
            description=payload.description,
        )
        return await self.topic_repo.create(topic)

    async def update_topic(self, topic_id: uuid.UUID, payload: TopicUpdate) -> Topic:
        topic = await self.topic_repo.get_by_id(topic_id)
        if not topic:
            raise NotFoundError("Topic", str(topic_id))

        update_data = payload.model_dump(exclude_unset=True)
        unit_id = update_data.get("unit_id", topic.unit_id)
        unit = await self.unit_repo.get_by_id(unit_id)
        if not unit:
            raise NotFoundError("Unit", str(unit_id))

        topic_name = update_data.get("topic_name", topic.topic_name)
        if (unit_id != topic.unit_id) or (topic_name != topic.topic_name):
            existing = await self.topic_repo.get_by_unit_and_name(unit_id, topic_name)
            if existing and existing.id != topic_id:
                raise ConflictError(f"Topic '{topic_name}' already exists in this unit.")

        return await self.topic_repo.update(topic, update_data)

    async def get_topic(self, topic_id: uuid.UUID) -> Topic:
        topic = await self.topic_repo.get_by_id(topic_id)
        if not topic:
            raise NotFoundError("Topic", str(topic_id))
        return topic

    async def delete_topic(self, topic_id: uuid.UUID) -> None:
        topic = await self.topic_repo.get_by_id(topic_id)
        if not topic:
            raise NotFoundError("Topic", str(topic_id))
        await self.topic_repo.delete(topic)

    # ── Course Outcome CRUD ───────────────────────────────────────────────────
    async def create_co(self, payload: CourseOutcomeCreate) -> CourseOutcome:
        course = await self.course_repo.get_by_id(payload.course_id)
        if not course:
            raise NotFoundError("Course", str(payload.course_id))

        if await self.co_repo.get_by_course_and_number(payload.course_id, payload.co_number):
            raise ConflictError(
                f"Course Outcome CO{payload.co_number} already exists for this course."
            )

        co = CourseOutcome(
            id=uuid.uuid4(),
            course_id=payload.course_id,
            co_number=payload.co_number,
            description=payload.description,
        )
        return await self.co_repo.create(co)

    async def update_co(self, co_id: uuid.UUID, payload: CourseOutcomeUpdate) -> CourseOutcome:
        co = await self.co_repo.get_by_id(co_id)
        if not co:
            raise NotFoundError("CourseOutcome", str(co_id))

        update_data = payload.model_dump(exclude_unset=True)
        course_id = update_data.get("course_id", co.course_id)
        course = await self.course_repo.get_by_id(course_id)
        if not course:
            raise NotFoundError("Course", str(course_id))

        co_number = update_data.get("co_number", co.co_number)
        if (course_id != co.course_id) or (co_number != co.co_number):
            existing = await self.co_repo.get_by_course_and_number(course_id, co_number)
            if existing and existing.id != co_id:
                raise ConflictError(f"Course Outcome CO{co_number} already exists for this course.")

        return await self.co_repo.update(co, update_data)

    async def get_co(self, co_id: uuid.UUID) -> CourseOutcome:
        co = await self.co_repo.get_by_id(co_id)
        if not co:
            raise NotFoundError("CourseOutcome", str(co_id))
        return co

    async def delete_co(self, co_id: uuid.UUID) -> None:
        co = await self.co_repo.get_by_id(co_id)
        if not co:
            raise NotFoundError("CourseOutcome", str(co_id))
        await self.co_repo.delete(co)

    # ── Topic Mapping CRUD ────────────────────────────────────────────────────
    async def create_mapping(self, payload: TopicMappingCreate) -> TopicMapping:
        topic = await self.topic_repo.get_by_id(payload.topic_id)
        if not topic:
            raise NotFoundError("Topic", str(payload.topic_id))

        bloom = await self.bloom_repo.get_by_id(payload.bloom_level_id)
        if not bloom:
            raise NotFoundError("BloomLevel", str(payload.bloom_level_id))

        knowledge = await self.knowledge_repo.get_by_id(payload.knowledge_level_id)
        if not knowledge:
            raise NotFoundError("KnowledgeLevel", str(payload.knowledge_level_id))

        if payload.course_outcome_id:
            co = await self.co_repo.get_by_id(payload.course_outcome_id)
            if not co:
                raise NotFoundError("CourseOutcome", str(payload.course_outcome_id))

        mapping = TopicMapping(
            id=uuid.uuid4(),
            topic_id=payload.topic_id,
            bloom_level_id=payload.bloom_level_id,
            knowledge_level_id=payload.knowledge_level_id,
            course_outcome_id=payload.course_outcome_id,
        )
        return await self.mapping_repo.create(mapping)

    async def update_mapping(
        self, mapping_id: uuid.UUID, payload: TopicMappingUpdate
    ) -> TopicMapping:
        mapping = await self.mapping_repo.get_by_id(mapping_id)
        if not mapping:
            raise NotFoundError("TopicMapping", str(mapping_id))

        update_data = payload.model_dump(exclude_unset=True)
        if "topic_id" in update_data:
            topic = await self.topic_repo.get_by_id(update_data["topic_id"])
            if not topic:
                raise NotFoundError("Topic", str(update_data["topic_id"]))

        if "bloom_level_id" in update_data:
            bloom = await self.bloom_repo.get_by_id(update_data["bloom_level_id"])
            if not bloom:
                raise NotFoundError("BloomLevel", str(update_data["bloom_level_id"]))

        if "knowledge_level_id" in update_data:
            knowledge = await self.knowledge_repo.get_by_id(update_data["knowledge_level_id"])
            if not knowledge:
                raise NotFoundError("KnowledgeLevel", str(update_data["knowledge_level_id"]))

        if "course_outcome_id" in update_data and update_data["course_outcome_id"] is not None:
            co = await self.co_repo.get_by_id(update_data["course_outcome_id"])
            if not co:
                raise NotFoundError("CourseOutcome", str(update_data["course_outcome_id"]))

        return await self.mapping_repo.update(mapping, update_data)

    async def get_mapping(self, mapping_id: uuid.UUID) -> TopicMapping:
        mapping = await self.mapping_repo.get_by_id(mapping_id)
        if not mapping:
            raise NotFoundError("TopicMapping", str(mapping_id))
        return mapping

    async def delete_mapping(self, mapping_id: uuid.UUID) -> None:
        mapping = await self.mapping_repo.get_by_id(mapping_id)
        if not mapping:
            raise NotFoundError("TopicMapping", str(mapping_id))
        await self.mapping_repo.delete(mapping)

    # ── CSV Import Feature ────────────────────────────────────────────────────
    async def import_from_csv(self, file_content: str) -> ImportReportItem:
        """
        Parse and import curriculum data from a flat CSV structure in a single transaction.
        Returns a detailed report.
        """
        f = io.StringIO(file_content)
        reader = csv.DictReader(f)

        report = ImportReportItem(
            rows_processed=0,
            departments_created=0,
            programs_created=0,
            courses_created=0,
            units_created=0,
            topics_created=0,
            mappings_created=0,
            errors=[],
        )

        # Cache of entities resolved during this import execution to minimize DB roundtrips
        resolved_depts = {}
        resolved_progs = {}
        resolved_sems = {}
        resolved_courses = {}
        resolved_units = {}
        resolved_topics = {}
        resolved_cos = {}

        # Resolve all Bloom levels and Knowledge levels first
        bloom_levels = {b.name.lower(): b.id for b in await self.bloom_repo.get_all()}
        knowledge_levels = {k.name.lower(): k.id for k in await self.knowledge_repo.get_all()}

        for row_index, row in enumerate(reader, start=2):
            report.rows_processed += 1
            try:
                # ── 1. Department ──
                dept_name = row.get("department_name", "").strip()
                dept_code = row.get("department_code", "").strip().upper()
                if not dept_name or not dept_code:
                    report.errors.append(f"Row {row_index}: Missing department name or code.")
                    continue

                if dept_code not in resolved_depts:
                    dept = await self.dept_repo.get_by_code(dept_code)
                    if not dept:
                        dept = Department(id=uuid.uuid4(), name=dept_name, code=dept_code)
                        await self.dept_repo.create(dept)
                        report.departments_created += 1
                    resolved_depts[dept_code] = dept
                else:
                    dept = resolved_depts[dept_code]

                # ── 2. Program ──
                prog_name = row.get("program_name", "").strip()
                prog_duration_str = row.get("program_duration", "").strip()
                if not prog_name:
                    report.errors.append(f"Row {row_index}: Missing program name.")
                    continue
                prog_duration = int(prog_duration_str) if prog_duration_str.isdigit() else 4

                prog_key = (dept.id, prog_name.lower())
                if prog_key not in resolved_progs:
                    # Look up in DB
                    db_progs = await self._session.execute(
                        select(Program).where(
                            Program.department_id == dept.id,
                            func.lower(Program.name) == prog_name.lower(),
                        )
                    )
                    prog = db_progs.scalar_one_or_none()
                    if not prog:
                        prog = Program(
                            id=uuid.uuid4(),
                            department_id=dept.id,
                            name=prog_name,
                            duration_years=prog_duration,
                        )
                        await self.prog_repo.create(prog)
                        report.programs_created += 1
                    resolved_progs[prog_key] = prog
                else:
                    prog = resolved_progs[prog_key]

                # ── 3. Semester ──
                sem_num_str = row.get("semester_number", "").strip()
                if not sem_num_str or not sem_num_str.isdigit():
                    report.errors.append(f"Row {row_index}: Missing or invalid semester number.")
                    continue
                sem_number = int(sem_num_str)

                sem_key = (prog.id, sem_number)
                if sem_key not in resolved_sems:
                    sem = await self.sem_repo.get_by_program_and_number(prog.id, sem_number)
                    if not sem:
                        sem = Semester(id=uuid.uuid4(), program_id=prog.id, number=sem_number)
                        await self.sem_repo.create(sem)
                    resolved_sems[sem_key] = sem
                else:
                    sem = resolved_sems[sem_key]

                # ── 4. Course ──
                course_code = row.get("course_code", "").strip().upper()
                course_title = row.get("course_title", "").strip()
                course_credits_str = row.get("course_credits", "").strip()
                if not course_code or not course_title:
                    report.errors.append(f"Row {row_index}: Missing course code or title.")
                    continue
                course_credits = int(course_credits_str) if course_credits_str.isdigit() else 3

                if course_code not in resolved_courses:
                    course = await self.course_repo.get_by_code(course_code)
                    if not course:
                        course = Course(
                            id=uuid.uuid4(),
                            semester_id=sem.id,
                            course_code=course_code,
                            course_title=course_title,
                            credits=course_credits,
                        )
                        await self.course_repo.create(course)
                        report.courses_created += 1
                    resolved_courses[course_code] = course
                else:
                    course = resolved_courses[course_code]

                # ── 5. Course Outcome (Optional per row, but checked) ──
                co_num_str = row.get("co_number", "").strip()
                co_desc = row.get("co_description", "").strip()
                co = None
                if co_num_str and co_num_str.isdigit() and co_desc:
                    co_number = int(co_num_str)
                    co_key = (course.id, co_number)
                    if co_key not in resolved_cos:
                        co = await self.co_repo.get_by_course_and_number(course.id, co_number)
                        if not co:
                            co = CourseOutcome(
                                id=uuid.uuid4(),
                                course_id=course.id,
                                co_number=co_number,
                                description=co_desc,
                            )
                            await self.co_repo.create(co)
                        resolved_cos[co_key] = co
                    else:
                        co = resolved_cos[co_key]

                # ── 6. Unit ──
                unit_num_str = row.get("unit_number", "").strip()
                unit_title = row.get("unit_title", "").strip()
                if not unit_num_str or not unit_num_str.isdigit() or not unit_title:
                    report.errors.append(f"Row {row_index}: Missing or invalid unit number/title.")
                    continue
                unit_number = int(unit_num_str)

                unit_key = (course.id, unit_number)
                if unit_key not in resolved_units:
                    unit = await self.unit_repo.get_by_course_and_number(course.id, unit_number)
                    if not unit:
                        unit = Unit(
                            id=uuid.uuid4(),
                            course_id=course.id,
                            unit_number=unit_number,
                            title=unit_title,
                        )
                        await self.unit_repo.create(unit)
                        report.units_created += 1
                    resolved_units[unit_key] = unit
                else:
                    unit = resolved_units[unit_key]

                # ── 7. Topic ──
                topic_name = row.get("topic_name", "").strip()
                topic_desc = row.get("topic_description", "").strip()
                if not topic_name:
                    report.errors.append(f"Row {row_index}: Missing topic name.")
                    continue

                topic_key = (unit.id, topic_name.lower())
                if topic_key not in resolved_topics:
                    topic = await self.topic_repo.get_by_unit_and_name(unit.id, topic_name)
                    if not topic:
                        topic = Topic(
                            id=uuid.uuid4(),
                            unit_id=unit.id,
                            topic_name=topic_name,
                            description=topic_desc,
                        )
                        await self.topic_repo.create(topic)
                        report.topics_created += 1
                    resolved_topics[topic_key] = topic
                else:
                    topic = resolved_topics[topic_key]

                # ── 8. Topic Mapping ──
                bloom_name = row.get("bloom_level", "").strip().lower()
                knowledge_name = row.get("knowledge_level", "").strip().lower()

                if bloom_name and knowledge_name:
                    bloom_id = bloom_levels.get(bloom_name)
                    knowledge_id = knowledge_levels.get(knowledge_name)

                    if not bloom_id:
                        report.errors.append(
                            f"Row {row_index}: Invalid Bloom level '{bloom_name}'."
                        )
                        continue
                    if not knowledge_id:
                        report.errors.append(
                            f"Row {row_index}: Invalid Knowledge level '{knowledge_name}'."
                        )
                        continue

                    # Prevent duplicate mapping for same topic/co combination
                    co_id = co.id if co else None
                    existing_mapping = None
                    if co_id:
                        existing_mapping = await self.mapping_repo.get_by_topic_and_outcome(
                            topic.id, co_id
                        )

                    if not existing_mapping:
                        mapping = TopicMapping(
                            id=uuid.uuid4(),
                            topic_id=topic.id,
                            bloom_level_id=bloom_id,
                            knowledge_level_id=knowledge_id,
                            course_outcome_id=co_id,
                        )
                        await self.mapping_repo.create(mapping)
                        report.mappings_created += 1

            except Exception as e:
                report.errors.append(f"Row {row_index}: Unexpected error: {str(e)}")

        return report
