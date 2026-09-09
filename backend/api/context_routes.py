from fastapi import APIRouter, Depends, HTTPException, Header
from typing import List, Dict, Any, Optional
from pydantic import BaseModel
from backend.core.context_schemas import (
    PersonalContextGraph,
    CommandCenterOverview,
    DecisionRecord,
    ContextConflict
)
from backend.services.context_graph_service import ContextGraphService
from backend.services.decision_intelligence_service import DecisionIntelligenceService

router = APIRouter(prefix="/api/context", tags=["Personal Context Graph & Decision Intelligence"])
context_service = ContextGraphService()
decision_service = DecisionIntelligenceService(context_service=context_service)

from backend.core.security import get_authenticated_person
get_person_id = get_authenticated_person

class RecordDecisionRequest(BaseModel):
    decision_type: str
    title: str
    user_choice: str
    alternatives_considered: Optional[List[str]] = []
    supporting_evidence_ids: Optional[List[str]] = []

class RecordOutcomeRequest(BaseModel):
    outcome_state: str  # POSITIVE, NEGATIVE, MIXED, SUPERSEDED
    outcome_note: str

@router.get("/graph", response_model=PersonalContextGraph)
async def get_personal_context_graph(person_id: str = Depends(get_person_id)):
    try:
        return await context_service.assemble_context_graph(person_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to assemble context graph: {str(e)}")

@router.get("/command-center", response_model=CommandCenterOverview)
async def get_command_center(person_id: str = Depends(get_person_id)):
    try:
        return await decision_service.get_command_center_overview(person_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate command center overview: {str(e)}")

@router.post("/decisions", response_model=DecisionRecord)
async def record_decision(
    req: RecordDecisionRequest,
    person_id: str = Depends(get_person_id)
):
    try:
        return await decision_service.record_user_decision(
            person_id=person_id,
            decision_type=req.decision_type,
            title=req.title,
            user_choice=req.user_choice,
            alternatives=req.alternatives_considered or [],
            supporting_evidence_ids=req.supporting_evidence_ids or []
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to record decision: {str(e)}")

@router.get("/decisions", response_model=List[DecisionRecord])
async def get_decisions(person_id: str = Depends(get_person_id)):
    try:
        raw = await context_service.store.get_decision_records(person_id)
        return [DecisionRecord(**d) for d in raw]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve decisions: {str(e)}")

@router.post("/decisions/{decision_id}/outcome")
async def record_decision_outcome(
    decision_id: str,
    req: RecordOutcomeRequest,
    person_id: str = Depends(get_person_id)
):
    try:
        success = await decision_service.record_decision_outcome(
            person_id=person_id,
            decision_id=decision_id,
            outcome_state=req.outcome_state,
            outcome_note=req.outcome_note
        )
        if not success:
            raise HTTPException(status_code=404, detail="Decision record not found.")
        return {"status": "SUCCESS", "message": "Decision outcome recorded."}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to record decision outcome: {str(e)}")

@router.get("/conflicts", response_model=List[ContextConflict])
async def get_conflicts(person_id: str = Depends(get_person_id)):
    try:
        raw = await context_service.store.get_context_conflicts(person_id)
        return [ContextConflict(**c) for c in raw]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve context conflicts: {str(e)}")
