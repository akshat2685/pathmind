from fastapi import APIRouter, Depends, HTTPException
from typing import List, Optional
from backend.services.market_intelligence_service import MarketIntelligenceService
from backend.services.pm_store import get_pm_store
from backend.core.market_schemas import MarketSignal, CareerTrajectory
from backend.core.goal_schemas import CanonicalGoal
from backend.core.security import get_authenticated_person

router = APIRouter(prefix="/api/market", tags=["Market Intelligence"])

@router.get("/signals", response_model=List[MarketSignal])
async def get_market_signals(
    person_id: str = Depends(get_authenticated_person),
    geography: Optional[str] = None
):
    """
    Retrieves evidence-based market signals for the person's active career goal.
    Gracefully handles unavailable data without fabricating values.
    """
    store = get_pm_store()
    market_service = MarketIntelligenceService()
    
    goal_data = await store.get_goal(person_id)
    if not goal_data:
        raise HTTPException(status_code=404, detail="No active career goal found.")
    goal = CanonicalGoal(**goal_data)
    
    signals = await market_service.get_market_signals(goal=goal, geography=geography)
    return signals

@router.get("/trajectory", response_model=CareerTrajectory)
async def get_career_trajectory(
    person_id: str = Depends(get_authenticated_person)
):
    """
    Retrieves the domain-aware career trajectory for the person's target goal.
    """
    store = get_pm_store()
    market_service = MarketIntelligenceService()
    
    goal_data = await store.get_goal(person_id)
    if not goal_data:
        raise HTTPException(status_code=404, detail="No active career goal found.")
    goal = CanonicalGoal(**goal_data)
    
    trajectory = await market_service.get_career_trajectory(goal=goal)
    return trajectory
