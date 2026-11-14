"""
Verification script for the Scholarship AI Intelligence Layer in ai/
"""
import json
import sys

try:
    from ai.schemas import ScholarshipGuidance, ApplicationPattern
    from ai.services.analyzer import generate_scholarship_guidance
    from ai.services.guidance_service import list_scholarships
    print("[Test] Successfully imported AI layer modules!")
except Exception as e:
    print(f"[Test Error] Failed to import AI modules: {e}")
    sys.exit(1)


def test_ai_guidance_generation():
    sample_scholarship = {
        "id": 1,
        "name": "Commonwealth Master's & Shared Scholarships (United Kingdom)",
        "provider": "Commonwealth Scholarship Commission (CSC)",
        "host_country": "United Kingdom",
        "degree_level": ["Master's"],
        "eligible_countries": ["Eligible Commonwealth developing countries"],
        "fields_of_study": ["Science and Technology for Development", "Health Systems", "Global Prosperity"],
        "application_open_date": None,
        "deadline": None,
        "deadline_timezone": "BST",
        "minimum_cgpa": "First degree of at least upper second-class (2:1) honours standard",
        "age_limit": None,
        "other_eligibility": (
            "Be a citizen of or have been granted refugee status by an eligible Commonwealth country. "
            "Be available to start academic studies in the UK by September/October 2027. "
            "Must apply to and hold an offer from a participating UK university, as well as applying "
            "separately to the CSC portal."
        ),
        "language_tests": {"ielts": "6.5 overall with no band below 6.0"},
        "funding_coverage": {"tuition": "Full tuition fees", "airfare": "Return airfare", "stipend": "Living allowance of £1,347 per month"},
        "award_duration": "1 year full-time taught Master's course",
        "required_documents": ["Undergraduate degree certificate", "Official transcripts", "Two references", "Proof of citizenship"],
        "essay_requirements": {
            "Development Impact": "Must describe how your proposed study relates to development in your home country (approx 500 words across 4 sections).",
            "Personal Statement": "Summarize how your personal background influenced your ambitions (max 500 words)."
        },
        "referee_requirements": {"count": 2, "details": "Two letters of recommendation uploaded directly by referees."},
        "application_fee_and_effort": "Free to apply to CSC. Some universities may charge course application fees.",
        "official_url": "https://cscuk.fcdo.gov.uk/apply/",
    }

    print("\n--- Running AI Guidance Generation on Commonwealth Scholarships ---")
    guidance = generate_scholarship_guidance(sample_scholarship)

    print("\n[Generated AI Guidance Summary]")
    print(f"Scholarship: {guidance.scholarship_name}")
    print(f"Pattern Type: {guidance.application_pattern.value}")
    print(f"Total Applications Required: {guidance.total_applications_required}")
    print(f"Primary Apply URL: {guidance.active_apply_link.primary_apply_url}")
    print(f"Portal Name: {guidance.active_apply_link.portal_name}")
    print(f"Direct Account Creation: {guidance.active_apply_link.is_direct_account_creation}")
    print(f"Timeline Status: {guidance.timeline.status}")
    print(f"Estimated Open Window: {guidance.timeline.estimated_open_window}")
    print(f"Estimated Deadline: {guidance.timeline.estimated_deadline_window}")
    
    print("\n[Essay & Motivation Letter Word Counts]")
    for essay in guidance.essay_requirements:
        print(f"  - {essay.prompt_title}: Max Words: {essay.max_word_count}, Max Chars: {essay.max_character_count}")
        if essay.sub_questions:
            print(f"    Sub-questions: {essay.sub_questions[:2]}")

    print("\n[Workflow Phases]")
    for phase in guidance.workflow_phases:
        print(f"  Phase {phase.phase_number}: {phase.title} ({phase.target_entity})")
        print(f"    Action Items: {phase.action_items[:2]}")
        print(f"    Pitfalls: {phase.pitfalls_to_avoid[:1]}")

    assert guidance.total_applications_required >= 1, "Must require at least 1 application"
    assert guidance.active_apply_link.primary_apply_url.startswith("http"), "Must have a valid apply URL"
    assert len(guidance.workflow_phases) >= 1, "Must have workflow phases"
    assert len(guidance.essay_requirements) >= 1, "Must have essay requirements"

    print("\n[SUCCESS] AI guidance generation and schema assertions passed perfectly!")


if __name__ == "__main__":
    test_ai_guidance_generation()

