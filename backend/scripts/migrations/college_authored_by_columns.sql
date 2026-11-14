-- College provenance columns (round 7 payloads, round 8 migration).
--
-- Round 7 added `authored_by` to the CollegeAssessment and
-- CollegeLearningPlan payloads ("adk:assessment_agent" / "gemini_direct"
-- / "rag_fallback" for diagnostics; "adk:plan_agent" / "static_fallback"
-- for plans) so AI authorship is verifiable in the product itself. The
-- store upserts model dumps wholesale, and PostgREST rejects any key
-- that is not a real column — so until these columns existed, every
-- diagnostic and plan save failed with PERSISTENCE_UNAVAILABLE.
--
-- Applied live on 2026-10-01 during the final-pass verification, after
-- the failure was reproduced against production. The store now also
-- whitelist-filters its dumps to verified columns, so a future
-- model-only field degrades to a dropped key instead of a failed save;
-- this migration remains the record (and the catch-up for any
-- environment built before the columns existed).

ALTER TABLE public.assessments
    ADD COLUMN IF NOT EXISTS authored_by text;

ALTER TABLE public.learning_plans
    ADD COLUMN IF NOT EXISTS authored_by text;
