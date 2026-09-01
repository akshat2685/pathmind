from google.cloud import firestore
from typing import Optional, Dict, Any, List
import json
from backend.core.config import settings

class FirestoreStore:
    _in_memory_cache: Dict[str, Any] = {}
    _in_memory_persons: Dict[str, Dict[str, Any]] = {}
    _in_memory_shared_patterns: List[Dict[str, Any]] = []

    def __init__(self):
        # Initializes using default GOOGLE_APPLICATION_CREDENTIALS if available
        try:
            self.db = firestore.AsyncClient(project=settings.FIRESTORE_PROJECT_ID)
            self._available = True
        except Exception:
            self.db = None
            self._available = False

    async def check_health(self) -> str:
        if not self._available:
            return "NOT_CONFIGURED"
        try:
            collections = self.db.collections()
            async for _ in collections:
                break
            return "CONNECTED"
        except Exception:
            return "SOURCE_UNAVAILABLE"

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
                "career_goal": None,
                "readiness_reports": [],
                "active_readiness_report": None
            }

    # --- Knowledge Cache ---
    async def get_cached_knowledge(self, key: str) -> Optional[Dict[str, Any]]:
        if not self._available:
            return self._in_memory_cache.get(key)
            
        try:
            doc_ref = self.db.collection('knowledge_cache').document(key)
            doc = await doc_ref.get()
            if doc.exists:
                return doc.to_dict()
        except Exception:
            return self._in_memory_cache.get(key)
        return self._in_memory_cache.get(key)

    async def set_cached_knowledge(self, key: str, data: Dict[str, Any]) -> None:
        self._in_memory_cache[key] = data
        if not self._available:
            return
            
        try:
            doc_ref = self.db.collection('knowledge_cache').document(key)
            await doc_ref.set(data)
        except Exception:
            pass

    # --- Assessment Submissions ---
    async def save_assessment_result(self, person_id: str, result_data: Dict[str, Any]) -> None:
        self._ensure_person_bucket(person_id)
        self._in_memory_persons[person_id]["assessments"].append(result_data)

        if not self._available:
            return
        try:
            doc_ref = self.db.collection('persons').document(person_id).collection('assessments').document()
            await doc_ref.set(result_data)
        except Exception:
            pass

    async def get_assessment_results(self, person_id: str) -> List[Dict[str, Any]]:
        if not self._available:
            return self._in_memory_persons.get(person_id, {}).get("assessments", [])
        try:
            docs = self.db.collection('persons').document(person_id).collection('assessments').stream()
            results = []
            async for doc in docs:
                results.append(doc.to_dict())
            if results:
                return results
            return self._in_memory_persons.get(person_id, {}).get("assessments", [])
        except Exception:
            return self._in_memory_persons.get(person_id, {}).get("assessments", [])

    # --- Assessment Drafts (Pause / Resume) ---
    async def save_assessment_draft(self, person_id: str, assessment_id: str, draft_data: Dict[str, Any]) -> None:
        self._ensure_person_bucket(person_id)
        self._in_memory_persons[person_id]["drafts"][assessment_id] = draft_data

        if not self._available:
            return
        try:
            doc_ref = self.db.collection('persons').document(person_id).collection('drafts').document(assessment_id)
            await doc_ref.set(draft_data)
        except Exception:
            pass

    async def get_assessment_draft(self, person_id: str, assessment_id: str) -> Optional[Dict[str, Any]]:
        if not self._available:
            return self._in_memory_persons.get(person_id, {}).get("drafts", {}).get(assessment_id)
        try:
            doc_ref = self.db.collection('persons').document(person_id).collection('drafts').document(assessment_id)
            doc = await doc_ref.get()
            if doc.exists:
                return doc.to_dict()
            return self._in_memory_persons.get(person_id, {}).get("drafts", {}).get(assessment_id)
        except Exception:
            return self._in_memory_persons.get(person_id, {}).get("drafts", {}).get(assessment_id)

    # --- Counseling Profile Persistence ---
    async def save_counseling_profile(self, person_id: str, profile_data: Dict[str, Any]) -> None:
        self._ensure_person_bucket(person_id)
        self._in_memory_persons[person_id]["profile"] = profile_data

        if not self._available:
            return
        try:
            doc_ref = self.db.collection('persons').document(person_id).collection('counseling').document('active_profile')
            await doc_ref.set(profile_data)
        except Exception:
            pass

    async def get_counseling_profile(self, person_id: str) -> Optional[Dict[str, Any]]:
        if not self._available:
            return self._in_memory_persons.get(person_id, {}).get("profile")
        try:
            doc_ref = self.db.collection('persons').document(person_id).collection('counseling').document('active_profile')
            doc = await doc_ref.get()
            if doc.exists:
                return doc.to_dict()
            return self._in_memory_persons.get(person_id, {}).get("profile")
        except Exception:
            return self._in_memory_persons.get(person_id, {}).get("profile")

    # --- Structured Personal Memory Vault (Prompt 07) ---
    async def save_personal_memory(self, person_id: str, memory_data: Dict[str, Any]) -> None:
        self._ensure_person_bucket(person_id)
        # Check if updating existing memory
        mem_id = memory_data.get("memory_id")
        existing_idx = next((i for i, m in enumerate(self._in_memory_persons[person_id]["structured_memories"]) if m.get("memory_id") == mem_id), -1)
        if existing_idx >= 0:
            self._in_memory_persons[person_id]["structured_memories"][existing_idx] = memory_data
        else:
            self._in_memory_persons[person_id]["structured_memories"].append(memory_data)

        if not self._available:
            return
        try:
            doc_ref = self.db.collection('persons').document(person_id).collection('vault_memories').document(mem_id)
            await doc_ref.set(memory_data)
        except Exception:
            pass

    async def get_personal_memories(
        self,
        person_id: str,
        memory_type: Optional[str] = None,
        topic: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        self._ensure_person_bucket(person_id)
        mems = self._in_memory_persons[person_id]["structured_memories"]

        if self._available:
            try:
                docs = self.db.collection('persons').document(person_id).collection('vault_memories').stream()
                loaded = []
                async for doc in docs:
                    loaded.append(doc.to_dict())
                if loaded:
                    mems = loaded
            except Exception:
                pass

        if memory_type and memory_type != "ALL":
            mems = [m for m in mems if m.get("memory_type") == memory_type]
        if topic:
            mems = [m for m in mems if topic.lower() in m.get("topic", "").lower()]

        return mems

    async def delete_personal_memory(self, person_id: str, memory_id: str) -> bool:
        self._ensure_person_bucket(person_id)
        self._in_memory_persons[person_id]["structured_memories"] = [
            m for m in self._in_memory_persons[person_id]["structured_memories"] if m.get("memory_id") != memory_id
        ]
        if not self._available:
            return True
        try:
            doc_ref = self.db.collection('persons').document(person_id).collection('vault_memories').document(memory_id)
            await doc_ref.delete()
            return True
        except Exception:
            return True

    # --- Shared Generalized Learning Patterns (Prompt 07) ---
    async def save_shared_pattern(self, pattern_data: Dict[str, Any]) -> None:
        pat_id = pattern_data.get("pattern_id")
        existing_idx = next((i for i, p in enumerate(self._in_memory_shared_patterns) if p.get("pattern_id") == pat_id), -1)
        if existing_idx >= 0:
            self._in_memory_shared_patterns[existing_idx] = pattern_data
        else:
            self._in_memory_shared_patterns.append(pattern_data)

        if not self._available:
            return
        try:
            doc_ref = self.db.collection('shared_learning_patterns').document(pat_id)
            await doc_ref.set(pattern_data)
        except Exception:
            pass

    async def get_shared_patterns(self) -> List[Dict[str, Any]]:
        if not self._available:
            return self._in_memory_shared_patterns
        try:
            docs = self.db.collection('shared_learning_patterns').stream()
            results = []
            async for doc in docs:
                results.append(doc.to_dict())
            if results:
                return results
            return self._in_memory_shared_patterns
        except Exception:
            return self._in_memory_shared_patterns

    # --- Career Path Selection & Versioning (Prompt 05) ---
    async def save_selected_path(self, person_id: str, selection_data: Dict[str, Any]) -> int:
        self._ensure_person_bucket(person_id)
        version = len(self._in_memory_persons[person_id]["path_history"]) + 1
        selection_data["version"] = version
        self._in_memory_persons[person_id]["path_history"].append(selection_data)
        self._in_memory_persons[person_id]["active_path"] = selection_data

        if not self._available:
            return version

        try:
            doc_ref = self.db.collection('persons').document(person_id).collection('path_versions').document(f"v{version}")
            await doc_ref.set(selection_data)
            active_ref = self.db.collection('persons').document(person_id).collection('career_path').document('active_path')
            await active_ref.set(selection_data)
            return version
        except Exception:
            return version

    async def get_active_selected_path(self, person_id: str) -> Optional[Dict[str, Any]]:
        if not self._available:
            return self._in_memory_persons.get(person_id, {}).get("active_path")
        try:
            doc_ref = self.db.collection('persons').document(person_id).collection('career_path').document('active_path')
            doc = await doc_ref.get()
            if doc.exists:
                return doc.to_dict()
            return self._in_memory_persons.get(person_id, {}).get("active_path")
        except Exception:
            return self._in_memory_persons.get(person_id, {}).get("active_path")

    async def get_path_selection_history(self, person_id: str) -> List[Dict[str, Any]]:
        if not self._available:
            return self._in_memory_persons.get(person_id, {}).get("path_history", [])
        try:
            docs = self.db.collection('persons').document(person_id).collection('path_versions').stream()
            history = []
            async for doc in docs:
                history.append(doc.to_dict())
            if history:
                return sorted(history, key=lambda x: x.get("version", 1))
            return self._in_memory_persons.get(person_id, {}).get("path_history", [])
        except Exception:
            return self._in_memory_persons.get(person_id, {}).get("path_history", [])

    # --- Roadmap Persistence & Versioning (Prompt 06) ---
    async def save_roadmap(self, person_id: str, roadmap_data: Dict[str, Any]) -> int:
        self._ensure_person_bucket(person_id)
        version = len(self._in_memory_persons[person_id]["roadmaps"]) + 1
        roadmap_data["version"] = version
        self._in_memory_persons[person_id]["roadmaps"].append(roadmap_data)
        self._in_memory_persons[person_id]["active_roadmap"] = roadmap_data

        if not self._available:
            return version

        try:
            doc_ref = self.db.collection('persons').document(person_id).collection('roadmaps').document(f"v{version}")
            await doc_ref.set(roadmap_data)
            active_ref = self.db.collection('persons').document(person_id).collection('roadmap_state').document('active')
            await active_ref.set(roadmap_data)
            return version
        except Exception:
            return version

    async def get_active_roadmap(self, person_id: str) -> Optional[Dict[str, Any]]:
        if not self._available:
            return self._in_memory_persons.get(person_id, {}).get("active_roadmap")
        try:
            doc_ref = self.db.collection('persons').document(person_id).collection('roadmap_state').document('active')
            doc = await doc_ref.get()
            if doc.exists:
                return doc.to_dict()
            return self._in_memory_persons.get(person_id, {}).get("active_roadmap")
        except Exception:
            return self._in_memory_persons.get(person_id, {}).get("active_roadmap")

    async def update_active_roadmap(self, person_id: str, roadmap_data: Dict[str, Any]) -> None:
        self._ensure_person_bucket(person_id)
        self._in_memory_persons[person_id]["active_roadmap"] = roadmap_data

        if not self._available:
            return
        try:
            active_ref = self.db.collection('persons').document(person_id).collection('roadmap_state').document('active')
            await active_ref.set(roadmap_data)
        except Exception:
            pass

    async def get_roadmap_history(self, person_id: str) -> List[Dict[str, Any]]:
        if not self._available:
            return self._in_memory_persons.get(person_id, {}).get("roadmaps", [])
        try:
            docs = self.db.collection('persons').document(person_id).collection('roadmaps').stream()
            history = []
            async for doc in docs:
                history.append(doc.to_dict())
            if history:
                return sorted(history, key=lambda x: x.get("version", 1))
            return self._in_memory_persons.get(person_id, {}).get("roadmaps", [])
        except Exception:
            return self._in_memory_persons.get(person_id, {}).get("roadmaps", [])

    # --- Evidence Submissions & Evaluations (Prompt 06) ---
    async def save_evidence_submission(self, person_id: str, submission: Dict[str, Any]) -> None:
        self._ensure_person_bucket(person_id)
        self._in_memory_persons[person_id]["submissions"].append(submission)

        if not self._available:
            return
        try:
            doc_ref = self.db.collection('persons').document(person_id).collection('evidence_submissions').document(submission.get("submission_id", "sub"))
            await doc_ref.set(submission)
        except Exception:
            pass

    async def save_evaluation_result(self, person_id: str, evaluation: Dict[str, Any]) -> None:
        self._ensure_person_bucket(person_id)
        self._in_memory_persons[person_id]["evaluations"].append(evaluation)

        if not self._available:
            return
        try:
            doc_ref = self.db.collection('persons').document(person_id).collection('evaluations').document(evaluation.get("submission_id", "eval"))
            await doc_ref.set(evaluation)
        except Exception:
            pass

    async def get_stage_submissions(self, person_id: str, stage_id: str) -> List[Dict[str, Any]]:
        self._ensure_person_bucket(person_id)
        submissions = [s for s in self._in_memory_persons[person_id]["submissions"] if s.get("stage_id") == stage_id]
        return submissions

    # --- Personal Agent Model & Learning Events (Prompt 06 Addendum) ---
    async def save_learning_event(self, person_id: str, event: Dict[str, Any]) -> None:
        self._ensure_person_bucket(person_id)
        self._in_memory_persons[person_id]["learning_events"].append(event)

        if not self._available:
            return
        try:
            doc_ref = self.db.collection('persons').document(person_id).collection('learning_events').document(event.get("event_id", "evt"))
            await doc_ref.set(event)
        except Exception:
            pass

    async def get_learning_events(self, person_id: str) -> List[Dict[str, Any]]:
        self._ensure_person_bucket(person_id)
        if not self._available:
            return self._in_memory_persons[person_id]["learning_events"]
        try:
            docs = self.db.collection('persons').document(person_id).collection('learning_events').stream()
            events = []
            async for doc in docs:
                events.append(doc.to_dict())
            if events:
                return sorted(events, key=lambda x: x.get("timestamp", ""))
            return self._in_memory_persons[person_id]["learning_events"]
        except Exception:
            return self._in_memory_persons[person_id]["learning_events"]

    async def save_personal_agent_model(self, person_id: str, model_data: Dict[str, Any]) -> int:
        self._ensure_person_bucket(person_id)
        version = len(self._in_memory_persons[person_id]["personal_agent_models"]) + 1
        model_data["version"] = version
        self._in_memory_persons[person_id]["personal_agent_models"].append(model_data)
        self._in_memory_persons[person_id]["active_personal_agent_model"] = model_data

        if not self._available:
            return version

        try:
            doc_ref = self.db.collection('persons').document(person_id).collection('agent_model_versions').document(f"v{version}")
            await doc_ref.set(model_data)
            active_ref = self.db.collection('persons').document(person_id).collection('agent_model').document('active')
            await active_ref.set(model_data)
            return version
        except Exception:
            return version

    async def get_personal_agent_model(self, person_id: str) -> Optional[Dict[str, Any]]:
        self._ensure_person_bucket(person_id)
        if not self._available:
            return self._in_memory_persons[person_id].get("active_personal_agent_model")
        try:
            doc_ref = self.db.collection('persons').document(person_id).collection('agent_model').document('active')
            doc = await doc_ref.get()
            if doc.exists:
                return doc.to_dict()
            return self._in_memory_persons[person_id].get("active_personal_agent_model")
        except Exception:
            return self._in_memory_persons[person_id].get("active_personal_agent_model")

    # --- Career Goal & Readiness Persistence (Prompt 08) ---
    async def save_career_goal(self, person_id: str, goal_data: Dict[str, Any]) -> None:
        self._ensure_person_bucket(person_id)
        self._in_memory_persons[person_id]["career_goal"] = goal_data

        if not self._available:
            return
        try:
            doc_ref = self.db.collection('persons').document(person_id).collection('career_goals').document('active_goal')
            await doc_ref.set(goal_data)
        except Exception:
            pass

    async def get_career_goal(self, person_id: str) -> Optional[Dict[str, Any]]:
        self._ensure_person_bucket(person_id)
        if not self._available:
            return self._in_memory_persons[person_id].get("career_goal")
        try:
            doc_ref = self.db.collection('persons').document(person_id).collection('career_goals').document('active_goal')
            doc = await doc_ref.get()
            if doc.exists:
                return doc.to_dict()
            return self._in_memory_persons[person_id].get("career_goal")
        except Exception:
            return self._in_memory_persons[person_id].get("career_goal")

    async def save_readiness_report(self, person_id: str, report_data: Dict[str, Any]) -> None:
        self._ensure_person_bucket(person_id)
        self._in_memory_persons[person_id]["readiness_reports"].append(report_data)
        self._in_memory_persons[person_id]["active_readiness_report"] = report_data

        if not self._available:
            return
        try:
            doc_ref = self.db.collection('persons').document(person_id).collection('readiness_reports').document('active_report')
            await doc_ref.set(report_data)
        except Exception:
            pass

    async def get_readiness_report(self, person_id: str) -> Optional[Dict[str, Any]]:
        self._ensure_person_bucket(person_id)
        if not self._available:
            return self._in_memory_persons[person_id].get("active_readiness_report")
        try:
            doc_ref = self.db.collection('persons').document(person_id).collection('readiness_reports').document('active_report')
            doc = await doc_ref.get()
            if doc.exists:
                return doc.to_dict()
            return self._in_memory_persons[person_id].get("active_readiness_report")
        except Exception:
            return self._in_memory_persons[person_id].get("active_readiness_report")

