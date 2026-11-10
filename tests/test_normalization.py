"""Unit tests for deterministic normalization and projection layer."""

from datetime import date
import pytest
from api.models.scholarship import ScholarshipModel
from api.schemas.scholarship import ScholarshipDetail, ScholarshipRead
from api.normalization import (
    classify_organization,
    derive_eligibility_detail,
    derive_location,
    derive_offer,
    extract_benefits,
    extract_document_requirements,
    extract_english,
    extract_motivation,
    extract_recommendations,
    extract_stipend,
    extract_work_experience,
    format_deadline_dates,
)


def test_classify_organization():
    """Verify deterministic organization classification."""
    assert classify_organization("University of Michigan") == "Institution"
    assert classify_organization("Imperial College London") == "Institution"
    assert classify_organization("ETH Zurich Institute of Technology") == "Institution"
    assert classify_organization("British Government Chevening") == "Government"
    assert classify_organization("Ministry of Higher Education") == "Government"
    assert classify_organization("Bill & Melinda Gates Foundation") == "Foundation"
    assert classify_organization("Mastercard Foundation") == "Foundation"
    assert classify_organization("Wellcome Trust") == "Foundation"
    assert classify_organization("International Rotary Club") == "Organization"
    assert classify_organization(None) == "Organization"
    assert classify_organization("") == "Organization"


def test_derive_offer():
    """Verify offer derivation without fabricating unverified funding."""
    assert derive_offer({"tuition": "full", "living_stipend": "$1,100/mo"}) == "Fully-funded"
    assert derive_offer({"tuition": "100%"}) == "Fully-funded"
    assert derive_offer({"tuition": "partial"}) == "Partial"
    assert derive_offer("Fully-funded master's award") == "Fully-funded"
    assert derive_offer("Partial tuition discount") == "Partial"
    assert derive_offer(None) == "Funding details in announcement"
    assert derive_offer({}) == "Funding details in announcement"


def test_stipend_and_benefits_extraction():
    """Verify stipend and benefits extraction respects source data integrity."""
    funding_full = {
        "tuition": "full",
        "living_stipend": "$1,100/mo",
        "travel": "included",
        "living": "covered",
    }
    assert extract_stipend(funding_full) == "$1,100/mo"
    benefits = extract_benefits(funding_full)
    assert "Travel" in benefits
    assert "Living" in benefits
    assert "Stipend" in benefits

    # Must NOT fabricate stipend when missing
    funding_no_stipend = {"tuition": "full", "travel": "included"}
    assert extract_stipend(funding_no_stipend) is None
    assert extract_stipend(None) is None
    assert extract_stipend({}) is None


def test_deadline_formatting_and_countdown():
    """Verify safe deadline formatting, countdown calculations, and expired handling."""
    ref_date = date(2026, 12, 20)

    # Future date (90 days out)
    target = date(2027, 3, 20)
    short_str, full_str, days_left = format_deadline_dates(target, reference_date=ref_date)
    assert full_str == "20th March, 2027"
    assert days_left == "90 days"
    assert "20th March" in short_str

    # Past date
    past = date(2026, 10, 15)
    short_past, full_past, days_left_past = format_deadline_dates(past, reference_date=ref_date)
    assert days_left_past == "Expired"
    assert "Expired" in short_past

    # Null / Rolling deadline
    short_null, full_null, days_left_null = format_deadline_dates(None)
    assert short_null == "Rolling / Open"
    assert full_null == "Rolling / Open"
    assert days_left_null == "Rolling"


def test_document_requirements_no_inference():
    """Rule: Never infer document formats or file-size limits unless source explicitly provides them."""
    # Source with explicit formats and size limits
    explicit_docs = [
        {"name": "CV", "formats": ["PDF"], "maxSize": "5 MB"},
        {"name": "Transcript", "formats": ["PDF", "JPG"], "maxSize": "10 MB"},
    ]
    fallback_str, structured = extract_document_requirements(explicit_docs)
    assert fallback_str == "CV, Transcript"
    assert structured is not None
    assert len(structured) == 2
    assert structured[0]["formats"] == ["PDF"]
    assert structured[0]["maxSize"] == "5 MB"

    # Source with plain strings: MUST NOT invent fake PDF/size limits
    plain_docs = ["CV", "Transcript", "Passport"]
    fallback_plain, structured_plain = extract_document_requirements(plain_docs)
    assert fallback_plain == "CV, Transcript, Passport"
    assert structured_plain is None  # Safe fallback to plain string


def test_work_experience_no_false_negatives():
    """Rule: Do not convert missing work-experience requirements into 'Not required'."""
    assert extract_work_experience(None) is None
    assert extract_work_experience("Applicants must have a high GPA.") is None
    assert extract_work_experience("2 years work experience required") == "Required"
    assert extract_work_experience("Professional experience preferred") == "Preferred"
    assert extract_work_experience("No work experience required") == "Not required"


def test_scholarship_detail_projection_representative_types():
    """Verify ScholarshipDetail projection across Institution, Government, and Foundation records."""
    # 1. Institution Award
    inst_model = ScholarshipModel(
        id=1,
        name="University of Michigan Scholarships",
        provider="University of Michigan",
        host_country="United States",
        deadline=date(2027, 3, 20),
        funding_coverage={"tuition": "full", "living_stipend": "$1,100/mo", "travel": "included"},
        award_duration="1.5 Years",
        minimum_cgpa="3.5",
        fields_of_study=["Msc Mechatronics Engineering", "Msc Robotics"],
        eligible_countries=["Nigeria", "Ghana", "Kenya"],
        official_url="https://finaid.umich.edu",
        is_published=True,
    )
    detail = ScholarshipDetail.from_model(inst_model)
    assert detail.organization == "Institution"
    assert detail.offer == "Fully-funded"
    assert detail.stipend == "$1,100/mo"
    assert detail.duration == "1.5 Years"
    assert detail.courses == ["Msc Mechatronics Engineering", "Msc Robotics"]
    assert detail.focusAreas is None  # Institution uses courses, not focusAreas
    assert detail.official_url == "https://finaid.umich.edu"
    assert detail.source == "Url"
    assert detail.eligibilityDetail == "Available to Nigerians"

    # 2. Government Award (Coverage block)
    gov_model = ScholarshipModel(
        id=2,
        name="Chevening Scholarships",
        provider="UK Government Foreign Office",
        host_country="United Kingdom",
        deadline=date(2026, 11, 5),
        funding_coverage={"tuition": "full", "living_stipend": "£1,347/mo"},
        fields_of_study=["Public Policy", "International Relations"],
        other_eligibility="2 years work experience required",
        is_published=True,
    )
    gov_detail = ScholarshipDetail.from_model(gov_model)
    assert gov_detail.organization == "Government"
    assert gov_detail.courses is None  # Government uses focusAreas
    assert gov_detail.focusAreas == ["Public Policy", "International Relations"]
    assert gov_detail.workExperience == "Required"

    # 3. Foundation Award with Missing Deadline
    found_model = ScholarshipModel(
        id=3,
        name="Rolling Community Fund",
        provider="Global Community Foundation",
        deadline=None,
        funding_coverage=None,
        is_published=True,
    )
    found_detail = ScholarshipDetail.from_model(found_model)
    assert found_detail.organization == "Foundation"
    assert found_detail.deadline == None
    assert found_detail.display_deadline == "Rolling / Open"
    assert found_detail.deadlineDate == "Rolling / Open"
    assert found_detail.daysLeft == "Rolling"
    assert found_detail.stipend is None
