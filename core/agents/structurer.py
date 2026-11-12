import os
from typing import Any
from dotenv import load_dotenv, find_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI

try:
    from core.schemas import ScholarshipCreate
except ImportError:
    from schemas import ScholarshipCreate

load_dotenv(find_dotenv())


api_key = os.getenv("GOOGLE_GEMINI_API") or os.getenv("GEMINI_API_KEY")
if not api_key:
    raise ValueError("GOOGLE_GEMINI_API is missing from .env")

model_name = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")

llm = ChatGoogleGenerativeAI(
    model=model_name,
    google_api_key=api_key,
    temperature=0.0,
)

structured_llm = llm.with_structured_output(ScholarshipCreate)

STRUCTURER_SYSTEM_PROMPT = """You are a rigorous academic data extraction and structuring agent.
Your task is to take an unstructured scholarship research report and map it strictly into the ScholarshipCreate schema.

Strict Schema Rules:
1. Only populate fields with facts explicitly supported by the research evidence.
2. If any field (e.g. minimum_cgpa, age_limit, application_open_date, deadline) is unknown or not yet announced for the upcoming cycle, leave it as null / None. Do NOT invent dates or requirements.
3. Dates must be in ISO format: YYYY-MM-DD.
4. Lists: Ensure degree_level, eligible_countries, fields_of_study, and required_documents are clean lists of strings.
5. Official URL: Must be the primary official website or official application portal of the scholarship. If multiple URLs exist, prioritize the official .org/.gov/.edu/.ac domain over news or third-party links.
6. Language tests: Structure as a dictionary (e.g., {"ielts": "6.5 minimum", "toefl": "not required"}) or list, or null if unspecified.
7. Funding coverage: Structure as a dictionary detailing tuition, stipend, flights, health insurance, etc.
"""


def structure_scholarship(research_data: dict[str, Any]) -> ScholarshipCreate | None:
    """
    Converts unstructured research report and grounding sources into a validated
    ScholarshipCreate Pydantic schema.
    """
    target_name = research_data.get("target_name", "Unknown Scholarship")
    report = research_data.get("report", "")
    sources = research_data.get("sources", [])

    prompt = f"""{STRUCTURER_SYSTEM_PROMPT}

Target Scholarship: {target_name}

Research Evidence:
{report}

Verified Source Links:
{chr(10).join(f"- {s}" for s in sources)}

Extract the scholarship information and return the structured ScholarshipCreate record."""

    try:
        result: ScholarshipCreate = structured_llm.invoke(prompt)

        
        validated = ScholarshipCreate.model_validate(result)

        # Ensure official_url is populated from sources if model omitted it
        if not validated.official_url and sources:
            for source in sources:
                if not source.startswith("https://vertexaisearch"):
                    try:
                        validated.official_url = source
                        break
                    except Exception:
                        continue

        return validated
    except Exception as e:
        print(f"[Structurer] Validation failed for '{target_name}': {type(e).__name__}: {e}")
        return None
