-- ==========================================================================
-- PATHMIND Memory Schema Migration: learner_id → user_id
-- ==========================================================================
-- This migration renames the identity column in both memory tables from
-- learner_id to user_id, aligning the database with the College MVP backend.
--
-- IMPORTANT: Execute this BEFORE college_schema.sql.
-- This migration is idempotent and safe to re-run.
-- No data is lost — ALTER TABLE RENAME COLUMN preserves all existing values.
-- ==========================================================================

-- 1. Rename columns (idempotent: will fail silently if already renamed)
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_schema = 'public'
          AND table_name = 'pathmind_short_term_memories'
          AND column_name = 'learner_id'
    ) THEN
        ALTER TABLE public.pathmind_short_term_memories RENAME COLUMN learner_id TO user_id;
    END IF;

    IF EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_schema = 'public'
          AND table_name = 'pathmind_long_term_memories'
          AND column_name = 'learner_id'
    ) THEN
        ALTER TABLE public.pathmind_long_term_memories RENAME COLUMN learner_id TO user_id;
    END IF;
END $$;

-- 2. Drop old RLS policies (idempotent)
DROP POLICY IF EXISTS "Learners can access own short-term memory" ON public.pathmind_short_term_memories;
DROP POLICY IF EXISTS "Learners can access own long-term memory" ON public.pathmind_long_term_memories;

-- 3. Recreate RLS policies with user_id
DO $$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_policies WHERE policyname = 'Users can access own short-term memory' AND tablename = 'pathmind_short_term_memories') THEN
        CREATE POLICY "Users can access own short-term memory"
        ON public.pathmind_short_term_memories FOR ALL
        USING (auth.uid() = user_id)
        WITH CHECK (auth.uid() = user_id);
    END IF;

    IF NOT EXISTS (SELECT FROM pg_policies WHERE policyname = 'Users can access own long-term memory' AND tablename = 'pathmind_long_term_memories') THEN
        CREATE POLICY "Users can access own long-term memory"
        ON public.pathmind_long_term_memories FOR ALL
        USING (auth.uid() = user_id)
        WITH CHECK (auth.uid() = user_id);
    END IF;
END $$;

-- 4. Drop old indexes and recreate with new column name (idempotent)
DROP INDEX IF EXISTS idx_short_mem_learner;
DROP INDEX IF EXISTS idx_long_mem_learner;

CREATE INDEX IF NOT EXISTS idx_short_mem_user ON public.pathmind_short_term_memories(user_id);
CREATE INDEX IF NOT EXISTS idx_long_mem_user ON public.pathmind_long_term_memories(user_id);
