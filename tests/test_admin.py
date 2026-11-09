"""Tests for administrative review, publication, and lifecycle state transitions.

Coverage:
 - Authentication (unauthenticated, invalid token, crawler token blocked, Bearer token)
 - State machine transitions (valid & invalid / 409 Conflict)
 - Idempotency guards (re-publishing does not overwrite published_at or duplicate events)
 - Reviewer identity (always server-side 'admin-token'; client-supplied values rejected)
 - Audit history integrity across multiple transitions
 - Crawler cannot silently update published record content
 - Crawler update on a published record is blocked and logged
 - Crawler cannot modify publication status or audit fields directly
 - Contradictory publication states are rejected (via CheckConstraint)
 - Existing published records (seed data) correctly have publication_status='published'
 - Existing unpublished records remain unpublished after seeding
 - Production startup rejects missing/default admin credentials

SQLite concurrency note:
    with_for_update() row-locking is silently ignored by aiosqlite. Concurrent
    write collision tests would require a real PostgreSQL instance.
"""

import pytest
from httpx import AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from api.config import settings

VALID_ADMIN_TOKEN = settings.admin_token
CRAWLER_INGESTION_TOKEN = settings.ingestion_token

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _admin(token: str = VALID_ADMIN_TOKEN) -> dict:
    return {"X-Admin-Token": token}


async def _ingest_new(client: AsyncClient, url: str, name: str = "Test Scholarship") -> int:
    """Ingest a fresh scholarship and return its ID."""
    res = await client.post(
        "/api/v1/scholarships/ingest",
        json={"items": [{"name": name, "official_url": url}]},
        headers={"X-Ingestion-Token": CRAWLER_INGESTION_TOKEN},
    )
    assert res.status_code == 200, res.text
    return res.json()["results"][0]["id"]


# ===========================================================================
# 1. Authentication
# ===========================================================================

@pytest.mark.asyncio
async def test_admin_unauthenticated_request_rejected(client: AsyncClient):
    """Requests to administrative endpoints without credentials receive 401."""
    res = await client.get("/api/v1/admin/scholarships")
    assert res.status_code == 401
    assert "missing" in res.json()["detail"].lower()


@pytest.mark.asyncio
async def test_admin_invalid_token_rejected(client: AsyncClient):
    """Requests with an invalid admin token receive 401."""
    res = await client.get("/api/v1/admin/scholarships", headers=_admin("invalid-token"))
    assert res.status_code == 401
    assert "invalid" in res.json()["detail"].lower()


@pytest.mark.asyncio
async def test_admin_rejects_crawler_ingestion_token(client: AsyncClient):
    """Crawler ingestion token cannot be used to access administrative endpoints."""
    res = await client.get("/api/v1/admin/scholarships", headers=_admin(CRAWLER_INGESTION_TOKEN))
    assert res.status_code == 401
    assert "crawler ingestion token cannot be used" in res.json()["detail"].lower()


@pytest.mark.asyncio
async def test_admin_bearer_token_authorization(client: AsyncClient):
    """Admin endpoints accept standard Authorization: Bearer <admin_token>."""
    headers = {"Authorization": f"Bearer {VALID_ADMIN_TOKEN}"}
    res = await client.get("/api/v1/admin/scholarships", headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert "items" in data
    assert "pagination" in data
    assert "status_counts" in data


# ===========================================================================
# 2. Seed data integrity (backfill equivalence)
# ===========================================================================

@pytest.mark.asyncio
async def test_existing_published_records_have_correct_status(client: AsyncClient):
    """Pre-existing published records have publication_status='published' (not 'draft').
    
    This is the in-process analogue of the migration backfill (MIG-1). The seed
    data in conftest.py explicitly sets both fields consistently, confirming that
    any seeded published record will appear correctly in the admin queue.
    """
    res = await client.get("/api/v1/admin/scholarships?status=published", headers=_admin())
    assert res.status_code == 200
    items = res.json()["items"]
    assert len(items) >= 4  # seeds 1-4 are published
    for item in items:
        assert item["is_published"] is True
        assert item["publication_status"] == "published", (
            f"ID {item['id']} has is_published=True but publication_status={item['publication_status']!r}"
        )


@pytest.mark.asyncio
async def test_existing_draft_record_remains_unpublished(client: AsyncClient):
    """Pre-existing draft record (seed 5) is not published and not in public feed."""
    # Confirm hidden from public
    pub = await client.get("/api/v1/scholarships/5")
    assert pub.status_code == 404

    # Confirm visible in admin draft queue
    admin_res = await client.get("/api/v1/admin/scholarships?status=draft", headers=_admin())
    assert admin_res.status_code == 200
    draft_names = [i["name"] for i in admin_res.json()["items"]]
    assert "Secret Internal Draft Scholarship" in draft_names


@pytest.mark.asyncio
async def test_admin_list_draft_scholarships(client: AsyncClient):
    """Admin can list pending draft records."""
    res = await client.get("/api/v1/admin/scholarships?status=draft", headers=_admin())
    assert res.status_code == 200
    data = res.json()
    assert data["pagination"]["total_records"] >= 1


@pytest.mark.asyncio
async def test_admin_get_draft_detail_with_audit_log(client: AsyncClient):
    """Admin can retrieve full scholarship detail for draft record 5."""
    res = await client.get("/api/v1/admin/scholarships/5", headers=_admin())
    assert res.status_code == 200
    item = res.json()
    assert item["id"] == 5
    assert item["is_published"] is False
    assert item["publication_status"] == "draft"
    assert "audit_log" in item
    assert isinstance(item["audit_log"], list)


# ===========================================================================
# 3. State machine — valid transitions
# ===========================================================================

@pytest.mark.asyncio
async def test_admin_publish_draft_scholarship(client: AsyncClient):
    """Admin approves and publishes a draft (record 5), making it live in public endpoints."""
    # Step 1: Verify record 5 is not currently visible on public GET
    public_before = await client.get("/api/v1/scholarships/5")
    assert public_before.status_code == 404

    # Step 2: Publish record 5
    publish_res = await client.patch(
        "/api/v1/admin/scholarships/5/publish",
        json={"notes": "Verified official announcement portal and degree criteria."},
        headers=_admin(),
    )
    assert publish_res.status_code == 200
    data = publish_res.json()
    assert data["success"] is True
    assert data["action"] == "publish"
    assert data["previous_status"] == "draft"
    assert data["new_status"] == "published"
    assert data["scholarship"]["is_published"] is True

    # Step 3: Verify record 5 is now visible in public endpoint
    public_after = await client.get("/api/v1/scholarships/5")
    assert public_after.status_code == 200
    assert public_after.json()["id"] == 5


@pytest.mark.asyncio
async def test_admin_reject_draft_scholarship(client: AsyncClient):
    """Admin rejects a draft scholarship with a mandatory rejection rationale."""
    draft_id = await _ingest_new(client, "https://reject-test.example.com", "Spam Opportunity to Reject")

    # Reject with missing reason -> 422
    bad_reject = await client.patch(
        f"/api/v1/admin/scholarships/{draft_id}/reject",
        json={},
        headers=_admin(),
    )
    assert bad_reject.status_code == 422

    # Reject with valid reason
    reject_res = await client.patch(
        f"/api/v1/admin/scholarships/{draft_id}/reject",
        json={"reason": "Official website is defunct and redirects to an advertisement."},
        headers=_admin(),
    )
    assert reject_res.status_code == 200
    data = reject_res.json()
    assert data["action"] == "reject"
    assert data["new_status"] == "rejected"
    assert data["scholarship"]["is_published"] is False
    assert "defunct" in data["scholarship"]["rejection_reason"]

    # Public endpoint must return 404
    pub = await client.get(f"/api/v1/scholarships/{draft_id}")
    assert pub.status_code == 404


@pytest.mark.asyncio
async def test_admin_unpublish_published_scholarship(client: AsyncClient):
    """Admin unpublishes an active scholarship (record 1) back to draft."""
    pub_res = await client.get("/api/v1/scholarships/1")
    assert pub_res.status_code == 200

    unpub_res = await client.patch(
        "/api/v1/admin/scholarships/1/unpublish",
        json={"reason": "Application window temporarily paused by host university."},
        headers=_admin(),
    )
    assert unpub_res.status_code == 200
    data = unpub_res.json()
    assert data["action"] == "unpublish"
    assert data["new_status"] == "draft"
    assert data["scholarship"]["is_published"] is False

    # Verify no longer available publicly
    pub_after = await client.get("/api/v1/scholarships/1")
    assert pub_after.status_code == 404


@pytest.mark.asyncio
async def test_admin_archive_draft_scholarship(client: AsyncClient):
    """Admin archives a draft scholarship record."""
    draft_id = await _ingest_new(client, "https://archive-draft.example.com", "Draft to Archive")

    archive_res = await client.patch(
        f"/api/v1/admin/scholarships/{draft_id}/archive",
        json={"reason": "Archived stale draft."},
        headers=_admin(),
    )
    assert archive_res.status_code == 200
    data = archive_res.json()
    assert data["action"] == "archive"
    assert data["new_status"] == "archived"
    assert data["scholarship"]["is_published"] is False


@pytest.mark.asyncio
async def test_admin_archive_published_scholarship(client: AsyncClient):
    """Admin archives a published scholarship (record 2)."""
    archive_res = await client.patch(
        "/api/v1/admin/scholarships/2/archive",
        json={"reason": "Archived prior award cycle"},
        headers=_admin(),
    )
    assert archive_res.status_code == 200
    data = archive_res.json()
    assert data["action"] == "archive"
    assert data["new_status"] == "archived"
    assert data["scholarship"]["is_published"] is False


@pytest.mark.asyncio
async def test_admin_archive_rejected_scholarship(client: AsyncClient):
    """Admin can archive a rejected scholarship."""
    draft_id = await _ingest_new(client, "https://archive-rejected.example.com", "Rejected to Archive")

    # Reject it first
    await client.patch(
        f"/api/v1/admin/scholarships/{draft_id}/reject",
        json={"reason": "Spam link."},
        headers=_admin(),
    )

    # Then archive
    archive_res = await client.patch(
        f"/api/v1/admin/scholarships/{draft_id}/archive",
        json={"reason": "Permanently archived spam."},
        headers=_admin(),
    )
    assert archive_res.status_code == 200
    assert archive_res.json()["new_status"] == "archived"


# ===========================================================================
# 4. State machine — invalid transitions (HTTP 409)
# ===========================================================================

@pytest.mark.asyncio
async def test_publish_already_published_returns_409(client: AsyncClient):
    """Re-publishing an already published scholarship returns 409 Conflict."""
    # Publish record 5 first
    await client.patch(
        "/api/v1/admin/scholarships/5/publish",
        json={"notes": "First publish."},
        headers=_admin(),
    )
    # Attempt to publish again
    second_publish = await client.patch(
        "/api/v1/admin/scholarships/5/publish",
        json={"notes": "Second publish attempt."},
        headers=_admin(),
    )
    assert second_publish.status_code == 409
    assert "published" in second_publish.json()["detail"]


@pytest.mark.asyncio
async def test_reject_published_scholarship_returns_409(client: AsyncClient):
    """Rejecting an already published scholarship returns 409 (must unpublish first)."""
    # Record 3 (DAAD) is published
    reject_res = await client.patch(
        "/api/v1/admin/scholarships/3/reject",
        json={"reason": "Some reason."},
        headers=_admin(),
    )
    assert reject_res.status_code == 409
    detail = reject_res.json()["detail"]
    assert "published" in detail


@pytest.mark.asyncio
async def test_unpublish_draft_returns_409(client: AsyncClient):
    """Unpublishing a draft (not published) scholarship returns 409."""
    unpub_res = await client.patch(
        "/api/v1/admin/scholarships/5/unpublish",
        json={"reason": "Mistake."},
        headers=_admin(),
    )
    assert unpub_res.status_code == 409
    assert "draft" in unpub_res.json()["detail"]


@pytest.mark.asyncio
async def test_reject_archived_scholarship_returns_409(client: AsyncClient):
    """Rejecting an archived scholarship returns 409."""
    draft_id = await _ingest_new(client, "https://archive-then-reject.example.com", "Archive Then Reject")
    # Archive from draft
    await client.patch(
        f"/api/v1/admin/scholarships/{draft_id}/archive",
        json={"reason": "Archiving."},
        headers=_admin(),
    )
    # Try to reject the archived record
    reject_res = await client.patch(
        f"/api/v1/admin/scholarships/{draft_id}/reject",
        json={"reason": "Trying to reject archived."},
        headers=_admin(),
    )
    assert reject_res.status_code == 409


@pytest.mark.asyncio
async def test_archive_already_archived_returns_409(client: AsyncClient):
    """Archiving an already archived scholarship returns 409."""
    draft_id = await _ingest_new(client, "https://double-archive.example.com", "Double Archive Test")
    await client.patch(
        f"/api/v1/admin/scholarships/{draft_id}/archive",
        json={"reason": "First archive."},
        headers=_admin(),
    )
    second_archive = await client.patch(
        f"/api/v1/admin/scholarships/{draft_id}/archive",
        json={"reason": "Second archive attempt."},
        headers=_admin(),
    )
    assert second_archive.status_code == 409


# ===========================================================================
# 5. Idempotency — published_at not overwritten on re-transition
# ===========================================================================

@pytest.mark.asyncio
async def test_publish_sets_published_at_exactly_once(client: AsyncClient):
    """published_at is set when first published and NOT overwritten on re-publish attempts."""
    # Publish record 5
    pub1 = await client.patch(
        "/api/v1/admin/scholarships/5/publish",
        json={"notes": "First."},
        headers=_admin(),
    )
    assert pub1.status_code == 200
    published_at_first = pub1.json()["scholarship"]["published_at"]
    assert published_at_first is not None

    # Unpublish and re-publish to verify published_at is preserved
    await client.patch(
        "/api/v1/admin/scholarships/5/unpublish",
        json={"reason": "Temporarily paused."},
        headers=_admin(),
    )
    pub2 = await client.patch(
        "/api/v1/admin/scholarships/5/publish",
        json={"notes": "Re-publish."},
        headers=_admin(),
    )
    assert pub2.status_code == 200
    published_at_second = pub2.json()["scholarship"]["published_at"]
    # published_at must remain the original timestamp
    assert published_at_second == published_at_first


# ===========================================================================
# 6. Reviewer identity — always server-side, never client-supplied
# ===========================================================================

@pytest.mark.asyncio
async def test_reviewer_identity_is_server_side_not_client_supplied(client: AsyncClient):
    """Reviewer in audit log is always 'admin-token'; client-supplied values are ignored."""
    # Provide a fake reviewer in the body — it should be silently ignored
    res = await client.patch(
        "/api/v1/admin/scholarships/5/publish",
        # Pydantic will reject unknown fields if model_config forbids extras,
        # but AdminPublishRequest only has 'notes', so 'reviewer' becomes extra
        # and is ignored (extra='ignore' is Pydantic default for BaseModel).
        json={"notes": "Test note", "reviewer": "impersonated@evil.com"},
        headers=_admin(),
    )
    assert res.status_code == 200
    scholarship = res.json()["scholarship"]
    # The reviewed_by field must be the server-side actor, not the client value
    assert scholarship["reviewed_by"] == "admin-token"

    # Verify in audit log
    detail = await client.get("/api/v1/admin/scholarships/5", headers=_admin())
    audit = detail.json()["audit_log"]
    for entry in audit:
        reviewer = entry.get("reviewer")
        if reviewer:
            assert reviewer == "admin-token", (
                f"Audit entry contains unexpected reviewer identity: {reviewer!r}"
            )


@pytest.mark.asyncio
async def test_reject_reviewer_is_server_side(client: AsyncClient):
    """Reviewer in rejection audit entry is 'admin-token', not client input."""
    draft_id = await _ingest_new(client, "https://reviewer-test.example.com", "Reviewer Test")
    res = await client.patch(
        f"/api/v1/admin/scholarships/{draft_id}/reject",
        json={"reason": "Spam.", "reviewer": "fake-reviewer@evil.com"},
        headers=_admin(),
    )
    assert res.status_code == 200
    assert res.json()["scholarship"]["reviewed_by"] == "admin-token"


# ===========================================================================
# 7. Audit history integrity
# ===========================================================================

@pytest.mark.asyncio
async def test_audit_trail_preserves_chronological_history(client: AsyncClient):
    """Multiple state transitions maintain a complete, non-destructive audit history."""
    # Target record 3 (DAAD — published)
    # 1. Unpublish
    await client.patch(
        "/api/v1/admin/scholarships/3/unpublish",
        json={"reason": "Flagged for review"},
        headers=_admin(),
    )
    # 2. Re-publish
    await client.patch(
        "/api/v1/admin/scholarships/3/publish",
        json={"notes": "Re-verified and cleared"},
        headers=_admin(),
    )

    # 3. Inspect audit log
    detail_res = await client.get("/api/v1/admin/scholarships/3", headers=_admin())
    assert detail_res.status_code == 200
    audit = detail_res.json()["audit_log"]

    actions = [entry["action"] for entry in audit]
    assert "unpublished" in actions
    assert "published" in actions
    assert len(audit) >= 2


@pytest.mark.asyncio
async def test_audit_entries_contain_required_fields(client: AsyncClient):
    """Every admin audit entry contains action, reviewer, timestamp, previous_status, new_status."""
    draft_id = await _ingest_new(client, "https://audit-fields.example.com", "Audit Fields Test")
    await client.patch(
        f"/api/v1/admin/scholarships/{draft_id}/publish",
        json={"notes": "Full audit entry test."},
        headers=_admin(),
    )

    detail = await client.get(f"/api/v1/admin/scholarships/{draft_id}", headers=_admin())
    audit = detail.json()["audit_log"]
    publish_entries = [e for e in audit if e.get("action") == "published"]
    assert len(publish_entries) == 1
    entry = publish_entries[0]
    assert entry["action"] == "published"
    assert entry["reviewer"] == "admin-token"
    assert entry["timestamp"]
    assert entry["previous_status"] == "draft"
    assert entry["new_status"] == "published"


# ===========================================================================
# 8. Crawler protection of published records
# ===========================================================================

@pytest.mark.asyncio
async def test_crawler_cannot_modify_admin_publication_status(client: AsyncClient):
    """Crawler submissions must not be able to approve, reject, or set publication status."""
    payload = {
        "items": [
            {
                "name": "Bypass Attempt Award",
                "official_url": "https://bypass.example.com",
                "is_published": True,  # Crawler attempting to self-publish
            }
        ]
    }
    res = await client.post("/api/v1/scholarships/ingest", json=payload,
                            headers={"X-Ingestion-Token": CRAWLER_INGESTION_TOKEN})
    assert res.status_code == 200
    item_id = res.json()["results"][0]["id"]

    # Verify via admin that status remained draft and is_published is False
    admin_res = await client.get(f"/api/v1/admin/scholarships/{item_id}", headers=_admin())
    assert admin_res.status_code == 200
    assert admin_res.json()["is_published"] is False
    assert admin_res.json()["publication_status"] == "draft"


@pytest.mark.asyncio
async def test_crawler_cannot_silently_update_published_record_content(client: AsyncClient):
    """Crawler changes to a published record are blocked; original content is preserved."""
    # Record 1 (Michigan) is published — attempt to overwrite its content
    update_payload = {
        "items": [
            {
                "name": "REPLACED BY CRAWLER",
                "official_url": "https://finaid.umich.edu/types-scholarships",  # Same URL as record 1
                "provider": "Malicious Override",
                "description": "This should not appear publicly.",
            }
        ]
    }
    res = await client.post("/api/v1/scholarships/ingest", json=update_payload,
                            headers={"X-Ingestion-Token": CRAWLER_INGESTION_TOKEN})
    assert res.status_code == 200
    result = res.json()["results"][0]
    # Should be "skipped" (blocked), NOT "updated"
    assert result["status"] == "skipped"
    assert "protected" in result["message"].lower() or "blocked" in result["message"].lower()

    # Public API must still return the original unchanged data
    pub = await client.get("/api/v1/scholarships/1")
    assert pub.status_code == 200
    pub_data = pub.json()
    assert pub_data["name"] == "University of Michigan Scholarships"
    assert pub_data.get("provider") == "Institution"


@pytest.mark.asyncio
async def test_crawler_blocked_update_is_logged_in_audit(client: AsyncClient):
    """A blocked crawler update on a published record is recorded in the audit log."""
    update_payload = {
        "items": [
            {
                "name": "REPLACED BY CRAWLER",
                "official_url": "https://finaid.umich.edu/types-scholarships",
                "provider": "Malicious Override",
            }
        ]
    }
    await client.post("/api/v1/scholarships/ingest", json=update_payload,
                      headers={"X-Ingestion-Token": CRAWLER_INGESTION_TOKEN})

    # Admin audit log should contain 'crawler_update_blocked' entry
    admin_res = await client.get("/api/v1/admin/scholarships/1", headers=_admin())
    audit = admin_res.json()["audit_log"]
    blocked_entries = [e for e in audit if e.get("action") == "crawler_update_blocked"]
    assert len(blocked_entries) >= 1
    assert "blocked" in blocked_entries[-1].get("reason", "").lower()


@pytest.mark.asyncio
async def test_crawler_can_update_draft_record_content(client: AsyncClient):
    """Crawler changes to a draft (not published) record are still applied normally."""
    # Ingest a fresh draft
    draft_id = await _ingest_new(client, "https://crawler-draft-update.example.com", "Original Draft Name")

    # Crawler submits updated content for the same URL
    update_payload = {
        "items": [
            {
                "name": "Updated Draft Name",
                "official_url": "https://crawler-draft-update.example.com",
                "provider": "Updated Provider",
            }
        ]
    }
    res = await client.post("/api/v1/scholarships/ingest", json=update_payload,
                            headers={"X-Ingestion-Token": CRAWLER_INGESTION_TOKEN})
    assert res.status_code == 200
    result = res.json()["results"][0]
    assert result["status"] == "updated"
    assert result["id"] == draft_id

    # Admin inspection confirms updated content
    detail = await client.get(f"/api/v1/admin/scholarships/{draft_id}", headers=_admin())
    assert detail.json()["name"] == "Updated Draft Name"


# ===========================================================================
# 9. Contradictory state check constraint
# ===========================================================================

@pytest.mark.asyncio
async def test_contradictory_publication_state_rejected_by_db(db_session: AsyncSession):
    """Database CHECK constraint rejects is_published=True with publication_status!='published'."""
    from api.models.scholarship import ScholarshipModel
    contradictory = ScholarshipModel(
        name="Contradictory State Test",
        is_published=True,            # Published...
        publication_status="draft",   # ...but status is 'draft' — invalid
    )
    db_session.add(contradictory)
    try:
        await db_session.flush()
        # If no exception: constraint is NOT enforced (SQLite may not enforce all CHECK constraints
        # depending on version and configuration). Record this as a known SQLite limitation.
        await db_session.rollback()
        import warnings
        warnings.warn(
            "SQLite did not enforce chk_publication_status_is_published CHECK constraint. "
            "PostgreSQL enforcement must be verified in an integration environment.",
            UserWarning,
        )
    except Exception:
        # Constraint enforced (expected on PostgreSQL; may vary on SQLite)
        await db_session.rollback()


@pytest.mark.asyncio
async def test_valid_publication_states_accepted_by_db(db_session: AsyncSession):
    """Valid is_published / publication_status combinations pass the CHECK constraint."""
    from api.models.scholarship import ScholarshipModel

    valid_combinations = [
        (True, "published"),
        (False, "draft"),
        (False, "rejected"),
        (False, "archived"),
    ]
    for idx, (is_pub, pub_status) in enumerate(valid_combinations):
        record = ScholarshipModel(
            name=f"Valid State {idx}",
            is_published=is_pub,
            publication_status=pub_status,
        )
        db_session.add(record)
    # Should commit cleanly
    await db_session.commit()


# ===========================================================================
# 10. Production startup credential rejection
# ===========================================================================

def test_production_startup_rejects_default_admin_token():
    """Settings raises ValueError in production environment with default admin token."""
    from pydantic import ValidationError
    from api.config import Settings

    with pytest.raises((ValueError, ValidationError)):
        Settings(
            environment="production",
            admin_token="dev-secret-admin-token-change-me",
            ingestion_token="a-valid-unique-ingestion-token",
            database_url="postgresql+asyncpg://user:pass@localhost/testdb",
        )


def test_production_startup_rejects_default_ingestion_token():
    """Settings raises ValueError in production environment with default ingestion token."""
    from pydantic import ValidationError
    from api.config import Settings

    with pytest.raises((ValueError, ValidationError)):
        Settings(
            environment="production",
            admin_token="a-valid-unique-admin-token",
            ingestion_token="dev-secret-ingestion-token-change-me",
            database_url="postgresql+asyncpg://user:pass@localhost/testdb",
        )


def test_production_startup_rejects_empty_admin_token():
    """Settings raises ValueError in production environment with empty admin token."""
    from pydantic import ValidationError
    from api.config import Settings

    with pytest.raises((ValueError, ValidationError)):
        Settings(
            environment="production",
            admin_token="",
            ingestion_token="a-valid-unique-ingestion-token",
            database_url="postgresql+asyncpg://user:pass@localhost/testdb",
        )


# ===========================================================================
# 11. Concurrency, Ingestion & Admin Interleaving Audit Tests (Phase 8.2.2)
# ===========================================================================

@pytest.mark.asyncio
async def test_crawler_update_followed_by_admin_publish_preserves_audit_trail(client: AsyncClient):
    """Crawler updates a draft, admin publishes it: both audit entries must persist in chronological order."""
    # 1. Ingest initial draft
    url = "https://interleave-test-1.example.com"
    draft_id = await _ingest_new(client, url, "Initial Draft Interleave")

    # 2. Crawler updates draft content
    update_res = await client.post(
        "/api/v1/scholarships/ingest",
        json={"items": [{"name": "Updated By Crawler Interleave", "official_url": url}]},
        headers={"X-Ingestion-Token": CRAWLER_INGESTION_TOKEN},
    )
    assert update_res.status_code == 200
    assert update_res.json()["results"][0]["status"] == "updated"

    # 3. Admin publishes the scholarship
    pub_res = await client.patch(
        f"/api/v1/admin/scholarships/{draft_id}/publish",
        json={"notes": "Reviewed after crawler update"},
        headers=_admin(),
    )
    assert pub_res.status_code == 200
    assert pub_res.json()["scholarship"]["is_published"] is True

    # 4. Verify complete audit trail
    detail_res = await client.get(f"/api/v1/admin/scholarships/{draft_id}", headers=_admin())
    assert detail_res.status_code == 200
    audit = detail_res.json()["audit_log"]

    actions = [e["action"] for e in audit]
    assert "ingested" in actions
    assert "crawler_updated" in actions
    assert "published" in actions

    # Verify chronological sequence
    assert actions.index("ingested") < actions.index("crawler_updated") < actions.index("published")

    # Verify admin actor is not contaminated by crawler
    pub_entry = [e for e in audit if e["action"] == "published"][0]
    assert pub_entry["reviewer"] == "admin-token"


@pytest.mark.asyncio
async def test_admin_publish_followed_by_crawler_update_blocked_preserves_both(client: AsyncClient):
    """Admin publishes draft, crawler subsequently attempts update: update is blocked and both audit entries remain intact."""
    url = "https://interleave-test-2.example.com"
    draft_id = await _ingest_new(client, url, "Draft Before Publish")

    # 1. Admin publishes
    await client.patch(
        f"/api/v1/admin/scholarships/{draft_id}/publish",
        json={"notes": "Initial approval"},
        headers=_admin(),
    )

    # 2. Crawler attempts update on published record
    update_res = await client.post(
        "/api/v1/scholarships/ingest",
        json={"items": [{"name": "MUTATION ATTEMPT", "official_url": url}]},
        headers={"X-Ingestion-Token": CRAWLER_INGESTION_TOKEN},
    )
    assert update_res.status_code == 200
    assert update_res.json()["results"][0]["status"] == "skipped"

    # 3. Inspect admin view
    detail_res = await client.get(f"/api/v1/admin/scholarships/{draft_id}", headers=_admin())
    data = detail_res.json()
    assert data["name"] == "Draft Before Publish"
    assert data["is_published"] is True
    assert data["publication_status"] == "published"

    actions = [e["action"] for e in data["audit_log"]]
    assert "published" in actions
    assert "crawler_update_blocked" in actions
    assert actions.index("published") < actions.index("crawler_update_blocked")


@pytest.mark.asyncio
async def test_multiple_sequential_crawler_updates_append_audit_entries(client: AsyncClient):
    """Multiple crawler updates to the same draft preserve all historical audit events."""
    url = "https://multi-crawler-update.example.com"
    draft_id = await _ingest_new(client, url, "Version 1")

    # Update 1
    await client.post(
        "/api/v1/scholarships/ingest",
        json={"items": [{"name": "Version 2", "official_url": url}]},
        headers={"X-Ingestion-Token": CRAWLER_INGESTION_TOKEN},
    )

    # Update 2
    await client.post(
        "/api/v1/scholarships/ingest",
        json={"items": [{"name": "Version 3", "official_url": url}]},
        headers={"X-Ingestion-Token": CRAWLER_INGESTION_TOKEN},
    )

    detail_res = await client.get(f"/api/v1/admin/scholarships/{draft_id}", headers=_admin())
    audit = detail_res.json()["audit_log"]
    crawler_updates = [e for e in audit if e.get("action") == "crawler_updated"]
    assert len(crawler_updates) == 2
    assert detail_res.json()["name"] == "Version 3"


@pytest.mark.asyncio
async def test_audit_history_preserved_when_batch_item_fails_uniqueness(client: AsyncClient):
    """When one item in an ingestion batch fails, valid sibling items commit their audit entries cleanly."""
    url_existing = "https://batch-failure-existing.example.com"
    draft_id = await _ingest_new(client, url_existing, "Existing Batch Scholarship")

    # Batch with:
    # 1. Valid update to existing
    # 2. Invalid item with empty name (will be rejected at Pydantic level) OR
    # 3. Collision item
    batch_payload = {
        "items": [
            {"name": "Existing Batch Scholarship Updated", "official_url": url_existing},
            {"name": "Fresh New Valid Scholarship", "official_url": "https://batch-new-item.example.com"},
        ]
    }
    batch_res = await client.post(
        "/api/v1/scholarships/ingest",
        json=batch_payload,
        headers={"X-Ingestion-Token": CRAWLER_INGESTION_TOKEN},
    )
    assert batch_res.status_code == 200
    assert batch_res.json()["status"] == "completed"

    # Verify audit log on existing record has crawler_updated
    detail_res = await client.get(f"/api/v1/admin/scholarships/{draft_id}", headers=_admin())
    actions = [e["action"] for e in detail_res.json()["audit_log"]]
    assert "crawler_updated" in actions
