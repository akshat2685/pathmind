"""
PathMind intelligence-pack providers for the KnowledgeService.

Mirrors the existing provider pattern (ESCO / NCO): the professions
encyclopedia KB plugs in as an occupation provider, so the counselor's
evidence flow uses one system instead of a parallel one.

The KB is curated, verified, ML-indexed knowledge — NOT a "trained model".
Salaries are always surfaced as estimates.
"""

from datetime import datetime, timezone
from typing import List, Optional

from backend.core.schemas import Occupation
from backend.providers.base import ProviderAdapter, ProviderError
from backend.services.intelligence_service import get_intelligence_service


class IntelligenceProfessionsProvider(ProviderAdapter):
    """Occupation provider backed by the vendored professions encyclopedia KB."""

    @property
    def provider_name(self) -> str:
        return "pathmind_intelligence_professions"

    async def check_health(self) -> str:
        service = get_intelligence_service()
        return "CONNECTED" if service.available else f"NOT_CONFIGURED: {service.load_error}"

    def _create_context(self, entry_id: str):
        from backend.core.schemas import ProviderContext

        return ProviderContext(
            provider=self.provider_name,
            retrieved_at=datetime.now(timezone.utc).isoformat(),
            version="professions-kb-2026-10-15",
            source_id=entry_id,
        )

    def _describe(self, e: dict) -> str:
        sal = e.get("salary_inr") or {}
        parts = [e.get("description", "")]
        entry_paths = e.get("entry_paths") or []
        if entry_paths:
            parts.append("Entry paths: " + ", ".join(entry_paths))
        if e.get("demand_outlook"):
            parts.append("Demand outlook: " + e["demand_outlook"])
        # Salaries are ranges marked "estimate" in the KB — keep that label here.
        parts.append(
            "Salary (ESTIMATE, not a precise fact): "
            f"{sal.get('entry', '?')} entry / {sal.get('experienced', '?')} experienced."
        )
        pros = (e.get("pros") or [])[:4]
        cons = (e.get("cons") or [])[:4]
        if pros:
            parts.append("Pros: " + "; ".join(pros))
        if cons:
            parts.append("Cons: " + "; ".join(cons))
        return "\n".join(p for p in parts if p)

    async def search_occupations(self, query: str, limit: int = 10) -> List[Occupation]:
        service = get_intelligence_service()
        if not service.available:
            raise ProviderError(
                f"Intelligence professions KB unavailable: {service.load_error}"
            )
        try:
            hits = service.retrieve_professions(query, k=limit)
        except Exception as e:
            raise ProviderError(f"Intelligence professions retrieval failed: {e}")
        occupations = []
        for h in hits:
            e = h["entry"]
            occupations.append(
                Occupation(
                    id=e.get("id", ""),
                    title=e.get("name", ""),
                    description=self._describe(e),
                    source_context=self._create_context(e.get("id", "")),
                )
            )
        return occupations

    async def get_occupation_details(self, occupation_id: str) -> Optional[Occupation]:
        # Detail lookup by id is not indexed; retrieval is query-based.
        return None
