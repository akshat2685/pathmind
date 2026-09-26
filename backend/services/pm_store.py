"""
PmStore — Supabase-backed persistence for the PATHMIND main product.

Drop-in replacement for FirestoreStore (backend/services/store.py):
identical public method signatures so routes/services need no changes.

HARD RULES (unlike FirestoreStore):
  * No in-memory fallback. Every method hits the real Supabase database.
  * No silent degradation. Any DB error propagates to the caller.
  * Fail fast: missing SUPABASE_URL / SUPABASE_SECRET_KEY, a missing
    `supabase` package, or a client that cannot be built raises
    RuntimeError("PERSISTENCE_UNAVAILABLE: ...") at construction time.

Table layout: one pm_-prefixed table per Firestore collection/bucket
(see backend/migrations/001_pm_core_tables.sql). Uniform row shape:
  id uuid PK, person_id text (Supabase Auth user id; 'global' sentinel for
  cross-learner rows), data jsonb (the original document payload),
  created_at timestamptz.

Natural keys (memory_id, assessment_id, ...) live inside `data` and are
matched in Python after a per-person fetch — the same filtering semantics
the original in-memory buckets used.
"""

from __future__ import annotations

import asyncio
import uuid
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List

from backend.core.config import settings
from backend.services.supabase_adapter import get_supabase_adapter

_GLOBAL_PERSON = "global"  # sentinel person_id for cross-learner rows

_MISSING_CONFIG_MSG = (
    "PERSISTENCE_UNAVAILABLE: SUPABASE_URL and SUPABASE_SECRET_KEY must be set. "
    "PmStore refuses to start without a real database — no in-memory fallback."
)
_NO_PACKAGE_MSG = (
    "PERSISTENCE_UNAVAILABLE: the 'supabase' python package is not installed "
    "(pip install supabase). PmStore refuses to degrade silently."
)
_NO_CLIENT_MSG = (
    "PERSISTENCE_UNAVAILABLE: Supabase client could not be initialized. "
    "Check SUPABASE_URL / SUPABASE_SECRET_KEY."
)
_DB_DOWN_MSG = (
    "PERSISTENCE_UNAVAILABLE: Supabase request failed. Refusing to degrade silently."
)


def _utcnow_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class PmStore:
    _person_locks: Dict[str, asyncio.Lock] = {}

    def get_person_lock(self, person_id: str) -> asyncio.Lock:
        if person_id not in self._person_locks:
            self._person_locks[person_id] = asyncio.Lock()
        return self._person_locks[person_id]

    def __init__(self):
        url = settings.SUPABASE_URL
        key = settings.SUPABASE_SECRET_KEY
        if not url or not key:
            raise RuntimeError(_MISSING_CONFIG_MSG)
        try:
            import supabase  # noqa: F401  (imported for its side effect / availability check)
        except ImportError as e:
            raise RuntimeError(_NO_PACKAGE_MSG) from e
        adapter = get_supabase_adapter()
        client = adapter.client
        if client is None:
            raise RuntimeError(_NO_CLIENT_MSG)
        self._client = client

    def _db(self):
        if self._client is None:
            raise RuntimeError(_NO_CLIENT_MSG)
        return self._client

    async def check_health(self) -> str:
        """Real server-side check. Returns 'CONNECTED' or raises loudly."""
        try:
            await asyncio.to_thread(
                lambda: self._db().table("pm_persons").select("id").limit(1).execute()
            )
        except Exception as e:
            raise RuntimeError(f"{_DB_DOWN_MSG} ({type(e).__name__})") from e
        return "CONNECTED"

    # ------------------------------------------------------------------
    # Low-level helpers (all raise on DB failure — never swallow)
    # ------------------------------------------------------------------
    async def _rows(self, table: str, person_id: str) -> List[Dict[str, Any]]:
        res = await asyncio.to_thread(
            lambda: self._db().table(table)
            .select("id,data,created_at")
            .eq("person_id", person_id)
            .execute()
        )
        return res.data or []

    @staticmethod
    def _payloads(rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        return [r["data"] for r in rows]

    async def _insert(self, table: str, person_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        payload = {"person_id": person_id, "data": dict(data)}
        res = await asyncio.to_thread(
            lambda: self._db().table(table).insert(payload).execute()
        )
        rows = res.data or []
        return rows[0] if rows else payload

    async def _get_singleton(self, table: str, person_id: str) -> Optional[Dict[str, Any]]:
        rows = await self._rows(table, person_id)
        return rows[0]["data"] if rows else None

    async def _upsert_singleton(
        self, table: str, person_id: str, data: Dict[str, Any], merge: bool = False
    ) -> None:
        body = dict(data)
        if merge:
            existing = await self._get_singleton(table, person_id)
            if existing:
                body = {**existing, **body}  # shallow top-level merge (Firestore merge=True)
        payload = {"person_id": person_id, "data": body}
        await asyncio.to_thread(
            lambda: self._db().table(table).upsert(payload, on_conflict="person_id").execute()
        )

    async def _get_by_key(
        self, table: str, person_id: str, key_name: str, key_value: Any
    ) -> Optional[Dict[str, Any]]:
        for row in await self._rows(table, person_id):
            if row["data"].get(key_name) == key_value:
                return row
        return None

    async def _upsert_by_key(
        self, table: str, person_id: str, key_name: str, key_value: Any, data: Dict[str, Any]
    ) -> None:
        body = dict(data)
        body[key_name] = key_value
        existing = await self._get_by_key(table, person_id, key_name, key_value)
        if existing:
            payload = {"data": body}
            row_id = existing["id"]
            await asyncio.to_thread(
                lambda: self._db().table(table).update(payload).eq("id", row_id).execute()
            )
        else:
            await self._insert(table, person_id, body)

    async def _delete_by_key(
        self, table: str, person_id: str, key_name: str, key_value: Any
    ) -> bool:
        existing = await self._get_by_key(table, person_id, key_name, key_value)
        if existing:
            row_id = existing["id"]
            await asyncio.to_thread(
                lambda: self._db().table(table).delete().eq("id", row_id).execute()
            )
            return True
        return False

    async def _update_by_key(
        self, table: str, person_id: str, key_name: str, key_value: Any, updates: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        existing = await self._get_by_key(table, person_id, key_name, key_value)
        if not existing:
            return None
        body = dict(existing["data"])
        body.update(updates)
        row_id = existing["id"]
        await asyncio.to_thread(
            lambda: self._db().table(table).update({"data": body}).eq("id", row_id).execute()
        )
        return body

    async def _next_version(self, table: str, person_id: str) -> int:
        versions = [
            r["data"].get("version", 0)
            for r in await self._rows(table, person_id)
            if isinstance(r["data"].get("version"), int)
        ]
        return (max(versions) + 1) if versions else 1

    @staticmethod
    def _sort(rows_payloads: List[Dict[str, Any]], key: str, reverse: bool = False):
        return sorted(rows_payloads, key=lambda x: x.get(key, ""), reverse=reverse)

    # ------------------------------------------------------------------
    # Knowledge Cache (global)
    # ------------------------------------------------------------------
    async def get_cached_knowledge(self, key: str) -> Optional[Dict[str, Any]]:
        row = await self._get_by_key("pm_knowledge_cache", _GLOBAL_PERSON, "cache_key", key)
        return row["data"].get("payload") if row else None

    async def set_cached_knowledge(self, key: str, data: Dict[str, Any]) -> None:
        await self._upsert_by_key(
            "pm_knowledge_cache", _GLOBAL_PERSON, "cache_key", key, {"payload": data}
        )

    # ------------------------------------------------------------------
    # Assessment Submissions
    # ------------------------------------------------------------------
    async def save_assessment_result(self, person_id: str, result_data: Dict[str, Any]) -> None:
        await self._insert("pm_assessments", person_id, result_data)

    async def get_assessment_results(self, person_id: str) -> List[Dict[str, Any]]:
        return self._payloads(await self._rows("pm_assessments", person_id))

    # ------------------------------------------------------------------
    # Assessment Drafts (Pause / Resume)
    # ------------------------------------------------------------------
    async def save_assessment_draft(
        self, person_id: str, assessment_id: str, draft_data: Dict[str, Any]
    ) -> None:
        await self._upsert_by_key(
            "pm_assessment_drafts", person_id, "assessment_id", assessment_id, draft_data
        )

    async def get_assessment_draft(
        self, person_id: str, assessment_id: str
    ) -> Optional[Dict[str, Any]]:
        row = await self._get_by_key("pm_assessment_drafts", person_id, "assessment_id", assessment_id)
        return row["data"] if row else None

    # ------------------------------------------------------------------
    # Counseling Profile
    # ------------------------------------------------------------------
    async def save_counseling_profile(self, person_id: str, profile_data: Dict[str, Any]) -> None:
        await self._upsert_singleton("pm_counseling_profiles", person_id, profile_data)

    async def get_counseling_profile(self, person_id: str) -> Optional[Dict[str, Any]]:
        return await self._get_singleton("pm_counseling_profiles", person_id)

    # ------------------------------------------------------------------
    # Structured Personal Memory Vault
    # ------------------------------------------------------------------
    async def save_personal_memory(self, person_id: str, memory_data: Dict[str, Any]) -> None:
        mem_id = memory_data.get("memory_id") or f"mem_{_utcnow_iso()}"
        await self._upsert_by_key("pm_memories", person_id, "memory_id", mem_id, memory_data)

    async def save_counseling_memory(self, person_id: str, memory_data: Dict[str, Any]) -> None:
        """Persists a counseling episodic memory item via the personal memory store."""
        await self.save_personal_memory(person_id, memory_data)

    async def get_personal_memories(
        self,
        person_id: str,
        memory_type: Optional[str] = None,
        topic: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        mems = self._payloads(await self._rows("pm_memories", person_id))
        if memory_type and memory_type != "ALL":
            mems = [m for m in mems if m.get("memory_type") == memory_type]
        if topic:
            mems = [m for m in mems if topic.lower() in m.get("topic", "").lower()]
        return mems

    async def get_memories(self, person_id: str) -> List[Dict[str, Any]]:
        return await self.get_personal_memories(person_id)

    async def delete_personal_memory(self, person_id: str, memory_id: str) -> bool:
        await self._delete_by_key("pm_memories", person_id, "memory_id", memory_id)
        return True

    # ------------------------------------------------------------------
    # Shared Generalized Learning Patterns (global)
    # ------------------------------------------------------------------
    async def save_shared_pattern(self, pattern_data: Dict[str, Any]) -> None:
        pat_id = pattern_data.get("pattern_id") or f"pat_{_utcnow_iso()}"
        await self._upsert_by_key(
            "pm_shared_patterns", _GLOBAL_PERSON, "pattern_id", pat_id, pattern_data
        )

    async def get_shared_patterns(self) -> List[Dict[str, Any]]:
        return self._payloads(await self._rows("pm_shared_patterns", _GLOBAL_PERSON))

    # ------------------------------------------------------------------
    # Career Path Selection & Versioning
    # ------------------------------------------------------------------
    async def save_selected_path(self, person_id: str, selection_data: Dict[str, Any]) -> int:
        version = await self._next_version("pm_path_versions", person_id)
        selection_data["version"] = version
        await self._insert("pm_path_versions", person_id, selection_data)
        await self._upsert_singleton("pm_active_paths", person_id, selection_data)
        return version

    async def get_active_selected_path(self, person_id: str) -> Optional[Dict[str, Any]]:
        return await self._get_singleton("pm_active_paths", person_id)

    async def get_path_selection_history(self, person_id: str) -> List[Dict[str, Any]]:
        history = self._payloads(await self._rows("pm_path_versions", person_id))
        return sorted(history, key=lambda x: x.get("version", 1))

    # ------------------------------------------------------------------
    # Roadmap Persistence & Versioning
    # ------------------------------------------------------------------
    async def save_roadmap(self, person_id: str, roadmap_data: Dict[str, Any]) -> int:
        version = await self._next_version("pm_roadmap_versions", person_id)
        roadmap_data["version"] = version
        await self._insert("pm_roadmap_versions", person_id, roadmap_data)
        await self._upsert_singleton("pm_active_roadmaps", person_id, roadmap_data)
        return version

    async def get_active_roadmap(self, person_id: str) -> Optional[Dict[str, Any]]:
        return await self._get_singleton("pm_active_roadmaps", person_id)

    async def update_active_roadmap(self, person_id: str, roadmap_data: Dict[str, Any]) -> None:
        await self._upsert_singleton("pm_active_roadmaps", person_id, roadmap_data)

    async def get_roadmap_history(self, person_id: str) -> List[Dict[str, Any]]:
        history = self._payloads(await self._rows("pm_roadmap_versions", person_id))
        return sorted(history, key=lambda x: x.get("version", 1))

    async def get_all_roadmap_versions(self, person_id: str) -> List[Dict[str, Any]]:
        return self._payloads(await self._rows("pm_roadmap_versions", person_id))

    async def get_roadmap_version_by_number(
        self, person_id: str, version_num: int
    ) -> Optional[Dict[str, Any]]:
        for r in await self._rows("pm_roadmap_versions", person_id):
            if r["data"].get("version") == version_num:
                return r["data"]
        return None

    # ------------------------------------------------------------------
    # Evidence Submissions & Evaluations
    # ------------------------------------------------------------------
    async def save_evidence_submission(self, person_id: str, submission: Dict[str, Any]) -> None:
        sub_id = submission.get("submission_id", "sub")
        await self._upsert_by_key(
            "pm_evidence_submissions", person_id, "submission_id", sub_id, submission
        )

    async def save_evaluation_result(self, person_id: str, evaluation: Dict[str, Any]) -> None:
        eval_id = evaluation.get("submission_id", "eval")
        await self._upsert_by_key(
            "pm_evaluations", person_id, "submission_id", eval_id, evaluation
        )

    async def get_stage_submissions(self, person_id: str, stage_id: str) -> List[Dict[str, Any]]:
        subs = self._payloads(await self._rows("pm_evidence_submissions", person_id))
        return [s for s in subs if s.get("stage_id") == stage_id]

    # ------------------------------------------------------------------
    # Personal Agent Model & Learning Events
    # ------------------------------------------------------------------
    async def save_learning_event(self, person_id: str, event: Dict[str, Any]) -> None:
        evt_id = event.get("event_id", "evt")
        await self._upsert_by_key("pm_learning_events", person_id, "event_id", evt_id, event)

    async def get_learning_events(self, person_id: str) -> List[Dict[str, Any]]:
        events = self._payloads(await self._rows("pm_learning_events", person_id))
        return self._sort(events, "timestamp")

    async def save_personal_agent_model(self, person_id: str, model_data: Dict[str, Any]) -> int:
        version = await self._next_version("pm_agent_model_versions", person_id)
        model_data["version"] = version
        await self._insert("pm_agent_model_versions", person_id, model_data)
        await self._upsert_singleton("pm_active_agent_models", person_id, model_data)
        return version

    async def get_personal_agent_model(self, person_id: str) -> Optional[Dict[str, Any]]:
        return await self._get_singleton("pm_active_agent_models", person_id)

    # ------------------------------------------------------------------
    # Canonical Universal Career Profile
    # ------------------------------------------------------------------
    async def save_career_profile(self, person_id: str, profile_data: Dict[str, Any]) -> None:
        await self._upsert_singleton("pm_career_profiles", person_id, profile_data)

    async def get_career_profile(self, person_id: str) -> Optional[Dict[str, Any]]:
        return await self._get_singleton("pm_career_profiles", person_id)

    async def get_profile(self, person_id: str) -> Optional[Dict[str, Any]]:
        return await self.get_career_profile(person_id)

    async def save_profile(self, person_id: str, profile_data: Dict[str, Any]) -> None:
        await self.save_career_profile(person_id, profile_data)

    # ------------------------------------------------------------------
    # Career Goal / Target Outcome
    # ------------------------------------------------------------------
    async def save_career_goal(self, person_id: str, goal_data: Dict[str, Any]) -> None:
        await self._upsert_singleton("pm_career_goals", person_id, goal_data)

    async def get_career_goal(self, person_id: str) -> Optional[Dict[str, Any]]:
        return await self._get_singleton("pm_career_goals", person_id)

    async def save_goal(self, person_id: str, goal_data: Dict[str, Any]) -> None:
        await self.save_career_goal(person_id, goal_data)

    async def get_goal(self, person_id: str) -> Optional[Dict[str, Any]]:
        return await self.get_career_goal(person_id)

    # ------------------------------------------------------------------
    # Readiness Reports & Transition Records
    # ------------------------------------------------------------------
    async def save_readiness_report(self, person_id: str, report_data: Dict[str, Any]) -> None:
        await self._insert("pm_readiness_reports", person_id, report_data)
        await self._upsert_singleton("pm_active_readiness_reports", person_id, report_data)

    async def get_readiness_report(self, person_id: str) -> Optional[Dict[str, Any]]:
        return await self._get_singleton("pm_active_readiness_reports", person_id)

    async def get_readiness_history(self, person_id: str) -> List[Dict[str, Any]]:
        # NOTE: FirestoreStore kept history in-memory only (lost across restarts
        # in Firestore mode). PmStore persists it properly.
        return self._payloads(await self._rows("pm_readiness_reports", person_id))

    # ------------------------------------------------------------------
    # Career Checkpoints
    # ------------------------------------------------------------------
    async def save_career_checkpoint(self, person_id: str, checkpoint_data: Dict[str, Any]) -> None:
        chk_id = checkpoint_data.get("checkpoint_id", "chk")
        await self._upsert_by_key("pm_checkpoints", person_id, "checkpoint_id", chk_id, checkpoint_data)

    async def get_career_checkpoints(self, person_id: str) -> List[Dict[str, Any]]:
        chks = self._payloads(await self._rows("pm_checkpoints", person_id))
        return self._sort(chks, "timestamp")

    # ------------------------------------------------------------------
    # Tailored Resumes
    # ------------------------------------------------------------------
    async def save_tailored_resume(self, person_id: str, resume_data: Dict[str, Any]) -> None:
        res_id = resume_data.get("resume_id", "res")
        await self._upsert_by_key("pm_resumes", person_id, "resume_id", res_id, resume_data)

    async def get_tailored_resumes(self, person_id: str) -> List[Dict[str, Any]]:
        return self._payloads(await self._rows("pm_resumes", person_id))

    # ------------------------------------------------------------------
    # Adaptive Replanning & Audit Trail
    # ------------------------------------------------------------------
    async def resolve_proposed_adaptation(
        self, person_id: str, adaptation_id: str, action: str
    ) -> bool:
        return await self.update_adaptation_status(person_id, adaptation_id, action)

    async def save_micro_adaptation(self, person_id: str, micro_data: Dict[str, Any]) -> None:
        micro_id = micro_data.get(
            "micro_adaptation_id", f"micro_{int(datetime.now(timezone.utc).timestamp() * 1000)}"
        )
        await self._upsert_by_key(
            "pm_micro_adaptations", person_id, "micro_adaptation_id", micro_id, micro_data
        )

    async def get_active_micro_adaptations(self, person_id: str) -> List[Dict[str, Any]]:
        micros = self._payloads(await self._rows("pm_micro_adaptations", person_id))
        micros = [m for m in micros if m.get("active", True)]
        return self._sort(micros, "created_at", reverse=True)

    async def save_proposed_adaptation(
        self, person_id: str, adaptation_data: Dict[str, Any]
    ) -> None:
        adapt_id = adaptation_data.get("adaptation_id", "adapt")
        await self._upsert_by_key(
            "pm_proposed_adaptations", person_id, "adaptation_id", adapt_id, adaptation_data
        )

    async def get_proposed_adaptation(
        self, person_id: str, adaptation_id: str
    ) -> Optional[Dict[str, Any]]:
        row = await self._get_by_key(
            "pm_proposed_adaptations", person_id, "adaptation_id", adaptation_id
        )
        return row["data"] if row else None

    async def get_pending_adaptations(self, person_id: str) -> List[Dict[str, Any]]:
        ads = self._payloads(await self._rows("pm_proposed_adaptations", person_id))
        return [ad for ad in ads if ad.get("status") in ["PENDING_APPROVAL", "REVIEW_REQUIRED"]]

    async def update_adaptation_status(
        self, person_id: str, adaptation_id: str, status: str
    ) -> bool:
        updated = await self._update_by_key(
            "pm_proposed_adaptations",
            person_id,
            "adaptation_id",
            adaptation_id,
            {"status": status, "resolved_at": _utcnow_iso()},
        )
        return updated is not None

    async def save_adaptation_audit(self, person_id: str, audit_data: Dict[str, Any]) -> None:
        audit_id = audit_data.get("audit_id", "audit")
        await self._upsert_by_key(
            "pm_adaptation_audits", person_id, "audit_id", audit_id, audit_data
        )

    async def get_adaptation_audits(self, person_id: str) -> List[Dict[str, Any]]:
        audits = self._payloads(await self._rows("pm_adaptation_audits", person_id))
        return self._sort(audits, "timestamp", reverse=True)

    # ------------------------------------------------------------------
    # Canonical Evidence & Mastery Engine
    # ------------------------------------------------------------------
    async def save_canonical_evidence(self, person_id: str, evidence_data: Dict[str, Any]) -> None:
        ev_id = evidence_data.get("evidence_id", "ev")
        await self._upsert_by_key(
            "pm_canonical_evidence", person_id, "evidence_id", ev_id, evidence_data
        )

    async def get_canonical_evidence(
        self, person_id: str, evidence_id: str
    ) -> Optional[Dict[str, Any]]:
        row = await self._get_by_key(
            "pm_canonical_evidence", person_id, "evidence_id", evidence_id
        )
        return row["data"] if row else None

    async def get_all_person_evidence(self, person_id: str) -> List[Dict[str, Any]]:
        return self._payloads(await self._rows("pm_canonical_evidence", person_id))

    async def save_evaluation_attempt(self, person_id: str, attempt_data: Dict[str, Any]) -> None:
        att_id = attempt_data.get("attempt_id", "att")
        await self._upsert_by_key(
            "pm_evaluation_attempts", person_id, "attempt_id", att_id, attempt_data
        )

    async def get_evaluation_attempts(
        self, person_id: str, stage_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        atts = self._payloads(await self._rows("pm_evaluation_attempts", person_id))
        if stage_id:
            atts = [a for a in atts if a.get("stage_id") == stage_id]
        return self._sort(atts, "evaluated_at", reverse=True)

    async def save_evidence_dispute(self, person_id: str, dispute_data: Dict[str, Any]) -> None:
        disp_id = dispute_data.get("dispute_id", "disp")
        await self._upsert_by_key(
            "pm_evidence_disputes", person_id, "dispute_id", disp_id, dispute_data
        )

    async def get_evidence_disputes(self, person_id: str) -> List[Dict[str, Any]]:
        return self._payloads(await self._rows("pm_evidence_disputes", person_id))

    async def update_evidence_dispute(
        self,
        person_id: str,
        dispute_id: str,
        status: str,
        resolution_note: Optional[str] = None,
    ) -> bool:
        updated = await self._update_by_key(
            "pm_evidence_disputes",
            person_id,
            "dispute_id",
            dispute_id,
            {
                "status": status,
                "resolution_note": resolution_note,
                "resolved_at": _utcnow_iso(),
            },
        )
        return updated is not None

    async def save_skill_mastery_profile(
        self, person_id: str, skill_name: str, profile_data: Dict[str, Any]
    ) -> None:
        await self._upsert_by_key(
            "pm_skill_mastery_profiles", person_id, "skill_name", skill_name, profile_data
        )

    async def get_skill_mastery_profiles(self, person_id: str) -> Dict[str, Dict[str, Any]]:
        rows = self._payloads(await self._rows("pm_skill_mastery_profiles", person_id))
        return {r.get("skill_name"): r for r in rows if r.get("skill_name")}

    # ------------------------------------------------------------------
    # Personal Context Graph & Decision Intelligence
    # ------------------------------------------------------------------
    async def save_decision_record(self, person_id: str, decision_data: Dict[str, Any]) -> None:
        dec_id = decision_data.get("decision_id", "dec")
        await self._upsert_by_key(
            "pm_decision_records", person_id, "decision_id", dec_id, decision_data
        )

    async def get_decision_records(self, person_id: str) -> List[Dict[str, Any]]:
        decs = self._payloads(await self._rows("pm_decision_records", person_id))
        return self._sort(decs, "timestamp", reverse=True)

    async def get_decision_record_by_id(
        self, person_id: str, decision_id: str
    ) -> Optional[Dict[str, Any]]:
        row = await self._get_by_key(
            "pm_decision_records", person_id, "decision_id", decision_id
        )
        return row["data"] if row else None

    async def update_decision_outcome(
        self,
        person_id: str,
        decision_id: str,
        outcome_state: str,
        outcome_note: Optional[str] = None,
    ) -> bool:
        updated = await self._update_by_key(
            "pm_decision_records",
            person_id,
            "decision_id",
            decision_id,
            {"outcome_state": outcome_state, "outcome_note": outcome_note},
        )
        return updated is not None

    async def save_context_conflict(self, person_id: str, conflict_data: Dict[str, Any]) -> None:
        await self._insert("pm_context_conflicts", person_id, conflict_data)

    async def get_context_conflicts(self, person_id: str) -> List[Dict[str, Any]]:
        return self._payloads(await self._rows("pm_context_conflicts", person_id))

    # ------------------------------------------------------------------
    # Proactive Events & Interventions
    # ------------------------------------------------------------------
    async def save_event_record(self, person_id: str, event_data: Dict[str, Any]) -> None:
        evt_id = event_data.get("event_id", "evt")
        await self._upsert_by_key("pm_event_records", person_id, "event_id", evt_id, event_data)

    async def get_event_records(
        self, person_id: str, event_type: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        evts = self._payloads(await self._rows("pm_event_records", person_id))
        if event_type:
            evts = [e for e in evts if e.get("event_type") == event_type]
        return self._sort(evts, "occurred_at", reverse=True)

    async def save_intervention(self, person_id: str, intervention_data: Dict[str, Any]) -> None:
        intv_id = intervention_data.get("intervention_id", "intv")
        await self._upsert_by_key(
            "pm_interventions", person_id, "intervention_id", intv_id, intervention_data
        )

    async def get_interventions(
        self, person_id: str, status: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        intvs = self._payloads(await self._rows("pm_interventions", person_id))
        if status:
            intvs = [i for i in intvs if i.get("status") == status]
        return self._sort(intvs, "created_at", reverse=True)

    async def get_intervention_by_id(
        self, person_id: str, intervention_id: str
    ) -> Optional[Dict[str, Any]]:
        row = await self._get_by_key(
            "pm_interventions", person_id, "intervention_id", intervention_id
        )
        return row["data"] if row else None

    async def update_intervention_status(
        self, person_id: str, intervention_id: str, status: str
    ) -> bool:
        updated = await self._update_by_key(
            "pm_interventions", person_id, "intervention_id", intervention_id, {"status": status}
        )
        return updated is not None

    async def save_notification_preferences(
        self, person_id: str, prefs_data: Dict[str, Any]
    ) -> None:
        await self._upsert_singleton("pm_notification_preferences", person_id, prefs_data)

    async def get_notification_preferences(self, person_id: str) -> Optional[Dict[str, Any]]:
        return await self._get_singleton("pm_notification_preferences", person_id)

    # ------------------------------------------------------------------
    # Trust Layer & Recommendations
    # ------------------------------------------------------------------
    async def save_structured_recommendation(
        self, person_id: str, rec_data: Dict[str, Any]
    ) -> None:
        rec_id = rec_data.get("recommendation_id", "rec")
        await self._upsert_by_key(
            "pm_structured_recommendations", person_id, "recommendation_id", rec_id, rec_data
        )

    async def get_structured_recommendations(
        self, person_id: str, status: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        recs = self._payloads(await self._rows("pm_structured_recommendations", person_id))
        if status:
            recs = [r for r in recs if r.get("status") == status]
        return self._sort(recs, "created_at", reverse=True)

    async def get_structured_recommendation_by_id(
        self, person_id: str, rec_id: str
    ) -> Optional[Dict[str, Any]]:
        row = await self._get_by_key(
            "pm_structured_recommendations", person_id, "recommendation_id", rec_id
        )
        return row["data"] if row else None

    async def update_recommendation_status(
        self, person_id: str, rec_id: str, status: str
    ) -> bool:
        updated = await self._update_by_key(
            "pm_structured_recommendations",
            person_id,
            "recommendation_id",
            rec_id,
            {"status": status},
        )
        return updated is not None

    async def save_recommendation_explanation(
        self, person_id: str, rec_id: str, exp_data: Dict[str, Any]
    ) -> None:
        await self._upsert_by_key(
            "pm_recommendation_explanations", person_id, "rec_id", rec_id, exp_data
        )

    async def get_recommendation_explanation(
        self, person_id: str, rec_id: str
    ) -> Optional[Dict[str, Any]]:
        row = await self._get_by_key(
            "pm_recommendation_explanations", person_id, "rec_id", rec_id
        )
        return row["data"] if row else None

    async def save_recommendation_feedback(
        self, person_id: str, feedback_data: Dict[str, Any]
    ) -> None:
        await self._insert("pm_recommendation_feedback", person_id, feedback_data)

    async def get_recommendation_feedback(
        self, person_id: str, rec_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        fb = self._payloads(await self._rows("pm_recommendation_feedback", person_id))
        if rec_id:
            fb = [f for f in fb if f.get("recommendation_id") == rec_id]
        return fb

    # ------------------------------------------------------------------
    # Longitudinal Learner Model
    # ------------------------------------------------------------------
    async def save_progress_insight(self, person_id: str, insight_data: Dict[str, Any]) -> None:
        ins_id = insight_data.get("insight_id", "ins")
        await self._upsert_by_key(
            "pm_progress_insights", person_id, "insight_id", ins_id, insight_data
        )

    async def get_progress_insights(
        self, person_id: str, status: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        insights = self._payloads(await self._rows("pm_progress_insights", person_id))
        if status:
            insights = [i for i in insights if i.get("status") == status]
        return self._sort(insights, "created_at", reverse=True)

    async def get_progress_insight_by_id(
        self, person_id: str, insight_id: str
    ) -> Optional[Dict[str, Any]]:
        row = await self._get_by_key(
            "pm_progress_insights", person_id, "insight_id", insight_id
        )
        return row["data"] if row else None

    async def update_progress_insight_status(
        self,
        person_id: str,
        insight_id: str,
        status: str,
        dispute_reason: Optional[str] = None,
    ) -> bool:
        updates: Dict[str, Any] = {"status": status}
        if dispute_reason:
            updates["dispute_reason"] = dispute_reason
        updated = await self._update_by_key(
            "pm_progress_insights", person_id, "insight_id", insight_id, updates
        )
        return updated is not None

    async def save_learning_strategy_profile(
        self, person_id: str, profile_data: Dict[str, Any]
    ) -> None:
        dim = profile_data.get("strategy_dimension", "unknown")
        await self._upsert_by_key(
            "pm_learning_strategy_profiles", person_id, "strategy_dimension", dim, profile_data
        )

    async def get_learning_strategy_profiles(self, person_id: str) -> List[Dict[str, Any]]:
        return self._payloads(await self._rows("pm_learning_strategy_profiles", person_id))

    async def save_recurring_misconception(
        self, person_id: str, misc_data: Dict[str, Any]
    ) -> None:
        area = misc_data.get("concept_area", "unknown")
        await self._upsert_by_key(
            "pm_recurring_misconceptions", person_id, "concept_area", area, misc_data
        )

    async def get_recurring_misconceptions(
        self, person_id: str, status: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        miscs = self._payloads(await self._rows("pm_recurring_misconceptions", person_id))
        if status:
            miscs = [m for m in miscs if m.get("status") == status]
        return miscs

    async def save_turning_point(self, person_id: str, tp_data: Dict[str, Any]) -> None:
        await self._insert("pm_turning_points", person_id, tp_data)

    async def get_turning_points(self, person_id: str) -> List[Dict[str, Any]]:
        tps = self._payloads(await self._rows("pm_turning_points", person_id))
        return self._sort(tps, "timestamp", reverse=True)

    # ------------------------------------------------------------------
    # Canonical Artifacts & Verified Portfolio Layer
    # ------------------------------------------------------------------
    async def save_canonical_artifact(self, person_id: str, artifact_data: Dict[str, Any]) -> None:
        art_id = artifact_data.get("artifact_id") or f"art_{_utcnow_iso()}"
        await self._upsert_by_key(
            "pm_canonical_artifacts", person_id, "artifact_id", art_id, artifact_data
        )

    async def get_canonical_artifact(
        self, person_id: str, artifact_id: str
    ) -> Optional[Dict[str, Any]]:
        row = await self._get_by_key(
            "pm_canonical_artifacts", person_id, "artifact_id", artifact_id
        )
        return row["data"] if row else None

    async def get_person_artifacts(
        self, person_id: str, artifact_type: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        arts = self._payloads(await self._rows("pm_canonical_artifacts", person_id))
        if artifact_type:
            arts = [a for a in arts if a.get("type") == artifact_type]
        return arts

    async def save_defense_session(self, person_id: str, session_data: Dict[str, Any]) -> None:
        sess_id = session_data.get("session_id") or f"sess_{_utcnow_iso()}"
        await self._upsert_by_key(
            "pm_defense_sessions", person_id, "session_id", sess_id, session_data
        )

    async def get_defense_session(
        self, person_id: str, session_id: str
    ) -> Optional[Dict[str, Any]]:
        row = await self._get_by_key(
            "pm_defense_sessions", person_id, "session_id", session_id
        )
        return row["data"] if row else None

    async def save_claim_validation(self, person_id: str, claim_data: Dict[str, Any]) -> None:
        await self._insert("pm_claim_validations", person_id, claim_data)

    async def get_claims_validated(self, person_id: str) -> List[Dict[str, Any]]:
        return self._payloads(await self._rows("pm_claim_validations", person_id))

    async def save_step_verification(self, person_id: str, step_data: Dict[str, Any]) -> None:
        await self._insert("pm_step_verifications", person_id, step_data)

    async def get_step_verifications(
        self, person_id: str, stage_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        steps = self._payloads(await self._rows("pm_step_verifications", person_id))
        if stage_id:
            steps = [s for s in steps if s.get("stage_id") == stage_id]
        return steps

    async def record_learning_strategy_outcome(
        self, person_id: str, strategy_type: str, outcome: str, context: str
    ) -> None:
        row = await self._get_by_key(
            "pm_learning_strategy_profiles", person_id, "strategy_dimension", strategy_type
        )
        if row:
            profile = dict(row["data"])
            if outcome == "SUCCESS":
                profile["supporting_events_count"] = profile.get("supporting_events_count", 0) + 1
                profile["confidence_score"] = min(100.0, profile.get("confidence_score", 70.0) + 5.0)
                profile["status"] = "SUPPORTED"
            else:
                profile["contradicting_events_count"] = (
                    profile.get("contradicting_events_count", 0) + 1
                )
                profile["confidence_score"] = max(20.0, profile.get("confidence_score", 70.0) - 10.0)
            profile["last_evaluated_at"] = _utcnow_iso()
            row_id = row["id"]
            await asyncio.to_thread(
                lambda: self._db().table("pm_learning_strategy_profiles")
                .update({"data": profile})
                .eq("id", row_id)
                .execute()
            )
        else:
            await self._insert(
                "pm_learning_strategy_profiles",
                person_id,
                {
                    "strategy_dimension": strategy_type,
                    "status": "SUPPORTED" if outcome == "SUCCESS" else "EMERGING",
                    "confidence_score": 85.0 if outcome == "SUCCESS" else 60.0,
                    "supporting_events_count": 1 if outcome == "SUCCESS" else 0,
                    "contradicting_events_count": 0 if outcome == "SUCCESS" else 1,
                    "effective_context": context,
                    "last_evaluated_at": _utcnow_iso(),
                },
            )

    # ------------------------------------------------------------------
    # Execution Engine, Action Tracking & Accountability
    # ------------------------------------------------------------------
    async def save_action(self, person_id: str, action_data: Dict[str, Any]) -> None:
        act_id = action_data.get("action_id") or f"act_{_utcnow_iso()}"
        await self._upsert_by_key("pm_actions", person_id, "action_id", act_id, action_data)

    async def get_action(
        self, person_id: str, action_id: str
    ) -> Optional[Dict[str, Any]]:
        row = await self._get_by_key("pm_actions", person_id, "action_id", action_id)
        return row["data"] if row else None

    async def get_person_actions(
        self,
        person_id: str,
        stage_id: Optional[str] = None,
        status: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        actions = self._payloads(await self._rows("pm_actions", person_id))
        if stage_id:
            actions = [a for a in actions if a.get("stage_id") == stage_id]
        if status:
            actions = [a for a in actions if a.get("status") == status]
        return actions

    async def save_opportunity_application(
        self, person_id: str, app_data: Dict[str, Any]
    ) -> None:
        app_id = app_data.get("application_id") or f"app_{_utcnow_iso()}"
        await self._upsert_by_key(
            "pm_opportunity_applications", person_id, "application_id", app_id, app_data
        )

    async def get_opportunity_applications(self, person_id: str) -> List[Dict[str, Any]]:
        return self._payloads(await self._rows("pm_opportunity_applications", person_id))

    async def set_execution_pause_state(self, person_id: str, pause_data: Dict[str, Any]) -> None:
        await self._upsert_singleton("pm_execution_pause_states", person_id, pause_data)

    async def get_execution_pause_state(self, person_id: str) -> Optional[Dict[str, Any]]:
        return await self._get_singleton("pm_execution_pause_states", person_id)

    async def save_orchestration_trace(self, person_id: str, trace_data: Dict[str, Any]) -> None:
        await self._insert("pm_orchestration_traces", person_id, trace_data)

    async def get_orchestration_traces(self, person_id: str) -> List[Dict[str, Any]]:
        return self._payloads(await self._rows("pm_orchestration_traces", person_id))

    async def get_orchestration_trace(
        self, person_id: str, workflow_id: str
    ) -> Optional[Dict[str, Any]]:
        for row in await self._rows("pm_orchestration_traces", person_id):
            if row["data"].get("workflow_id") == workflow_id:
                return row["data"]
        return None

    async def save_action_proposal(self, person_id: str, proposal_data: Dict[str, Any]) -> None:
        prop_id = proposal_data.get("proposal_id") or f"prop_{_utcnow_iso()}"
        await self._upsert_by_key(
            "pm_action_proposals", person_id, "proposal_id", prop_id, proposal_data
        )

    async def get_action_proposals(
        self, person_id: str, status: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        props = self._payloads(await self._rows("pm_action_proposals", person_id))
        if status:
            props = [p for p in props if p.get("status") == status]
        return props

    async def get_action_proposal(
        self, person_id: str, proposal_id: str
    ) -> Optional[Dict[str, Any]]:
        row = await self._get_by_key(
            "pm_action_proposals", person_id, "proposal_id", proposal_id
        )
        return row["data"] if row else None

    async def update_action_proposal_status(
        self, person_id: str, proposal_id: str, status: str
    ) -> Optional[Dict[str, Any]]:
        return await self._update_by_key(
            "pm_action_proposals", person_id, "proposal_id", proposal_id, {"status": status}
        )

    # ------------------------------------------------------------------
    # Person Record (Immediate Persistence upon Name Collection)
    # ------------------------------------------------------------------
    async def save_person_record(self, person_id: str, record_data: Dict[str, Any]) -> None:
        await self._upsert_singleton("pm_persons", person_id, record_data, merge=True)

    async def get_person_record(self, person_id: str) -> Optional[Dict[str, Any]]:
        return await self._get_singleton("pm_persons", person_id)

    # ------------------------------------------------------------------
    # Continuous Journey State (Resumption & Progression)
    # ------------------------------------------------------------------
    async def save_journey_state(self, person_id: str, state_data: Dict[str, Any]) -> None:
        await self._upsert_singleton("pm_journey_states", person_id, state_data)

    async def get_journey_state(self, person_id: str) -> Optional[Dict[str, Any]]:
        return await self._get_singleton("pm_journey_states", person_id)

    # ------------------------------------------------------------------
    # Domain-Neutral & Stage-Aware Assessment Blueprint
    # ------------------------------------------------------------------
    async def save_assessment_blueprint(
        self, person_id: str, blueprint_data: Dict[str, Any]
    ) -> None:
        await self._upsert_singleton("pm_assessment_blueprints", person_id, blueprint_data)

    async def get_assessment_blueprint(self, person_id: str) -> Optional[Dict[str, Any]]:
        return await self._get_singleton("pm_assessment_blueprints", person_id)

    # ------------------------------------------------------------------
    # Aspiration tests (onboarding TEST step)
    # Correct answers live in pm_aspiration_tests.data but must NEVER leave
    # the backend — the service layer strips them before responding.
    # ------------------------------------------------------------------
    async def save_aspiration_test(self, person_id: str, test_data: Dict[str, Any]) -> str:
        """Persist a generated test (questions WITH correct answers). Returns test_id."""
        test_id = test_data.get("test_id") or str(uuid.uuid4())
        body = dict(test_data)
        body["test_id"] = test_id
        await self._insert("pm_aspiration_tests", person_id, body)
        return test_id

    async def get_aspiration_test(
        self, person_id: str, test_id: str
    ) -> Optional[Dict[str, Any]]:
        """Fetch one test by test_id; returns None when missing or not owned by person."""
        for row in await self._rows("pm_aspiration_tests", person_id):
            if row["data"].get("test_id") == test_id:
                return row["data"]
        return None

    async def get_latest_aspiration_test(
        self, person_id: str
    ) -> Optional[Dict[str, Any]]:
        """Latest generated test for a person (the pending/active one)."""
        rows = await self._rows("pm_aspiration_tests", person_id)
        if not rows:
            return None
        latest = max(rows, key=lambda r: r.get("created_at") or "")
        return latest["data"]

    async def save_test_result(
        self, person_id: str, result_data: Dict[str, Any]
    ) -> str:
        """Persist a test evaluation. Returns result_id."""
        result_id = result_data.get("result_id") or str(uuid.uuid4())
        body = dict(result_data)
        body["result_id"] = result_id
        await self._insert("pm_test_results", person_id, body)
        return result_id

    async def get_test_result(
        self, person_id: str, result_id: str
    ) -> Optional[Dict[str, Any]]:
        """Fetch one result by result_id; None when missing or not owned by person."""
        for row in await self._rows("pm_test_results", person_id):
            if row["data"].get("result_id") == result_id:
                return row["data"]
        return None

    async def get_test_result_for_test(
        self, person_id: str, test_id: str
    ) -> Optional[Dict[str, Any]]:
        """Latest result submitted for a given test (None when unattempted)."""
        matches = [
            r for r in await self._rows("pm_test_results", person_id)
            if r["data"].get("test_id") == test_id
        ]
        if not matches:
            return None
        latest = max(matches, key=lambda r: r.get("created_at") or "")
        return latest["data"]


    # ------------------------------------------------------------------
    # Verified question bank (pm_domains, pm_domain_aliases, pm_question_bank,
    # pm_question_reviews, pm_test_question_map — migration 004)
    #
    # Tier order for serving: VERIFIED > EXPERT_REVIEWED > AI_DRAFT.
    # The word "verified" is never shown to users unless
    # verification_status == VERIFIED with an official source + key.
    # ------------------------------------------------------------------
    _BANK_TIER_ORDER = {"VERIFIED": 0, "EXPERT_REVIEWED": 1, "AI_DRAFT": 2}

    async def get_domain_for_aspiration(self, text: str) -> str:
        """Deterministic alias match: free-text aspiration -> domain slug.

        Returns 'general' when nothing matches (the honest uncharted path).
        """
        if not text:
            return "general"
        lowered = text.lower()

        def _lookup():
            rows = (
                self._db().table("pm_domain_aliases").select("alias,domain_slug").execute()
            ).data or []
            return rows

        try:
            rows = await asyncio.to_thread(_lookup)
        except Exception:
            return "general"
        # Longest alias first so "electronics mechanic" beats "mechanic"
        for row in sorted(rows, key=lambda r: len(r.get("alias") or ""), reverse=True):
            alias = (row.get("alias") or "").lower()
            if alias and alias in lowered:
                return row["domain_slug"]
        return "general"

    async def get_bank_questions(
        self, domain: str, limit: int = 12,
        tiers: tuple = ("VERIFIED", "EXPERT_REVIEWED", "AI_DRAFT"),
    ) -> List[Dict[str, Any]]:
        """Fetch active bank questions for a domain, tier-ordered, least-used first."""
        def _q():
            return (
                self._db().table("pm_question_bank")
                .select("*")
                .eq("domain", domain)
                .eq("status", "active")
                .in_("verification_status", list(tiers))
                .execute()
            ).data or []

        try:
            rows = await asyncio.to_thread(_q)
        except Exception:
            return []
        order = self._BANK_TIER_ORDER
        rows.sort(key=lambda r: (
            order.get(r.get("verification_status"), 9),
            r.get("usage_count") or 0,
            r.get("last_used_at") or "",
        ))
        return rows[:limit]

    async def save_bank_question(self, q: Dict[str, Any]) -> str:
        """Insert one bank question. Returns question_id."""
        def _ins():
            payload = dict(q)
            payload.pop("question_id", None)
            return (
                self._db().table("pm_question_bank").insert(payload).execute()
            ).data[0]["question_id"]

        return await asyncio.to_thread(_ins)

    async def record_test_questions(
        self, test_id: str, items: List[tuple]
    ) -> None:
        """Audit trail: which bank questions a test served, and their tier at serve time."""
        def _ins():
            rows = [
                {"test_id": test_id, "question_id": qid, "tier_at_time": tier}
                for qid, tier in items
            ]
            if rows:
                self._db().table("pm_test_question_map").insert(rows).execute()

        await asyncio.to_thread(_ins)

    async def bump_question_usage(self, question_ids: List[str]) -> None:
        """Increment usage_count + last_used_at for rotation."""
        if not question_ids:
            return

        def _upd():
            now = datetime.now(timezone.utc).isoformat()
            for qid in question_ids:
                try:
                    row = (
                        self._db().table("pm_question_bank")
                        .select("usage_count").eq("question_id", qid).single().execute()
                    ).data or {}
                    self._db().table("pm_question_bank").update({
                        "usage_count": (row.get("usage_count") or 0) + 1,
                        "last_used_at": now,
                        "updated_at": now,
                    }).eq("question_id", qid).execute()
                except Exception:
                    continue

        await asyncio.to_thread(_upd)

    async def save_question_review(
        self, question_id: str, reviewer: str, verdict: str, notes: str = ""
    ) -> None:
        """Record an expert review verdict; promotes/demotes the question tier."""
        def _run():
            self._db().table("pm_question_reviews").insert({
                "question_id": question_id,
                "reviewer": reviewer,
                "verdict": verdict,
                "notes": notes,
            }).execute()
            if verdict == "approved":
                self._db().table("pm_question_bank").update({
                    "verification_status": "EXPERT_REVIEWED",
                    "verified_by": reviewer,
                    "verified_at": datetime.now(timezone.utc).isoformat(),
                    "updated_at": datetime.now(timezone.utc).isoformat(),
                }).eq("question_id", question_id).execute()
            elif verdict == "rejected":
                self._db().table("pm_question_bank").update({
                    "verification_status": "DEPRECATED",
                    "status": "deprecated",
                    "updated_at": datetime.now(timezone.utc).isoformat(),
                }).eq("question_id", question_id).execute()

        await asyncio.to_thread(_run)


    async def save_domain_request(self, person_id: str, aspiration_text: str) -> str:
        """Record an uncharted aspiration for later research/promotion."""
        import re as _re
        slug = _re.sub(r"[^a-z0-9]+", "_", (aspiration_text or "").lower()).strip("_")[:60]
        slug = slug or "unknown"

        def _ins():
            existing = (
                self._db().table("pm_domain_requests")
                .select("request_id").eq("normalized_slug", slug)
                .eq("status", "pending").limit(1).execute()
            ).data
            if existing:
                return existing[0]["request_id"]
            return (
                self._db().table("pm_domain_requests").insert({
                    "person_id": person_id,
                    "aspiration_text": aspiration_text,
                    "normalized_slug": slug,
                    "status": "pending",
                }).execute()
            ).data[0]["request_id"]

        return await asyncio.to_thread(_ins)


    # ------------------------------------------------------------------
    # User verification (pm_verifications — explicit columns, migration 002)
    # One active verification per person; resubmission upserts the row.
    # ------------------------------------------------------------------
    async def save_verification(
        self, person_id: str, record: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Upsert the person's verification row. Returns the stored row."""
        payload = {
            "person_id": person_id,
            "user_type": record.get("user_type"),
            "verification_data": record.get("verification_data") or {},
            "document_urls": record.get("document_urls") or [],
            "status": record.get("status") or "PENDING",
            "verified_at": record.get("verified_at"),
            "updated_at": _utcnow_iso(),
        }

        def _upsert():
            return (
                self._db()
                .table("pm_verifications")
                .upsert(payload, on_conflict="person_id")
                .execute()
            )

        res = await asyncio.to_thread(_upsert)
        rows = res.data or []
        return rows[0] if rows else payload

    async def get_verification(self, person_id: str) -> Optional[Dict[str, Any]]:
        """Current verification row for the person (None if never submitted)."""

        def _select():
            return (
                self._db()
                .table("pm_verifications")
                .select("*")
                .eq("person_id", person_id)
                .execute()
            )

        res = await asyncio.to_thread(_select)
        rows = res.data or []
        return rows[0] if rows else None

    async def get_verification_by_id(self, verification_id: str) -> Optional[Dict[str, Any]]:
        """Fetch a verification row by its id."""

        def _select():
            return (
                self._db()
                .table("pm_verifications")
                .select("*")
                .eq("id", verification_id)
                .execute()
            )

        res = await asyncio.to_thread(_select)
        rows = res.data or []
        return rows[0] if rows else None

    async def update_verification_status(
        self, verification_id: str, status: str, reasons: List[str]
    ) -> Dict[str, Any]:
        """Set status (+ reasons, verified_at) for a verification row."""
        payload: Dict[str, Any] = {
            "status": status,
            "updated_at": _utcnow_iso(),
            "verified_at": _utcnow_iso() if status == "VERIFIED" else None,
        }

        def _update():
            # Read-modify-write so evaluation reasons are appended into
            # verification_data without clobbering submitted values.
            current = (
                self._db()
                .table("pm_verifications")
                .select("*")
                .eq("id", verification_id)
                .execute()
            )
            rows = current.data or []
            if not rows:
                raise RuntimeError(f"pm_verifications row {verification_id} not found")
            data = dict(rows[0].get("verification_data") or {})
            data["evaluation_reasons"] = list(reasons or [])
            payload["verification_data"] = data
            updated = (
                self._db()
                .table("pm_verifications")
                .update(payload)
                .eq("id", verification_id)
                .execute()
            )
            return (updated.data or [rows[0]])[0]

        return await asyncio.to_thread(_update)


_pm_store_instance: Optional[PmStore] = None


def get_pm_store() -> PmStore:
    """Process-wide PmStore singleton. Raises loudly if Supabase is unusable."""
    global _pm_store_instance
    if _pm_store_instance is None:
        _pm_store_instance = PmStore()
    return _pm_store_instance
