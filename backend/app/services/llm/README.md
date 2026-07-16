# Enterprise LLM Orchestrator Documentation

This module defines the architectural layer responsible for communicating with large language models. It decouples core business logic from specific LLM providers and encapsulates connection retries, streaming delivery, formatting validation, and compliance-grade logging controls.

---

## Architecture

```
Prompt Builder (Phase 8)
    │
    ▼
LLMOrchestratorService (app/services/llm_orchestrator.py)
    │
    ├── LLMProvider (Interface)
    │   └── OllamaProvider (app/ai/providers/llm/ollama.py)
    │
    └── Response Validation (UTF-8, JSON parsing, Markdown check, Truncation)
```

1. **`LLMProvider` (Interface)**: Defines abstract contract operations (`generate`, `generate_stream`, `health_check`, `available_models`, `model_information`, `estimate_cost`, `estimate_tokens`).
2. **`OllamaProvider` (Concrete Adapter)**: Implements calls to local or containerized Ollama services using `httpx.AsyncClient` via `/api/chat`, `/api/tags`, and `/api/show` endpoints.
3. **`LLMOrchestratorService` (Orchestrator)**: Validates input prompts, routes queries to the configured provider, handles failures using exponential backoff retry policies, and validates response formats.

---

## Configuration Settings

The system reads settings via environment variables configured in `app/core/config.py`:

```env
# Configured Provider (ollama / mock / etc.)
LLM_PROVIDER=ollama
OLLAMA_HOST=http://localhost:11434
LLM_MODEL=gemma3:4b

# Model Hyperparameters
LLM_TEMPERATURE=0.7
LLM_TOP_P=0.9
LLM_TOP_K=40
LLM_MAX_TOKENS=4096
LLM_REPEAT_PENALTY=1.1
LLM_NUM_CTX=8192

# Transient Retry Rules
LLM_MAX_RETRIES=3
LLM_TIMEOUT_SECONDS=60.0
```

---

## Response Validation Rules

Every raw response returned from the LLM provider is verified by `validate_response()`:
- **Non-empty check**: Discards whitespace-only or empty responses.
- **UTF-8 check**: Asserts clean byte encoding/decoding.
- **JSON check**: When `require_json=True` (e.g. MCQ generation), asserts the text can be loaded as JSON (automatically stripping markdown fences like ```json).
- **Markdown check**: Asserts all code block fences (` ``` `) are closed.
- **Truncation check**: Inspects the end of text to ensure it doesn't terminate mid-sentence or cut off mid-word.

If any check fails, the orchestrator triggers an automatic retry (up to `LLM_MAX_RETRIES` times) with exponential backoff.

---

## Logging & Security Controls

To ensure student privacy and protect academic intellectual property, **prompts, configurations, and generated contents are never logged**.

Logged variables are limited to execution metrics:
- Provider and Model used
- Request Latency (seconds)
- Tokens Evaluated/Generated
- Retry Counts
- Response Payload Size (bytes)
- Execution Errors / Validation Failures

---

## HTTP Endpoints

| Path | Method | Auth Role | Description |
|---|---|---|---|
| `/api/v1/llm/generate` | `POST` | Faculty+ | Synchronous text generation block |
| `/api/v1/llm/generate-stream` | `POST` | Faculty+ | Streaming text generation |
| `/api/v1/llm/models` | `GET` | Faculty+ | Retrieve pulled provider models |
| `/api/v1/llm/provider` | `GET` | Faculty+ | Retrieve active provider settings |
| `/api/v1/llm/health` | `GET` | Faculty+ | Check Ollama server health |
| `/api/v1/llm/validate` | `POST` | Faculty+ | Utility to validate arbitrary strings |
