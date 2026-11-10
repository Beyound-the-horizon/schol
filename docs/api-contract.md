# Scholarship Platform — API Integration Contract

**Version:** 1.0.0  
**Base URL:** `/api/v1`  
**Default Local Port:** `http://localhost:8000`  
**Target Database:** Supabase Cloud PostgreSQL (`public.scholarships`)

---

## 1. Overview & Architecture

The backend API is implemented using **Python 3.12** and **FastAPI**. It serves two primary audiences:
1. **Frontend Application (Teammate 1 - Agoro)**: Consumes public read endpoints (`/scholarships`) to display scholarship feeds and details.
2. **Crawling Agent (Teammate 2 - Ayomide)**: Submits structured scholarship records via an authenticated batch endpoint (`/scholarships/ingest`).

---

## 2. Public Endpoints (Frontend Contract)

Public endpoints require **no authentication**. They only return active, published records (`is_published = true`).

### 2.1. Health Check

* **Method & Route:** `GET /api/v1/health`
* **Purpose:** Probes service operational status and actively checks database connectivity.

#### Response: Healthy (`200 OK`)
```json
{
  "status": "healthy",
  "environment": "development",
  "database": "connected",
  "version": "1.0.0"
}
```

#### Response: Database Unavailable (`503 Service Unavailable`)
```json
{
  "status": "degraded",
  "environment": "development",
  "database": "disconnected: ConnectionRefusedError",
  "version": "1.0.0"
}
```

---

### 2.2. List Published Scholarships

* **Method & Route:** `GET /api/v1/scholarships`
* **Response Format:** A plain JSON array of objects matching the frontend's 7 expected fields.
* **Query Parameters:**

| Parameter | Type | Default | Description |
| :--- | :--- | :--- | :--- |
| `limit` | `integer` (1-100) | `20` | Maximum items to return |
| `offset` | `integer` (>= 0) | `0` | Number of items to skip |
| `location` | `string` | `null` | Case-insensitive filter (e.g. `Germany`, `United Kingdom`) |
| `organization` | `string` | `null` | Filter by organization or provider type |
| `offer` | `string` | `null` | Filter by funding offer (e.g. `Fully-funded`, `Partial`) |
| `search` | `string` | `null` | Keyword search across title, description, and organization |
| `deadline_before`| `date` (YYYY-MM-DD)| `null` | Include scholarships with deadline on or before this date |
| `deadline_after` | `date` (YYYY-MM-DD)| `null` | Include scholarships with deadline on or after this date |

#### Example Request
```http
GET /api/v1/scholarships?location=Germany&offer=Partial HTTP/1.1
Host: localhost:8000
Accept: application/json
```

#### Example Response (`200 OK`)
```json
[
  {
    "id": 3,
    "name": "DAAD Helmut-Schmidt Programme",
    "location": "Germany",
    "organization": "Foundation",
    "offer": "Partial",
    "eligibility": "Not eligible",
    "deadline": "2027-08-31"
  }
]
```

> **Note on Deadlines:** Dates are returned strictly as ISO 8601 calendar strings (`YYYY-MM-DD`). Unknown, rolling, or unverified deadlines are returned as `null`. The frontend integration client formats `null` as `"Rolling / Open"` and parses valid ISO dates into friendly localized display strings.

---

### 2.3. Get Scholarship Details

* **Method & Route:** `GET /api/v1/scholarships/{id}`
* **Purpose:** Detailed view of an individual published scholarship.

#### Example Response (`200 OK`)
```json
{
  "id": 1,
  "name": "University of Michigan Scholarships",
  "location": "Michigan, United States",
  "organization": "Institution",
  "offer": "Fully-funded",
  "eligibility": "Eligible",
  "deadline": "2027-03-20",
  "official_url": "https://finaid.umich.edu/types-scholarships",
  "description": "Comprehensive merit support for undergraduate and graduate students.",
  "created_at": "2026-10-28T12:00:00Z",
  "updated_at": "2026-10-28T12:00:00Z"
}
```

#### Error Response: Not Found (`404 Not Found`)
```json
{
  "detail": "Scholarship with ID 999 not found."
}
```

---

## 3. Crawler Ingestion Endpoint (Crawler Teammate Contract)

> **Provisional Agreement:** This specification establishes the baseline HTTP interface for the crawling agent. Teammate 2 (Ayomide) can coordinate adjustments or extensions to this contract.

### 3.1. Ingest Batch

* **Method & Route:** `POST /api/v1/scholarships/ingest`
* **Authentication:** Required.
  * Header: `X-Ingestion-Token: <INGESTION_TOKEN>` or `Authorization: Bearer <INGESTION_TOKEN>`
* **Content-Type:** `application/json`

#### Request Schema
```json
{
  "items": [
    {
      "name": "string (1-500 chars, required)",
      "location": "string (1-255 chars, required)",
      "organization": "string (1-255 chars, required)",
      "offer": "string (1-100 chars, required)",
      "eligibility": "string (required)",
      "deadline": "YYYY-MM-DD (optional date, null if unknown)",
      "official_url": "https://... (optional URL, used for deduplication)",
      "description": "string (optional description or notes)",
      "is_published": true
    }
  ]
}
```

#### Deduplication & Idempotency Rules
1. **Primary Deduplication Key:** `official_url`.
2. If `official_url` is provided and already exists in the database:
   * **Identical Content:** Skipped without re-writing (`status: "skipped"`).
   * **Modified Content:** Record is updated with new details (`status: "updated"`).
3. If `official_url` is not in the database (or omitted):
   * Inserted as a new record (`status: "created"`).
4. If an item fails schema or database validation:
   * Item is isolated with a savepoint, marked as `"rejected"`, and does not abort the rest of the batch.

#### Example Request
```http
POST /api/v1/scholarships/ingest HTTP/1.1
Host: localhost:8000
Content-Type: application/json
X-Ingestion-Token: your-configured-ingestion-token

{
  "items": [
    {
      "name": "Gates Cambridge Scholarship",
      "location": "United Kingdom",
      "organization": "Foundation",
      "offer": "Fully-funded",
      "eligibility": "International applicants outside the UK",
      "deadline": "2027-01-05",
      "official_url": "https://www.gatescambridge.org",
      "description": "Full-cost scholarships for postgraduate study at Cambridge.",
      "is_published": true
    }
  ]
}
```

#### Example Response (`200 OK`)
```json
{
  "status": "completed",
  "total": 1,
  "created": 1,
  "updated": 0,
  "skipped": 0,
  "rejected": 0,
  "results": [
    {
      "index": 0,
      "name": "Gates Cambridge Scholarship",
      "status": "created",
      "id": 5,
      "message": "New scholarship record created"
    }
  ]
}
```

#### Error Response: Unauthorized (`401 Unauthorized`)
```json
{
  "detail": "Missing crawler ingestion token. Supply X-Ingestion-Token header."
}
```

---

## 4. Frontend Integration Guide

The frontend React application connects to the API via [`src/services/api.ts`](file:///c:/Users/user/Downloads/Schol/schol/src/services/api.ts).

* **Configuration Variable:** `VITE_API_BASE_URL` (Defaults to `http://localhost:8000/api/v1`).
* **Display Adaptation:** The client automatically adapts ISO dates to human-friendly local dates while gracefully displaying `"Rolling / Open"` for `null` deadlines.
* **Fault Tolerance:** If the backend is loading or unavailable, [`src/App.tsx`](file:///c:/Users/user/Downloads/Schol/schol/src/App.tsx) displays clean loading and connection warning states with a retry button.
