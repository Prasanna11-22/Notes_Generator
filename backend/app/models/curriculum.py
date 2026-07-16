"""
Curriculum Management Database Models.

Entities defined:
- Department
- Program
- Semester
- Course
- Unit
- Topic
- CourseOutcome
- BloomLevel (lookup)
- KnowledgeLevel (lookup)
- TopicMapping (combining topic, bloom level, knowledge level, and course outcome)
"""

import uuid

from sqlalchemy import ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base, TimestampMixin


class BloomLevel(Base):
    """
    Lookup table for Bloom's Taxonomy Cognitive Levels.
    Values: Remember, Understand, Apply, Analyze, Evaluate, Create
    """

    __tablename__ = "bloom_levels"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True
    )
    name: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)

    def __repr__(self) -> str:
        return f"<BloomLevel name={self.name!r}>"


class KnowledgeLevel(Base):
    """
    Lookup table for Knowledge Dimension Levels.
    Values: Factual, Conceptual, Procedural, Metacognitive
    """

    __tablename__ = "knowledge_levels"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True
    )
    name: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)

    def __repr__(self) -> str:
        return f"<KnowledgeLevel name={self.name!r}>"


class Department(Base, TimestampMixin):
    """
    Represents an Academic Department.
    E.g. Computer Science, Mechanical Engineering.
    """

    __tablename__ = "departments"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    code: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    description: Mapped[str | None] = mapped_column(String(1000), nullable=True)

    # Relationships
    programs: Mapped[list["Program"]] = relationship(
        "Program", back_populates="department", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Department code={self.code!r} name={self.name!r}>"


class Program(Base, TimestampMixin):
    """
    Represents a degree or educational program.
    E.g., B.E., B.Tech., M.Tech.
    """

    __tablename__ = "programs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True
    )
    department_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("departments.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    duration_years: Mapped[int] = mapped_column(Integer, nullable=False, default=4)

    # Relationships
    department: Mapped[Department] = relationship("Department", back_populates="programs")
    semesters: Mapped[list["Semester"]] = relationship(
        "Semester", back_populates="program", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Program name={self.name!r}>"


class Semester(Base, TimestampMixin):
    """
    Represents a specific Semester within a Program.
    """

    __tablename__ = "semesters"
    __table_args__ = (UniqueConstraint("program_id", "number", name="uq_program_semester_number"),)

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True
    )
    program_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("programs.id", ondelete="CASCADE"), nullable=False
    )
    number: Mapped[int] = mapped_column(Integer, nullable=False)

    # Relationships
    program: Mapped[Program] = relationship("Program", back_populates="semesters")
    courses: Mapped[list["Course"]] = relationship(
        "Course", back_populates="semester", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Semester number={self.number} program_id={self.program_id}>"


class Course(Base, TimestampMixin):
    """
    Represents an Academic Course.
    E.g. Database Management Systems, Data Structures.
    """

    __tablename__ = "courses"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True
    )
    semester_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("semesters.id", ondelete="CASCADE"), nullable=False
    )
    course_code: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    course_title: Mapped[str] = mapped_column(String(255), nullable=False)
    credits: Mapped[int] = mapped_column(Integer, nullable=False, default=3)
    description: Mapped[str | None] = mapped_column(String(2000), nullable=True)

    # Relationships
    semester: Mapped[Semester] = relationship("Semester", back_populates="courses")
    units: Mapped[list["Unit"]] = relationship(
        "Unit", back_populates="course", cascade="all, delete-orphan"
    )
    course_outcomes: Mapped[list["CourseOutcome"]] = relationship(
        "CourseOutcome", back_populates="course", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Course code={self.course_code!r} title={self.course_title!r}>"


class Unit(Base, TimestampMixin):
    """
    Represents a syllabus Unit within a Course.
    """

    __tablename__ = "units"
    __table_args__ = (
        UniqueConstraint("course_id", "unit_number", name="uq_course_unit_number"),
        UniqueConstraint("course_id", "title", name="uq_course_unit_title"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True
    )
    course_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("courses.id", ondelete="CASCADE"), nullable=False
    )
    unit_number: Mapped[int] = mapped_column(Integer, nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)

    # Relationships
    course: Mapped[Course] = relationship("Course", back_populates="units")
    topics: Mapped[list["Topic"]] = relationship(
        "Topic", back_populates="unit", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Unit number={self.unit_number} title={self.title!r}>"


class Topic(Base, TimestampMixin):
    """
    Represents a specific teaching Topic inside a syllabus Unit.
    """

    __tablename__ = "topics"
    __table_args__ = (UniqueConstraint("unit_id", "topic_name", name="uq_unit_topic_name"),)

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True
    )
    unit_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("units.id", ondelete="CASCADE"), nullable=False
    )
    topic_name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(String(1000), nullable=True)

    # Relationships
    unit: Mapped[Unit] = relationship("Unit", back_populates="topics")
    topic_mappings: Mapped[list["TopicMapping"]] = relationship(
        "TopicMapping", back_populates="topic", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Topic name={self.topic_name!r}>"


class CourseOutcome(Base, TimestampMixin):
    """
    Represents a Course Outcome (CO).
    E.g. CO1: Understand database normalization concepts.
    """

    __tablename__ = "course_outcomes"
    __table_args__ = (UniqueConstraint("course_id", "co_number", name="uq_course_co_number"),)

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True
    )
    course_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("courses.id", ondelete="CASCADE"), nullable=False
    )
    co_number: Mapped[int] = mapped_column(Integer, nullable=False)
    description: Mapped[str] = mapped_column(String(1000), nullable=False)

    # Relationships
    course: Mapped[Course] = relationship("Course", back_populates="course_outcomes")
    topic_mappings: Mapped[list["TopicMapping"]] = relationship(
        "TopicMapping", back_populates="course_outcome", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<CourseOutcome co_number={self.co_number}>"


class TopicMapping(Base, TimestampMixin):
    """
    Associates a Topic with a Bloom Level, Knowledge Level, and Course Outcome.
    """

    __tablename__ = "topic_mappings"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True
    )
    topic_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("topics.id", ondelete="CASCADE"), nullable=False
    )
    bloom_level_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("bloom_levels.id", ondelete="RESTRICT"), nullable=False
    )
    knowledge_level_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("knowledge_levels.id", ondelete="RESTRICT"), nullable=False
    )
    course_outcome_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("course_outcomes.id", ondelete="SET NULL"), nullable=True
    )

    # Relationships
    topic: Mapped[Topic] = relationship("Topic", back_populates="topic_mappings")
    bloom_level: Mapped[BloomLevel] = relationship("BloomLevel")
    knowledge_level: Mapped[KnowledgeLevel] = relationship("KnowledgeLevel")
    course_outcome: Mapped[CourseOutcome | None] = relationship(
        "CourseOutcome", back_populates="topic_mappings"
    )

    def __repr__(self) -> str:
        return f"<TopicMapping topic_id={self.topic_id}>"
