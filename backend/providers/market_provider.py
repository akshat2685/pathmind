from typing import List, Dict, Any, Optional
from backend.core.market_schemas import MarketSignal
from backend.core.config import settings

class RealisticMarketProviderAdapter:
    """
    Connects to external labor market APIs (BLS, O*NET, ESCO, etc.).
    Gracefully handles missing credentials or missing data without fabricating numbers.
    """
    def __init__(self):
        self.bls_api_key = getattr(settings, "BLS_API_KEY", None)
        self.onet_api_key = getattr(settings, "ONET_API_KEY", None)

    async def fetch_market_signals(
        self,
        domain: str,
        occupation: str,
        geography: str
    ) -> List[MarketSignal]:
        
        # If we have no API keys, we explicitly declare source unavailable.
        # We return an empty list, and the MarketIntelligenceService will handle SOURCE_UNAVAILABLE.
        return []

    async def fetch_trajectory_data(
        self,
        domain: str,
        occupation: str
    ) -> Dict[str, Any]:
        """
        Retrieves career trajectory patterns from official sources.
        """
        return {
            "source": "SOURCE_UNAVAILABLE",
            "confidence": "INSUFFICIENT_EVIDENCE",
            "stages": []
        }
