"""
Computed trajectory intelligence (not narrated).

Derives from stored data only — no LLM prose:
  pace          28-day planned-vs-completed commitments (+ per-week rate)
  pivots        DECISION-nature memories, chronological, with reasons
  skill_velocity verified skills count + per-30-day rate since first claim
  lapsed        planned commitments overdue by more than LAPSED_AFTER_DAYS

Read-only. Every computation is fail-soft; missing data yields nulls, never
exceptions. This is the "failure memory" and "computed trajectory" substrate
the counselor and the timeline read from.
"""
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from backend.services.commitment_service import CommitmentService
from backend.services.longitudinal_memory_service import LongitudinalMemoryService
from backend.services.skill_profile_service import (
    SKILL_NATURE, _is_skill_memory, _meta, _normalize_skill, _status,
)

LAPSED_AFTER_DAYS = 14
PACE_WINDOW_DAYS = 28


def _parse(ts: Any) -> Optional[datetime]:
    try:
        dt = datetime.fromisoformat(str(ts).replace("Z", "+00:00"))
        return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
    except Exception:
        return None


def _nature(m: Dict[str, Any]) -> str:
    return str(_meta(m).get("nature") or m.get("nature") or "")


class TrajectoryService:
    def __init__(
        self,
        memory: Optional[LongitudinalMemoryService] = None,
        commitments: Optional[CommitmentService] = None,
    ):
        self._memory = memory
        self._commitments = commitments

    @property
    def memory(self) -> LongitudinalMemoryService:
        if self._memory is None:
            self._memory = LongitudinalMemoryService()
        return self._memory

    @property
    def commitment_service(self) -> CommitmentService:
        if self._commitments is None:
            self._commitments = CommitmentService()
        return self._commitments

    async def _commitments_all(self, person_id: str) -> List[Dict[str, Any]]:
        try:
            return await self.commitment_service.list_commitments(person_id)
        except Exception:
            return []

    async def _memories(self, person_id: str) -> List[Dict[str, Any]]:
        try:
            return await self.memory.get_long_term(person_id, limit=200)
        except Exception:
            return []

    async def pace(self, person_id: str,
                   window_days: int = PACE_WINDOW_DAYS) -> Dict[str, Any]:
        """Plan-vs-actual over the trailing window + completions per week."""
        now = datetime.now(timezone.utc)
        start = now - timedelta(days=window_days)
        due, done = 0, 0
        per_week_done = 0.0
        try:
            for c in await self._commitments_all(person_id):
                d = _parse(c.get("due_at"))
                if not d or not (start <= d <= now):
                    continue
                due += 1
                if c.get("status") == "completed":
                    done += 1
            per_week_done = round(done / (window_days / 7), 2)
        except Exception:
            pass
        return {
            "window_days": window_days,
            "due": due,
            "completed": done,
            "completion_rate": round(done / due, 2) if due else None,
            "completions_per_week": per_week_done,
        }

    async def pivots(self, person_id: str) -> List[Dict[str, Any]]:
        """Decision journal entries, chronological, with reasons."""
        out = []
        for m in await self._memories(person_id):
            if _nature(m) != "DECISION":
                continue
            meta = _meta(m)
            out.append({
                "at": m.get("created_at"),
                "title": m.get("title"),
                "reason": (m.get("content") or "")[:300],
                "alternatives_rejected": meta.get("alternatives_rejected") or [],
            })
        out.sort(key=lambda e: e["at"] or "")
        return out

    async def skill_velocity(self, person_id: str) -> Dict[str, Any]:
        """Verified-skill accumulation rate. Honest about sparse data."""
        latest: Dict[str, Dict[str, Any]] = {}
        for m in await self._memories(person_id):
            if not _is_skill_memory(m):
                continue
            skill = _meta(m).get("skill") or _normalize_skill(m.get("title", ""))
            if not skill:
                continue
            prev = latest.get(skill)
            if prev is None or (m.get("created_at") or "") > (prev.get("created_at") or ""):
                latest[skill] = m
        verified = [s for s, m in latest.items() if _status(m) == "VERIFIED"]
        first_dates = [m.get("created_at") for m in latest.values() if m.get("created_at")]
        months = None
        per_30d = None
        if first_dates:
            first = min(first_dates)
            dt = _parse(first)
            if dt:
                days = max(1, (datetime.now(timezone.utc) - dt).days)
                months = round(days / 30, 1)
                per_30d = round(len(verified) / (days / 30), 2)
        return {
            "verified_count": len(verified),
            "claimed_total": len(latest),
            "months_since_first_claim": months,
            "verified_per_30d": per_30d,
        }

    async def lapsed(self, person_id: str) -> List[Dict[str, Any]]:
        """Failure memory: planned commitments overdue beyond the lapse horizon."""
        now = datetime.now(timezone.utc)
        out = []
        for c in await self._commitments_all(person_id):
            if c.get("status") != "planned":
                continue
            d = _parse(c.get("due_at"))
            if not d:
                continue
            days_overdue = (now - d).days
            if days_overdue > LAPSED_AFTER_DAYS:
                out.append({
                    "title": c.get("title"),
                    "due_at": c.get("due_at"),
                    "days_overdue": days_overdue,
                })
        out.sort(key=lambda e: e["days_overdue"], reverse=True)
        return out

    async def summary(self, person_id: str) -> Dict[str, Any]:
        """Full computed trajectory in one call."""
        return {
            "person_id": person_id,
            "computed_at": datetime.now(timezone.utc).isoformat(),
            "pace_28d": await self.pace(person_id),
            "pivots": await self.pivots(person_id),
            "skill_velocity": await self.skill_velocity(person_id),
            "lapsed": await self.lapsed(person_id),
        }
