from datetime import date, datetime

from sqlalchemy import Date, DateTime, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

try:
    from core.db import Base
except ImportError:
    from db import Base


class Scholarship(Base):
    __tablename__ = "scholarships"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

    name: Mapped[str] = mapped_column(Text, nullable=False, index=True)
    provider: Mapped[str | None] = mapped_column(Text)
    host_country: Mapped[str | None] = mapped_column(Text)
    degree_level: Mapped[list | None] = mapped_column(JSONB)
    eligible_countries: Mapped[list | None] = mapped_column(JSONB)
    fields_of_study: Mapped[list | None] = mapped_column(JSONB)

    application_open_date: Mapped[date | None] = mapped_column(Date)
    deadline: Mapped[date | None] = mapped_column(Date)
    deadline_timezone: Mapped[str | None] = mapped_column(Text)

    minimum_cgpa: Mapped[str | None] = mapped_column(Text)
    age_limit: Mapped[str | None] = mapped_column(Text)
    other_eligibility: Mapped[str | None] = mapped_column(Text)

    language_tests: Mapped[dict | list | None] = mapped_column(JSONB)
    funding_coverage: Mapped[dict | list | None] = mapped_column(JSONB)
    award_duration: Mapped[str | None] = mapped_column(Text)
    required_documents: Mapped[list | None] = mapped_column(JSONB)
    essay_requirements: Mapped[dict | list | None] = mapped_column(JSONB)
    referee_requirements: Mapped[dict | list | None] = mapped_column(JSONB)

    application_fee_and_effort: Mapped[str | None] = mapped_column(Text)
    official_url: Mapped[str | None] = mapped_column(Text, unique=True)
    last_verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    ai_guidance: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
