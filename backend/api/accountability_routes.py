"""
Accountability routes: commitments, streaks, today's schedule.

The daily accountability loop ported from the college MVP.
Auth: person_id always comes from the verified JWT.
"""

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from backend.core.security import get_authenticated_person
from backend.services.commitment_service import CommitmentService, VALID_STATUSES

router = APIRouter(prefix="/api/accountability", tags=["Accountability"])
get_person_id = get_authenticated_person

_service: Optional[CommitmentService] = None


def get_service() -> CommitmentService:
    global _service
    if _service is None:
        _service = CommitmentService()
    return _service


class CreateCommitmentRequest(BaseModel):
    title: str = Field(..., min_length=3, max_length=200)
    due_at: Optional[str] = None
    estimated_minutes: int = Field(default=60, ge=5, le=1440)
    roadmap_phase: Optional[str] = None


class UpdateStatusRequest(BaseModel):
    status: str


@router.post("/commitments")
async def create_commitment(
    req: CreateCommitmentRequest,
    person_id: str = Depends(get_person_id),
):
    try:
        return await get_service().create_commitment(
            person_id,
            title=req.title,
            due_at=req.due_at,
            estimated_minutes=req.estimated_minutes,
            roadmap_phase=req.roadmap_phase,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/commitments")
async def list_commitments(
    status: Optional[str] = Query(None),
    person_id: str = Depends(get_person_id),
):
    if status and status not in VALID_STATUSES:
        raise HTTPException(status_code=400, detail=f"Invalid status; one of {VALID_STATUSES}")
    return await get_service().list_commitments(person_id, status=status)


@router.patch("/commitments/{commitment_id}")
async def update_commitment(
    commitment_id: str,
    req: UpdateStatusRequest,
    person_id: str = Depends(get_person_id),
):
    try:
        updated = await get_service().update_commitment_status(
            person_id, commitment_id, req.status
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    if updated is None:
        raise HTTPException(status_code=404, detail="Commitment not found")
    return updated


@router.get("/today")
async def today_schedule(person_id: str = Depends(get_person_id)):
    """Today's schedule: open commitments, due/overdue, streak, completion rate."""
    return await get_service().get_today_schedule(person_id)


@router.get("/check-in")
async def accountability_check_in(person_id: str = Depends(get_person_id)):
    """
    The accountability loop: weekly check-in with plan-vs-actual.

    Returns overdue commitments, this week's planned-vs-completed numbers,
    and — for the most overdue item — a non-judgmental intervention with
    concrete options (continue / reschedule / report blocker / adjust).
    This is the difference between a chatbot and a coach: the system checks
    whether the plan was followed and adapts. Fail-soft: check-in problems
    never break the rest of the API.
    """
    from datetime import datetime, timedelta, timezone

    svc = get_service()
    try:
        commitments = await svc.list_commitments(person_id)
    except Exception:
        commitments = []

    def _parse(ts):
        try:
            return datetime.fromisoformat(str(ts).replace("Z", "+00:00"))
        except Exception:
            return None

    now = datetime.now(timezone.utc)
    week_ago = now - timedelta(days=7)

    overdue = []
    due_this_week = []
    for c in commitments:
        due = _parse(c.get("due_at"))
        if not due:
            continue
        if due < now and c.get("status") == "planned":
            overdue.append(c)
        if week_ago <= due <= now:
            due_this_week.append(c)
    overdue.sort(key=lambda c: c.get("due_at") or "")

    completed_week = [c for c in due_this_week if c.get("status") == "completed"]
    week = {
        "planned": len(due_this_week),
        "completed": len(completed_week),
        "completion_rate": (
            round(len(completed_week) / len(due_this_week), 2)
            if due_this_week else None
        ),
    }

    intervention = None
    if overdue:
        most = overdue[0]
        due = _parse(most.get("due_at"))
        days_overdue = max(1, (now - due).days) if due else 1
        try:
            from backend.services.execution_intelligence_agent import (
                ExecutionIntelligenceAgent,
            )
            from backend.core.execution_schemas import CanonicalAction

            action = CanonicalAction(
                person_id=person_id,
                title=most.get("title", "commitment"),
                description=most.get("title", "commitment"),
                due_at=most.get("due_at"),
            )
            iv = await ExecutionIntelligenceAgent().generate_accountability_intervention(
                person_id, action, days_overdue
            )
            intervention = iv.model_dump(mode="json")
        except Exception:
            # Deterministic fallback: same shape, no LLM needed.
            intervention = {
                "person_id": person_id,
                "action_title": most.get("title"),
                "days_overdue": days_overdue,
                "non_judgmental_message": (
                    f"'{most.get('title')}' was due earlier and is still open. "
                    "No judgment — plans slip. Pick what fits: continue today, "
                    "reschedule by a few days, or report a blocker."
                ),
                "suggested_options": [
                    "Continue with active plan (work on it today)",
                    "Reschedule deadline by 3 days",
                    "Report a blocker and explore a workaround",
                ],
            }

    return {
        "person_id": person_id,
        "checked_at": now.isoformat(),
        "overdue": [
            {"title": c.get("title"), "due_at": c.get("due_at"),
             "status": c.get("status")}
            for c in overdue
        ],
        "week_plan_vs_actual": week,
        "intervention": intervention,
    }


@router.get("/projection")
async def adaptive_projection(person_id: str = Depends(get_person_id)):
    """
    Adaptive timeline from demonstrated pace (not a generic template):
    open commitments divided by the learner's own completions-per-week over
    the trailing 28 days. Honest about sparse data — no projection without
    a measured pace, never a fabricated date.
    """
    from backend.services.trajectory_service import TrajectoryService

    svc = TrajectoryService()
    pace = await svc.pace(person_id)
    try:
        open_items = [
            c for c in await svc.commitment_service.list_commitments(person_id)
            if c.get("status") == "planned"
        ]
    except Exception:
        open_items = []
    per_week = pace.get("completions_per_week") or 0
    projected_weeks = (
        round(len(open_items) / per_week, 1) if per_week > 0 else None
    )
    if projected_weeks is None:
        note = ("No measured pace yet — complete a few commitments first and "
                "I'll project from your actual rate, not a template.")
    else:
        note = (f"At your measured pace ({per_week}/week), {len(open_items)} "
                f"open commitments project to ~{projected_weeks} weeks.")
    return {
        "person_id": person_id,
        "open_commitments": len(open_items),
        "completions_per_week_28d": per_week,
        "completion_rate_28d": pace.get("completion_rate"),
        "projected_weeks_remaining": projected_weeks,
        "note": note,
    }
