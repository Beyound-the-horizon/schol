"""Tests for database URL normalization, engine options, and production configuration safety."""

import pytest
from pydantic import ValidationError
from api.config import Settings
from api.db import get_engine_options, normalize_database_url


def test_normalize_database_url_postgresql():
    """Verify postgresql conversion and sslmode query stripping for asyncpg."""
    raw_url = "postgresql://postgres:secret@db.project.supabase.co:5432/postgres?sslmode=require"
    normalized = normalize_database_url(raw_url)
    assert normalized.startswith("postgresql+asyncpg://")
    assert "sslmode" not in normalized

    postgres_shorthand = "postgres://user:pass@host:5432/db"
    assert normalize_database_url(postgres_shorthand) == "postgresql+asyncpg://user:pass@host:5432/db"


def test_normalize_database_url_sqlite():
    """Verify sqlite URL conversion for aiosqlite."""
    assert normalize_database_url("sqlite:///./dev.db") == "sqlite+aiosqlite:///./dev.db"
    assert normalize_database_url("sqlite+aiosqlite:///:memory:") == "sqlite+aiosqlite:///:memory:"


def test_get_engine_options_direct_postgresql():
    """Verify engine arguments for direct PostgreSQL include finite timeouts and ssl without disabling statement cache."""
    db_url = "postgresql+asyncpg://user:pass@db.supabase.co:5432/postgres"
    options = get_engine_options(db_url)
    assert "connect_args" in options
    connect_args = options["connect_args"]
    assert connect_args.get("ssl") == "require"
    assert "statement_cache_size" not in connect_args
    assert "statement_cache_size" not in connect_args
    assert "timeout" in connect_args
    assert "command_timeout" in connect_args
    assert options.get("pool_size") is not None
    assert options.get("pool_timeout") is not None


def test_get_engine_options_transaction_pooler():
    """Verify engine arguments for PgBouncer / Transaction pooler (port 6543) disable statement caching."""
    pooler_url = "postgresql+asyncpg://postgres:pass@aws-0-eu-central-1.pooler.supabase.com:6543/postgres"
    options = get_engine_options(pooler_url)
    assert "connect_args" in options
    connect_args = options["connect_args"]
    assert connect_args.get("ssl") == "require"
    assert connect_args.get("statement_cache_size") == 0
    assert "prepared_statement_cache_size" not in connect_args


def test_get_engine_options_sqlite():
    """Verify engine arguments for SQLite."""
    options = get_engine_options("sqlite+aiosqlite:///:memory:")
    assert options["connect_args"] == {"check_same_thread": False}
    assert "pool_size" not in options


def test_production_settings_rejects_default_token():
    """Verify that insecure default ingestion or admin token in production fails fast at startup."""
    with pytest.raises(ValidationError) as exc_info:
        Settings(
            environment="production",
            ingestion_token="dev-secret-ingestion-token-change-me",
            admin_token="strong-custom-production-admin-token-xyz123",
        )
    assert "prohibited in production" in str(exc_info.value).lower()

    with pytest.raises(ValidationError) as exc_info_admin:
        Settings(
            environment="production",
            ingestion_token="strong-custom-production-secret-token-xyz123",
            admin_token="dev-secret-admin-token-change-me",
        )
    assert "prohibited in production" in str(exc_info_admin.value).lower()


def test_production_settings_rejects_empty_token():
    """Verify that empty ingestion or admin token in production fails fast at startup."""
    with pytest.raises(ValidationError) as exc_info:
        Settings(
            environment="production",
            ingestion_token="",
            admin_token="strong-custom-production-admin-token-xyz123",
        )
    assert "prohibited in production" in str(exc_info.value).lower()

    with pytest.raises(ValidationError) as exc_info_admin:
        Settings(
            environment="production",
            ingestion_token="strong-custom-production-secret-token-xyz123",
            admin_token="",
        )
    assert "prohibited in production" in str(exc_info_admin.value).lower()


def test_production_settings_accepts_strong_token():
    """Verify production settings pass with custom secure tokens."""
    s = Settings(
        environment="production",
        ingestion_token="strong-custom-production-secret-token-xyz123",
        admin_token="strong-custom-production-admin-token-xyz123",
    )
    assert s.environment == "production"
    assert s.ingestion_token == "strong-custom-production-secret-token-xyz123"
    assert s.admin_token == "strong-custom-production-admin-token-xyz123"
