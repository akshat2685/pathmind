from fastapi import APIRouter, Depends, HTTPException, Header, Query
from typing import List, Dict, Any, Optional
from pydantic import BaseModel
from backend.core.longitudinal_schemas import (
    LongitudinalLearnerState,
    ProgressInsight,
    TemporalQueryResponse,
    LearningStrategyProfile
)
from backend.services.progress_analysis_service import ProgressAnalysisService
from backend.services.learner_evolution_agent import LearnerEvolutionAgent

router = APIRouter(prefix="/api/longitudinal", tags=["Longitudinal Learner Model & Progress Intelligence"])
progress_service = ProgressAnalysisService()
evolution_agent = LearnerEvolutionAgent(progress_service=progress_service)

from backend.core.security import get_authenticated_person
get_person_id = get_authenticated_person

class TemporalQueryRequest(BaseModel):
    query_text: str

class DisputeInsightRequest(BaseModel):
    dispute_reason: str

@router.get("/state", response_model=LongitudinalLearnerState)
async def get_longitudinal_state(person_id: str = Depends(get_person_id)):
    try:
        return await progress_service.assemble_longitudinal_state(person_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to assemble longitudinal state: {str(e)}")

@router.post("/temporal-query", response_model=TemporalQueryResponse)
async def query_temporal_history(
    req: TemporalQueryRequest,
    person_id: str = Depends(get_person_id)
):
    try:
        return await evolution_agent.answer_temporal_query(person_id, req.query_text)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to process temporal query: {str(e)}")

@router.get("/insights", response_model=List[ProgressInsight])
async def get_progress_insights(person_id: str = Depends(get_person_id)):
    try:
        raw = await progress_service.store.get_progress_insights(person_id, status="ACTIVE")
        if not raw:
            # Generate initial active growth insight
            state = await progress_service.assemble_longitudinal_state(person_id)
            ins = ProgressInsight(
                person_id=person_id,
                type="GROWTH_OBSERVATION",
                claim=f"Demonstrated steady milestone progress across {state.current_state_summary.get('completed_stages', 0)} stages in {state.current_state_summary.get('active_target_role')}.",
                supporting_events=["Stage progression and verified artifact evaluations."],
                supporting_evidence=[],
                time_range="Active Enrollment",
                confidence="HIGH"
            )
            await progress_service.store.save_progress_insight(person_id, ins.model_dump())
            return [ins]
        return [ProgressInsight(**i) for i in raw]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch insights: {str(e)}")

@router.post("/insights/{insight_id}/dispute")
async def dispute_insight(
    insight_id: str,
    req: DisputeInsightRequest,
    person_id: str = Depends(get_person_id)
):
    try:
        success = await evolution_agent.dispute_insight(person_id, insight_id, req.dispute_reason)
        if not success:
            raise HTTPException(status_code=404, detail="Insight not found.")
        return {"status": "SUCCESS", "message": "Dispute recorded and added to personal agent learning calibration."}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to dispute insight: {str(e)}")

@router.get("/strategies", response_model=List[LearningStrategyProfile])
async def get_learning_strategies(person_id: str = Depends(get_person_id)):
    try:
        return await progress_service.evaluate_strategy_profiles(person_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch learning strategies: {str(e)}")
