# Phase 11 — Enterprise MCQ Generation Engine

Module handles target cognitive Bloom taxonomy allocations, distractor uniqueness analysis, phrasing duplicate checking, and API endpoints for MCQ generation.

## Component Architecture

```
MCQOrchestratorService
  ├── AssessmentBlueprintService (Largest Remainder Method allocation)
  ├── GenerationStrategyFactory (Resolves Bloom level to strategy generator)
  ├── MCQValidator (Basic layouts, verb alignment, Course Outcomes keyword mapping)
  ├── DistractorAnalyzer (Verify distractor unique choices and plausibility)
  ├── DifficultyCalibrator (Sentence length and Bloom verb calibration)
  └── MCQDuplicateDetector (Wording similarity overlap checking)
```

## Setup & Execution

### 1. Database Migrations
Verify migration is applied:
```bash
python -m alembic upgrade head
```

### 2. Running Test Suite
Execute the Phase 11 test suite:
```bash
python -m pytest tests/test_mcq.py -v
```

## REST API Endpoints

- `POST /api/v1/mcq/generate`: Generate curriculum-aligned MCQs from blueprint.
- `POST /api/v1/mcq/regenerate`: Overwrite/regenerate a single question with history version logs.
- `POST /api/v1/mcq/validate`: Manually run alignment check on custom MCQs.
- `GET /api/v1/mcq/history`: List generation history for current Faculty user.
- `GET /api/v1/mcq/{id}`: View question stem and option metadata details.
- `DELETE /api/v1/mcq/{id}`: Wipe question from database.
- `GET /api/v1/mcq/health`: Heartbeat check of the MCQ Generation module.
