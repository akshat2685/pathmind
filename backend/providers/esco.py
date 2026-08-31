import httpx
from typing import List, Optional
from datetime import datetime
from backend.core.config import settings
from backend.core.schemas import Occupation, ProviderContext
from backend.providers.base import ProviderAdapter, ProviderError

class EscoProvider(ProviderAdapter):
    def __init__(self):
        self.base_url = settings.ESCO_API_URL
        self.version = "v1.1.2" # Current ESCO API version

    @property
    def provider_name(self) -> str:
        return "esco"

    async def check_health(self) -> str:
        try:
            async with httpx.AsyncClient() as client:
                # A simple request to check connectivity
                response = await client.get(f"{self.base_url}/resource/concept", params={
                    "uri": "http://data.europa.eu/esco/occupation/528f90ed-e250-48bd-aacc-ffb7b1de5654",
                    "language": "en"
                }, timeout=5.0)
                if response.status_code == 200:
                    return "CONNECTED"
                return "INVALID_RESPONSE"
        except Exception:
            return "SOURCE_UNAVAILABLE"

    def _create_context(self, source_url: str = None, source_id: str = None) -> ProviderContext:
        return ProviderContext(
            provider=self.provider_name,
            retrieved_at=datetime.utcnow().isoformat() + "Z",
            version=self.version,
            source_url=source_url,
            source_id=source_id
        )

    async def search_occupations(self, query: str, limit: int = 10) -> List[Occupation]:
        # ESCO Search API
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(f"{self.base_url}/search", params={
                    "text": query,
                    "language": "en",
                    "type": "occupation",
                    "limit": limit
                })
                response.raise_for_status()
                data = response.json()
                
                occupations = []
                for item in data.get("_embedded", {}).get("results", []):
                    uri = item.get("uri")
                    title = item.get("title")
                    
                    occupations.append(Occupation(
                        id=uri.split("/")[-1] if uri else "",
                        title=title,
                        description=item.get("description"),
                        source_context=self._create_context(source_url=uri, source_id=uri)
                    ))
                return occupations
        except Exception as e:
            raise ProviderError(f"ESCO search failed: {str(e)}")

    async def get_occupation_details(self, occupation_id: str) -> Optional[Occupation]:
        # Implementation for detailed view if necessary
        return None
