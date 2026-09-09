from fastapi import APIRouter, Depends, HTTPException, Header, Query
from typing import List, Dict, Any, Optional

from backend.core.execution_schemas import (
    CanonicalAction,
    DailyExecutionPlan,
    AccountabilityIntervention,
    OpportunityApplicationTracker,
    CreateActionRequest,
    RescheduleActionRequest,
    BlockActionRequest,
    CompleteActionRequest,
    PauseExecutionRequest,
    TrackApplicationRequest
)
from backend.services.execution_engine import ExecutionEngine

from backend.core.security import get_authenticated_person

router = APIRouter(prefix="/api/execution", tags=["Execution Engine & Action Tracking"])
execution_engine = ExecutionEngine()
get_person_id = get_authenticated_person

@router.get("/daily", response_model=DailyExecutionPlan)
async def get_daily_plan(person_id: str = Depends(get_person_id)):
    try:
        return await execution_engine.get_daily_execution_plan(person_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to load daily execution plan: {str(e)}")

@router.get("/actions", response_model=List[CanonicalAction])
async def list_actions(
    stage_id: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    person_id: str = Depends(get_person_id)
):
    try:
        raw = await execution_engine.store.get_person_actions(person_id, stage_id=stage_id, status=status)
        return [CanonicalAction(**a) for a in raw]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list actions: {str(e)}")

@router.post("/actions", response_model=CanonicalAction)
async def create_action(
    req: CreateActionRequest,
    person_id: str = Depends(get_person_id)
):
    try:
        return await execution_engine.create_user_action(person_id, req)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create action: {str(e)}")

@router.post("/actions/{action_id}/start", response_model=CanonicalAction)
async def start_action(
    action_id: str,
    person_id: str = Depends(get_person_id)
):
    try:
        return await execution_engine.start_action(person_id, action_id)
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to start action: {str(e)}")

@router.post("/actions/{action_id}/complete", response_model=CanonicalAction)
async def complete_action(
    action_id: str,
    req: CompleteActionRequest,
    person_id: str = Depends(get_person_id)
):
    try:
        return await execution_engine.complete_action(person_id, action_id, req)
    except ValueError as ve:
        raise HTTPException(status_code=404, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to complete action: {str(e)}")

@router.post("/actions/{action_id}/reschedule", response_model=CanonicalAction)
async def reschedule_action(
    action_id: str,
    req: RescheduleActionRequest,
    person_id: str = Depends(get_person_id)
):
    try:
        return await execution_engine.reschedule_action(person_id, action_id, req.new_due_at, req.reason)
    except ValueError as ve:
        raise HTTPException(status_code=404, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to reschedule action: {str(e)}")

@router.post("/actions/{action_id}/block", response_model=CanonicalAction)
async def block_action(
    action_id: str,
    req: BlockActionRequest,
    person_id: str = Depends(get_person_id)
):
    try:
        return await execution_engine.block_action(person_id, action_id, req.blocker_type, req.description, req.workaround)
    except ValueError as ve:
        raise HTTPException(status_code=404, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to block action: {str(e)}")

@router.post("/actions/{action_id}/resolve-blocker", response_model=CanonicalAction)
async def resolve_blocker(
    action_id: str,
    person_id: str = Depends(get_person_id)
):
    try:
        return await execution_engine.resolve_blocker(person_id, action_id)
    except ValueError as ve:
        raise HTTPException(status_code=404, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to resolve blocker: {str(e)}")

@router.post("/pause")
async def pause_execution(
    req: PauseExecutionRequest,
    person_id: str = Depends(get_person_id)
):
    try:
        return await execution_engine.pause_execution(person_id, req.reason)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to pause execution: {str(e)}")

@router.post("/resume")
async def resume_execution(person_id: str = Depends(get_person_id)):
    try:
        return await execution_engine.resume_execution(person_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to resume execution: {str(e)}")

@router.get("/accountability", response_model=List[AccountabilityIntervention])
async def get_accountability(person_id: str = Depends(get_person_id)):
    try:
        return await execution_engine.get_accountability_status(person_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get accountability status: {str(e)}")

@router.get("/applications", response_model=List[OpportunityApplicationTracker])
async def list_applications(person_id: str = Depends(get_person_id)):
    try:
        raw = await execution_engine.store.get_opportunity_applications(person_id)
        return [OpportunityApplicationTracker(**a) for a in raw]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list applications: {str(e)}")

@router.post("/applications", response_model=OpportunityApplicationTracker)
async def track_application(
    req: TrackApplicationRequest,
    person_id: str = Depends(get_person_id)
):
    try:
        return await execution_engine.track_opportunity_application(
            person_id=person_id,
            opp_id=req.opportunity_id,
            opp_title=req.opportunity_title,
            organization=req.organization,
            status=req.status,
            notes=req.notes
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to track application: {str(e)}")
