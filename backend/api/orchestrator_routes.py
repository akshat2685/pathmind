from fastapi import APIRouter, Depends, HTTPException, Header, Query
from typing import List, Dict, Any, Optional

from backend.core.orchestration_schemas import (
    AgentContract,
    ActionProposal,
    OrchestrationTrace,
    OrchestrationRequest,
    OrchestrationResponse
)
from backend.services.pathmind_orchestrator import PathmindOrchestrator
from backend.services.store import FirestoreStore

from backend.core.security import get_authenticated_person

router = APIRouter(prefix="/api/orchestrate", tags=["Unified Agent Orchestration & Control Tower"])
store = FirestoreStore()
orchestrator = PathmindOrchestrator(store=store)
get_person_id = get_authenticated_person

@router.post("", response_model=OrchestrationResponse)
async def execute_orchestrated_task(
    request: OrchestrationRequest,
    person_id: str = Depends(get_person_id)
):
    try:
        return await orchestrator.orchestrate(person_id=person_id, request=request)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Orchestration failure: {str(e)}")

@router.get("/agents", response_model=List[AgentContract])
async def list_agent_registry():
    return orchestrator.get_agent_registry()

@router.get("/traces", response_model=List[OrchestrationTrace])
async def get_recent_traces(
    person_id: str = Depends(get_person_id)
):
    try:
        raw_traces = await store.get_orchestration_traces(person_id)
        return [OrchestrationTrace(**t) for t in raw_traces]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch orchestration traces: {str(e)}")

@router.get("/traces/{workflow_id}", response_model=OrchestrationTrace)
async def get_workflow_trace(
    workflow_id: str,
    person_id: str = Depends(get_person_id)
):
    trace_dict = await store.get_orchestration_trace(person_id, workflow_id)
    if not trace_dict:
        raise HTTPException(status_code=404, detail=f"Workflow trace {workflow_id} not found.")
    return OrchestrationTrace(**trace_dict)

@router.get("/proposals", response_model=List[ActionProposal])
async def list_action_proposals(
    status: Optional[str] = Query(None),
    person_id: str = Depends(get_person_id)
):
    try:
        raw_props = await store.get_action_proposals(person_id, status=status)
        return [ActionProposal(**p) for p in raw_props]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch action proposals: {str(e)}")

@router.post("/proposals/{proposal_id}/approve")
async def approve_proposal(
    proposal_id: str,
    person_id: str = Depends(get_person_id)
):
    try:
        return await orchestrator.approve_action_proposal(person_id, proposal_id)
    except ValueError as ve:
        raise HTTPException(status_code=404, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to approve proposal: {str(e)}")

@router.post("/proposals/{proposal_id}/reject")
async def reject_proposal(
    proposal_id: str,
    person_id: str = Depends(get_person_id)
):
    try:
        return await orchestrator.reject_action_proposal(person_id, proposal_id)
    except ValueError as ve:
        raise HTTPException(status_code=404, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to reject proposal: {str(e)}")
