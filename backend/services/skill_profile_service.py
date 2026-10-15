"""
Skill verification lifecycle + anti-resume (verified, not vibes — made real).

Append-only design: a skill claim is recorded as a long-term memory with
evidence_verification_status=SELF_REPORTED; submitting evidence runs the
deterministic EvidenceVerificationService and appends a new memory with the
outcome (VERIFIED / UNVERIFIED). Latest record per skill wins, so the full
audit trail survives. A VERIFIED outcome also records a MILESTONE signal so
the counselor's longitudinal brief picks it up and can acknowledge it.

Conventions (must match readers in trajectory_service / memory_tier_routes):
  metadata = {"nature": "SKILL_KNOWLEDGE", "skill": <normalized>,
              "evidence_verification_status": <status>, ...}
"""
from typing import Any, Dict, List, Optional

from backend.services.longitudinal_memory_service import LongitudinalMemoryService
from backend.services.evidence_verification_service import (
    EvidenceVerificationService,
)

SKILL_NATURE = "SKILL_KNOWLEDGE"


def _normalize_skill(skill: str) -> str:
    return " ".join((skill or "").strip().lower().split())


def _meta(m: Dict[str, Any]) -> Dict[str, Any]:
    return m.get("metadata") or {}


def _is_skill_memory(m: Dict[str, Any]) -> bool:
    return _meta(m).get("nature") == SKILL_NATURE or (
        m.get("nature") == SKILL_NATURE
    )


def _status(m: Dict[str, Any]) -> str:
    return _meta(m).get("evidence_verification_status") or m.get(
        "evidence_verification_status", "SELF_REPORTED"
    )


class SkillProfileService:
    """Append-only skill claim/verification lifecycle."""

    def __init__(self, memory: Optional[LongitudinalMemoryService] = None):
        self._memory = memory

    @property
    def memory(self) -> LongitudinalMemoryService:
        if self._memory is None:
            self._memory = LongitudinalMemoryService()
        return self._memory

    async def _skill_memories(self, person_id: str) -> List[Dict[str, Any]]:
        try:
            all_mems = await self.memory.get_long_term(person_id, limit=200)
        except Exception:
            return []
        return [m for m in all_mems if _is_skill_memory(m)]

    async def claim_skill(self, person_id: str, skill: str) -> Dict[str, Any]:
        """Record a self-reported skill claim. Never presented as verified."""
        norm = _normalize_skill(skill)
        if not norm or len(norm) > 80:
            raise ValueError("skill must be 1-80 characters")
        mem = await self.memory.record_long_term(
            person_id=person_id,
            title=f"Skill claimed: {norm}",
            content=(
                f"Learner claims knowledge of '{norm}'. SELF-REPORTED — "
                "not verified. Do not treat as established fact."
            ),
            memory_type="SEMANTIC",
            importance="MEDIUM",
            related_domain=norm,
            metadata={
                "nature": SKILL_NATURE,
                "skill": norm,
                "evidence_verification_status": "SELF_REPORTED",
            },
        )
        return {"skill": norm, "status": "SELF_REPORTED",
                "memory_id": mem.get("memory_id")}

    async def verify_skill(
        self,
        person_id: str,
        skill: str,
        payload: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Run deterministic verification on submitted evidence and append the
        outcome. payload: {code?, repo_url?, explanation?}.
        """
        norm = _normalize_skill(skill)
        if not norm:
            raise ValueError("skill is required")
        payload = payload or {}
        status, quality, confidence = EvidenceVerificationService().verify_artifact(
            None, payload
        )
        # Map engine statuses onto the memory lifecycle vocabulary.
        final = "VERIFIED" if status == "VERIFIED" else "UNVERIFIED"
        mem = await self.memory.record_long_term(
            person_id=person_id,
            title=f"Skill verification ({final.lower()}): {norm}",
            content=(
                f"Evidence submitted for '{norm}' was deterministically "
                f"evaluated: status={status}, quality={quality}, "
                f"confidence={confidence}."
            ),
            memory_type="SEMANTIC",
            importance="HIGH" if final == "VERIFIED" else "MEDIUM",
            related_domain=norm,
            metadata={
                "nature": SKILL_NATURE,
                "skill": norm,
                "evidence_verification_status": final,
                "verification_detail": {
                    "status": status, "quality": quality,
                    "confidence": confidence,
                },
            },
        )
        if final == "VERIFIED":
            try:
                await self.memory.record_signal(
                    person_id=person_id,
                    signal_type="MILESTONE",
                    content=f"Skill verified: {norm} ({quality}, {confidence} confidence)",
                    related_domain=norm,
                )
            except Exception:
                pass
        return {
            "skill": norm,
            "status": final,
            "engine_status": status,
            "quality": quality,
            "confidence": confidence,
            "memory_id": mem.get("memory_id"),
        }

    async def skill_profile(
        self, person_id: str, gaps: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        The anti-resume: proven vs claimed vs missing, side by side.
        Latest record per skill wins. Gaps come from the caller's journey
        state (evidence_gaps) — passed in so this service stays decoupled.
        """
        mems = await self._skill_memories(person_id)
        latest: Dict[str, Dict[str, Any]] = {}
        for m in sorted(mems, key=lambda x: x.get("created_at") or ""):
            skill = _meta(m).get("skill") or _normalize_skill(m.get("title", ""))
            if skill:
                latest[skill] = m
        proven, claimed = [], []
        for skill, m in sorted(latest.items()):
            entry = {
                "skill": skill,
                "status": _status(m),
                "detail": (_meta(m).get("verification_detail")
                           or {"status": _status(m)}),
                "at": m.get("created_at"),
            }
            (proven if _status(m) == "VERIFIED" else claimed).append(entry)
        return {
            "person_id": person_id,
            "proven": proven,
            "claimed": claimed,
            "gaps": gaps or [],
            "counts": {
                "proven": len(proven),
                "claimed": len(claimed),
                "gaps": len(gaps or []),
            },
        }
