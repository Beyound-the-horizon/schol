"""Scholarship Pydantic schemas and deterministic projection models.

Provides frontend-compatible response schemas for listing cards, detailed view,
and pagination/stats envelopes while preserving underlying canonical models.
"""

from datetime import date, datetime
from typing import Any, Dict, List, Optional, Union
from pydantic import BaseModel, ConfigDict, Field, field_serializer

from api.normalization import (
    classify_organization,
    derive_eligibility_detail,
    derive_location,
    derive_offer,
    derive_organization,
    extract_benefits,
    extract_document_requirements,
    extract_english,
    extract_motivation,
    extract_recommendations,
    extract_stipend,
    extract_work_experience,
    format_deadline_dates,
)


def format_calendar_date(d: Optional[Union[date, datetime, str]]) -> Optional[str]:
    """Format calendar date to YYYY-MM-DD string without timezone offset shifts."""
    if d is None:
        return None
    if isinstance(d, datetime):
        return d.date().isoformat()
    if isinstance(d, date):
        return d.isoformat()
    s = str(d).strip()
    return s[:10] if len(s) >= 10 and s[4] == "-" and s[7] == "-" else s


def derive_eligibility_summary(
    minimum_cgpa: Optional[str] = None,
    degree_level: Optional[Union[List[str], Any]] = None,
    age_limit: Optional[str] = None,
    other_eligibility: Optional[str] = None,
    eligible_countries: Optional[Union[List[str], Any]] = None,
) -> str:
    """Synthesize concise eligibility summary for listing cards."""
    clauses: List[str] = []

    if minimum_cgpa and str(minimum_cgpa).strip():
        clauses.append(f"Min CGPA: {str(minimum_cgpa).strip()}")

    if degree_level:
        if isinstance(degree_level, list) and degree_level:
            clauses.append(f"Degree: {', '.join(str(d) for d in degree_level[:2])}")
        elif isinstance(degree_level, str) and degree_level.strip():
            clauses.append(f"Degree: {degree_level.strip()}")

    if not clauses and eligible_countries:
        if isinstance(eligible_countries, list) and len(eligible_countries) <= 3:
            clauses.append(f"Countries: {', '.join(str(c) for c in eligible_countries)}")
        elif isinstance(eligible_countries, list):
            clauses.append(f"{len(eligible_countries)} eligible countries")

    if not clauses and other_eligibility and other_eligibility.strip():
        snippet = other_eligibility.strip()
        clauses.append(snippet[:50] + ("..." if len(snippet) > 50 else ""))

    return " | ".join(clauses) if clauses else "See requirements in announcement"


# Backward-compatible function aliases for existing test suites
derive_eligibility = derive_eligibility_summary


class DocumentRequirementSchema(BaseModel):
    """Structured document requirement specification."""
    name: str
    formats: List[str] = Field(default_factory=list)
    maxSize: str = ""


class ScholarshipRead(BaseModel):
    """Stable public scholarship representation strictly adhering to frontend 7 fields plus course scope."""

    id: int = Field(..., description="Unique scholarship identifier")
    name: str = Field(..., description="Scholarship title / award name")
    provider: Optional[str] = Field(None, description="Raw provider / institution name preserved separately")
    location: str = Field(..., description="Geographic location or host country")
    organization: str = Field(..., description="Provider category ('Institution' | 'Organization' | 'Foundation' | 'Government')")
    offer: str = Field(..., description="Funding coverage ('Fully-funded' | 'Partial' | descriptive)")
    eligibility: str = Field(..., description="Eligibility criteria summary badge")
    deadline: Optional[str] = Field(
        None,
        description="ISO 8601 calendar date (YYYY-MM-DD), or null if rolling/unknown",
    )
    display_deadline: Optional[str] = Field(
        None,
        description="Formatted display deadline (e.g. '20th March 3mo' or 'Rolling / Open')",
    )
    courses: Optional[List[str]] = Field(
        None,
        description="Degree programs or disciplines for institutional awards",
    )
    focusAreas: Optional[List[str]] = Field(
        None,
        description="Thematic disciplines or focus areas for non-institutional awards",
    )

    model_config = ConfigDict(from_attributes=True)

    @field_serializer("deadline", mode="plain")
    def serialize_deadline(self, v: Optional[Union[str, date]]) -> Optional[str]:
        return format_calendar_date(v)

    @classmethod
    def from_model(cls, model: Any) -> "ScholarshipRead":
        """Project canonical database model into frontend 7-field listing card."""
        raw_deadline = getattr(model, "deadline", None)
        short_dl, _, _ = format_deadline_dates(raw_deadline)

        raw_provider = getattr(model, "provider", None)
        org_kind = classify_organization(raw_provider)

        raw_fields = getattr(model, "fields_of_study", None)
        fields_list: Optional[List[str]] = None
        if isinstance(raw_fields, list):
            fields_list = [str(f).strip() for f in raw_fields if str(f).strip()] or None
        elif isinstance(raw_fields, str) and raw_fields.strip():
            fields_list = [raw_fields.strip()]

        return cls(
            id=model.id,
            name=model.name,
            provider=raw_provider,
            location=derive_location(getattr(model, "host_country", None)),
            organization=org_kind,
            offer=derive_offer(getattr(model, "funding_coverage", None)),
            eligibility=derive_eligibility_summary(
                minimum_cgpa=getattr(model, "minimum_cgpa", None),
                degree_level=getattr(model, "degree_level", None),
                age_limit=getattr(model, "age_limit", None),
                other_eligibility=getattr(model, "other_eligibility", None),
                eligible_countries=getattr(model, "eligible_countries", None),
            ),
            deadline=format_calendar_date(raw_deadline),
            display_deadline=short_dl or "Rolling / Open",
            courses=fields_list if org_kind == "Institution" else None,
            focusAreas=fields_list if org_kind != "Institution" else None,
        )


class ScholarshipDetail(ScholarshipRead):
    """Detailed scholarship response containing all 24 UI fields and canonical fields."""

    # UI-specific detail view fields
    source: Optional[str] = Field("Url", description="Source indicator label")
    official_url: Optional[str] = Field(None, description="Official portal URL for 'Apply' button")
    deadlineDate: Optional[str] = Field(None, description="Formatted deadline date (e.g. '20th March, 2027')")
    daysLeft: Optional[str] = Field(None, description="Countdown badge (e.g. '90 days' or 'Expired')")
    eligibilityDetail: Optional[str] = Field(None, description="Nationality / regional eligibility explanation")
    duration: Optional[str] = Field(None, description="Award duration (e.g. '1.5 Years')")
    minCgpa: Optional[str] = Field(None, description="Minimum CGPA required")
    workExperience: Optional[str] = Field(None, description="Work experience requirement ('Required', 'Preferred', 'Not required', or null)")
    recommendations: Optional[str] = Field(None, description="Number of recommendation letters required")
    english: Optional[str] = Field(None, description="Accepted English test certifications")
    documents: Optional[str] = Field(None, description="Fallback comma-separated list of required documents")
    documentRequirements: Optional[List[DocumentRequirementSchema]] = Field(None, description="Structured document requirements")
    motivation: Optional[str] = Field(None, description="Motivation letter / statement of purpose requirements")
    stipend: Optional[str] = Field(None, description="Stipend amount string (e.g. '$1,100/mo')")
    benefits: Optional[List[str]] = Field(None, description="List of funded benefits (e.g. ['Travel', 'Living', 'Stipend'])")
    courses: Optional[List[str]] = Field(None, description="Degree programs (for institutional awards)")
    focusAreas: Optional[List[str]] = Field(None, description="Thematic disciplines (for non-institutional awards)")
    selection: Optional[str] = Field(None, description="Overview of selection procedure")

    # Canonical database attributes preserved
    provider: Optional[str] = None
    host_country: Optional[str] = None
    degree_level: Optional[Any] = None
    eligible_countries: Optional[Any] = None
    fields_of_study: Optional[Any] = None
    application_open_date: Optional[str] = None
    deadline_timezone: Optional[str] = None
    minimum_cgpa: Optional[str] = None
    age_limit: Optional[str] = None
    other_eligibility: Optional[str] = None
    language_tests: Optional[Any] = None
    funding_coverage: Optional[Any] = None
    award_duration: Optional[str] = None
    required_documents: Optional[Any] = None
    essay_requirements: Optional[Any] = None
    referee_requirements: Optional[Any] = None
    application_fee_and_effort: Optional[str] = None
    last_verified_at: Optional[datetime] = None
    description: Optional[str] = None
    is_published: Optional[bool] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    @classmethod
    def from_model(cls, model: Any) -> "ScholarshipDetail":
        """Project canonical model into complete ScholarshipView compatible structure."""
        base = ScholarshipRead.from_model(model)
        data = base.model_dump()

        raw_deadline = getattr(model, "deadline", None)
        _, deadline_date_str, days_left_str = format_deadline_dates(raw_deadline)

        raw_docs = getattr(model, "required_documents", None)
        docs_fallback, doc_reqs = extract_document_requirements(raw_docs)

        raw_funding = getattr(model, "funding_coverage", None)
        raw_fields = getattr(model, "fields_of_study", None)
        courses_list = [str(f) for f in raw_fields] if isinstance(raw_fields, list) else None

        org_kind = classify_organization(getattr(model, "provider", None))

        data.update({
            "source": "Url" if getattr(model, "official_url", None) else None,
            "official_url": getattr(model, "official_url", None),
            "deadlineDate": deadline_date_str,
            "daysLeft": days_left_str,
            "eligibilityDetail": derive_eligibility_detail(
                getattr(model, "eligible_countries", None),
                getattr(model, "other_eligibility", None),
            ),
            "duration": getattr(model, "award_duration", None),
            "minCgpa": getattr(model, "minimum_cgpa", None),
            "workExperience": extract_work_experience(getattr(model, "other_eligibility", None)),
            "recommendations": extract_recommendations(getattr(model, "referee_requirements", None)),
            "english": extract_english(getattr(model, "language_tests", None)),
            "documents": docs_fallback,
            "documentRequirements": doc_reqs,
            "motivation": extract_motivation(getattr(model, "essay_requirements", None)),
            "stipend": extract_stipend(raw_funding),
            "benefits": extract_benefits(raw_funding) or None,
            "courses": courses_list if org_kind == "Institution" else None,
            "focusAreas": courses_list if org_kind != "Institution" else None,
            "selection": getattr(model, "other_eligibility", None),

            # Preserve canonical fields
            "provider": getattr(model, "provider", None),
            "host_country": getattr(model, "host_country", None),
            "degree_level": getattr(model, "degree_level", None),
            "eligible_countries": getattr(model, "eligible_countries", None),
            "fields_of_study": getattr(model, "fields_of_study", None),
            "application_open_date": format_calendar_date(getattr(model, "application_open_date", None)),
            "deadline_timezone": getattr(model, "deadline_timezone", None),
            "minimum_cgpa": getattr(model, "minimum_cgpa", None),
            "age_limit": getattr(model, "age_limit", None),
            "other_eligibility": getattr(model, "other_eligibility", None),
            "language_tests": getattr(model, "language_tests", None),
            "funding_coverage": getattr(model, "funding_coverage", None),
            "award_duration": getattr(model, "award_duration", None),
            "required_documents": getattr(model, "required_documents", None),
            "essay_requirements": getattr(model, "essay_requirements", None),
            "referee_requirements": getattr(model, "referee_requirements", None),
            "application_fee_and_effort": getattr(model, "application_fee_and_effort", None),
            "last_verified_at": getattr(model, "last_verified_at", None),
            "description": getattr(model, "description", None),
            "is_published": getattr(model, "is_published", None),
            "created_at": getattr(model, "created_at", None),
            "updated_at": getattr(model, "updated_at", None),
        })

        return cls(**data)


class ScholarshipPagination(BaseModel):
    """Pagination metadata for scholarship listing."""
    page: int = Field(1, description="Current page number (1-based)")
    limit: int = Field(20, description="Items per page")
    total_records: int = Field(0, description="Total matching published records")
    total_pages: int = Field(1, description="Total pages available")


class ScholarshipStats(BaseModel):
    """Live dashboard statistics computed from database records."""
    total_count: str = Field("0", description="Total published scholarships")
    ongoing_count: str = Field("0", description="Currently ongoing / open scholarships")
    eligible_count: str = Field("0", description="Scholarships open to international applicants")


class ScholarshipListResponse(BaseModel):
    """Envelope response for scholarship listing containing items, pagination and stats."""
    items: List[ScholarshipRead]
    pagination: ScholarshipPagination
    stats: ScholarshipStats


class ScholarshipFilterParams(BaseModel):
    """Query parameters for filtering public scholarship listings."""
    page: int = Field(1, ge=1, description="Page number (1-based)")
    limit: int = Field(20, ge=1, le=100, description="Items per page (1-100)")
    offset: int = Field(0, ge=0, description="Offset for pagination")
    location: Optional[str] = Field(None, description="Filter by location/host country")
    organization: Optional[str] = Field(None, description="Filter by organization category")
    offer: Optional[str] = Field(None, description="Filter by funding offer")
    search: Optional[str] = Field(None, description="Search term in title, provider, or notes")
    status: Optional[str] = Field(None, description="Filter by status ('Ongoing' | 'Closed')")
    course: Optional[str] = Field(None, description="Filter by course / field of study")
    deadline_before: Optional[date] = Field(None, description="Filter deadline <= date")
    deadline_after: Optional[date] = Field(None, description="Filter deadline >= date")
