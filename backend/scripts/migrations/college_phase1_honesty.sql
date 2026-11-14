-- ============================================================================
-- PathMind College MVP — Phase 1 (backend contract + honesty) migration
-- ============================================================================
-- What this changes and why:
--
-- 1. Plan/goal SCOPE (WHOLE_PROGRAM / SEMESTER / SUBJECT_PART).
--    Persisted on college_goals.scope and learning_plans.scope so a plan's
--    breadth is explicit and survives reloads. Default SEMESTER keeps every
--    existing row and client backward compatible.
--
-- 2. DIAGNOSTIC assessment kind.
--    assessments.assessment_kind ('CHECKPOINT' | 'DIAGNOSTIC'). Diagnostic
--    assessments are generated from onboarding aspirations and are NOT tied
--    to any plan phase, so plan_id / phase_id / subject_id become nullable.
--    No fake phase linkage is ever written.
--
-- 3. Per-topic mastery store: public.learner_topic_mastery.
--    One row per (user_id, subject_id, topic): a mastery_score 0.0–1.0 plus a
--    MasteryStatus outcome. Updated from assessment results and learning
--    signals. Phase unlock_rule gates on this table (required topics must
--    meet the threshold). The future memory subagent reads this table, so the
--    schema is kept minimal and documented here.
--
-- All statements are idempotent (IF NOT EXISTS / ADD COLUMN IF NOT EXISTS).
-- ============================================================================

-- 1. Scope on goals and plans ----------------------------------------------
ALTER TABLE public.college_goals
    ADD COLUMN IF NOT EXISTS scope TEXT NOT NULL DEFAULT 'SEMESTER';

ALTER TABLE public.learning_plans
    ADD COLUMN IF NOT EXISTS scope TEXT NOT NULL DEFAULT 'SEMESTER';

-- 2. Diagnostic assessment kind ---------------------------------------------
ALTER TABLE public.assessments
    ADD COLUMN IF NOT EXISTS assessment_kind TEXT NOT NULL DEFAULT 'CHECKPOINT';

ALTER TABLE public.assessments ALTER COLUMN plan_id DROP NOT NULL;
ALTER TABLE public.assessments ALTER COLUMN phase_id DROP NOT NULL;
ALTER TABLE public.assessments ALTER COLUMN subject_id DROP NOT NULL;

-- 3. Per-topic mastery store -------------------------------------------------
CREATE TABLE IF NOT EXISTS public.learner_topic_mastery (
    user_id UUID NOT NULL REFERENCES public.learners(user_id) ON DELETE CASCADE,
    subject_id TEXT REFERENCES public.subjects(subject_id) ON DELETE SET NULL,
    topic TEXT NOT NULL,
    mastery_score NUMERIC(4, 3) NOT NULL
        CONSTRAINT check_mastery_score_range CHECK (mastery_score >= 0 AND mastery_score <= 1),
    outcome TEXT NOT NULL DEFAULT 'INSUFFICIENT_EVIDENCE',
    -- assessment_result_id or signal_id backing this row; NULL when the row
    -- only records that no evidence exists yet.
    evidence_ref TEXT,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL,
    PRIMARY KEY (user_id, subject_id, topic)
);

ALTER TABLE public.learner_topic_mastery ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "Users can view own learner_topic_mastery"
    ON public.learner_topic_mastery;
CREATE POLICY "Users can view own learner_topic_mastery"
    ON public.learner_topic_mastery FOR SELECT
    USING (auth.uid() = user_id);

DROP POLICY IF EXISTS "Users can insert own learner_topic_mastery"
    ON public.learner_topic_mastery;
CREATE POLICY "Users can insert own learner_topic_mastery"
    ON public.learner_topic_mastery FOR INSERT
    WITH CHECK (auth.uid() = user_id);

DROP POLICY IF EXISTS "Users can update own learner_topic_mastery"
    ON public.learner_topic_mastery;
CREATE POLICY "Users can update own learner_topic_mastery"
    ON public.learner_topic_mastery FOR UPDATE
    USING (auth.uid() = user_id)
    WITH CHECK (auth.uid() = user_id);

DROP POLICY IF EXISTS "Users can delete own learner_topic_mastery"
    ON public.learner_topic_mastery;
CREATE POLICY "Users can delete own learner_topic_mastery"
    ON public.learner_topic_mastery FOR DELETE
    USING (auth.uid() = user_id);

CREATE INDEX IF NOT EXISTS idx_topic_mastery_user_subject
    ON public.learner_topic_mastery(user_id, subject_id);
