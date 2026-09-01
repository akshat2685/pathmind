from fastapi import APIRouter, Depends, HTTPException, Header
from typing import List, Dict, Any, Optional
from backend.core.assessment_schemas import (
    AssessmentDefinition,
    AssessmentResult,
    AssessmentResponse,
    AssessmentDraft
)
from backend.services.assessment import AssessmentEngine
from backend.services.store import FirestoreStore

router = APIRouter(prefix="/api/assessments", tags=["Assessments"])
engine = AssessmentEngine()
store = FirestoreStore()

def get_person_id(x_person_id: Optional[str] = Header(None)) -> str:
    if not x_person_id:
        return "demo-user"
    return x_person_id

@router.get("/", response_model=List[AssessmentDefinition])
async def list_assessments():
    return engine.get_all_assessments()

@router.get("/{assessment_id}", response_model=AssessmentDefinition)
async def get_assessment(assessment_id: str):
    definition = engine.get_assessment(assessment_id)
    if not definition:
        raise HTTPException(status_code=404, detail="Assessment not found")
    return definition

@router.get("/{assessment_id}/draft", response_model=Optional[AssessmentDraft])
async def get_assessment_draft(assessment_id: str, person_id: str = Depends(get_person_id)):
    draft_data = await store.get_assessment_draft(person_id, assessment_id)
    if not draft_data:
        return None
    return AssessmentDraft(**draft_data)

@router.post("/{assessment_id}/draft", response_model=AssessmentDraft)
async def save_assessment_draft(
    assessment_id: str,
    draft: AssessmentDraft,
    person_id: str = Depends(get_person_id)
):
    draft.person_id = person_id
    draft.assessment_id = assessment_id
    await store.save_assessment_draft(person_id, assessment_id, draft.model_dump(mode="json"))
    return draft

@router.post("/{assessment_id}/submit", response_model=AssessmentResult)
async def submit_assessment(
    assessment_id: str,
    responses: List[AssessmentResponse],
    person_id: str = Depends(get_person_id)
):
    try:
        result = engine.process_submission(person_id, assessment_id, responses)
        
        # Persist result securely scoped to person_id
        await store.save_assessment_result(person_id, result.model_dump(mode="json"))
        
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")
