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

class JobOpportunitiesProvider(BaseOpportunityProvider):
    """
    An adapter that makes real HTTP requests to JobOpportunitiesAPI (public keyless).
    Fails safely and honestly if requests are rate-limited.
    No fabricated opportunities are injected.
    """
    def __init__(self, api_endpoint: str = "https://api.jobopportunitiesapi.org/public/jobs"):
        self.api_endpoint = api_endpoint
        self._is_connected = False
        self._status_code = "UNKNOWN"
        self._opportunities = []
        self._last_filters = None

    def get_provider_name(self) -> str:
        return "JobOpportunitiesAPI Provider"

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
        
        current_filters = (domain_filter, role_filter, geography)
        if self._opportunities and self._last_filters == current_filters:
            now = datetime.now(timezone.utc).isoformat()
            valid = [o for o in self._opportunities if o.deadline == "UNKNOWN" or o.deadline >= now]
            if valid:
                return valid
            else:
                self._opportunities = []
        # Determine strict eligibility constraints via canonical goal domains
        query_params = {}
        # The public API doesn't document specific filters, so we just pass search and location
        search_term = ""
        if domain_filter:
            search_term += domain_filter + " "
        if role_filter:
            search_term += role_filter
            
        if search_term.strip():
            query_params["search"] = search_term.strip()
        if geography:
            query_params["location"] = geography

        try:
            # We attempt a real network call
            async with httpx.AsyncClient(timeout=10.0) as client:
                headers = {
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
                }
                
                # Make the request to a real endpoint
                response = await client.get(self.api_endpoint, params=query_params, headers=headers)
                
                if response.status_code == 200:
                    self._is_connected = True
                    self._status_code = "OK"
                    data = response.json()
                    jobs = data.get("data", [])
                    
                    # Convert response to CanonicalOpportunity
                    opportunities = []
                    for item in jobs:
                        opp = CanonicalOpportunity(
                            title=item.get("title", "Unknown Role"),
                            organization=item.get("company", "Unknown Organization"),
                            location=item.get("location", "Unknown Location") or item.get("city", "Unknown Location"),
                            opportunity_type=item.get("employment_type", "UNKNOWN"),
                            source_url=item.get("apply_url", "UNKNOWN"),
                            source=item.get("source", self.get_provider_name()),
                            verification_status="VERIFIED"
                        )
                        opportunities.append(opp)
                        
                    # Filter manually if API search is unreliable
                    if search_term.strip():
                        term = search_term.strip().lower()
                        opportunities = [o for o in opportunities if term in o.title.lower() or term in o.organization.lower()]
                        
                    self._opportunities = opportunities
                    self._last_filters = current_filters
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
