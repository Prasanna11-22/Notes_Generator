"""
Curriculum Management Repositories.
"""

import uuid
from collections.abc import Sequence

from sqlalchemy import and_, func, select

from app.models.curriculum import (
    BloomLevel,
    Course,
    CourseOutcome,
    Department,
    KnowledgeLevel,
    Program,
    Semester,
    Topic,
    TopicMapping,
    Unit,
)
from app.repositories.base import BaseRepository


class BloomLevelRepository(BaseRepository[BloomLevel]):
    model = BloomLevel

    async def get_by_name(self, name: str) -> BloomLevel | None:
        result = await self._session.execute(
            select(BloomLevel).where(func.lower(BloomLevel.name) == name.lower().strip())
        )
        return result.scalar_one_or_none()


class KnowledgeLevelRepository(BaseRepository[KnowledgeLevel]):
    model = KnowledgeLevel

    async def get_by_name(self, name: str) -> KnowledgeLevel | None:
        result = await self._session.execute(
            select(KnowledgeLevel).where(func.lower(KnowledgeLevel.name) == name.lower().strip())
        )
        return result.scalar_one_or_none()


class DepartmentRepository(BaseRepository[Department]):
    model = Department

    async def get_by_code(self, code: str) -> Department | None:
        result = await self._session.execute(
            select(Department).where(func.lower(Department.code) == code.lower().strip())
        )
        return result.scalar_one_or_none()

    async def list_departments(
        self, *, skip: int = 0, limit: int = 100, search: str | None = None
    ) -> tuple[Sequence[Department], int]:
        query = select(Department)
        if search:
            query = query.where(
                (Department.name.ilike(f"%{search}%")) | (Department.code.ilike(f"%{search}%"))
            )

        # Count total
        count_query = select(func.count()).select_from(query.subquery())
        total_result = await self._session.execute(count_query)
        total = total_result.scalar_one()

        # Paginated results
        result = await self._session.execute(query.offset(skip).limit(limit))
        return result.scalars().all(), total


class ProgramRepository(BaseRepository[Program]):
    model = Program

    async def list_programs(
        self,
        *,
        skip: int = 0,
        limit: int = 100,
        department_id: uuid.UUID | None = None,
        search: str | None = None,
    ) -> tuple[Sequence[Program], int]:
        query = select(Program)
        if department_id:
            query = query.where(Program.department_id == department_id)
        if search:
            query = query.where(Program.name.ilike(f"%{search}%"))

        count_query = select(func.count()).select_from(query.subquery())
        total_result = await self._session.execute(count_query)
        total = total_result.scalar_one()

        result = await self._session.execute(query.offset(skip).limit(limit))
        return result.scalars().all(), total


class SemesterRepository(BaseRepository[Semester]):
    model = Semester

    async def get_by_program_and_number(
        self, program_id: uuid.UUID, number: int
    ) -> Semester | None:
        result = await self._session.execute(
            select(Semester).where(
                and_(Semester.program_id == program_id, Semester.number == number)
            )
        )
        return result.scalar_one_or_none()

    async def list_semesters(
        self, *, skip: int = 0, limit: int = 100, program_id: uuid.UUID | None = None
    ) -> tuple[Sequence[Semester], int]:
        query = select(Semester)
        if program_id:
            query = query.where(Semester.program_id == program_id)
        query = query.order_by(Semester.number.asc())

        count_query = select(func.count()).select_from(query.subquery())
        total_result = await self._session.execute(count_query)
        total = total_result.scalar_one()

        result = await self._session.execute(query.offset(skip).limit(limit))
        return result.scalars().all(), total


class CourseRepository(BaseRepository[Course]):
    model = Course

    async def get_by_code(self, course_code: str) -> Course | None:
        result = await self._session.execute(
            select(Course).where(func.lower(Course.course_code) == course_code.lower().strip())
        )
        return result.scalar_one_or_none()

    async def list_courses(
        self,
        *,
        skip: int = 0,
        limit: int = 100,
        semester_id: uuid.UUID | None = None,
        program_id: uuid.UUID | None = None,
        department_id: uuid.UUID | None = None,
        search: str | None = None,
        sort_by: str = "course_title",
        sort_order: str = "asc",
    ) -> tuple[Sequence[Course], int]:
        query = select(Course)

        # Filters
        if semester_id:
            query = query.where(Course.semester_id == semester_id)
        if program_id or department_id:
            # Join for deeper filters
            query = query.join(Semester).join(Program)
            if program_id:
                query = query.where(Program.id == program_id)
            if department_id:
                query = query.where(Program.department_id == department_id)

        # Search
        if search:
            query = query.where(
                (Course.course_title.ilike(f"%{search}%"))
                | (Course.course_code.ilike(f"%{search}%"))
            )

        # Sorting
        sort_col = getattr(Course, sort_by, Course.course_title)
        if sort_order.lower() == "desc":
            query = query.order_by(sort_col.desc())
        else:
            query = query.order_by(sort_col.asc())

        # Count total
        count_query = select(func.count()).select_from(query.subquery())
        total_result = await self._session.execute(count_query)
        total = total_result.scalar_one()

        # Paginated query execution
        result = await self._session.execute(query.offset(skip).limit(limit))
        return result.scalars().all(), total


class UnitRepository(BaseRepository[Unit]):
    model = Unit

    async def get_by_course_and_number(self, course_id: uuid.UUID, unit_number: int) -> Unit | None:
        result = await self._session.execute(
            select(Unit).where(and_(Unit.course_id == course_id, Unit.unit_number == unit_number))
        )
        return result.scalar_one_or_none()

    async def get_by_course_and_title(self, course_id: uuid.UUID, title: str) -> Unit | None:
        result = await self._session.execute(
            select(Unit).where(
                and_(Unit.course_id == course_id, func.lower(Unit.title) == title.lower().strip())
            )
        )
        return result.scalar_one_or_none()

    async def list_units(
        self, *, skip: int = 0, limit: int = 100, course_id: uuid.UUID | None = None
    ) -> tuple[Sequence[Unit], int]:
        query = select(Unit)
        if course_id:
            query = query.where(Unit.course_id == course_id)
        query = query.order_by(Unit.unit_number.asc())

        count_query = select(func.count()).select_from(query.subquery())
        total_result = await self._session.execute(count_query)
        total = total_result.scalar_one()

        result = await self._session.execute(query.offset(skip).limit(limit))
        return result.scalars().all(), total


class TopicRepository(BaseRepository[Topic]):
    model = Topic

    async def get_by_unit_and_name(self, unit_id: uuid.UUID, topic_name: str) -> Topic | None:
        result = await self._session.execute(
            select(Topic).where(
                and_(
                    Topic.unit_id == unit_id,
                    func.lower(Topic.topic_name) == topic_name.lower().strip(),
                )
            )
        )
        return result.scalar_one_or_none()

    async def list_topics(
        self, *, skip: int = 0, limit: int = 100, unit_id: uuid.UUID | None = None
    ) -> tuple[Sequence[Topic], int]:
        query = select(Topic)
        if unit_id:
            query = query.where(Topic.unit_id == unit_id)

        count_query = select(func.count()).select_from(query.subquery())
        total_result = await self._session.execute(count_query)
        total = total_result.scalar_one()

        result = await self._session.execute(query.offset(skip).limit(limit))
        return result.scalars().all(), total


class CourseOutcomeRepository(BaseRepository[CourseOutcome]):
    model = CourseOutcome

    async def get_by_course_and_number(
        self, course_id: uuid.UUID, co_number: int
    ) -> CourseOutcome | None:
        result = await self._session.execute(
            select(CourseOutcome).where(
                and_(CourseOutcome.course_id == course_id, CourseOutcome.co_number == co_number)
            )
        )
        return result.scalar_one_or_none()

    async def list_course_outcomes(
        self, *, skip: int = 0, limit: int = 100, course_id: uuid.UUID | None = None
    ) -> tuple[Sequence[CourseOutcome], int]:
        query = select(CourseOutcome)
        if course_id:
            query = query.where(CourseOutcome.course_id == course_id)
        query = query.order_by(CourseOutcome.co_number.asc())

        count_query = select(func.count()).select_from(query.subquery())
        total_result = await self._session.execute(count_query)
        total = total_result.scalar_one()

        result = await self._session.execute(query.offset(skip).limit(limit))
        return result.scalars().all(), total


class TopicMappingRepository(BaseRepository[TopicMapping]):
    model = TopicMapping

    async def get_by_topic_and_outcome(
        self, topic_id: uuid.UUID, course_outcome_id: uuid.UUID
    ) -> TopicMapping | None:
        result = await self._session.execute(
            select(TopicMapping).where(
                and_(
                    TopicMapping.topic_id == topic_id,
                    TopicMapping.course_outcome_id == course_outcome_id,
                )
            )
        )
        return result.scalar_one_or_none()

    async def list_mappings(
        self, *, skip: int = 0, limit: int = 100, topic_id: uuid.UUID | None = None
    ) -> tuple[Sequence[TopicMapping], int]:
        query = select(TopicMapping)
        if topic_id:
            query = query.where(TopicMapping.topic_id == topic_id)

        count_query = select(func.count()).select_from(query.subquery())
        total_result = await self._session.execute(count_query)
        total = total_result.scalar_one()

        result = await self._session.execute(query.offset(skip).limit(limit))
        return result.scalars().all(), total
