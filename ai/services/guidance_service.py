from datetime import datetime, timezone
from typing import Any
from sqlalchemy import select

from core.db import SessionLocal
from core.model import Scholarship
from core.tools.db import ensure_schema_compatibility
from ai.schemas import ScholarshipGuidance
from ai.services.analyzer import generate_scholarship_guidance


def scholarship_to_dict(scholarship: Scholarship) -> dict[str, Any]:
    """Helper to convert a SQLAlchemy Scholarship ORM instance into a clean dictionary."""
    return {
        "id": scholarship.id,
        "name": scholarship.name,
        "provider": scholarship.provider,
        "host_country": scholarship.host_country,
        "degree_level": scholarship.degree_level,
        "eligible_countries": scholarship.eligible_countries,
        "fields_of_study": scholarship.fields_of_study,
        "application_open_date": scholarship.application_open_date,
        "deadline": scholarship.deadline,
        "deadline_timezone": scholarship.deadline_timezone,
        "minimum_cgpa": scholarship.minimum_cgpa,
        "age_limit": scholarship.age_limit,
        "other_eligibility": scholarship.other_eligibility,
        "language_tests": scholarship.language_tests,
        "funding_coverage": scholarship.funding_coverage,
        "award_duration": scholarship.award_duration,
        "required_documents": scholarship.required_documents,
        "essay_requirements": scholarship.essay_requirements,
        "referee_requirements": scholarship.referee_requirements,
        "application_fee_and_effort": scholarship.application_fee_and_effort,
        "official_url": scholarship.official_url,
        "last_verified_at": scholarship.last_verified_at,
        "ai_guidance": getattr(scholarship, "ai_guidance", None),
    }


def list_scholarships(limit: int = 50, offset: int = 0) -> list[dict[str, Any]]:
    """Retrieve indexed scholarships from Supabase with summary status."""
    ensure_schema_compatibility()
    with SessionLocal() as session:
        query = (
            select(
                Scholarship.id,
                Scholarship.name,
                Scholarship.provider,
                Scholarship.host_country,
                Scholarship.deadline,
                Scholarship.official_url,
                Scholarship.ai_guidance,
                Scholarship.last_verified_at,
            )
            .order_by(Scholarship.id.asc())
            .offset(offset)
            .limit(limit)
        )
        results = session.execute(query).all()
        return [
            {
                "id": row.id,
                "name": row.name,
                "provider": row.provider,
                "host_country": row.host_country,
                "deadline": str(row.deadline) if row.deadline else None,
                "official_url": row.official_url,
                "has_ai_guidance": bool(row.ai_guidance),
                "last_verified_at": row.last_verified_at.isoformat() if row.last_verified_at else None,
            }
            for row in results
        ]


def get_scholarship(scholarship_id: int) -> dict[str, Any] | None:
    """Retrieve a single scholarship record by primary key ID."""
    ensure_schema_compatibility()
    with SessionLocal() as session:
        query = select(Scholarship).where(Scholarship.id == scholarship_id)
        record = session.execute(query).scalars().first()
        if not record:
            return None
        return scholarship_to_dict(record)


def get_or_create_guidance(
    scholarship_id: int,
    force_refresh: bool = False,
) -> ScholarshipGuidance | None:
    """
    Retrieves cached AI application guidance from Supabase if available.
    If not cached or if force_refresh is True, generates fresh guidance using Gemini,
    persists it into the database for future instantaneous retrieval, and returns it.
    """
    ensure_schema_compatibility()
    with SessionLocal() as session:
        query = select(Scholarship).where(Scholarship.id == scholarship_id)
        scholarship = session.execute(query).scalars().first()
        if not scholarship:
            return None

        # Return cached guidance if present and refresh not requested
        if not force_refresh and scholarship.ai_guidance:
            try:
                return ScholarshipGuidance.model_validate(scholarship.ai_guidance)
            except Exception as e:
                print(f"[GuidanceService] Cached guidance validation warning: {e}. Regenerating...")

        # Generate fresh guidance with Gemini
        scholarship_data = scholarship_to_dict(scholarship)
        guidance = generate_scholarship_guidance(scholarship_data)

        # Cache in Supabase
        scholarship.ai_guidance = guidance.model_dump()
        session.commit()
        session.refresh(scholarship)

        return guidance

