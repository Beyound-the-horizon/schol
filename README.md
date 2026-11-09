# Scholarship Platform

A modern scholarship discovery and curation platform connecting students with global funding opportunities. Built with a **React 19 / TypeScript** frontend and a **Python / FastAPI** backend backed by **Supabase Cloud PostgreSQL**.

---

## Architecture Overview

```
+-------------------------------------------------------------------------------+
|                               SCHOLARSHIP PLATFORM                            |
+-------------------------------------------------------------------------------+
|  React 19 + TypeScript (Vite)          |  Crawler Ingestion Agent (Python)    |
|  - Scholarship Feed Listing            |  - Discovers scholarships            |
|  - UI Design Tokens & Components       |  - Extracts structured fields        |
|  - Centralized API Service             |  - Authenticates via X-Ingestion-Token|
+----------------------------------------+--------------------------------------+
                    |                                        |
                    | GET /api/v1/scholarships               | POST /api/v1/scholarships/ingest
                    v                                        v
+-------------------------------------------------------------------------------+
|                             FastAPI Backend Service                           |
|  - Routers: Health, Public Scholarships, Authenticated Ingestion              |
|  - Deduplication & Upsert Logic (keyed on official_url)                       |
|  - Parameterized async SQLAlchemy & Pydantic v2 validation                    |
|  - CORS middleware allowing http://localhost:5173                             |
+-------------------------------------------------------------------------------+
                                        |
                                        v
+-------------------------------------------------------------------------------+
|                        Shared Supabase Cloud PostgreSQL                       |
|  - Table: public.scholarships                                                 |
|  - Seed: supabase/seed.sql (Development test data)                            |
|  - Versioned Migration: supabase/migrations/20261028000000_create_scholarships|
+-------------------------------------------------------------------------------+
```

---

## 1. Prerequisites

* **Python:** 3.12+
* **Node.js:** v20+ / v22+
* **Docker:** **Not required** for local development. (Tests run using isolated in-memory SQLite; production targets Supabase Cloud).

---

## 2. Environment Setup

### 2.1. Backend Setup

1. **Create and activate a virtual environment:**
   ```bash
   python -m venv .venv
   # Windows (PowerShell):
   .venv\Scripts\Activate.ps1
   # macOS / Linux:
   source .venv/bin/activate
   ```

2. **Install backend dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure environment variables:**
   ```bash
   cp .env.example .env
   ```
   Edit `.env` to configure your settings:
   * For local offline testing, leave `DATABASE_URL` empty or use `sqlite+aiosqlite:///./scholarships_dev.db`.
   * For Supabase Cloud, provide your database connection string:
     ```env
     DATABASE_URL=postgresql+asyncpg://postgres.[REF]:[PASSWORD]@aws-0-[REGION].pooler.supabase.com:6543/postgres
     ```
   * Set a secure ingestion token for crawler authorization:
     ```env
     INGESTION_TOKEN=your-secure-crawler-token
     ```

### 2.2. Frontend Setup

1. **Install Node dependencies:**
   ```bash
   npm install
   ```

2. **(Optional) Configure API Base URL:**
   By default, the frontend connects to `http://localhost:8000/api/v1`. If needed, create `.env.local`:
   ```env
   VITE_API_BASE_URL=http://localhost:8000/api/v1
   ```

---

## 3. Running Locally

### Start the Backend Service
```bash
python -m uvicorn api.main:app --reload --host 0.0.0.0 --port 8000
```
* **Interactive OpenAPI Swagger Docs:** [http://localhost:8000/api/v1/docs](http://localhost:8000/api/v1/docs)
* **ReDoc Documentation:** [http://localhost:8000/api/v1/redoc](http://localhost:8000/api/v1/redoc)

### Start the Frontend Application
In a separate terminal:
```bash
npm run dev
```
Open [http://localhost:5173](http://localhost:5173) in your browser.

---

## 4. Health Check Verification

Probe the service health endpoint to verify application and database status:
```bash
curl http://localhost:8000/api/v1/health
```

Expected response:
```json
{
  "status": "healthy",
  "environment": "development",
  "database": "connected",
  "version": "1.0.0"
}
```

---

## 5. Running Automated Tests

Run the full automated test suite (15 unit and API integration tests):
```bash
pytest -v
```

Tests run against an isolated in-memory database with zero external dependencies and cover:
* Health checks (healthy and database-degraded responses)
* Public scholarship listing, JSON formatting, and frontend field compatibility
* Pagination (`limit`, `offset`) and filtering (`location`, `organization`, `offer`, `search`, `deadline`)
* Single scholarship retrieval by numeric ID and 404 behavior
* Exclusion of unpublished draft records
* Crawler ingestion authentication (rejecting unauthorized requests, supporting `X-Ingestion-Token` and `Bearer`)
* Ingestion deduplication (insert new, skip unchanged, update modified on `official_url` match)
* Payload schema and malformed URL/date validation
* CORS preflight and response headers

---

## 6. Supabase Cloud Migration Guide

The database schema is defined in [`supabase/migrations/20261028000000_create_scholarships.sql`](supabase/migrations/20261028000000_create_scholarships.sql).

### Review and Approval Process
> **IMPORTANT:** In accordance with team safety protocols, migrations are **never applied automatically**. Always obtain explicit team approval before running migrations against the shared Supabase Cloud project.

### How to Apply the Migration to Supabase Cloud:
1. Log in to your [Supabase Dashboard](https://supabase.com/dashboard).
2. Select the project (`schol`).
3. Navigate to the **SQL Editor**.
4. Open or paste the contents of `supabase/migrations/20261028000000_create_scholarships.sql`.
5. Click **Run**.
6. (Optional Development Seed) To load the initial 4 development test records, execute `supabase/seed.sql` in the SQL Editor.

---

## 7. Crawler Ingestion Interface

Crawling agents submit scraped scholarship records to:
```http
POST /api/v1/scholarships/ingest
Content-Type: application/json
X-Ingestion-Token: <INGESTION_TOKEN>
```

Payload example:
```json
{
  "items": [
    {
      "name": "Chevening Scholarships",
      "location": "United Kingdom",
      "organization": "Government",
      "offer": "Fully-funded",
      "eligibility": "Eligible",
      "deadline": "2026-11-05",
      "official_url": "https://www.chevening.org/scholarships",
      "description": "UK government global scholarship programme.",
      "is_published": true
    }
  ]
}
```
For complete contract specifications, see [`docs/api-contract.md`](docs/api-contract.md).

---

## 8. Known Limitations & Teammate Coordination

1. **Crawler Ingestion Payload:** The ingestion contract is provisional until Teammate 2 (Ayomide) confirms the fields emitted by `core/agents/structurer.py`.
2. **Search Indexing:** Current keyword search uses PostgreSQL `ILIKE`. For large-scale production feeds, a `tsvector` full-text search index or pgvector similarity index can be added in a future migration.
3. **Database Mutation:** Shared cloud migrations require explicit review to ensure teammate access and existing tables are not disrupted.
