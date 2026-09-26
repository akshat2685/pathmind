-- ============================================================================
-- PATHMIND main product: core persistence tables (migration 001)
--
-- Creates ONLY new pm_-prefixed tables for the main-product backend.
-- This migration is ADDITIVE and SAFE to run on the shared Supabase project:
--   * every table is prefixed pm_ (main-product namespace)
--   * NO college tables are created, altered, or dropped
--   * NO existing tables, policies, or data are touched
-- College tables (curriculum_units, learning_resources, ...) are never referenced.
--
-- Backend access: service_role key only (see RLS policies below).
-- person_id = Supabase Auth user id; 'global' sentinel marks cross-learner rows
-- (knowledge cache, shared patterns) that have no owning person.
-- ============================================================================

-- gen_random_uuid() is built into Postgres 13+; pgcrypto line kept for explicitness.
create extension if not exists "pgcrypto";

-- Person record (Firestore: persons/{id} merge)
create table if not exists public.pm_persons (
  id uuid not null default gen_random_uuid() primary key,
  person_id text not null,
  data jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now()
);
create index if not exists idx_pm_persons_person_id on public.pm_persons (person_id);
do $$ begin
  alter table public.pm_persons add constraint pm_persons_person_id_key unique (person_id);
exception when duplicate_object then null;
end $$;
alter table public.pm_persons enable row level security;
drop policy if exists pm_persons_service_all on public.pm_persons;
create policy pm_persons_service_all on public.pm_persons
  for all to service_role using (true) with check (true);

-- Global knowledge cache (person_id='global'), keyed by data.cache_key
create table if not exists public.pm_knowledge_cache (
  id uuid not null default gen_random_uuid() primary key,
  person_id text not null,
  data jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now()
);
create index if not exists idx_pm_knowledge_cache_person_id on public.pm_knowledge_cache (person_id);
alter table public.pm_knowledge_cache enable row level security;
drop policy if exists pm_knowledge_cache_service_all on public.pm_knowledge_cache;
create policy pm_knowledge_cache_service_all on public.pm_knowledge_cache
  for all to service_role using (true) with check (true);

-- Assessment results (append)
create table if not exists public.pm_assessments (
  id uuid not null default gen_random_uuid() primary key,
  person_id text not null,
  data jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now()
);
create index if not exists idx_pm_assessments_person_id on public.pm_assessments (person_id);
alter table public.pm_assessments enable row level security;
drop policy if exists pm_assessments_service_all on public.pm_assessments;
create policy pm_assessments_service_all on public.pm_assessments
  for all to service_role using (true) with check (true);

-- Assessment drafts, keyed by data.assessment_id
create table if not exists public.pm_assessment_drafts (
  id uuid not null default gen_random_uuid() primary key,
  person_id text not null,
  data jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now()
);
create index if not exists idx_pm_assessment_drafts_person_id on public.pm_assessment_drafts (person_id);
alter table public.pm_assessment_drafts enable row level security;
drop policy if exists pm_assessment_drafts_service_all on public.pm_assessment_drafts;
create policy pm_assessment_drafts_service_all on public.pm_assessment_drafts
  for all to service_role using (true) with check (true);

-- Active counseling profile (singleton)
create table if not exists public.pm_counseling_profiles (
  id uuid not null default gen_random_uuid() primary key,
  person_id text not null,
  data jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now()
);
create index if not exists idx_pm_counseling_profiles_person_id on public.pm_counseling_profiles (person_id);
do $$ begin
  alter table public.pm_counseling_profiles add constraint pm_counseling_profiles_person_id_key unique (person_id);
exception when duplicate_object then null;
end $$;
alter table public.pm_counseling_profiles enable row level security;
drop policy if exists pm_counseling_profiles_service_all on public.pm_counseling_profiles;
create policy pm_counseling_profiles_service_all on public.pm_counseling_profiles
  for all to service_role using (true) with check (true);

-- Personal memory vault, keyed by data.memory_id
create table if not exists public.pm_memories (
  id uuid not null default gen_random_uuid() primary key,
  person_id text not null,
  data jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now()
);
create index if not exists idx_pm_memories_person_id on public.pm_memories (person_id);
alter table public.pm_memories enable row level security;
drop policy if exists pm_memories_service_all on public.pm_memories;
create policy pm_memories_service_all on public.pm_memories
  for all to service_role using (true) with check (true);

-- Shared generalized learning patterns (person_id='global'), keyed by data.pattern_id
create table if not exists public.pm_shared_patterns (
  id uuid not null default gen_random_uuid() primary key,
  person_id text not null,
  data jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now()
);
create index if not exists idx_pm_shared_patterns_person_id on public.pm_shared_patterns (person_id);
alter table public.pm_shared_patterns enable row level security;
drop policy if exists pm_shared_patterns_service_all on public.pm_shared_patterns;
create policy pm_shared_patterns_service_all on public.pm_shared_patterns
  for all to service_role using (true) with check (true);

-- Selected-path versions (append, data.version)
create table if not exists public.pm_path_versions (
  id uuid not null default gen_random_uuid() primary key,
  person_id text not null,
  data jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now()
);
create index if not exists idx_pm_path_versions_person_id on public.pm_path_versions (person_id);
alter table public.pm_path_versions enable row level security;
drop policy if exists pm_path_versions_service_all on public.pm_path_versions;
create policy pm_path_versions_service_all on public.pm_path_versions
  for all to service_role using (true) with check (true);

-- Active selected path (singleton)
create table if not exists public.pm_active_paths (
  id uuid not null default gen_random_uuid() primary key,
  person_id text not null,
  data jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now()
);
create index if not exists idx_pm_active_paths_person_id on public.pm_active_paths (person_id);
do $$ begin
  alter table public.pm_active_paths add constraint pm_active_paths_person_id_key unique (person_id);
exception when duplicate_object then null;
end $$;
alter table public.pm_active_paths enable row level security;
drop policy if exists pm_active_paths_service_all on public.pm_active_paths;
create policy pm_active_paths_service_all on public.pm_active_paths
  for all to service_role using (true) with check (true);

-- Roadmap versions (append, data.version)
create table if not exists public.pm_roadmap_versions (
  id uuid not null default gen_random_uuid() primary key,
  person_id text not null,
  data jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now()
);
create index if not exists idx_pm_roadmap_versions_person_id on public.pm_roadmap_versions (person_id);
alter table public.pm_roadmap_versions enable row level security;
drop policy if exists pm_roadmap_versions_service_all on public.pm_roadmap_versions;
create policy pm_roadmap_versions_service_all on public.pm_roadmap_versions
  for all to service_role using (true) with check (true);

-- Active roadmap (singleton)
create table if not exists public.pm_active_roadmaps (
  id uuid not null default gen_random_uuid() primary key,
  person_id text not null,
  data jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now()
);
create index if not exists idx_pm_active_roadmaps_person_id on public.pm_active_roadmaps (person_id);
do $$ begin
  alter table public.pm_active_roadmaps add constraint pm_active_roadmaps_person_id_key unique (person_id);
exception when duplicate_object then null;
end $$;
alter table public.pm_active_roadmaps enable row level security;
drop policy if exists pm_active_roadmaps_service_all on public.pm_active_roadmaps;
create policy pm_active_roadmaps_service_all on public.pm_active_roadmaps
  for all to service_role using (true) with check (true);

-- Evidence submissions, keyed by data.submission_id
create table if not exists public.pm_evidence_submissions (
  id uuid not null default gen_random_uuid() primary key,
  person_id text not null,
  data jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now()
);
create index if not exists idx_pm_evidence_submissions_person_id on public.pm_evidence_submissions (person_id);
alter table public.pm_evidence_submissions enable row level security;
drop policy if exists pm_evidence_submissions_service_all on public.pm_evidence_submissions;
create policy pm_evidence_submissions_service_all on public.pm_evidence_submissions
  for all to service_role using (true) with check (true);

-- Evaluation results, keyed by data.submission_id
create table if not exists public.pm_evaluations (
  id uuid not null default gen_random_uuid() primary key,
  person_id text not null,
  data jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now()
);
create index if not exists idx_pm_evaluations_person_id on public.pm_evaluations (person_id);
alter table public.pm_evaluations enable row level security;
drop policy if exists pm_evaluations_service_all on public.pm_evaluations;
create policy pm_evaluations_service_all on public.pm_evaluations
  for all to service_role using (true) with check (true);

-- Learning events, keyed by data.event_id
create table if not exists public.pm_learning_events (
  id uuid not null default gen_random_uuid() primary key,
  person_id text not null,
  data jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now()
);
create index if not exists idx_pm_learning_events_person_id on public.pm_learning_events (person_id);
alter table public.pm_learning_events enable row level security;
drop policy if exists pm_learning_events_service_all on public.pm_learning_events;
create policy pm_learning_events_service_all on public.pm_learning_events
  for all to service_role using (true) with check (true);

-- Personal agent model versions (append, data.version)
create table if not exists public.pm_agent_model_versions (
  id uuid not null default gen_random_uuid() primary key,
  person_id text not null,
  data jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now()
);
create index if not exists idx_pm_agent_model_versions_person_id on public.pm_agent_model_versions (person_id);
alter table public.pm_agent_model_versions enable row level security;
drop policy if exists pm_agent_model_versions_service_all on public.pm_agent_model_versions;
create policy pm_agent_model_versions_service_all on public.pm_agent_model_versions
  for all to service_role using (true) with check (true);

-- Active personal agent model (singleton)
create table if not exists public.pm_active_agent_models (
  id uuid not null default gen_random_uuid() primary key,
  person_id text not null,
  data jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now()
);
create index if not exists idx_pm_active_agent_models_person_id on public.pm_active_agent_models (person_id);
do $$ begin
  alter table public.pm_active_agent_models add constraint pm_active_agent_models_person_id_key unique (person_id);
exception when duplicate_object then null;
end $$;
alter table public.pm_active_agent_models enable row level security;
drop policy if exists pm_active_agent_models_service_all on public.pm_active_agent_models;
create policy pm_active_agent_models_service_all on public.pm_active_agent_models
  for all to service_role using (true) with check (true);

-- Canonical career profile (singleton)
create table if not exists public.pm_career_profiles (
  id uuid not null default gen_random_uuid() primary key,
  person_id text not null,
  data jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now()
);
create index if not exists idx_pm_career_profiles_person_id on public.pm_career_profiles (person_id);
do $$ begin
  alter table public.pm_career_profiles add constraint pm_career_profiles_person_id_key unique (person_id);
exception when duplicate_object then null;
end $$;
alter table public.pm_career_profiles enable row level security;
drop policy if exists pm_career_profiles_service_all on public.pm_career_profiles;
create policy pm_career_profiles_service_all on public.pm_career_profiles
  for all to service_role using (true) with check (true);

-- Active career goal (singleton)
create table if not exists public.pm_career_goals (
  id uuid not null default gen_random_uuid() primary key,
  person_id text not null,
  data jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now()
);
create index if not exists idx_pm_career_goals_person_id on public.pm_career_goals (person_id);
do $$ begin
  alter table public.pm_career_goals add constraint pm_career_goals_person_id_key unique (person_id);
exception when duplicate_object then null;
end $$;
alter table public.pm_career_goals enable row level security;
drop policy if exists pm_career_goals_service_all on public.pm_career_goals;
create policy pm_career_goals_service_all on public.pm_career_goals
  for all to service_role using (true) with check (true);

-- Readiness reports (append)
create table if not exists public.pm_readiness_reports (
  id uuid not null default gen_random_uuid() primary key,
  person_id text not null,
  data jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now()
);
create index if not exists idx_pm_readiness_reports_person_id on public.pm_readiness_reports (person_id);
alter table public.pm_readiness_reports enable row level security;
drop policy if exists pm_readiness_reports_service_all on public.pm_readiness_reports;
create policy pm_readiness_reports_service_all on public.pm_readiness_reports
  for all to service_role using (true) with check (true);

-- Active readiness report (singleton)
create table if not exists public.pm_active_readiness_reports (
  id uuid not null default gen_random_uuid() primary key,
  person_id text not null,
  data jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now()
);
create index if not exists idx_pm_active_readiness_reports_person_id on public.pm_active_readiness_reports (person_id);
do $$ begin
  alter table public.pm_active_readiness_reports add constraint pm_active_readiness_reports_person_id_key unique (person_id);
exception when duplicate_object then null;
end $$;
alter table public.pm_active_readiness_reports enable row level security;
drop policy if exists pm_active_readiness_reports_service_all on public.pm_active_readiness_reports;
create policy pm_active_readiness_reports_service_all on public.pm_active_readiness_reports
  for all to service_role using (true) with check (true);

-- Career checkpoints, keyed by data.checkpoint_id
create table if not exists public.pm_checkpoints (
  id uuid not null default gen_random_uuid() primary key,
  person_id text not null,
  data jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now()
);
create index if not exists idx_pm_checkpoints_person_id on public.pm_checkpoints (person_id);
alter table public.pm_checkpoints enable row level security;
drop policy if exists pm_checkpoints_service_all on public.pm_checkpoints;
create policy pm_checkpoints_service_all on public.pm_checkpoints
  for all to service_role using (true) with check (true);

-- Tailored resumes, keyed by data.resume_id
create table if not exists public.pm_resumes (
  id uuid not null default gen_random_uuid() primary key,
  person_id text not null,
  data jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now()
);
create index if not exists idx_pm_resumes_person_id on public.pm_resumes (person_id);
alter table public.pm_resumes enable row level security;
drop policy if exists pm_resumes_service_all on public.pm_resumes;
create policy pm_resumes_service_all on public.pm_resumes
  for all to service_role using (true) with check (true);

-- Micro-adaptations, keyed by data.micro_adaptation_id
create table if not exists public.pm_micro_adaptations (
  id uuid not null default gen_random_uuid() primary key,
  person_id text not null,
  data jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now()
);
create index if not exists idx_pm_micro_adaptations_person_id on public.pm_micro_adaptations (person_id);
alter table public.pm_micro_adaptations enable row level security;
drop policy if exists pm_micro_adaptations_service_all on public.pm_micro_adaptations;
create policy pm_micro_adaptations_service_all on public.pm_micro_adaptations
  for all to service_role using (true) with check (true);

-- Proposed adaptations, keyed by data.adaptation_id
create table if not exists public.pm_proposed_adaptations (
  id uuid not null default gen_random_uuid() primary key,
  person_id text not null,
  data jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now()
);
create index if not exists idx_pm_proposed_adaptations_person_id on public.pm_proposed_adaptations (person_id);
alter table public.pm_proposed_adaptations enable row level security;
drop policy if exists pm_proposed_adaptations_service_all on public.pm_proposed_adaptations;
create policy pm_proposed_adaptations_service_all on public.pm_proposed_adaptations
  for all to service_role using (true) with check (true);

-- Adaptation audit trail, keyed by data.audit_id
create table if not exists public.pm_adaptation_audits (
  id uuid not null default gen_random_uuid() primary key,
  person_id text not null,
  data jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now()
);
create index if not exists idx_pm_adaptation_audits_person_id on public.pm_adaptation_audits (person_id);
alter table public.pm_adaptation_audits enable row level security;
drop policy if exists pm_adaptation_audits_service_all on public.pm_adaptation_audits;
create policy pm_adaptation_audits_service_all on public.pm_adaptation_audits
  for all to service_role using (true) with check (true);

-- Canonical evidence, keyed by data.evidence_id
create table if not exists public.pm_canonical_evidence (
  id uuid not null default gen_random_uuid() primary key,
  person_id text not null,
  data jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now()
);
create index if not exists idx_pm_canonical_evidence_person_id on public.pm_canonical_evidence (person_id);
alter table public.pm_canonical_evidence enable row level security;
drop policy if exists pm_canonical_evidence_service_all on public.pm_canonical_evidence;
create policy pm_canonical_evidence_service_all on public.pm_canonical_evidence
  for all to service_role using (true) with check (true);

-- Evaluation attempts, keyed by data.attempt_id
create table if not exists public.pm_evaluation_attempts (
  id uuid not null default gen_random_uuid() primary key,
  person_id text not null,
  data jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now()
);
create index if not exists idx_pm_evaluation_attempts_person_id on public.pm_evaluation_attempts (person_id);
alter table public.pm_evaluation_attempts enable row level security;
drop policy if exists pm_evaluation_attempts_service_all on public.pm_evaluation_attempts;
create policy pm_evaluation_attempts_service_all on public.pm_evaluation_attempts
  for all to service_role using (true) with check (true);

-- Evidence disputes, keyed by data.dispute_id
create table if not exists public.pm_evidence_disputes (
  id uuid not null default gen_random_uuid() primary key,
  person_id text not null,
  data jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now()
);
create index if not exists idx_pm_evidence_disputes_person_id on public.pm_evidence_disputes (person_id);
alter table public.pm_evidence_disputes enable row level security;
drop policy if exists pm_evidence_disputes_service_all on public.pm_evidence_disputes;
create policy pm_evidence_disputes_service_all on public.pm_evidence_disputes
  for all to service_role using (true) with check (true);

-- Skill mastery profiles, keyed by data.skill_name
create table if not exists public.pm_skill_mastery_profiles (
  id uuid not null default gen_random_uuid() primary key,
  person_id text not null,
  data jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now()
);
create index if not exists idx_pm_skill_mastery_profiles_person_id on public.pm_skill_mastery_profiles (person_id);
alter table public.pm_skill_mastery_profiles enable row level security;
drop policy if exists pm_skill_mastery_profiles_service_all on public.pm_skill_mastery_profiles;
create policy pm_skill_mastery_profiles_service_all on public.pm_skill_mastery_profiles
  for all to service_role using (true) with check (true);

-- Decision records, keyed by data.decision_id
create table if not exists public.pm_decision_records (
  id uuid not null default gen_random_uuid() primary key,
  person_id text not null,
  data jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now()
);
create index if not exists idx_pm_decision_records_person_id on public.pm_decision_records (person_id);
alter table public.pm_decision_records enable row level security;
drop policy if exists pm_decision_records_service_all on public.pm_decision_records;
create policy pm_decision_records_service_all on public.pm_decision_records
  for all to service_role using (true) with check (true);

-- Context conflicts (append)
create table if not exists public.pm_context_conflicts (
  id uuid not null default gen_random_uuid() primary key,
  person_id text not null,
  data jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now()
);
create index if not exists idx_pm_context_conflicts_person_id on public.pm_context_conflicts (person_id);
alter table public.pm_context_conflicts enable row level security;
drop policy if exists pm_context_conflicts_service_all on public.pm_context_conflicts;
create policy pm_context_conflicts_service_all on public.pm_context_conflicts
  for all to service_role using (true) with check (true);

-- Proactive event records, keyed by data.event_id
create table if not exists public.pm_event_records (
  id uuid not null default gen_random_uuid() primary key,
  person_id text not null,
  data jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now()
);
create index if not exists idx_pm_event_records_person_id on public.pm_event_records (person_id);
alter table public.pm_event_records enable row level security;
drop policy if exists pm_event_records_service_all on public.pm_event_records;
create policy pm_event_records_service_all on public.pm_event_records
  for all to service_role using (true) with check (true);

-- Interventions, keyed by data.intervention_id
create table if not exists public.pm_interventions (
  id uuid not null default gen_random_uuid() primary key,
  person_id text not null,
  data jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now()
);
create index if not exists idx_pm_interventions_person_id on public.pm_interventions (person_id);
alter table public.pm_interventions enable row level security;
drop policy if exists pm_interventions_service_all on public.pm_interventions;
create policy pm_interventions_service_all on public.pm_interventions
  for all to service_role using (true) with check (true);

-- Notification preferences (singleton)
create table if not exists public.pm_notification_preferences (
  id uuid not null default gen_random_uuid() primary key,
  person_id text not null,
  data jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now()
);
create index if not exists idx_pm_notification_preferences_person_id on public.pm_notification_preferences (person_id);
do $$ begin
  alter table public.pm_notification_preferences add constraint pm_notification_preferences_person_id_key unique (person_id);
exception when duplicate_object then null;
end $$;
alter table public.pm_notification_preferences enable row level security;
drop policy if exists pm_notification_preferences_service_all on public.pm_notification_preferences;
create policy pm_notification_preferences_service_all on public.pm_notification_preferences
  for all to service_role using (true) with check (true);

-- Structured recommendations, keyed by data.recommendation_id
create table if not exists public.pm_structured_recommendations (
  id uuid not null default gen_random_uuid() primary key,
  person_id text not null,
  data jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now()
);
create index if not exists idx_pm_structured_recommendations_person_id on public.pm_structured_recommendations (person_id);
alter table public.pm_structured_recommendations enable row level security;
drop policy if exists pm_structured_recommendations_service_all on public.pm_structured_recommendations;
create policy pm_structured_recommendations_service_all on public.pm_structured_recommendations
  for all to service_role using (true) with check (true);

-- Recommendation explanations, keyed by data.rec_id
create table if not exists public.pm_recommendation_explanations (
  id uuid not null default gen_random_uuid() primary key,
  person_id text not null,
  data jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now()
);
create index if not exists idx_pm_recommendation_explanations_person_id on public.pm_recommendation_explanations (person_id);
alter table public.pm_recommendation_explanations enable row level security;
drop policy if exists pm_recommendation_explanations_service_all on public.pm_recommendation_explanations;
create policy pm_recommendation_explanations_service_all on public.pm_recommendation_explanations
  for all to service_role using (true) with check (true);

-- Recommendation feedback (append)
create table if not exists public.pm_recommendation_feedback (
  id uuid not null default gen_random_uuid() primary key,
  person_id text not null,
  data jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now()
);
create index if not exists idx_pm_recommendation_feedback_person_id on public.pm_recommendation_feedback (person_id);
alter table public.pm_recommendation_feedback enable row level security;
drop policy if exists pm_recommendation_feedback_service_all on public.pm_recommendation_feedback;
create policy pm_recommendation_feedback_service_all on public.pm_recommendation_feedback
  for all to service_role using (true) with check (true);

-- Progress insights, keyed by data.insight_id
create table if not exists public.pm_progress_insights (
  id uuid not null default gen_random_uuid() primary key,
  person_id text not null,
  data jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now()
);
create index if not exists idx_pm_progress_insights_person_id on public.pm_progress_insights (person_id);
alter table public.pm_progress_insights enable row level security;
drop policy if exists pm_progress_insights_service_all on public.pm_progress_insights;
create policy pm_progress_insights_service_all on public.pm_progress_insights
  for all to service_role using (true) with check (true);

-- Learning strategy profiles, keyed by data.strategy_dimension
create table if not exists public.pm_learning_strategy_profiles (
  id uuid not null default gen_random_uuid() primary key,
  person_id text not null,
  data jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now()
);
create index if not exists idx_pm_learning_strategy_profiles_person_id on public.pm_learning_strategy_profiles (person_id);
alter table public.pm_learning_strategy_profiles enable row level security;
drop policy if exists pm_learning_strategy_profiles_service_all on public.pm_learning_strategy_profiles;
create policy pm_learning_strategy_profiles_service_all on public.pm_learning_strategy_profiles
  for all to service_role using (true) with check (true);

-- Recurring misconceptions, keyed by data.concept_area
create table if not exists public.pm_recurring_misconceptions (
  id uuid not null default gen_random_uuid() primary key,
  person_id text not null,
  data jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now()
);
create index if not exists idx_pm_recurring_misconceptions_person_id on public.pm_recurring_misconceptions (person_id);
alter table public.pm_recurring_misconceptions enable row level security;
drop policy if exists pm_recurring_misconceptions_service_all on public.pm_recurring_misconceptions;
create policy pm_recurring_misconceptions_service_all on public.pm_recurring_misconceptions
  for all to service_role using (true) with check (true);

-- Turning points (append)
create table if not exists public.pm_turning_points (
  id uuid not null default gen_random_uuid() primary key,
  person_id text not null,
  data jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now()
);
create index if not exists idx_pm_turning_points_person_id on public.pm_turning_points (person_id);
alter table public.pm_turning_points enable row level security;
drop policy if exists pm_turning_points_service_all on public.pm_turning_points;
create policy pm_turning_points_service_all on public.pm_turning_points
  for all to service_role using (true) with check (true);

-- Canonical artifacts, keyed by data.artifact_id
create table if not exists public.pm_canonical_artifacts (
  id uuid not null default gen_random_uuid() primary key,
  person_id text not null,
  data jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now()
);
create index if not exists idx_pm_canonical_artifacts_person_id on public.pm_canonical_artifacts (person_id);
alter table public.pm_canonical_artifacts enable row level security;
drop policy if exists pm_canonical_artifacts_service_all on public.pm_canonical_artifacts;
create policy pm_canonical_artifacts_service_all on public.pm_canonical_artifacts
  for all to service_role using (true) with check (true);

-- Artifact defense sessions, keyed by data.session_id
create table if not exists public.pm_defense_sessions (
  id uuid not null default gen_random_uuid() primary key,
  person_id text not null,
  data jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now()
);
create index if not exists idx_pm_defense_sessions_person_id on public.pm_defense_sessions (person_id);
alter table public.pm_defense_sessions enable row level security;
drop policy if exists pm_defense_sessions_service_all on public.pm_defense_sessions;
create policy pm_defense_sessions_service_all on public.pm_defense_sessions
  for all to service_role using (true) with check (true);

-- Claim validations (append)
create table if not exists public.pm_claim_validations (
  id uuid not null default gen_random_uuid() primary key,
  person_id text not null,
  data jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now()
);
create index if not exists idx_pm_claim_validations_person_id on public.pm_claim_validations (person_id);
alter table public.pm_claim_validations enable row level security;
drop policy if exists pm_claim_validations_service_all on public.pm_claim_validations;
create policy pm_claim_validations_service_all on public.pm_claim_validations
  for all to service_role using (true) with check (true);

-- Step verifications (append)
create table if not exists public.pm_step_verifications (
  id uuid not null default gen_random_uuid() primary key,
  person_id text not null,
  data jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now()
);
create index if not exists idx_pm_step_verifications_person_id on public.pm_step_verifications (person_id);
alter table public.pm_step_verifications enable row level security;
drop policy if exists pm_step_verifications_service_all on public.pm_step_verifications;
create policy pm_step_verifications_service_all on public.pm_step_verifications
  for all to service_role using (true) with check (true);

-- Canonical actions, keyed by data.action_id
create table if not exists public.pm_actions (
  id uuid not null default gen_random_uuid() primary key,
  person_id text not null,
  data jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now()
);
create index if not exists idx_pm_actions_person_id on public.pm_actions (person_id);
alter table public.pm_actions enable row level security;
drop policy if exists pm_actions_service_all on public.pm_actions;
create policy pm_actions_service_all on public.pm_actions
  for all to service_role using (true) with check (true);

-- Opportunity applications, keyed by data.application_id
create table if not exists public.pm_opportunity_applications (
  id uuid not null default gen_random_uuid() primary key,
  person_id text not null,
  data jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now()
);
create index if not exists idx_pm_opportunity_applications_person_id on public.pm_opportunity_applications (person_id);
alter table public.pm_opportunity_applications enable row level security;
drop policy if exists pm_opportunity_applications_service_all on public.pm_opportunity_applications;
create policy pm_opportunity_applications_service_all on public.pm_opportunity_applications
  for all to service_role using (true) with check (true);

-- Execution pause state (singleton)
create table if not exists public.pm_execution_pause_states (
  id uuid not null default gen_random_uuid() primary key,
  person_id text not null,
  data jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now()
);
create index if not exists idx_pm_execution_pause_states_person_id on public.pm_execution_pause_states (person_id);
do $$ begin
  alter table public.pm_execution_pause_states add constraint pm_execution_pause_states_person_id_key unique (person_id);
exception when duplicate_object then null;
end $$;
alter table public.pm_execution_pause_states enable row level security;
drop policy if exists pm_execution_pause_states_service_all on public.pm_execution_pause_states;
create policy pm_execution_pause_states_service_all on public.pm_execution_pause_states
  for all to service_role using (true) with check (true);

-- Orchestration traces (append)
create table if not exists public.pm_orchestration_traces (
  id uuid not null default gen_random_uuid() primary key,
  person_id text not null,
  data jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now()
);
create index if not exists idx_pm_orchestration_traces_person_id on public.pm_orchestration_traces (person_id);
alter table public.pm_orchestration_traces enable row level security;
drop policy if exists pm_orchestration_traces_service_all on public.pm_orchestration_traces;
create policy pm_orchestration_traces_service_all on public.pm_orchestration_traces
  for all to service_role using (true) with check (true);

-- Action proposals, keyed by data.proposal_id
create table if not exists public.pm_action_proposals (
  id uuid not null default gen_random_uuid() primary key,
  person_id text not null,
  data jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now()
);
create index if not exists idx_pm_action_proposals_person_id on public.pm_action_proposals (person_id);
alter table public.pm_action_proposals enable row level security;
drop policy if exists pm_action_proposals_service_all on public.pm_action_proposals;
create policy pm_action_proposals_service_all on public.pm_action_proposals
  for all to service_role using (true) with check (true);

-- Continuous journey state (singleton)
create table if not exists public.pm_journey_states (
  id uuid not null default gen_random_uuid() primary key,
  person_id text not null,
  data jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now()
);
create index if not exists idx_pm_journey_states_person_id on public.pm_journey_states (person_id);
do $$ begin
  alter table public.pm_journey_states add constraint pm_journey_states_person_id_key unique (person_id);
exception when duplicate_object then null;
end $$;
alter table public.pm_journey_states enable row level security;
drop policy if exists pm_journey_states_service_all on public.pm_journey_states;
create policy pm_journey_states_service_all on public.pm_journey_states
  for all to service_role using (true) with check (true);

-- Assessment blueprint (singleton)
create table if not exists public.pm_assessment_blueprints (
  id uuid not null default gen_random_uuid() primary key,
  person_id text not null,
  data jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now()
);
create index if not exists idx_pm_assessment_blueprints_person_id on public.pm_assessment_blueprints (person_id);
do $$ begin
  alter table public.pm_assessment_blueprints add constraint pm_assessment_blueprints_person_id_key unique (person_id);
exception when duplicate_object then null;
end $$;
alter table public.pm_assessment_blueprints enable row level security;
drop policy if exists pm_assessment_blueprints_service_all on public.pm_assessment_blueprints;
create policy pm_assessment_blueprints_service_all on public.pm_assessment_blueprints
  for all to service_role using (true) with check (true);
