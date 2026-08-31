import hashlib
import json
from typing import List, Dict, Any, Optional
from backend.core.schemas import KnowledgeResponse, Occupation, ProviderContext
from backend.providers.esco import EscoProvider
from backend.providers.nco import NcoProvider
from backend.services.store import FirestoreStore

class KnowledgeService:
    def __init__(self):
        self.providers = {
            "esco": EscoProvider(),
            "nco": NcoProvider()
        }
        self.store = FirestoreStore()

    def _generate_cache_key(self, method: str, kwargs: Dict[str, Any]) -> str:
        key_str = f"{method}:{json.dumps(kwargs, sort_keys=True)}"
        return hashlib.md5(key_str.encode()).hexdigest()

    async def get_health_status(self) -> Dict[str, str]:
        status = {}
        for name, provider in self.providers.items():
            status[name] = await provider.check_health()
        
        status["firestore_cache"] = await self.store.check_health()
        return status

    async def search_occupations(self, query: str, limit: int = 10, preferred_provider: str = None) -> KnowledgeResponse:
        cache_key = self._generate_cache_key("search_occupations", {"query": query, "limit": limit, "preferred": preferred_provider})
        
        cached_data = await self.store.get_cached_knowledge(cache_key)
        if cached_data:
            return KnowledgeResponse(**cached_data)

        results = []
        sources = []

        providers_to_use = [self.providers[preferred_provider]] if preferred_provider and preferred_provider in self.providers else self.providers.values()

        for provider in providers_to_use:
            try:
                provider_results = await provider.search_occupations(query, limit)
                results.extend(provider_results)
                if provider_results:
                    sources.append(provider_results[0].source_context)
            except Exception:
                # Log provider failure but continue with others
                continue

        response = KnowledgeResponse(
            results=results,
            sources=sources,
            confidence="source-backed" if sources else "no-results"
        )

        if results:
            await self.store.set_cached_knowledge(cache_key, response.model_dump(mode="json"))

        return response
