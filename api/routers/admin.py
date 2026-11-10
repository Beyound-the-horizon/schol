"""Authenticated administrative router for scholarship editorial review and publication.

Authentication model:
    All endpoints require a shared static ADMIN_TOKEN verified via constant-time
    comparison (secrets.compare_digest). This authenticates token possession only,
    NOT individual administrator identity. The crawler ingestion token is explicitly
    blocked from accessing admin routes.

    Reviewer identity in audit entries is ALWAYS the server-side literal "admin-token".
    Clients cannot supply or override reviewer identity through request bodies.

    This shared-token model is a known limitation documented in the Phase 8.1 audit.
    Individual per-user authentication (e.g. Supabase Auth JWTs with RBAC) is
    recommended for a future phase.
"""

import secrets
from typing import Annotated, Optional
from fastapi import APIRouter, Depends, Header, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from api.config import settings
from api.db import get_db_session
from api.schemas.admin import (
    AdminActionResponse,
    AdminArchiveRequest,
    AdminPublishRequest,
    AdminRejectRequest,
    AdminScholarshipDetail,
    AdminScholarshipListResponse,
    AdminUnpublishRequest,
)
from api.services.admin_service import AdminService

router = APIRouter(prefix="/admin/scholarships", tags=["Admin"])


async def verify_admin_token(
    x_admin_token: Annotated[Optional[str], Header(alias="X-Admin-Token")] = None,
    authorization: Annotated[Optional[str], Header()] = None,
) -> None:
    """Verify administrator authorization credentials.

    Accepts X-Admin-Token header or Authorization: Bearer <admin_token>.
    Guarantees:
    - Ingestion token cannot authenticate to admin routes.
    - Constant-time secret comparison via secrets.compare_digest.
    - 401 Unauthorized returned if missing or invalid.
    """
    token = x_admin_token

    if not token and authorization and authorization.startswith("Bearer "):
        token = authorization[7:].strip()

    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing administrator authentication token. Supply X-Admin-Token header.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    expected_admin_token = settings.admin_token
    if not expected_admin_token:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Server administrator token is not configured.",
        )

    # Strictly disallow using the crawler ingestion token as an admin credential
    if settings.ingestion_token and secrets.compare_digest(token, settings.ingestion_token):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Crawler ingestion token cannot be used for administrative operations.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    is_valid = secrets.compare_digest(token, expected_admin_token)
    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid administrator credentials.",
            headers={"WWW-Authenticate": "Bearer"},
        )


@router.get(
    "",
    response_model=AdminScholarshipListResponse,
    summary="List Scholarships for Administrative Review",
    description="Returns paginated scholarship records with publication status filters and review counts.",
)
async def list_admin_scholarships(
    status: Annotated[
        Optional[str],
        Query(description="Filter by status ('draft' | 'published' | 'rejected' | 'archived' | 'all')"),
    ] = "draft",
    page: Annotated[int, Query(ge=1, description="Page number")] = 1,
    limit: Annotated[int, Query(ge=1, le=100, description="Items per page")] = 20,
    search: Annotated[Optional[str], Query(description="Search in name, provider, host country")] = None,
    _auth: None = Depends(verify_admin_token),
    session: AsyncSession = Depends(get_db_session),
) -> AdminScholarshipListResponse:
    """Retrieve scholarships queue for editorial management."""
    return await AdminService.list_scholarships(
        session=session,
        status_filter=status,
        page=page,
        limit=limit,
        search=search,
    )


@router.get(
    "/{scholarship_id}",
    response_model=AdminScholarshipDetail,
    summary="Get Scholarship Details with Audit Trail",
    description="Retrieve single scholarship with complete canonical fields and chronological audit log.",
)
async def get_admin_scholarship(
    scholarship_id: int,
    _auth: None = Depends(verify_admin_token),
    session: AsyncSession = Depends(get_db_session),
) -> AdminScholarshipDetail:
    """Retrieve detailed scholarship record for review."""
    return await AdminService.get_scholarship_by_id(session, scholarship_id)


@router.patch(
    "/{scholarship_id}/publish",
    response_model=AdminActionResponse,
    summary="Approve and Publish Scholarship",
    description=(
        "Transitions scholarship to 'published' status and exposes it on public endpoints. "
        "Allowed from 'draft' status only. Returns 409 if already published or in a disallowed state."
    ),
)
async def publish_scholarship(
    scholarship_id: int,
    body: Optional[AdminPublishRequest] = None,
    _auth: None = Depends(verify_admin_token),
    session: AsyncSession = Depends(get_db_session),
) -> AdminActionResponse:
    """Approve and publish a draft scholarship.

    Reviewer identity is set server-side to 'admin-token'. Any reviewer field
    in the request body is ignored.
    """
    notes = body.notes if body else None
    return await AdminService.publish_scholarship(
        session=session,
        scholarship_id=scholarship_id,
        notes=notes,
    )


@router.patch(
    "/{scholarship_id}/reject",
    response_model=AdminActionResponse,
    summary="Reject Scholarship Draft",
    description=(
        "Transitions scholarship to 'rejected' status with a mandatory rejection rationale. "
        "Allowed from 'draft' status only. Returns 409 if in a disallowed state."
    ),
)
async def reject_scholarship(
    scholarship_id: int,
    body: AdminRejectRequest,
    _auth: None = Depends(verify_admin_token),
    session: AsyncSession = Depends(get_db_session),
) -> AdminActionResponse:
    """Reject a scholarship draft with required reason.

    Reviewer identity is set server-side to 'admin-token'. Any reviewer field
    in the request body is ignored.
    """
    return await AdminService.reject_scholarship(
        session=session,
        scholarship_id=scholarship_id,
        reason=body.reason,
    )


@router.patch(
    "/{scholarship_id}/unpublish",
    response_model=AdminActionResponse,
    summary="Unpublish Scholarship",
    description=(
        "Reverts a published scholarship back to draft status, removing it from public endpoints. "
        "Allowed from 'published' status only. Returns 409 if in a disallowed state."
    ),
)
async def unpublish_scholarship(
    scholarship_id: int,
    body: Optional[AdminUnpublishRequest] = None,
    _auth: None = Depends(verify_admin_token),
    session: AsyncSession = Depends(get_db_session),
) -> AdminActionResponse:
    """Remove a scholarship from public visibility.

    Reviewer identity is set server-side to 'admin-token'. Any reviewer field
    in the request body is ignored.
    """
    reason = body.reason if body else None
    return await AdminService.unpublish_scholarship(
        session=session,
        scholarship_id=scholarship_id,
        reason=reason,
    )


@router.patch(
    "/{scholarship_id}/archive",
    response_model=AdminActionResponse,
    summary="Archive Scholarship",
    description=(
        "Marks scholarship as archived, removing it from active review queues and public feeds. "
        "Allowed from 'draft', 'published', and 'rejected' statuses. Returns 409 if already archived."
    ),
)
async def archive_scholarship(
    scholarship_id: int,
    body: Optional[AdminArchiveRequest] = None,
    _auth: None = Depends(verify_admin_token),
    session: AsyncSession = Depends(get_db_session),
) -> AdminActionResponse:
    """Archive an obsolete scholarship.

    Reviewer identity is set server-side to 'admin-token'. Any reviewer field
    in the request body is ignored.
    """
    reason = body.reason if body else None
    return await AdminService.archive_scholarship(
        session=session,
        scholarship_id=scholarship_id,
        reason=reason,
    )
