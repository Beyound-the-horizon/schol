from datetime import datetime, timezone
import json
from typing import Any
from langchain_google_genai import ChatGoogleGenerativeAI

from ai.config import GEMINI_API_KEY, GEMINI_MODEL
from ai.schemas import ScholarshipGuidance


ANALYZER_SYSTEM_PROMPT = """You are an elite, authoritative international scholarship strategist and application advisor.
Your mission is to transform raw scholarship data into precise, actionable application guidance for prospective candidates.

You must analyze the scholarship details and produce a complete, strictly-validated ScholarshipGuidance object according to these rules:

1. APPLICATION PATTERN CLASSIFICATION:
   Determine the exact operational pattern of this scholarship:
   - SINGLE_PORTAL: The candidate registers on one central scholarship portal where account creation, personal details, and course choices are handled in a single application (e.g., Chevening, Australia Awards). Total applications: 1.
   - COURSE_FIRST_AUTOMATIC: The candidate applies directly for admission to a university/course; scholarship eligibility is automatically evaluated without a separate application form (e.g., Oxford Clarendon, Cambridge Trust). Total applications: 1.
   - COURSE_FIRST_NOMINATED: The candidate must first apply to and be accepted by an eligible university course; the university then chooses candidates and submits an official nomination to the scholarship board (e.g., Eiffel Excellence Scholarship). Total applications: 1 or 2.
   - DUAL_APPLICATION: The candidate must submit TWO distinct, independent applications:
     * Application 1: Academic admission application directly to the university/consortium.
     * Application 2: Funding/scholarship application directly to the scholarship foundation/government agency portal referencing the university application (e.g., Commonwealth Master's & Shared Scholarships, DAAD EPOS, Gates Cambridge). Total applications: 2.

2. ACTIVE NESTED APPLY URL & ACCOUNT CREATION:
   - Identify the exact URL where candidates create their applicant account or log in to begin submitting.
   - If the database `official_url` is a generic info/landing page, identify the actual application portal system (e.g., SmartSimple, DAAD Portal, OASIS, University Admissions Portal).
   - Set `is_direct_account_creation` to True if the URL opens directly to registration/signup.
   - Provide explicit, step-by-step `navigation_instructions` detailing where to click on the landing page if the portal login is nested.
   - For DUAL_APPLICATION schemes, supply both the primary scholarship portal URL and the university admission portal URL in `secondary_apply_url`.

3. DEADLINE & OPENING WINDOW ESTIMATIONS:
   - If exact dates are confirmed in the data, reflect them and set `is_estimated = False`. Compare current date against deadlines to set status to 'OPEN', 'CLOSED', or 'UPCOMING'.
   - If exact dates are missing or for future intakes, project the realistic estimated opening window (e.g., "Early August 2026") and deadline window (e.g., "Mid-to-Late October 2026") based on annual academic intake rhythms. Set `is_estimated = True`.
   - Provide concrete `timing_advice` on when to start drafting essays, requesting referee letters, and translating transcripts.

4. ESSAY & MOTIVATION LETTER WORD COUNTS:
   - Inspect `essay_requirements`, `required_documents`, and standard award guidelines.
   - Detail every written submission (Personal Statement, Motivation Letter, Study Plan, Leadership Essay, Development Impact).
   - Specify exact `min_word_count`, `max_word_count` (e.g. 500 words), and `max_character_count` if applicable.
   - Break down sub-questions that must be answered, key scoring criteria, and recommended paragraph structure.

5. ACTIONABLE WORKFLOW PHASES & GENERAL TIPS:
   - Provide an ordered sequence of phases with clear prerequisites, concrete action items, and disqualification pitfalls to avoid.
   - Offer 3-5 high-yield insider tips to maximize chances of selection.
"""


def get_llm() -> ChatGoogleGenerativeAI:
    if not GEMINI_API_KEY:
        raise ValueError("GOOGLE_GEMINI_API or GEMINI_API_KEY is missing from environment variables.")
    return ChatGoogleGenerativeAI(
        model=GEMINI_MODEL,
        google_api_key=GEMINI_API_KEY,
        temperature=0.1,
    )


def generate_scholarship_guidance(scholarship_data: dict[str, Any]) -> ScholarshipGuidance:
    """
    Analyzes raw scholarship record data and produces structured, adaptive
    application intelligence and nested portal guidance using Gemini.
    """
    llm = get_llm()
    structured_llm = llm.with_structured_output(ScholarshipGuidance)

    scholarship_id = scholarship_data.get("id", 0)
    scholarship_name = scholarship_data.get("name", "Unknown Scholarship")

    payload_summary = {
        "id": scholarship_id,
        "name": scholarship_name,
        "provider": scholarship_data.get("provider"),
        "host_country": scholarship_data.get("host_country"),
        "degree_level": scholarship_data.get("degree_level"),
        "eligible_countries": scholarship_data.get("eligible_countries"),
        "fields_of_study": scholarship_data.get("fields_of_study"),
        "application_open_date": str(scholarship_data.get("application_open_date")) if scholarship_data.get("application_open_date") else None,
        "deadline": str(scholarship_data.get("deadline")) if scholarship_data.get("deadline") else None,
        "deadline_timezone": scholarship_data.get("deadline_timezone"),
        "minimum_cgpa": scholarship_data.get("minimum_cgpa"),
        "age_limit": scholarship_data.get("age_limit"),
        "other_eligibility": scholarship_data.get("other_eligibility"),
        "language_tests": scholarship_data.get("language_tests"),
        "funding_coverage": scholarship_data.get("funding_coverage"),
        "award_duration": scholarship_data.get("award_duration"),
        "required_documents": scholarship_data.get("required_documents"),
        "essay_requirements": scholarship_data.get("essay_requirements"),
        "referee_requirements": scholarship_data.get("referee_requirements"),
        "application_fee_and_effort": scholarship_data.get("application_fee_and_effort"),
        "official_url": str(scholarship_data.get("official_url") or ""),
    }

    prompt = f"""{ANALYZER_SYSTEM_PROMPT}

Target Scholarship Record:
{json.dumps(payload_summary, indent=2, default=str)}

Current Date Context: {datetime.now(timezone.utc).strftime('%Y-%m-%d')}

Analyze this scholarship thoroughly and output the complete, validated ScholarshipGuidance schema."""

    result: ScholarshipGuidance = structured_llm.invoke(prompt)

    # Ensure scholarship_id, name, and timestamp are synchronized
    result.scholarship_id = scholarship_id
    result.scholarship_name = scholarship_name
    result.generated_at = datetime.now(timezone.utc).isoformat()

    return result

