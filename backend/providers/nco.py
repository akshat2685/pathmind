from typing import List, Optional
from datetime import datetime
from backend.core.schemas import Occupation, ProviderContext
from backend.providers.base import ProviderAdapter, ProviderError
import os
import json

class NcoProvider(ProviderAdapter):
    """
    Indian NCO Data Provider using controlled ingestion.
    Expects data to be present in a local JSON/CSV format.
    """
    def __init__(self):
        self.data_path = os.getenv("NCO_DATA_PATH", "data/nco_2015.json")
        self.version = "NCO-2015"

    @property
    def provider_name(self) -> str:
        return "india_nco"

    async def check_health(self) -> str:
        if os.path.exists(self.data_path):
            return "INGESTED"
        return "NOT_CONFIGURED"

    def _create_context(self, source_id: str = None) -> ProviderContext:
        return ProviderContext(
            provider=self.provider_name,
            retrieved_at=datetime.utcnow().isoformat() + "Z",
            version=self.version,
            source_id=source_id
        )

    async def search_occupations(self, query: str, limit: int = 10) -> List[Occupation]:
        if not os.path.exists(self.data_path):
            raise ProviderError("NCO data not ingested.")
            
        try:
            with open(self.data_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            results = []
            for item in data:
                if query.lower() in item.get('title', '').lower():
                    results.append(Occupation(
                        id=item.get('code', ''),
                        title=item.get('title', ''),
                        description=item.get('description', ''),
                        source_context=self._create_context(source_id=item.get('code', ''))
                    ))
                    if len(results) >= limit:
                        break
            return results
        except Exception as e:
            raise ProviderError(f"Failed to read NCO data: {str(e)}")

    async def get_occupation_details(self, occupation_id: str) -> Optional[Occupation]:
        if not os.path.exists(self.data_path):
            raise ProviderError("NCO data not ingested.")
            
        try:
            with open(self.data_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                
            for item in data:
                if item.get('code') == occupation_id:
                    return Occupation(
                        id=item.get('code', ''),
                        title=item.get('title', ''),
                        description=item.get('description', ''),
                        source_context=self._create_context(source_id=item.get('code', ''))
                    )
            return None
        except Exception as e:
            raise ProviderError(f"Failed to read NCO data: {str(e)}")
