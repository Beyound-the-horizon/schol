"""Database connection pool and lifecycle management.

Supports PostgreSQL (via asyncpg for Supabase Cloud) and SQLite
(via aiosqlite for tests and offline local development).
"""

import logging
import re
from typing import AsyncGenerator, Dict, Optional, Tuple
from urllib.parse import parse_qsl, quote, unquote, urlencode, urlsplit, urlunsplit
from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from api.config import settings

logger = logging.getLogger("api.db")

# Global engine and sessionmaker references
_engine: Optional[AsyncEngine] = None
_sessionmaker: Optional[async_sessionmaker[AsyncSession]] = None


def normalize_database_url(url: str) -> str:
    """Normalize database connection URL for SQLAlchemy async drivers.
    
    1. Converts postgres:// or postgresql:// to postgresql+asyncpg://.
    2. Converts sqlite:// to sqlite+aiosqlite://.
    3. Safely percent-encodes unencoded special characters in the password.
    4. Strips 'sslmode' query parameters, as asyncpg does not accept sslmode
       in the URL and expects ssl passed via connect_args instead.
    """
    if not url:
        return ""

    url_str = url.strip()

    # Handle driver scheme conversions
    if url_str.startswith("postgres://"):
        url_str = url_str.replace("postgres://", "postgresql+asyncpg://", 1)
    elif url_str.startswith("postgresql://") and not url_str.startswith("postgresql+asyncpg://"):
        url_str = url_str.replace("postgresql://", "postgresql+asyncpg://", 1)
    elif url_str.startswith("sqlite://") and not url_str.startswith("sqlite+aiosqlite://"):
        url_str = url_str.replace("sqlite://", "sqlite+aiosqlite://", 1)

    # Safely handle passwords with unescaped special characters (@, #, %, !, etc.)
    # Pattern: scheme://user:password@host:port/database?query
    match = re.match(
        r"^(?P<scheme>[a-zA-Z0-9+_]+)://(?P<user>[^:/@]+):(?P<password>.+?)@(?P<rest>[^/@:]+(?::\d+)?(?:/.*)?)$",
        url_str
    )
    if match:
        scheme = match.group("scheme")
        user = match.group("user")
        raw_pw = match.group("password")
        rest = match.group("rest")
        # Ensure password is clean percent-encoded (unquote first in case partially encoded)
        encoded_pw = quote(unquote(raw_pw), safe="")
        url_str = f"{scheme}://{user}:{encoded_pw}@{rest}"

    # For asyncpg, strip sslmode from query parameters to prevent connection errors
    if "asyncpg" in url_str and "?" in url_str:
        parsed = urlsplit(url_str)
        filtered_query = [
            (k, v) for k, v in parse_qsl(parsed.query, keep_blank_values=True)
            if k.lower() != "sslmode"
        ]
        url_str = urlunsplit((
            parsed.scheme,
            parsed.netloc,
            parsed.path,
            urlencode(filtered_query),
            parsed.fragment,
        ))

    return url_str


def get_engine_options(db_url: str) -> Dict[str, object]:
    """Build engine keyword arguments tailored to SQLite or asyncpg PostgreSQL."""
    options: Dict[str, object] = {
        "echo": settings.debug and settings.environment == "development",
        "pool_pre_ping": True,
    }

    if db_url.startswith("sqlite"):
        options["connect_args"] = {"check_same_thread": False}
    else:
        # Detect if connecting via PgBouncer / Transaction pooler (e.g. Supabase port 6543)
        # In transaction pooling mode, prepared statement caching must be disabled (statement_cache_size = 0).
        # For direct PostgreSQL (port 5432), statement caching can be retained unless explicitly configured.
        is_transaction_pooler = ":6543" in db_url or "pooler" in db_url.lower()

        connect_args: Dict[str, object] = {
            "ssl": "require",
            "timeout": settings.db_timeout_seconds,
            "command_timeout": settings.db_timeout_seconds,
        }

        if settings.db_statement_cache_size is not None:
            connect_args["statement_cache_size"] = settings.db_statement_cache_size
        elif is_transaction_pooler:
            connect_args["statement_cache_size"] = 0

        # PostgreSQL / Supabase pooler options
        options.update({
            "pool_size": settings.db_pool_min_size,
            "max_overflow": max(0, settings.db_pool_max_size - settings.db_pool_min_size),
            "pool_timeout": settings.db_timeout_seconds,
            "connect_args": connect_args,
        })

    return options


def get_engine() -> Optional[AsyncEngine]:
    """Retrieve current AsyncEngine instance."""
    return _engine


async def init_db_pool(custom_url: Optional[str] = None) -> None:
    """Initialize database engine and connection pool."""
    global _engine, _sessionmaker

    raw_url = custom_url or settings.database_url
    if not raw_url:
        logger.warning(
            "DATABASE_URL is not set. Database operations will fail until configured."
        )
        return

    db_url = normalize_database_url(raw_url)
    engine_kwargs = get_engine_options(db_url)

    _engine = create_async_engine(db_url, **engine_kwargs)
    _sessionmaker = async_sessionmaker(
        bind=_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )
    logger.info("Database connection engine initialized successfully.")


async def close_db_pool() -> None:
    """Dispose of the database engine and close all connections."""
    global _engine, _sessionmaker
    if _engine is not None:
        await _engine.dispose()
        _engine = None
        _sessionmaker = None
        logger.info("Database connection pool closed.")


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency yielding an async database session."""
    if _sessionmaker is None:
        raise RuntimeError(
            "Database engine is not initialized. Check DATABASE_URL configuration."
        )
    async with _sessionmaker() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise


async def check_db_health() -> Tuple[bool, str]:
    """Verify database connectivity with a lightweight ping query.
    
    Returns:
        (is_healthy, message_or_status)
    """
    if _engine is None:
        return False, "Database engine is not configured (missing DATABASE_URL)"

    try:
        async with _engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        return True, "connected"
    except Exception as exc:
        logger.error("Database health check ping failed: %s", type(exc).__name__)
        return False, f"disconnected: {type(exc).__name__}"
