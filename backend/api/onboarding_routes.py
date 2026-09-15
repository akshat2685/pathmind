from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional
from backend.core.person_schemas import PersonProfile
from backend.core.assessment_schemas import AssessmentBlueprint
from backend.services.store import FirestoreStore
from backend.services.goal_assessment_service import GoalAssessmentService
from backend.core.security import get_authenticated_person

router = APIRouter(prefix="/api/onboarding", tags=["Onboarding"])
store = FirestoreStore()
goal_engine = GoalAssessmentService()
get_person_id = get_authenticated_person

class OnboardingProfileRequest(BaseModel):
    learner_stage: str
    aspiration: str
    domain: Optional[str] = "General"
    evidence_summary: Optional[str] = None

@router.post("/profile", response_model=AssessmentBlueprint)
async def submit_profile(
    req: OnboardingProfileRequest,
    person_id: str = Depends(get_person_id)
):
    try:
        # Create and save canonical profile
        profile = PersonProfile(
            person_id=person_id,
            learner_stage=req.learner_stage,
            aspiration=req.aspiration,
            domain=req.domain,
            evidence_summary=req.evidence_summary
        )
        await store.save_person_profile(person_id, profile.model_dump())

        # Generate stage-aware assessment blueprint
        blueprint = goal_engine.generate_assessment_blueprint(profile)
        
        # Save blueprint
        await store.save_assessment_blueprint(person_id, blueprint.id, blueprint.model_dump())
        
        return blueprint
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to process onboarding profile: {str(e)}")
