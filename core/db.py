import os
from sqlalchemy import create_engine
from sqlalchemy.engine import URL, make_url
from sqlalchemy.orm import declarative_base, sessionmaker
from dotenv import load_dotenv, find_dotenv

load_dotenv(find_dotenv())


def get_env_val(*keys: str, default: str = "") -> str:
    """Helper to retrieve environment variables supporting both DB_UPPERCASE and lowercase naming."""
    for k in keys:
        val = os.getenv(k)
        if val is not None:
            cleaned = val.strip().strip("'\"")
            if cleaned:
                return cleaned
    return default


# Support either full DATABASE_URL or discrete connection parameters
raw_database_url = os.getenv("DATABASE_URL")

if raw_database_url:
    # Ensure psycopg (v3) driver is used with SQLAlchemy
    if raw_database_url.startswith("postgresql://"):
        raw_database_url = raw_database_url.replace("postgresql://", "postgresql+psycopg://", 1)
    elif raw_database_url.startswith("postgres://"):
        raw_database_url = raw_database_url.replace("postgres://", "postgresql+psycopg://", 1)

    try:
        url_obj = make_url(raw_database_url)
        # Ensure database is 'postgres' on Supabase
        if url_obj.host and "supabase" in url_obj.host.lower() and url_obj.database != "postgres":
            print(f"[DB] Supabase database name auto-corrected from '{url_obj.database}' to 'postgres'.")
            url_obj = url_obj.set(database="postgres")
        DATABASE_URL = url_obj
    except Exception:
        DATABASE_URL = raw_database_url
else:
    db_user = get_env_val("DB_USER", "user")
    db_password = get_env_val("DB_PASSWORD", "password")
    db_host = get_env_val("DB_HOST", "host")
    db_port_str = get_env_val("DB_PORT", "port", default="5432")
    db_port = int(db_port_str) if db_port_str.isdigit() else 5432
    db_name = get_env_val("DB_NAME", "dbname", default="postgres")

    
    if not db_name or ("supabase" in db_host.lower() and db_name != "postgres"):
        if db_name and db_name != "postgres":
            print(f"[DB] Supabase database name auto-corrected from '{db_name}' to 'postgres'.")
        db_name = "postgres"

    DATABASE_URL = URL.create(
        drivername="postgresql+psycopg",
        username=db_user,
        password=db_password,
        host=db_host,
        port=db_port,
        database=db_name,
        query={"sslmode": "require"},
    )

engine = create_engine(DATABASE_URL, pool_pre_ping=True)

SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    autocommit=False,
)

Base = declarative_base()
