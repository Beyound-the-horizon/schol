import os
from sqlalchemy import create_engine
from sqlalchemy.engine import URL, make_url
from sqlalchemy.orm import declarative_base, sessionmaker
from dotenv import load_dotenv, find_dotenv

load_dotenv(find_dotenv())

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
    db_host = (os.getenv("host") or "").strip()
    db_name = (os.getenv("dbname") or "").strip()
    db_port = int((os.getenv("port") or "").strip() or "5432")


    # If a user entered their project name or reference ID as dbname, auto-correct i
    if not db_name or ("supabase" in db_host.lower() and db_name != "postgres"):
        if db_name and db_name != "postgres":
            print(f"[DB] Supabase database name auto-corrected from '{db_name}' to 'postgres'.")
        db_name = "postgres"

    DATABASE_URL = URL.create(
        drivername="postgresql+psycopg",
        username=os.getenv("user"),
        password=os.getenv("password"),
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
