import os
import re
import requests
from dotenv import load_dotenv, find_dotenv

load_dotenv(find_dotenv())


# Built-in fallback catalog if no online document URL is configured yet
DEFAULT_CATALOG = [
    "Chevening Scholarships (United Kingdom)",
    "Erasmus Mundus Joint Masters Scholarships (European Union)",
    "Commonwealth Master's & Shared Scholarships (United Kingdom)",
    "DAAD Helmut-Schmidt Programme / EPOS (Germany)",
    "Fulbright Foreign Student Program (United States)",
    "Gates Cambridge Scholarships (University of Cambridge)",
    "Rhodes Scholarships (University of Oxford)",
    "MEXT Japanese Government Scholarships (Japan)",
    "Swedish Institute Scholarships for Global Professionals (Sweden)",
    "Australia Awards Scholarships (Australia)",
    "MasterCard Foundation Scholars Program",
    "Eiffel Excellence Scholarship Programme (France)",
]


def convert_to_export_url(url: str) -> str:
    """Convert any Google Docs sharing/view URL into a plain-text export URL."""
    doc_id_match = re.search(r"/document/d/([a-zA-Z0-9-_]+)", url)
    if doc_id_match:
        doc_id = doc_id_match.group(1)
        return f"https://docs.google.com/document/d/{doc_id}/export?format=txt"
    return url


def parse_numbered_list(text: str) -> list[str]:
    """
    Parse a numbered or bulleted list of scholarships from plain text.
    """
    scholarships = []
    seen = set()

    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            continue

        # Skip common headers/metadata lines
        lower = line.lower()
        if lower.startswith("#") or "scholarship list" in lower or "curated scholarships" in lower:
            continue

        # Strip leading numbers/bullets: e.g. "1.", "1)", "[1]", "-", "*", "•"
        cleaned = re.sub(r"^(?:\[?\d+[\.\)\]]?|\-|\*|•)\s*", "", line).strip()

        # Basic validity check (must be at least 3 chars)
        if len(cleaned) >= 3 and cleaned.lower() not in seen:
            scholarships.append(cleaned)
            seen.add(cleaned.lower())

    return scholarships


def fetch_curated_scholarships(doc_url: str | None = None) -> list[str]:
    """
    Fetch the numbered list of scholarships from an online Google Doc.
    If no URL is provided, falls back to SCHOLARSHIP_CATALOG_URL in .env,
    or the default catalog if neither is available.
    """
    target_url = doc_url or os.getenv("SCHOLARSHIP_CATALOG_URL")

    if not target_url:
        print("[Catalog] No SCHOLARSHIP_CATALOG_URL provided. Using default seed catalog.")
        return DEFAULT_CATALOG

    export_url = convert_to_export_url(target_url)

    try:
        response = requests.get(export_url, timeout=15)
        response.raise_for_status()
        items = parse_numbered_list(response.text)
        if items:
            print(f"[Catalog] Successfully fetched {len(items)} scholarships from Google Doc.")
            return items
        else:
            print("[Catalog] Google Doc returned no valid items. Falling back to default catalog.")
            return DEFAULT_CATALOG
    except Exception as e:
        print(f"[Catalog] Failed to fetch Google Doc ({e}). Falling back to default catalog.")
        return DEFAULT_CATALOG
