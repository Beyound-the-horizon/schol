-- ==============================================================================
-- Development Seed Data: supabase/seed.sql
-- Description: Initial test scholarships matching canonical crawler model
--              and platform governance schema.
-- NOTE: For local development and testing environments only.
-- ==============================================================================

INSERT INTO public.scholarships (
    name,
    provider,
    host_country,
    degree_level,
    funding_coverage,
    minimum_cgpa,
    other_eligibility,
    deadline,
    official_url,
    description,
    is_published
)
VALUES
(
    'University of Michigan Scholarships',
    'Institution',
    'Michigan, United States',
    '["Bachelor''s", "Master''s"]'::jsonb,
    '{"tuition": "Full", "living_stipend": "Full"}'::jsonb,
    '3.5',
    'Enrolled full-time student',
    '2027-03-20',
    'https://finaid.umich.edu/types-scholarships',
    'Comprehensive merit and need-based support for international and domestic students at the University of Michigan.',
    TRUE
),
(
    'Chevening Scholarships',
    'Government',
    'United Kingdom',
    '["Master''s"]'::jsonb,
    '{"tuition": "Full", "living_stipend": "Full"}'::jsonb,
    'Upper Second-Class (2:1)',
    'Minimum two years of work experience',
    '2026-11-05',
    'https://www.chevening.org/scholarships',
    'UK government global scholarship programme offering future leaders the opportunity to study a one-year masters degree.',
    TRUE
),
(
    'DAAD Helmut-Schmidt Programme',
    'Foundation',
    'Germany',
    '["Master''s"]'::jsonb,
    '{"tuition": "Partial", "living_stipend": "Monthly allowance"}'::jsonb,
    'First or Upper Second',
    'Graduates from developing and emerging countries',
    '2027-08-31',
    'https://www.daad.de/helmut-schmidt',
    'Master of Public Policy and Good Governance scholarship programme for future leaders from developing countries.',
    TRUE
),
(
    'Mastercard Foundation Scholars Programme',
    'Foundation',
    'Multiple countries',
    '["Undergraduate", "Master''s"]'::jsonb,
    '"Fully-funded"'::jsonb,
    NULL,
    'Academically talented young people from Africa facing economic barriers',
    '2027-01-12',
    'https://mastercardfdn.org/all/scholars',
    'Education and leadership development initiative for talented young people primarily from Africa.',
    TRUE
)
ON CONFLICT (official_url) DO UPDATE SET
    name = EXCLUDED.name,
    provider = EXCLUDED.provider,
    host_country = EXCLUDED.host_country,
    degree_level = EXCLUDED.degree_level,
    funding_coverage = EXCLUDED.funding_coverage,
    minimum_cgpa = EXCLUDED.minimum_cgpa,
    other_eligibility = EXCLUDED.other_eligibility,
    deadline = EXCLUDED.deadline,
    description = EXCLUDED.description,
    is_published = EXCLUDED.is_published,
    updated_at = NOW();
