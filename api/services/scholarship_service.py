"""Scholarship read service filtering on canonical model columns."""

from datetime import date
from typing import List, Optional, Tuple
from sqlalchemy import cast, func, or_, select, String
from sqlalchemy.ext.asyncio import AsyncSession
from api.models.scholarship import ScholarshipModel
from api.schemas.scholarship import ScholarshipFilterParams, ScholarshipStats


class ScholarshipService:
    """Read operations on canonical scholarship models."""

    @staticmethod
    async def list_scholarships(
        session: AsyncSession,
        filters: ScholarshipFilterParams,
    ) -> Tuple[List[ScholarshipModel], int]:
        """Retrieve published scholarships with total matching count."""
        base_stmt = select(ScholarshipModel).where(ScholarshipModel.is_published.is_(True))

        # Filter by host country (projected as location)
        if filters.location:
            locs = [l.strip() for l in filters.location.split(",") if l.strip()]
            if locs:
                base_stmt = base_stmt.where(
                    or_(*(ScholarshipModel.host_country.ilike(f"%{l}%") for l in locs))
                )

        # Filter by provider / organization
        if filters.organization:
            orgs = [o.strip() for o in filters.organization.split(",") if o.strip()]
            if orgs:
                base_stmt = base_stmt.where(
                    or_(*(ScholarshipModel.provider.ilike(f"%{o}%") for o in orgs))
                )

        # General search keyword across name, provider, location, notes, and fields of study
        if filters.search:
            p = f"%{filters.search.strip()}%"
            base_stmt = base_stmt.where(
                or_(
                    ScholarshipModel.name.ilike(p),
                    ScholarshipModel.provider.ilike(p),
                    ScholarshipModel.host_country.ilike(p),
                    ScholarshipModel.description.ilike(p),
                    ScholarshipModel.other_eligibility.ilike(p),
                    cast(ScholarshipModel.fields_of_study, String).ilike(p),
                )
            )

        # Status filter ('Ongoing' | 'Closed')
        if filters.status:
            today = date.today()
            status_vals = [s.strip().lower() for s in filters.status.split(",") if s.strip()]
            wants_ongoing = "ongoing" in status_vals
            wants_closed = "closed" in status_vals
            if wants_ongoing and not wants_closed:
                base_stmt = base_stmt.where(
                    or_(ScholarshipModel.deadline.is_(None), ScholarshipModel.deadline >= today)
                )
            elif wants_closed and not wants_ongoing:
                base_stmt = base_stmt.where(ScholarshipModel.deadline < today)

        # Course / Field of study filter
        if filters.course:
            courses = [c.strip() for c in filters.course.split(",") if c.strip()]
            if courses:
                base_stmt = base_stmt.where(
                    or_(*(cast(ScholarshipModel.fields_of_study, String).ilike(f"%{c}%") for c in courses))
                )

        # Funding / Offer filter
        if filters.offer:
            offers = [of.strip() for of in filters.offer.split(",") if of.strip()]
            if offers:
                base_stmt = base_stmt.where(
                    or_(*(cast(ScholarshipModel.funding_coverage, String).ilike(f"%{of}%") for of in offers))
                )

        # Deadline filters
        if filters.deadline_before:
            base_stmt = base_stmt.where(ScholarshipModel.deadline <= filters.deadline_before)
        if filters.deadline_after:
            base_stmt = base_stmt.where(ScholarshipModel.deadline >= filters.deadline_after)

        # Count total matching records before pagination
        count_stmt = select(func.count()).select_from(base_stmt.subquery())
        total_count_res = await session.execute(count_stmt)
        total_records = total_count_res.scalar_one() or 0

        # Calculate offset from page if offset is not explicitly provided
        effective_offset = filters.offset
        if effective_offset == 0 and filters.page > 1:
            effective_offset = (filters.page - 1) * filters.limit

        # Deterministic sorting: earliest deadline first, tie-break by ID
        query_stmt = base_stmt.order_by(
            ScholarshipModel.deadline.asc().nulls_last(),
            ScholarshipModel.id.asc(),
        ).offset(effective_offset).limit(filters.limit)

        result = await session.execute(query_stmt)
        records = list(result.scalars().all())
        return records, total_records

    @staticmethod
    async def get_stats(session: AsyncSession) -> ScholarshipStats:
        """Compute live dashboard stats for published scholarships."""
        today = date.today()

        # Total published
        total_stmt = select(func.count(ScholarshipModel.id)).where(
            ScholarshipModel.is_published.is_(True)
        )
        total_res = await session.execute(total_stmt)
        total = total_res.scalar_one() or 0

        # Ongoing (deadline is in future or rolling/null)
        ongoing_stmt = select(func.count(ScholarshipModel.id)).where(
            ScholarshipModel.is_published.is_(True),
            or_(ScholarshipModel.deadline.is_(None), ScholarshipModel.deadline >= today),
        )
        ongoing_res = await session.execute(ongoing_stmt)
        ongoing = ongoing_res.scalar_one() or 0

        # Eligible (open without disqualifying country restrictions)
        eligible_stmt = select(func.count(ScholarshipModel.id)).where(
            ScholarshipModel.is_published.is_(True),
            or_(
                ScholarshipModel.eligible_countries.is_(None),
                cast(ScholarshipModel.eligible_countries, String).ilike("%nigeria%"),
                cast(ScholarshipModel.eligible_countries, String).ilike("%all%"),
                cast(ScholarshipModel.eligible_countries, String).ilike("%international%"),
            ),
        )
        eligible_res = await session.execute(eligible_stmt)
        eligible = eligible_res.scalar_one() or 0

        return ScholarshipStats(
            total_count=f"{total:,}",
            ongoing_count=f"{ongoing:,}",
            eligible_count=f"{eligible:,}",
        )

    @staticmethod
    async def get_scholarship_by_id(
        session: AsyncSession,
        scholarship_id: int,
    ) -> Optional[ScholarshipModel]:
        """Retrieve single published scholarship by primary key."""
        stmt = select(ScholarshipModel).where(
            ScholarshipModel.id == scholarship_id,
            ScholarshipModel.is_published.is_(True),
        )
        result = await session.execute(stmt)
        return result.scalar_one_or_none()
