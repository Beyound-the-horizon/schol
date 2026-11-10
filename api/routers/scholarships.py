"""Public scholarships endpoints projecting canonical models to frontend schemas."""

from typing import Annotated, List, Optional, Union
from datetime import date
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from api.db import get_db_session
from api.schemas.scholarship import (
    ScholarshipDetail,
    ScholarshipFilterParams,
    ScholarshipListResponse,
    ScholarshipPagination,
    ScholarshipRead,
    ScholarshipStats,
)
from api.services.scholarship_service import ScholarshipService

router = APIRouter(prefix="/scholarships", tags=["Scholarships"])


@router.get(
    "/stats",
    response_model=ScholarshipStats,
    summary="Get Dashboard Statistics",
    description="Returns live counts for total, ongoing, and eligible published scholarships.",
)
async def get_scholarship_stats(
    session: AsyncSession = Depends(get_db_session),
) -> ScholarshipStats:
    """Compute and return aggregate dashboard metrics."""
    return await ScholarshipService.get_stats(session)


@router.get(
    "",
    response_model=Union[ScholarshipListResponse, List[ScholarshipRead]],
    summary="List Published Scholarships",
    description=(
        "Returns published scholarships. If envelope=true, returns full envelope with "
        "pagination and dashboard stats. Defaults to plain array for direct listing cards."
    ),
)
async def list_scholarships(
    page: Annotated[int, Query(ge=1, description="Page number (1-based)")] = 1,
    limit: Annotated[int, Query(ge=1, le=100, description="Items per page (max 100)")] = 20,
    offset: Annotated[int, Query(ge=0, description="Offset for pagination")] = 0,
    location: Annotated[Optional[str], Query(description="Filter by location or host country")] = None,
    organization: Annotated[Optional[str], Query(description="Filter by organization category")] = None,
    offer: Annotated[Optional[str], Query(description="Filter by funding offer")] = None,
    search: Annotated[Optional[str], Query(description="Search term in title, provider, or notes")] = None,
    status: Annotated[Optional[str], Query(description="Filter by status ('Ongoing' | 'Closed')")] = None,
    course: Annotated[Optional[str], Query(description="Filter by course / field of study")] = None,
    deadline_before: Annotated[Optional[date], Query(description="Filter deadline <= date")] = None,
    deadline_after: Annotated[Optional[date], Query(description="Filter deadline >= date")] = None,
    envelope: Annotated[bool, Query(description="Wrap response in pagination and stats envelope")] = False,
    session: AsyncSession = Depends(get_db_session),
) -> Union[ScholarshipListResponse, List[ScholarshipRead]]:
    """Retrieve scholarships with optional filtering and deterministic pagination."""
    filters = ScholarshipFilterParams(
        page=page,
        limit=limit,
        offset=offset,
        location=location,
        organization=organization,
        offer=offer,
        search=search,
        status=status,
        course=course,
        deadline_before=deadline_before,
        deadline_after=deadline_after,
    )
    records, total_records = await ScholarshipService.list_scholarships(session, filters)
    items = [ScholarshipRead.from_model(r) for r in records]

    if envelope:
        total_pages = max(1, (total_records + limit - 1) // limit) if total_records else 1
        stats = await ScholarshipService.get_stats(session)
        return ScholarshipListResponse(
            items=items,
            pagination=ScholarshipPagination(
                page=page,
                limit=limit,
                total_records=total_records,
                total_pages=total_pages,
            ),
            stats=stats,
        )

    return items


@router.get(
    "/{scholarship_id}",
    response_model=ScholarshipDetail,
    summary="Get Scholarship Details",
    description="Retrieve a single published scholarship by its numeric identifier.",
    responses={
        404: {"description": "Scholarship not found or not published"},
    },
)
async def get_scholarship(
    scholarship_id: int,
    session: AsyncSession = Depends(get_db_session),
) -> ScholarshipDetail:
    """Retrieve full scholarship details by numeric ID."""
    record = await ScholarshipService.get_scholarship_by_id(session, scholarship_id)
    if record is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Scholarship with ID {scholarship_id} not found.",
        )
    return ScholarshipDetail.from_model(record)
