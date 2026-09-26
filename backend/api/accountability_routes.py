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
