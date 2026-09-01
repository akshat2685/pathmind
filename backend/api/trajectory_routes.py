from fastapi import APIRouter, Depends, HTTPException, Header
from typing import List, Dict, Any, Optional
from backend.core.trajectory_schemas import (
    DiscoveryRequest,
    DiscoveryResponse,
    CounterfactualRequest,
    CounterfactualResponse,
    PathSelectionRecord,
    CandidatePath,
    TrajectoryCase,
    TrajectoryPattern
)
from backend.core.assessment_schemas import CounselingProfile
from backend.services.store import FirestoreStore
from backend.services.trajectory_engine import TrajectoryEngine
from backend.services.trajectory_corpus import TrajectoryCorpusService

router = APIRouter(prefix="/api/trajectories", tags=["Trajectory Discovery"])
store = FirestoreStore()
engine = TrajectoryEngine()
corpus_service = TrajectoryCorpusService()

def get_person_id(x_person_id: Optional[str] = Header(None)) -> str:
    if not x_person_id:
        return "demo-user"
    return x_person_id

@router.post("/discover", response_model=DiscoveryResponse)
async def discover_candidate_paths(
    req: Optional[DiscoveryRequest] = None,
    person_id: str = Depends(get_person_id)
):
    try:
        active_person_id = (req.person_id if req and req.person_id else None) or person_id
        goals = req.goals if req and req.goals else ["Explore AI/ML and Engineering"]
        constraints = req.constraints if req and req.constraints else []
        geo_pref = req.geographic_preference if req and req.geographic_preference else "India & Global"

        # Retrieve stored counseling profile if available
        profile_data = await store.get_counseling_profile(active_person_id)
        counseling_profile = CounselingProfile(**profile_data) if profile_data else None

        response = await engine.discover_candidate_paths(
            person_id=active_person_id,
            counseling_profile=counseling_profile,
            goals=goals,
            constraints=constraints,
            geographic_preference=geo_pref
        )

        return response
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to discover candidate paths: {str(e)}")

@router.post("/select", response_model=PathSelectionRecord)
async def select_candidate_path(
    selection: PathSelectionRecord,
    person_id: str = Depends(get_person_id)
):
    try:
        active_person_id = selection.person_id or person_id
        selection.person_id = active_person_id
        
        # Persist versioned selection
        version = await store.save_selected_path(active_person_id, selection.model_dump(mode="json"))
        selection.version = version
        
        return selection
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save path selection: {str(e)}")

@router.get("/active", response_model=Optional[PathSelectionRecord])
async def get_active_path(person_id: str = Depends(get_person_id)):
    active_data = await store.get_active_selected_path(person_id)
    if not active_data:
        return None
    return PathSelectionRecord(**active_data)

@router.get("/history", response_model=List[PathSelectionRecord])
async def get_path_history(person_id: str = Depends(get_person_id)):
    history_data = await store.get_path_selection_history(person_id)
    return [PathSelectionRecord(**h) for h in history_data]

@router.post("/counterfactual", response_model=CounterfactualResponse)
async def counterfactual_exploration(
    req: CounterfactualRequest,
    person_id: str = Depends(get_person_id)
):
    try:
        active_person_id = req.person_id or person_id
        
        # Discover base paths
        discovery = await engine.discover_candidate_paths(person_id=active_person_id)
        base_path = next((p for p in discovery.candidate_paths if p.path_id == req.base_path_id), None)
        
        if not base_path and discovery.candidate_paths:
            base_path = discovery.candidate_paths[0]
            
        if not base_path:
            raise HTTPException(status_code=404, detail="Base candidate path not found")

        response = engine.generate_counterfactual_path(
            base_path=base_path,
            modification_type=req.modification_type,
            modification_prompt=req.modification_prompt
        )

        return response
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Counterfactual generation failed: {str(e)}")

@router.get("/corpus", response_model=Dict[str, Any])
async def get_trajectory_corpus():
    """
    Returns the attributed trajectory corpus and empirical cross-trajectory patterns.
    """
    return {
        "trajectories": [t.model_dump() for t in corpus_service.get_all_trajectories()],
        "patterns": [p.model_dump() for p in corpus_service.get_all_patterns()],
        "source_type": "ATTRIBUTED_EMPIRICAL_CORPUS"
    }
