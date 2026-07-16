# CampusBot AI — Backend (Phase 3)

> **AI-Powered Academic Content, Assessment & Question Generation System**
> Phase 3: Resource Management & Document Upload

---

## Tech Stack

| Layer | Technology |
|---|---|
| Runtime | Python 3.12 |
| Web Framework | FastAPI 0.115 |
| ORM | SQLAlchemy 2.x (async) |
| Database | PostgreSQL 16 |
| Migrations | Alembic |
| Validation | Pydantic v2 |
| Auth | JWT (python-jose) + bcrypt (passlib) |
| Storage | Local Filesystem Storage (Extensible abstraction layer) |
| Logging | Loguru |
| Testing | pytest + pytest-asyncio + httpx |
| Containerisation | Docker + Docker Compose |
| Linting | Ruff + Black |

---

## Architecture

```
backend/
├── app/
│   ├── api/v1/          # FastAPI route handlers (thin — no business logic)
│   ├── core/            # config, security, logging
│   ├── database/        # SQLAlchemy engine, session, base
│   ├── dependencies/    # FastAPI Depends() helpers (auth guards)
│   ├── exceptions/      # Custom exception classes + global handlers
│   ├── middleware/      # Request logging
│   ├── models/          # SQLAlchemy ORM models (Curriculum, Resource, User)
│   ├── repositories/    # Data-access layer (CurriculumRepo, ResourceRepo)
│   ├── schemas/         # Pydantic request/response models
│   ├── services/        # Business logic (CurriculumService, ResourceService)
│   ├── storage/         # Storage abstraction layer (BaseStorage, LocalStorage)
│   └── main.py          # App factory
├── alembic/             # DB migrations
├── tests/               # pytest test suite
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
└── pyproject.toml
```

---

## Quick Start (Docker Compose)

```bash
# 1. Clone / enter backend directory
cd backend

# 2. Copy environment file
cp .env.example .env
# Edit .env and set strong SECRET_KEY and JWT_SECRET values

# 3. Build and start services (PostgreSQL + FastAPI)
docker compose up --build

# 4. API is live at:
#    http://localhost:8000/docs   — Swagger UI
#    http://localhost:8000/redoc  — ReDoc
#    http://localhost:8000/health — Health check
```

---

## Local Development (without Docker)

```bash
# 1. Create and activate a virtual environment
python -m venv .venv
.venv\Scripts\activate          # Windows
# source .venv/bin/activate     # Linux/macOS

# 2. Install dependencies
pip install -r requirements.txt

# 3. Set up .env (point DATABASE_URL to your local PostgreSQL instance)
cp .env.example .env

# 4. Run migrations
alembic upgrade head

# 5. Start the development server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

---

## Running Tests

```bash
# Install test dependencies (included in requirements.txt)
pip install -r requirements.txt

# Run the full test suite with coverage report
pytest tests/ -v --cov=app --cov-report=term-missing
```

---

## API Endpoints

### Authentication
| Method | Path | Auth | Description |
|---|---|---|---|
| `POST` | `/api/v1/auth/register` | ❌ | Register a new user |
| `POST` | `/api/v1/auth/login` | ❌ | Login and receive JWT tokens |
| `POST` | `/api/v1/auth/refresh` | ❌ | Refresh access token |
| `POST` | `/api/v1/auth/logout` | ✅ Bearer | Log out (client discards tokens) |
| `GET` | `/api/v1/auth/me` | ✅ Bearer | Get current user profile |

### Curriculum Management
| Method | Path | Auth | Description |
|---|---|---|---|
| `POST` | `/api/v1/departments` | ✅ Admin | Create department |
| `GET` | `/api/v1/departments` | ✅ Faculty | List departments |
| `POST` | `/api/v1/programs` | ✅ Admin | Create academic program |
| `POST` | `/api/v1/semesters` | ✅ Admin | Create semester |
| `POST` | `/api/v1/courses` | ✅ Admin | Create course |
| `POST` | `/api/v1/units` | ✅ Faculty | Create unit in course |
| `POST` | `/api/v1/topics` | ✅ Faculty | Create topic in unit |
| `POST` | `/api/v1/course-outcomes` | ✅ Faculty | Create course outcome |
| `POST` | `/api/v1/curriculum/import` | ✅ Faculty | CSV Batch import curriculum |

### Resource Management & Document Upload (Phase 3)
| Method | Path | Auth | Description |
|---|---|---|---|
| `POST` | `/api/v1/resources` | ✅ Faculty | Upload course resource (multipart form) |
| `POST` | `/api/v1/resources/{id}/versions` | ✅ Faculty | Upload new version of a resource |
| `POST` | `/api/v1/resources/{id}/restore` | ✅ Faculty | Restore a previous version to active status |
| `GET` | `/api/v1/resources` | ✅ Faculty | List resources (search, date, paginated) |
| `GET` | `/api/v1/resources/{id}` | ✅ Faculty | View resource details |
| `GET` | `/api/v1/resources/{id}/history` | ✅ Faculty | View version history lineage |
| `GET` | `/api/v1/resources/{id}/download` | ✅ Faculty | Stream resource download as attachment |
| `PUT` | `/api/v1/resources/{id}` | ✅ Faculty | Edit resource title / type / description |
| `DELETE` | `/api/v1/resources/{id}` | ✅ Faculty | Delete resource (Admins delete all; Faculty delete own) |

---

## Storage & Configuration Variables

| Variable | Default Value | Description |
|---|---|---|
| `UPLOAD_DIR` | `uploads` | Target local storage uploads directory |
| `MAX_UPLOAD_SIZE_BYTES` | `10485760` (10MB) | Absolute size limit per file payload |
| `ALLOWED_EXTENSIONS` | `.pdf, .docx, .pptx, .txt` | Allowed document file extensions |
| `ALLOWED_MIME_TYPES` | `application/pdf, ...` | Allowed document mime types |

---

## Code Quality

```bash
# Lint with Ruff
ruff check app/ tests/

# Format with Black
black app/ tests/
```
