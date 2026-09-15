import uuid
from typing import List, Dict, Any, Optional
from backend.core.market_schemas import MarketSignal, CareerTrajectory, TrajectoryStage
from backend.providers.market_provider import RealisticMarketProviderAdapter
from backend.core.goal_schemas import CanonicalGoal
from backend.core.config import settings

class MarketIntelligenceService:
    """
    Service responsible for retrieving and synthesizing domain-aware market intelligence,
    ensuring geographic context, preserving provenance, and handling data failures.
    """
    def __init__(self):
        self.provider = RealisticMarketProviderAdapter()

    async def get_market_signals(
        self,
        goal: CanonicalGoal,
        geography: Optional[str] = None
    ) -> List[MarketSignal]:
        geo = geography or goal.geography or "Global"
        
        # 1. Attempt to fetch from real external provider
        raw_signals = await self.provider.fetch_market_signals(
            domain=goal.target_domain,
            occupation=goal.target_role,
            geography=geo
        )
        
        if raw_signals:
            return raw_signals
            
        # 2. If provider is unavailable/unconfigured, we generate a SOURCE_UNAVAILABLE signal 
        # instead of fabricating data.
        return [
            MarketSignal(
                id=str(uuid.uuid4()),
                goal_id=goal.goal_id,
                domain=goal.target_domain,
                field=goal.target_role,
                geography=geo,
                signal_type="all_metrics",
                metric="data_availability",
                value="SOURCE_UNAVAILABLE",
                period="CURRENT",
                source="System",
                confidence="INSUFFICIENT_EVIDENCE",
                freshness_status="UNKNOWN",
                notes="Real market data provider API keys (BLS, ONET) are not configured."
            )
        ]

    async def get_career_trajectory(self, goal: CanonicalGoal) -> CareerTrajectory:
        # 1. Attempt to fetch structured trajectory from real external provider
        traj_data = await self.provider.fetch_trajectory_data(
            domain=goal.target_domain,
            occupation=goal.target_role
        )
        
        # We do NOT fabricate missing trajectory data with Gemini anymore.
        # We explicitly return SOURCE_UNAVAILABLE honestly if missing.
        stages = [TrajectoryStage(**s) for s in traj_data.get("stages", [])]
        return CareerTrajectory(
            goal_id=goal.goal_id,
            occupation=goal.target_role,
            domain=goal.target_domain,
            stages=stages,
            source=traj_data.get("source", "SOURCE_UNAVAILABLE"),
            confidence=traj_data.get("confidence", "INSUFFICIENT_EVIDENCE")
        )
