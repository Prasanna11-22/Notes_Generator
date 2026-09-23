"""
Database session management.

Provides:
- Async SQLAlchemy engine
- ``AsyncSession`` factory
- ``get_db()`` FastAPI dependency that yields a session per request
"""

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.config import settings

# ── Engine ──────────────────────────────────────────────────────────────────
engine_kwargs = {
    "echo": settings.debug,
    "pool_pre_ping": True,
}

if not settings.database_url.startswith("sqlite"):
    engine_kwargs["pool_size"] = 10
    engine_kwargs["max_overflow"] = 20

engine = create_async_engine(
    settings.database_url,
    **engine_kwargs
)

# ── Session factory ──────────────────────────────────────────────────────────
AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,  # keep objects accessible after commit
    autoflush=False,
)


# ── FastAPI dependency ───────────────────────────────────────────────────────
async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Yield an ``AsyncSession`` for the duration of a single request.

    The session is committed on success and rolled back + closed on any
    unhandled exception, ensuring the connection is always returned to the
    pool.

    Usage::

        @router.get("/items")
        async def list_items(db: AsyncSession = Depends(get_db)):
            ...
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def seed_lookup_tables() -> None:
    """
    Seed BloomLevel, KnowledgeLevel, Department, Program, Semester, Course, Unit, and Topic tables if they are empty.
    Runs during lifespan startup.
    """
    import uuid
    from sqlalchemy import select
    from app.models.curriculum import (
        BloomLevel, 
        KnowledgeLevel, 
        Department, 
        Program, 
        Semester, 
        Course, 
        Unit, 
        Topic
    )

    async with AsyncSessionLocal() as session:
        try:
            # 1. Seed Bloom levels
            bloom_res = await session.execute(select(BloomLevel))
            if not bloom_res.scalars().all():
                bloom_names = ["Remember", "Understand", "Apply", "Analyze", "Evaluate", "Create"]
                for name in bloom_names:
                    session.add(BloomLevel(id=uuid.uuid4(), name=name))

            # 2. Seed Knowledge levels
            knowledge_res = await session.execute(select(KnowledgeLevel))
            if not knowledge_res.scalars().all():
                knowledge_names = ["Factual", "Conceptual", "Procedural", "Metacognitive"]
                for name in knowledge_names:
                    session.add(KnowledgeLevel(id=uuid.uuid4(), name=name))

            # 3. Seed default Department
            dept_res = await session.execute(select(Department).where(Department.code == "CSE"))
            dept = dept_res.scalar_one_or_none()
            if not dept:
                dept = Department(
                    id=uuid.uuid4(),
                    name="Computer Science & Engineering",
                    code="CSE",
                    description="Department of Computer Science & Engineering"
                )
                session.add(dept)
                
            # Seed another Department
            dept_it_res = await session.execute(select(Department).where(Department.code == "IT"))
            dept_it = dept_it_res.scalar_one_or_none()
            if not dept_it:
                dept_it = Department(
                    id=uuid.uuid4(),
                    name="Information Technology",
                    code="IT",
                    description="Department of Information Technology"
                )
                session.add(dept_it)

            await session.flush()

            # 4. Seed default Program
            prog_res = await session.execute(select(Program).where(Program.name == "B.Tech. Computer Science"))
            prog = prog_res.scalar_one_or_none()
            if not prog:
                prog = Program(
                    id=uuid.uuid4(),
                    department_id=dept.id,
                    name="B.Tech. Computer Science",
                    duration_years=4
                )
                session.add(prog)

            await session.flush()

            # 5. Seed default Semesters (1 to 8)
            semesters_map = {}
            for i in range(1, 9):
                sem_res = await session.execute(
                    select(Semester).where(Semester.program_id == prog.id, Semester.number == i)
                )
                sem = sem_res.scalar_one_or_none()
                if not sem:
                    sem = Semester(
                        id=uuid.uuid4(),
                        program_id=prog.id,
                        number=i
                    )
                    session.add(sem)
                semesters_map[i] = sem

            await session.flush()

            # 6. Seed default Courses
            courses_to_seed = [
                {
                    "code": "CS-301",
                    "title": "Data Structures (CS-301)",
                    "sem": 5,
                    "credits": 4,
                    "units": [
                        {
                            "number": 1,
                            "title": "Unit I: Basics & Trees",
                            "topics": ["Binary Search Trees & Balancing", "Red-Black Tree Insertion rules"]
                        },
                        {
                            "number": 2,
                            "title": "Unit II: Balancing & Graphs",
                            "topics": ["Graph representation & Traversals"]
                        },
                        {
                            "number": 3,
                            "title": "Unit III: Advanced Indexing",
                            "topics": ["B/B+ Trees structure"]
                        }
                    ]
                },
                {
                    "code": "CS-401",
                    "title": "Design & Analysis of Algorithms (CS-401)",
                    "sem": 5,
                    "credits": 4,
                    "units": [
                        {
                            "number": 1,
                            "title": "Unit I: Divide and Conquer",
                            "topics": ["Merge Sort & Quick Sort analysis"]
                        }
                    ]
                },
                {
                    "code": "CS-402",
                    "title": "Computer Networks (CS-402)",
                    "sem": 5,
                    "credits": 3,
                    "units": [
                        {
                            "number": 1,
                            "title": "Unit I: Network Layers",
                            "topics": ["Routing algorithms & Subnetting"]
                        }
                    ]
                },
                {
                    "code": "CS-302",
                    "title": "Database Management Systems (CS-302)",
                    "sem": 5,
                    "credits": 4,
                    "units": [
                        {
                            "number": 1,
                            "title": "Unit I: Relational Algebra",
                            "topics": ["Query optimization & Indexing"]
                        }
                    ]
                }
            ]

            for c_data in courses_to_seed:
                course_res = await session.execute(
                    select(Course).where(Course.course_code == c_data["code"])
                )
                course = course_res.scalar_one_or_none()
                sem_obj = semesters_map[c_data["sem"]]
                if not course:
                    course = Course(
                        id=uuid.uuid4(),
                        semester_id=sem_obj.id,
                        course_code=c_data["code"],
                        course_title=c_data["title"],
                        credits=c_data["credits"],
                        description=f"Course on {c_data['title']}"
                    )
                    session.add(course)
                    await session.flush()
                    
                    # Seed units & topics
                    for u_data in c_data["units"]:
                        unit = Unit(
                            id=uuid.uuid4(),
                            course_id=course.id,
                            unit_number=u_data["number"],
                            title=u_data["title"]
                        )
                        session.add(unit)
                        await session.flush()
                        
                        for t_name in u_data["topics"]:
                            topic = Topic(
                                id=uuid.uuid4(),
                                unit_id=unit.id,
                                topic_name=t_name,
                                description=f"Topic on {t_name}"
                            )
                            session.add(topic)
                
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
