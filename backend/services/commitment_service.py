"""
Commitment & accountability service for the PathMind main product.

Ported from the college MVP's CollegeAccountabilityService (commitments,
streaks, today's schedule) — rewired to PmStore/Supabase instead of the
college Firestore store. Deterministic streak math: consecutive calendar
days with at least one completed commitment; zero activity = zero streak.
"""

from typing import List, Dict, Any, Optional
import uuid
from datetime import datetime, timezone, date

from backend.services.pm_store import get_pm_store


VALID_STATUSES = ("planned", "in_progress", "completed", "cancelled", "missed")


def calculate_streak_days(completed_dates: List[date], today: date) -> int:
    """Consecutive days ending today (or yesterday) with >= 1 completion."""
    if not completed_dates:
        return 0
    days = sorted(set(completed_dates), reverse=True)
    # Streak can be "alive" if the most recent completion was today or yesterday.
    if days[0] < today and (today - days[0]).days > 1:
        return 0
    streak = 0
    cursor = today
    day_set = set(days)
    # Allow the streak to start yesterday (today not done yet).
    if cursor not in day_set:
        cursor = date.fromordinal(today.toordinal() - 1)
    while cursor in day_set:
        streak += 1
        cursor = date.fromordinal(cursor.toordinal() - 1)
    return streak


class CommitmentService:
    def __init__(self, store=None):
        self._store = store

    @property
    def store(self):
        if self._store is None:
            from backend.services.pm_store import get_pm_store
            self._store = get_pm_store()
        return self._store

    async def create_commitment(
        self,
        person_id: str,
        title: str,
        due_at: Optional[str] = None,
        estimated_minutes: int = 60,
        roadmap_phase: Optional[str] = None,
    ) -> Dict[str, Any]:
        commitment = {
            "commitment_id": f"cmt_{uuid.uuid4().hex[:8]}",
            "title": title.strip(),
            "due_at": due_at,
            "estimated_minutes": max(5, int(estimated_minutes or 60)),
            "roadmap_phase": roadmap_phase,
            "status": "planned",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "completed_at": None,
        }
        await self.store._insert("pm_commitments", person_id, commitment)
        return commitment

    async def list_commitments(
        self, person_id: str, status: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        rows = await self.store._rows("pm_commitments", person_id)
        out = [r["data"] for r in rows]
        if status:
            out = [c for c in out if c.get("status") == status]
        out.sort(key=lambda c: c.get("created_at") or "", reverse=True)
        return out

    async def update_commitment_status(
        self, person_id: str, commitment_id: str, status: str
    ) -> Optional[Dict[str, Any]]:
        if status not in VALID_STATUSES:
            raise ValueError(f"Invalid status {status!r}; expected one of {VALID_STATUSES}")
        rows = await self.store._rows("pm_commitments", person_id)

        def _run():
            for r in rows:
                if r["data"].get("commitment_id") == commitment_id:
                    body = dict(r["data"])
                    body["status"] = status
                    body["updated_at"] = datetime.now(timezone.utc).isoformat()
                    if status == "completed":
                        body["completed_at"] = body["updated_at"]
                    (self.store._db().table("pm_commitments")
                     .update({"data": body}).eq("id", r["id"]).execute())
                    return body
            return None

        import asyncio
        return await asyncio.to_thread(_run)

    async def get_today_schedule(self, person_id: str) -> Dict[str, Any]:
        """Today's actionable schedule: open commitments, streak, totals."""
        commitments = await self.list_commitments(person_id)
        today = datetime.now(timezone.utc).date()

        open_cmts = [c for c in commitments if c.get("status") in ("planned", "in_progress")]
        completed_dates: List[date] = []
        for c in commitments:
            if c.get("status") != "completed":
                continue
            ts = c.get("completed_at") or c.get("updated_at")
            if not ts:
                continue
            try:
                completed_dates.append(datetime.fromisoformat(str(ts)).date())
            except (ValueError, TypeError):
                continue
        streak = calculate_streak_days(completed_dates, today)

        total_planned = sum(
            c.get("estimated_minutes", 0) for c in commitments
            if c.get("status") != "cancelled"
        )
        total_completed = sum(
            c.get("estimated_minutes", 0) for c in commitments
            if c.get("status") == "completed"
        )
        # Due today or overdue (and still open)
        due_today = []
        for c in open_cmts:
            due = c.get("due_at")
            if not due:
                continue
            try:
                due_date = datetime.fromisoformat(str(due)).date()
                if due_date <= today:
                    due_today.append(c)
            except (ValueError, TypeError):
                continue

        return {
            "date": today.isoformat(),
            "streak_days": streak,
            "open_commitments": open_cmts,
            "due_today_or_overdue": due_today,
            "total_planned_minutes": total_planned,
            "total_completed_minutes": total_completed,
            "completion_rate": round(total_completed / total_planned, 2) if total_planned else 0.0,
        }
