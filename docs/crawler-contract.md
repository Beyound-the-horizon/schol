# External Scholarship Crawler Integration Contract

**Specification Version:** 2.0.0  
**Service:** Scholarship Platform API  
**Target Endpoint:** `POST /api/v1/scholarships/ingest`  
**Default Base URL:** `http://localhost:8000/api/v1` (local) or configured API gateway URL  

---

## 1. Overview

This document specifies the exact contract for external crawler and scraper agents to submit discovered and structured scholarship opportunities into the platform backend.

No direct database credentials, SQL connections, or Supabase service keys are needed by the crawling service. All interaction occurs over authenticated HTTPS REST requests.

---

## 2. Authentication

Every ingestion request must include a secret token in an HTTP header. The backend accepts either:

1. **Custom Ingestion Header (Preferred):**
   ```http
   X-Ingestion-Token: YOUR_INGESTION_TOKEN_HERE
   ```
2. **Standard Authorization Bearer Header:**
   ```http
   Authorization: Bearer YOUR_INGESTION_TOKEN_HERE
   ```

*Requests missing this header or providing an invalid token receive `401 Unauthorized` with a standard `WWW-Authenticate` header.*

---

## 3. Request Specifications

* **HTTP Method:** `POST`
* **Route:** `/api/v1/scholarships/ingest`
* **Content-Type:** `application/json`
* **Batch Size Limits:**
  * **Minimum:** 1 item
  * **Maximum:** 500 items per request

Requests submitting empty batches (`{"items": []}`) or more than 500 items in a single call are rejected with `422 Unprocessable Entity`.

---

## 4. Payload Schema (`IngestionItem`)

Each element inside the `items` array represents a structured scholarship record.

### 4.1. Required Fields

| Field | Type | Rules | Description |
| :--- | :--- | :--- | :--- |
| `name` | `string` | Min 2 chars, max 300 chars, non-whitespace | Official title of the scholarship or award. |

### 4.2. Optional Canonical Fields

| Field | Type | Expected Format / Example | Description |
| :--- | :--- | :--- | :--- |
| `provider` | `string` | e.g. `"University of Oxford"`, `"DAAD"` | Institution, government, or foundation providing the award. |
| `host_country` | `string` | e.g. `"United Kingdom"`, `"Germany"` | Primary geographic location / host nation. |
| `official_url` | `string` | Absolute `http://` or `https://` URL | Canonical announcement / application URL. **Primary deduplication key.** |
| `deadline` | `string` | ISO date: `YYYY-MM-DD` (e.g. `"2027-03-31"`) | Application closing date. |
| `application_open_date` | `string` | ISO date: `YYYY-MM-DD` | Date applications officially open. |
| `deadline_timezone` | `string` | e.g. `"Europe/London"`, `"UTC"` | Timezone governing the deadline. |
| `degree_level` | `array[string]` | e.g. `["Master's", "PhD"]` | Targeted educational levels. |
| `eligible_countries` | `array[string]` | e.g. `["Nigeria", "Ghana", "International"]` | Nationalities eligible to apply. |
| `fields_of_study` | `array[string]` | e.g. `["Computer Science", "Public Policy"]` | Academic programs or focus disciplines. |
| `minimum_cgpa` | `string` | e.g. `"3.5/4.0"`, `"First Class"` | Minimum academic standing requirement. |
| `age_limit` | `string` | e.g. `"Under 30"`, `"None"` | Age limits, if any. |
| `other_eligibility` | `string` | Free text | Work experience, full-time enrollment, or special criteria. |
| `funding_coverage` | `object` / `string` | e.g. `{"tuition": "Full", "living_stipend": "Full"}` | Detailed financial coverage breakdown. |
| `award_duration` | `string` | e.g. `"2 Years"`, `"12 Months"` | Duration of funding support. |
| `language_tests` | `object` / `array` | e.g. `{"IELTS": 7.0, "TOEFL": 100}` | Minimum English/language exam thresholds. |
| `required_documents` | `array[string]` | e.g. `["CV", "Transcript", "Passport"]` | Required application materials. |
| `essay_requirements` | `object` / `array` | e.g. `{"statement": "500 words"}` | Statement of purpose / motivational essay prompts. |
| `referee_requirements` | `object` / `array` | e.g. `{"count": 2, "type": "Academic"}` | Letters of recommendation criteria. |
| `application_fee_and_effort`| `string` | e.g. `"Free"`, `"£50 application fee"` | Financial or time cost to apply. |
| `description` | `string` | Free text | High-level summary or overview notes. |
| `last_verified_at` | `string` | ISO 8601 timestamp (e.g. `"2026-11-08T18:00:00Z"`) | Timestamp when crawler extracted / verified information. |

---

## 5. Idempotency, Deduplication, & Update Rules

1. **Deduplication by `official_url`:**
   - If `official_url` matches an existing database record:
     - **Unchanged Content:** Record is skipped (`status: "skipped"`).
     - **Updated Content on a draft/rejected/archived record:** Record fields are refreshed (`status: "updated"`).
     - **Updated Content on a published record:** Update is **blocked** (`status: "skipped"`). See §5.1 below.
2. **Fallback Deduplication (when `official_url` is omitted):**
   - The backend checks for an existing record matching `name` and `provider`.
3. **Publication Safety (`is_published`):**
   - **New Records:** Always created with `is_published: false` (Draft). Crawler items never enter public listings without review.
   - **Existing Published Records:** Crawler updates to published scholarships are **blocked to protect public content**. See §5.1.
4. **Transaction Isolation & Fault Tolerance:**
   - Each item in a batch is isolated with a database transaction savepoint.
   - If one record in a batch fails a constraint or unique conflict, that single item is marked `rejected`, while all valid sibling records in the batch are committed.

### 5.1. Published Record Content Protection

> [!IMPORTANT]
> As of Phase 8.2, crawler updates to already-published scholarships are **blocked**. This prevents unreviewed crawler submissions from silently changing live public content.

**When a crawler submits changes to a published record:**

- The update is **not applied**.
- The response marks the item as `status: "skipped"` with a message explaining the block.
- A `crawler_update_blocked` audit entry is added to the scholarship's audit log.
- `last_verified_at` is updated (non-content metadata only).
- The original published content remains live and unchanged.

**Example blocked update response:**
```json
{
  "status": "completed",
  "total": 1,
  "created": 0,
  "updated": 0,
  "skipped": 1,
  "rejected": 0,
  "results": [
    {
      "index": 0,
      "name": "Chevening Scholarships",
      "status": "skipped",
      "id": 2,
      "message": "Published record protected: crawler changes blocked. Unpublish before applying crawler updates, or await pending-revision workflow (see admin contract §7)."
    }
  ]
}
```

**To apply crawler updates to a published record,** an administrator must:
1. Review the `crawler_update_blocked` audit entry.
2. Use `/unpublish` to revert the scholarship to `draft`.
3. The crawler may then re-submit — the draft will be updated normally.
4. The administrator re-reviews the updated draft and re-publishes.

A future pending-revision workflow (staging proposed changes in a `scholarship_pending_revisions` table for side-by-side admin review) is documented in `docs/admin-publication-contract.md §7` and deferred to a future phase.

---

## 6. Response Schema

### Success Response (`200 OK`)
```json
{
  "status": "completed",
  "total": 2,
  "created": 1,
  "updated": 1,
  "skipped": 0,
  "rejected": 0,
  "results": [
    {
      "index": 0,
      "name": "Rhodes Scholarship 2027",
      "status": "created",
      "id": 105,
      "message": "New draft scholarship record created (pending publication)"
    },
    {
      "index": 1,
      "name": "Chevening Scholarships",
      "status": "updated",
      "id": 2,
      "message": "Existing record updated from crawler data"
    }
  ]
}
```

### Partial Failure Response (`200 OK` with `status: "partial_failure"`)
When valid records are committed but one or more items violate constraints:
```json
{
  "status": "partial_failure",
  "total": 2,
  "created": 1,
  "updated": 0,
  "skipped": 0,
  "rejected": 1,
  "results": [
    {
      "index": 0,
      "name": "Valid Scholarship",
      "status": "created",
      "id": 106,
      "message": "New draft scholarship record created (pending publication)"
    },
    {
      "index": 1,
      "name": "Colliding Record",
      "status": "rejected",
      "id": null,
      "message": "Conflict: unique constraint or duplicate record collision on official_url."
    }
  ]
}
```

### Client Error Responses
* **`401 Unauthorized`:**
  ```json
  { "detail": "Missing crawler ingestion token. Supply X-Ingestion-Token header." }
  ```
* **`422 Unprocessable Entity`:**
  Returned when batch schema, dates, or URLs are invalid:
  ```json
  {
    "detail": [
      {
        "loc": ["body", "items", 0, "official_url"],
        "msg": "Value error, official_url must start with http:// or https://",
        "type": "value_error"
      }
    ]
  }
  ```

---

## 7. Integration Example

### cURL
```bash
curl -X POST "http://localhost:8000/api/v1/scholarships/ingest" \
  -H "Content-Type: application/json" \
  -H "X-Ingestion-Token: YOUR_INGESTION_TOKEN_HERE" \
  -d '{
    "items": [
      {
        "name": "Gates Cambridge Scholarship",
        "provider": "Bill and Melinda Gates Foundation",
        "host_country": "United Kingdom",
        "official_url": "https://www.gatescambridge.org/apply/",
        "deadline": "2027-01-07",
        "degree_level": ["Postgraduate", "PhD"],
        "eligible_countries": ["International"],
        "fields_of_study": ["Any Cambridge Postgraduate Program"],
        "funding_coverage": {
          "tuition": "Full",
          "stipend": "£21,000/yr",
          "airfare": "Return economy"
        },
        "minimum_cgpa": "3.8/4.0",
        "required_documents": ["CV", "Academic Transcripts", "Research Proposal", "References"],
        "last_verified_at": "2026-11-08T22:00:00Z"
      }
    ]
  }'
```

### Python (`requests` / `httpx`)
```python
import httpx

INGESTION_URL = "http://localhost:8000/api/v1/scholarships/ingest"
TOKEN = "YOUR_INGESTION_TOKEN_HERE"

payload = {
    "items": [
        {
            "name": "DAAD Helmut-Schmidt Programme",
            "provider": "German Academic Exchange Service",
            "host_country": "Germany",
            "official_url": "https://www.daad.de/helmut-schmidt",
            "deadline": "2027-07-31",
            "degree_level": ["Master's"],
            "fields_of_study": ["Public Policy", "Good Governance"],
            "funding_coverage": {"tuition": "Full", "monthly_stipend": "€934"},
        }
    ]
}

response = httpx.post(
    INGESTION_URL,
    json=payload,
    headers={"X-Ingestion-Token": TOKEN},
    timeout=15.0,
)

print(response.status_code, response.json())
```

