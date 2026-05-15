"""
HireMind Configuration via Pydantic Settings.

All sensitive values are loaded from environment variables or a `.env` file.
"""

from pydantic import Field, PostgresDsn, RedisDsn
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from env / .env file."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── Application ──────────────────────────────────────────
    APP_NAME: str = "HireMind"
    APP_VERSION: str = "0.1.0"
    DEBUG: bool = False
    LOG_LEVEL: str = "INFO"

    # ── PostgreSQL ────────────────────────────────────────────
    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: int = 5432
    POSTGRES_USER: str = "hiremind"
    POSTGRES_PASSWORD: str = "hiremind_dev"
    POSTGRES_DB: str = "hiremind"
    DATABASE_URL: PostgresDsn = Field(
        default="postgresql+asyncpg://hiremind:hiremind_dev@localhost:5432/hiremind",
        description="Async PostgreSQL connection string",
    )
    DB_POOL_SIZE: int = 20
    DB_MAX_OVERFLOW: int = 10

    # ── Redis ────────────────────────────────────────────────
    REDIS_URL: RedisDsn = Field(
        default="redis://localhost:6379/0",
        description="Redis connection for caching & sessions",
    )

    # ── MinIO / S3 ───────────────────────────────────────────
    MINIO_ENDPOINT: str = "localhost:9000"
    MINIO_ACCESS_KEY: str = "minioadmin"
    MINIO_SECRET_KEY: str = "minioadmin"
    MINIO_BUCKET_RESUMES: str = "resumes"
    MINIO_SECURE: bool = False

    # ── JWT Authentication ───────────────────────────────────
    JWT_SECRET_KEY: str = "change-me-in-production"
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    JWT_REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # ── Hermes Agent Integration ─────────────────────────────
    HERMES_AGENT_URL: str = "http://localhost:8648"
    HERMES_AGENT_API_KEY: str = ""
    HERMES_AGENT_MODEL: str = "default"

    # ── File Upload ───────────────────────────────────────────
    UPLOAD_DIR: str = "uploads"
    MAX_UPLOAD_SIZE_MB: int = 20

    # ── OpenAI / LLM ─────────────────────────────────────────
    OPENAI_API_KEY: str = ""
    OPENAI_API_BASE: str = "https://api.openai.com/v1"
    OPENAI_MODEL_RESUME: str = "gpt-4o-mini"
    OPENAI_MODEL_MATCHING: str = "gpt-4o-mini"

    # ── CORS ─────────────────────────────────────────────────
    CORS_ORIGINS: list[str] = Field(
        default=["http://localhost:8648", "http://localhost:3000", "http://localhost:5173"],
        description="Allowed CORS origins",
    )

    # ── Pagination ───────────────────────────────────────────
    DEFAULT_PAGE_SIZE: int = 20
    MAX_PAGE_SIZE: int = 100

    @property
    def async_database_url(self) -> str:
        """Return the async database URL string."""
        return str(self.DATABASE_URL)


settings = Settings()
