"""Crawler ingestion request and response schemas matching core/schemas.py."""

from datetime import date, datetime
from typing import Any, Dict, List, Literal, Optional, Union
from pydantic import BaseModel, ConfigDict, Field, HttpUrl, field_validator


class IngestionItem(BaseModel):
    """Canonical crawler scholarship ingestion payload.
    
    100% compatible with Ayomide's ScholarshipCreate in core/schemas.py,
    retaining all structured academic and eligibility criteria.
    """
    model_config = ConfigDict(extra="ignore")

    name: str = Field(..., min_length=2, max_length=300, description="Scholarship title / name")
    provider: Optional[str] = Field(None, description="Scholarship provider or institution")
    host_country: Optional[str] = Field(None, description="Host country or geographic location")

    degree_level: Optional[List[str]] = Field(None, description="List of eligible degree levels")
    eligible_countries: Optional[List[str]] = Field(None, description="List of eligible nationalities/countries")
    fields_of_study: Optional[List[str]] = Field(None, description="Applicable fields of study")

    application_open_date: Optional[date] = Field(None, description="Application opening date")
    deadline: Optional[date] = Field(None, description="Application closing date")
    deadline_timezone: Optional[str] = Field(None, description="Deadline timezone string")

    minimum_cgpa: Optional[str] = Field(None, description="Minimum CGPA or academic score requirement")
    age_limit: Optional[str] = Field(None, description="Age limit specification")
    other_eligibility: Optional[str] = Field(None, description="Additional eligibility conditions")

    language_tests: Optional[Union[Dict[str, Any], List[Any]]] = Field(
        None, description="Required language test scores"
    )
    funding_coverage: Optional[Union[Dict[str, Any], List[Any], str]] = Field(
        None, description="Structured funding coverage details"
    )
    award_duration: Optional[str] = Field(None, description="Duration of scholarship funding")
    required_documents: Optional[List[str]] = Field(None, description="List of required application documents")
    essay_requirements: Optional[Union[Dict[str, Any], List[Any]]] = Field(
        None, description="Essay prompts and guidelines"
    )
    referee_requirements: Optional[Union[Dict[str, Any], List[Any]]] = Field(
        None, description="Reference letter requirements"
    )

    application_fee_and_effort: Optional[str] = Field(None, description="Application fee and difficulty notes")
    official_url: Optional[Union[HttpUrl, str]] = Field(
        None, description="Canonical official announcement URL (primary deduplication key)"
    )
    last_verified_at: Optional[datetime] = Field(None, description="Crawler verification timestamp")

    # Optional description & visibility override (defaults strictly to False for draft safety)
    description: Optional[str] = Field(None, description="General description or remarks")
    is_published: bool = Field(
        default=False,
        description="Visibility flag. Defaults strictly to false for safety until reviewed.",
    )

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        clean = v.strip() if v else ""
        if len(clean) < 2:
            raise ValueError("name must contain at least 2 non-whitespace characters")
        return clean

    @field_validator("official_url", mode="before")
    @classmethod
    def validate_url(cls, v: Optional[Union[HttpUrl, str]]) -> Optional[str]:
        if v is None:
            return None
        v_str = str(v).strip()
        if not v_str:
            return None
        if not (v_str.startswith("http://") or v_str.startswith("https://")):
            raise ValueError("official_url must start with http:// or https://")
        return v_str


class IngestionRequest(BaseModel):
    """Batch ingestion payload from crawling agent."""

    items: List[IngestionItem] = Field(
        ...,
        min_length=1,
        max_length=500,
        description="Batch of structured scholarships to ingest",
    )


class IngestionItemResult(BaseModel):
    """Per-item processing result."""

    index: int = Field(..., description="Item index in the submitted batch")
    name: str = Field(..., description="Scholarship name")
    status: Literal["created", "updated", "skipped", "rejected"] = Field(
        ..., description="Processing outcome"
    )
    id: Optional[int] = Field(None, description="Scholarship database primary key")
    message: Optional[str] = Field(None, description="Status detail or error message")


class IngestionResponse(BaseModel):
    """Summary response for batch ingestion."""

    status: Literal["completed", "partial_failure", "failed"] = Field(
        ..., description="Overall ingestion outcome"
    )
    total: int = Field(..., description="Total items submitted")
    created: int = Field(default=0, description="Count of newly created records")
    updated: int = Field(default=0, description="Count of updated existing records")
    skipped: int = Field(default=0, description="Count of unchanged existing records")
    rejected: int = Field(default=0, description="Count of rejected invalid records")
    results: List[IngestionItemResult] = Field(
        default_factory=list, description="Per-item outcome items"
    )
