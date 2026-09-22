import logging
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
    LearnerContextSubject
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
            res = self.client.table("learner_academic_contexts").select("*").eq("user_id", uid).execute()
            if not res.data:
                return None
            
            ctx = res.data[0]
            
            # Fetch relational subjects
            sub_res = self.client.table("learner_context_subjects").select("subject_id").eq("context_id", ctx["context_id"]).eq("user_id", uid).execute()
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
            
            # Sync subjects (delete old, insert new)
            self.client.table("learner_context_subjects").delete().eq("context_id", ctx_id).eq("user_id", uid).execute()
            if subjects:
                subject_rows = [{"context_id": ctx_id, "user_id": uid, "subject_id": sid} for sid in subjects]
                self.client.table("learner_context_subjects").insert(subject_rows).execute()
                
        except Exception as e:
            logger.error("Failed to save_college_academic_context: %s", str(e))
            raise RuntimeError("PERSISTENCE_UNAVAILABLE")

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
            res = self.client.table("learning_plans").select("*").eq("user_id", uid).eq("status", "ACTIVE").order("created_at", desc=True).limit(1).execute()
            if not res.data:
                return None
                
            plan_dict = res.data[0]
            plan_id = plan_dict["plan_id"]
            
            # Fetch Plan Subjects
            sub_res = self.client.table("learning_plan_subjects").select("*").eq("plan_id", plan_id).eq("user_id", uid).execute()
            plan_dict["subjects"] = sub_res.data if sub_res.data else []
            
            # Fetch Phases
            phases_res = self.client.table("learning_plan_phases").select("*").eq("plan_id", plan_id).eq("user_id", uid).order("order").execute()
            phases = phases_res.data if phases_res.data else []
            
            # Fetch Activities
            act_res = self.client.table("learning_activities").select("*").eq("plan_id", plan_id).eq("user_id", uid).order("order").execute()
            activities = act_res.data if act_res.data else []
            
            # Assemble Hierarchy
            for phase in phases:
                phase["activities"] = [a for a in activities if a["phase_id"] == phase["phase_id"]]
                
            plan_dict["phases"] = phases
            return CollegeLearningPlan(**plan_dict)
            
        except Exception as e:
            logger.error("Failed to get_college_learning_plan: %s", str(e))
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
            if plan_data.subjects:
                subs = [s.model_dump() for s in plan_data.subjects]
                for s in subs: s["user_id"] = uid
                self.client.table("learning_plan_subjects").delete().eq("plan_id", plan_id).eq("user_id", uid).execute()
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
            res = self.client.table("accountability_commitments").update({"status": status}).eq("commitment_id", commitment_id).eq("user_id", uid).execute()
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

college_store = CollegeStore()
