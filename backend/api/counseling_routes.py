import json
from typing import List, Dict, Any, Optional
from pydantic import BaseModel
from fastapi import APIRouter, Depends, HTTPException, Header
from backend.core.assessment_schemas import CounselingProfile, AssessmentResult, AssessmentResponse
from backend.services.store import FirestoreStore
from backend.services.counseling import CounselingAgent

router = APIRouter(prefix="/api/counseling", tags=["Counseling"])
store = FirestoreStore()
agent = CounselingAgent()

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
        
        # Parse inline assessment results if provided
        if body and body.assessment_results and len(body.assessment_results) > 0:
            parsed_results = []
            for r in body.assessment_results:
                raw_resp = [
                    AssessmentResponse(item_id=str(k), response_value=v, timestamp="2026-08-31T00:00:00Z")
                    for k, v in r.get("raw_responses", {}).items()
                ] if isinstance(r.get("raw_responses"), dict) else []
                
                parsed_results.append(
                    AssessmentResult(
                        person_id=person_id,
                        assessment_id=r.get("assessment_id", "riasec-assessment"),
                        version="1.0.0",
                        timestamp="2026-08-31T00:00:00Z",
                        raw_responses=raw_resp,
                        calculated_scores=r.get("computed_scores", {})
                    )
                )
        else:
            # Fallback to store
            results = await store.get_assessment_results(person_id)
            if not results:
                results = [{
                    "person_id": person_id,
                    "assessment_id": "riasec-interest-inventory",
                    "version": "1.0.0",
                    "timestamp": "2026-08-31T00:00:00Z",
                    "raw_responses": [
                        {"item_id": "r1", "response_value": 3, "timestamp": "2026-08-31T00:00:00Z"},
                        {"item_id": "i1", "response_value": 4, "timestamp": "2026-08-31T00:00:00Z"}
                    ],
                    "calculated_scores": {"R": 3, "I": 4}
                }]
            parsed_results = [AssessmentResult(**r) for r in results]
        
        # Build strictly factual background context without hallucinating unprovided evidence
        context_parts = []
        if body and body.goals and len(body.goals) > 0:
            context_parts.append(f"Stated Career Aspirations / Goals: {', '.join(body.goals)}")
        else:
            context_parts.append("Stated Career Aspirations / Goals: Not explicitly declared.")
            
        if body and body.constraints and len(body.constraints) > 0:
            context_parts.append(f"Stated Constraints: {', '.join(body.constraints)}")
            
        if body and body.evidence and len(body.evidence) > 0:
            context_parts.append(f"Provided Observable Evidence & Work Artifacts: {json.dumps(body.evidence)}")
        else:
            context_parts.append("Provided Observable Evidence: NONE PROVIDED. The candidate has NOT submitted any portfolio, code repositories, work samples, or transcripts.")
            
        background_context = "\n".join(context_parts)
        
        profile = agent.synthesize_profile(person_id, parsed_results, background_context)
        return profile
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to synthesize profile: {str(e)}")
