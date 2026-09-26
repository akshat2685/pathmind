-- ============================================================================
-- PATHMIND main product: aspiration test tables (migration 003)
--
-- Creates ONLY new pm_-prefixed tables for the main-product aspiration test
-- flow (sign in -> name -> aspiration -> status card -> verification -> TEST).
--
-- This migration is ADDITIVE and SAFE to run on the shared Supabase project:
--   * every table is prefixed pm_ (main-product namespace)
--   * NO college tables are created, altered, or dropped
--   * NO existing tables, policies, or data are touched
-- College tables (curriculum_units, learning_resources, ...) are never referenced.
--
-- Backend access: service_role key only (see RLS policies below).
-- person_id = Supabase Auth user id.
-- Both tables follow the uniform pm_ schema: id uuid PK, person_id text,
-- data jsonb, created_at. All test payloads live in data jsonb:
--   pm_aspiration_tests.data = {test_id, aspiration, stage, user_type,
--     verification_summary, questions (WITH correct answers), total_points}
--   pm_test_results.data     = {result_id, test_id, answers, score,
--     max_score, percentage, evaluation}
-- Correct answers are stored here but NEVER leave the backend: the API layer
-- strips them before responding.
--
-- NOT APPLIED to live DB by this commit. Apply via the same Management API
-- SQL path used for 001/002 only when the main product deploys.
-- ============================================================================

-- Aspiration tests (append; latest per person is the pending/active test)
create table if not exists public.pm_aspiration_tests (
  id uuid not null default gen_random_uuid() primary key,
  person_id text not null,
  data jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now()
);
create index if not exists idx_pm_aspiration_tests_person_id on public.pm_aspiration_tests (person_id);
alter table public.pm_aspiration_tests enable row level security;
drop policy if exists pm_aspiration_tests_service_all on public.pm_aspiration_tests;
create policy pm_aspiration_tests_service_all on public.pm_aspiration_tests
  for all to service_role using (true) with check (true);

-- Aspiration test results (append)
create table if not exists public.pm_test_results (
  id uuid not null default gen_random_uuid() primary key,
  person_id text not null,
  data jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now()
);
create index if not exists idx_pm_test_results_person_id on public.pm_test_results (person_id);
alter table public.pm_test_results enable row level security;
drop policy if exists pm_test_results_service_all on public.pm_test_results;
create policy pm_test_results_service_all on public.pm_test_results
  for all to service_role using (true) with check (true);
