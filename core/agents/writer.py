import os
from typing import Any
from dotenv import load_dotenv, find_dotenv

load_dotenv(find_dotenv())

try:
    from core.schemas import ScholarshipCreate
    from core.tools.db import save_or_update_scholarship
except ImportError:
    from schemas import ScholarshipCreate
    from tools.db import save_or_update_scholarship




def write_scholarship(structured_record: ScholarshipCreate | None) -> dict[str, Any]:
    """
    Writer Agent: Gatekeeper and executor for Supabase.
    Evaluates record quality and uses safe Python execution to insert or update.
    """
    if not structured_record:
        return {
            "status": "rejected",
            "reason": "Record is empty or failed schema validation.",
        }

    
    if not structured_record.name or len(structured_record.name.strip()) < 2:
        return {
            "status": "rejected",
            "reason": "Missing or invalid scholarship name.",
        }

    if not structured_record.official_url:
        return {
            "status": "rejected",
            "reason": "Missing official verification URL.",
        }

    try:
        # Standard, safe Python execution: checks duplicates & commits to Supabase
        result = save_or_update_scholarship(structured_record)
        return {
            "status": result.get("status", "saved"),
            "id": result.get("id"),
            "name": result.get("name"),
            "official_url": str(result.get("official_url")),
            "last_verified_at": result.get("last_verified_at"),
        }
    except Exception as e:
        print(f"[Writer] Persistence error for '{structured_record.name}': {type(e).__name__}: {e}")
        return {
            "status": "error",
            "reason": f"{type(e).__name__}: {e}",
            "name": structured_record.name,
        }
