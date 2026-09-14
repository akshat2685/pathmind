from fastapi import APIRouter, Depends, Header, HTTPException
from typing import List, Optional
from backend.services.market_intelligence_service import MarketIntelligenceService
from backend.services.store import FirestoreStore
from backend.core.market_schemas import MarketSignal, CareerTrajectory
from backend.core.goal_schemas import CanonicalGoal

router = APIRouter(prefix="/api/market", tags=["Market Intelligence"])

@router.get("/signals", response_model=List[MarketSignal])
async def get_market_signals(
    x_person_id: str = Header(...),
    geography: Optional[str] = None
):
    """
    Retrieves evidence-based market signals for the person's active career goal.
    Gracefully handles unavailable data without fabricating values.
    """
    store = FirestoreStore()
    market_service = MarketIntelligenceService()
    
    goal_data = await store.get_goal(x_person_id)
    if not goal_data:
        raise HTTPException(status_code=404, detail="No active career goal found.")
    goal = CanonicalGoal(**goal_data)
    
    signals = await market_service.get_market_signals(goal=goal, geography=geography)
    return signals

@router.get("/trajectory", response_model=CareerTrajectory)
async def get_career_trajectory(
    x_person_id: str = Header(...)
):
    """
    Retrieves the domain-aware career trajectory for the person's target goal.
    """
    store = FirestoreStore()
    market_service = MarketIntelligenceService()
    
    goal_data = await store.get_goal(x_person_id)
    if not goal_data:
        raise HTTPException(status_code=404, detail="No active career goal found.")
    goal = CanonicalGoal(**goal_data)
    
    trajectory = await market_service.get_career_trajectory(goal=goal)
    return trajectory
