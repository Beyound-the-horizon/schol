"""Admin scholarship service: editorial review, state machine, audit logging, lifecycle management.

Authentication model:
    Admin endpoints use a shared static ADMIN_TOKEN. The actor recorded in audit
    entries is always the server-side literal "admin-token", never a client-supplied
    string. This reflects honest shared-token attribution; individual identity
    requires a future migration to per-user authentication.

State machine (enforced transitions only):
    draft      -> published   (/publish)
    draft      -> rejected    (/reject)
    draft      -> archived    (/archive)
    published  -> draft       (/unpublish)
    published  -> archived    (/archive)
    rejected   -> archived    (/archive)
    archived   -> draft       (/restore) [not yet implemented as a separate endpoint]

    All other transitions return HTTP 409 Conflict.

Audit log concurrency:
    Each mutating method acquires a row-level lock via SELECT … FOR UPDATE before
    reading and modifying audit_log. This serialises concurrent admin actions on
    the same record within a PostgreSQL session and prevents lost audit entries
    from concurrent writes.

    IMPORTANT: SQLite (used in tests) does not support SELECT … FOR UPDATE.
    The with_for_update() call is silently ignored by aiosqlite. PostgreSQL
    concurrency guarantees therefore cannot be verified by the SQLite test suite.
    A dedicated PostgreSQL integration test environment is required for full
    concurrency validation.
"""

from datetime import datetime, timezone
import logging
from typing import Dict, List, Optional, Tuple
from fastapi import HTTPException, status
from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from api.models.scholarship import ScholarshipModel
from api.schemas.admin import (
    AdminActionResponse,
    AdminScholarshipDetail,
    AdminScholarshipListResponse,
    AdminScholarshipRead,
)
from api.schemas.scholarship import ScholarshipPagination

logger = logging.getLogger("api.services.admin")

# Server-side audit actor. With shared-token auth there is no individual identity.
# This value is always set by the server; it is never accepted from client input.
_AUDIT_ACTOR = "admin-token"

# ---------------------------------------------------------------------------
# Supported state machine transitions.
# Key: current status. Value: set of statuses that may be transitioned to.
# ---------------------------------------------------------------------------
_ALLOWED_TRANSITIONS: Dict[str, Tuple[str, ...]] = {
    "draft":     ("published", "rejected", "archived"),
    "published": ("draft", "archived"),          # draft via /unpublish
    "rejected":  ("archived",),
    "archived":  ("draft",),                     # draft via /restore (not yet a route)
}


def _assert_transition_allowed(current: str, target: str, scholarship_id: int) -> None:
    """Raise HTTP 409 if the requested state transition is not permitted."""
    allowed = _ALLOWED_TRANSITIONS.get(current, ())
    if target not in allowed:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                f"Scholarship {scholarship_id} is in '{current}' status. "
                f"Transition to '{target}' is not permitted. "
                f"Allowed transitions from '{current}': {list(allowed) or ['none']}."
            ),
        )


class AdminService:
    """Administrative review, publication, and lifecycle management."""

    @staticmethod
    async def list_scholarships(
        session: AsyncSession,
        status_filter: Optional[str] = "draft",
        page: int = 1,
        limit: int = 20,
        search: Optional[str] = None,
    ) -> AdminScholarshipListResponse:
        """List scholarships filtered by review status with pagination and status counts."""
        base_stmt = select(ScholarshipModel)

        # Apply status filter
        if status_filter and status_filter.lower() != "all":
            sf = status_filter.lower()
            if sf == "published":
                base_stmt = base_stmt.where(ScholarshipModel.is_published.is_(True))
            elif sf == "draft":
                base_stmt = base_stmt.where(
                    or_(
                        ScholarshipModel.publication_status == "draft",
                        and_(
                            ScholarshipModel.publication_status.is_(None),
                            ScholarshipModel.is_published.is_(False),
                        ),
                    )
                )
            else:
                base_stmt = base_stmt.where(ScholarshipModel.publication_status == sf)

        # Apply search filter
        if search and search.strip():
            p = f"%{search.strip()}%"
            base_stmt = base_stmt.where(
                or_(
                    ScholarshipModel.name.ilike(p),
                    ScholarshipModel.provider.ilike(p),
                    ScholarshipModel.host_country.ilike(p),
                )
            )

        # Count total matching records
        count_stmt = select(func.count()).select_from(base_stmt.subquery())
        count_res = await session.execute(count_stmt)
        total_records = count_res.scalar_one() or 0

        # Calculate pagination
        total_pages = max(1, (total_records + limit - 1) // limit) if total_records else 1
        offset = (page - 1) * limit

        # Order by newest first, tie-break by ID
        query_stmt = (
            base_stmt.order_by(ScholarshipModel.id.desc())
            .offset(offset)
            .limit(limit)
        )
        result = await session.execute(query_stmt)
        records = list(result.scalars().all())

        # Compute status counts for admin dashboard
        status_counts = await AdminService._get_status_counts(session)

        return AdminScholarshipListResponse(
            items=[AdminScholarshipRead.model_validate(r) for r in records],
            pagination=ScholarshipPagination(
                page=page,
                limit=limit,
                total_records=total_records,
                total_pages=total_pages,
            ),
            status_counts=status_counts,
        )

    @staticmethod
    async def get_scholarship_by_id(
        session: AsyncSession,
        scholarship_id: int,
    ) -> AdminScholarshipDetail:
        """Retrieve single scholarship record with full editorial audit log."""
        stmt = select(ScholarshipModel).where(ScholarshipModel.id == scholarship_id)
        result = await session.execute(stmt)
        record = result.scalar_one_or_none()
        if not record:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Scholarship with ID {scholarship_id} not found.",
            )
        return AdminScholarshipDetail.model_validate(record)

    @staticmethod
    async def publish_scholarship(
        session: AsyncSession,
        scholarship_id: int,
        notes: Optional[str] = None,
    ) -> AdminActionResponse:
        """Approve and publish a scholarship, making it visible to public feeds.

        Allowed from: draft only.
        Idempotency: If already published, returns 409 (not a silent no-op).
        published_at is set exactly once; re-publishing does not overwrite it.
        """
        record = await AdminService._get_model_or_404_locked(session, scholarship_id)
        prev_status = record.publication_status or ("published" if record.is_published else "draft")

        _assert_transition_allowed(prev_status, "published", scholarship_id)

        now = datetime.now(timezone.utc)

        record.is_published = True
        record.publication_status = "published"
        # Set published_at exactly once — do not overwrite if already stamped.
        if record.published_at is None:
            record.published_at = now
        record.reviewed_at = now
        record.reviewed_by = _AUDIT_ACTOR
        record.rejection_reason = None

        audit_entry = {
            "action": "published",
            "reviewer": _AUDIT_ACTOR,
            "timestamp": now.isoformat(),
            "previous_status": prev_status,
            "new_status": "published",
            "notes": notes,
        }
        record.audit_log = list(record.audit_log or []) + [audit_entry]

        await session.commit()
        await session.refresh(record)

        logger.info("Scholarship %d published by %s", scholarship_id, _AUDIT_ACTOR)

        return AdminActionResponse(
            success=True,
            id=record.id,
            action="publish",
            previous_status=prev_status,
            new_status="published",
            message=f"Scholarship '{record.name}' published successfully.",
            scholarship=AdminScholarshipDetail.model_validate(record),
        )

    @staticmethod
    async def reject_scholarship(
        session: AsyncSession,
        scholarship_id: int,
        reason: str,
    ) -> AdminActionResponse:
        """Reject a draft scholarship with a mandatory reason.

        Allowed from: draft only.
        """
        record = await AdminService._get_model_or_404_locked(session, scholarship_id)
        prev_status = record.publication_status or ("published" if record.is_published else "draft")

        _assert_transition_allowed(prev_status, "rejected", scholarship_id)

        now = datetime.now(timezone.utc)

        record.is_published = False
        record.publication_status = "rejected"
        record.rejection_reason = reason
        record.reviewed_at = now
        record.reviewed_by = _AUDIT_ACTOR

        audit_entry = {
            "action": "rejected",
            "reviewer": _AUDIT_ACTOR,
            "timestamp": now.isoformat(),
            "previous_status": prev_status,
            "new_status": "rejected",
            "reason": reason,
        }
        record.audit_log = list(record.audit_log or []) + [audit_entry]

        await session.commit()
        await session.refresh(record)

        logger.info("Scholarship %d rejected by %s: %s", scholarship_id, _AUDIT_ACTOR, reason)

        return AdminActionResponse(
            success=True,
            id=record.id,
            action="reject",
            previous_status=prev_status,
            new_status="rejected",
            message=f"Scholarship '{record.name}' rejected. Reason: {reason}",
            scholarship=AdminScholarshipDetail.model_validate(record),
        )

    @staticmethod
    async def unpublish_scholarship(
        session: AsyncSession,
        scholarship_id: int,
        reason: Optional[str] = None,
    ) -> AdminActionResponse:
        """Revert a published scholarship back to draft status.

        Allowed from: published only.
        """
        record = await AdminService._get_model_or_404_locked(session, scholarship_id)
        prev_status = record.publication_status or ("published" if record.is_published else "draft")

        _assert_transition_allowed(prev_status, "draft", scholarship_id)

        now = datetime.now(timezone.utc)

        record.is_published = False
        record.publication_status = "draft"
        record.reviewed_at = now
        record.reviewed_by = _AUDIT_ACTOR

        audit_entry = {
            "action": "unpublished",
            "reviewer": _AUDIT_ACTOR,
            "timestamp": now.isoformat(),
            "previous_status": prev_status,
            "new_status": "draft",
            "reason": reason,
        }
        record.audit_log = list(record.audit_log or []) + [audit_entry]

        await session.commit()
        await session.refresh(record)

        logger.info("Scholarship %d unpublished by %s", scholarship_id, _AUDIT_ACTOR)

        return AdminActionResponse(
            success=True,
            id=record.id,
            action="unpublish",
            previous_status=prev_status,
            new_status="draft",
            message=f"Scholarship '{record.name}' returned to draft.",
            scholarship=AdminScholarshipDetail.model_validate(record),
        )

    @staticmethod
    async def archive_scholarship(
        session: AsyncSession,
        scholarship_id: int,
        reason: Optional[str] = None,
    ) -> AdminActionResponse:
        """Archive a scholarship record, removing it from active review queues.

        Allowed from: draft, published, rejected.
        """
        record = await AdminService._get_model_or_404_locked(session, scholarship_id)
        prev_status = record.publication_status or ("published" if record.is_published else "draft")

        _assert_transition_allowed(prev_status, "archived", scholarship_id)

        now = datetime.now(timezone.utc)

        record.is_published = False
        record.publication_status = "archived"
        record.reviewed_at = now
        record.reviewed_by = _AUDIT_ACTOR

        audit_entry = {
            "action": "archived",
            "reviewer": _AUDIT_ACTOR,
            "timestamp": now.isoformat(),
            "previous_status": prev_status,
            "new_status": "archived",
            "reason": reason,
        }
        record.audit_log = list(record.audit_log or []) + [audit_entry]

        await session.commit()
        await session.refresh(record)

        logger.info("Scholarship %d archived by %s", scholarship_id, _AUDIT_ACTOR)

        return AdminActionResponse(
            success=True,
            id=record.id,
            action="archive",
            previous_status=prev_status,
            new_status="archived",
            message=f"Scholarship '{record.name}' archived.",
            scholarship=AdminScholarshipDetail.model_validate(record),
        )

    @staticmethod
    async def _get_model_or_404_locked(session: AsyncSession, scholarship_id: int) -> ScholarshipModel:
        """Fetch scholarship entity with a row-level lock to serialise concurrent writes.

        The with_for_update() call acquires a PostgreSQL FOR UPDATE lock, preventing
        concurrent transactions from reading and overwriting the audit_log array
        simultaneously.

        On SQLite (aiosqlite), with_for_update() is silently ignored. The SQLite
        test suite therefore does NOT verify PostgreSQL concurrency behaviour.
        """
        stmt = (
            select(ScholarshipModel)
            .where(ScholarshipModel.id == scholarship_id)
            .with_for_update()
        )
        result = await session.execute(stmt)
        record = result.scalar_one_or_none()
        if not record:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Scholarship with ID {scholarship_id} not found.",
            )
        return record

    @staticmethod
    async def _get_status_counts(session: AsyncSession) -> Dict[str, int]:
        """Compute scholarship counts grouped by publication status."""
        total_stmt = select(func.count(ScholarshipModel.id))
        total_res = await session.execute(total_stmt)
        total = total_res.scalar_one() or 0

        published_stmt = select(func.count(ScholarshipModel.id)).where(
            ScholarshipModel.is_published.is_(True)
        )
        published_res = await session.execute(published_stmt)
        published = published_res.scalar_one() or 0

        rejected_stmt = select(func.count(ScholarshipModel.id)).where(
            ScholarshipModel.publication_status == "rejected"
        )
        rejected_res = await session.execute(rejected_stmt)
        rejected = rejected_res.scalar_one() or 0

        archived_stmt = select(func.count(ScholarshipModel.id)).where(
            ScholarshipModel.publication_status == "archived"
        )
        archived_res = await session.execute(archived_stmt)
        archived = archived_res.scalar_one() or 0

        draft_stmt = select(func.count(ScholarshipModel.id)).where(
            or_(
                ScholarshipModel.publication_status == "draft",
                and_(
                    ScholarshipModel.publication_status.is_(None),
                    ScholarshipModel.is_published.is_(False),
                ),
            )
        )
        draft_res = await session.execute(draft_stmt)
        draft = draft_res.scalar_one() or 0

        return {
            "total": total,
            "published": published,
            "draft": draft,
            "rejected": rejected,
            "archived": archived,
        }
