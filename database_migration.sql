-- Supabase Schema Migration: College MVP
-- This script creates the `learners` table mapped to `auth.users`

CREATE TABLE IF NOT EXISTS public.learners (
    user_id UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
    email TEXT,
    name TEXT,
    academic_context JSONB,
    learning_plans JSONB,
    assessments JSONB,
    roadmaps JSONB,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL
);

-- Enable RLS
ALTER TABLE public.learners ENABLE ROW LEVEL SECURITY;

-- Create policies
CREATE POLICY "Users can view own profile" 
    ON public.learners FOR SELECT 
    USING (auth.uid() = user_id);

CREATE POLICY "Users can update own profile" 
    ON public.learners FOR UPDATE 
    USING (auth.uid() = user_id);

CREATE POLICY "Users can insert own profile" 
    ON public.learners FOR INSERT 
    WITH CHECK (auth.uid() = user_id);
