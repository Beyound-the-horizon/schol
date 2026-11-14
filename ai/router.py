from typing import Any
from fastapi import APIRouter, HTTPException, Query, status

from ai.schemas import (
    ScholarshipGuidance,
    GuidancePreviewRequest,
)
from ai.services.guidance_service import (
    list_scholarships,
    get_scholarship,
    get_or_create_guidance,
)
from ai.services.analyzer import generate_scholarship_guidance

router = APIRouter(prefix="", tags=["Scholarship AI Intelligence"])


@router.get(
    "/scholarships",
    summary="List scholarships from Supabase",
    description="Returns a paginated list of indexed scholarships with basic metadata and AI guidance availability.",
)
def get_scholarships(
    limit: int = Query(default=20, ge=1, le=100, description="Number of records to return"),
    offset: int = Query(default=0, ge=0, description="Offset for pagination"),
) -> dict[str, Any]:
    items = list_scholarships(limit=limit, offset=offset)
    return {
        "count": len(items),
        "limit": limit,
        "offset": offset,
        "scholarships": items,
    }


@router.get(
    "/scholarships/{scholarship_id}",
    summary="Get scholarship record details",
    description="Retrieve all raw and structured database attributes for a specific scholarship ID.",
)
def get_scholarship_details(scholarship_id: int) -> dict[str, Any]:
    scholarship = get_scholarship(scholarship_id)
    if not scholarship:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Scholarship with ID {scholarship_id} not found in database.",
        )
    return scholarship


@router.get(
    "/scholarships/{scholarship_id}/guidance",
    response_model=ScholarshipGuidance,
    summary="Get AI application guidance & nested apply URL",
    description="""
Returns actionable AI-powered application intelligence for a scholarship:
- **Active Nested Apply URL**: Direct account registration / portal link.
- **Adaptive Application Pattern**: Single portal vs. Course-first vs. Dual university & scholarship application.
- **Workflow Roadmap**: Ordered phase-by-phase action items with prerequisites and pitfalls.
- **Deadline Estimations**: Rough intake window estimates and status (OPEN, UPCOMING, CLOSED, ROLLING).
- **Motivation Letter Guidelines**: Exact word count limits, character caps, sub-questions, and scoring keys.
    """,
)
def get_guidance(
    scholarship_id: int,
    refresh: bool = Query(
        default=False,
        description="Force re-running Gemini AI analysis and updating the database cache",
    ),
) -> ScholarshipGuidance:
    guidance = get_or_create_guidance(scholarship_id=scholarship_id, force_refresh=refresh)
    if not guidance:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Scholarship with ID {scholarship_id} not found.",
        )
    return guidance


@router.post(
    "/guidance/preview",
    response_model=ScholarshipGuidance,
    summary="Preview AI guidance on custom scholarship data",
    description="Analyze arbitrary scholarship information on the fly without saving to the permanent database.",
)
def preview_guidance(request: GuidancePreviewRequest) -> ScholarshipGuidance:
    try:
        raw_dict = request.model_dump()
        raw_dict["id"] = 0
        raw_dict["name"] = request.scholarship_name
        return generate_scholarship_guidance(raw_dict)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate preview guidance: {e}",
        )

