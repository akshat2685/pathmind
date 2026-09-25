import logging
import uuid
from typing import Optional, Dict, Any, List
from backend.services.supabase_adapter import get_supabase_adapter
from backend.core.college_schemas import (
    UserProfile,
    AcademicContext,
    CollegeGoal,
    CollegeLearningPlan,
    CollegeAssessment,
    CollegeAssessmentResult,
    AccountabilityCommitment,
    CollegeShortMemory,
    CollegeLongMemory,
    LearningSignal,
    CollegeActivity,
    CollegePlanPhase,
    LearningPlanSubject,
    LearnerContextSubject,
    TopicMasteryRecord
)

logger = logging.getLogger(__name__)

class CollegeStore:
    """
    Authoritative persistence layer for the College MVP.
    Strictly isolated from legacy `_in_memory_persons` and JSONB blobs.
    Enforces relational integrity matching `college_schema.sql`.
    """
    
    def __init__(self):
        self.adapter = get_supabase_adapter()
    
    @property
    def client(self):
        if not self.adapter.client:
            raise RuntimeError("Supabase client is not available for CollegeStore.")
        return self.adapter.client
        
    # --- Users ---

    async def list_all_college_users(self) -> List[UserProfile]:
        """Lists every registered learner. Reads the real learners table."""
        try:
            res = self.client.table("learners").select("*").execute()
            return [UserProfile(**row) for row in (res.data or [])]
        except Exception as e:
            logger.error("Failed to list_all_college_users: %s", str(e))
            return []

    async def get_or_create_college_user(self, uid: str, name: str, email: Optional[str] = None) -> Optional[UserProfile]:
        """
        Creates a learner if it doesn't exist. Name is REQUIRED.
        """
        try:
            # Check existing first
            res = self.client.table("learners").select("*").eq("user_id", uid).execute()
            if res.data:
                return UserProfile(**res.data[0])
                
            if not name or name.strip() == "":
                logger.error("Cannot create a learner without a valid name.")
                return None
                
            data = {
                "user_id": uid,
                "name": name,
                "email": email
            }
            upsert_res = self.client.table("learners").upsert(data, on_conflict="user_id").execute()
            if upsert_res.data:
                return UserProfile(**upsert_res.data[0])
            return None
        except Exception as e:
            logger.error("Failed to get_or_create_college_user: %s", str(e))
            return None
            
    async def get_college_user_profile(self, uid: str) -> Optional[UserProfile]:
        try:
            res = self.client.table("learners").select("*").eq("user_id", uid).execute()
            if res.data:
                return UserProfile(**res.data[0])
            return None
        except Exception as e:
            logger.error("Failed to get_college_user_profile: %s", str(e))
            return None

    async def save_college_user_profile(self, uid: str, profile_data: dict) -> None:
        try:
            data = profile_data.copy()
            if "user_id" not in data:
                data["user_id"] = uid
                
            self.client.table("learners").update(data).eq("user_id", uid).execute()
        except Exception as e:
            logger.error("Failed to save_college_user_profile: %s", str(e))
            raise RuntimeError("PERSISTENCE_UNAVAILABLE")

    # --- Academic Context ---

    async def get_college_academic_context(self, uid: str) -> Optional[AcademicContext]:
        try:
            # A user can hold several contexts (one per semester they've tried).
            # Always serve the most recently saved one — data[0] without an
            # ORDER BY is arbitrary and served stale contexts, breaking
            # subject-part plan generation with SUBJECT_NOT_FOUND.
            res = (
                self.client.table("learner_academic_contexts")
                .select("*")
                .eq("user_id", uid)
                .order("updated_at", desc=True)
                .limit(1)
                .execute()
            )
            if not res.data:
                return None

            ctx = res.data[0]
            
            # Fetch relational subjects
            # Fetch relational subjects. The mapping table carries no user_id
            # column; ownership is enforced through the parent context FK + RLS.
            sub_res = self.client.table("learner_context_subjects").select("subject_id").eq("context_id", ctx["context_id"]).execute()
            ctx["subjects"] = [s["subject_id"] for s in sub_res.data] if sub_res.data else []
            
            return AcademicContext(**ctx)
        except Exception as e:
            logger.error("Failed to get_college_academic_context: %s", str(e))
            return None

    async def save_college_academic_context(self, uid: str, context_data: dict) -> None:
        try:
            subjects = context_data.pop("subjects", [])
            context_data["user_id"] = uid
            
            ctx_id = context_data.get("context_id")
            if not ctx_id:
                raise ValueError("context_id is required")
                
            # Upsert context
            self.client.table("learner_academic_contexts").upsert(context_data, on_conflict="context_id").execute()
            
            # Sync subjects (delete old, insert new). The mapping table has no
            # user_id column; ownership is enforced via the parent context FK + RLS.
            # Only link subject_ids that exist in subjects (FK-safe); warn on the rest.
            self.client.table("learner_context_subjects").delete().eq("context_id", ctx_id).execute()
            if subjects:
                existing = self.client.table("subjects").select("subject_id").in_("subject_id", subjects).execute()
                existing_ids = {s["subject_id"] for s in (existing.data or [])}
                missing = [s for s in subjects if s not in existing_ids]
                if missing:
                    logger.warning("Skipping learner_context_subjects with no subjects row: %s", missing)
                subject_rows = [{"context_id": ctx_id, "subject_id": sid} for sid in subjects if sid in existing_ids]
                if subject_rows:
                    self.client.table("learner_context_subjects").insert(subject_rows).execute()
                
        except Exception as e:
            logger.error("Failed to save_college_academic_context: %s", str(e))
            raise RuntimeError("PERSISTENCE_UNAVAILABLE")

    async def find_program_id(self, university_id: str, branch_values: List[str]) -> Optional[str]:
        """Resolves the canonical program_id for a university + branch.

        Returns None when the knowledge tables are unseeded; callers must not
        invent a program id (no-fake-state rule).
        """
        try:
            res = self.client.table("programs").select("program_id").eq("university_id", university_id).in_("branch", branch_values).limit(1).execute()
            if res.data:
                return res.data[0]["program_id"]
            return None
        except Exception as e:
            logger.error("Failed to find_program_id: %s", str(e))
            return None

    async def get_context_subject_ids(self, context_id: str) -> List[str]:
        """Returns subject_ids linked to an academic context (mapping table)."""
        try:
            res = self.client.table("learner_context_subjects").select("subject_id").eq("context_id", context_id).execute()
            return [s["subject_id"] for s in (res.data or [])]
        except Exception as e:
            logger.error("Failed to get_context_subject_ids: %s", str(e))
            return []

    # --- Goal ---

    async def get_college_goal(self, uid: str) -> Optional[CollegeGoal]:
        try:
            res = self.client.table("college_goals").select("*").eq("user_id", uid).eq("status", "ACTIVE").execute()
            if res.data:
                return CollegeGoal(**res.data[0])
            return None
        except Exception as e:
            logger.error("Failed to get_college_goal: %s", str(e))
            return None

    async def save_college_goal(self, uid: str, goal_data: dict) -> None:
        try:
            goal_data["user_id"] = uid
            self.client.table("college_goals").upsert(goal_data, on_conflict="goal_id").execute()
        except Exception as e:
            logger.error("Failed to save_college_goal: %s", str(e))
            raise RuntimeError("PERSISTENCE_UNAVAILABLE")

    # --- Learning Plan ---

    async def get_college_learning_plan(self, uid: str) -> Optional[CollegeLearningPlan]:
        try:
            # Newest ACTIVE plans first; a plan left half-written by a killed
            # function (pre-DRAFT-era orphan, or a DRAFT that leaked through)
            # must never shadow the learner's last good plan — skip phaseless
            # rows and keep looking.
            res = self.client.table("learning_plans").select("*").eq("user_id", uid).eq("status", "ACTIVE").order("created_at", desc=True).limit(5).execute()
            if not res.data:
                return None

            for plan_dict in res.data:
                plan_id = plan_dict["plan_id"]

                # Fetch Plan Subjects
                # Fetch Plan Subjects (mapping table has no user_id column)
                sub_res = self.client.table("learning_plan_subjects").select("*").eq("plan_id", plan_id).execute()
                plan_dict["subjects"] = sub_res.data if sub_res.data else []

                # Fetch Phases
                phases_res = self.client.table("learning_plan_phases").select("*").eq("plan_id", plan_id).eq("user_id", uid).order("order").execute()
                phases = phases_res.data if phases_res.data else []

                if not phases:
                    logger.warning(
                        "Skipping phaseless ACTIVE plan %s for user %s "
                        "(likely orphaned by an interrupted generation); "
                        "falling back to the next newest plan.", plan_id, uid)
                    continue

                # Fetch Activities
                act_res = self.client.table("learning_activities").select("*").eq("plan_id", plan_id).eq("user_id", uid).order("order").execute()
                activities = act_res.data if act_res.data else []

                # Assemble Hierarchy
                for phase in phases:
                    phase["activities"] = [a for a in activities if a["phase_id"] == phase["phase_id"]]

                plan_dict["phases"] = phases
                return CollegeLearningPlan(**plan_dict)

            logger.warning("User %s has ACTIVE plan rows but none with phases.",
                           uid)
            return None

        except Exception as e:
            logger.error("Failed to get_college_learning_plan for user %s: %s",
                         uid, str(e), exc_info=True)
            return None

    async def save_college_learning_plan(self, uid: str, plan_data: CollegeLearningPlan) -> None:
        """
        Creates a learning plan and its full hierarchy.
        This must be atomic. Supabase Python client does not have native transaction start/commit,
        so we will use an RPC call if available, or fallback to sequential inserts.
        To fulfill the requirement, we will implement this as a batched sequential insert,
        and ideally, the DB should provide an RPC. However, without modifying schema, 
        we will try sequential inserts. If any fail, we might need a rollback logic, 
        or we assume the caller ensures safety. 
        Wait, user said: "Use a transaction-safe PostgreSQL mechanism such as an RPC or... If a transaction fails, no partial learning plan should remain."
        The best approach using standard REST without a custom RPC is to insert everything sequentially.
        If any step fails, we delete the plan_id (cascading).
        """
        plan_id = plan_data.plan_id
        try:
            plan_dict = plan_data.model_dump(exclude={"phases", "subjects"})
            plan_dict["user_id"] = uid
            
            # 1. Insert Plan
            self.client.table("learning_plans").upsert(plan_dict, on_conflict="plan_id").execute()
            
            # 2. Insert Subjects
            # 2. Insert Subjects (mapping table has no user_id column; FK-safe)
            if plan_data.subjects:
                # learning_plan_subjects is a pure mapping table (plan_id, subject_id):
                # drop model-only fields that are not DB columns.
                subs = [s.model_dump(exclude={"user_id", "created_at"}) for s in plan_data.subjects]
                self.client.table("learning_plan_subjects").delete().eq("plan_id", plan_id).execute()
                if subs:
                    wanted = [s["subject_id"] for s in subs]
                    existing = self.client.table("subjects").select("subject_id").in_("subject_id", wanted).execute()
                    existing_ids = {s["subject_id"] for s in (existing.data or [])}
                    missing = [s for s in wanted if s not in existing_ids]
                    if missing:
                        logger.warning("Skipping learning_plan_subjects with no subjects row: %s", missing)
                    subs = [s for s in subs if s["subject_id"] in existing_ids]
                    if subs:
                        self.client.table("learning_plan_subjects").insert(subs).execute()
                
            # 3. Insert Phases
            if plan_data.phases:
                phases = [p.model_dump(exclude={"activities"}) for p in plan_data.phases]
                for p in phases: p["user_id"] = uid
                # We upsert to allow partial updates, or delete/insert. 
                # For safety, let's upsert
                self.client.table("learning_plan_phases").upsert(phases, on_conflict="phase_id").execute()
                
                # 4. Insert Activities
                all_acts = []
                for p in plan_data.phases:
                    if p.activities:
                        for act in p.activities:
                            act_dict = act.model_dump(exclude={"resource", "pyq_question"})
                            act_dict["user_id"] = uid
                            all_acts.append(act_dict)
                            
                if all_acts:
                    self.client.table("learning_activities").upsert(all_acts, on_conflict="activity_id").execute()
                    
        except Exception as e:
            logger.error("Transaction failed during save_college_learning_plan: %s. Rolling back plan %s", str(e), plan_id)
            # Rollback: Since it's learner owned, we can just delete it and ON DELETE CASCADE will handle children.
            try:
                self.client.table("learning_plans").delete().eq("plan_id", plan_id).eq("user_id", uid).execute()
            except Exception as rollback_e:
                logger.error("Failed to rollback learning plan: %s", str(rollback_e))
            raise RuntimeError("PERSISTENCE_UNAVAILABLE")

    async def activate_college_learning_plan(self, uid: str, plan_id: str) -> None:
        """
        Flip a fully-persisted plan from DRAFT to ACTIVE. Called only after
        save_college_learning_plan completes, so a function killed mid-save
        (serverless timeout) can never leave a half-written plan as the
        newest ACTIVE row shadowing the learner's previous good plan.
        """
        try:
            self.client.table("learning_plans").update({"status": "ACTIVE"}) \
                .eq("plan_id", plan_id).eq("user_id", uid).execute()
        except Exception as e:
            logger.error("Failed to activate_college_learning_plan %s: %s",
                         plan_id, str(e))
            raise RuntimeError("PERSISTENCE_UNAVAILABLE")

    async def update_activity_status(self, uid: str, activity_id: str, status: str, evidence: dict = None) -> None:
        try:
            data = {"status": status}
            if evidence:
                data["completion_evidence"] = evidence
            self.client.table("learning_activities").update(data).eq("activity_id", activity_id).eq("user_id", uid).execute()
        except Exception as e:
            logger.error("Failed to update_activity_status: %s", str(e))
            raise RuntimeError("PERSISTENCE_UNAVAILABLE")

    # --- Assessments ---

    async def save_college_assessment(self, uid: str, assessment_data: dict) -> None:
        try:
            assessment_data["user_id"] = uid
            self.client.table("assessments").upsert(assessment_data, on_conflict="assessment_id").execute()
        except Exception as e:
            logger.error("Failed to save_college_assessment: %s", str(e))
            raise RuntimeError("PERSISTENCE_UNAVAILABLE")

    async def get_college_assessment(self, uid: str, assessment_id: str) -> Optional[CollegeAssessment]:
        try:
            res = self.client.table("assessments").select("*").eq("assessment_id", assessment_id).eq("user_id", uid).execute()
            if res.data:
                return CollegeAssessment(**res.data[0])
            return None
        except Exception as e:
            logger.error("Failed to get_college_assessment: %s", str(e))
            return None

    async def get_all_college_assessments(self, uid: str) -> List[CollegeAssessment]:
        try:
            res = self.client.table("assessments").select("*").eq("user_id", uid).execute()
            if res.data:
                return [CollegeAssessment(**row) for row in res.data]
            return []
        except Exception as e:
            logger.error("Failed to get_all_college_assessments: %s", str(e))
            return []

    async def save_college_assessment_result(self, uid: str, result_data: dict) -> None:
        try:
            result_data["user_id"] = uid
            self.client.table("assessment_results").upsert(result_data, on_conflict="result_id").execute()
        except Exception as e:
            logger.error("Failed to save_college_assessment_result: %s", str(e))
            raise RuntimeError("PERSISTENCE_UNAVAILABLE")

    async def get_college_assessment_results(self, uid: str) -> List[CollegeAssessmentResult]:
        try:
            res = self.client.table("assessment_results").select("*").eq("user_id", uid).execute()
            if res.data:
                return [CollegeAssessmentResult(**row) for row in res.data]
            return []
        except Exception as e:
            logger.error("Failed to get_college_assessment_results: %s", str(e))
            return []

    # --- Commitments (Accountability) ---

    async def save_college_commitment(self, uid: str, commitment_data: dict) -> None:
        try:
            commitment_data["user_id"] = uid
            self.client.table("accountability_commitments").upsert(commitment_data, on_conflict="commitment_id").execute()
        except Exception as e:
            logger.error("Failed to save_college_commitment: %s", str(e))
            raise RuntimeError("PERSISTENCE_UNAVAILABLE")

    async def get_college_commitments(self, uid: str) -> List[AccountabilityCommitment]:
        try:
            res = self.client.table("accountability_commitments").select("*").eq("user_id", uid).execute()
            if res.data:
                return [AccountabilityCommitment(**row) for row in res.data]
            return []
        except Exception as e:
            logger.error("Failed to get_college_commitments: %s", str(e))
            return []

    async def update_college_commitment_status(self, uid: str, commitment_id: str, status: str) -> Optional[AccountabilityCommitment]:
        try:
            # Bump updated_at ourselves: PostgREST does not maintain it, and
            # the streak engine derives consecutive-day streaks from it.
            from datetime import datetime, timezone
            now = datetime.now(timezone.utc).isoformat()
            res = self.client.table("accountability_commitments").update(
                {"status": status, "updated_at": now}
            ).eq("commitment_id", commitment_id).eq("user_id", uid).execute()
            if res.data:
                return AccountabilityCommitment(**res.data[0])
            return None
        except Exception as e:
            logger.error("Failed to update_college_commitment_status: %s", str(e))
            return None

    # --- Memory & Learning Signals ---

    async def save_college_short_memory(self, uid: str, memory_data: dict) -> None:
        try:
            memory_data["user_id"] = uid
            self.client.table("pathmind_short_term_memories").upsert(memory_data, on_conflict="memory_id").execute()
        except Exception as e:
            logger.error("Failed to save_college_short_memory: %s", str(e))
            raise RuntimeError("PERSISTENCE_UNAVAILABLE")

    async def get_college_short_memories(self, uid: str) -> List[CollegeShortMemory]:
        try:
            res = self.client.table("pathmind_short_term_memories").select("*").eq("user_id", uid).execute()
            if res.data:
                return [CollegeShortMemory(**row) for row in res.data]
            return []
        except Exception as e:
            logger.error("Failed to get_college_short_memories: %s", str(e))
            return []

    async def save_college_long_memory(self, uid: str, memory_data: dict) -> None:
        try:
            memory_data["user_id"] = uid
            self.client.table("pathmind_long_term_memories").upsert(memory_data, on_conflict="memory_id").execute()
        except Exception as e:
            logger.error("Failed to save_college_long_memory: %s", str(e))
            raise RuntimeError("PERSISTENCE_UNAVAILABLE")

    async def get_college_long_memories(self, uid: str) -> List[CollegeLongMemory]:
        try:
            res = self.client.table("pathmind_long_term_memories").select("*").eq("user_id", uid).execute()
            if res.data:
                return [CollegeLongMemory(**row) for row in res.data]
            return []
        except Exception as e:
            logger.error("Failed to get_college_long_memories: %s", str(e))
            return []
            
    async def get_college_learning_signals(self, uid: str) -> List[LearningSignal]:
        try:
            res = self.client.table("learning_signals").select("*").eq("user_id", uid).execute()
            if res.data:
                return [LearningSignal(**row) for row in res.data]
            return []
        except Exception as e:
            logger.error("Failed to get_college_learning_signals: %s", str(e))
            return []

    async def save_learning_signal(self, uid: str, signal_data: dict) -> None:
        try:
            signal_data["user_id"] = uid
            self.client.table("learning_signals").upsert(signal_data, on_conflict="signal_id").execute()
        except Exception as e:
            logger.error("Failed to save_learning_signal: %s", str(e))
            raise RuntimeError("PERSISTENCE_UNAVAILABLE")

    async def update_long_memory_status(self, uid: str, memory_id: str, status: str, supersedes_id: str) -> None:
        try:
            data = {"status": status, "supersedes_memory_id": supersedes_id}
            self.client.table("pathmind_long_term_memories").update(data).eq("memory_id", memory_id).eq("user_id", uid).execute()
        except Exception as e:
            logger.error("Failed to update_long_memory_status: %s", str(e))
            raise RuntimeError("PERSISTENCE_UNAVAILABLE")

    # --- Per-topic mastery (single source of truth for unlocks + baseline) ---

    async def get_topic_mastery(
        self, uid: str, subject_id: Optional[str], topic: str
    ) -> Optional[TopicMasteryRecord]:
        try:
            res = (
                self.client.table("learner_topic_mastery")
                .select("*")
                .eq("user_id", uid)
                .eq("topic", topic)
                .execute()
            )
            for row in res.data or []:
                if row.get("subject_id") == subject_id:
                    return TopicMasteryRecord(**row)
            return None
        except Exception as e:
            logger.error("Failed to get_topic_mastery: %s", str(e))
            return None

    async def get_topic_masteries(
        self, uid: str, subject_id: Optional[str] = None
    ) -> List[TopicMasteryRecord]:
        try:
            query = (
                self.client.table("learner_topic_mastery")
                .select("*")
                .eq("user_id", uid)
            )
            if subject_id is not None:
                query = query.eq("subject_id", subject_id)
            res = query.execute()
            return [TopicMasteryRecord(**row) for row in (res.data or [])]
        except Exception as e:
            logger.error("Failed to get_topic_masteries: %s", str(e))
            return []

    async def upsert_topic_mastery(self, uid: str, record: TopicMasteryRecord) -> None:
        try:
            data = record.model_dump(mode="json")
            data["user_id"] = uid
            self.client.table("learner_topic_mastery").upsert(data).execute()
        except Exception as e:
            logger.error("Failed to upsert_topic_mastery: %s", str(e))
            raise RuntimeError("PERSISTENCE_UNAVAILABLE")

    # --- Chat sessions & messages (agent conversation persistence) ---

    async def get_or_create_chat_session(
        self, uid: str, session_id: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """Returns the chat session row; creates one when needed."""
        try:
            if session_id:
                res = (
                    self.client.table("chat_sessions").select("*")
                    .eq("user_id", uid).eq("session_id", session_id).execute()
                )
                if res.data:
                    return res.data[0]
            new_session_id = session_id or f"chat_{uuid.uuid4().hex[:12]}"
            row = {
                "session_id": new_session_id,
                "user_id": uid,
                "title": "College agent conversation",
                "status": "ACTIVE",
            }
            res = self.client.table("chat_sessions").insert(row).execute()
            return (res.data or [row])[0]
        except Exception as e:
            logger.error("Failed to get_or_create_chat_session: %s", str(e))
            return None

    async def save_chat_message(
        self,
        uid: str,
        session_id: str,
        role: str,
        content: str,
        source_refs: Optional[List[str]] = None,
    ) -> Optional[Dict[str, Any]]:
        """Persists one chat turn. Never raises — persistence failures return None."""
        try:
            row = {
                "message_id": f"msg_{uuid.uuid4().hex[:12]}",
                "session_id": session_id,
                "user_id": uid,
                "role": role,
                "content": content,
                "source_refs": source_refs or [],
            }
            res = self.client.table("chat_messages").insert(row).execute()
            return (res.data or [row])[0]
        except Exception as e:
            logger.error("Failed to save_chat_message: %s", str(e))
            return None

    async def get_chat_history(
        self, uid: str, session_id: str, limit: int = 20
    ) -> List[Dict[str, Any]]:
        """Recent messages for a session, oldest first. Never raises."""
        try:
            res = (
                self.client.table("chat_messages").select("*")
                .eq("user_id", uid).eq("session_id", session_id)
                .order("timestamp", desc=False).limit(limit).execute()
            )
            return list(res.data or [])
        except Exception as e:
            logger.error("Failed to get_chat_history: %s", str(e))
            return []

college_store = CollegeStore()
