import os
import time
from typing import Any
from dotenv import load_dotenv, find_dotenv
from google import genai
from google.genai import types
from tenacity import retry, stop_after_attempt, wait_exponential

load_dotenv(find_dotenv())


api_key = os.getenv("GOOGLE_GEMINI_API") or os.getenv("GEMINI_API_KEY")

client = None
if api_key:
    client = genai.Client(api_key=api_key)


def get_gemini_client() -> genai.Client:
    """Retrieve or initialize the Google Gemini Client on demand.
    
    Raises ValueError with a helpful message if API key is not configured.
    """
    global client, api_key
    if client is not None:
        return client
    api_key = os.getenv("GOOGLE_GEMINI_API") or os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError(
            "GOOGLE_GEMINI_API is missing from environment. Set GOOGLE_GEMINI_API in .env"
        )
    client = genai.Client(api_key=api_key)
    return client


RESEARCH_SYSTEM_PROMPT = """You are an elite, meticulous academic scholarship research agent.
Your objective is to perform real-time web research using Google Search to gather verified facts for an official scholarship program.

For the requested scholarship:
1. Search specifically for the OFFICIAL scholarship provider or university portal (avoid unofficial third-party aggregator blogs).
2. Gather verified details for the current or upcoming application cycle (2026 / 2027 / 2028 intake):
   - Official Scholarship Name and Awarding Provider / Government
   - Host Country and Degree Levels covered (Master's, PhD, Undergraduate, Postdoc)
   - Eligible Countries and Fields of Study
   - Application Opening Date, Final Deadline, and Timezone
   - Minimum CGPA / Academic Requirements, Age Limits, and Other Eligibility Criteria
   - Language Tests Accepted (e.g. IELTS, TOEFL, Duolingo, waivers)
   - Funding Coverage (Full tuition, monthly stipend, flights, visa, health insurance, etc.)
   - Award Duration (e.g., 1 year, 2 years, duration of course)
   - Required Application Documents (transcripts, letters of recommendation, CV, etc.)
   - Essay Requirements and Referee / Recommendation Requirements
   - Application Fee (Free vs fee)
   - Official Application Portal URL (Must be the primary official website)
3. Integrity rules:
   - NEVER hallucinate dates, GPA thresholds, or funding details.
   - If a specific date or criteria for the upcoming intake is not yet announced, state clearly: "UNKNOWN / NOT YET ANNOUNCED".
   - Distinguish past application cycles from upcoming cycles.
   - Provide direct URLs to official pages where each fact was verified.
"""


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=2, min=2, max=10),
    reraise=True,
)
def research_scholarship(target_name: str) -> dict[str, Any]:

    """
    Autonomously research a single target scholarship using Gemini 2.5 Flash
    with native Google Search grounding.
    """
    user_query = f"""Please perform deep web research on the following scholarship:
Target: {target_name}

Search for the official portal, upcoming deadlines, funding terms, eligibility criteria, and application requirements.
Provide a comprehensive, factual research report citing the official sources."""

    gemini = get_gemini_client()
    response = gemini.models.generate_content(
        model="gemini-2.5-flash",
        contents=user_query,
        config=types.GenerateContentConfig(
            system_instruction=RESEARCH_SYSTEM_PROMPT,
            tools=[types.Tool(google_search=types.GoogleSearch())],
            temperature=0.0,
        ),
    )

    # Extract source URLs and search queries from grounding metadata
    sources = []
    queries = []
    candidates = getattr(response, "candidates", [])
    if candidates and len(candidates) > 0:
        candidate = candidates[0]
        grounding_meta = getattr(candidate, "grounding_metadata", None)
        if grounding_meta:
            queries = list(getattr(grounding_meta, "web_search_queries", []) or [])
            chunks = getattr(grounding_meta, "grounding_chunks", []) or []
            for chunk in chunks:
                web = getattr(chunk, "web", None)
                if web and getattr(web, "uri", None):
                    sources.append(web.uri)

    return {
        "target_name": target_name,
        "report": response.text,
        "sources": list(dict.fromkeys(sources)),  
        "queries": queries,
    }


def research_scholarships(query_or_target: str) -> dict[str, Any]:
    """Compatibility wrapper for plural function name imported in tests/scripts."""
    return research_scholarship(query_or_target)
