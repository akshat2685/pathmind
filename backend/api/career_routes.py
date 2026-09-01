from fastapi import APIRouter, Depends, HTTPException, Header, Query
from typing import List, Dict, Any, Optional
from backend.core.career_schemas import (
    CareerGoal,
    CareerReadinessReport,
    AccountabilityStatus,
    VerifiedOpportunity,
    TailoredResume
)
from backend.services.career_readiness_engine import CareerReadinessEngine
from backend.services.opportunity_service import OpportunityService
from backend.services.store import FirestoreStore

router = APIRouter(prefix="/api/career", tags=["Career Readiness & Accountability Engine"])
engine = CareerReadinessEngine()
opp_service = OpportunityService()
store = FirestoreStore()

def get_person_id(x_person_id: Optional[str] = Header(None)) -> str:
    if not x_person_id:
        return "demo-user"
    return x_person_id

@router.post("/goal", response_model=CareerGoal)
async def set_career_goal(
    goal_payload: Dict[str, Any],
    person_id: str = Depends(get_person_id)
):
    try:
        active_person_id = goal_payload.get("person_id") or person_id
        goal = CareerGoal(
            goal_id=f"goal_{active_person_id}",
            person_id=active_person_id,
            target_role=goal_payload.get("target_role", "Applied Machine Learning Systems Engineer"),
            target_industry=goal_payload.get("target_industry", "Artificial Intelligence & Software Engineering"),
            geography=goal_payload.get("geography", "India & Global"),
            target_timeline=goal_payload.get("target_timeline", "12–18 Months"),
            priority=goal_payload.get("priority", "HIGH"),
            constraints=goal_payload.get("constraints", {})
        )
        await store.save_career_goal(active_person_id, goal.model_dump(mode="json"))
        return goal
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to set career goal: {str(e)}")

@router.get("/readiness", response_model=CareerReadinessReport)
async def get_career_readiness(
    current_state: Optional[str] = Query("college_student"),
    person_id: str = Depends(get_person_id)
):
    try:
        report = await engine.generate_career_readiness_report(
            person_id=person_id,
            current_state=current_state or "college_student"
        )
        return report
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to calculate career readiness: {str(e)}")

@router.post("/accountability/check-in", response_model=AccountabilityStatus)
async def accountability_check_in(
    checkin_payload: Dict[str, Any],
    person_id: str = Depends(get_person_id)
):
    try:
        completed = checkin_payload.get("completed_stages", 1)
        weekly_hours = checkin_payload.get("weekly_hours", 10)
        return engine.evaluate_accountability(
            person_id=person_id,
            completed_stages=completed,
            weekly_hours=weekly_hours
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to execute accountability check-in: {str(e)}")

@router.get("/opportunities", response_model=List[VerifiedOpportunity])
async def get_matched_opportunities(
    target_role: Optional[str] = Query("Machine Learning Engineer"),
    person_id: str = Depends(get_person_id)
):
    try:
        return opp_service.match_opportunities_for_person(
            skills_held=["Python", "Linear Algebra", "Git", "Pytest", "Data Structures"],
            target_role=target_role or "Machine Learning Engineer"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch opportunities: {str(e)}")

@router.post("/resume/tailor", response_model=TailoredResume)
async def tailor_resume_for_role(
    payload: Dict[str, Any],
    person_id: str = Depends(get_person_id)
):
    try:
        target_role = payload.get("target_role", "Applied Machine Learning Systems Engineer")
        skills = payload.get("verified_skills", ["Python 3.12", "Pytest", "Linear Algebra", "Dataclasses", "Git"])
        return engine.generate_tailored_resume(
            person_id=person_id,
            target_role=target_role,
            verified_skills=skills,
            projects=[]
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate tailored resume: {str(e)}")
