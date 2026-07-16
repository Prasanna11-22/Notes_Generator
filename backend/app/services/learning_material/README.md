# Phase 10 — Enterprise Learning Material Generation Engine

This module is responsible for orchestrating the curriculum-aligned generation of learning materials using retrieved context blocks and the LLM Orchestrator. It applies rigorous educational constraints, ensures topic coverage, implements persistent database-backed caching, and tracks version history.

---

## Directory Structure

```
app/services/learning_material/
├── README.md               # This system documentation file
├── generator_base.py       # Abstract base strategy interface
├── generators.py          # Concrete implementations for all 11 types
├── factory.py             # GenerationStrategyFactory (registry-based)
├── service.py             # Main Orchestration Service
├── validator.py           # Educational & Content Validation Service
├── formatter.py           # Output Formatting Service (HTML/Plain Text/JSON)
├── cache_service.py       # Persistent Caching Service (SHA-256 DB-backed)
└── history_service.py     # Revision History Service
```

---

## Strategy Factory Pattern

Each supported material type is mapped to a dedicated generator class implementing `LearningMaterialGenerator`:
1. `NotesGenerator` ("Topic Notes")
2. `ConceptExplanationGenerator` ("Concept Explanation")
3. `WorkedExampleGenerator` ("Worked Examples")
4. `SummaryGenerator` ("Summary Notes")
5. `RevisionGenerator` ("Revision Notes")
6. `DiscussionGenerator` ("Discussion Questions")
7. `ActivityGenerator` ("Classroom Activities")
8. `LearningObjectiveGenerator` ("Learning Objectives")
9. `KeyTakeawayGenerator` ("Key Takeaways")
10. `CommonMistakeGenerator` ("Common Mistakes")
11. `RealWorldApplicationGenerator` ("Real-world Applications")

The `GenerationStrategyFactory` selects the appropriate generator dynamically using a static map registry, avoiding nested `if-else` blocks.

---

## Pipeline Workflow

```
[Validate Request]
       │
       ▼
[Retrieve Context] ────► Query RetrieverService with Topic & filters
       │
       ▼
[Build Prompt] ────────► Hydrate prompt template via PromptBuilderService
       │
       ▼
[LLM Generation] ──────► Generate text using LLMOrchestratorService
       │
       ▼
[Content Validation] ──► Scan for duplicates, placeholders, and layout
       │
       ▼
[Edu Validation] ──────► Validate topic coverage, CO keywords, Bloom level
       │
       ▼
[Formatting] ──────────► Transform markdown to Markdown/HTML/Plain Text/JSON
       │
       ▼
[Store History] ───────► Log previous iterations in the history JSON array
       │
       ▼
[Cache Write] ─────────► Save generated markdown to persistent cache
       │
       ▼
[Return Response]
```

---

## Educational Validation

- **Bloom Level Validation**: Scans active verbs in the output text to ensure cognitive levels match the target (e.g. "Remember" -> define, recall, list; "Create" -> design, build, formulate).
- **Course Outcome Validation**: Measures text overlap with Course Outcomes description keywords, raising alignment exceptions if there is insufficient coverage.
- **Topic Coverage**: Ensures key terms from the topic name are used within the generated content.
- **Placeholder checks**: Rejects prompts containing leftover `[Insert here]`, `TODO`, or default instruction text.

---

## API Endpoints

| Method | Endpoint | Description | Role Constraint |
|---|---|---|---|
| `POST` | `/api/v1/learning-material/generate` | Generates material based on topic/course parameters. | Faculty+ |
| `POST` | `/api/v1/learning-material/regenerate` | Regenerates material appending faculty preferences. | Faculty+ |
| `POST` | `/api/v1/learning-material/validate` | Runs content validation checks on a text block. | Faculty+ |
| `GET` | `/api/v1/learning-material/{id}` | Retrieves a generated material. | Faculty+ |
| `GET` | `/api/v1/learning-material/history` | Retrieves generation history list for the faculty member. | Faculty+ |
| `DELETE`| `/api/v1/learning-material/{id}` | Deletes a learning material. | Faculty+ |
| `GET` | `/api/v1/learning-material/cache` | Inspects all cached entries in the system. | Faculty+ |
| `DELETE`| `/api/v1/learning-material/cache` | Purges all cache entries. | Faculty+ |
| `GET` | `/api/v1/learning-material/health` | Service operational health check. | Any Auth |
