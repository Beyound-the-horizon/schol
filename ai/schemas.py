from enum import Enum
from typing import Any
from pydantic import BaseModel, Field


class ApplicationPattern(str, Enum):
    SINGLE_PORTAL = "SINGLE_PORTAL"              # 1 application: account creation + course choice in scholarship portal
    COURSE_FIRST_AUTOMATIC = "COURSE_FIRST_AUTOMATIC" # 1 application: apply to university course, scholarship considered automatically
    COURSE_FIRST_NOMINATED = "COURSE_FIRST_NOMINATED" # Apply to university, university nominates candidate to scholarship body
    DUAL_APPLICATION = "DUAL_APPLICATION"        # 2 applications: 1 to University + 1 to Scholarship Body/Government


class ApplicationPhase(BaseModel):
    phase_number: int = Field(description="Order of execution (1, 2, ...)")
    title: str = Field(description="Short title of this phase, e.g., 'Phase 1: Secure University Admission'")
    target_entity: str = Field(description="Organization or university receiving this application")
    portal_url: str | None = Field(default=None, description="Direct URL to complete this phase")
    prerequisites: list[str] = Field(default_factory=list, description="Documents or admissions needed before starting")
    action_items: list[str] = Field(default_factory=list, description="Concrete step-by-step actions to execute")
    pitfalls_to_avoid: list[str] = Field(default_factory=list, description="Critical mistakes that lead to disqualification")


class ActiveApplyLink(BaseModel):
    primary_apply_url: str = Field(description="Direct URL to start application or create an account on portal")
    portal_name: str = Field(description="Human-readable name of the portal system (e.g. 'SmartSimple Portal', 'DAAD Portal')")
    is_direct_account_creation: bool = Field(description="True if this URL opens directly to registration/signup form")
    secondary_apply_url: str | None = Field(default=None, description="University portal URL if dual application is required")
    navigation_instructions: str = Field(description="Clear instructions on navigating to the registration button if nested")


class EssayRequirementDetail(BaseModel):
    prompt_title: str = Field(description="Title of essay/letter, e.g., 'Motivation Letter', 'Personal Statement'")
    min_word_count: int | None = Field(default=None, description="Minimum word count if specified")
    max_word_count: int | None = Field(default=None, description="Maximum word limit (e.g., 500 words)")
    max_character_count: int | None = Field(default=None, description="Character limit if specified (e.g., 2500 characters)")
    sub_questions: list[str] = Field(default_factory=list, description="Specific questions the prompt demands answered")
    key_scoring_criteria: list[str] = Field(default_factory=list, description="What the selection panel evaluates most strictly")
    recommended_structure: list[str] = Field(default_factory=list, description="Recommended paragraph breakdown")


class TimelineEstimate(BaseModel):
    status: str = Field(description="'OPEN', 'UPCOMING', 'CLOSED', or 'ROLLING'")
    is_estimated: bool = Field(description="True if dates are based on intake cycle projections rather than confirmed dates")
    confirmed_open_date: str | None = Field(default=None, description="Confirmed opening date in YYYY-MM-DD if available")
    confirmed_deadline: str | None = Field(default=None, description="Confirmed deadline date in YYYY-MM-DD if available")
    estimated_open_window: str = Field(description="Estimated opening window, e.g., 'Early August 2026'")
    estimated_deadline_window: str = Field(description="Estimated final deadline window, e.g., 'Late October 2026'")
    typical_duration_weeks: int | None = Field(default=None, description="Typical number of weeks the portal remains open")
    timing_advice: str = Field(description="Actionable timeline advice on when to begin drafting essays and requesting referee letters")


class ScholarshipGuidance(BaseModel):
    scholarship_id: int
    scholarship_name: str
    summary_explanation: str = Field(description="Clear, plain-English overview of the entire application journey")
    application_pattern: ApplicationPattern = Field(description="Pattern classification: SINGLE_PORTAL, COURSE_FIRST_AUTOMATIC, COURSE_FIRST_NOMINATED, or DUAL_APPLICATION")
    total_applications_required: int = Field(description="Number of separate applications required (1 or 2)")
    active_apply_link: ActiveApplyLink
    workflow_phases: list[ApplicationPhase] = Field(description="Step-by-step phased application roadmap")
    timeline: TimelineEstimate
    essay_requirements: list[EssayRequirementDetail] = Field(description="Word counts, character limits, and instructions for all written submissions")
    general_tips: list[str] = Field(default_factory=list, description="High-yield insider tips to maximize winning chances")
    generated_at: str = Field(description="Timestamp when this guidance was generated")


class GuidancePreviewRequest(BaseModel):
    scholarship_name: str
    provider: str | None = None
    host_country: str | None = None
    official_url: str | None = None
    other_eligibility: str | None = None
    essay_requirements: Any | None = None
    required_documents: list[str] | None = None

