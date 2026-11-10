import os
from sqlalchemy import create_engine
from sqlalchemy.engine import URL
from sqlalchemy.orm import declarative_base, sessionmaker
from dotenv import load_dotenv, find_dotenv

load_dotenv(find_dotenv())

# Support either full DATABASE_URL or discrete connection parameters
raw_database_url = os.getenv("DATABASE_URL")

if raw_database_url:
    # Ensure psycopg (v3) driver is used with SQLAlchemy
    if raw_database_url.startswith("postgresql://"):
        DATABASE_URL = raw_database_url.replace("postgresql://", "postgresql+psycopg://", 1)
    elif raw_database_url.startswith("postgres://"):
        DATABASE_URL = raw_database_url.replace("postgres://", "postgresql+psycopg://", 1)
    else:
        DATABASE_URL = raw_database_url
else:
    DATABASE_URL = URL.create(
        drivername="postgresql+psycopg",
        username=os.getenv("user"),
        password=os.getenv("password"),
        host=os.getenv("host"),
        port=int(os.getenv("port", "5432")),
        database=os.getenv("dbname", "postgres"),
        query={"sslmode": "require"},
    )

engine = create_engine(DATABASE_URL, pool_pre_ping=True)

SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    autocommit=False,
)

Base = declarative_base()
