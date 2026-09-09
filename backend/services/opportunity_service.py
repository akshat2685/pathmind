from typing import List, Dict, Any, Optional
from datetime import datetime, timezone
from backend.core.career_schemas import (
    UniversalCareerProfile,
    VerifiedOpportunity,
    MarketContext
)
from backend.providers.opportunity_provider import (
    BaseOpportunityProvider,
    VerifiedOpenOpportunityProvider
)
from backend.services.career_agents import OpportunityAgent

class OpportunityService:
    def __init__(self, provider: Optional[BaseOpportunityProvider] = None):
        self.provider = provider or VerifiedOpenOpportunityProvider()
        self.agent = OpportunityAgent()

    def get_provider_status(self) -> Dict[str, Any]:
        return {
            "provider_name": self.provider.get_provider_name(),
            "is_connected": self.provider.is_connected(),
            "status_code": self.provider.get_status_code()
        }

    async def get_all_opportunities(
        self,
        role_filter: Optional[str] = None,
        geography: Optional[str] = None
    ) -> List[VerifiedOpportunity]:
        return await self.provider.fetch_opportunities(role_filter=role_filter, geography=geography)

    async def match_opportunities_for_person(
        self,
        profile: UniversalCareerProfile,
        target_role: str = "Machine Learning Engineer",
        readiness_state: str = "DEVELOPING"
    ) -> List[VerifiedOpportunity]:
        """
        Calculates explainable fit match using ADK OpportunityAgent:
        - HIGH / MEDIUM / LOW fit levels
        - Surfaces transparent fit reasons and missing requirements
        - Differentiates career fit from legal/geographic eligibility
        - Provides timing advice based on qualitative readiness state
        """
        all_opps = await self.provider.fetch_opportunities()
        return self.agent.match_and_explain(
            opportunities=all_opps,
            profile=profile,
            target_role=target_role,
            readiness_state=readiness_state
        )
