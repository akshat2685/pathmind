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

# =============================================================================
# Continuous Guided Journey Routes (State Machine Endpoints)
# =============================================================================

from pydantic import BaseModel

class InitJourneyRequest(BaseModel):
    name: str

class AspirationRequest(BaseModel):
    aspiration: str
    stage: str
    constraints: Optional[List[str]] = []

class EvidenceSubmissionRequest(BaseModel):
    evidence: List[Dict[str, Any]]

class AssessmentSubmissionRequest(BaseModel):
    responses: List[Dict[str, Any]]

class SelectPathRequest(BaseModel):
    selected_path_id: str

class PhaseEvidenceRequest(BaseModel):
    stage_id: str
    mission_id: str
    content_payload: Dict[str, Any]

@router.post("/journey/init")
async def init_journey(request: InitJourneyRequest):
    """
    Requirement 3: Canonical person ID created immediately after name collection.
    Persists initial learner record.
    """
    try:
        return await orchestrator.init_journey(name=request.name)
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to initialize journey: {str(e)}")

@router.get("/journey/state")
async def get_journey_state(person_id: str = Depends(get_person_id)):
    """
    Retrieves the persisted continuous journey state for the authenticated learner.
    """
    try:
        return await orchestrator.get_journey_state(person_id=person_id)
    except ValueError as ve:
        raise HTTPException(status_code=404, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch journey state: {str(e)}")

@router.post("/journey/aspiration")
async def record_aspiration(
    request: AspirationRequest,
    person_id: str = Depends(get_person_id)
):
    """
    Records aspiration and learner stage, returns grounded evidence requirements.
    """
    try:
        return await orchestrator.record_aspiration_and_stage(
            person_id=person_id,
            aspiration=request.aspiration,
            stage=request.stage,
            constraints=request.constraints
        )
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to record aspiration: {str(e)}")

@router.post("/journey/evidence")
async def submit_evidence(
    request: EvidenceSubmissionRequest,
    person_id: str = Depends(get_person_id)
):
    """
    Submits evidence, evaluates gaps, and generates domain-neutral assessment blueprint.
    """
    try:
        return await orchestrator.submit_evidence_and_generate_blueprint(
            person_id=person_id,
            evidence_items=request.evidence
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to process evidence: {str(e)}")

@router.post("/journey/assessment")
async def submit_assessment(
    request: AssessmentSubmissionRequest,
    person_id: str = Depends(get_person_id)
):
    """
    Submits actual answers, computes objective evaluation, and builds verified baseline profile.
    """
    try:
        return await orchestrator.submit_assessment_and_generate_baseline(
            person_id=person_id,
            responses=request.responses
        )
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to evaluate assessment: {str(e)}")

@router.post("/journey/discover-paths")
async def discover_pathways(person_id: str = Depends(get_person_id)):
    """
    Discovers 2-3 transparent candidate pathways grounded in empirical trajectories.
    """
    try:
        return await orchestrator.discover_pathways(person_id=person_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to discover pathways: {str(e)}")

@router.post("/journey/select-path")
async def select_pathway(
    request: SelectPathRequest,
    person_id: str = Depends(get_person_id)
):
    """
    Saves chosen pathway and generates multi-phase hidden roadmap with Active Phase 1.
    """
    try:
        return await orchestrator.select_pathway_and_init_roadmap(
            person_id=person_id,
            selected_path_id=request.selected_path_id
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to select pathway: {str(e)}")

@router.get("/journey/roadmap")
async def get_roadmap(person_id: str = Depends(get_person_id)):
    """
    Retrieves progressive disclosed roadmap view.
    """
    try:
        return await orchestrator.get_active_disclosed_roadmap(person_id=person_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch roadmap: {str(e)}")

@router.post("/journey/submit-phase-evidence")
async def submit_phase_evidence(
    request: PhaseEvidenceRequest,
    person_id: str = Depends(get_person_id)
):
    """
    Requirement 10: Evidence-gated phase progression.
    Deterministic backend decides PASS / REINFORCE / INSUFFICIENT_EVIDENCE.
    """
    try:
        return await orchestrator.submit_phase_evidence(
            person_id=person_id,
            stage_id=request.stage_id,
            mission_id=request.mission_id,
            content_payload=request.content_payload
        )
    except PermissionError as pe:
        raise HTTPException(status_code=403, detail=str(pe))
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Evidence verification failure: {str(e)}")

