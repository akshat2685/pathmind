-- 005: domain requests for uncharted aspirations
-- When an aspiration matches no known domain, the request is recorded here
-- so it can be researched and promoted to a real domain later.
-- Additive only; service_role-only RLS.

create table if not exists public.pm_domain_requests (
  request_id uuid primary key default gen_random_uuid(),
  person_id text not null,
  aspiration_text text not null,
  normalized_slug text not null,
  status text not null default 'pending'
    check (status in ('pending','researched','promoted','rejected')),
  research_notes text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);
create index if not exists idx_pm_domain_requests_slug
  on public.pm_domain_requests (normalized_slug);

do $$
begin
  execute 'alter table public.pm_domain_requests enable row level security';
  execute 'drop policy if exists pm_domain_requests_service_all on public.pm_domain_requests';
  execute 'create policy pm_domain_requests_service_all on public.pm_domain_requests
           for all to service_role using (true) with check (true)';
end $$;
