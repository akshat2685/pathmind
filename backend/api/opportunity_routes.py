from fastapi import APIRouter, Depends, HTTPException, Header, Query
from typing import List, Dict, Any, Optional

from backend.core.opportunity_schemas import (
    CanonicalOpportunity,
    OpportunityMatchResult,
    ApplicationPreparationPlan,
    InterviewPrepPackage,
    CreatePreparationPlanRequest
)
from backend.services.opportunity_matching_engine import OpportunityMatchingEngine

from backend.core.security import get_authenticated_person

router = APIRouter(prefix="/api/opportunities", tags=["Universal Opportunity Intelligence Layer"])
matching_engine = OpportunityMatchingEngine()
get_person_id = get_authenticated_person

@router.get("", response_model=List[CanonicalOpportunity])
async def list_opportunities(
    role_filter: Optional[str] = Query(None),
    geography: Optional[str] = Query(None)
):
    try:
        return await matching_engine.get_all_opportunities(role_filter=role_filter, geography=geography)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch opportunities: {str(e)}")

@router.get("/matched", response_model=List[OpportunityMatchResult])
async def get_matched_opportunities(
    role_filter: Optional[str] = Query(None),
    geography: Optional[str] = Query(None),
    person_id: str = Depends(get_person_id)
):
    try:
        return await matching_engine.match_opportunities_for_person(
            person_id=person_id,
            role_filter=role_filter,
            geography=geography
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to calculate matched opportunities: {str(e)}")

@router.get("/{opportunity_id}", response_model=CanonicalOpportunity)
async def get_opportunity_detail(opportunity_id: str):
    opp = await matching_engine.get_opportunity_by_id(opportunity_id)
    if not opp:
        raise HTTPException(status_code=404, detail=f"Opportunity {opportunity_id} not found.")
    return opp

@router.post("/{opportunity_id}/preparation-plan", response_model=ApplicationPreparationPlan)
async def create_preparation_plan(
    opportunity_id: str,
    req: CreatePreparationPlanRequest = CreatePreparationPlanRequest(),
    person_id: str = Depends(get_person_id)
):
    try:
        return await matching_engine.generate_preparation_plan(
            person_id=person_id,
            opportunity_id=opportunity_id,
            spawn_to_execution_engine=req.spawn_actions_to_execution_engine
        )
    except ValueError as ve:
        raise HTTPException(status_code=404, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate preparation plan: {str(e)}")

@router.get("/{opportunity_id}/interview-prep", response_model=InterviewPrepPackage)
async def get_interview_prep(
    opportunity_id: str,
    person_id: str = Depends(get_person_id)
):
    try:
        return await matching_engine.generate_interview_prep(person_id=person_id, opportunity_id=opportunity_id)
    except ValueError as ve:
        raise HTTPException(status_code=404, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate interview prep: {str(e)}")
