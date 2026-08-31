from fastapi import APIRouter, Depends, HTTPException, Header
from typing import List
from backend.core.assessment_schemas import CounselingProfile
from backend.services.store import FirestoreStore
from backend.services.counseling import CounselingAgent

router = APIRouter(prefix="/api/counseling", tags=["Counseling"])
store = FirestoreStore()
agent = CounselingAgent()

def get_person_id(x_person_id: str = Header(None)) -> str:
    if not x_person_id:
        raise HTTPException(status_code=400, detail="X-Person-ID header is required")
    return x_person_id

@router.post("/synthesize", response_model=CounselingProfile)
async def synthesize_profile(person_id: str = Depends(get_person_id)):
    try:
        # Fetch all assessment results for this person
        results = await store.get_assessment_results(person_id)
        if not results:
            raise HTTPException(status_code=404, detail="No assessment results found for this person.")
        
        # Convert dicts back to AssessmentResult objects
        from backend.core.assessment_schemas import AssessmentResult
        parsed_results = [AssessmentResult(**r) for r in results]
        
        # We can add mock background context here. 
        # In a real system, this would come from the person's onboarding profile.
        background_context = "12th-grade student interested in technology, previously stated low interest in programming but has 3 tech projects."
        
        profile = agent.synthesize_profile(person_id, parsed_results, background_context)
        
        # Optionally persist the generated profile
        
        return profile
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to synthesize profile: {str(e)}")
