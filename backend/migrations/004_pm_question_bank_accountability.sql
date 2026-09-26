-- 004: verified question bank + accountability loop + longitudinal memory
-- Additive only. pm_* tables, service_role-only RLS. Never touches college tables.

-- ------------------------------------------------------------------
-- Verified aptitude question bank
-- ------------------------------------------------------------------
create table if not exists public.pm_domains (
  slug text primary key,
  display_name text not null,
  parent_slug text references public.pm_domains(slug),
  description text,
  verification_status text not null default 'PROVISIONAL'
    check (verification_status in ('VERIFIED','RESEARCHED','PROVISIONAL')),
  created_at timestamptz not null default now()
);

create table if not exists public.pm_domain_aliases (
  alias text primary key,
  domain_slug text not null references public.pm_domains(slug)
);

create table if not exists public.pm_question_bank (
  question_id uuid primary key default gen_random_uuid(),
  domain text not null references public.pm_domains(slug),
  aspiration_aliases text[] not null default '{}',
  question_type text not null check (question_type in ('mcq','short','self_assess')),
  question_text text not null,
  options jsonb,
  correct_option text,
  rubric text,
  skill_tag text,
  difficulty int check (difficulty between 1 and 5),
  points int not null default 1,
  source_type text not null check (source_type in
    ('UNIVERSITY','CERTIFICATION_BODY','GOVT_BODY','EXPERT',
     'PUBLISHED_WORK','COMMUNITY','AI_GENERATED')),
  source_name text not null,
  source_url text,
  source_detail text,
  verification_status text not null default 'AI_DRAFT' check (verification_status in
    ('VERIFIED','EXPERT_REVIEWED','AI_DRAFT','COMMUNITY_UNREVIEWED','DEPRECATED')),
  verified_by text,
  verified_at timestamptz,
  license_note text,
  status text not null default 'active' check (status in ('active','deprecated')),
  usage_count int not null default 0,
  last_used_at timestamptz,
  created_by text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);
create index if not exists pm_qb_domain_status
  on public.pm_question_bank(domain, status, verification_status);

create table if not exists public.pm_question_reviews (
  review_id uuid primary key default gen_random_uuid(),
  question_id uuid not null references public.pm_question_bank(question_id),
  reviewer text not null,
  verdict text not null check (verdict in ('approved','rejected','needs_changes')),
  notes text,
  reviewed_at timestamptz not null default now()
);

create table if not exists public.pm_test_question_map (
  test_id text not null,
  question_id uuid not null references public.pm_question_bank(question_id),
  tier_at_time text not null,
  primary key (test_id, question_id)
);

-- ------------------------------------------------------------------
-- Accountability loop: commitments / streak / today schedule
-- ------------------------------------------------------------------
create table if not exists public.pm_commitments (
  id uuid not null default gen_random_uuid() primary key,
  person_id text not null,
  data jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now()
);
create index if not exists idx_pm_commitments_person_id
  on public.pm_commitments (person_id);

-- ------------------------------------------------------------------
-- Longitudinal memory tiers (short-term session + long-term + signals)
-- ------------------------------------------------------------------
create table if not exists public.pm_short_term_memories (
  id uuid not null default gen_random_uuid() primary key,
  person_id text not null,
  data jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now()
);
create index if not exists idx_pm_stm_person_id
  on public.pm_short_term_memories (person_id);

create table if not exists public.pm_long_term_memories (
  id uuid not null default gen_random_uuid() primary key,
  person_id text not null,
  data jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now()
);
create index if not exists idx_pm_ltm_person_id
  on public.pm_long_term_memories (person_id);

create table if not exists public.pm_longitudinal_signals (
  id uuid not null default gen_random_uuid() primary key,
  person_id text not null,
  data jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now()
);
create index if not exists idx_pm_ls_person_id
  on public.pm_longitudinal_signals (person_id);

-- ------------------------------------------------------------------
-- RLS: service_role-only, mirroring migrations 001-003
-- ------------------------------------------------------------------
do $$
declare t text;
begin
  foreach t in array array[
    'pm_domains','pm_domain_aliases','pm_question_bank','pm_question_reviews',
    'pm_test_question_map','pm_commitments','pm_short_term_memories',
    'pm_long_term_memories','pm_longitudinal_signals'
  ]
  loop
    execute format('alter table public.%I enable row level security', t);
    execute format('drop policy if exists %I on public.%I',
      'pm_' || replace(t, 'pm_', '') || '_service_all', t);
    execute format(
      'create policy %I on public.%I for all to service_role using (true) with check (true)',
      'pm_' || replace(t, 'pm_', '') || '_service_all', t
    );
  end loop;
end $$;
