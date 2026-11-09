"""Pytest fixtures and isolated in-memory test database setup using canonical model."""

import asyncio
from datetime import date
from typing import AsyncGenerator
import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import StaticPool

from api.db import get_db_session
from api.main import app
from api.models.scholarship import Base, ScholarshipModel

TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@pytest.fixture(scope="session")
def event_loop():
    """Create an event loop for the test session."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="function")
async def test_engine():
    """Initialize test database engine with isolated schema."""
    engine = create_async_engine(
        TEST_DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield engine

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    await engine.dispose()


@pytest_asyncio.fixture(scope="function")
async def db_session(test_engine) -> AsyncGenerator[AsyncSession, None]:
    """Provide isolated AsyncSession for database operations in tests."""
    session_factory = async_sessionmaker(
        bind=test_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )
    async with session_factory() as session:
        yield session


@pytest_asyncio.fixture(scope="function")
async def seeded_session(db_session: AsyncSession) -> AsyncSession:
    """Pre-seed test database with canonical scholarship records."""
    seed_records = [
        ScholarshipModel(
            id=1,
            name="University of Michigan Scholarships",
            provider="Institution",
            host_country="Michigan, United States",
            degree_level=["Bachelor's", "Master's"],
            eligible_countries=["United States", "International"],
            funding_coverage={"tuition": "Full", "living_stipend": "Full"},
            minimum_cgpa="3.5",
            other_eligibility="Enrolled full-time student",
            deadline=date(2027, 3, 20),
            official_url="https://finaid.umich.edu/types-scholarships",
            description="Comprehensive merit support at University of Michigan.",
            fields_of_study=["Mechatronics Engineering", "Computer Science"],
            is_published=True,
            publication_status="published",
        ),
        ScholarshipModel(
            id=2,
            name="Chevening Scholarships",
            provider="Government",
            host_country="United Kingdom",
            degree_level=["Master's"],
            eligible_countries=["Nigeria", "Ghana", "Kenya"],
            funding_coverage={"tuition": "Full", "living_stipend": "Full"},
            minimum_cgpa="Upper Second-Class (2:1)",
            deadline=date(2026, 11, 5),
            official_url="https://www.chevening.org/scholarships",
            description="UK government flagship master degree scholarship.",
            fields_of_study=["Public Policy", "International Relations"],
            is_published=True,
            publication_status="published",
        ),
        ScholarshipModel(
            id=3,
            name="DAAD Helmut-Schmidt Programme",
            provider="Foundation",
            host_country="Germany",
            degree_level=["Master's"],
            funding_coverage={"tuition": "Partial", "living_stipend": "Monthly allowance"},
            minimum_cgpa="First or Upper Second",
            deadline=date(2027, 8, 31),
            official_url="https://www.daad.de/helmut-schmidt",
            description="Master of Public Policy programme in Germany.",
            fields_of_study=["Development Studies", "Public Policy"],
            is_published=True,
            publication_status="published",
        ),
        ScholarshipModel(
            id=4,
            name="Mastercard Foundation Scholars Programme",
            provider="Foundation",
            host_country="Multiple countries",
            degree_level=["Undergraduate", "Master's"],
            funding_coverage="Fully-funded",
            deadline=date(2027, 1, 12),
            official_url="https://mastercardfdn.org/all/scholars",
            description="Leadership development and academic education.",
            fields_of_study=None,  # No fields specified — tests null handling
            is_published=True,
            publication_status="published",
        ),
        ScholarshipModel(
            id=5,
            name="Secret Internal Draft Scholarship",
            provider="Internal",
            host_country="Unpublished Region",
            funding_coverage={"tuition": "Internal only"},
            deadline=None,
            official_url="https://internal.test/draft",
            description="Internal record that must NEVER appear in public feeds.",
            is_published=False,  # DRAFT
            publication_status="draft",
        ),
    ]

    for item in seed_records:
        db_session.add(item)
    await db_session.commit()

    return db_session


@pytest_asyncio.fixture(scope="function")
async def client(seeded_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """HTTP test client with database dependency override."""
    async def override_get_db_session() -> AsyncGenerator[AsyncSession, None]:
        yield seeded_session

    app.dependency_overrides[get_db_session] = override_get_db_session

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as ac:
        yield ac

    app.dependency_overrides.clear()
