-- Supabase Schema Migration: College MVP
-- Idempotent schema for College MVP persistent entities.

CREATE EXTENSION IF NOT EXISTS pgcrypto;


-- ============================================================================
-- 1. PUBLIC SHARED KNOWLEDGE TABLES
-- ============================================================================
-- Note on RLS: Public shared knowledge tables have RLS enabled.
-- Verified rows are globally readable by anon/authenticated users via SELECT.
-- Privileged backend writes bypass RLS via SUPABASE_SECRET_KEY.

CREATE TABLE IF NOT EXISTS public.source_records (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source_id TEXT UNIQUE NOT NULL,
    url TEXT NOT NULL,
    canonical_url TEXT,
    title TEXT NOT NULL,
    domain TEXT NOT NULL,
    provider_name TEXT NOT NULL,
    provider_type TEXT,
    source_tier TEXT NOT NULL,
    source_type TEXT,
    author TEXT,
    verification_status TEXT DEFAULT 'UNVERIFIED',
    content_hash TEXT,
    language TEXT,
    content_available BOOLEAN,
    topic_ids JSONB DEFAULT '[]'::jsonb,
    curriculum_ids JSONB DEFAULT '[]'::jsonb,
    quality_signals JSONB DEFAULT '{}'::jsonb,
    notes TEXT,
    retrieved_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()),
    last_verified_at TIMESTAMP WITH TIME ZONE
);

CREATE TABLE IF NOT EXISTS public.universities (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    university_id TEXT UNIQUE NOT NULL,
    name TEXT NOT NULL,
    normalized_name TEXT NOT NULL,
    country TEXT,
    state TEXT NOT NULL,
    official_domain TEXT,
    official_url TEXT,
    verification_status TEXT DEFAULT 'UNVERIFIED',
    source_id TEXT REFERENCES public.source_records(source_id) ON DELETE RESTRICT,
    aliases JSONB DEFAULT '[]'::jsonb,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL
);

CREATE TABLE IF NOT EXISTS public.programs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    program_id TEXT UNIQUE NOT NULL,
    university_id TEXT NOT NULL REFERENCES public.universities(university_id) ON DELETE RESTRICT,
    name TEXT NOT NULL,
    normalized_name TEXT NOT NULL,
    degree TEXT,
    branch TEXT NOT NULL,
    supported_path TEXT NOT NULL,
    duration_semesters INTEGER,
    version INTEGER DEFAULT 1,
    verification_status TEXT DEFAULT 'UNVERIFIED',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()),
    UNIQUE(university_id, program_id)
);

CREATE TABLE IF NOT EXISTS public.subjects (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    subject_id TEXT UNIQUE NOT NULL,
    code TEXT NOT NULL,
    name TEXT NOT NULL,
    credits INTEGER,
    lecture_hours INTEGER,
    practical_hours INTEGER,
    assessment_pattern JSONB,
    verification_status TEXT DEFAULT 'UNVERIFIED',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now())
);

CREATE TABLE IF NOT EXISTS public.curricula (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    curriculum_id TEXT UNIQUE NOT NULL,
    university_id TEXT NOT NULL,
    program_id TEXT NOT NULL,
    academic_year TEXT,
    semester INTEGER NOT NULL,
    version INTEGER DEFAULT 1,
    verification_status TEXT DEFAULT 'UNVERIFIED',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()),
    FOREIGN KEY (university_id, program_id) REFERENCES public.programs(university_id, program_id) ON DELETE RESTRICT,
    CONSTRAINT check_semester_valid CHECK (semester BETWEEN 1 AND 8)
);

CREATE TABLE IF NOT EXISTS public.curriculum_subjects (
    curriculum_id TEXT NOT NULL REFERENCES public.curricula(curriculum_id) ON DELETE CASCADE,
    subject_id TEXT NOT NULL REFERENCES public.subjects(subject_id) ON DELETE CASCADE,
    verification_status TEXT DEFAULT 'UNVERIFIED',
    PRIMARY KEY (curriculum_id, subject_id)
);

CREATE TABLE IF NOT EXISTS public.curriculum_units (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    curriculum_id TEXT NOT NULL,
    subject_id TEXT NOT NULL,
    unit INTEGER NOT NULL,
    title TEXT NOT NULL,
    topics JSONB DEFAULT '[]'::jsonb,
    source_ids JSONB DEFAULT '[]'::jsonb,
    verification_status TEXT DEFAULT 'UNVERIFIED',
    FOREIGN KEY (curriculum_id, subject_id) REFERENCES public.curriculum_subjects(curriculum_id, subject_id) ON DELETE CASCADE,
    UNIQUE (curriculum_id, subject_id, unit)
);

CREATE TABLE IF NOT EXISTS public.resource_records (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    resource_id TEXT UNIQUE NOT NULL,
    title TEXT NOT NULL,
    resource_type TEXT NOT NULL,
    provider TEXT NOT NULL,
    url TEXT NOT NULL,
    source_id TEXT NOT NULL REFERENCES public.source_records(source_id) ON DELETE RESTRICT,
    source_tier TEXT NOT NULL,
    difficulty TEXT,
    estimated_minutes INTEGER,
    cost TEXT,
    language TEXT,
    topic_ids JSONB DEFAULT '[]'::jsonb,
    curriculum_ids JSONB DEFAULT '[]'::jsonb,
    video_timestamps JSONB DEFAULT '[]'::jsonb,
    document_sections JSONB DEFAULT '[]'::jsonb,
    learner_preference_metadata JSONB DEFAULT '{}'::jsonb,
    verification_status TEXT DEFAULT 'UNVERIFIED',
    last_verified_at TIMESTAMP WITH TIME ZONE
);

CREATE TABLE IF NOT EXISTS public.pyq_sets (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    pyq_set_id TEXT UNIQUE NOT NULL,
    university_id TEXT NOT NULL,
    program_id TEXT NOT NULL,
    curriculum_id TEXT,
    semester INTEGER NOT NULL,
    subject_id TEXT NOT NULL REFERENCES public.subjects(subject_id) ON DELETE RESTRICT,
    exam_year INTEGER NOT NULL,
    exam_type TEXT,
    source_id TEXT NOT NULL REFERENCES public.source_records(source_id) ON DELETE RESTRICT,
    verification_status TEXT DEFAULT 'UNVERIFIED',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()),
    FOREIGN KEY (university_id, program_id) REFERENCES public.programs(university_id, program_id) ON DELETE RESTRICT,
    FOREIGN KEY (curriculum_id, subject_id) REFERENCES public.curriculum_subjects(curriculum_id, subject_id) ON DELETE RESTRICT,
    UNIQUE(university_id, program_id, semester, subject_id, exam_year, exam_type),
    CONSTRAINT check_not_ai_generated CHECK (exam_type IS NULL OR exam_type != 'AI_GENERATED'),
    CONSTRAINT check_semester_valid CHECK (semester BETWEEN 1 AND 8)
);

CREATE TABLE IF NOT EXISTS public.pyq_questions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    question_id TEXT UNIQUE NOT NULL,
    pyq_set_id TEXT NOT NULL REFERENCES public.pyq_sets(pyq_set_id) ON DELETE CASCADE,
    question_number TEXT NOT NULL,
    question_text TEXT NOT NULL,
    marks INTEGER,
    topic_ids JSONB DEFAULT '[]'::jsonb,
    unit INTEGER,
    difficulty TEXT,
    source_id TEXT REFERENCES public.source_records(source_id) ON DELETE SET NULL,
    verification_status TEXT DEFAULT 'UNVERIFIED',
    UNIQUE (pyq_set_id, question_number)
);

-- ============================================================================
-- 2. PRIVATE LEARNER TABLES (Learner Scoped)
-- ============================================================================

CREATE TABLE IF NOT EXISTS public.learners (
    user_id UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
    name TEXT,
    email TEXT,
    primary_university_id TEXT,
    primary_program_id TEXT,
    current_semester INTEGER,
    current_academic_year TEXT,
    supported_path TEXT DEFAULT 'GENERAL_OTHER',
    profile_status TEXT DEFAULT 'INITIALIZED',
    timezone TEXT DEFAULT 'Asia/Kolkata',
    locale TEXT DEFAULT 'en-IN',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()),
    last_login_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()),
    FOREIGN KEY (primary_university_id, primary_program_id) REFERENCES public.programs(university_id, program_id) ON DELETE SET NULL,
    CONSTRAINT check_university_program_consistency CHECK ((primary_university_id IS NULL AND primary_program_id IS NULL) OR (primary_university_id IS NOT NULL AND primary_program_id IS NOT NULL)),
    CONSTRAINT check_current_semester_valid CHECK (current_semester BETWEEN 1 AND 8)
);

CREATE TABLE IF NOT EXISTS public.learner_academic_contexts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    context_id TEXT UNIQUE NOT NULL,
    user_id UUID NOT NULL REFERENCES public.learners(user_id) ON DELETE CASCADE,
    university_id TEXT,
    program_id TEXT,
    semester INTEGER NOT NULL,
    academic_year TEXT,
    exam_window JSONB DEFAULT '{}'::jsonb,
    available_hours_per_week INTEGER,
    learning_style_preferences JSONB DEFAULT '[]'::jsonb,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()),
    FOREIGN KEY (university_id, program_id) REFERENCES public.programs(university_id, program_id) ON DELETE SET NULL,
    CONSTRAINT check_semester_valid CHECK (semester BETWEEN 1 AND 8)
);

CREATE TABLE IF NOT EXISTS public.learner_context_subjects (
    context_id TEXT NOT NULL REFERENCES public.learner_academic_contexts(context_id) ON DELETE CASCADE,
    subject_id TEXT NOT NULL REFERENCES public.subjects(subject_id) ON DELETE CASCADE,
    PRIMARY KEY (context_id, subject_id)
);

CREATE TABLE IF NOT EXISTS public.college_goals (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    goal_id TEXT UNIQUE NOT NULL,
    user_id UUID NOT NULL REFERENCES public.learners(user_id) ON DELETE CASCADE,
    goal_type TEXT DEFAULT 'SEMESTER_EXAM',
    raw_goal TEXT NOT NULL,
    normalized_goal TEXT NOT NULL,
    target_subject_ids JSONB DEFAULT '[]'::jsonb,
    target_score NUMERIC(5, 2),
    deadline TIMESTAMP WITH TIME ZONE,
    status TEXT DEFAULT 'ACTIVE',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()),
    UNIQUE(user_id, goal_id)
);

CREATE TABLE IF NOT EXISTS public.learning_plans (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    plan_id TEXT UNIQUE NOT NULL,
    user_id UUID NOT NULL REFERENCES public.learners(user_id) ON DELETE CASCADE,
    goal_id TEXT,
    plan_type TEXT DEFAULT 'SEMESTER_PREPARATION',
    version INTEGER DEFAULT 1,
    status TEXT DEFAULT 'ACTIVE', -- ACTIVE, SUPERSEDED, COMPLETED
    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()),
    FOREIGN KEY (user_id, goal_id) REFERENCES public.college_goals(user_id, goal_id) ON DELETE RESTRICT,
    UNIQUE(user_id, plan_id)
);

CREATE TABLE IF NOT EXISTS public.learning_plan_subjects (
    plan_id TEXT NOT NULL REFERENCES public.learning_plans(plan_id) ON DELETE CASCADE,
    subject_id TEXT NOT NULL REFERENCES public.subjects(subject_id) ON DELETE CASCADE,
    PRIMARY KEY (plan_id, subject_id)
);

CREATE TABLE IF NOT EXISTS public.learning_plan_phases (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    phase_id TEXT UNIQUE NOT NULL,
    user_id UUID NOT NULL REFERENCES public.learners(user_id) ON DELETE CASCADE,
    plan_id TEXT NOT NULL,
    "order" INTEGER NOT NULL,
    title TEXT NOT NULL,
    objective TEXT NOT NULL,
    status TEXT DEFAULT 'AVAILABLE',
    unlock_rule JSONB DEFAULT '{}'::jsonb,
    assessment_id TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()),
    FOREIGN KEY (user_id, plan_id) REFERENCES public.learning_plans(user_id, plan_id) ON DELETE CASCADE,
    UNIQUE(plan_id, "order"),
    UNIQUE(user_id, plan_id, phase_id),
    UNIQUE(user_id, phase_id)
);

CREATE TABLE IF NOT EXISTS public.learning_activities (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    activity_id TEXT UNIQUE NOT NULL,
    user_id UUID NOT NULL REFERENCES public.learners(user_id) ON DELETE CASCADE,
    plan_id TEXT NOT NULL,
    phase_id TEXT NOT NULL,
    activity_type TEXT NOT NULL,
    title TEXT NOT NULL,
    resource_id TEXT REFERENCES public.resource_records(resource_id) ON DELETE SET NULL,
    pyq_question_id TEXT REFERENCES public.pyq_questions(question_id) ON DELETE SET NULL,
    "order" INTEGER NOT NULL,
    instructions TEXT NOT NULL,
    estimated_minutes INTEGER,
    status TEXT DEFAULT 'AVAILABLE',
    started_at TIMESTAMP WITH TIME ZONE,
    completed_at TIMESTAMP WITH TIME ZONE,
    completion_evidence JSONB,
    FOREIGN KEY (user_id, plan_id) REFERENCES public.learning_plans(user_id, plan_id) ON DELETE CASCADE,
    FOREIGN KEY (user_id, plan_id, phase_id) REFERENCES public.learning_plan_phases(user_id, plan_id, phase_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS public.assessments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    assessment_id TEXT UNIQUE NOT NULL,
    user_id UUID NOT NULL REFERENCES public.learners(user_id) ON DELETE CASCADE,
    plan_id TEXT NOT NULL,
    phase_id TEXT NOT NULL,
    subject_id TEXT NOT NULL REFERENCES public.subjects(subject_id) ON DELETE RESTRICT,
    title TEXT NOT NULL,
    questions JSONB DEFAULT '[]'::jsonb,
    status TEXT DEFAULT 'AVAILABLE',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()),
    FOREIGN KEY (user_id, plan_id) REFERENCES public.learning_plans(user_id, plan_id) ON DELETE CASCADE,
    FOREIGN KEY (user_id, plan_id, phase_id) REFERENCES public.learning_plan_phases(user_id, plan_id, phase_id) ON DELETE CASCADE,
    UNIQUE(user_id, assessment_id),
    UNIQUE(user_id, plan_id, phase_id, assessment_id)
);


CREATE TABLE IF NOT EXISTS public.assessment_results (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    result_id TEXT UNIQUE NOT NULL,
    user_id UUID NOT NULL REFERENCES public.learners(user_id) ON DELETE CASCADE,
    assessment_id TEXT NOT NULL,
    score NUMERIC(6, 2) NOT NULL,
    normalized_score NUMERIC(5, 3) NOT NULL,
    mastery_status TEXT NOT NULL,
    topic_results JSONB DEFAULT '[]'::jsonb,
    feedback TEXT NOT NULL,
    evaluation_confidence NUMERIC(4, 3),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()),
    FOREIGN KEY (user_id, assessment_id) REFERENCES public.assessments(user_id, assessment_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS public.learning_signals (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    signal_id TEXT UNIQUE NOT NULL,
    user_id UUID NOT NULL REFERENCES public.learners(user_id) ON DELETE CASCADE,
    signal_type TEXT DEFAULT 'REPEATED_MISCONCEPTION',
    subject_id TEXT REFERENCES public.subjects(subject_id) ON DELETE SET NULL,
    topic_id TEXT,
    description TEXT NOT NULL,
    confidence NUMERIC(4, 3),
    recommended_intervention TEXT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now())
);

CREATE TABLE IF NOT EXISTS public.accountability_commitments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    commitment_id TEXT UNIQUE NOT NULL,
    user_id UUID NOT NULL REFERENCES public.learners(user_id) ON DELETE CASCADE,
    title TEXT NOT NULL,
    plan_id TEXT,
    phase_id TEXT,
    due_at TIMESTAMP WITH TIME ZONE NOT NULL,
    estimated_minutes INTEGER,
    status TEXT DEFAULT 'PLANNED',
    completion_evidence_ref TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()),
    FOREIGN KEY (user_id, plan_id) REFERENCES public.learning_plans(user_id, plan_id) ON DELETE CASCADE,
    FOREIGN KEY (user_id, plan_id, phase_id) REFERENCES public.learning_plan_phases(user_id, plan_id, phase_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS public.chat_sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id TEXT UNIQUE NOT NULL,
    user_id UUID NOT NULL REFERENCES public.learners(user_id) ON DELETE CASCADE,
    title TEXT NOT NULL,
    started_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()),
    last_active_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()),
    current_subject_id TEXT REFERENCES public.subjects(subject_id) ON DELETE SET NULL,
    current_topic_id TEXT,
    current_plan_id TEXT,
    status TEXT DEFAULT 'ACTIVE',
    FOREIGN KEY (user_id, current_plan_id) REFERENCES public.learning_plans(user_id, plan_id) ON DELETE RESTRICT,
    UNIQUE(user_id, session_id)
);

CREATE TABLE IF NOT EXISTS public.chat_messages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    message_id TEXT UNIQUE NOT NULL,
    session_id TEXT NOT NULL,
    user_id UUID NOT NULL REFERENCES public.learners(user_id) ON DELETE CASCADE,
    role TEXT NOT NULL,
    content TEXT NOT NULL,
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()),
    memory_candidates JSONB DEFAULT '[]'::jsonb,
    source_refs JSONB DEFAULT '[]'::jsonb,
    FOREIGN KEY (user_id, session_id) REFERENCES public.chat_sessions(user_id, session_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS public.learner_evidence (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    evidence_id TEXT UNIQUE NOT NULL,
    user_id UUID NOT NULL REFERENCES public.learners(user_id) ON DELETE CASCADE,
    type TEXT NOT NULL,
    title TEXT NOT NULL,
    document_reference TEXT, 
    extracted_metadata JSONB,
    source_url TEXT,
    related_subject_id TEXT REFERENCES public.subjects(subject_id) ON DELETE SET NULL,
    related_phase_id TEXT,
    verification_status TEXT DEFAULT 'SUBMITTED',
    verification_reason TEXT,
    content_hash TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()),
    verified_at TIMESTAMP WITH TIME ZONE,
    FOREIGN KEY (user_id, related_phase_id) REFERENCES public.learning_plan_phases(user_id, phase_id) ON DELETE RESTRICT
);

CREATE TABLE IF NOT EXISTS public.progress_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    event_id TEXT UNIQUE NOT NULL,
    user_id UUID NOT NULL REFERENCES public.learners(user_id) ON DELETE CASCADE,
    event_type TEXT NOT NULL,
    entity_type TEXT NOT NULL,
    entity_id TEXT NOT NULL,
    metadata JSONB DEFAULT '{}'::jsonb,
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now())
);

CREATE TABLE IF NOT EXISTS public.roadmaps (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    roadmap_id TEXT UNIQUE NOT NULL,
    user_id UUID NOT NULL REFERENCES public.learners(user_id) ON DELETE CASCADE,
    title TEXT NOT NULL,
    target_outcome TEXT NOT NULL,
    version INTEGER DEFAULT 1,
    status TEXT DEFAULT 'ACTIVE', -- ACTIVE, SUPERSEDED
    constraints JSONB DEFAULT '{}'::jsonb,
    stages_snapshot JSONB DEFAULT '[]'::jsonb,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now())
);

-- ============================================================================
-- 3. ROW LEVEL SECURITY (RLS)
-- ============================================================================

-- Apply RLS to shared knowledge tables allowing public READ ONLY access.
-- Backend privileged writes will bypass this via the SUPABASE_SECRET_KEY.

ALTER TABLE public.source_records ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "Anyone can view source_records" ON public.source_records;
CREATE POLICY "Anyone can view source_records" ON public.source_records FOR SELECT USING (verification_status = 'VERIFIED');

ALTER TABLE public.universities ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "Anyone can view universities" ON public.universities;
CREATE POLICY "Anyone can view universities" ON public.universities FOR SELECT USING (verification_status = 'VERIFIED' AND EXISTS (SELECT 1 FROM public.source_records s WHERE s.source_id = universities.source_id AND s.verification_status = 'VERIFIED'));

ALTER TABLE public.programs ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "Anyone can view programs" ON public.programs;
CREATE POLICY "Anyone can view programs" ON public.programs FOR SELECT USING (verification_status = 'VERIFIED' AND EXISTS (SELECT 1 FROM public.universities u WHERE u.university_id = programs.university_id AND u.verification_status = 'VERIFIED'));

ALTER TABLE public.subjects ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "Anyone can view subjects" ON public.subjects;
CREATE POLICY "Anyone can view subjects" ON public.subjects FOR SELECT USING (verification_status = 'VERIFIED');

ALTER TABLE public.curricula ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "Anyone can view curricula" ON public.curricula;
CREATE POLICY "Anyone can view curricula" ON public.curricula FOR SELECT USING (verification_status = 'VERIFIED' AND EXISTS(SELECT 1 FROM public.programs p WHERE p.program_id = curricula.program_id AND p.verification_status = 'VERIFIED'));

ALTER TABLE public.curriculum_subjects ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "Anyone can view curriculum_subjects" ON public.curriculum_subjects;
CREATE POLICY "Anyone can view curriculum_subjects" ON public.curriculum_subjects FOR SELECT USING (verification_status = 'VERIFIED' AND EXISTS(SELECT 1 FROM public.curricula c WHERE c.curriculum_id = curriculum_subjects.curriculum_id AND c.verification_status = 'VERIFIED') AND EXISTS(SELECT 1 FROM public.subjects s WHERE s.subject_id = curriculum_subjects.subject_id AND s.verification_status = 'VERIFIED'));

ALTER TABLE public.curriculum_units ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "Anyone can view curriculum_units" ON public.curriculum_units;
CREATE POLICY "Anyone can view curriculum_units" ON public.curriculum_units FOR SELECT USING (verification_status = 'VERIFIED' AND EXISTS(SELECT 1 FROM public.curricula c WHERE c.curriculum_id = curriculum_units.curriculum_id AND c.verification_status = 'VERIFIED') AND EXISTS(SELECT 1 FROM public.curriculum_subjects cs WHERE cs.curriculum_id = curriculum_units.curriculum_id AND cs.subject_id = curriculum_units.subject_id AND cs.verification_status = 'VERIFIED') AND EXISTS(SELECT 1 FROM public.subjects s WHERE s.subject_id = curriculum_units.subject_id AND s.verification_status = 'VERIFIED'));

ALTER TABLE public.resource_records ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "Anyone can view resource_records" ON public.resource_records;
CREATE POLICY "Anyone can view resource_records" ON public.resource_records FOR SELECT USING (verification_status = 'VERIFIED' AND EXISTS(SELECT 1 FROM public.source_records s WHERE s.source_id = resource_records.source_id AND s.verification_status = 'VERIFIED'));

ALTER TABLE public.pyq_sets ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "Anyone can view pyq_sets" ON public.pyq_sets;
CREATE POLICY "Anyone can view pyq_sets" ON public.pyq_sets FOR SELECT USING (verification_status = 'VERIFIED' AND EXISTS(SELECT 1 FROM public.source_records s WHERE s.source_id = pyq_sets.source_id AND s.verification_status = 'VERIFIED'));

ALTER TABLE public.pyq_questions ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "Anyone can view pyq_questions" ON public.pyq_questions;
CREATE POLICY "Anyone can view pyq_questions" ON public.pyq_questions FOR SELECT USING (verification_status = 'VERIFIED' AND EXISTS(SELECT 1 FROM public.pyq_sets p WHERE p.pyq_set_id = pyq_questions.pyq_set_id AND p.verification_status = 'VERIFIED'));

ALTER TABLE public.learner_context_subjects ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "Users can view own context subjects" ON public.learner_context_subjects;
CREATE POLICY "Users can view own context subjects" ON public.learner_context_subjects FOR SELECT USING (EXISTS (SELECT 1 FROM public.learner_academic_contexts c WHERE c.context_id = learner_context_subjects.context_id AND c.user_id = auth.uid()));
DROP POLICY IF EXISTS "Users can insert own context subjects" ON public.learner_context_subjects;
CREATE POLICY "Users can insert own context subjects" ON public.learner_context_subjects FOR INSERT WITH CHECK (EXISTS (SELECT 1 FROM public.learner_academic_contexts c WHERE c.context_id = learner_context_subjects.context_id AND c.user_id = auth.uid()));
DROP POLICY IF EXISTS "Users can delete own context subjects" ON public.learner_context_subjects;
CREATE POLICY "Users can delete own context subjects" ON public.learner_context_subjects FOR DELETE USING (EXISTS (SELECT 1 FROM public.learner_academic_contexts c WHERE c.context_id = learner_context_subjects.context_id AND c.user_id = auth.uid()));

ALTER TABLE public.learning_plan_subjects ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "Users can view own plan subjects" ON public.learning_plan_subjects;
CREATE POLICY "Users can view own plan subjects" ON public.learning_plan_subjects FOR SELECT USING (EXISTS (SELECT 1 FROM public.learning_plans p WHERE p.plan_id = learning_plan_subjects.plan_id AND p.user_id = auth.uid()));
DROP POLICY IF EXISTS "Users can insert own plan subjects" ON public.learning_plan_subjects;
CREATE POLICY "Users can insert own plan subjects" ON public.learning_plan_subjects FOR INSERT WITH CHECK (EXISTS (SELECT 1 FROM public.learning_plans p WHERE p.plan_id = learning_plan_subjects.plan_id AND p.user_id = auth.uid()));
DROP POLICY IF EXISTS "Users can delete own plan subjects" ON public.learning_plan_subjects;
CREATE POLICY "Users can delete own plan subjects" ON public.learning_plan_subjects FOR DELETE USING (EXISTS (SELECT 1 FROM public.learning_plans p WHERE p.plan_id = learning_plan_subjects.plan_id AND p.user_id = auth.uid()));


-- Apply RLS to learner-scoped tables enforcing auth.uid() = user_id.

DO $$
DECLARE
    t text;
BEGIN
    FOR t IN 
        SELECT table_name 
        FROM information_schema.tables 
        WHERE table_schema = 'public' 
          AND table_name IN (
            'learners', 'learner_academic_contexts', 'college_goals', 'learning_plans', 
            'learning_plan_phases', 'learning_activities', 'assessments', 
            'assessment_results', 'learning_signals', 'accountability_commitments', 
            'chat_sessions', 'chat_messages', 'learner_evidence', 'progress_events', 
            'roadmaps'
          )
    LOOP
        EXECUTE format('ALTER TABLE public.%I ENABLE ROW LEVEL SECURITY;', t);
        
        -- Drop existing policies if they exist (idempotent setup)
        EXECUTE format('DROP POLICY IF EXISTS %I ON public.%I;', 'Users can view own ' || t, t);
        EXECUTE format('DROP POLICY IF EXISTS %I ON public.%I;', 'Users can update own ' || t, t);
        EXECUTE format('DROP POLICY IF EXISTS %I ON public.%I;', 'Users can insert own ' || t, t);
        EXECUTE format('DROP POLICY IF EXISTS %I ON public.%I;', 'Users can delete own ' || t, t);
        
        EXECUTE format('
            CREATE POLICY %I 
            ON public.%I FOR SELECT 
            USING (auth.uid() = user_id);
        ', 'Users can view own ' || t, t);
        
        EXECUTE format('
            CREATE POLICY %I 
            ON public.%I FOR UPDATE 
            USING (auth.uid() = user_id)
            WITH CHECK (auth.uid() = user_id);
        ', 'Users can update own ' || t, t);
        
        EXECUTE format('
            CREATE POLICY %I 
            ON public.%I FOR INSERT 
            WITH CHECK (auth.uid() = user_id);
        ', 'Users can insert own ' || t, t);

        EXECUTE format('
            CREATE POLICY %I 
            ON public.%I FOR DELETE 
            USING (auth.uid() = user_id);
        ', 'Users can delete own ' || t, t);
    END LOOP;
END $$;

-- ============================================================================
-- 4. INDEXES
-- ============================================================================

CREATE INDEX IF NOT EXISTS idx_academic_contexts_user ON public.learner_academic_contexts(user_id);
CREATE INDEX IF NOT EXISTS idx_learning_plans_user ON public.learning_plans(user_id);
CREATE INDEX IF NOT EXISTS idx_learning_activities_plan ON public.learning_activities(user_id, plan_id, phase_id);
CREATE INDEX IF NOT EXISTS idx_assessments_user ON public.assessments(user_id, plan_id, phase_id);
CREATE INDEX IF NOT EXISTS idx_assessment_results_user ON public.assessment_results(user_id);
CREATE INDEX IF NOT EXISTS idx_commitments_user ON public.accountability_commitments(user_id);
CREATE INDEX IF NOT EXISTS idx_chat_sessions_user ON public.chat_sessions(user_id, session_id);
CREATE INDEX IF NOT EXISTS idx_roadmaps_user ON public.roadmaps(user_id);

CREATE INDEX IF NOT EXISTS idx_universities_id ON public.universities(university_id);
CREATE INDEX IF NOT EXISTS idx_subjects_id ON public.subjects(subject_id);
CREATE INDEX IF NOT EXISTS idx_curricula_id ON public.curricula(curriculum_id);
CREATE INDEX IF NOT EXISTS idx_pyq_sets_id ON public.pyq_sets(pyq_set_id);
