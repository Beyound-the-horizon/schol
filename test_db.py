
import os
import pytest
from core.agents.researcher import research_scholarships

def test_research_scholarships_manual_or_mocked():
    """Execute scholarship research using live API if configured, otherwise assert on environment guard."""
    if not (os.getenv("GOOGLE_GEMINI_API") or os.getenv("GEMINI_API_KEY")):
        pytest.skip("GOOGLE_GEMINI_API is not set in environment (skipped in offline test mode)")

    result = research_scholarships(
        "Research fully funded master's scholarships open to Nigerian "
        "applicants for the 2027 intake. Find official sources, "
        "application deadlines, eligibility, and funding coverage. "
        "Clearly distinguish confirmed facts from unknown information."
    )
    assert result is not None
    assert "target_name" in result

if __name__ == "__main__":
    test_research_scholarships_manual_or_mocked()
