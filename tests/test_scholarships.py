"""Tests for public /api/v1/scholarships endpoints and canonical projections."""

from datetime import date
import pytest
from httpx import AsyncClient
from api.schemas.scholarship import (
    derive_eligibility,
    derive_location,
    derive_offer,
    derive_organization,
    format_calendar_date,
)


@pytest.mark.asyncio
async def test_list_scholarships_plain_array(client: AsyncClient):
    """Listing scholarships returns a plain JSON array matching frontend 7-field contract."""
    response = await client.get("/api/v1/scholarships")
    assert response.status_code == 200

    data = response.json()
    assert isinstance(data, list)
    assert len(data) == 4  # 4 published items, 1 draft excluded

    # Verify required 7 fields on every record
    for item in data:
        assert isinstance(item["id"], int)
        assert isinstance(item["name"], str)
        assert isinstance(item["location"], str)
        assert isinstance(item["organization"], str)
        assert isinstance(item["offer"], str)
        assert isinstance(item["eligibility"], str)
        assert item["deadline"] is None or isinstance(item["deadline"], str)

    # Verify draft scholarship (id=5) is excluded from the public feed
    ids = [item["id"] for item in data]
    assert 5 not in ids


@pytest.mark.asyncio
async def test_list_scholarships_projections(client: AsyncClient):
    """Verify projection from canonical crawler model to frontend fields."""
    response = await client.get("/api/v1/scholarships")
    assert response.status_code == 200

    data = response.json()
    michigan = next(item for item in data if "Michigan" in item["name"])
    assert michigan["location"] == "Michigan, United States"
    assert michigan["organization"] == "Institution"
    assert michigan["offer"] == "Fully-funded"
    assert "Min CGPA: 3.5" in michigan["eligibility"]
    assert michigan["deadline"] == "2027-03-20"


@pytest.mark.asyncio
async def test_calendar_date_no_timezone_shift():
    """Verify calendar-date serialization does not alter dates with timezone shifts."""
    d = date(2027, 3, 20)
    formatted = format_calendar_date(d)
    assert formatted == "2027-03-20"
    assert format_calendar_date(None) is None


@pytest.mark.asyncio
async def test_projection_fallbacks():
    """Verify safe fallbacks when provider, host_country, or funding are missing."""
    assert derive_location(None) == "Global / Unspecified"
    assert derive_location("   ") == "Global / Unspecified"
    assert derive_location("Canada") == "Canada"

    assert derive_organization(None) == "Unknown Provider"
    assert derive_organization("Oxford") == "Oxford"

    assert derive_offer(None) == "Funding details in announcement"
    assert derive_offer({"tuition": "Full", "living_stipend": "Full"}) == "Fully-funded"
    assert derive_offer({"tuition": "Partial"}) == "Partial"
    assert derive_offer("Stipend only") == "Stipend only"

    assert derive_eligibility() == "See requirements in announcement"
    assert derive_eligibility(minimum_cgpa="3.8") == "Min CGPA: 3.8"


@pytest.mark.asyncio
async def test_list_scholarships_pagination_boundaries(client: AsyncClient):
    """Pagination parameters validate boundaries strictly."""
    res_limit = await client.get("/api/v1/scholarships?limit=2")
    assert res_limit.status_code == 200
    assert len(res_limit.json()) == 2

    # Boundary validation: limit=0 should be rejected with 422
    res_bad_low = await client.get("/api/v1/scholarships?limit=0")
    assert res_bad_low.status_code == 422

    # Boundary validation: limit=101 should be rejected with 422
    res_bad_high = await client.get("/api/v1/scholarships?limit=101")
    assert res_bad_high.status_code == 422


@pytest.mark.asyncio
async def test_list_scholarships_filters(client: AsyncClient):
    """Filter parameters match canonical columns accurately."""
    res_loc = await client.get("/api/v1/scholarships?location=Germany")
    assert res_loc.status_code == 200
    items = res_loc.json()
    assert len(items) == 1
    assert "DAAD" in items[0]["name"]

    res_org = await client.get("/api/v1/scholarships?organization=Government")
    assert res_org.status_code == 200
    items = res_org.json()
    assert len(items) == 1
    assert "Chevening" in items[0]["name"]

    res_search = await client.get("/api/v1/scholarships?search=Mastercard")
    assert res_search.status_code == 200
    items = res_search.json()
    assert len(items) == 1
    assert "Mastercard" in items[0]["name"]


@pytest.mark.asyncio
async def test_get_scholarship_by_id_success(client: AsyncClient):
    """Retrieving a valid scholarship returns detailed representation with canonical fields."""
    response = await client.get("/api/v1/scholarships/1")
    assert response.status_code == 200

    item = response.json()
    assert item["id"] == 1
    assert item["name"] == "University of Michigan Scholarships"
    assert item["host_country"] == "Michigan, United States"
    assert item["provider"] == "Institution"
    assert item["official_url"] == "https://finaid.umich.edu/types-scholarships"
    assert item["degree_level"] == ["Bachelor's", "Master's"]


@pytest.mark.asyncio
async def test_get_scholarship_by_id_not_found(client: AsyncClient):
    """Non-existent ID returns 404."""
    response = await client.get("/api/v1/scholarships/99999")
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_get_scholarship_unpublished_returns_404(client: AsyncClient):
    """Draft / unpublished scholarship record returns 404 on public retrieval."""
    response = await client.get("/api/v1/scholarships/5")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_cors_headers(client: AsyncClient):
    """CORS headers are returned for allowed origins."""
    headers = {"Origin": "http://localhost:5173"}
    response = await client.get("/api/v1/scholarships", headers=headers)
    assert response.status_code == 200
    assert response.headers.get("access-control-allow-origin") == "http://localhost:5173"


@pytest.mark.asyncio
async def test_course_filter_matches(client: AsyncClient):
    """Course filter returns only scholarships whose fields_of_study contain the term."""
    res = await client.get("/api/v1/scholarships?course=Computer Science")
    assert res.status_code == 200
    items = res.json()
    assert len(items) == 1
    assert "Michigan" in items[0]["name"]


@pytest.mark.asyncio
async def test_course_filter_multiple(client: AsyncClient):
    """Comma-separated course values match any of the listed courses."""
    res = await client.get("/api/v1/scholarships?course=Public Policy,Computer Science")
    assert res.status_code == 200
    items = res.json()
    names = [item["name"] for item in items]
    # Michigan (Computer Science) + Chevening (Public Policy) + DAAD (Public Policy)
    assert any("Michigan" in n for n in names)
    assert any("Chevening" in n for n in names)
    assert any("DAAD" in n for n in names)


@pytest.mark.asyncio
async def test_course_filter_no_match(client: AsyncClient):
    """Course filter with nonexistent term returns empty list."""
    res = await client.get("/api/v1/scholarships?course=Quantum Basketweaving")
    assert res.status_code == 200
    items = res.json()
    assert len(items) == 0


@pytest.mark.asyncio
async def test_fields_of_study_null_handled(client: AsyncClient):
    """Scholarship with null fields_of_study still appears in unfiltered listings."""
    res = await client.get("/api/v1/scholarships")
    assert res.status_code == 200
    items = res.json()
    mastercard = next(item for item in items if "Mastercard" in item["name"])
    assert mastercard is not None  # exists despite null fields_of_study


@pytest.mark.asyncio
async def test_courses_in_listing_response(client: AsyncClient):
    """ScholarshipRead listing includes courses and focusAreas fields."""
    res = await client.get("/api/v1/scholarships?envelope=true")
    assert res.status_code == 200
    data = res.json()
    items = data["items"]
    michigan = next(item for item in items if "Michigan" in item["name"])
    # Institution provider → courses populated from fields_of_study
    assert "courses" in michigan
    assert isinstance(michigan["courses"], list)
    assert len(michigan["courses"]) > 0

    mastercard = next(item for item in items if "Mastercard" in item["name"])
    # Null fields_of_study on a non-Institution → both courses and focusAreas are null
    assert mastercard["courses"] is None
    assert mastercard["focusAreas"] is None


@pytest.mark.asyncio
async def test_search_includes_fields_of_study(client: AsyncClient):
    """General search keyword matches against fields_of_study content."""
    res = await client.get("/api/v1/scholarships?search=Mechatronics")
    assert res.status_code == 200
    items = res.json()
    assert len(items) == 1
    assert "Michigan" in items[0]["name"]


@pytest.mark.asyncio
async def test_envelope_pagination_with_filters(client: AsyncClient):
    """Envelope response reflects filtered totals, not global totals."""
    res = await client.get("/api/v1/scholarships?envelope=true&location=Germany")
    assert res.status_code == 200
    data = res.json()
    assert data["pagination"]["total_records"] == 1
    assert data["pagination"]["total_pages"] == 1
    assert len(data["items"]) == 1


@pytest.mark.asyncio
async def test_offer_filter(client: AsyncClient):
    """Offer/funding filter correctly matches funding_coverage values."""
    res = await client.get("/api/v1/scholarships?offer=Partial")
    assert res.status_code == 200
    items = res.json()
    assert len(items) == 1
    assert "DAAD" in items[0]["name"]


@pytest.mark.asyncio
async def test_multi_location_filter(client: AsyncClient):
    """Comma-separated location filter matches any of the listed locations."""
    res = await client.get("/api/v1/scholarships?location=Germany,United Kingdom")
    assert res.status_code == 200
    items = res.json()
    names = [item["name"] for item in items]
    assert any("DAAD" in n for n in names)
    assert any("Chevening" in n for n in names)
    assert len(items) == 2
