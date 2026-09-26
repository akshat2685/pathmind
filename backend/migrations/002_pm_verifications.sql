-- ============================================================================
-- PATHMIND main product: user verification records (migration 002)
--
-- Creates the pm_verifications table for the main-product verification step
-- (sign in -> name -> aspiration -> status card -> VERIFICATION -> test ->
-- personalized path).
--
-- This migration is ADDITIVE and SAFE to run on the shared Supabase project:
--   * only the new pm_verifications table is created
--   * NO college tables are created, altered, or dropped
--   * NO existing tables, policies, or data are touched
-- College tables (curriculum_units, learning_resources, ...) are never referenced.
--
-- Backend access: service_role key only (see RLS policy below).
-- person_id = Supabase Auth user id. One active verification row per person
-- (unique constraint on person_id); resubmission upserts the row.
--
-- NOTE: this migration is NOT auto-applied. Apply via the Supabase Management
-- API when deploying the main product backend.
-- ============================================================================

-- Verification record: what the learner submitted to prove their status
-- (school marksheet details, college semester results, professional
-- experience, business details, ...). Documents themselves are stored as
-- URL references in document_urls (uploaded separately); only metadata and
-- self-declared values live in verification_data.
create table if not exists public.pm_verifications (
  id uuid not null default gen_random_uuid() primary key,
  person_id text not null,
  user_type text not null,
  verification_data jsonb not null default '{}'::jsonb,
  document_urls jsonb not null default '[]'::jsonb,
  status text not null default 'PENDING',
  verified_at timestamptz,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);
create index if not exists idx_pm_verifications_person_id on public.pm_verifications (person_id);
do $$ begin
  alter table public.pm_verifications add constraint pm_verifications_person_id_key unique (person_id);
exception when duplicate_object then null;
end $$;
alter table public.pm_verifications enable row level security;
drop policy if exists pm_verifications_service_all on public.pm_verifications;
create policy pm_verifications_service_all on public.pm_verifications
  for all to service_role using (true) with check (true);

-- Status values: PENDING (submitted, awaiting evaluation),
-- VERIFIED (deterministic checks passed), NEEDS_REVIEW (values look off,
-- human review), REJECTED (impossible/contradictory values).
do $$ begin
  alter table public.pm_verifications
    add constraint pm_verifications_status_check
    check (status in ('PENDING', 'VERIFIED', 'NEEDS_REVIEW', 'REJECTED'));
exception when duplicate_object then null;
end $$;
