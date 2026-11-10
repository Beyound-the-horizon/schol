# Scholarship Platform — Admin Review & Publication Lifecycle Contract

**Version:** 2.0.0 (Phase 8.2 — Integrity & Security Remediation)
**Target:** Editorial Administrators & Platform Management
**Base URL:** `http://localhost:8000/api/v1/admin/scholarships`
**Security Level:** Administrator Credentials Required (`ADMIN_TOKEN`)

---

## 1. Overview & Architecture

This document specifies the backend administrative workflow for reviewing, approving, rejecting, archiving, and publishing scholarship records ingested by external crawlers.

### Core Governance Principles

1. **Zero Public Leakage of Unapproved Data:** All crawler submissions default strictly to `is_published: false` and `publication_status: "draft"`. They are completely hidden from public search, feeds, and detail lookups.
2. **Dedicated Administrator Authorization:** Administrative endpoints require a dedicated `ADMIN_TOKEN`. The crawler ingestion token cannot access administrative routes.
3. **State-Machine Enforced Transitions:** Scholarship lifecycle transitions are strictly validated. Disallowed transitions return `HTTP 409 Conflict`. See §3 for the full matrix.
4. **Server-Side Audit Attribution:** All administrative decisions are recorded with a server-derived actor identifier. Client-supplied reviewer identities are not accepted.
5. **Immutable Audit Trail:** All decisions (approvals, rejections, unpublishing, archiving) are appended to an audit log. Entries are never deleted or modified.
6. **Published Record Protection:** Crawler updates to already-published scholarships are blocked. Original published content is preserved. See §7 for the pending-revision design.
7. **Database-Level Integrity Constraint:** A `CHECK` constraint (`chk_publication_status_is_published`) enforces that `is_published` and `publication_status` cannot contradict each other at the database layer.

---

## 2. Authentication & Authorization

All requests to `/api/v1/admin/scholarships` require an administrator token.

### Accepted Headers

1. **Primary Admin Header:**
   ```http
   X-Admin-Token: YOUR_ADMIN_TOKEN_HERE
   ```
2. **Standard Authorization Bearer Header:**
   ```http
   Authorization: Bearer YOUR_ADMIN_TOKEN_HERE
   ```

### Security Rules

- If no token is provided → `401 Unauthorized` (`Missing administrator authentication token`).
- If an invalid token is provided → `401 Unauthorized` (`Invalid administrator credentials`).
- If a crawler ingestion token is supplied → `401 Unauthorized` (`Crawler ingestion token cannot be used for administrative operations`).
- Verification uses `secrets.compare_digest` to prevent timing side-channel attacks.
- In `production` environments, the server fails fast at boot if `ADMIN_TOKEN` is unset or equals the development placeholder `"dev-secret-admin-token-change-me"`.

### Authentication Model Limitations (Shared Token)

> [!IMPORTANT]
> The current implementation uses a **shared static secret token** (`ADMIN_TOKEN`). It authenticates *possession of the token only*, not individual administrator identity.
>
> - There are **no individual administrator user accounts** or JWT claims.
> - The `reviewed_by` field in audit entries is always the server-side literal `"admin-token"`. It is **never accepted from client request bodies**; any `reviewer` field sent by a client is silently ignored.
> - All token holders share the same audit identity. Individual actions cannot be attributed to specific people.
> - Credential rotation requires updating the `ADMIN_TOKEN` environment variable and restarting the server. Zero-downtime rotation of multiple simultaneous tokens is not supported.
>
> **Recommended future upgrade:** Replace with individual administrator accounts using Supabase Auth JWTs and RBAC, where `reviewed_by` is derived from verified token claims.

---

## 3. Publication Lifecycle State Machine

### Supported Transitions

```mermaid
stateDiagram-v2
    [*] --> draft : Ingested by Crawler (is_published=false)
    draft --> published : Admin Approves /publish
    draft --> rejected : Admin Rejects /reject (reason required)
    draft --> archived : Admin Archives /archive
    published --> draft : Admin Unpublishes /unpublish
    published --> archived : Admin Archives /archive
    rejected --> archived : Admin Archives /archive
    archived --> draft : (restore — not yet implemented as separate endpoint)
```

| Lifecycle Status | `is_published` | `publication_status` | Visible on Public Feed? | Description |
| :--- | :---: | :---: | :---: | :--- |
| `draft` | `false` | `"draft"` | **No** | Newly discovered opportunity awaiting administrative verification. |
| `published` | `true` | `"published"` | **YES** | Verified, live scholarship accessible in public feeds and search. |
| `rejected` | `false` | `"rejected"` | **No** | Disqualified or invalid opportunity (spam, defunct portal, dead link). |
| `archived` | `false` | `"archived"` | **No** | Historical, obsolete, or lapsed award retained for institutional records. |

### Allowed Transition Matrix

| Current Status | `/publish` | `/reject` | `/unpublish` | `/archive` |
| :--- | :---: | :---: | :---: | :---: |
| `draft` | ✅ | ✅ | ❌ 409 | ✅ |
| `published` | ❌ 409 | ❌ 409 | ✅ | ✅ |
| `rejected` | ❌ 409 | ❌ 409 | ❌ 409 | ✅ |
| `archived` | ❌ 409 | ❌ 409 | ❌ 409 | ❌ 409 |

> [!NOTE]
> Transitioning `archived → draft` (restore) is defined in the state machine but is not yet implemented as a dedicated endpoint. To restore an archived record, use the standard publish flow after manually correcting `publication_status` via a database migration or future `/restore` endpoint.
>
> Transitioning `rejected → draft` (return to review) is similarly not yet implemented as a separate endpoint. Unpublish cannot be used on a rejected record (409 is returned). A future `/return-to-review` endpoint is recommended.

### Idempotency Rules

- **`published_at`** is set exactly once — when the scholarship is first published. Subsequent publish cycles (unpublish → re-publish) preserve the original `published_at` timestamp.
- Repeated identical actions (e.g. publishing an already-published record) return **`409 Conflict`** rather than silently succeeding.

---

## 4. Database Integrity Constraint

A PostgreSQL `CHECK` constraint enforces that `is_published` and `publication_status` cannot contradict each other:

```sql
CONSTRAINT chk_publication_status_is_published CHECK (
    (is_published = TRUE  AND publication_status = 'published') OR
    (is_published = FALSE AND publication_status IN ('draft', 'rejected', 'archived'))
)
```

This is enforced at the database layer independently of application logic, preventing bypass via direct SQL, raw migrations, or incomplete application code paths.

> [!WARNING]
> SQLite (used in isolated tests) may not enforce all `CHECK` constraints in older versions. Full enforcement is verified only on PostgreSQL. Run PostgreSQL integration tests before production deployment.

---

## 5. Administrative Endpoints

### 5.1. List Scholarships for Review

- **Route:** `GET /api/v1/admin/scholarships`
- **Query Parameters:**
  - `status`: Filter by status (`"draft"`, `"published"`, `"rejected"`, `"archived"`, or `"all"`). Default: `"draft"`.
  - `page`: Page number (1-based, default: `1`).
  - `limit`: Items per page (1–100, default: `20`).
  - `search`: Search keyword across `name`, `provider`, and `host_country`.
- **Response:**
  ```json
  {
    "items": [
      {
        "id": 105,
        "name": "Rhodes Scholarship 2027",
        "publication_status": "draft",
        "is_published": false,
        "reviewed_by": null,
        "reviewed_at": null,
        "published_at": null,
        "rejection_reason": null
      }
    ],
    "pagination": { "page": 1, "limit": 20, "total_records": 1, "total_pages": 1 },
    "status_counts": { "total": 12, "published": 4, "draft": 6, "rejected": 1, "archived": 1 }
  }
  ```

---

### 5.2. Get Scholarship Detail with Audit Trail

- **Route:** `GET /api/v1/admin/scholarships/{id}`
- **Response:** Returns all 24 canonical fields plus full `audit_log` array.

---

### 5.3. Approve and Publish Scholarship

- **Route:** `PATCH /api/v1/admin/scholarships/{id}/publish`
- **Allowed from:** `draft` only. Returns `409` otherwise.
- **Request Body (optional):**
  ```json
  { "notes": "Verified official announcement portal and degree eligibility." }
  ```
  > **Note:** A `reviewer` field in the request body is ignored. Actor is always `"admin-token"`.
- **Effect:**
  - `is_published` becomes `true`.
  - `publication_status` becomes `"published"`.
  - `published_at` is set once (never overwritten on re-publish).
  - `reviewed_by` is set to `"admin-token"`.
  - Appends `"action": "published"` to `audit_log`.

---

### 5.4. Reject Scholarship Draft

- **Route:** `PATCH /api/v1/admin/scholarships/{id}/reject`
- **Allowed from:** `draft` only. Returns `409` otherwise.
- **Request Body (mandatory `reason`):**
  ```json
  { "reason": "Official website is defunct and redirects to an advertisement." }
  ```
  > **Note:** A `reviewer` field in the request body is ignored. Actor is always `"admin-token"`.
- **Effect:**
  - `is_published` remains `false`.
  - `publication_status` becomes `"rejected"`.
  - `rejection_reason` is recorded.
  - Appends `"action": "rejected"` to `audit_log`.

---

### 5.5. Unpublish Scholarship

- **Route:** `PATCH /api/v1/admin/scholarships/{id}/unpublish`
- **Allowed from:** `published` only. Returns `409` otherwise.
- **Request Body (optional):**
  ```json
  { "reason": "Host university temporarily paused applications." }
  ```
  > **Note:** A `reviewer` field in the request body is ignored. Actor is always `"admin-token"`.
- **Effect:**
  - `is_published` becomes `false`.
  - `publication_status` becomes `"draft"`.
  - Appends `"action": "unpublished"` to `audit_log`.

---

### 5.6. Archive Scholarship

- **Route:** `PATCH /api/v1/admin/scholarships/{id}/archive`
- **Allowed from:** `draft`, `published`, `rejected`. Returns `409` if already archived.
- **Request Body (optional):**
  ```json
  { "reason": "Expired 2025 award cycle." }
  ```
  > **Note:** A `reviewer` field in the request body is ignored. Actor is always `"admin-token"`.
- **Effect:**
  - `is_published` becomes `false`.
  - `publication_status` becomes `"archived"`.
  - Appends `"action": "archived"` to `audit_log`.

---

## 6. Audit Trail Specification

Every record contains an `audit_log` JSON/JSONB array. Each entry:

```json
{
  "action": "published",
  "reviewer": "admin-token",
  "timestamp": "2026-11-08T23:30:00Z",
  "previous_status": "draft",
  "new_status": "published",
  "notes": "Verified official announcement portal and degree criteria."
}
```

### Key Properties

- **`reviewer`** is always `"admin-token"` (server-derived). It never contains a client-supplied value.
- **Historical entries are never deleted or truncated** during lifecycle updates.
- **Atomic commits:** Transitions and their audit entries are committed in the same database transaction.
- **Row locking:** `SELECT … FOR UPDATE` is acquired before reading and modifying `audit_log` on PostgreSQL to prevent lost-update race conditions on concurrent admin actions. *(Not enforced by SQLite in tests.)*

### Crawler Audit Events

| Action | Triggered by |
| :--- | :--- |
| `ingested` | New record submitted by crawler |
| `crawler_updated` | Draft record updated by crawler |
| `crawler_update_blocked` | Crawler attempted to update a published record (blocked) |

---

## 7. Pending Revisions for Published Records

### Current Behavior (Phase 8.2)

Crawler updates to **already-published** scholarships are **blocked**. The ingestion service:

1. Detects that the matched record has `is_published = True`.
2. Does **not** apply any field changes.
3. Records a `crawler_update_blocked` audit entry with a reason explaining the block.
4. Returns `status: "skipped"` for that item, with a message indicating that administrator review is required.
5. Updates `last_verified_at` only (non-content metadata).

The original published content remains live and unchanged until an administrator reviews it.

### Recommended Workflow for Pending Revisions

To review crawler-submitted changes to a published record:

1. Admin views the blocked `crawler_update_blocked` audit entry.
2. Admin uses `/unpublish` to revert the record to `draft`.
3. The crawler re-submits the update — this time succeeding (record is now a draft).
4. Admin reviews the updated draft and uses `/publish` to re-approve.

### Future Pending-Revision Workflow (Deferred from Phase 8.2)

A full pending-revision system would add a `scholarship_pending_revisions` table:

```sql
CREATE TABLE scholarship_pending_revisions (
    id              SERIAL PRIMARY KEY,
    scholarship_id  INTEGER NOT NULL REFERENCES public.scholarships(id),
    submitted_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    submitted_by    VARCHAR(50) DEFAULT 'crawler',
    revision_data   JSONB NOT NULL,          -- complete proposed field changes
    status          VARCHAR(20) DEFAULT 'pending',  -- pending | approved | rejected
    reviewed_by     VARCHAR(200),
    reviewed_at     TIMESTAMPTZ
);
```

This would allow admins to compare pending crawler changes against live content side-by-side without taking the scholarship offline. Implementation is deferred until a dedicated revision-review UI is available.

---

## 8. Migration Safety Notes

The migration `supabase/migrations/20261108000002_add_admin_publication_lifecycle.sql` is safe to apply to existing databases because:

1. All `ADD COLUMN IF NOT EXISTS` statements are re-entrant.
2. Existing published records (`is_published = TRUE`) are immediately backfilled with `publication_status = 'published'` and `published_at` before the `CHECK` constraint is applied.
3. The `CHECK` constraint is added only after all data is in a consistent state.
4. The constraint guard uses `DO $$ … IF NOT EXISTS … END$$` to prevent errors on re-application.

**Rollback DDL (down migration):**
```sql
ALTER TABLE public.scholarships DROP CONSTRAINT IF EXISTS chk_publication_status_is_published;
DROP INDEX IF EXISTS idx_scholarships_publication_status;
ALTER TABLE public.scholarships
    DROP COLUMN IF EXISTS audit_log,
    DROP COLUMN IF EXISTS rejection_reason,
    DROP COLUMN IF EXISTS published_at,
    DROP COLUMN IF EXISTS reviewed_at,
    DROP COLUMN IF EXISTS reviewed_by,
    DROP COLUMN IF EXISTS publication_status;
```
