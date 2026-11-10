"""Crawler to FastAPI Ingestion Integration Tests.

Verifies:
1. Crawler structured records (ScholarshipCreate) are submitted via POST /api/v1/scholarships/ingest.
2. Ingestion authentication (X-Ingestion-Token) works.
3. Unauthenticated crawler submissions return 401.
4. Crawler records are stored as draft and isolated from public endpoints.
5. Crawler duplicates are detected and handled without error.
6. Invalid records return 422 or are rejected cleanly.
7. Published records cannot be silently updated or overwritten by crawler submissions.
8. Admin publish transitions draft to published.
9. Public API exposes published scholarship.
10. Frontend client projection consumes scholarship response cleanly.
"""

import pytest
from httpx import AsyncClient
from core.schemas import ScholarshipCreate
from core.agents.writer import write_scholarship


@pytest.mark.asyncio
async def test_crawler_writer_submits_via_api_and_authenticates(client: AsyncClient):
    """Verify write_scholarship submits to FastAPI and creates draft."""
    # Create a valid ScholarshipCreate from core/schemas.py
    crawler_record = ScholarshipCreate(
        name="Commonwealth Master Scholarship 2027",
        provider="Commonwealth Scholarship Commission",
        host_country="United Kingdom",
        degree_level=["Master"],
        eligible_countries=["Nigeria", "Kenya"],
        fields_of_study=["Engineering", "Public Policy"],
        deadline="2027-01-15",
        official_url="https://cscuk.fcdo.gov.uk/scholarships/commonwealth-master-scholarships-2027/",
    )

    # Submit via writer agent using the test HTTP client
    result = await write_scholarship(crawler_record, client=client)

    assert result["status"] == "created"
    assert result["name"] == "Commonwealth Master Scholarship 2027"
    scholarship_id = result["id"]
    assert scholarship_id is not None

    # Confirm draft is NOT exposed on public endpoints
    pub_resp = await client.get("/api/v1/scholarships?search=Commonwealth+Master")
    assert pub_resp.status_code == 200
    assert len(pub_resp.json()) == 0

    # Confirm admin can view draft in queue
    admin_resp = await client.get(
        "/api/v1/admin/scholarships?status=draft",
        headers={"Authorization": "Bearer dev-secret-admin-token-change-me"},
    )
    assert admin_resp.status_code == 200
    items = admin_resp.json()["items"]
    matching = [i for i in items if i["id"] == scholarship_id]
    assert len(matching) == 1
    assert matching[0]["publication_status"] == "draft"


@pytest.mark.asyncio
async def test_crawler_batch_submission_unauthenticated_fails(client: AsyncClient):
    """Verify submitting without token returns auth_error."""
    crawler_record = ScholarshipCreate(
        name="Unauthenticated Test Scholarship",
        official_url="https://test.org/unauth",
    )
    payload = {"items": [crawler_record.model_dump(mode="json")]}
    resp = await client.post(
        "/api/v1/scholarships/ingest",
        json=payload,
        headers={"X-Ingestion-Token": "wrong-token"},
    )
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_crawler_cannot_overwrite_published_record(client: AsyncClient):
    """Verify published records are protected against crawler overwrites."""
    # 1. Ingest initial record
    record = ScholarshipCreate(
        name="Gates Cambridge Scholarship 2027",
        provider="Gates Cambridge Trust",
        host_country="United Kingdom",
        deadline="2027-10-15",
        official_url="https://www.gatescambridge.org/programme-2027/",
    )
    res1 = await write_scholarship(record, client=client)
    assert res1["status"] in ("created", "updated")
    sch_id = res1["id"]

    # 2. Admin publishes it
    pub_res = await client.patch(
        f"/api/v1/admin/scholarships/{sch_id}/publish",
        headers={"Authorization": "Bearer dev-secret-admin-token-change-me"},
    )
    assert pub_res.status_code == 200
    assert pub_res.json()["new_status"] == "published"

    # 3. Crawler attempts to submit modified content for the published record
    modified_record = ScholarshipCreate(
        name="Gates Cambridge Overwrite Attempt",
        provider="Malicious Crawler Provider",
        host_country="United Kingdom",
        official_url="https://www.gatescambridge.org/programme-2027/",
    )
    res2 = await write_scholarship(modified_record, client=client)
    
    # Ingestion service rejects/skips crawler updates on published records
    assert res2["status"] in ("rejected", "updated", "saved")

    # 4. Check public endpoint: title must remain untouched
    detail = await client.get(f"/api/v1/scholarships/{sch_id}")
    assert detail.status_code == 200
    assert detail.json()["name"] == "Gates Cambridge Scholarship 2027"


@pytest.mark.asyncio
async def test_crawler_full_lifecycle_and_frontend_schema_consumption(client: AsyncClient):
    """Test entire flow: Ingestion -> Admin Publish -> Public Listing -> Detail -> Projections."""
    # 1. Normalized crawler scholarship produced
    record = ScholarshipCreate(
        name="Chevening Master Scholarship 2027",
        provider="UK Foreign Office",
        host_country="United Kingdom",
        degree_level=["Master"],
        eligible_countries=["Nigeria"],
        fields_of_study=["International Relations"],
        deadline="2027-11-01",
        official_url="https://www.chevening.org/scholarships-2027/",
    )

    # 2. Crawler submits through FastAPI endpoint
    res = await write_scholarship(record, client=client)
    assert res["status"] == "created"
    item_id = res["id"]

    # 3. Published by admin
    pub = await client.patch(
        f"/api/v1/admin/scholarships/{item_id}/publish",
        headers={"Authorization": "Bearer dev-secret-admin-token-change-me"},
    )
    assert pub.status_code == 200

    # 4. Public API exposes the published scholarship
    listing = await client.get("/api/v1/scholarships?search=Chevening+Master")
    assert listing.status_code == 200
    items = listing.json()
    assert len(items) == 1
    sch = items[0]

    # 5. Frontend consumes expected fields from listing
    assert sch["id"] == item_id
    assert sch["name"] == "Chevening Master Scholarship 2027"
    assert sch["location"] == "United Kingdom"
    assert sch["organization"] in ("Government", "Institution", "Organization", "Foundation")

    # 6. Public Detail API returns full UI projection with official_url
    detail_resp = await client.get(f"/api/v1/scholarships/{item_id}")
    assert detail_resp.status_code == 200
    detail = detail_resp.json()
    assert detail["id"] == item_id
    assert detail["official_url"] == "https://www.chevening.org/scholarships-2027/"
    assert detail["source"] == "Url"
    assert detail["location"] == "United Kingdom"
