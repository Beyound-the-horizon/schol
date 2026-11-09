"""Crawler ingestion service persisting canonical scholarship models.

Concurrency & Audit Integrity:
    When updating an existing scholarship (or checking for changes), queries acquire
    a row-level lock via `select(...).with_for_update()`.
    
    This ensures that:
    1. Concurrent crawler batches and administrative review actions (publish, reject,
       unpublish, archive) are serialized per row in PostgreSQL.
    2. Read-modify-write operations on `audit_log` cannot silently overwrite audit
       events added by simultaneous transactions.
    3. The lock is acquired inside the item savepoint (`begin_nested()`) and held
       until the transaction commits, ensuring atomicity of field changes and audit trails.
    
    SQLite note:
        As in `AdminService`, `with_for_update()` is tolerated and silently ignored by
        aiosqlite during local testing. True row lock verification requires PostgreSQL.
"""

import logging
from datetime import datetime, timezone
from typing import List
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from api.models.scholarship import ScholarshipModel
from api.schemas.ingestion import (
    IngestionItem,
    IngestionItemResult,
    IngestionRequest,
    IngestionResponse,
)

logger = logging.getLogger("api.services.ingestion")


class IngestionService:
    """Handles parsing, deduplicating, and persisting canonical crawler records."""

    @staticmethod
    async def ingest_batch(
        session: AsyncSession,
        request: IngestionRequest,
    ) -> IngestionResponse:
        """Process incoming batch of structured scholarships.
        
        Rules:
        - If official_url matches an existing record:
          - If fields are identical, mark as 'skipped'.
          - If fields differ, update record and mark as 'updated'.
        - If official_url is not in database:
          - Insert new record with is_published=False (draft by default) and mark as 'created'.
        - Isolate each item with a database savepoint (begin_nested) to protect against
          unique-constraint race conditions or single-record validation failures.
        """
        results: List[IngestionItemResult] = []
        created_count = 0
        updated_count = 0
        skipped_count = 0
        rejected_count = 0

        url_str = None

        for idx, item in enumerate(request.items):
            try:
                async with session.begin_nested():
                    existing = None
                    target_url = str(item.official_url) if item.official_url else None

                    if target_url:
                        stmt = (
                            select(ScholarshipModel)
                            .where(ScholarshipModel.official_url == target_url)
                            .with_for_update()
                        )
                        res = await session.execute(stmt)
                        existing = res.scalar_one_or_none()
                    elif item.name:
                        # Fallback deduplication when official_url is missing: match on (name, provider)
                        stmt = select(ScholarshipModel).where(
                            ScholarshipModel.name == item.name
                        )
                        if item.provider:
                            stmt = stmt.where(ScholarshipModel.provider == item.provider)
                        stmt = stmt.with_for_update()
                        res = await session.execute(stmt)
                        existing = res.scalar_one_or_none()

                    if existing is not None:
                        # Check if any data changed
                        has_changed = (
                            existing.name != item.name
                            or existing.provider != item.provider
                            or existing.host_country != item.host_country
                            or existing.degree_level != item.degree_level
                            or existing.eligible_countries != item.eligible_countries
                            or existing.fields_of_study != item.fields_of_study
                            or existing.application_open_date != item.application_open_date
                            or existing.deadline != item.deadline
                            or existing.deadline_timezone != item.deadline_timezone
                            or existing.minimum_cgpa != item.minimum_cgpa
                            or existing.age_limit != item.age_limit
                            or existing.other_eligibility != item.other_eligibility
                            or existing.language_tests != item.language_tests
                            or existing.funding_coverage != item.funding_coverage
                            or existing.award_duration != item.award_duration
                            or existing.required_documents != item.required_documents
                            or existing.essay_requirements != item.essay_requirements
                            or existing.referee_requirements != item.referee_requirements
                            or existing.application_fee_and_effort != item.application_fee_and_effort
                            or existing.description != item.description
                        )

                        if not has_changed:
                            skipped_count += 1
                            results.append(
                                IngestionItemResult(
                                    index=idx,
                                    name=item.name,
                                    status="skipped",
                                    id=existing.id,
                                    message="Identical record already exists (matched on official_url)",
                                )
                            )
                        elif existing.is_published:
                            # PUBLISHED RECORD PROTECTION:
                            # Crawler changes on a live published scholarship must NOT
                            # silently overwrite content that is already public.
                            # We record the detection in the audit log but DO NOT apply
                            # any field changes. An administrator must unpublish and
                            # re-approve (or a future pending-revisions workflow must be
                            # implemented) before crawler-submitted content updates become live.
                            #
                            # Design note: A full pending-revision workflow (storing proposed
                            # changes in a separate `scholarship_pending_revisions` table and
                            # surfacing them in the admin queue) is the recommended long-term
                            # approach. It was deferred from Phase 8.2 to avoid an incomplete
                            # schema migration; see docs/admin-publication-contract.md §7.
                            audit_entries = list(existing.audit_log or [])
                            audit_entries.append({
                                "action": "crawler_update_blocked",
                                "timestamp": datetime.now(timezone.utc).isoformat(),
                                "reason": (
                                    "Crawler submitted changes to a published record. "
                                    "Content update blocked; administrator review required."
                                ),
                            })
                            existing.audit_log = audit_entries
                            if item.last_verified_at:
                                existing.last_verified_at = item.last_verified_at

                            await session.flush()
                            skipped_count += 1
                            results.append(
                                IngestionItemResult(
                                    index=idx,
                                    name=item.name,
                                    status="skipped",
                                    id=existing.id,
                                    message=(
                                        "Published record protected: crawler changes blocked. "
                                        "Unpublish before applying crawler updates, or await "
                                        "pending-revision workflow (see admin contract §7)."
                                    ),
                                )
                            )
                        else:
                            # Safe to update: record is not published (draft / rejected / archived)
                            existing.name = item.name
                            existing.provider = item.provider
                            existing.host_country = item.host_country
                            existing.degree_level = item.degree_level
                            existing.eligible_countries = item.eligible_countries
                            existing.fields_of_study = item.fields_of_study
                            existing.application_open_date = item.application_open_date
                            existing.deadline = item.deadline
                            existing.deadline_timezone = item.deadline_timezone
                            existing.minimum_cgpa = item.minimum_cgpa
                            existing.age_limit = item.age_limit
                            existing.other_eligibility = item.other_eligibility
                            existing.language_tests = item.language_tests
                            existing.funding_coverage = item.funding_coverage
                            existing.award_duration = item.award_duration
                            existing.required_documents = item.required_documents
                            existing.essay_requirements = item.essay_requirements
                            existing.referee_requirements = item.referee_requirements
                            existing.application_fee_and_effort = item.application_fee_and_effort
                            existing.description = item.description
                            if item.last_verified_at:
                                existing.last_verified_at = item.last_verified_at

                            audit_entries = list(existing.audit_log or [])
                            audit_entries.append({
                                "action": "crawler_updated",
                                "timestamp": datetime.now(timezone.utc).isoformat(),
                            })
                            existing.audit_log = audit_entries

                            await session.flush()
                            updated_count += 1
                            results.append(
                                IngestionItemResult(
                                    index=idx,
                                    name=item.name,
                                    status="updated",
                                    id=existing.id,
                                    message="Existing draft record updated from crawler data",
                                )
                            )
                    else:
                        new_record = ScholarshipModel(
                            name=item.name,
                            provider=item.provider,
                            host_country=item.host_country,
                            degree_level=item.degree_level,
                            eligible_countries=item.eligible_countries,
                            fields_of_study=item.fields_of_study,
                            application_open_date=item.application_open_date,
                            deadline=item.deadline,
                            deadline_timezone=item.deadline_timezone,
                            minimum_cgpa=item.minimum_cgpa,
                            age_limit=item.age_limit,
                            other_eligibility=item.other_eligibility,
                            language_tests=item.language_tests,
                            funding_coverage=item.funding_coverage,
                            award_duration=item.award_duration,
                            required_documents=item.required_documents,
                            essay_requirements=item.essay_requirements,
                            referee_requirements=item.referee_requirements,
                            application_fee_and_effort=item.application_fee_and_effort,
                            official_url=target_url,
                            last_verified_at=item.last_verified_at,
                            description=item.description,
                            is_published=False,  # Enforce False strictly: all crawler intake is draft until approved
                            publication_status="draft",
                            audit_log=[
                                {
                                    "action": "ingested",
                                    "source": "crawler",
                                    "timestamp": datetime.now(timezone.utc).isoformat(),
                                    "status": "draft",
                                }
                            ],
                        )
                        session.add(new_record)
                        await session.flush()

                        created_count += 1
                        results.append(
                            IngestionItemResult(
                                index=idx,
                                name=item.name,
                                status="created",
                                id=new_record.id,
                                message="New draft scholarship record created (pending publication)",
                            )
                        )

            except IntegrityError as ie:
                logger.warning("Concurrency / Integrity error on item %d (%s): %s", idx, item.name, ie)
                rejected_count += 1
                results.append(
                    IngestionItemResult(
                        index=idx,
                        name=item.name,
                        status="rejected",
                        id=None,
                        message="Conflict: unique constraint or concurrency collision on official_url.",
                    )
                )
            except Exception as exc:
                logger.error("Processing error on item %d (%s): %s", idx, item.name, exc)
                rejected_count += 1
                results.append(
                    IngestionItemResult(
                        index=idx,
                        name=item.name,
                        status="rejected",
                        id=None,
                        message="Internal processing error while persisting record.",
                    )
                )

        # Commit transaction
        await session.commit()

        overall_status = "completed"
        if rejected_count > 0:
            overall_status = "partial_failure" if (created_count + updated_count + skipped_count) > 0 else "failed"

        return IngestionResponse(
            status=overall_status,
            total=len(request.items),
            created=created_count,
            updated=updated_count,
            skipped=skipped_count,
            rejected=rejected_count,
            results=results,
        )
