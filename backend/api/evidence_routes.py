from fastapi import APIRouter, Depends, HTTPException, Header, Query
from typing import List, Dict, Any, Optional
from pydantic import BaseModel
from backend.core.evidence_schemas import (
    CanonicalEvidence,
    EvaluationAttempt,
    EvidenceDispute,
    SkillMasteryProfile,
    MasteryDashboardState
)
from backend.services.mastery_engine import MasteryEngine

from backend.core.security import get_authenticated_person

router = APIRouter(prefix="/api/evidence", tags=["Evidence & Mastery Engine"])
mastery_engine = MasteryEngine()
get_person_id = get_authenticated_person

class EvidenceSubmissionRequest(BaseModel):
    stage_id: str
    evidence_type: Optional[str] = "CODE_REPO"
    title: str
    source_reference: str
    payload: Dict[str, Any]
    is_transfer_task: Optional[bool] = False

class DisputeRequest(BaseModel):
    attempt_id: str
    reason: str
    additional_evidence_reference: Optional[str] = None

@router.post("/submit", response_model=EvaluationAttempt)
async def submit_evidence(
    req: EvidenceSubmissionRequest,
    person_id: str = Depends(get_person_id)
):
    try:
        return await mastery_engine.submit_and_evaluate_evidence(
            person_id=person_id,
            stage_id=req.stage_id,
            evidence_type=req.evidence_type or "CODE_REPO",
            title=req.title,
            source_reference=req.source_reference,
            payload=req.payload,
            is_transfer_task=bool(req.is_transfer_task)
        )
    except PermissionError as pe:
        raise HTTPException(status_code=403, detail=str(pe))
    except ValueError as ve:
        raise HTTPException(status_code=404, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Evidence submission failed: {str(e)}")

@router.get("/dashboard", response_model=MasteryDashboardState)
async def get_mastery_dashboard(person_id: str = Depends(get_person_id)):
    try:
        return await mastery_engine.get_mastery_dashboard_state(person_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to load mastery dashboard: {str(e)}")

@router.get("/history", response_model=List[EvaluationAttempt])
async def get_evaluation_history(
    stage_id: Optional[str] = Query(None),
    person_id: str = Depends(get_person_id)
):
    try:
        raw = await mastery_engine.store.get_evaluation_attempts(person_id, stage_id)
        return [EvaluationAttempt(**a) for a in raw]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve evaluation history: {str(e)}")

@router.post("/dispute", response_model=EvidenceDispute)
async def dispute_evaluation(
    req: DisputeRequest,
    person_id: str = Depends(get_person_id)
):
    try:
        return await mastery_engine.file_dispute(
            person_id=person_id,
            attempt_id=req.attempt_id,
            reason=req.reason,
            additional_evidence_reference=req.additional_evidence_reference
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to submit evaluation dispute: {str(e)}")

@router.get("/skills", response_model=List[SkillMasteryProfile])
async def get_verified_skills(person_id: str = Depends(get_person_id)):
    try:
        profiles = await mastery_engine.store.get_skill_mastery_profiles(person_id)
        return [SkillMasteryProfile(**p) for p in profiles.values()]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve verified skills: {str(e)}")
