from fastapi import APIRouter, Depends, HTTPException, Header
from typing import List, Dict, Any, Optional
from backend.core.roadmap_schemas import (
    Roadmap,
    DisclosedRoadmapView,
    Stage,
    EvidenceSubmission,
    EvaluationResult,
    PersonalAgentModel,
    AdaptConstraintRequest
)
from backend.services.roadmap_engine import RoadmapEngine
from backend.services.personal_agent_engine import PersonalAgentEngine
from backend.services.store import FirestoreStore

router = APIRouter(prefix="/api/roadmap", tags=["Progressive Roadmap & Adaptive Learning"])
engine = RoadmapEngine()
personal_agent = PersonalAgentEngine()
store = FirestoreStore()

def get_person_id(x_person_id: Optional[str] = Header(None)) -> str:
    if not x_person_id:
        return "demo-user"
    return x_person_id

@router.post("/generate", response_model=DisclosedRoadmapView)
async def generate_roadmap(
    path_id: Optional[str] = "path_applied_ai_ml_systems",
    person_id: str = Depends(get_person_id)
):
    try:
        roadmap = await engine.get_or_create_roadmap(person_id=person_id, path_id=path_id)
        # Check for cross-stage memory
        active_stage = next((s for s in engine.get_all_stages_flat(roadmap) if s.stage_id == roadmap.current_stage_id), None)
        memory_moment = None
        if active_stage:
            memory_moment = await personal_agent.retrieve_cross_stage_memory(person_id, active_stage.title)

        return engine.build_disclosed_view(
            roadmap=roadmap,
            personal_agent_note="Roadmap synthesized with evidence-gated stage progression.",
            memory_moment=memory_moment
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate roadmap: {str(e)}")

@router.get("/current", response_model=DisclosedRoadmapView)
async def get_current_roadmap_view(person_id: str = Depends(get_person_id)):
    try:
        roadmap = await engine.get_or_create_roadmap(person_id=person_id)
        active_stage = next((s for s in engine.get_all_stages_flat(roadmap) if s.stage_id == roadmap.current_stage_id), None)
        memory_moment = None
        if active_stage:
            memory_moment = await personal_agent.retrieve_cross_stage_memory(person_id, active_stage.title)

        return engine.build_disclosed_view(
            roadmap=roadmap,
            personal_agent_note="Active stage is unlocked. Complete mission evidence to unlock subsequent stages.",
            memory_moment=memory_moment
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve current roadmap: {str(e)}")

@router.get("/stage/{stage_id}", response_model=Stage)
async def get_protected_stage(
    stage_id: str,
    person_id: str = Depends(get_person_id)
):
    """
    Backend Lock Enforcement:
    Rejects access if stage is locked and not currently active.
    """
    roadmap = await engine.get_or_create_roadmap(person_id=person_id)
    flat_stages = engine.get_all_stages_flat(roadmap)
    target = next((s for s in flat_stages if s.stage_id == stage_id), None)
    
    if not target:
        raise HTTPException(status_code=404, detail="Stage not found")
        
    if target.locked and target.stage_id != roadmap.current_stage_id:
        raise HTTPException(
            status_code=403,
            detail="UNLOCK_REJECTED: Stage is locked. You must satisfy prerequisites and submit passing evidence for preceding stages."
        )

    return target

@router.post("/evidence/submit", response_model=EvaluationResult)
async def submit_evidence(
    submission: EvidenceSubmission,
    person_id: str = Depends(get_person_id)
):
    try:
        active_person_id = submission.person_id or person_id
        submission.person_id = active_person_id
        result = await engine.evaluate_evidence_and_progress(active_person_id, submission)
        return result
    except PermissionError as pe:
        raise HTTPException(status_code=403, detail=str(pe))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Evidence evaluation failed: {str(e)}")

@router.post("/adapt/constraints", response_model=DisclosedRoadmapView)
async def adapt_constraints(
    req: AdaptConstraintRequest,
    person_id: str = Depends(get_person_id)
):
    try:
        active_person_id = req.person_id or person_id
        req.person_id = active_person_id
        updated_roadmap = await engine.adapt_constraints(active_person_id, req)
        return engine.build_disclosed_view(
            roadmap=updated_roadmap,
            personal_agent_note=f"Roadmap adapted to {req.weekly_hours or 'custom'} hours/week pacing while preserving all completed work."
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Constraint adaptation failed: {str(e)}")

@router.get("/personal-agent", response_model=PersonalAgentModel)
async def get_personal_agent_model(person_id: str = Depends(get_person_id)):
    try:
        model = await personal_agent.get_or_create_agent_model(person_id)
        return model
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve personal agent model: {str(e)}")

@router.get("/history", response_model=List[Dict[str, Any]])
async def get_roadmap_history(person_id: str = Depends(get_person_id)):
    try:
        return await store.get_roadmap_history(person_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve roadmap history: {str(e)}")
