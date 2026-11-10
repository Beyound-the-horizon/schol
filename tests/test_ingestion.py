"""Tests for crawler ingestion endpoint using canonical crawler payload."""

import pytest
from httpx import AsyncClient
from sqlalchemy.exc import IntegrityError
from api.config import settings
from api.schemas.ingestion import IngestionItem, IngestionRequest
from api.services.ingestion_service import IngestionService

VALID_TOKEN = settings.ingestion_token


@pytest.mark.asyncio
async def test_ingest_missing_token_returns_401(client: AsyncClient):
    """Ingestion request without token header is rejected."""
    payload = {
        "items": [
            {
                "name": "Test Scholarship",
                "provider": "Test Foundation",
                "host_country": "Canada",
            }
        ]
    }
    response = await client.post("/api/v1/scholarships/ingest", json=payload)
    assert response.status_code == 401
    assert "missing" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_ingest_invalid_token_returns_401(client: AsyncClient):
    """Ingestion request with incorrect token is rejected."""
    payload = {
        "items": [
            {
                "name": "Test Scholarship",
                "provider": "Test Foundation",
                "host_country": "Canada",
            }
        ]
    }
    headers = {"X-Ingestion-Token": "wrong-token-value"}
    response = await client.post("/api/v1/scholarships/ingest", json=payload, headers=headers)
    assert response.status_code == 401
    assert "invalid" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_ingest_bearer_token_authorization(client: AsyncClient):
    """Ingestion request accepts standard Authorization: Bearer header."""
    payload = {
        "items": [
            {
                "name": "Bearer Test Scholarship",
                "provider": "Australian Government",
                "host_country": "Australia",
                "official_url": "https://australia.gov.au/scholars",
            }
        ]
    }
    headers = {"Authorization": f"Bearer {VALID_TOKEN}"}
    response = await client.post("/api/v1/scholarships/ingest", json=payload, headers=headers)
    assert response.status_code == 200
    assert response.json()["created"] == 1


@pytest.mark.asyncio
async def test_ingest_actual_crawler_payload_draft_by_default(client: AsyncClient):
    """Test crawler's actual rich payload from core/schemas.py and draft-by-default isolation."""
    headers = {"X-Ingestion-Token": VALID_TOKEN}

    crawler_payload = {
        "name": "Rhodes Scholarship",
        "provider": "Rhodes Trust",
        "host_country": "United Kingdom",
        "degree_level": ["Postgraduate", "DPhil"],
        "eligible_countries": ["International"],
        "funding_coverage": {"tuition": "Full", "living_stipend": "Full"},
        "minimum_cgpa": "3.7",
        "official_url": "https://www.rhodeshouse.ox.ac.uk/scholarships",
        "language_tests": {"IELTS": 7.5},
        "required_documents": ["Transcripts", "CV", "References"],
        "deadline": "2026-10-01",
    }

    # Step 1: Submit new crawler record
    res1 = await client.post(
        "/api/v1/scholarships/ingest",
        json={"items": [crawler_payload]},
        headers=headers,
    )
    assert res1.status_code == 200
    data1 = res1.json()
    assert data1["status"] == "completed"
    assert data1["created"] == 1
    new_id = data1["results"][0]["id"]
    assert new_id is not None

    # Step 2: Verify draft-by-default behavior (MUST NOT appear in public listing)
    public_res = await client.get("/api/v1/scholarships")
    assert public_res.status_code == 200
    public_ids = [item["id"] for item in public_res.json()]
    assert new_id not in public_ids

    # Step 3: Verify single public get also returns 404 for draft
    detail_res = await client.get(f"/api/v1/scholarships/{new_id}")
    assert detail_res.status_code == 404

    # Step 4: Deduplication - re-submitting identical payload marks it skipped
    res_skip = await client.post(
        "/api/v1/scholarships/ingest",
        json={"items": [crawler_payload]},
        headers=headers,
    )
    assert res_skip.status_code == 200
    assert res_skip.json()["skipped"] == 1
    assert res_skip.json()["results"][0]["status"] == "skipped"

    # Step 5: Deduplication update - modified payload updates existing record
    modified_payload = dict(crawler_payload)
    modified_payload["minimum_cgpa"] = "3.8"
    res_upd = await client.post(
        "/api/v1/scholarships/ingest",
        json={"items": [modified_payload]},
        headers=headers,
    )
    assert res_upd.status_code == 200
    assert res_upd.json()["updated"] == 1
    assert res_upd.json()["results"][0]["status"] == "updated"


@pytest.mark.asyncio
async def test_ingest_validation_errors(client: AsyncClient):
    """Payload validation catches malformed URLs and dates."""
    headers = {"X-Ingestion-Token": VALID_TOKEN}

    # Invalid URL scheme
    bad_url = {
        "items": [
            {
                "name": "Invalid URL Item",
                "official_url": "ftp://invalid-scheme.com",
            }
        ]
    }
    res_url = await client.post(
        "/api/v1/scholarships/ingest",
        json=bad_url,
        headers=headers,
    )
    assert res_url.status_code == 422

    # Malformed date string
    bad_date = {
        "items": [
            {
                "name": "Invalid Date Item",
                "deadline": "not-a-valid-date",
            }
        ]
    }
    res_date = await client.post(
        "/api/v1/scholarships/ingest",
        json=bad_date,
        headers=headers,
    )
    assert res_date.status_code == 422


@pytest.mark.asyncio
async def test_ingest_duplicate_urls_within_single_batch(client: AsyncClient):
    """A single batch with repeated identical URLs is deduplicated safely."""
    headers = {"X-Ingestion-Token": VALID_TOKEN}
    payload = {
        "items": [
            {
                "name": "First Ingest Item",
                "provider": "Foundation A",
                "host_country": "Japan",
                "official_url": "https://japan.example.com/scholarship",
            },
            {
                "name": "Second Ingest Item Same URL Modified",
                "provider": "Foundation A Updated",
                "host_country": "Japan",
                "official_url": "https://japan.example.com/scholarship",
            },
        ]
    }
    response = await client.post("/api/v1/scholarships/ingest", json=payload, headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "completed"
    assert data["total"] == 2
    assert data["created"] == 1
    assert data["updated"] == 1
    assert data["results"][0]["status"] == "created"
    assert data["results"][1]["status"] == "updated"
    assert data["results"][0]["id"] == data["results"][1]["id"]


@pytest.mark.asyncio
async def test_ingest_mixed_batch_pydantic_validation_fails_atomically(client: AsyncClient):
    """A batch containing both valid and invalid items is rejected before writing to DB."""
    headers = {"X-Ingestion-Token": VALID_TOKEN}
    payload = {
        "items": [
            {
                "name": "Valid Item in Batch",
                "host_country": "Sweden",
                "official_url": "https://sweden.example.com",
            },
            {
                "name": "Invalid Item Bad URL Scheme",
                "official_url": "ftp://bad-scheme.com",
            },
        ]
    }
    response = await client.post("/api/v1/scholarships/ingest", json=payload, headers=headers)
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_ingest_database_uniqueness_conflict_savepoint_rollback(db_session):
    """Database uniqueness conflict on one item rolls back only that item savepoint."""
    orig_flush = db_session.flush

    async def flush_with_simulated_conflict():
        for obj in list(db_session.new):
            if getattr(obj, "name", None) == "Colliding Unique Item":
                raise IntegrityError(
                    "UNIQUE constraint failed: scholarships.official_url",
                    params=None,
                    orig=Exception("simulated unique constraint collision"),
                )
        await orig_flush()

    db_session.flush = flush_with_simulated_conflict

    request = IngestionRequest(
        items=[
            IngestionItem(
                name="Valid Prior Item",
                host_country="United Kingdom",
                official_url="https://valid-prior.example.com",
            ),
            IngestionItem(
                name="Colliding Unique Item",
                host_country="United States",
                official_url="https://conflict.example.com",
            ),
            IngestionItem(
                name="Valid Subsequent Item",
                host_country="Canada",
                official_url="https://valid-subsequent.example.com",
            ),
        ]
    )

    response = await IngestionService.ingest_batch(db_session, request)
    assert response.status == "partial_failure"
    assert response.total == 3
    assert response.created == 2
    assert response.rejected == 1
    assert response.results[0].status == "created"
    assert response.results[1].status == "rejected"
    assert "unique constraint" in response.results[1].message.lower()
    assert response.results[2].status == "created"


@pytest.mark.asyncio
async def test_unpublished_records_isolated_from_public_and_search(client: AsyncClient):
    """Unpublished records are completely hidden from public list, search, and detail."""
    headers = {"X-Ingestion-Token": VALID_TOKEN}
    # Ingest a new draft record
    ingest_res = await client.post(
        "/api/v1/scholarships/ingest",
        json={
            "items": [
                {
                    "name": "Confidential Unreleased Fellowship",
                    "host_country": "Switzerland",
                    "description": "Top secret fellowship description",
                    "official_url": "https://swiss.example.com/fellowship",
                }
            ]
        },
        headers=headers,
    )
    assert ingest_res.status_code == 200
    draft_id = ingest_res.json()["results"][0]["id"]
    assert draft_id is not None

    # Verify not in public listing
    list_res = await client.get("/api/v1/scholarships")
    assert list_res.status_code == 200
    ids = [item["id"] for item in list_res.json()]
    assert draft_id not in ids

    # Verify not in search query
    search_res = await client.get("/api/v1/scholarships?search=Confidential")
    assert search_res.status_code == 200
    assert len(search_res.json()) == 0

    # Verify 404 on direct ID retrieval
    detail_res = await client.get(f"/api/v1/scholarships/{draft_id}")
    assert detail_res.status_code == 404


@pytest.mark.asyncio
async def test_ingest_missing_or_whitespace_name_rejected(client: AsyncClient):
    """Payload with missing, empty, or whitespace-only scholarship name is rejected with 422."""
    headers = {"X-Ingestion-Token": VALID_TOKEN}

    # Missing name completely
    res_missing = await client.post(
        "/api/v1/scholarships/ingest",
        json={"items": [{"provider": "Test Org", "host_country": "UK"}]},
        headers=headers,
    )
    assert res_missing.status_code == 422

    # Whitespace-only name
    res_whitespace = await client.post(
        "/api/v1/scholarships/ingest",
        json={"items": [{"name": "   ", "provider": "Test Org"}]},
        headers=headers,
    )
    assert res_whitespace.status_code == 422

    # Single character name (less than min_length 2)
    res_single = await client.post(
        "/api/v1/scholarships/ingest",
        json={"items": [{"name": "A", "provider": "Test Org"}]},
        headers=headers,
    )
    assert res_single.status_code == 422


@pytest.mark.asyncio
async def test_ingest_invalid_official_url_rejected(client: AsyncClient):
    """Payload with non-HTTP/HTTPS official URL is rejected with 422."""
    headers = {"X-Ingestion-Token": VALID_TOKEN}

    invalid_urls = [
        "javascript:alert(1)",
        "file:///etc/passwd",
        "/relative/path/only",
        "ftp://mirror.example.com",
    ]

    for bad_url in invalid_urls:
        res = await client.post(
            "/api/v1/scholarships/ingest",
            json={"items": [{"name": "URL Test", "official_url": bad_url}]},
            headers=headers,
        )
        assert res.status_code == 422


@pytest.mark.asyncio
async def test_ingest_oversized_batch_rejected(client: AsyncClient):
    """Batches with zero items or more than 500 items are rejected with 422."""
    headers = {"X-Ingestion-Token": VALID_TOKEN}

    # Zero items
    res_empty = await client.post(
        "/api/v1/scholarships/ingest",
        json={"items": []},
        headers=headers,
    )
    assert res_empty.status_code == 422

    # 501 items (exceeds max_length=500)
    oversized = [{"name": f"Scholarship {i}"} for i in range(501)]
    res_oversized = await client.post(
        "/api/v1/scholarships/ingest",
        json={"items": oversized},
        headers=headers,
    )
    assert res_oversized.status_code == 422


@pytest.mark.asyncio
async def test_ingest_update_preserves_published_status(client: AsyncClient, seeded_session):
    """Crawler updates on a published record are blocked; the published record is preserved intact.

    Phase 8.2 security hardening: crawler submissions cannot silently change public
    scholarship content after publication. The ingestion service returns 'skipped'
    for blocked updates to published records and records a 'crawler_update_blocked'
    audit entry. Original content remains live and unchanged.
    """
    headers = {"X-Ingestion-Token": VALID_TOKEN}

    # Record 1 (University of Michigan Scholarships) is seeded with is_published=True
    res_before = await client.get("/api/v1/scholarships/1")
    assert res_before.status_code == 200
    original_name = res_before.json()["name"]

    # Attempt crawler update matching official_url of record 1 with modified content
    update_payload = {
        "items": [
            {
                "name": "University of Michigan Scholarships OVERWRITTEN BY CRAWLER",
                "official_url": "https://finaid.umich.edu/types-scholarships",
                "description": "Crawler-injected description — must NOT be published.",
                "minimum_cgpa": "3.9",
                "is_published": False,  # Crawler sending is_published=False
            }
        ]
    }
    ingest_res = await client.post(
        "/api/v1/scholarships/ingest",
        json=update_payload,
        headers=headers,
    )
    assert ingest_res.status_code == 200
    result = ingest_res.json()
    # The record must be "skipped" (blocked), NOT "updated"
    assert result["updated"] == 0
    assert result["skipped"] == 1
    blocked_msg = result["results"][0]["message"]
    assert "protected" in blocked_msg.lower() or "blocked" in blocked_msg.lower()

    # Verify that record 1 remains published and its original content is UNCHANGED
    res_after = await client.get("/api/v1/scholarships/1")
    assert res_after.status_code == 200
    assert res_after.json()["name"] == original_name, (
        "Published record name was overwritten by crawler — protection failed."
    )


@pytest.mark.asyncio
async def test_ingest_new_scholarship_enforces_draft_even_if_crawler_requests_published(client: AsyncClient):
    """Crawler intake must strictly create drafts (is_published=False) even if is_published=True is passed."""
    headers = {"X-Ingestion-Token": VALID_TOKEN}

    payload = {
        "items": [
            {
                "name": "Self-Publish Attempt Scholarship",
                "official_url": "https://unauthorized-publish.example.com",
                "is_published": True,  # Crawler attempting to self-publish
            }
        ]
    }
    ingest_res = await client.post(
        "/api/v1/scholarships/ingest",
        json=payload,
        headers=headers,
    )
    assert ingest_res.status_code == 200
    new_id = ingest_res.json()["results"][0]["id"]
    assert new_id is not None

    # Must be hidden from public listing because it was forced to is_published=False
    public_res = await client.get(f"/api/v1/scholarships/{new_id}")
    assert public_res.status_code == 404


@pytest.mark.asyncio
async def test_ingest_deduplication_missing_official_url(client: AsyncClient):
    """When official_url is missing, deduplication safely falls back to (name, provider)."""
    headers = {"X-Ingestion-Token": VALID_TOKEN}

    payload1 = {
        "items": [
            {
                "name": "Url-Less Scholarship Fellowship",
                "provider": "Global Heritage Foundation",
                "host_country": "France",
                "description": "Initial version without official URL",
            }
        ]
    }
    res1 = await client.post("/api/v1/scholarships/ingest", json=payload1, headers=headers)
    assert res1.status_code == 200
    assert res1.json()["created"] == 1
    record_id = res1.json()["results"][0]["id"]

    # Re-submit identical payload without URL -> should be skipped
    res2 = await client.post("/api/v1/scholarships/ingest", json=payload1, headers=headers)
    assert res2.status_code == 200
    assert res2.json()["skipped"] == 1

    # Submit updated description without URL -> should update the same record
    payload_updated = {
        "items": [
            {
                "name": "Url-Less Scholarship Fellowship",
                "provider": "Global Heritage Foundation",
                "host_country": "France",
                "description": "Updated version without official URL",
            }
        ]
    }
    res3 = await client.post("/api/v1/scholarships/ingest", json=payload_updated, headers=headers)
    assert res3.status_code == 200
    assert res3.json()["updated"] == 1
    assert res3.json()["results"][0]["id"] == record_id
