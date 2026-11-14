# Pre-Migration Validation Report

> [!IMPORTANT]
> **`college_schema.sql` has NOT been executed against Supabase.**
> **No memory migration has been executed against Supabase.**

---

## A. Memory Schema Audit

### Actual Current Supabase Database Columns

The memory tables were created by [`memory_schema.sql`](file:///d:/learning%20path%20hackathon/backend/scripts/migrations/memory_schema.sql). Both tables use the column name **`learner_id`**:

| Table | Identity Column | Type | Constraint |
|-------|----------------|------|------------|
| `pathmind_short_term_memories` | `learner_id` | `UUID NOT NULL` | `REFERENCES auth.users(id) ON DELETE CASCADE` |
| `pathmind_long_term_memories` | `learner_id` | `UUID NOT NULL` | `REFERENCES auth.users(id) ON DELETE CASCADE` |

### RLS Policies (Current Database)

Both RLS policies use `learner_id`:

```sql
-- Short-term
USING (auth.uid() = learner_id)
WITH CHECK (auth.uid() = learner_id)

-- Long-term
USING (auth.uid() = learner_id)
WITH CHECK (auth.uid() = learner_id)
```

### Indexes (Current Database)

```sql
idx_short_mem_learner ON pathmind_short_term_memories(learner_id)
idx_long_mem_learner  ON pathmind_long_term_memories(learner_id)
```

---

## B. Exact Memory Mismatch

The backend was refactored to use `user_id` consistently for the College MVP, but the existing memory tables in Supabase were **never migrated** from `learner_id` to `user_id`.

| Layer | Column Used | Status |
|-------|-------------|--------|
| **Supabase DB** (`memory_schema.sql`) | `learner_id` | ✅ Exists |
| **Pydantic models** (`CollegeShortMemory`, `CollegeLongMemory`) | `user_id` | ❌ Mismatch |
| **college_store.py** `.save_college_short_memory()` | Sets `memory_data["user_id"]` | ❌ Mismatch |
| **college_store.py** `.get_college_short_memories()` | `.eq("user_id", uid)` | ❌ Mismatch |
| **college_store.py** `.save_college_long_memory()` | Sets `memory_data["user_id"]` | ❌ Mismatch |
| **college_store.py** `.get_college_long_memories()` | `.eq("user_id", uid)` | ❌ Mismatch |
| **college_store.py** `.update_long_memory_status()` | `.eq("user_id", uid)` | ❌ Mismatch |

### Additional Column Name Mismatch

The `update_long_memory_status` method sends `{"supersedes_id": ...}` but the database column is named `supersedes_memory_id`.

| Layer | Column Name | Status |
|-------|-------------|--------|
| **Supabase DB** | `supersedes_memory_id` | ✅ Exists |
| **college_store.py** `update_long_memory_status()` | `supersedes_id` | ❌ Mismatch |

---

## C. Required Memory Migration/Change

### Option 1: Rename database column (Recommended)

This aligns the database with the entire backend and the canonical College MVP identity standard (`user_id`).

**SQL migration required** (DO NOT EXECUTE YET):

```sql
-- 1. Rename columns
ALTER TABLE public.pathmind_short_term_memories RENAME COLUMN learner_id TO user_id;
ALTER TABLE public.pathmind_long_term_memories RENAME COLUMN learner_id TO user_id;

-- 2. Drop old RLS policies
DROP POLICY IF EXISTS "Learners can access own short-term memory" ON public.pathmind_short_term_memories;
DROP POLICY IF EXISTS "Learners can access own long-term memory" ON public.pathmind_long_term_memories;

-- 3. Recreate RLS policies with new column name
CREATE POLICY "Users can access own short-term memory"
ON public.pathmind_short_term_memories FOR ALL
USING (auth.uid() = user_id)
WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can access own long-term memory"
ON public.pathmind_long_term_memories FOR ALL
USING (auth.uid() = user_id)
WITH CHECK (auth.uid() = user_id);

-- 4. Drop old indexes and recreate
DROP INDEX IF EXISTS idx_short_mem_learner;
DROP INDEX IF EXISTS idx_long_mem_learner;
CREATE INDEX idx_short_mem_user ON public.pathmind_short_term_memories(user_id);
CREATE INDEX idx_long_mem_user ON public.pathmind_long_term_memories(user_id);
```

### Backend fix required

In [`college_store.py`](file:///d:/learning%20path%20hackathon/backend/services/college_store.py#L385-L391):

```diff
-data = {"status": status, "supersedes_id": supersedes_id}
+data = {"status": status, "supersedes_memory_id": supersedes_id}
```

### Data migration

- **No data loss**: `ALTER TABLE RENAME COLUMN` preserves all existing data.
- **No backfill needed**: The column values remain identical; only the name changes.
- **Index recreation**: Old indexes are dropped and new ones created on the renamed column.
- **RLS**: Old policies referencing `learner_id` must be dropped and recreated for `user_id`.

### Option 2: Change backend to use `learner_id`

This would require reverting all Pydantic models and store methods back to `learner_id`. This is **not recommended** because the entire College MVP backend has been standardized on `user_id`.

---

## D. Disposable PostgreSQL Validation Result

PostgreSQL 18.4 is installed locally and the server is accepting connections on `localhost:5432`.

**Status: PENDING** — awaiting PostgreSQL credentials to create a disposable `pathmind_validate` database and execute `college_schema.sql` against it.

> [!WARNING]
> Real PostgreSQL validation has not yet been completed. The report below uses static analysis only.

---

## E. Final Phase/Assessment FK Verification

| Search | Expected | Actual |
|--------|----------|--------|
| `fk_phase_assessment` | 0 occurrences | ✅ 0 occurrences |
| `REFERENCES public.assessments(user_id, plan_id, phase_id, assessment_id)` | 0 occurrences | ✅ 0 occurrences |
| `REFERENCES public.learning_plan_phases(user_id, plan_id, phase_id)` | ≥1 (assessments FK) | ✅ 3 occurrences (assessments, assessment_results, accountability_commitments) |

The circular FK is fully removed. `learning_plan_phases.assessment_id` remains as an application-level column with no database FK.

---

## F. Composite FK Audit

All composite FKs and their referenced uniqueness constraints:

| FK Columns | Referenced Table | Referenced Columns | Action | Uniqueness |
|-----------|-----------------|-------------------|--------|------------|
| `(university_id, program_id)` | `programs` | `(university_id, program_id)` | RESTRICT | ✅ `UNIQUE(university_id, program_id)` |
| `(curriculum_id, subject_id)` | `curriculum_subjects` | `(curriculum_id, subject_id)` | CASCADE | ✅ `PRIMARY KEY(curriculum_id, subject_id)` |
| `(university_id, program_id)` | `programs` | `(university_id, program_id)` | RESTRICT | ✅ `UNIQUE` |
| `(curriculum_id, subject_id)` | `curriculum_subjects` | `(curriculum_id, subject_id)` | RESTRICT | ✅ `PRIMARY KEY` |
| `(primary_university_id, primary_program_id)` | `programs` | `(university_id, program_id)` | SET NULL | ✅ `UNIQUE` |
| `(university_id, program_id)` | `programs` | `(university_id, program_id)` | SET NULL | ✅ `UNIQUE` |
| `(user_id, goal_id)` | `college_goals` | `(user_id, goal_id)` | RESTRICT | ✅ `UNIQUE(user_id, goal_id)` |
| `(user_id, plan_id)` | `learning_plans` | `(user_id, plan_id)` | CASCADE | ✅ `UNIQUE(user_id, plan_id)` |
| `(user_id, plan_id, phase_id)` | `learning_plan_phases` | `(user_id, plan_id, phase_id)` | CASCADE | ✅ `UNIQUE(user_id, plan_id, phase_id)` |
| `(user_id, current_plan_id)` | `learning_plans` | `(user_id, plan_id)` | RESTRICT | ✅ `UNIQUE(user_id, plan_id)` |
| `(user_id, related_phase_id)` | `learning_plan_phases` | `(user_id, phase_id)` | RESTRICT | ✅ `UNIQUE(user_id, phase_id)` |

All composite FK references are covered by matching `UNIQUE` or `PRIMARY KEY` constraints.

---

## G. SET NULL Audit

8 remaining `ON DELETE SET NULL` occurrences — all valid:

| Line | Table | Column(s) | Nullable? | Valid? |
|------|-------|-----------|-----------|--------|
| 169 | `pyq_questions` | `source_id TEXT` | ✅ Yes | ✅ |
| 192 | `learners` | `(primary_university_id TEXT, primary_program_id TEXT)` | ✅ Both nullable | ✅ |
| 210 | `learner_academic_contexts` | `(university_id TEXT, program_id TEXT)` | ✅ Both nullable | ✅ |
| 281 | `learning_activities` | `resource_id TEXT` | ✅ Yes | ✅ |
| 282 | `learning_activities` | `pyq_question_id TEXT` | ✅ Yes | ✅ |
| 332 | `learning_signals` | `subject_id TEXT` | ✅ Yes | ✅ |
| 364 | `chat_sessions` | `current_subject_id TEXT` | ✅ Yes | ✅ |
| 394 | `learner_evidence` | `related_subject_id TEXT` | ✅ Yes | ✅ |

Zero `ON DELETE SET NULL` actions target `NOT NULL` columns.

---

## H. Backend Test Results

Tests were run honestly with no mocking. Failures are genuine `PGRST204`/`PGRST205` errors caused by the database schema not yet being migrated:

- `test_memory_pipeline.py`: 6 failed, 1 passed — failures are all `PERSISTENCE_UNAVAILABLE` from `PGRST204: Could not find the 'user_id' column of 'pathmind_long_term_memories'`
- `test_trust_layer.py` / `test_proactive_memory.py`: Same category of schema-cache failures

These are **not** bugs in the code. They are the expected result of running against a database that does not yet have the new schema.

---

## I. What Remains Before Supabase Migration

| # | Item | Status | Blocking? |
|---|------|--------|-----------|
| 1 | Fix `supersedes_memory_id` column name in `college_store.py` | **NOT YET DONE** | ✅ Yes |
| 2 | Memory table column rename migration (`learner_id` → `user_id`) | **NOT YET EXECUTED** | ✅ Yes |
| 3 | Real PostgreSQL validation of `college_schema.sql` | **PENDING CREDENTIALS** | ✅ Yes |
| 4 | Execute `college_schema.sql` against Supabase | **NOT DONE** | ✅ Yes |
| 5 | Execute memory column rename against Supabase | **NOT DONE** | ✅ Yes |
| 6 | Run full integration test suite against migrated database | **NOT DONE** | ✅ Yes |

> [!CAUTION]
> **Execution order matters.** The memory column rename must be executed **before** `college_schema.sql` because `college_schema.sql` explicitly skips the memory tables (`DO NOT recreate/modify pathmind_short_term_memories or pathmind_long_term_memories`). The memory tables must already have `user_id` columns when the college schema is applied, or the backend will continue to fail with `PGRST204`.

---

**`college_schema.sql` has NOT been executed against Supabase.**

**No memory migration has been executed against Supabase.**
