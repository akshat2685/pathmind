from fastapi import APIRouter, Depends, HTTPException, Header, Query
from typing import List, Dict, Any, Optional
from pydantic import BaseModel
from backend.core.trust_schemas import (
    StructuredRecommendation,
    RecommendationExplanation,
    SafetyGuardrailResult,
    UserRecommendationFeedback,
    TraceableClaim
)
from backend.services.recommendation_explanation_service import RecommendationExplanationService
from backend.services.trust_provenance_service import TrustProvenanceService

router = APIRouter(prefix="/api/trust", tags=["Trust Layer, Provenance & Explainability"])
explanation_service = RecommendationExplanationService()
trust_service = TrustProvenanceService()

from backend.core.security import get_authenticated_person
get_person_id = get_authenticated_person

class DecideRequest(BaseModel):
    user_choice: str
    notes: Optional[str] = None

class FeedbackRequest(BaseModel):
    feedback_type: str  # HELPFUL, NOT_HELPFUL, INCORRECT, MISSING_CONTEXT, OUTDATED, WRONG_SOURCE, DISAGREE
    notes: Optional[str] = None

class ValidateClaimRequest(BaseModel):
    claim_text: str
    claim_category: Optional[str] = "INFERENCE"
    source_type: Optional[str] = "INTERNAL_DETERMINISTIC"

@router.get("/recommendations", response_model=List[StructuredRecommendation])
async def get_recommendations(person_id: str = Depends(get_person_id)):
    try:
        raw = await explanation_service.store.get_structured_recommendations(person_id, status="ACTIVE")
        if not raw:
            # Generate initial active recommendation for learner
            rec = await explanation_service.generate_structured_recommendation(
                person_id=person_id,
                rec_type="NEXT_ACTION",
                title="Stage Focus: Production Repository Implementation",
                summary="Build hands-on verified code repository with end-to-end tests.",
                why_now="Satisfies foundational prerequisites for your target career direction.",
                recommended_choice="Hands-on Project with Pytest Unit Tests",
                alternative_choices=["Theoretical Lecture Only", "Paid Exam Certification"],
                options=[
                    {"name": "Hands-on Project", "pace": "Self-paced", "proof": "Verifiable Git Repo"},
                    {"name": "Theoretical Course", "pace": "Fast", "proof": "Completion Certificate"}
                ],
                tradeoffs=[
                    "Project repositories provide verifiable code evidence required by hiring teams."
                ],
                uncertainties=[
                    "Asynchronous performance profiling has not yet been benchmarked."
                ],
                facts=[
                    "Target role requirement graph lists practical testing and clean code as mandatory."
                ],
                inferences=[
                    "Demonstrating verified code evidence accelerates career readiness progression."
                ]
            )
            return [rec]
        return [StructuredRecommendation(**r) for r in raw]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch recommendations: {str(e)}")

@router.get("/recommendations/{rec_id}/explain", response_model=RecommendationExplanation)
async def explain_recommendation(
    rec_id: str,
    person_id: str = Depends(get_person_id)
):
    try:
        return await explanation_service.explain_recommendation(person_id, rec_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate explanation: {str(e)}")

@router.post("/recommendations/{rec_id}/decide")
async def decide_recommendation(
    rec_id: str,
    req: DecideRequest,
    person_id: str = Depends(get_person_id)
):
    try:
        success = await explanation_service.record_user_decision(
            person_id=person_id,
            recommendation_id=rec_id,
            user_choice=req.user_choice,
            notes=req.notes
        )
        return {"status": "SUCCESS", "message": "Decision recorded in permanent decision history."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to record decision: {str(e)}")

@router.post("/recommendations/{rec_id}/feedback", response_model=UserRecommendationFeedback)
async def submit_feedback(
    rec_id: str,
    req: FeedbackRequest,
    person_id: str = Depends(get_person_id)
):
    try:
        return await explanation_service.record_feedback(
            person_id=person_id,
            recommendation_id=rec_id,
            feedback_type=req.feedback_type,
            notes=req.notes
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to record feedback: {str(e)}")

@router.post("/validate-claim", response_model=TraceableClaim)
async def validate_claim(
    req: ValidateClaimRequest,
    person_id: str = Depends(get_person_id)
):
    try:
        return await trust_service.verify_claim_provenance(
            person_id=person_id,
            claim_text=req.claim_text,
            claim_category=req.claim_category or "INFERENCE",
            source_type=req.source_type or "INTERNAL_DETERMINISTIC"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to validate claim: {str(e)}")
