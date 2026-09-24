"""
Accountability & Exam Timeline Engine for PATHMIND College Engineering MVP.
Calculates deterministic exam countdowns, manages study commitments,
tracks streaks, and organizes today's actionable schedule.
"""

from typing import List, Dict, Any, Optional
import uuid
from datetime import datetime, timezone, date
from backend.core.college_schemas import (
    AccountabilityCommitment,
    CommitmentStatus,
    TodaySchedule,
    AcademicContext,
    CollegeActivity
)
from backend.core.college_rules import calculate_streak_days, exam_countdown_days
from backend.core.college_logging import log_event, timed_stage
from backend.services.store import FirestoreStore

class CollegeAccountabilityService:
    def __init__(self, store: Optional[FirestoreStore] = None):
        self.store = store or FirestoreStore()

    async def calculate_exam_countdown(self, uid: str) -> Optional[int]:
        """Calculates exact days remaining until upcoming university examinations."""
        raw_ctx = await self.store.get_college_academic_context(uid)
        if not raw_ctx:
            return None
        
        ctx = AcademicContext(**raw_ctx)
        exam_start = ctx.exam_window.get("start")
        if not exam_start:
            # Check goal deadline as fallback
            raw_goal = await self.store.get_college_goal(uid)
            if raw_goal and raw_goal.get("deadline"):
                exam_start = raw_goal["deadline"]

        if not exam_start:
            return None

        try:
            # Parse ISO or YYYY-MM-DD
            clean_date = exam_start.split("T")[0]
            target_date = datetime.strptime(clean_date, "%Y-%m-%d").date()
            today = datetime.now(timezone.utc).date()
            return exam_countdown_days(target_date, today)
        except Exception:
            return None

    async def create_commitment(
        self,
        uid: str,
        title: str,
        due_at: str,
        estimated_minutes: int = 60,
        plan_id: Optional[str] = None,
        phase_id: Optional[str] = None
    ) -> AccountabilityCommitment:
        """Records a learner commitment with strict status tracking."""
        commitment = AccountabilityCommitment(
            commitment_id=f"cmt_{uuid.uuid4().hex[:8]}",
            user_id=uid,
            title=title,
            due_at=due_at,
            estimated_minutes=estimated_minutes,
            plan_id=plan_id,
            phase_id=phase_id,
            status=CommitmentStatus.PLANNED
        )
        await self.store.save_college_commitment(uid, commitment.model_dump(mode="json"))
        return commitment

    async def update_commitment_status(
        self,
        uid: str,
        commitment_id: str,
        status: CommitmentStatus
    ) -> Optional[AccountabilityCommitment]:
        res = await self.store.update_college_commitment_status(uid, commitment_id, status.value)
        if res:
            # The store may return a model instance (direct CollegeStore) or a
            # dict (FirestoreStore delegation) — handle both honestly.
            return res if isinstance(res, AccountabilityCommitment) else AccountabilityCommitment(**res)
        return None

    async def get_today_schedule(self, uid: str) -> TodaySchedule:
        """Compiles today's actionable study plan, commitments, and exam urgency."""
        countdown = await self.calculate_exam_countdown(uid)
        raw_cmts = await self.store.get_college_commitments(uid)
        commitments = [AccountabilityCommitment(**c) for c in raw_cmts]

        # Fetch active learning plan activities
        raw_plan = await self.store.get_college_learning_plan(uid)
        active_activities: List[CollegeActivity] = []
        if raw_plan:
            for phase in raw_plan.get("phases", []):
                if phase.get("status") in ["AVAILABLE", "IN_PROGRESS"]:
                    for act in phase.get("activities", []):
                        if act.get("status") in ["AVAILABLE", "IN_PROGRESS"]:
                            active_activities.append(CollegeActivity(**act))

        today = datetime.now(timezone.utc).date()
        today_str = today.isoformat()
        total_planned = sum(c.estimated_minutes for c in commitments if c.status != CommitmentStatus.CANCELLED)
        total_completed = sum(c.estimated_minutes for c in commitments if c.status == CommitmentStatus.COMPLETED)

        # Real streak: consecutive calendar days with at least one completed
        # commitment, derived from completion timestamps. Zero activity gives
        # zero — no minimum floor.
        completed_dates = []
        for c in commitments:
            if c.status != CommitmentStatus.COMPLETED or not c.updated_at:
                continue
            try:
                completed_dates.append(
                    datetime.fromisoformat(c.updated_at).date())
            except (ValueError, TypeError):
                continue
        streak = calculate_streak_days(completed_dates, today)
        log_event("college.accountability.streak_computed", user_id=uid,
                  streak_days=streak,
                  completed_commitments=len(completed_dates), outcome="ok")

        from backend.core.college_schemas import CollegeAssessment
        raw_assessments = await self.store.get_all_college_assessments(uid)
        active_assessments = []
        for a in raw_assessments:
            if a.get("status") == "AVAILABLE":
                active_assessments.append(CollegeAssessment(**a))

        return TodaySchedule(
            date=today_str,
            exam_days_remaining=countdown,
            commitments=commitments,
            active_activities=active_activities,
            active_assessments=active_assessments,
            streak_days=streak,
            total_planned_minutes=total_planned,
            total_completed_minutes=total_completed
        )
