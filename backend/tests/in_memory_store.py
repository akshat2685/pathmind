"""
InMemoryStore — TEST DOUBLE ONLY.

In-memory fake with the same method signatures as PmStore, for unit tests
that need a fast store without a live Supabase database. Never imported
by production code: production persistence is PmStore (Supabase) via
backend/services/pm_store.py.
"""

from typing import Optional, Dict, Any, List
import asyncio
from datetime import datetime, timezone

class InMemoryStore:
    _in_memory_cache: Dict[str, Any] = {}
    _in_memory_persons: Dict[str, Dict[str, Any]] = {}
    _in_memory_shared_patterns: List[Dict[str, Any]] = []
    _person_locks: Dict[str, asyncio.Lock] = {}


    def get_person_lock(self, person_id: str) -> asyncio.Lock:
        if person_id not in self._person_locks:
            self._person_locks[person_id] = asyncio.Lock()
        return self._person_locks[person_id]


    def __init__(self):
        # Pure in-memory store. TEST DOUBLE ONLY — never used in production.
        # Production persistence is PmStore (Supabase); see backend/services/pm_store.py.
        pass  # no external backend; all state lives in the dicts below


    async def check_health(self) -> str:
        return "IN_MEMORY_ACTIVE"


    def _ensure_person_bucket(self, person_id: str):
        if person_id not in self._in_memory_persons:
            self._in_memory_persons[person_id] = {
                "assessments": [],
                "drafts": {},
                "memories": [],
                "structured_memories": [],
                "path_history": [],
                "active_path": None,
                "roadmaps": [],
                "active_roadmap": None,
                "submissions": [],
                "evaluations": [],
                "learning_events": [],
                "personal_agent_models": [],
                "active_personal_agent_model": None,
                "micro_adaptations": [],
                "career_profile": None,
                "career_goal": None,
                "readiness_reports": [],
                "active_readiness_report": None,
                "career_checkpoints": [],
                "tailored_resumes": [],
                "proposed_adaptations": [],
                "adaptation_audits": [],
                "canonical_evidence": [],
                "evaluation_attempts": [],
                "evidence_disputes": [],
                "skill_mastery_profiles": {},
                "decision_records": [],
                "context_conflicts": [],
                "event_records": [],
                "interventions": [],
                "notification_preferences": None,
                "structured_recommendations": [],
                "recommendation_explanations": {},
                "recommendation_feedback": [],
                "progress_insights": [],
                "learning_strategy_profiles": [],
                "recurring_misconceptions": [],
                "turning_points": [],
                "canonical_artifacts": [],
                "artifact_defense_sessions": [],
                "claims_validated": [],
                "step_verifications": [],
                "canonical_actions": [],
                "opportunity_applications": [],
                "execution_pause_state": None,
                "orchestration_traces": [],
                "action_proposals": [],
                "person_record": None,
                "journey_state": None,
                "assessment_blueprint": None
            }

    # --- Knowledge Cache ---

    async def get_cached_knowledge(self, key: str) -> Optional[Dict[str, Any]]:
        return self._in_memory_cache.get(key)

    async def set_cached_knowledge(self, key: str, data: Dict[str, Any]) -> None:
        self._in_memory_cache[key] = data
        return

    async def save_assessment_result(self, person_id: str, result_data: Dict[str, Any]) -> None:
        self._ensure_person_bucket(person_id)
        self._in_memory_persons[person_id]["assessments"].append(result_data)

        return

    async def get_assessment_results(self, person_id: str) -> List[Dict[str, Any]]:
        return self._in_memory_persons.get(person_id, {}).get("assessments", [])

    async def save_assessment_draft(self, person_id: str, assessment_id: str, draft_data: Dict[str, Any]) -> None:
        self._ensure_person_bucket(person_id)
        self._in_memory_persons[person_id]["drafts"][assessment_id] = draft_data

        return

    async def get_assessment_draft(self, person_id: str, assessment_id: str) -> Optional[Dict[str, Any]]:
        return self._in_memory_persons.get(person_id, {}).get("drafts", {}).get(assessment_id)

    async def save_counseling_profile(self, person_id: str, profile_data: Dict[str, Any]) -> None:
        self._ensure_person_bucket(person_id)
        self._in_memory_persons[person_id]["profile"] = profile_data

        return

    async def get_counseling_profile(self, person_id: str) -> Optional[Dict[str, Any]]:
        return self._in_memory_persons.get(person_id, {}).get("profile")

    async def save_personal_memory(self, person_id: str, memory_data: Dict[str, Any]) -> None:
        self._ensure_person_bucket(person_id)
        mem_id = memory_data.get("memory_id")
        existing_idx = next((i for i, m in enumerate(self._in_memory_persons[person_id]["structured_memories"]) if m.get("memory_id") == mem_id), -1)
        if existing_idx >= 0:
            self._in_memory_persons[person_id]["structured_memories"][existing_idx] = memory_data
        else:
            self._in_memory_persons[person_id]["structured_memories"].append(memory_data)

        return

    async def save_counseling_memory(self, person_id: str, memory_data: Dict[str, Any]) -> None:
        """Persists a counseling episodic memory item via the personal memory store."""
        await self.save_personal_memory(person_id, memory_data)


    async def get_personal_memories(
        self,
        person_id: str,
        memory_type: Optional[str] = None,
        topic: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        self._ensure_person_bucket(person_id)
        mems = self._in_memory_persons[person_id]["structured_memories"]

        if memory_type and memory_type != "ALL":
            mems = [m for m in mems if m.get("memory_type") == memory_type]
        if topic:
            mems = [m for m in mems if topic.lower() in m.get("topic", "").lower()]

        return mems


    async def get_memories(self, person_id: str) -> List[Dict[str, Any]]:
        return await self.get_personal_memories(person_id)


    async def delete_personal_memory(self, person_id: str, memory_id: str) -> bool:
        self._ensure_person_bucket(person_id)
        self._in_memory_persons[person_id]["structured_memories"] = [
            m for m in self._in_memory_persons[person_id]["structured_memories"] if m.get("memory_id") != memory_id
        ]
        return True

    async def save_shared_pattern(self, pattern_data: Dict[str, Any]) -> None:
        pat_id = pattern_data.get("pattern_id")
        existing_idx = next((i for i, p in enumerate(self._in_memory_shared_patterns) if p.get("pattern_id") == pat_id), -1)
        if existing_idx >= 0:
            self._in_memory_shared_patterns[existing_idx] = pattern_data
        else:
            self._in_memory_shared_patterns.append(pattern_data)

        return

    async def get_shared_patterns(self) -> List[Dict[str, Any]]:
        return self._in_memory_shared_patterns

    async def save_selected_path(self, person_id: str, selection_data: Dict[str, Any]) -> int:
        self._ensure_person_bucket(person_id)
        version = len(self._in_memory_persons[person_id]["path_history"]) + 1
        selection_data["version"] = version
        self._in_memory_persons[person_id]["path_history"].append(selection_data)
        self._in_memory_persons[person_id]["active_path"] = selection_data

        return version

    async def get_active_selected_path(self, person_id: str) -> Optional[Dict[str, Any]]:
        return self._in_memory_persons.get(person_id, {}).get("active_path")

    async def get_path_selection_history(self, person_id: str) -> List[Dict[str, Any]]:
        return self._in_memory_persons.get(person_id, {}).get("path_history", [])

    async def save_roadmap(self, person_id: str, roadmap_data: Dict[str, Any]) -> int:
        self._ensure_person_bucket(person_id)
        version = len(self._in_memory_persons[person_id]["roadmaps"]) + 1
        roadmap_data["version"] = version
        self._in_memory_persons[person_id]["roadmaps"].append(roadmap_data)
        self._in_memory_persons[person_id]["active_roadmap"] = roadmap_data

        return version

    async def get_active_roadmap(self, person_id: str) -> Optional[Dict[str, Any]]:
        return self._in_memory_persons.get(person_id, {}).get("active_roadmap")

    async def update_active_roadmap(self, person_id: str, roadmap_data: Dict[str, Any]) -> None:
        self._ensure_person_bucket(person_id)
        self._in_memory_persons[person_id]["active_roadmap"] = roadmap_data

        return

    async def list_person_ids_with_active_roadmaps(self) -> List[str]:
        """
        Lists person_ids that currently have an active roadmap.
        Used by the accountability scheduler to find learners to check.
        Raises loudly on DB failure in production — never silently returns [].
        """
        ids: List[str] = [
            pid for pid, bucket in self._in_memory_persons.items()
            if bucket.get("active_roadmap")
        ]
        return ids

    async def get_roadmap_history(self, person_id: str) -> List[Dict[str, Any]]:
        return self._in_memory_persons.get(person_id, {}).get("roadmaps", [])

    async def save_evidence_submission(self, person_id: str, submission: Dict[str, Any]) -> None:
        self._ensure_person_bucket(person_id)
        self._in_memory_persons[person_id]["submissions"].append(submission)

        return

    async def save_evaluation_result(self, person_id: str, evaluation: Dict[str, Any]) -> None:
        self._ensure_person_bucket(person_id)
        self._in_memory_persons[person_id]["evaluations"].append(evaluation)

        return

    async def get_stage_submissions(self, person_id: str, stage_id: str) -> List[Dict[str, Any]]:
        self._ensure_person_bucket(person_id)
        submissions = [s for s in self._in_memory_persons[person_id]["submissions"] if s.get("stage_id") == stage_id]
        return submissions

    # --- Personal Agent Model & Learning Events ---

    async def save_learning_event(self, person_id: str, event: Dict[str, Any]) -> None:
        self._ensure_person_bucket(person_id)
        self._in_memory_persons[person_id]["learning_events"].append(event)

        return

    async def get_learning_events(self, person_id: str) -> List[Dict[str, Any]]:
        self._ensure_person_bucket(person_id)
        return self._in_memory_persons[person_id]["learning_events"]

    async def save_personal_agent_model(self, person_id: str, model_data: Dict[str, Any]) -> int:
        self._ensure_person_bucket(person_id)
        version = len(self._in_memory_persons[person_id]["personal_agent_models"]) + 1
        model_data["version"] = version
        self._in_memory_persons[person_id]["personal_agent_models"].append(model_data)
        self._in_memory_persons[person_id]["active_personal_agent_model"] = model_data

        return version

    async def get_personal_agent_model(self, person_id: str) -> Optional[Dict[str, Any]]:
        self._ensure_person_bucket(person_id)
        return self._in_memory_persons[person_id].get("active_personal_agent_model")

    async def save_career_profile(self, person_id: str, profile_data: Dict[str, Any]) -> None:
        self._ensure_person_bucket(person_id)
        self._in_memory_persons[person_id]["career_profile"] = profile_data

        return

    async def get_career_profile(self, person_id: str) -> Optional[Dict[str, Any]]:
        self._ensure_person_bucket(person_id)
        return self._in_memory_persons[person_id].get("career_profile")

    async def get_profile(self, person_id: str) -> Optional[Dict[str, Any]]:
        return await self.get_career_profile(person_id)


    async def save_profile(self, person_id: str, profile_data: Dict[str, Any]) -> None:
        await self.save_career_profile(person_id, profile_data)

    # --- Career Goal / Target Outcome ---

    async def save_career_goal(self, person_id: str, goal_data: Dict[str, Any]) -> None:
        self._ensure_person_bucket(person_id)
        self._in_memory_persons[person_id]["career_goal"] = goal_data

        return

    async def get_career_goal(self, person_id: str) -> Optional[Dict[str, Any]]:
        self._ensure_person_bucket(person_id)
        return self._in_memory_persons[person_id].get("career_goal")

    async def save_goal(self, person_id: str, goal_data: Dict[str, Any]) -> None:
        await self.save_career_goal(person_id, goal_data)


    async def get_goal(self, person_id: str) -> Optional[Dict[str, Any]]:
        return await self.get_career_goal(person_id)

    # --- Readiness Reports & Transition Records ---

    async def save_readiness_report(self, person_id: str, report_data: Dict[str, Any]) -> None:
        self._ensure_person_bucket(person_id)
        self._in_memory_persons[person_id]["readiness_reports"].append(report_data)
        self._in_memory_persons[person_id]["active_readiness_report"] = report_data

        return

    async def get_readiness_report(self, person_id: str) -> Optional[Dict[str, Any]]:
        self._ensure_person_bucket(person_id)
        return self._in_memory_persons[person_id].get("active_readiness_report")

    async def get_readiness_history(self, person_id: str) -> List[Dict[str, Any]]:
        self._ensure_person_bucket(person_id)
        return self._in_memory_persons[person_id]["readiness_reports"]

    # --- Career Checkpoints ---

    async def save_career_checkpoint(self, person_id: str, checkpoint_data: Dict[str, Any]) -> None:
        self._ensure_person_bucket(person_id)
        self._in_memory_persons[person_id]["career_checkpoints"].append(checkpoint_data)

        return

    async def get_career_checkpoints(self, person_id: str) -> List[Dict[str, Any]]:
        self._ensure_person_bucket(person_id)
        return self._in_memory_persons[person_id]["career_checkpoints"]

    async def save_tailored_resume(self, person_id: str, resume_data: Dict[str, Any]) -> None:
        self._ensure_person_bucket(person_id)
        self._in_memory_persons[person_id]["tailored_resumes"].append(resume_data)

        return

    async def get_tailored_resumes(self, person_id: str) -> List[Dict[str, Any]]:
        self._ensure_person_bucket(person_id)
        return self._in_memory_persons[person_id]["tailored_resumes"]

    async def resolve_proposed_adaptation(self, person_id: str, adaptation_id: str, action: str) -> bool:
        return await self.update_adaptation_status(person_id, adaptation_id, action)

    # --- Micro-Adaptations ---

    async def save_micro_adaptation(self, person_id: str, micro_data: Dict[str, Any]) -> None:
        self._ensure_person_bucket(person_id)
        self._in_memory_persons[person_id]["micro_adaptations"].append(micro_data)

        return

    async def get_active_micro_adaptations(self, person_id: str) -> List[Dict[str, Any]]:
        self._ensure_person_bucket(person_id)
        return [m for m in self._in_memory_persons[person_id]["micro_adaptations"] if m.get("active", True)]

    async def save_proposed_adaptation(self, person_id: str, adaptation_data: Dict[str, Any]) -> None:
        self._ensure_person_bucket(person_id)
        self._in_memory_persons[person_id]["proposed_adaptations"].append(adaptation_data)

        return

    async def get_proposed_adaptation(self, person_id: str, adaptation_id: str) -> Optional[Dict[str, Any]]:
        self._ensure_person_bucket(person_id)
        for ad in self._in_memory_persons[person_id]["proposed_adaptations"]:
            if ad.get("adaptation_id") == adaptation_id:
                return ad

        return None

    async def get_pending_adaptations(self, person_id: str) -> List[Dict[str, Any]]:
        self._ensure_person_bucket(person_id)
        in_mem = [
            ad for ad in self._in_memory_persons[person_id]["proposed_adaptations"]
            if ad.get("status") in ["PENDING_APPROVAL", "REVIEW_REQUIRED"]
        ]
        return in_mem

    async def update_adaptation_status(self, person_id: str, adaptation_id: str, status: str) -> bool:
        self._ensure_person_bucket(person_id)
        found = False
        for ad in self._in_memory_persons[person_id]["proposed_adaptations"]:
            if ad.get("adaptation_id") == adaptation_id:
                ad["status"] = status
                ad["resolved_at"] = datetime.now(timezone.utc).isoformat()
                found = True

        return found

    async def save_adaptation_audit(self, person_id: str, audit_data: Dict[str, Any]) -> None:
        self._ensure_person_bucket(person_id)
        self._in_memory_persons[person_id]["adaptation_audits"].append(audit_data)

        return

    async def get_adaptation_audits(self, person_id: str) -> List[Dict[str, Any]]:
        self._ensure_person_bucket(person_id)
        return sorted(self._in_memory_persons[person_id]["adaptation_audits"], key=lambda x: x.get("timestamp", ""), reverse=True)

    async def get_all_roadmap_versions(self, person_id: str) -> List[Dict[str, Any]]:
        self._ensure_person_bucket(person_id)
        return self._in_memory_persons[person_id]["roadmaps"]


    async def get_roadmap_version_by_number(self, person_id: str, version_num: int) -> Optional[Dict[str, Any]]:
        self._ensure_person_bucket(person_id)
        for r in self._in_memory_persons[person_id]["roadmaps"]:
            if r.get("version") == version_num:
                return r
        return None

    # --- Canonical Evidence & Mastery Engine ---

    async def save_canonical_evidence(self, person_id: str, evidence_data: Dict[str, Any]) -> None:
        self._ensure_person_bucket(person_id)
        self._in_memory_persons[person_id]["canonical_evidence"].append(evidence_data)

        return

    async def get_canonical_evidence(self, person_id: str, evidence_id: str) -> Optional[Dict[str, Any]]:
        self._ensure_person_bucket(person_id)
        for ev in self._in_memory_persons[person_id]["canonical_evidence"]:
            if ev.get("evidence_id") == evidence_id:
                return ev
        return None

    async def get_all_person_evidence(self, person_id: str) -> List[Dict[str, Any]]:
        self._ensure_person_bucket(person_id)
        return self._in_memory_persons[person_id]["canonical_evidence"]

    async def save_evaluation_attempt(self, person_id: str, attempt_data: Dict[str, Any]) -> None:
        self._ensure_person_bucket(person_id)
        self._in_memory_persons[person_id]["evaluation_attempts"].append(attempt_data)

        return

    async def get_evaluation_attempts(self, person_id: str, stage_id: Optional[str] = None) -> List[Dict[str, Any]]:
        self._ensure_person_bucket(person_id)
        all_att = self._in_memory_persons[person_id]["evaluation_attempts"]
        if stage_id:
            all_att = [a for a in all_att if a.get("stage_id") == stage_id]
        return sorted(all_att, key=lambda x: x.get("evaluated_at", ""), reverse=True)


    async def save_evidence_dispute(self, person_id: str, dispute_data: Dict[str, Any]) -> None:
        self._ensure_person_bucket(person_id)
        self._in_memory_persons[person_id]["evidence_disputes"].append(dispute_data)

        return

    async def get_evidence_disputes(self, person_id: str) -> List[Dict[str, Any]]:
        self._ensure_person_bucket(person_id)
        return self._in_memory_persons[person_id]["evidence_disputes"]


    async def update_evidence_dispute(
        self,
        person_id: str,
        dispute_id: str,
        status: str,
        resolution_note: Optional[str] = None
    ) -> bool:
        self._ensure_person_bucket(person_id)
        for d in self._in_memory_persons[person_id]["evidence_disputes"]:
            if d.get("dispute_id") == dispute_id:
                d["status"] = status
                d["resolution_note"] = resolution_note
                d["resolved_at"] = datetime.now(timezone.utc).isoformat()
                return True
        return False


    async def save_skill_mastery_profile(self, person_id: str, skill_name: str, profile_data: Dict[str, Any]) -> None:
        self._ensure_person_bucket(person_id)
        self._in_memory_persons[person_id]["skill_mastery_profiles"][skill_name] = profile_data


    async def get_skill_mastery_profiles(self, person_id: str) -> Dict[str, Dict[str, Any]]:
        self._ensure_person_bucket(person_id)
        return self._in_memory_persons[person_id]["skill_mastery_profiles"]

    # --- Personal Context Graph & Decision Intelligence ---

    async def save_decision_record(self, person_id: str, decision_data: Dict[str, Any]) -> None:
        self._ensure_person_bucket(person_id)
        self._in_memory_persons[person_id]["decision_records"].append(decision_data)

        return

    async def get_decision_records(self, person_id: str) -> List[Dict[str, Any]]:
        self._ensure_person_bucket(person_id)
        return sorted(self._in_memory_persons[person_id]["decision_records"], key=lambda x: x.get("timestamp", ""), reverse=True)

    async def get_decision_record_by_id(self, person_id: str, decision_id: str) -> Optional[Dict[str, Any]]:
        self._ensure_person_bucket(person_id)
        for dec in self._in_memory_persons[person_id]["decision_records"]:
            if dec.get("decision_id") == decision_id:
                return dec
        return None


    async def update_decision_outcome(
        self,
        person_id: str,
        decision_id: str,
        outcome_state: str,
        outcome_note: Optional[str] = None
    ) -> bool:
        self._ensure_person_bucket(person_id)
        for dec in self._in_memory_persons[person_id]["decision_records"]:
            if dec.get("decision_id") == decision_id:
                dec["outcome_state"] = outcome_state
                dec["outcome_note"] = outcome_note
                return True
        return False


    async def save_context_conflict(self, person_id: str, conflict_data: Dict[str, Any]) -> None:
        self._ensure_person_bucket(person_id)
        self._in_memory_persons[person_id]["context_conflicts"].append(conflict_data)


    async def get_context_conflicts(self, person_id: str) -> List[Dict[str, Any]]:
        self._ensure_person_bucket(person_id)
        return self._in_memory_persons[person_id]["context_conflicts"]

    # --- Proactive Events & Interventions ---

    async def save_event_record(self, person_id: str, event_data: Dict[str, Any]) -> None:
        self._ensure_person_bucket(person_id)
        self._in_memory_persons[person_id]["event_records"].append(event_data)

        return

    async def get_event_records(self, person_id: str, event_type: Optional[str] = None) -> List[Dict[str, Any]]:
        self._ensure_person_bucket(person_id)
        evts = self._in_memory_persons[person_id]["event_records"]
        if event_type:
            evts = [e for e in evts if e.get("event_type") == event_type]
        return sorted(evts, key=lambda x: x.get("occurred_at", ""), reverse=True)


    async def save_intervention(self, person_id: str, intervention_data: Dict[str, Any]) -> None:
        self._ensure_person_bucket(person_id)
        self._in_memory_persons[person_id]["interventions"].append(intervention_data)

        return

    async def get_interventions(self, person_id: str, status: Optional[str] = None) -> List[Dict[str, Any]]:
        self._ensure_person_bucket(person_id)
        intvs = self._in_memory_persons[person_id]["interventions"]
        if status:
            intvs = [i for i in intvs if i.get("status") == status]
        return sorted(intvs, key=lambda x: x.get("created_at", ""), reverse=True)


    async def get_intervention_by_id(self, person_id: str, intervention_id: str) -> Optional[Dict[str, Any]]:
        self._ensure_person_bucket(person_id)
        for i in self._in_memory_persons[person_id]["interventions"]:
            if i.get("intervention_id") == intervention_id:
                return i
        return None


    async def update_intervention_status(self, person_id: str, intervention_id: str, status: str) -> bool:
        self._ensure_person_bucket(person_id)
        for i in self._in_memory_persons[person_id]["interventions"]:
            if i.get("intervention_id") == intervention_id:
                i["status"] = status
                return True
        return False


    async def save_notification_preferences(self, person_id: str, prefs_data: Dict[str, Any]) -> None:
        self._ensure_person_bucket(person_id)
        self._in_memory_persons[person_id]["notification_preferences"] = prefs_data


    async def get_notification_preferences(self, person_id: str) -> Optional[Dict[str, Any]]:
        self._ensure_person_bucket(person_id)
        return self._in_memory_persons[person_id].get("notification_preferences")

    # --- Trust Layer & Recommendations ---

    async def save_structured_recommendation(self, person_id: str, rec_data: Dict[str, Any]) -> None:
        self._ensure_person_bucket(person_id)
        self._in_memory_persons[person_id]["structured_recommendations"].append(rec_data)

        return

    async def get_structured_recommendations(self, person_id: str, status: Optional[str] = None) -> List[Dict[str, Any]]:
        self._ensure_person_bucket(person_id)
        recs = self._in_memory_persons[person_id]["structured_recommendations"]
        if status:
            recs = [r for r in recs if r.get("status") == status]
        return sorted(recs, key=lambda x: x.get("created_at", ""), reverse=True)


    async def get_structured_recommendation_by_id(self, person_id: str, rec_id: str) -> Optional[Dict[str, Any]]:
        self._ensure_person_bucket(person_id)
        for r in self._in_memory_persons[person_id]["structured_recommendations"]:
            if r.get("recommendation_id") == rec_id:
                return r
        return None


    async def update_recommendation_status(self, person_id: str, rec_id: str, status: str) -> bool:
        self._ensure_person_bucket(person_id)
        for r in self._in_memory_persons[person_id]["structured_recommendations"]:
            if r.get("recommendation_id") == rec_id:
                r["status"] = status
                return True
        return False


    async def save_recommendation_explanation(self, person_id: str, rec_id: str, exp_data: Dict[str, Any]) -> None:
        self._ensure_person_bucket(person_id)
        self._in_memory_persons[person_id]["recommendation_explanations"][rec_id] = exp_data


    async def get_recommendation_explanation(self, person_id: str, rec_id: str) -> Optional[Dict[str, Any]]:
        self._ensure_person_bucket(person_id)
        return self._in_memory_persons[person_id]["recommendation_explanations"].get(rec_id)


    async def save_recommendation_feedback(self, person_id: str, feedback_data: Dict[str, Any]) -> None:
        self._ensure_person_bucket(person_id)
        self._in_memory_persons[person_id]["recommendation_feedback"].append(feedback_data)


    async def get_recommendation_feedback(self, person_id: str, rec_id: Optional[str] = None) -> List[Dict[str, Any]]:
        self._ensure_person_bucket(person_id)
        fb = self._in_memory_persons[person_id]["recommendation_feedback"]
        if rec_id:
            fb = [f for f in fb if f.get("recommendation_id") == rec_id]
        return fb

    # --- Longitudinal Learner Model ---

    async def save_progress_insight(self, person_id: str, insight_data: Dict[str, Any]) -> None:
        self._ensure_person_bucket(person_id)
        self._in_memory_persons[person_id]["progress_insights"].append(insight_data)

        return

    async def get_progress_insights(self, person_id: str, status: Optional[str] = None) -> List[Dict[str, Any]]:
        self._ensure_person_bucket(person_id)
        insights = self._in_memory_persons[person_id]["progress_insights"]
        if status:
            insights = [i for i in insights if i.get("status") == status]
        return sorted(insights, key=lambda x: x.get("created_at", ""), reverse=True)


    async def get_progress_insight_by_id(self, person_id: str, insight_id: str) -> Optional[Dict[str, Any]]:
        self._ensure_person_bucket(person_id)
        for i in self._in_memory_persons[person_id]["progress_insights"]:
            if i.get("insight_id") == insight_id:
                return i
        return None


    async def update_progress_insight_status(
        self,
        person_id: str,
        insight_id: str,
        status: str,
        dispute_reason: Optional[str] = None
    ) -> bool:
        self._ensure_person_bucket(person_id)
        for i in self._in_memory_persons[person_id]["progress_insights"]:
            if i.get("insight_id") == insight_id:
                i["status"] = status
                if dispute_reason:
                    i["dispute_reason"] = dispute_reason
                return True
        return False


    async def save_learning_strategy_profile(self, person_id: str, profile_data: Dict[str, Any]) -> None:
        self._ensure_person_bucket(person_id)
        existing_idx = next(
            (idx for idx, p in enumerate(self._in_memory_persons[person_id]["learning_strategy_profiles"])
             if p.get("strategy_dimension") == profile_data.get("strategy_dimension")),
            -1
        )
        if existing_idx >= 0:
            self._in_memory_persons[person_id]["learning_strategy_profiles"][existing_idx] = profile_data
        else:
            self._in_memory_persons[person_id]["learning_strategy_profiles"].append(profile_data)


    async def get_learning_strategy_profiles(self, person_id: str) -> List[Dict[str, Any]]:
        self._ensure_person_bucket(person_id)
        return self._in_memory_persons[person_id]["learning_strategy_profiles"]


    async def save_recurring_misconception(self, person_id: str, misc_data: Dict[str, Any]) -> None:
        self._ensure_person_bucket(person_id)
        existing_idx = next(
            (idx for idx, m in enumerate(self._in_memory_persons[person_id]["recurring_misconceptions"])
             if m.get("concept_area") == misc_data.get("concept_area")),
            -1
        )
        if existing_idx >= 0:
            self._in_memory_persons[person_id]["recurring_misconceptions"][existing_idx] = misc_data
        else:
            self._in_memory_persons[person_id]["recurring_misconceptions"].append(misc_data)


    async def get_recurring_misconceptions(self, person_id: str, status: Optional[str] = None) -> List[Dict[str, Any]]:
        self._ensure_person_bucket(person_id)
        miscs = self._in_memory_persons[person_id]["recurring_misconceptions"]
        if status:
            miscs = [m for m in miscs if m.get("status") == status]
        return miscs


    async def save_turning_point(self, person_id: str, tp_data: Dict[str, Any]) -> None:
        self._ensure_person_bucket(person_id)
        self._in_memory_persons[person_id]["turning_points"].append(tp_data)


    async def get_turning_points(self, person_id: str) -> List[Dict[str, Any]]:
        self._ensure_person_bucket(person_id)
        return sorted(self._in_memory_persons[person_id]["turning_points"], key=lambda x: x.get("timestamp", ""), reverse=True)

    # --- Prompt 16: Canonical Artifacts & Verified Portfolio Layer ---

    async def save_canonical_artifact(self, person_id: str, artifact_data: Dict[str, Any]) -> None:
        self._ensure_person_bucket(person_id)
        art_id = artifact_data.get("artifact_id")
        existing_idx = next(
            (idx for idx, a in enumerate(self._in_memory_persons[person_id]["canonical_artifacts"])
             if a.get("artifact_id") == art_id),
            -1
        )
        if existing_idx >= 0:
            self._in_memory_persons[person_id]["canonical_artifacts"][existing_idx] = artifact_data
        else:
            self._in_memory_persons[person_id]["canonical_artifacts"].append(artifact_data)

        return

    async def get_canonical_artifact(self, person_id: str, artifact_id: str) -> Optional[Dict[str, Any]]:
        self._ensure_person_bucket(person_id)
        for a in self._in_memory_persons[person_id]["canonical_artifacts"]:
            if a.get("artifact_id") == artifact_id:
                return a
        return None

    async def get_person_artifacts(self, person_id: str, artifact_type: Optional[str] = None) -> List[Dict[str, Any]]:
        self._ensure_person_bucket(person_id)
        arts = self._in_memory_persons[person_id]["canonical_artifacts"]
        if artifact_type:
            arts = [a for a in arts if a.get("type") == artifact_type]
        return arts


    async def save_defense_session(self, person_id: str, session_data: Dict[str, Any]) -> None:
        self._ensure_person_bucket(person_id)
        sess_id = session_data.get("session_id")
        existing_idx = next(
            (idx for idx, s in enumerate(self._in_memory_persons[person_id]["artifact_defense_sessions"])
             if s.get("session_id") == sess_id),
            -1
        )
        if existing_idx >= 0:
            self._in_memory_persons[person_id]["artifact_defense_sessions"][existing_idx] = session_data
        else:
            self._in_memory_persons[person_id]["artifact_defense_sessions"].append(session_data)


    async def get_defense_session(self, person_id: str, session_id: str) -> Optional[Dict[str, Any]]:
        self._ensure_person_bucket(person_id)
        for s in self._in_memory_persons[person_id]["artifact_defense_sessions"]:
            if s.get("session_id") == session_id:
                return s
        return None


    async def save_claim_validation(self, person_id: str, claim_data: Dict[str, Any]) -> None:
        self._ensure_person_bucket(person_id)
        self._in_memory_persons[person_id]["claims_validated"].append(claim_data)


    async def get_claims_validated(self, person_id: str) -> List[Dict[str, Any]]:
        self._ensure_person_bucket(person_id)
        return self._in_memory_persons[person_id]["claims_validated"]


    async def save_step_verification(self, person_id: str, step_data: Dict[str, Any]) -> None:
        self._ensure_person_bucket(person_id)
        self._in_memory_persons[person_id]["step_verifications"].append(step_data)


    async def get_step_verifications(self, person_id: str, stage_id: Optional[str] = None) -> List[Dict[str, Any]]:
        self._ensure_person_bucket(person_id)
        steps = self._in_memory_persons[person_id]["step_verifications"]
        if stage_id:
            steps = [s for s in steps if s.get("stage_id") == stage_id]
        return steps


    async def record_learning_strategy_outcome(
        self,
        person_id: str,
        strategy_type: str,
        outcome: str,
        context: str
    ) -> None:
        self._ensure_person_bucket(person_id)
        profiles = self._in_memory_persons[person_id]["learning_strategy_profiles"]
        existing = next((p for p in profiles if p.get("strategy_dimension") == strategy_type), None)
        if existing:
            if outcome == "SUCCESS":
                existing["supporting_events_count"] = existing.get("supporting_events_count", 0) + 1
                existing["confidence_score"] = min(100.0, existing.get("confidence_score", 70.0) + 5.0)
                existing["status"] = "SUPPORTED"
            else:
                existing["contradicting_events_count"] = existing.get("contradicting_events_count", 0) + 1
                existing["confidence_score"] = max(20.0, existing.get("confidence_score", 70.0) - 10.0)
            existing["last_evaluated_at"] = datetime.now(timezone.utc).isoformat()
        else:
            profiles.append({
                "strategy_dimension": strategy_type,
                "status": "SUPPORTED" if outcome == "SUCCESS" else "EMERGING",
                "confidence_score": 85.0 if outcome == "SUCCESS" else 60.0,
                "supporting_events_count": 1 if outcome == "SUCCESS" else 0,
                "contradicting_events_count": 0 if outcome == "SUCCESS" else 1,
                "effective_context": context,
                "last_evaluated_at": datetime.now(timezone.utc).isoformat()
            })

    # --- Prompt 17: Execution Engine, Action Tracking & Accountability ---

    async def save_action(self, person_id: str, action_data: Dict[str, Any]) -> None:
        self._ensure_person_bucket(person_id)
        act_id = action_data.get("action_id")
        existing_idx = next(
            (idx for idx, a in enumerate(self._in_memory_persons[person_id]["canonical_actions"])
             if a.get("action_id") == act_id),
            -1
        )
        if existing_idx >= 0:
            self._in_memory_persons[person_id]["canonical_actions"][existing_idx] = action_data
        else:
            self._in_memory_persons[person_id]["canonical_actions"].append(action_data)

        return

    async def get_action(self, person_id: str, action_id: str) -> Optional[Dict[str, Any]]:
        self._ensure_person_bucket(person_id)
        for a in self._in_memory_persons[person_id]["canonical_actions"]:
            if a.get("action_id") == action_id:
                return a
        return None

    async def get_person_actions(
        self,
        person_id: str,
        stage_id: Optional[str] = None,
        status: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        self._ensure_person_bucket(person_id)
        actions = self._in_memory_persons[person_id]["canonical_actions"]
        if stage_id:
            actions = [a for a in actions if a.get("stage_id") == stage_id]
        if status:
            actions = [a for a in actions if a.get("status") == status]
        return actions


    async def save_opportunity_application(self, person_id: str, app_data: Dict[str, Any]) -> None:
        self._ensure_person_bucket(person_id)
        app_id = app_data.get("application_id")
        existing_idx = next(
            (idx for idx, a in enumerate(self._in_memory_persons[person_id]["opportunity_applications"])
             if a.get("application_id") == app_id),
            -1
        )
        if existing_idx >= 0:
            self._in_memory_persons[person_id]["opportunity_applications"][existing_idx] = app_data
        else:
            self._in_memory_persons[person_id]["opportunity_applications"].append(app_data)


    async def get_opportunity_applications(self, person_id: str) -> List[Dict[str, Any]]:
        self._ensure_person_bucket(person_id)
        return self._in_memory_persons[person_id]["opportunity_applications"]


    async def set_execution_pause_state(self, person_id: str, pause_data: Dict[str, Any]) -> None:
        self._ensure_person_bucket(person_id)
        self._in_memory_persons[person_id]["execution_pause_state"] = pause_data


    async def get_execution_pause_state(self, person_id: str) -> Optional[Dict[str, Any]]:
        self._ensure_person_bucket(person_id)
        return self._in_memory_persons[person_id]["execution_pause_state"]


    async def save_orchestration_trace(self, person_id: str, trace_data: Dict[str, Any]) -> None:
        self._ensure_person_bucket(person_id)
        self._in_memory_persons[person_id]["orchestration_traces"].append(trace_data)


    async def get_orchestration_traces(self, person_id: str) -> List[Dict[str, Any]]:
        self._ensure_person_bucket(person_id)
        return self._in_memory_persons[person_id]["orchestration_traces"]


    async def get_orchestration_trace(self, person_id: str, workflow_id: str) -> Optional[Dict[str, Any]]:
        self._ensure_person_bucket(person_id)
        for t in self._in_memory_persons[person_id]["orchestration_traces"]:
            if t.get("workflow_id") == workflow_id:
                return t
        return None


    async def save_action_proposal(self, person_id: str, proposal_data: Dict[str, Any]) -> None:
        self._ensure_person_bucket(person_id)
        prop_id = proposal_data.get("proposal_id")
        existing_idx = next(
            (idx for idx, p in enumerate(self._in_memory_persons[person_id]["action_proposals"])
             if p.get("proposal_id") == prop_id),
            -1
        )
        if existing_idx >= 0:
            self._in_memory_persons[person_id]["action_proposals"][existing_idx] = proposal_data
        else:
            self._in_memory_persons[person_id]["action_proposals"].append(proposal_data)


    async def get_action_proposals(self, person_id: str, status: Optional[str] = None) -> List[Dict[str, Any]]:
        self._ensure_person_bucket(person_id)
        props = self._in_memory_persons[person_id]["action_proposals"]
        if status:
            props = [p for p in props if p.get("status") == status]
        return props


    async def get_action_proposal(self, person_id: str, proposal_id: str) -> Optional[Dict[str, Any]]:
        self._ensure_person_bucket(person_id)
        for p in self._in_memory_persons[person_id]["action_proposals"]:
            if p.get("proposal_id") == proposal_id:
                return p
        return None


    async def update_action_proposal_status(self, person_id: str, proposal_id: str, status: str) -> Optional[Dict[str, Any]]:
        self._ensure_person_bucket(person_id)
        for p in self._in_memory_persons[person_id]["action_proposals"]:
            if p.get("proposal_id") == proposal_id:
                p["status"] = status
                return p
        return None

    # --- Person Record (Immediate Persistence upon Name Collection) ---

    async def save_person_record(self, person_id: str, record_data: Dict[str, Any]) -> None:
        self._ensure_person_bucket(person_id)
        self._in_memory_persons[person_id]["person_record"] = record_data
        return

    async def get_person_record(self, person_id: str) -> Optional[Dict[str, Any]]:
        self._ensure_person_bucket(person_id)
        return self._in_memory_persons[person_id].get("person_record")

    async def save_journey_state(self, person_id: str, state_data: Dict[str, Any]) -> None:
        self._ensure_person_bucket(person_id)
        self._in_memory_persons[person_id]["journey_state"] = state_data
        return

    async def get_journey_state(self, person_id: str) -> Optional[Dict[str, Any]]:
        self._ensure_person_bucket(person_id)
        return self._in_memory_persons[person_id].get("journey_state")

    async def save_assessment_blueprint(self, person_id: str, blueprint_data: Dict[str, Any]) -> None:
        self._ensure_person_bucket(person_id)
        self._in_memory_persons[person_id]["assessment_blueprint"] = blueprint_data
        return

    async def get_assessment_blueprint(self, person_id: str) -> Optional[Dict[str, Any]]:
        self._ensure_person_bucket(person_id)
        return self._in_memory_persons[person_id].get("assessment_blueprint")
