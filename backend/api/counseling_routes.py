from fastapi import APIRouter, Depends, HTTPException, Header
from typing import List
from backend.core.assessment_schemas import CounselingProfile
from backend.services.store import FirestoreStore
from backend.services.counseling import CounselingAgent

router = APIRouter(prefix="/api/counseling", tags=["Counseling"])
store = FirestoreStore()
agent = CounselingAgent()

from pydantic import BaseModel
from typing import Optional, Any

class SynthesizeRequest(BaseModel):
    person_id: Optional[str] = "demo-user"
    goals: Optional[List[str]] = []
    constraints: Optional[List[str]] = []
    evidence: Optional[List[Dict[str, Any]]] = []
    assessment_results: Optional[List[Dict[str, Any]]] = []

def get_person_id(x_person_id: Optional[str] = Header(None)) -> Optional[str]:
    return x_person_id

@router.post("/synthesize", response_model=CounselingProfile)
async def synthesize_profile(
    body: Optional[SynthesizeRequest] = None,
    x_person_id: Optional[str] = Header(None)
):
    try:
        person_id = x_person_id or (body.person_id if body else None) or "demo-user"
        
        # Check if inline assessment results were provided in the request body
        if body and body.assessment_results and len(body.assessment_results) > 0:
            from backend.core.assessment_schemas import AssessmentResult, AssessmentResponse
            parsed_results = []
            for r in body.assessment_results:
                raw_resp = [
                    AssessmentResponse(item_id=str(k), response_value=v, timestamp="2026-08-31T00:00:00Z")
                    for k, v in r.get("raw_responses", {}).items()
                ] if isinstance(r.get("raw_responses"), dict) else []
                
                parsed_results.append(
                    AssessmentResult(
                        person_id=person_id,
                        assessment_id=r.get("assessment_id", "assessment-1"),
                        version="1.0.0",
                        timestamp="2026-08-31T00:00:00Z",
                        raw_responses=raw_resp,
                        calculated_scores=r.get("computed_scores", {})
                    )
                )
        else:
            # Fallback to fetching from Firestore store
            results = await store.get_assessment_results(person_id)
            if not results:
                # Provide deterministic fallback seed result for demo purposes
                from backend.core.assessment_schemas import AssessmentResult, AssessmentResponse
                results = [{
                    "person_id": person_id,
                    "assessment_id": "riasec-interest-inventory",
                    "version": "1.0.0",
                    "timestamp": "2026-08-31T00:00:00Z",
                    "raw_responses": [
                        {"item_id": "r1", "response_value": 5, "timestamp": "2026-08-31T00:00:00Z"},
                        {"item_id": "i1", "response_value": 5, "timestamp": "2026-08-31T00:00:00Z"}
                    ],
                    "calculated_scores": {"R": 5, "I": 5}
                }]
            from backend.core.assessment_schemas import AssessmentResult
            parsed_results = [AssessmentResult(**r) for r in results]
        
        background_context = "12th-grade student interested in technology, stated interest in AI/ML, built 4 projects."
        if body and body.evidence:
            background_context += f" Observable evidence: {json.dumps(body.evidence)}"
            
        profile = agent.synthesize_profile(person_id, parsed_results, background_context)
        return profile
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to synthesize profile: {str(e)}")
