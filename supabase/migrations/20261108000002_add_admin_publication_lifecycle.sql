-- Migration: Add Admin Review & Publication Lifecycle Tracking
-- File: supabase/migrations/20261108000002_add_admin_publication_lifecycle.sql
--
-- Safety notes:
--   - All ADD COLUMN statements use IF NOT EXISTS (re-entrant / idempotent).
--   - The DEFAULT 'draft' on publication_status will initially populate ALL rows
--     (including already-published rows) with 'draft'. The UPDATE statements
--     below immediately correct that for pre-existing rows BEFORE the CHECK
--     constraint is added, which would otherwise block the transaction.
--   - DO NOT apply this migration to production without first verifying that
--     the backfill UPDATE rows are correct in a staging environment.
--
-- Rollback (down migration):
--   ALTER TABLE public.scholarships DROP CONSTRAINT IF EXISTS chk_publication_status_is_published;
--   DROP INDEX IF EXISTS idx_scholarships_publication_status;
--   ALTER TABLE public.scholarships
--       DROP COLUMN IF EXISTS audit_log,
--       DROP COLUMN IF EXISTS rejection_reason,
--       DROP COLUMN IF EXISTS published_at,
--       DROP COLUMN IF EXISTS reviewed_at,
--       DROP COLUMN IF EXISTS reviewed_by,
--       DROP COLUMN IF EXISTS publication_status;

-- Step 1: Add new columns (publication_status starts as 'draft' for all rows)
ALTER TABLE public.scholarships
    ADD COLUMN IF NOT EXISTS publication_status VARCHAR(50) NOT NULL DEFAULT 'draft',
    ADD COLUMN IF NOT EXISTS reviewed_by VARCHAR(200),
    ADD COLUMN IF NOT EXISTS reviewed_at TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS published_at TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS rejection_reason TEXT,
    ADD COLUMN IF NOT EXISTS audit_log JSONB DEFAULT '[]'::jsonb;

-- Step 2: Backfill - correct publication_status for already-published records.
-- Sets published_at from updated_at if available, otherwise falls back to NOW().
-- This MUST run before the CHECK constraint is added.
UPDATE public.scholarships
SET
    publication_status = 'published',
    published_at       = COALESCE(published_at, updated_at, created_at, NOW())
WHERE is_published = TRUE;

-- Step 3: Confirm all unpublished rows have a valid non-'published' status.
-- Rows already set to 'draft' by DEFAULT are correct. This is a no-op guard
-- in case a partial migration left any unexpected value.
UPDATE public.scholarships
SET publication_status = 'draft'
WHERE is_published = FALSE
  AND publication_status NOT IN ('draft', 'rejected', 'archived');

-- Step 4: Add CHECK constraint enforcing state-field consistency.
-- Only add if the constraint does not already exist (safe to re-run).
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conname = 'chk_publication_status_is_published'
          AND conrelid = 'public.scholarships'::regclass
    ) THEN
        ALTER TABLE public.scholarships
            ADD CONSTRAINT chk_publication_status_is_published CHECK (
                (is_published = TRUE  AND publication_status = 'published') OR
                (is_published = FALSE AND publication_status IN ('draft', 'rejected', 'archived'))
            );
    END IF;
END$$;

-- Step 5: Index publication_status for fast administrative queue queries
CREATE INDEX IF NOT EXISTS idx_scholarships_publication_status
    ON public.scholarships (publication_status);

