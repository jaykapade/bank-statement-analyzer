"""
Central configuration for the Finance Tracker backend.

Uses pydantic-settings so that:
  - Every field is type-validated and coerced automatically.
  - A .env file in the backend directory is loaded automatically.
  - Missing required values raise a clear ValidationError at startup.
  - IDE autocomplete works on `settings.<field>`.

To override any value, set the corresponding environment variable
(case-insensitive) or add it to backend/.env.
"""

from pydantic import Field, computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        # Load .env first, then .env.local (same convention as Next.js).
        # Later files win — put machine-specific overrides in .env.local.
        # Neither file is required; missing files are silently skipped.
        env_file=(".env", ".env.local"),
        env_file_encoding="utf-8",
        extra="ignore",          # silently ignore unknown env vars
        case_sensitive=False,    # DATABASE_URL and database_url both work
    )

    # ── Database ────────────────────────────────────────────────────────────
    database_url: str = "postgresql://postgres:password@localhost:5432/finance"
    # Set DB_ECHO=true in .env.local to log every SQL statement (very noisy!)
    db_echo: bool = False

    # ── Redis / RQ ──────────────────────────────────────────────────────────
    redis_host: str = "localhost"
    redis_port: int = 6379

    # Max wall-clock seconds a background job may run (30 min default)
    job_timeout_seconds: int = 1800

    # ── MinIO / S3-compatible Storage ────────────────────────────────────────
    minio_endpoint: str = "localhost:9000"
    minio_access_key: str = "minioadmin"
    minio_secret_key: str = "minioadmin"
    bucket_name: str = "bank-statements"

    # ── CORS ─────────────────────────────────────────────────────────────────
    # Comma-separated list of allowed frontend origins.
    frontend_origins: str = "http://localhost:3000,http://127.0.0.1:3000"

    @computed_field  # type: ignore[prop-decorator]
    @property
    def allowed_origins(self) -> list[str]:
        return [o.strip() for o in self.frontend_origins.split(",") if o.strip()]

    # ── Session / Auth ───────────────────────────────────────────────────────
    session_cookie_name: str = "finance_tracker_session"

    # Session lifetime in seconds (7 days default)
    session_max_age_seconds: int = Field(default=60 * 60 * 24 * 7)

    # Set to True in production (requires HTTPS)
    session_cookie_secure: bool = False

    # PBKDF2 iteration count — 600 000 is the 2023 OWASP recommendation
    password_hash_iterations: int = Field(default=600_000, alias="PASSWORD_HASH_ITERATIONS")

    # Minimum password length enforced at registration
    password_min_length: int = 8

    # ── LLM (Ollama) ─────────────────────────────────────────────────────────
    ollama_url: str = "http://localhost:11434/api/generate"
    ollama_model: str = "deepseek-r1:7b"

    # Max characters per extraction chunk (tune to your model's context window)
    llm_max_chunk_chars: int = 3500

    # Max transactions per categorization batch
    llm_categorize_batch_size: int = 8

    # Retry attempts on empty/unparseable LLM output
    llm_retry_attempts: int = 2

    # ── Analysis Cache ───────────────────────────────────────────────────────
    # TTL (seconds) for user-level aggregation endpoints (summary, trend, categories).
    # These are invalidated immediately when a job completes, so 5 min is fine.
    cache_ttl_analysis: int = 5 * 60

    # TTL (seconds) for per-job summary once the job is in a terminal state.
    # Completed job data is immutable so we can cache it much longer.
    cache_ttl_job_summary: int = 60 * 60


# Single shared instance — import this everywhere.
settings = Settings()
