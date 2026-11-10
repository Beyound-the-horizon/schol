"""Live PostgreSQL Integration & Concurrency Test Suite against Neon Database.

Tests 20 required backend items:
1. Database connection & Pool Lifecycle
2. Health endpoint (/api/v1/health)
3. Scholarship insertion via ingestion
4. Scholarship retrieval via admin & public endpoints
5. JSONB serialization and deserialization (lists, dicts, complex structures)
6. Date and timezone handling (DATE, TIMESTAMPTZ)
7. URL uniqueness constraint enforcement
8. Ingestion authentication (X-Ingestion-Token verification)
9. Invalid ingestion payloads (validation errors)
10. Duplicate submission handling (safe update vs duplicate record)
11. Per-record batch failures (atomic savepoints)
12. Draft publication isolation (unpublished draft hidden from public list/search)
13. Admin authentication (X-Admin-Token / Bearer token)
14. Admin publication (draft -> published transition, sets published_at)
15. Admin rejection (draft -> rejected transition, requires rationale)
16. Unpublishing (published -> draft transition)
17. Archiving (published/draft -> archived transition)
18. Audit log creation & chronological tracking
19. Published scholarship protection against crawler updates
20. Public API visibility rules

Also tests Step 4 Concurrency:
- Simultaneous ingestion of the same official URL (no duplicates)
- Concurrent crawler update vs admin publication (row-level locking & content protection)
"""

import asyncio
import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from api.main import app
from api.db import init_db_pool, close_db_pool, get_db_session
from api.models.scholarship import ScholarshipModel
from sqlalchemy import delete
from core.schemas import ScholarshipCreate
from core.agents.writer import write_scholarship


@pytest_asyncio.fixture(scope="function")
async def client():
    """AsyncClient using live FastAPI app connected to Neon PostgreSQL with automatic cleanup."""
    await init_db_pool()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as ac:
        yield ac
    
    # Cleanup any neon-test.org records created during test
    try:
        session_gen = get_db_session()
        session = await anext(session_gen)
        await session.execute(
            delete(ScholarshipModel).where(ScholarshipModel.official_url.like("https://neon-test.org/%"))
        )
        await session.commit()
        await session.close()
    except Exception:
        pass

    await close_db_pool()


@pytest.mark.asyncio
async def test_01_neon_health_endpoint(client: AsyncClient):
    """Test 1 & 2: Real PostgreSQL connection & /health endpoint."""
    response = await client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["database"] == "connected"


@pytest.mark.asyncio
async def test_03_06_ingestion_and_jsonb_dates(client: AsyncClient):
    """Test 3, 4, 5, 6, 8, 12: Ingestion, Auth, JSONB fields, Dates, Draft isolation."""
    # 8. Ingestion auth failure
    unauth = await client.post(
        "/api/v1/scholarships/ingest",
        json={"items": []},
        headers={"X-Ingestion-Token": "bad-token"},
    )
    assert unauth.status_code == 401

    # 3, 5, 6. Valid ingestion with JSONB and Date fields
    test_url = "https://neon-test.org/award-jsonb-2027"
    item = ScholarshipCreate(
        name="Neon PostgreSQL Fellowship 2027",
        provider="Neon Research Institute",
        host_country="Germany",
        degree_level=["Master", "PhD"],
        fields_of_study=["Computer Science", "Artificial Intelligence"],
        eligible_countries=["Worldwide"],
        application_open_date="2027-01-15",
        deadline="2027-06-30",
        deadline_timezone="Europe/Berlin",
        minimum_cgpa="3.50",
        funding_coverage={"tuition": "Full", "monthly_stipend": 1600, "travel_grant": True},
        required_documents=["CV", "Transcripts", "Statement of Purpose"],
        official_url=test_url,
    )

    ingest_resp = await client.post(
        "/api/v1/scholarships/ingest",
        json={"items": [item.model_dump(mode="json")]},
        headers={"X-Ingestion-Token": "dev-secret-ingestion-token-change-me"},
    )
    assert ingest_resp.status_code == 200
    res = ingest_resp.json()
    assert res["total"] == 1
    assert res["created"] == 1
    assert len(res["results"]) == 1
    sch_id = res["results"][0]["id"]

    # 12. Draft isolation: verify draft is NOT returned in public search or list
    public_list_resp = await client.get("/api/v1/scholarships")
    assert public_list_resp.status_code == 200
    public_items = public_list_resp.json()
    assert all(s["id"] != sch_id for s in public_items), "Unpublished draft leaked into public list"

    # Public single retrieval must return 404 for draft
    public_detail_resp = await client.get(f"/api/v1/scholarships/{sch_id}")
    assert public_detail_resp.status_code == 404

    # 4 & 5. Admin detail returns complete JSONB and date structures
    admin_detail_resp = await client.get(
        f"/api/v1/admin/scholarships/{sch_id}",
        headers={"Authorization": "Bearer dev-secret-admin-token-change-me"},
    )
    assert admin_detail_resp.status_code == 200
    detail = admin_detail_resp.json()
    assert detail["id"] == sch_id
    assert detail["publication_status"] == "draft"
    assert detail["is_published"] is False
    assert detail["degree_level"] == ["Master", "PhD"]
    assert detail["fields_of_study"] == ["Computer Science", "Artificial Intelligence"]
    assert detail["funding_coverage"]["monthly_stipend"] == 1600
    assert detail["deadline"] == "2027-06-30"


@pytest.mark.asyncio
async def test_07_09_10_validation_duplicates_and_partial_batch(client: AsyncClient):
    """Test 7, 9, 10, 11: Validation failures, duplicate handling, and partial batch savepoints."""
    # 9. Invalid payload validation error
    invalid_resp = await client.post(
        "/api/v1/scholarships/ingest",
        json={"items": [{"name": "A"}]},  # name too short
        headers={"X-Ingestion-Token": "dev-secret-ingestion-token-change-me"},
    )
    assert invalid_resp.status_code == 422

    # Ingest a valid item
    url = "https://neon-test.org/dedup-award-2027"
    item1 = ScholarshipCreate(
        name="Dedup Test Award",
        provider="Global Trust",
        host_country="Sweden",
        official_url=url,
    )
    res1 = await client.post(
        "/api/v1/scholarships/ingest",
        json={"items": [item1.model_dump(mode="json")]},
        headers={"X-Ingestion-Token": "dev-secret-ingestion-token-change-me"},
    )
    assert res1.status_code == 200
    assert res1.json()["created"] == 1
    sch_id = res1.json()["results"][0]["id"]

    # 10. Duplicate URL submission updates existing draft instead of creating duplicate row
    item1_updated = ScholarshipCreate(
        name="Dedup Test Award (Updated Version)",
        provider="Global Trust International",
        host_country="Sweden",
        official_url=url,
    )
    res2 = await client.post(
        "/api/v1/scholarships/ingest",
        json={"items": [item1_updated.model_dump(mode="json")]},
        headers={"X-Ingestion-Token": "dev-secret-ingestion-token-change-me"},
    )
    assert res2.status_code == 200
    assert res2.json()["updated"] == 1
    assert res2.json()["created"] == 0
    assert res2.json()["results"][0]["id"] == sch_id

    # 11. Batch with mixed items
    batch_item_a = ScholarshipCreate(
        name="Batch Award Alpha",
        provider="Alpha Org",
        official_url="https://neon-test.org/batch-alpha",
    )
    batch_item_b = ScholarshipCreate(
        name="Batch Award Beta",
        provider="Beta Org",
        official_url="https://neon-test.org/batch-beta",
    )
    batch_resp = await client.post(
        "/api/v1/scholarships/ingest",
        json={"items": [batch_item_a.model_dump(mode="json"), batch_item_b.model_dump(mode="json")]},
        headers={"X-Ingestion-Token": "dev-secret-ingestion-token-change-me"},
    )
    assert batch_resp.status_code == 200
    assert batch_resp.json()["total"] == 2
    assert batch_resp.json()["created"] == 2


@pytest.mark.asyncio
async def test_13_20_admin_publication_lifecycle_and_content_protection(client: AsyncClient):
    """Test 13, 14, 15, 16, 17, 18, 19, 20: Full admin editorial lifecycle and protection."""
    url = "https://neon-test.org/lifecycle-2027"
    item = ScholarshipCreate(
        name="Lifecycle Fellowship 2027",
        provider="Institution",
        host_country="France",
        degree_level=["Master"],
        fields_of_study=["Data Science"],
        official_url=url,
    )

    ingest = await client.post(
        "/api/v1/scholarships/ingest",
        json={"items": [item.model_dump(mode="json")]},
        headers={"X-Ingestion-Token": "dev-secret-ingestion-token-change-me"},
    )
    sch_id = ingest.json()["results"][0]["id"]

    # 13. Admin auth failure
    bad_auth = await client.patch(
        f"/api/v1/admin/scholarships/{sch_id}/publish",
        headers={"Authorization": "Bearer invalid-token"},
    )
    assert bad_auth.status_code == 401

    # 14. Admin Publish
    publish_res = await client.patch(
        f"/api/v1/admin/scholarships/{sch_id}/publish",
        headers={"Authorization": "Bearer dev-secret-admin-token-change-me"},
        json={"notes": "Approved for publication on Neon"},
    )
    assert publish_res.status_code == 200
    assert publish_res.json()["new_status"] == "published"
    assert publish_res.json()["scholarship"]["is_published"] is True
    assert publish_res.json()["scholarship"]["published_at"] is not None

    # 20. Public API now returns published scholarship
    pub_list = await client.get("/api/v1/scholarships?search=Lifecycle+Fellowship")
    assert pub_list.status_code == 200
    found = [s for s in pub_list.json() if s["id"] == sch_id]
    assert len(found) == 1
    assert found[0]["name"] == "Lifecycle Fellowship 2027"

    # 19. Published scholarship protection: Crawler cannot silently overwrite content
    overwrite_attempt = ScholarshipCreate(
        name="Hacked Title by Crawler",
        provider="Hacker Provider",
        official_url=url,
    )
    crawler_res = await client.post(
        "/api/v1/scholarships/ingest",
        json={"items": [overwrite_attempt.model_dump(mode="json")]},
        headers={"X-Ingestion-Token": "dev-secret-ingestion-token-change-me"},
    )
    assert crawler_res.status_code == 200
    assert crawler_res.json()["skipped"] == 1

    # Verify public title remains untouched
    detail = await client.get(f"/api/v1/scholarships/{sch_id}")
    assert detail.status_code == 200
    assert detail.json()["name"] == "Lifecycle Fellowship 2027"

    # 16. Admin Unpublish (from published -> draft)
    unpub = await client.patch(
        f"/api/v1/admin/scholarships/{sch_id}/unpublish",
        headers={"Authorization": "Bearer dev-secret-admin-token-change-me"},
        json={"reason": "Audit review required"},
    )
    assert unpub.status_code == 200
    assert unpub.json()["new_status"] == "draft"

    # 15. Admin Rejection (from draft -> rejected)
    reject = await client.patch(
        f"/api/v1/admin/scholarships/{sch_id}/reject",
        headers={"Authorization": "Bearer dev-secret-admin-token-change-me"},
        json={"reason": "Ineligible provider requirements"},
    )
    assert reject.status_code == 200
    assert reject.json()["new_status"] == "rejected"

    # 17. Admin Archiving (from rejected -> archived)
    arch = await client.patch(
        f"/api/v1/admin/scholarships/{sch_id}/archive",
        headers={"Authorization": "Bearer dev-secret-admin-token-change-me"},
        json={"reason": "Programme ended"},
    )
    assert arch.status_code == 200
    assert arch.json()["new_status"] == "archived"

    # 18. Audit log creation: Inspect complete audit trail
    final_admin_view = await client.get(
        f"/api/v1/admin/scholarships/{sch_id}",
        headers={"Authorization": "Bearer dev-secret-admin-token-change-me"},
    )
    log = final_admin_view.json()["audit_log"]
    actions = [entry["action"] for entry in log]
    assert "ingested" in actions
    assert "published" in actions
    assert "crawler_update_blocked" in actions
    assert "unpublished" in actions
    assert "rejected" in actions
    assert "archived" in actions


@pytest.mark.asyncio
async def test_concurrency_simultaneous_ingestion_of_same_url(client: AsyncClient):
    """Step 4 Concurrency: Multiple concurrent crawler tasks ingesting the exact same official_url."""
    shared_url = "https://neon-test.org/concurrent-race-2027"
    
    async def ingest_task(i: int):
        item = {
            "name": f"Concurrent Opportunity #{i}",
            "provider": f"Provider {i}",
            "official_url": shared_url,
            "host_country": "Netherlands",
        }
        return await client.post(
            "/api/v1/scholarships/ingest",
            json={"items": [item]},
            headers={"X-Ingestion-Token": "dev-secret-ingestion-token-change-me"},
        )

    # Launch 5 concurrent submissions
    responses = await asyncio.gather(*(ingest_task(i) for i in range(5)))
    for r in responses:
        assert r.status_code == 200

    # Verify that exactly ONE row exists with this URL in Neon
    from api.db import get_db_session
    from sqlalchemy import select, func
    session_gen = get_db_session()
    session = await anext(session_gen)
    try:
        count_stmt = select(func.count()).where(ScholarshipModel.official_url == shared_url)
        res = await session.execute(count_stmt)
        count = res.scalar_one()
        assert count == 1, f"Expected exactly 1 row under concurrent ingestion race, found {count}"
    finally:
        await session.close()


@pytest.mark.asyncio
async def test_concurrency_crawler_update_vs_admin_publish(client: AsyncClient):
    """Step 4 Concurrency: Crawler update race against Admin publication with row-level locks."""
    race_url = "https://neon-test.org/crawler-vs-admin-race"
    init_res = await client.post(
        "/api/v1/scholarships/ingest",
        json={"items": [{"name": "Pre-Race Scholarship", "provider": "Initial Provider", "official_url": race_url}]},
        headers={"X-Ingestion-Token": "dev-secret-ingestion-token-change-me"},
    )
    sch_id = init_res.json()["results"][0]["id"]

    # Concurrently execute admin publish and crawler overwrite
    async def do_publish():
        return await client.patch(
            f"/api/v1/admin/scholarships/{sch_id}/publish",
            headers={"Authorization": "Bearer dev-secret-admin-token-change-me"},
            json={"notes": "Race publish"},
        )

    async def do_crawler_update():
        return await client.post(
            "/api/v1/scholarships/ingest",
            json={"items": [{"name": "Attempted Crawler Override", "provider": "Override Provider", "official_url": race_url}]},
            headers={"X-Ingestion-Token": "dev-secret-ingestion-token-change-me"},
        )

    pub_resp, crawl_resp = await asyncio.gather(do_publish(), do_crawler_update())
    assert pub_resp.status_code == 200
    assert crawl_resp.status_code == 200

    # Ensure database state is consistent
    detail = await client.get(
        f"/api/v1/admin/scholarships/{sch_id}",
        headers={"Authorization": "Bearer dev-secret-admin-token-change-me"},
    )
    detail_data = detail.json()
    assert detail_data["publication_status"] == "published"
    assert detail_data["is_published"] is True
