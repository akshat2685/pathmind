-- Idempotent Supabase SQL Migration for PATHMIND Memory System

-- Ensure the uuid-ossp extension is enabled for UUID generation
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- 1. Short-Term Memory Table
CREATE TABLE IF NOT EXISTS public.pathmind_short_term_memories (
    memory_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    learner_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    session_id TEXT,
    conversation_id TEXT,
    content TEXT NOT NULL,
    topic TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL,
    expires_at TIMESTAMP WITH TIME ZONE,
    metadata JSONB DEFAULT '{}'::jsonb
);

-- Index for fast short-term retrieval by learner and session
CREATE INDEX IF NOT EXISTS idx_short_mem_learner ON public.pathmind_short_term_memories(learner_id);
CREATE INDEX IF NOT EXISTS idx_short_mem_session ON public.pathmind_short_term_memories(session_id);

-- 2. Long-Term Memory Table
CREATE TABLE IF NOT EXISTS public.pathmind_long_term_memories (
    memory_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    learner_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    memory_type TEXT NOT NULL DEFAULT 'EPISODIC',
    nature TEXT NOT NULL DEFAULT 'EXPERIENCE',
    title TEXT NOT NULL,
    content TEXT NOT NULL,
    source_type TEXT NOT NULL DEFAULT 'UNKNOWN',
    source_reference TEXT,
    confidence TEXT NOT NULL DEFAULT 'HIGH',
    importance TEXT NOT NULL DEFAULT 'MEDIUM',
    status TEXT NOT NULL DEFAULT 'CURRENT', -- CURRENT, SUPERSEDED, ARCHIVED
    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL,
    related_subject TEXT,
    related_topic TEXT,
    related_skill TEXT,
    supersedes_memory_id UUID REFERENCES public.pathmind_long_term_memories(memory_id) ON DELETE SET NULL,
    metadata JSONB DEFAULT '{}'::jsonb
);

-- Index for targeted retrieval by learner
CREATE INDEX IF NOT EXISTS idx_long_mem_learner ON public.pathmind_long_term_memories(learner_id);
-- Index to quickly filter active memories
CREATE INDEX IF NOT EXISTS idx_long_mem_status ON public.pathmind_long_term_memories(status);

-- 3. Row Level Security (RLS) setup
ALTER TABLE public.pathmind_short_term_memories ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.pathmind_long_term_memories ENABLE ROW LEVEL SECURITY;

-- 4. RLS Policies for Short-Term Memory
-- Ensure learners can only select/insert/update/delete their own memory.
DO $$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_policies WHERE policyname = 'Learners can access own short-term memory' AND tablename = 'pathmind_short_term_memories') THEN
        CREATE POLICY "Learners can access own short-term memory" 
        ON public.pathmind_short_term_memories
        FOR ALL
        USING (auth.uid() = learner_id)
        WITH CHECK (auth.uid() = learner_id);
    END IF;
END $$;

-- 5. RLS Policies for Long-Term Memory
DO $$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_policies WHERE policyname = 'Learners can access own long-term memory' AND tablename = 'pathmind_long_term_memories') THEN
        CREATE POLICY "Learners can access own long-term memory" 
        ON public.pathmind_long_term_memories
        FOR ALL
        USING (auth.uid() = learner_id)
        WITH CHECK (auth.uid() = learner_id);
    END IF;
END $$;
