"""Admin scholarship review, publication, and lifecycle schemas.

Authentication model note:
    The admin backend uses a shared static secret token (ADMIN_TOKEN) for
    authentication. This proves token possession, NOT individual administrator
    identity. There are no individual user accounts or JWT claims.

    - Reviewer identity in audit logs is always derived server-side as
      "admin-token" (or a configured label). Clients cannot supply or override
      the reviewer identity.
    - This is intentional given the current shared-token model and must be
      updated when individual admin accounts are introduced.
"""

from datetime import date, datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field
from api.schemas.scholarship import ScholarshipPagination


class AuditLogEntry(BaseModel):
    """Individual entry in the scholarship editorial audit log."""
    action: str = Field(..., description="Action taken (ingested, published, unpublished, rejected, archived, crawler_updated)")
    timestamp: str = Field(..., description="ISO 8601 UTC timestamp of the action")
    reviewer: Optional[str] = Field(None, description="Server-derived actor identifier (never client-supplied)")
    previous_status: Optional[str] = Field(None, description="Previous publication status")
    new_status: Optional[str] = Field(None, description="New publication status")
    notes: Optional[str] = Field(None, description="Reviewer notes or comments")
    reason: Optional[str] = Field(None, description="Rejection or unpublish rationale")
    source: Optional[str] = Field(None, description="Originator of the action (e.g. 'crawler')")


class AdminScholarshipRead(BaseModel):
    """Summary item for administrative listing and review queues."""
    id: int
    name: str
    provider: Optional[str] = None
    host_country: Optional[str] = None
    official_url: Optional[str] = None
    deadline: Optional[date] = None
    is_published: bool
    publication_status: str = "draft"
    reviewed_by: Optional[str] = None
    reviewed_at: Optional[datetime] = None
    published_at: Optional[datetime] = None
    rejection_reason: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class AdminScholarshipDetail(AdminScholarshipRead):
    """Complete scholarship representation for detailed admin editorial review."""
    degree_level: Optional[Any] = None
    eligible_countries: Optional[Any] = None
    fields_of_study: Optional[Any] = None
    application_open_date: Optional[date] = None
    deadline_timezone: Optional[str] = None
    minimum_cgpa: Optional[str] = None
    age_limit: Optional[str] = None
    other_eligibility: Optional[str] = None
    language_tests: Optional[Any] = None
    funding_coverage: Optional[Any] = None
    award_duration: Optional[str] = None
    required_documents: Optional[Any] = None
    essay_requirements: Optional[Any] = None
    referee_requirements: Optional[Any] = None
    application_fee_and_effort: Optional[str] = None
    last_verified_at: Optional[datetime] = None
    description: Optional[str] = None
    audit_log: List[Dict[str, Any]] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)


class AdminPublishRequest(BaseModel):
    """Request payload to approve and publish a scholarship.

    Note: `reviewer` is NOT accepted from the client. The actor is always
    derived server-side from the authenticated token context ("admin-token").
    """
    notes: Optional[str] = Field(None, description="Optional approval notes or commentary")


class AdminRejectRequest(BaseModel):
    """Request payload to reject a scholarship draft.

    Note: `reviewer` is NOT accepted from the client. The actor is always
    derived server-side from the authenticated token context ("admin-token").
    """
    reason: str = Field(..., min_length=3, max_length=1000, description="Mandatory rationale for rejection")


class AdminUnpublishRequest(BaseModel):
    """Request payload to unpublish an active scholarship.

    Note: `reviewer` is NOT accepted from the client. The actor is always
    derived server-side from the authenticated token context ("admin-token").
    """
    reason: Optional[str] = Field(None, max_length=1000, description="Reason for removing scholarship from public feeds")


class AdminArchiveRequest(BaseModel):
    """Request payload to archive an obsolete or expired scholarship.

    Note: `reviewer` is NOT accepted from the client. The actor is always
    derived server-side from the authenticated token context ("admin-token").
    """
    reason: Optional[str] = Field(None, max_length=1000, description="Archiving notes")


class AdminActionResponse(BaseModel):
    """Response returned upon completing an administrative review action."""
    success: bool = True
    id: int
    action: str
    previous_status: str
    new_status: str
    message: str
    scholarship: AdminScholarshipDetail


class AdminScholarshipListResponse(BaseModel):
    """Paginated list of scholarships for administrative queues with status breakdowns."""
    items: List[AdminScholarshipRead]
    pagination: ScholarshipPagination
    status_counts: Dict[str, int]
