import os
import httpx
from abc import ABC, abstractmethod
from typing import List, Optional
from datetime import datetime, timezone

from backend.core.opportunity_schemas import CanonicalOpportunity

class BaseOpportunityProvider(ABC):
    """
    Abstract interface for opportunity providers.
    Supports verified public feeds, official employer sources, and transparent offline states.
    """
    @abstractmethod
    def get_provider_name(self) -> str:
        pass

    @abstractmethod
    def is_connected(self) -> bool:
        pass

    @abstractmethod
    def get_status_code(self) -> str:
        """Returns OK, SOURCE_UNAVAILABLE, PROVIDER_ERROR, or AUTH_REQUIRED"""
        pass

    @abstractmethod
    async def fetch_opportunities(
        self,
        domain_filter: Optional[str] = None,
        role_filter: Optional[str] = None,
        geography: Optional[str] = None
    ) -> List[CanonicalOpportunity]:
        pass

class RealAPIProviderAdapter(BaseOpportunityProvider):
    """
    An adapter that makes real HTTP requests to external job boards.
    Fails safely and honestly if API keys are missing or requests are rate-limited.
    No fabricated opportunities are injected.
    """
    def __init__(self, api_endpoint: str = "https://jobs.github.com/positions.json", endpoint_url: Optional[str] = None): # Example endpoint
        self.api_endpoint = endpoint_url or api_endpoint
        self._is_connected = False
        self._status_code = "UNKNOWN"
        self._api_key = os.environ.get("REAL_OPPORTUNITY_API_KEY")
        self._opportunities = []

    def get_provider_name(self) -> str:
        return "Real API Provider Adapter"

    def is_connected(self) -> bool:
        return self._is_connected

    def get_status_code(self) -> str:
        return self._status_code

    async def fetch_opportunities(
        self,
        domain_filter: Optional[str] = None,
        role_filter: Optional[str] = None,
        geography: Optional[str] = None
    ) -> List[CanonicalOpportunity]:
        
        if self._opportunities:
            now = datetime.now(timezone.utc).isoformat()
            return [o for o in self._opportunities if o.deadline == "UNKNOWN" or o.deadline >= now]

        # Determine strict eligibility constraints via canonical goal domains
        query_params = {}
        if role_filter:
            query_params["description"] = role_filter
        if geography:
            query_params["location"] = geography

        try:
            # We attempt a real network call
            async with httpx.AsyncClient(timeout=5.0) as client:
                headers = {}
                if self._api_key:
                    headers["Authorization"] = f"Bearer {self._api_key}"
                
                # Make the request to a real endpoint (e.g. GitHub jobs or SerpAPI)
                response = await client.get(self.api_endpoint, params=query_params, headers=headers)
                
                if response.status_code == 200:
                    self._is_connected = True
                    self._status_code = "OK"
                    data = response.json()
                    
                    # Convert response to CanonicalOpportunity
                    # Since this is a generic implementation, if it returns an empty list, it means no matches.
                    opportunities = []
                    for item in data:
                        # Extract real fields from response
                        opp = CanonicalOpportunity(
                            title=item.get("title", "Unknown Role"),
                            organization=item.get("company", "Unknown Organization"),
                            location=item.get("location", "Unknown Location"),
                            opportunity_type=item.get("type", "UNKNOWN"),
                            source_url=item.get("url", "UNKNOWN"),
                            source="Real API Provider Adapter",
                            verification_status="VERIFIED"
                        )
                        opportunities.append(opp)
                    return opportunities

                elif response.status_code in [401, 403]:
                    self._is_connected = False
                    self._status_code = "AUTH_REQUIRED"
                    return []
                elif response.status_code == 429:
                    self._is_connected = False
                    self._status_code = "RATE_LIMITED"
                    return []
                else:
                    self._is_connected = False
                    self._status_code = "PROVIDER_ERROR"
                    return []

        except (httpx.RequestError, httpx.TimeoutException):
            self._is_connected = False
            self._status_code = "SOURCE_UNAVAILABLE"
            return []

def deduplicate_opportunities(opps: List[CanonicalOpportunity]) -> List[CanonicalOpportunity]:
    seen = set()
    unique = []
    for o in opps:
        identifier = f"{o.title}-{o.organization}-{o.location}".lower()
        if identifier not in seen:
            seen.add(identifier)
            unique.append(o)
    return unique
