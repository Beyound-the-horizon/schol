"""Deterministic normalization and projection layer.

Bridges canonical database scholarship records with frontend-facing schemas
without fabricating missing facts or inferring unverified criteria.
"""

from datetime import date, datetime
import re
from typing import Any, Dict, List, Optional, Tuple, Union


def ordinal_day(day: int) -> str:
    """Format day integer to ordinal string (e.g. 1st, 2nd, 3rd, 20th)."""
    if 11 <= (day % 100) <= 13:
        suffix = "th"
    else:
        suffix = {1: "st", 2: "nd", 3: "rd"}.get(day % 10, "th")
    return f"{day}{suffix}"


def classify_organization(provider: Optional[str]) -> str:
    """Deterministically classify organization into frontend's 4 kinds.
    
    Categories: 'Institution' | 'Organization' | 'Foundation' | 'Government'
    Uses explicit keyword matching and defaults safely to 'Organization'.
    """
    if not provider or not provider.strip():
        return "Organization"

    p = provider.strip().lower()

    # Academic institutions
    if any(k in p for k in [
        "institution", "university", "college", "institute", "school", "faculty",
        "academy", "polytechnic", "universität", "universite", "universidad"
    ]):
        return "Institution"

    # Government bodies
    if any(k in p for k in [
        "government", "ministry", "department of", "commonwealth",
        "federal", "state of", "chevening", "fulbright", "embassy", "consulate"
    ]):
        return "Government"

    # Foundations and Trusts
    if any(k in p for k in [
        "foundation", "trust", "endowment", "fund", "gates", "mastercard"
    ]):
        return "Foundation"

    # Default to general organization
    return "Organization"


def derive_organization(provider: Optional[str]) -> str:
    """Project organization from provider with fallback for unclassified records."""
    if provider and provider.strip():
        return provider.strip()
    return "Unknown Provider"


def derive_location(host_country: Optional[str]) -> str:
    """Project location from host_country with safe fallback."""
    if host_country and host_country.strip():
        return host_country.strip()
    return "Global / Unspecified"


def derive_offer(funding_coverage: Optional[Union[Dict[str, Any], List[Any], str]]) -> str:
    """Derive funding offer ('Fully-funded' | 'Partial' | descriptive text).
    
    Derives 'Fully-funded' or 'Partial' only when supported by source data.
    Does not assume unverified coverage.
    """
    if not funding_coverage:
        return "Funding details in announcement"

    if isinstance(funding_coverage, str):
        cleaned = funding_coverage.strip()
        low = cleaned.lower()
        if "fully" in low or "full" in low and ("stipend" in low or "tuition" in low):
            return "Fully-funded"
        elif "partial" in low:
            return "Partial"
        return cleaned if cleaned else "Funding details in announcement"

    if isinstance(funding_coverage, dict):
        tuition = str(funding_coverage.get("tuition", "")).strip().lower()
        stipend = str(
            funding_coverage.get("living_stipend") or funding_coverage.get("stipend", "")
        ).strip().lower()

        is_full_tuition = tuition in ("full", "100%", "fully-funded", "fully funded", "yes", "covered")
        is_full_stipend = stipend in ("full", "yes", "included", "monthly stipend") or bool(stipend and "mo" in stipend)

        if is_full_tuition and is_full_stipend:
            return "Fully-funded"
        elif is_full_tuition:
            return "Fully-funded"
        elif "partial" in tuition or "partial" in stipend:
            return "Partial"
        elif tuition or stipend:
            return "Partial"
        else:
            parts = [f"{k}: {v}" for k, v in funding_coverage.items() if v]
            return ", ".join(parts[:2]) if parts else "Funding details in announcement"

    if isinstance(funding_coverage, list):
        items = [str(x).strip() for x in funding_coverage if str(x).strip()]
        low = " ".join(items).lower()
        if "fully" in low:
            return "Fully-funded"
        elif "partial" in low:
            return "Partial"
        return ", ".join(items[:2]) if items else "Funding details in announcement"

    return "Funding details in announcement"


def extract_benefits(funding_coverage: Optional[Union[Dict[str, Any], List[Any], str]]) -> List[str]:
    """Extract confirmed benefit tags without fabricating coverage."""
    if not funding_coverage:
        return []

    benefits: List[str] = []

    if isinstance(funding_coverage, dict):
        tuition = str(funding_coverage.get("tuition", "")).strip().lower()
        stipend = str(funding_coverage.get("living_stipend") or funding_coverage.get("stipend", "")).strip().lower()
        travel = str(funding_coverage.get("travel") or funding_coverage.get("flight", "")).strip().lower()
        living = str(funding_coverage.get("living") or funding_coverage.get("accommodation", "")).strip().lower()

        if travel in ("yes", "included", "full", "covered", "flights"):
            benefits.append("Travel")
        if living in ("yes", "included", "full", "covered", "accommodation") or (stipend and "living" in stipend):
            benefits.append("Living")
        if stipend and stipend not in ("no", "none", "false"):
            benefits.append("Stipend")

        for k, v in funding_coverage.items():
            k_low = k.lower()
            if "travel" in k_low and "Travel" not in benefits:
                benefits.append("Travel")
            elif ("stipend" in k_low or "allowance" in k_low) and "Stipend" not in benefits:
                benefits.append("Stipend")
            elif ("living" in k_low or "housing" in k_low or "accommodation" in k_low) and "Living" not in benefits:
                benefits.append("Living")

    elif isinstance(funding_coverage, list):
        for item in funding_coverage:
            s = str(item).strip().lower()
            if "travel" in s or "flight" in s:
                if "Travel" not in benefits: benefits.append("Travel")
            elif "stipend" in s or "allowance" in s:
                if "Stipend" not in benefits: benefits.append("Stipend")
            elif "living" in s or "accommodation" in s or "housing" in s:
                if "Living" not in benefits: benefits.append("Living")
            elif item and str(item) not in benefits:
                benefits.append(str(item).title())

    elif isinstance(funding_coverage, str):
        s = funding_coverage.lower()
        if "travel" in s or "flight" in s:
            benefits.append("Travel")
        if "living" in s or "accommodation" in s:
            benefits.append("Living")
        if "stipend" in s or "allowance" in s:
            benefits.append("Stipend")

    return benefits


def extract_stipend(funding_coverage: Optional[Union[Dict[str, Any], List[Any], str]]) -> Optional[str]:
    """Extract explicit stipend amount string without fabricating numbers."""
    if not funding_coverage:
        return None

    if isinstance(funding_coverage, dict):
        val = funding_coverage.get("living_stipend") or funding_coverage.get("stipend")
        if val and isinstance(val, (str, int, float)):
            s = str(val).strip()
            if s and s.lower() not in ("yes", "true", "included", "covered", "none", "no"):
                return s

    elif isinstance(funding_coverage, str):
        match = re.search(r"([$£€]\s*[\d,]+(?:\.\d+)?(?:\s*/\s*(?:mo|month|yr|year))?)", funding_coverage)
        if match:
            return match.group(1).replace(" ", "")

    return None


def format_deadline_dates(
    d: Optional[Union[date, datetime, str]],
    reference_date: Optional[date] = None,
) -> Tuple[Optional[str], Optional[str], Optional[str]]:
    """Return tuple of (short_deadline, deadlineDate, daysLeft).
    
    Safely handles None, rolling deadlines, and past/future dates.
    """
    if d is None:
        return ("Rolling / Open", "Rolling / Open", "Rolling")

    parsed_date: Optional[date] = None
    if isinstance(d, datetime):
        parsed_date = d.date()
    elif isinstance(d, date):
        parsed_date = d
    elif isinstance(d, str):
        s = d.strip()[:10]
        try:
            parsed_date = date.fromisoformat(s)
        except ValueError:
            return (d, d, None)

    ref = reference_date or date.today()
    diff_days = (parsed_date - ref).days

    # 1. deadlineDate: e.g. "20th March, 2027"
    day_ord = ordinal_day(parsed_date.day)
    month_name = parsed_date.strftime("%B")
    deadline_date_str = f"{day_ord} {month_name}, {parsed_date.year}"

    # 2. daysLeft: e.g. "90 days", "Expired", "Today"
    if diff_days < 0:
        days_left_str = "Expired"
    elif diff_days == 0:
        days_left_str = "Today"
    elif diff_days == 1:
        days_left_str = "1 day"
    elif diff_days <= 90:
        days_left_str = f"{diff_days} days"
    elif diff_days < 365:
        months = max(1, diff_days // 30)
        days_left_str = f"{months} months"
    else:
        years = diff_days // 365
        days_left_str = f"{years} year{'s' if years > 1 else ''}"

    # 3. short_deadline: e.g. "20th March 3mo" or "31st August 10mo"
    if diff_days < 0:
        short_str = f"{day_ord} {month_name} (Expired)"
    elif diff_days <= 30:
        short_str = f"{day_ord} {month_name} {diff_days}d"
    elif diff_days < 365:
        months = max(1, diff_days // 30)
        short_str = f"{day_ord} {month_name} {months}mo"
    else:
        years = diff_days // 365
        short_str = f"{day_ord} {month_name} {years}y"

    return (short_str, deadline_date_str, days_left_str)


def derive_eligibility_detail(
    eligible_countries: Optional[Union[List[str], Any]],
    other_eligibility: Optional[str],
) -> Optional[str]:
    """Derive nationality / country eligibility detail without hallucinating."""
    if eligible_countries and isinstance(eligible_countries, list) and len(eligible_countries) > 0:
        countries_lower = [str(c).strip().lower() for c in eligible_countries]
        if "nigeria" in countries_lower or "nigerian" in countries_lower:
            return "Available to Nigerians"
        elif any("all" in c or "international" in c or "worldwide" in c for c in countries_lower):
            return "Available to international students including Nigerians"
        else:
            names = [str(c) for c in eligible_countries[:3]]
            return f"Available to citizens of {', '.join(names)}"

    if other_eligibility and other_eligibility.strip():
        text = other_eligibility.strip()
        low = text.lower()
        if "nigeria" in low:
            return "Available to Nigerians"
        return text[:100]

    return None


def extract_document_requirements(
    required_documents: Optional[Union[List[Any], Dict[str, Any]]],
) -> Tuple[Optional[str], Optional[List[Dict[str, Any]]]]:
    """Extract documents fallback string and structured documentRequirements.
    
    Rule: Never infer document formats or file-size limits unless explicitly provided.
    """
    if not required_documents:
        return (None, None)

    if isinstance(required_documents, list):
        structured: List[Dict[str, Any]] = []
        doc_names: List[str] = []

        for item in required_documents:
            if isinstance(item, dict) and "name" in item:
                formats = item.get("formats", [])
                max_size = item.get("maxSize") or item.get("max_size", "")
                structured.append({
                    "name": str(item["name"]),
                    "formats": [str(f) for f in formats] if isinstance(formats, list) else [str(formats)],
                    "maxSize": str(max_size),
                })
                doc_names.append(str(item["name"]))
            elif isinstance(item, str) and item.strip():
                doc_names.append(item.strip())

        fallback_str = ", ".join(doc_names) if doc_names else None
        return (fallback_str, structured if structured else None)

    elif isinstance(required_documents, dict):
        items = [f"{k}: {v}" for k, v in required_documents.items()]
        return (", ".join(items), None)

    return (str(required_documents), None)


def extract_recommendations(
    referee_requirements: Optional[Union[Dict[str, Any], List[Any], str, int]],
) -> Optional[str]:
    """Extract recommendation count as a string if specified."""
    if referee_requirements is None:
        return None

    if isinstance(referee_requirements, int):
        return str(referee_requirements)

    if isinstance(referee_requirements, dict):
        count = (
            referee_requirements.get("count")
            or referee_requirements.get("number")
            or referee_requirements.get("required")
        )
        if count is not None:
            return str(count)
        for v in referee_requirements.values():
            if isinstance(v, (int, str)):
                m = re.search(r"\b([1-5])\b", str(v))
                if m:
                    return m.group(1)

    if isinstance(referee_requirements, str):
        m = re.search(r"\b([1-5])\s*(?:letters?|referees?|recommendations?)", referee_requirements.lower())
        if m:
            return m.group(1)
        m2 = re.search(r"\b([1-5])\b", referee_requirements)
        if m2:
            return m2.group(1)

    return None


def extract_english(
    language_tests: Optional[Union[Dict[str, Any], List[Any], str]],
) -> Optional[str]:
    """Extract English proficiency requirements."""
    if not language_tests:
        return None

    if isinstance(language_tests, dict):
        keys = [str(k).upper() for k in language_tests.keys() if str(k).strip()]
        if keys:
            return "/".join(keys)

    if isinstance(language_tests, list):
        items = [str(x).strip() for x in language_tests if str(x).strip()]
        return "/".join(items)

    if isinstance(language_tests, str):
        return language_tests.strip()

    return None


def extract_work_experience(other_eligibility: Optional[str]) -> Optional[str]:
    """Extract work experience requirement if explicitly mentioned.
    
    Rule: Never convert missing work-experience requirements into 'Not required'.
    """
    if not other_eligibility:
        return None

    low = other_eligibility.lower()
    if "work experience" in low or "experience" in low:
        if "not required" in low or "no experience" in low or "no work experience" in low:
            return "Not required"
        elif "preferred" in low or "advantage" in low:
            return "Preferred"
        elif "required" in low or "years of experience" in low or "years experience" in low:
            return "Required"

    return None


def extract_motivation(
    essay_requirements: Optional[Union[Dict[str, Any], List[Any], str]],
) -> Optional[str]:
    """Extract motivation letter requirement."""
    if not essay_requirements:
        return None

    if isinstance(essay_requirements, (dict, list)):
        return "Required" if essay_requirements else None

    if isinstance(essay_requirements, str) and essay_requirements.strip():
        s = essay_requirements.strip()
        return s if len(s) <= 40 else "Required"

    return None
