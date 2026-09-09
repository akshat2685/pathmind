from fastapi import APIRouter, Depends, HTTPException, Header, Query
from typing import List, Dict, Any, Optional
from pydantic import BaseModel
from backend.core.adaptation_schemas import (
    ContinuousIntelligenceState,
    ProposedAdaptation,
    UserAdaptationDecision,
    AdaptationAuditRecord,
    PauseResumeAnalysis,
    ConflictDetectionResult
)
from backend.services.adaptation_service import AdaptationService

router = APIRouter(prefix="/api/adaptation", tags=["Continuous Intelligence & Adaptive Replanning"])
adaptation_service = AdaptationService()

from backend.core.security import get_authenticated_person
get_person_id = get_authenticated_person

class GoalChangeRequest(BaseModel):
    new_target_role: str
    target_industry: Optional[str] = "Applied AI & Tech"
    geography: Optional[str] = "Global / India"
    target_timeline: Optional[str] = "6–9 Months"

class ConstraintChangeRequest(BaseModel):
    weekly_hours: int
    preferred_format: Optional[str] = "project-based"

class OpportunityEventRequest(BaseModel):
    opportunity_id: str
    opportunity_title: str
    organization: str
    required_milestones: List[str]

@router.get("/state", response_model=ContinuousIntelligenceState)
async def get_continuous_intelligence_state(person_id: str = Depends(get_person_id)):
    try:
        return await adaptation_service.get_continuous_intelligence_state(person_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve continuous intelligence state: {str(e)}")

@router.post("/goal-change", response_model=ProposedAdaptation)
async def request_goal_change(
    req: GoalChangeRequest,
    person_id: str = Depends(get_person_id)
):
    try:
        return await adaptation_service.handle_goal_change(
            person_id=person_id,
            new_target_role=req.new_target_role,
            target_industry=req.target_industry,
            geography=req.geography,
            target_timeline=req.target_timeline
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to process goal change: {str(e)}")

@router.post("/constraint-change", response_model=ProposedAdaptation)
async def request_constraint_change(
    req: ConstraintChangeRequest,
    person_id: str = Depends(get_person_id)
):
    try:
        return await adaptation_service.handle_constraint_change(
            person_id=person_id,
            weekly_hours=req.weekly_hours,
            preferred_format=req.preferred_format
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to process constraint change: {str(e)}")

@router.post("/opportunity-event", response_model=ProposedAdaptation)
async def request_opportunity_adaptation(
    req: OpportunityEventRequest,
    person_id: str = Depends(get_person_id)
):
    try:
        return await adaptation_service.handle_opportunity_event(
            person_id=person_id,
            opportunity_id=req.opportunity_id,
            opportunity_title=req.opportunity_title,
            organization=req.organization,
            required_milestones=req.required_milestones
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to process opportunity event: {str(e)}")

@router.get("/pending", response_model=List[ProposedAdaptation])
async def get_pending_adaptations(person_id: str = Depends(get_person_id)):
    try:
        raw = await adaptation_service.store.get_pending_adaptations(person_id)
        return [ProposedAdaptation(**p) for p in raw]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve pending adaptations: {str(e)}")

@router.post("/decide", response_model=Dict[str, Any])
async def decide_adaptation(
    decision: UserAdaptationDecision,
    person_id: str = Depends(get_person_id)
):
    try:
        active_person_id = decision.person_id or person_id
        decision.person_id = active_person_id
        return await adaptation_service.decide_adaptation(active_person_id, decision)
    except ValueError as ve:
        raise HTTPException(status_code=404, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to resolve adaptation decision: {str(e)}")

@router.get("/history", response_model=List[AdaptationAuditRecord])
async def get_adaptation_history(person_id: str = Depends(get_person_id)):
    try:
        raw = await adaptation_service.store.get_adaptation_audits(person_id)
        return [AdaptationAuditRecord(**a) for a in raw]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve adaptation audit history: {str(e)}")

@router.get("/pause-status", response_model=PauseResumeAnalysis)
async def get_pause_status(person_id: str = Depends(get_person_id)):
    try:
        return await adaptation_service.state_change_service.analyze_pause_and_resume(person_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to analyze pause status: {str(e)}")

@router.get("/conflict-check", response_model=ConflictDetectionResult)
async def check_evidence_conflicts(
    claimed_skill: str = Query("Python", description="Skill to check against evidence"),
    person_id: str = Depends(get_person_id)
):
    try:
        return await adaptation_service.state_change_service.detect_evidence_conflict(person_id, claimed_skill)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to perform conflict check: {str(e)}")
