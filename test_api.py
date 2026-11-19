"""
Live smoke and contract tests for the Scholarship AI Intelligence API.

Usage:
    pip install requests
    python test_live_api.py
    python test_live_api.py --base-url https://schol-api.vercel.app
    python test_live_api.py --include-ai      # also calls Gemini-backed endpoints (uses quota)

Exit code is 0 if no test failed, 1 otherwise. SKIP does not count as failure.
"""

import argparse
import sys
import time
from dataclasses import dataclass, field

import requests

PREFIX = "/api/v1"
EXPECTED_PATHS = [
    f"{PREFIX}/scholarships",
    f"{PREFIX}/scholarships/{{scholarship_id}}",
    f"{PREFIX}/scholarships/{{scholarship_id}}/guidance",
    f"{PREFIX}/guidance/preview",
    "/health",
]
GUIDANCE_KEYS = {
    "scholarship_id",
    "scholarship_name",
    "summary_explanation",
    "application_pattern",
    "total_applications_required",
    "active_apply_link",
    "workflow_phases",
    "timeline",
    "essay_requirements",
    "general_tips",
    "generated_at",
}
VALID_PATTERNS = {
    "SINGLE_PORTAL",
    "COURSE_FIRST_AUTOMATIC",
    "COURSE_FIRST_NOMINATED",
    "DUAL_APPLICATION",
}


class Skip(Exception):
    pass


@dataclass
class Runner:
    base: str
    timeout: float
    include_ai: bool
    results: list = field(default_factory=list)
    state: dict = field(default_factory=dict)
    session: requests.Session = field(default_factory=requests.Session)

    def url(self, path: str) -> str:
        return self.base.rstrip("/") + path

    def get(self, path: str, **kw):
        return self._timed("GET", path, **kw)

    def post(self, path: str, **kw):
        return self._timed("POST", path, **kw)

    def _timed(self, method: str, path: str, **kw):
        start = time.perf_counter()
        try:
            resp = self.session.request(method, self.url(path), timeout=self.timeout, **kw)
        except requests.ConnectionError:
            # A server error can close the keep-alive connection; retry once on a fresh one.
            self.session.close()
            resp = self.session.request(method, self.url(path), timeout=self.timeout, **kw)
        resp.elapsed_s = time.perf_counter() - start
        return resp

    def run(self, fn):
        name = fn.__name__.removeprefix("test_")
        try:
            detail = fn(self)
            self.results.append(("PASS", name, detail or ""))
        except Skip as e:
            self.results.append(("SKIP", name, str(e)))
        except AssertionError as e:
            self.results.append(("FAIL", name, str(e)))
        except requests.RequestException as e:
            self.results.append(("FAIL", name, f"request error: {e}"))
        except Exception as e:  # noqa: BLE001
            self.results.append(("FAIL", name, f"{type(e).__name__}: {e}"))
        status, _, detail = self.results[-1]
        print(f"[{status}] {name}" + (f" - {detail}" if detail else ""))


def body_preview(resp, n=200) -> str:
    return resp.text[:n].replace("\n", " ")


def expect_status(resp, expected, label=""):
    assert resp.status_code == expected, (
        f"{label}expected {expected}, got {resp.status_code}: {body_preview(resp)}"
    )


# ---------------------------------------------------------------- system routes

def test_root(r: Runner):
    resp = r.get("/")
    expect_status(resp, 200)
    data = resp.json()
    assert data.get("api_prefix") == PREFIX, f"api_prefix was {data.get('api_prefix')!r}"
    assert data.get("docs_url") == "/docs"
    assert data.get("health_url") == "/health"
    return f"{resp.elapsed_s:.2f}s (first request, includes any cold start)"


def test_health(r: Runner):
    resp = r.get("/health")
    expect_status(resp, 200)
    data = resp.json()
    assert data.get("status") == "healthy", data
    assert data.get("api_version") == "v1", data
    assert data.get("model"), "model field is empty, GEMINI_MODEL may be unset"
    return f"model={data['model']}, {resp.elapsed_s:.2f}s"


def test_docs_page(r: Runner):
    resp = r.get("/docs")
    expect_status(resp, 200)
    assert "text/html" in resp.headers.get("content-type", ""), resp.headers.get("content-type")


def test_openapi_lists_expected_routes(r: Runner):
    resp = r.get("/openapi.json")
    expect_status(resp, 200)
    paths = set(resp.json().get("paths", {}))
    missing = [p for p in EXPECTED_PATHS if p not in paths]
    assert not missing, f"missing routes: {missing}"


def test_unknown_route_returns_json_404(r: Runner):
    resp = r.get(f"{PREFIX}/does-not-exist")
    expect_status(resp, 404)
    assert "detail" in resp.json(), "404 body is not FastAPI JSON, rewrite may be misrouted"


def test_security_headers_and_https(r: Runner):
    if not r.base.startswith("https://"):
        raise Skip("not an https base url")
    resp = r.get("/health")
    assert resp.url.startswith("https://"), f"redirected to {resp.url}"


# ------------------------------------------------------------------------ cors

def test_cors_preflight(r: Runner):
    origin = "https://example-untrusted-origin.test"
    resp = r.session.options(
        r.url(f"{PREFIX}/scholarships"),
        headers={
            "Origin": origin,
            "Access-Control-Request-Method": "GET",
        },
        timeout=r.timeout,
    )
    allow = resp.headers.get("access-control-allow-origin")
    creds = resp.headers.get("access-control-allow-credentials")
    assert resp.status_code in (200, 204), f"preflight returned {resp.status_code}"
    assert allow != "*" or creds != "true", (
        "wildcard origin with credentials enabled"
    )
    assert allow != origin, (
        f"arbitrary origin {origin} is allowed (allow-origin={allow!r}, credentials={creds!r}); "
        "restrict ALLOWED_ORIGINS to your frontend domain"
    )
    return f"allow-origin={allow!r}"


# ----------------------------------------------------------- database endpoints

def test_list_scholarships(r: Runner):
    resp = r.get(f"{PREFIX}/scholarships", params={"limit": 5})
    expect_status(resp, 200, "database may be unreachable or DATABASE_URL unset: ")
    data = resp.json()
    for key in ("count", "limit", "offset", "scholarships"):
        assert key in data, f"missing key {key!r}"
    assert data["limit"] == 5 and data["offset"] == 0
    assert data["count"] == len(data["scholarships"])
    assert data["count"] <= 5
    if data["scholarships"]:
        item = data["scholarships"][0]
        for key in ("id", "name", "provider", "host_country", "deadline",
                    "official_url", "has_ai_guidance", "last_verified_at"):
            assert key in item, f"list item missing {key!r}"
        r.state["first_id"] = item["id"]
        r.state["ids"] = [s["id"] for s in data["scholarships"]]
    return f"{data['count']} rows, {resp.elapsed_s:.2f}s"


def test_list_is_ordered_by_id(r: Runner):
    ids = r.state.get("ids")
    if not ids:
        raise Skip("no scholarships returned")
    assert ids == sorted(ids), f"ids not ascending: {ids}"


def test_pagination_offset(r: Runner):
    if len(r.state.get("ids", [])) < 2:
        raise Skip("need at least 2 scholarships")
    a = r.get(f"{PREFIX}/scholarships", params={"limit": 1, "offset": 0}).json()
    b = r.get(f"{PREFIX}/scholarships", params={"limit": 1, "offset": 1}).json()
    assert a["scholarships"][0]["id"] != b["scholarships"][0]["id"], "offset had no effect"


def test_list_validation_rejects_bad_params(r: Runner):
    for params in ({"limit": 0}, {"limit": 101}, {"offset": -1}, {"limit": "abc"}):
        resp = r.get(f"{PREFIX}/scholarships", params=params)
        expect_status(resp, 422, f"params={params}: ")


def test_get_scholarship_detail(r: Runner):
    sid = r.state.get("first_id")
    if sid is None:
        raise Skip("no scholarship id available")
    resp = r.get(f"{PREFIX}/scholarships/{sid}")
    expect_status(resp, 200)
    data = resp.json()
    assert data.get("id") == sid
    for key in ("name", "official_url", "essay_requirements", "required_documents"):
        assert key in data, f"detail missing {key!r}"


def test_get_scholarship_not_found(r: Runner):
    resp = r.get(f"{PREFIX}/scholarships/2000000000")
    expect_status(resp, 404)
    assert "not found" in resp.json().get("detail", "").lower()


def test_get_scholarship_non_integer_id(r: Runner):
    resp = r.get(f"{PREFIX}/scholarships/not-a-number")
    expect_status(resp, 422)


def test_guidance_not_found_is_404(r: Runner):
    if not r.include_ai:
        raise Skip("use --include-ai to enable")
    resp = r.get(f"{PREFIX}/scholarships/2000000000/guidance")
    expect_status(resp, 404)


# ------------------------------------------------------------------ AI endpoints

def test_preview_validation_requires_name(r: Runner):
    resp = r.post(f"{PREFIX}/guidance/preview", json={"provider": "Test"})
    expect_status(resp, 422)


def assert_guidance_shape(data: dict):
    missing = GUIDANCE_KEYS - set(data)
    assert not missing, f"guidance missing keys: {sorted(missing)}"
    assert data["application_pattern"] in VALID_PATTERNS, data["application_pattern"]
    assert data["total_applications_required"] in (1, 2), data["total_applications_required"]
    assert data["active_apply_link"].get("primary_apply_url") is not None
    assert isinstance(data["workflow_phases"], list) and data["workflow_phases"], "no phases"
    assert data["timeline"].get("status") in {"OPEN", "UPCOMING", "CLOSED", "ROLLING"}, (
        data["timeline"].get("status")
    )


def test_preview_guidance_generation(r: Runner):
    if not r.include_ai:
        raise Skip("use --include-ai to enable (calls Gemini)")
    payload = {
        "scholarship_name": "Test Scholarship",
        "provider": "Example Foundation",
        "host_country": "Germany",
        "official_url": "https://example.org/scholarship",
        "other_eligibility": "Master's applicants with at least two years of work experience.",
        "required_documents": ["Transcript", "CV", "Motivation letter"],
    }
    resp = r.post(f"{PREFIX}/guidance/preview", json=payload)
    expect_status(resp, 200, "check GOOGLE_GEMINI_API and GEMINI_MODEL: ")
    assert_guidance_shape(resp.json())
    return f"{resp.elapsed_s:.1f}s"


def test_cached_guidance_for_first_scholarship(r: Runner):
    if not r.include_ai:
        raise Skip("use --include-ai to enable")
    sid = r.state.get("first_id")
    if sid is None:
        raise Skip("no scholarship id available")
    resp = r.get(f"{PREFIX}/scholarships/{sid}/guidance")
    expect_status(resp, 200)
    data = resp.json()
    assert_guidance_shape(data)
    assert data["scholarship_id"] == sid
    return f"{resp.elapsed_s:.1f}s"


TESTS = [
    test_root,
    test_health,
    test_docs_page,
    test_openapi_lists_expected_routes,
    test_unknown_route_returns_json_404,
    test_security_headers_and_https,
    test_cors_preflight,
    test_list_scholarships,
    test_list_is_ordered_by_id,
    test_pagination_offset,
    test_list_validation_rejects_bad_params,
    test_get_scholarship_detail,
    test_get_scholarship_not_found,
    test_get_scholarship_non_integer_id,
    test_preview_validation_requires_name,
    test_guidance_not_found_is_404,
    test_preview_guidance_generation,
    test_cached_guidance_for_first_scholarship,
]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    parser.add_argument("--base-url", default="https://schol-api.vercel.app")
    parser.add_argument("--timeout", type=float, default=60.0, help="per-request timeout in seconds")
    parser.add_argument("--include-ai", action="store_true", help="run Gemini-backed tests")
    args = parser.parse_args()

    print(f"Target: {args.base_url}  (ai tests: {'on' if args.include_ai else 'off'})\n")
    runner = Runner(base=args.base_url, timeout=args.timeout, include_ai=args.include_ai)
    for t in TESTS:
        runner.run(t)

    counts = {"PASS": 0, "FAIL": 0, "SKIP": 0}
    for status, _, _ in runner.results:
        counts[status] += 1
    print(f"\nSummary: {counts['PASS']} passed, {counts['FAIL']} failed, {counts['SKIP']} skipped")
    return 1 if counts["FAIL"] else 0


if __name__ == "__main__":
    sys.exit(main())