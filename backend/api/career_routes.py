from fastapi import APIRouter, Depends, HTTPException, Header, Query
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone
from backend.core.career_schemas import (
    UniversalCareerProfile,
    TargetOutcome,
    CareerGoal,
    CareerRequirementGraph,
    CareerReadinessReport,
    AccountabilityStatus,
    VerifiedOpportunity,
    VerifiedCredential,
    TailoredResume,
    CareerCheckpoint
)
from backend.services.career_readiness_engine import CareerReadinessEngine
from backend.services.opportunity_service import OpportunityService
from backend.services.store import FirestoreStore

from backend.core.security import get_authenticated_person

router = APIRouter(prefix="/api/career", tags=["Career Intelligence & Execution Layer"])
engine = CareerReadinessEngine()
opp_service = OpportunityService()
store = FirestoreStore()
get_person_id = get_authenticated_person

@router.post("/profile", response_model=UniversalCareerProfile)
async def update_career_profile(
    profile_payload: Dict[str, Any],
    person_id: str = Depends(get_person_id)
):
    try:
        active_id = profile_payload.get("person_id") or person_id
        profile_dict = profile_payload.copy()
        profile_dict["person_id"] = active_id
        profile = UniversalCareerProfile(**profile_dict)
        await store.save_career_profile(active_id, profile.model_dump(mode="json"))
        return profile
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update career profile: {str(e)}")

@router.get("/profile", response_model=UniversalCareerProfile)
async def get_career_profile(
    person_id: str = Depends(get_person_id),
    state_type: Optional[str] = Query("college_student")
):
    try:
        return await engine.get_or_create_canonical_profile(person_id, state_type or "college_student")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch career profile: {str(e)}")

@router.post("/goal", response_model=TargetOutcome)
async def set_career_goal(
    goal_payload: Dict[str, Any],
    person_id: str = Depends(get_person_id)
):
    try:
        active_id = goal_payload.get("person_id") or person_id
        existing_goal = await store.get_career_goal(active_id)
        version = (existing_goal.get("version", 1) + 1) if existing_goal else 1

        goal = TargetOutcome(
            goal_id=f"goal_{active_id}",
            person_id=active_id,
            goal_type=goal_payload.get("goal_type", "career"),
            target_role=goal_payload.get("target_role", "Applied Machine Learning Systems Engineer"),
            target_industry=goal_payload.get("target_industry", "Artificial Intelligence & Software Engineering"),
            geography=goal_payload.get("geography", "India & Global"),
            target_timeline=goal_payload.get("target_timeline", "12–18 Months"),
            priority=goal_payload.get("priority", "HIGH"),
            version=version,
            constraints=goal_payload.get("constraints", {})
        )
        await store.save_career_goal(active_id, goal.model_dump(mode="json"))
        return goal
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to set career goal: {str(e)}")

@router.get("/goal", response_model=TargetOutcome)
async def get_career_goal(
    person_id: str = Depends(get_person_id)
):
    try:
        return await engine.get_or_create_career_goal(person_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch career goal: {str(e)}")

@router.get("/requirement-graph", response_model=CareerRequirementGraph)
async def get_career_requirement_graph(
    target_role: Optional[str] = Query("Applied Machine Learning Systems Engineer"),
    person_id: str = Depends(get_person_id)
):
    try:
        profile = await engine.get_or_create_canonical_profile(person_id)
        return engine.build_requirement_graph(target_role or "Applied Machine Learning Systems Engineer", profile.skills)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch requirement graph: {str(e)}")

@router.get("/readiness", response_model=CareerReadinessReport)
async def get_career_readiness(
    current_state: Optional[str] = Query("college_student"),
    person_id: str = Depends(get_person_id)
):
    try:
        return await engine.generate_career_readiness_report(
            person_id=person_id,
            current_state_type=current_state or "college_student"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to calculate career readiness: {str(e)}")

@router.get("/readiness/history", response_model=List[Dict[str, Any]])
async def get_readiness_history(
    person_id: str = Depends(get_person_id)
):
    try:
        return await store.get_readiness_history(person_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch readiness history: {str(e)}")

@router.post("/checkpoint", response_model=CareerCheckpoint)
async def create_career_checkpoint(
    person_id: str = Depends(get_person_id)
):
    try:
        return await engine.record_career_checkpoint(person_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to record career checkpoint: {str(e)}")

@router.get("/checkpoints", response_model=List[CareerCheckpoint])
async def get_career_checkpoints(
    person_id: str = Depends(get_person_id)
):
    try:
        chks = await store.get_career_checkpoints(person_id)
        return [CareerCheckpoint(**c) for c in chks]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch checkpoints: {str(e)}")

@router.get("/opportunities", response_model=List[VerifiedOpportunity])
async def get_matched_opportunities(
    target_role: Optional[str] = Query("Machine Learning Engineer"),
    geography: Optional[str] = Query(None),
    person_id: str = Depends(get_person_id)
):
    try:
        profile = await engine.get_or_create_canonical_profile(person_id)
        return await opp_service.match_opportunities_for_person(
            profile=profile,
            target_role=target_role or "Machine Learning Engineer"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch opportunities: {str(e)}")

@router.get("/credentials", response_model=List[VerifiedCredential])
async def get_credentials_strategy(
    target_role: Optional[str] = Query("Machine Learning Engineer")
):
    try:
        return engine.credential_agent.evaluate_credentials(target_role or "Machine Learning Engineer")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch credentials strategy: {str(e)}")

@router.post("/resume/tailor", response_model=TailoredResume)
async def tailor_resume_for_role(
    payload: Dict[str, Any],
    person_id: str = Depends(get_person_id)
):
    try:
        profile = await engine.get_or_create_canonical_profile(person_id)
        target_role = payload.get("target_role", "Applied Machine Learning Systems Engineer")
        return engine.resume_agent.generate_tailored_resume(
            profile=profile,
            target_role=target_role
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate tailored resume: {str(e)}")

@router.post("/accountability/check-in", response_model=AccountabilityStatus)
async def accountability_check_in(
    checkin_payload: Dict[str, Any],
    person_id: str = Depends(get_person_id)
):
    try:
        completed = checkin_payload.get("completed_stages", 1)
        weekly_hours = checkin_payload.get("weekly_hours", 10)
        missed = checkin_payload.get("missed_milestones", 0)
        return engine.accountability_agent.evaluate_accountability(
            person_id=person_id,
            completed_stages=completed,
            total_stages=5,
            weekly_hours=weekly_hours,
            missed_milestones=missed
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to execute accountability check-in: {str(e)}")
