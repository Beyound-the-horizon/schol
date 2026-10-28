
from datetime import date, datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, HttpUrl


class ScholarshipCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=2, max_length=300)
    provider: str | None = None
    host_country: str | None = None

    degree_level: list[str] | None = None
    eligible_countries: list[str] | None = None
    fields_of_study: list[str] | None = None

    application_open_date: date | None = None
    deadline: date | None = None
    deadline_timezone: str | None = None

    minimum_cgpa: str | None = None
    age_limit: str | None = None
    other_eligibility: str | None = None

    language_tests: dict[str, Any] | list[Any] | None = None
    funding_coverage: dict[str, Any] | list[Any] | None = None
    award_duration: str | None = None
    required_documents: list[str] | None = None
    essay_requirements: dict[str, Any] | list[Any] | None = None
    referee_requirements: dict[str, Any] | list[Any] | None = None

    application_fee_and_effort: str | None = None
    official_url: HttpUrl | None = None
    last_verified_at: datetime | None = None
