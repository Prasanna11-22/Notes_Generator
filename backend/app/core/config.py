"""
Application configuration.

All settings are loaded from environment variables / .env file using
Pydantic Settings v2.  No secrets are hard-coded here.
"""

from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Central configuration object loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── Application ─────────────────────────────────────────────────────────
    app_name: str = "CampusBot AI"
    app_version: str = "1.0.0"
    environment: Literal["development", "staging", "production"] = "development"
    debug: bool = False
    api_v1_prefix: str = "/api/v1"

    # ── Database ─────────────────────────────────────────────────────────────
    database_url: str

    # ── Security / JWT ───────────────────────────────────────────────────────
    secret_key: str
    jwt_secret: str
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 7

    # ── CORS ─────────────────────────────────────────────────────────────────
    allowed_origins: str = "http://localhost:3000"
    allowed_hosts: str = "localhost,127.0.0.1"

    # ── Logging ──────────────────────────────────────────────────────────────
    log_level: str = "INFO"
    log_dir: str = "logs"

    # ── Uploads & Storage ───────────────────────────────────────────────────
    upload_dir: str = "uploads"
    max_upload_size_bytes: int = 10 * 1024 * 1024  # 10MB
    allowed_extensions: set[str] = {".pdf", ".docx", ".pptx", ".txt"}
    allowed_mime_types: set[str] = {
        "application/pdf",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "application/vnd.openxmlformats-officedocument.presentationml.presentation",
        "text/plain",
    }

    # ── Document Processing ──────────────────────────────────────────────────
    # Minimum text character threshold to decide a PDF page is "digital" vs
    # scanned.  Pages with fewer chars than this are treated as image-only.
    pdf_min_chars_per_page: int = 20
    # Maximum bytes a single cleaned_text column may hold (PostgreSQL TEXT is
    # unlimited, but we guard against gigantic documents in service layer).
    max_extracted_text_bytes: int = 50 * 1024 * 1024  # 50 MB

    # ── Semantic Chunking ────────────────────────────────────────────────────
    chunk_strategy: Literal["spacy", "nltk", "regex"] = "spacy"
    chunk_size: int = 1000
    chunk_overlap: int = 200
    min_chunk_char_length: int = 100
    max_chunk_char_length: int = 4000
    spacy_model: str = "en_core_web_sm"
    near_duplicate_similarity_threshold: float = 0.95

    # ── Enterprise Embedding Pipeline ─────────────────────────────────────────
    embedding_provider: str = "bge"
    embedding_model: str = "BAAI/bge-small-en-v1.5"
    vector_store: str = "faiss"
    batch_size: int = 32
    embedding_dimension: int = 384
    faiss_index_path: str = "faiss_data/faiss_index.bin"

    # ── Enterprise Retriever ──────────────────────────────────────────────────
    retriever_provider: str = "faiss"
    default_retrieval_limit: int = 5
    default_relevance_threshold: float = 0.5

    # ── Enterprise LLM Orchestrator ───────────────────────────────────────────
    llm_provider: str = "ollama"
    ollama_host: str = "http://localhost:11434"
    llm_model: str = "gemma3:4b"
    llm_temperature: float = 0.7
    llm_top_p: float = 0.9
    llm_top_k: int = 40
    llm_max_tokens: int = 4096
    llm_repeat_penalty: float = 1.1
    llm_num_ctx: int = 8192
    llm_max_retries: int = 3
    llm_timeout_seconds: float = 60.0

    # ── Derived helpers ───────────────────────────────────────────────────────
    @property
    def allowed_origins_list(self) -> list[str]:
        """Return CORS origins as a list."""
        return [o.strip() for o in self.allowed_origins.split(",") if o.strip()]

    @property
    def allowed_hosts_list(self) -> list[str]:
        """Return trusted hosts as a list."""
        return [h.strip() for h in self.allowed_hosts.split(",") if h.strip()]

    @property
    def is_production(self) -> bool:
        return self.environment == "production"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """
    Return a cached singleton Settings instance.

    Using ``lru_cache`` ensures the .env file is only read once for the
    lifetime of the process, which improves performance and avoids
    repeated I/O.
    """
    return Settings()


# Module-level singleton for convenience imports
settings = get_settings()
