"""Typed application settings using Pydantic Settings."""

from typing import List, Optional, Union
import json
from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Centralized configuration loaded from environment variables."""

    # Environment & Server
    environment: str = "development"
    debug: bool = True
    api_prefix: str = "/api/v1"
    host: str = "0.0.0.0"
    port: int = 8000

    # Database
    # Supports PostgreSQL (Supabase Cloud) via asyncpg or SQLite for tests/offline dev
    database_url: str = ""
    db_pool_min_size: int = 1
    db_pool_max_size: int = 10
    db_timeout_seconds: float = 10.0
    # Optional statement cache size for asyncpg (0 disables for PgBouncer / Transaction pooler)
    db_statement_cache_size: Optional[int] = None

    # CORS Allowlist
    cors_origins: Union[List[str], str] = ["http://localhost:5173", "http://127.0.0.1:5173"]

    # Crawler Ingestion Secret Token
    ingestion_token: str = "dev-secret-ingestion-token-change-me"

    # Administrator Secret Token for Editorial Review & Publishing
    admin_token: str = "dev-secret-admin-token-change-me"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    @model_validator(mode="before")
    @classmethod
    def resolve_database_url_from_integrations(cls, data: object) -> object:
        """Fallback to Vercel/Supabase integration environment variables if DATABASE_URL is not provided."""
        if isinstance(data, dict):
            url = (
                data.get("DATABASE_URL")
                or data.get("database_url")
                or data.get("POSTGRES_URL")
                or data.get("POSTGRES_PRISMA_URL")
                or data.get("POSTGRES_URL_NON_POOLING")
            )
            if url and not data.get("database_url"):
                data["database_url"] = url
        return data

    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, value: Union[str, List[str]]) -> List[str]:
        if isinstance(value, str):
            value = value.strip()
            if value.startswith("[") and value.endswith("]"):
                try:
                    return json.loads(value)
                except Exception:
                    pass
            return [origin.strip() for origin in value.split(",") if origin.strip()]
        return value

    @model_validator(mode="after")
    def validate_production_credentials(self) -> "Settings":
        """Fail fast at startup if insecure credentials are configured in production."""
        if self.environment.lower() == "production":
            if not self.ingestion_token or self.ingestion_token == "dev-secret-ingestion-token-change-me":
                raise ValueError(
                    "Insecure default or empty INGESTION_TOKEN is strictly prohibited in production environment."
                )
            if not self.admin_token or self.admin_token == "dev-secret-admin-token-change-me":
                raise ValueError(
                    "Insecure default or empty ADMIN_TOKEN is strictly prohibited in production environment."
                )
        return self

    @property
    def is_sqlite(self) -> bool:
        return self.database_url.startswith("sqlite")


# Global singleton settings instance
settings = Settings()
