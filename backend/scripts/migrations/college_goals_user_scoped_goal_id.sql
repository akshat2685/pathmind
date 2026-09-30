-- College goals are per-learner rows.
--
-- The first college schema made college_goals.goal_id globally UNIQUE while
-- learning_plans references the composite (user_id, goal_id). That combination
-- breaks as soon as two learners request the same static goal slug (for
-- example "goal_semester"): the second learner cannot create or upsert their
-- own goal row.
--
-- Apply AFTER deploying backend code that writes per-user canonical goal IDs
-- and upserts college_goals on (user_id, goal_id). Existing databases created
-- from college_schema.sql already have UNIQUE(user_id, goal_id); this migration
-- only removes the incorrect global uniqueness on goal_id alone.

ALTER TABLE public.college_goals
    DROP CONSTRAINT IF EXISTS college_goals_goal_id_key;
