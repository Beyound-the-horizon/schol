-- ==============================================================================
-- Migration: 20261028000001_reconcile_canonical_scholarships.sql
-- Description: Non-destructive reconciliation migration adding governance and
--              audit columns to public.scholarships.
--
-- Supported Target Environments:
-- 1. Existing Supabase Cloud (table created with canonical crawler schema)
-- 2. Fresh installation (table created by 20261028000000_create_scholarships.sql)
-- 3. Legacy installation (table created with earlier flat backend prototype)
--
-- Invariants & Safety Guarantees:
-- - Invariant: Every non-null official_url must be unique; multiple NULLs permitted.
-- - Defaults is_published to FALSE for newly ingested crawler records.
-- - Preserves existing records, integer IDs, and sequences without recreation.
-- - Defensively relaxes legacy flat NOT NULL constraints per-column independently.
-- - Uses direct PostgreSQL index catalog relationships (pg_attribute on i.indexrelid
--   with attnum = 1) to identify exact single-key-column indexes without string parsing.
-- - Rejects partial, composite, invalid, and expression indexes as substitutes for
--   full single-column indexes.
-- ==============================================================================

-- Step 1: Ensure base table exists (with INTEGER primary key if fresh)
CREATE TABLE IF NOT EXISTS public.scholarships (
    id SERIAL PRIMARY KEY,
    name VARCHAR(300) NOT NULL
);

-- Step 2a: Add canonical crawler columns if missing (idempotent for fresh or partial schemas)
ALTER TABLE public.scholarships
    ADD COLUMN IF NOT EXISTS provider VARCHAR(300),
    ADD COLUMN IF NOT EXISTS host_country VARCHAR(100),
    ADD COLUMN IF NOT EXISTS degree_level JSONB,
    ADD COLUMN IF NOT EXISTS eligible_countries JSONB,
    ADD COLUMN IF NOT EXISTS fields_of_study JSONB,
    ADD COLUMN IF NOT EXISTS application_open_date DATE,
    ADD COLUMN IF NOT EXISTS deadline DATE,
    ADD COLUMN IF NOT EXISTS deadline_timezone VARCHAR(100),
    ADD COLUMN IF NOT EXISTS minimum_cgpa VARCHAR(100),
    ADD COLUMN IF NOT EXISTS age_limit VARCHAR(200),
    ADD COLUMN IF NOT EXISTS other_eligibility TEXT,
    ADD COLUMN IF NOT EXISTS language_tests JSONB,
    ADD COLUMN IF NOT EXISTS funding_coverage JSONB,
    ADD COLUMN IF NOT EXISTS award_duration VARCHAR(200),
    ADD COLUMN IF NOT EXISTS required_documents JSONB,
    ADD COLUMN IF NOT EXISTS essay_requirements JSONB,
    ADD COLUMN IF NOT EXISTS referee_requirements JSONB,
    ADD COLUMN IF NOT EXISTS application_fee_and_effort TEXT,
    ADD COLUMN IF NOT EXISTS official_url TEXT,
    ADD COLUMN IF NOT EXISTS last_verified_at TIMESTAMPTZ;

-- Step 2b: Defensively relax legacy flat NOT NULL constraints independently per column
-- Checks each legacy column individually so that missing or partially present columns
-- never cause migration failure.
DO $$
DECLARE
    col_name TEXT;
BEGIN
    FOREACH col_name IN ARRAY ARRAY['location', 'organization', 'offer', 'eligibility']
    LOOP
        IF EXISTS (
            SELECT 1 FROM information_schema.columns
            WHERE table_schema = 'public'
              AND table_name = 'scholarships'
              AND column_name = col_name
              AND is_nullable = 'NO'
        ) THEN
            EXECUTE format('ALTER TABLE public.scholarships ALTER COLUMN %I DROP NOT NULL;', col_name);
        END IF;
    END LOOP;
END $$;

-- Step 3: Add platform governance and lifecycle audit columns (Draft by default)
ALTER TABLE public.scholarships
    ADD COLUMN IF NOT EXISTS description TEXT,
    ADD COLUMN IF NOT EXISTS is_published BOOLEAN NOT NULL DEFAULT FALSE,
    ADD COLUMN IF NOT EXISTS created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW();

-- Ensure is_published defaults strictly to FALSE for new records even if the column pre-existed with another default
ALTER TABLE public.scholarships
    ALTER COLUMN is_published SET DEFAULT FALSE;

-- Step 4: Preserve existing unique constraint or full unique index on official_url
-- Invariant: Every non-null official_url must be unique, while multiple NULLs are allowed.
-- Catalog check requires:
-- 1. Table is public.scholarships: i.indrelid = 'public.scholarships'::regclass
-- 2. Valid and ready index: i.indisvalid = true AND i.indisready = true
-- 3. Enforces uniqueness: i.indisunique = true
-- 4. Full index covering all rows: i.indpred IS NULL (rejects partial indexes)
-- 5. Simple column, not an expression: i.indexprs IS NULL
-- 6. Strict single-key-column: i.indnkeyatts = 1 AND i.indnatts = 1 (rejects composite/include)
-- 7. Exact column on source table: a.attrelid = i.indrelid AND a.attnum = i.indkey[0] AND a.attname = 'official_url'
-- (Note: If duplicate non-null URLs already exist, creating the unique index will fail).
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM pg_index i
        JOIN pg_attribute a
          ON a.attrelid = i.indrelid
         AND a.attnum = i.indkey[0]
         AND a.attnum > 0
         AND NOT a.attisdropped
        WHERE i.indrelid = 'public.scholarships'::regclass
          AND i.indisunique = true
          AND i.indisvalid = true
          AND i.indisready = true
          AND i.indnkeyatts = 1
          AND i.indnatts = 1
          AND i.indexprs IS NULL
          AND i.indpred IS NULL
          AND a.attname = 'official_url'
    ) THEN
        CREATE UNIQUE INDEX idx_scholarships_official_url
            ON public.scholarships (official_url);
    END IF;
END $$;

-- Step 5: Conditionally add single-column query performance indexes using catalog metadata
-- Requires:
-- 1. Correct table: i.indrelid = 'public.scholarships'::regclass
-- 2. Valid and ready index: i.indisvalid = true AND i.indisready = true
-- 3. Strict single-key-column: i.indnkeyatts = 1 AND i.indnatts = 1 (rejects composite)
-- 4. Simple column, not an expression: i.indexprs IS NULL
-- 5. Full index, not partial: i.indpred IS NULL
-- 6. Exact column match on source table: a.attrelid = i.indrelid AND a.attnum = i.indkey[0]
DO $$
DECLARE
    target_col TEXT;
BEGIN
    FOREACH target_col IN ARRAY ARRAY['is_published', 'deadline', 'host_country', 'provider']
    LOOP
        IF NOT EXISTS (
            SELECT 1
            FROM pg_index i
            JOIN pg_attribute a
              ON a.attrelid = i.indrelid
             AND a.attnum = i.indkey[0]
             AND a.attnum > 0
             AND NOT a.attisdropped
            WHERE i.indrelid = 'public.scholarships'::regclass
              AND i.indisvalid = true
              AND i.indisready = true
              AND i.indnkeyatts = 1
              AND i.indnatts = 1
              AND i.indexprs IS NULL
              AND i.indpred IS NULL
              AND a.attname = target_col
        ) THEN
            EXECUTE format('CREATE INDEX idx_scholarships_%I ON public.scholarships (%I);', target_col, target_col);
        END IF;
    END LOOP;
END $$;

-- Step 6: Create or update automatic timestamp trigger function
CREATE OR REPLACE FUNCTION public.handle_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Step 7: Conditionally create trigger or raise exception on configuration conflict
DO $$
DECLARE
    v_existing_equivalent BOOLEAN;
    v_existing_conflicting BOOLEAN;
BEGIN
    SELECT EXISTS (
        SELECT 1 FROM pg_trigger
        WHERE tgname = 'set_scholarships_updated_at'
          AND tgrelid = 'public.scholarships'::regclass
          AND NOT tgisinternal
          AND tgenabled IN ('O', 'A')
          AND (tgtype & 127) = 19
          AND tgfoid = 'public.handle_updated_at'::regproc::oid
    ) INTO v_existing_equivalent;

    IF v_existing_equivalent THEN
        NULL;
    ELSE
        SELECT EXISTS (
            SELECT 1 FROM pg_trigger
            WHERE tgname = 'set_scholarships_updated_at'
              AND tgrelid = 'public.scholarships'::regclass
              AND NOT tgisinternal
        ) INTO v_existing_conflicting;

        IF v_existing_conflicting THEN
            RAISE EXCEPTION 'Conflicting trigger "set_scholarships_updated_at" exists on public.scholarships with incompatible timing, event, function, or status. Manual database-owner review required.';
        ELSE
            CREATE TRIGGER set_scholarships_updated_at
                BEFORE UPDATE ON public.scholarships
                FOR EACH ROW
                EXECUTE FUNCTION public.handle_updated_at();
        END IF;
    END IF;
END $$;

