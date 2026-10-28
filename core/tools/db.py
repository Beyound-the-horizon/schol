from datetime import datetime, timezone
import re
from typing import Any
from sqlalchemy import select


try:
    from core.db import SessionLocal
    from core.model import Scholarship
    from core.schemas import ScholarshipCreate
except ImportError:
    from db import SessionLocal
    from model import Scholarship
    from schemas import ScholarshipCreate


def normalize_name(name: str) -> str:
    """Normalize a scholarship name for deduplication matching."""
    cleaned = re.sub(r"\(.*?\)", "", name)  # Remove parentheticals like (United Kingdom)
    cleaned = re.sub(r"[^a-zA-Z0-9\s]", "", cleaned)  # Remove punctuation
    return " ".join(cleaned.lower().split())


def get_existing_scholarships() -> list[dict[str, Any]]:
    """Retrieve all existing scholarships from Supabase."""
    with SessionLocal() as session:
        query = select(
            Scholarship.id,
            Scholarship.name,
            Scholarship.official_url,
            Scholarship.last_verified_at,
        )
        results = session.execute(query).all()
        return [
            {
                "id": row.id,
                "name": row.name,
                "official_url": row.official_url,
                "last_verified_at": row.last_verified_at,
                "normalized_name": normalize_name(row.name),
            }
            for row in results
        ]


def select_daily_batch(catalog_items: list[str], limit: int = 5) -> list[dict[str, Any]]:
    """
    Given a list of scholarships from the online Google Doc, select today's batch:
    1. Unindexed scholarships (not in DB) get highest priority.
    2. If fewer than `limit` new items exist, the oldest verified records are selected to refresh.
    """
    existing_records = get_existing_scholarships()
    existing_norm_map = {r["normalized_name"]: r for r in existing_records}

    new_items: list[dict[str, Any]] = []
    old_items: list[dict[str, Any]] = []

    for item in catalog_items:
        norm = normalize_name(item)
        match = None

        # Check exact or substring match
        for ex_norm, ex_rec in existing_norm_map.items():
            if norm == ex_norm or norm in ex_norm or ex_norm in norm:
                match = ex_rec
                break

        if match is None:
            new_items.append({
                "target_name": item,
                "is_new": True,
                "last_verified_at": None,
                "official_url": None,
            })
        else:
            old_items.append({
                "target_name": item,
                "is_new": False,
                "last_verified_at": match["last_verified_at"],
                "official_url": match["official_url"],
            })

    # Sort existing by oldest last_verified_at (None first, then oldest datetime)
    old_items.sort(key=lambda x: x["last_verified_at"] or datetime.min.replace(tzinfo=timezone.utc))

    selected = new_items[:limit]
    remaining = limit - len(selected)

    if remaining > 0:
        selected.extend(old_items[:remaining])

    return selected


def save_or_update_scholarship(data: ScholarshipCreate) -> dict[str, Any]:
    """
    Safely insert or update a validated Scholarship record in Supabase.
    - If official_url matches an existing record: updates fields and refreshes last_verified_at.
    - If new: creates a new row with last_verified_at = now().
    """
    with SessionLocal() as session:
        target_url = str(data.official_url) if data.official_url else None
        existing: Scholarship | None = None

        if target_url:
            query = select(Scholarship).where(Scholarship.official_url == target_url)
            existing = session.execute(query).scalars().first()

        now_utc = datetime.now(timezone.utc)

        # Dump Pydantic schema to dict
        dumped = data.model_dump()
        dumped["last_verified_at"] = now_utc
        if target_url:
            dumped["official_url"] = target_url

        if existing:
            # Update existing record
            for key, val in dumped.items():
                if val is not None:
                    setattr(existing, key, val)
            session.commit()
            session.refresh(existing)
            return {
                "status": "updated",
                "id": existing.id,
                "name": existing.name,
                "official_url": existing.official_url,
                "last_verified_at": existing.last_verified_at,
            }
        else:
            # Insert new record
            new_scholarship = Scholarship(**dumped)
            session.add(new_scholarship)
            session.commit()
            session.refresh(new_scholarship)
            return {
                "status": "created",
                "id": new_scholarship.id,
                "name": new_scholarship.name,
                "official_url": new_scholarship.official_url,
                "last_verified_at": new_scholarship.last_verified_at,
            }
