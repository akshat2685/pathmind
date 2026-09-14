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
        self.gemini_available = bool(settings.GEMINI_API_KEY)

    async def get_market_signals(
        self,
        goal: CanonicalGoal,
        geography: Optional[str] = None
    ) -> List[MarketSignal]:
        geo = geography or goal.geography or "Global"
        
        # 1. Attempt to fetch from real external provider
        raw_signals = await self.provider.fetch_market_signals(
            domain=goal.domain,
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
                domain=goal.domain,
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
            domain=goal.domain,
            occupation=goal.target_role
        )
        
        # If provider doesn't have it, we use Gemini to synthesize a logical, domain-aware trajectory, 
        # but mark it with medium/low confidence depending on evidence.
        if traj_data.get("source") == "SOURCE_UNAVAILABLE" and self.gemini_available:
            return await self._synthesize_trajectory_with_llm(goal)
            
        # If provider has it (or if Gemini isn't available), return base
        stages = [TrajectoryStage(**s) for s in traj_data.get("stages", [])]
        return CareerTrajectory(
            goal_id=goal.goal_id,
            occupation=goal.target_role,
            domain=goal.domain,
            stages=stages,
            source=traj_data.get("source", "SOURCE_UNAVAILABLE"),
            confidence=traj_data.get("confidence", "INSUFFICIENT_EVIDENCE")
        )

    async def _synthesize_trajectory_with_llm(self, goal: CanonicalGoal) -> CareerTrajectory:
        import json
        import google.generativeai as genai
        genai.configure(api_key=settings.GEMINI_API_KEY)
        model = genai.GenerativeModel("gemini-1.5-flash")
        
        prompt = f"""You are the PATHMIND Career Intelligence Agent.
Generate a realistic, evidence-based career trajectory for:
Role: {goal.target_role}
Domain: {goal.domain}

Rules:
1. Be strictly domain-aware. (e.g. Medicine requires licensing, Cricket requires trials/academy, Software requires projects/interviews).
2. Do NOT force software stages onto non-software roles.
3. Return ONLY a JSON object:
{{
    "stages": [
        {{
            "stage_name": "...",
            "typical_entry_requirements": ["..."],
            "common_next_steps": ["..."],
            "alternative_transitions": ["..."]
        }}
    ],
    "evidence": ["..."]
}}
"""
        try:
            import asyncio
            response = await asyncio.to_thread(model.generate_content, prompt)
            clean_text = response.text.strip()
            if "```json" in clean_text:
                clean_text = clean_text.split("```json")[1].split("```")[0].strip()
            elif "```" in clean_text:
                clean_text = clean_text.split("```")[1].split("```")[0].strip()
                
            data = json.loads(clean_text)
            stages = [TrajectoryStage(**s) for s in data.get("stages", [])]
            return CareerTrajectory(
                goal_id=goal.goal_id,
                occupation=goal.target_role,
                domain=goal.domain,
                stages=stages,
                evidence=data.get("evidence", []),
                source="LLM Synthesis (Fallback)",
                confidence="MEDIUM"
            )
        except Exception:
            return CareerTrajectory(
                goal_id=goal.goal_id,
                occupation=goal.target_role,
                domain=goal.domain,
                source="SOURCE_UNAVAILABLE",
                confidence="INSUFFICIENT_EVIDENCE"
            )
