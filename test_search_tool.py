
import os
import pytest
from dotenv import load_dotenv

load_dotenv()

def test_tavily_search():
    """Verify Tavily search invocation when API key is provided, or skip safely."""
    api_key = os.getenv("TAVILY_API_KEY")
    if not api_key:
        pytest.skip("TAVILY_API_KEY is missing from environment (skipped in offline test mode)")

    from langchain_tavily import TavilySearch
    search = TavilySearch(
        max_results=3,
        topic="general",
    )

    try:
        result = search.invoke({
            "query": "official Erasmus Mundus Joint Masters scholarship 2027"
        })
        assert result is not None
        print(result)
    except Exception as e:
        pytest.fail(f"Search failed: {type(e).__name__}: {e}")

if __name__ == "__main__":
    test_tavily_search()
