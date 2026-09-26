import httpx
from typing import List, Optional
from datetime import datetime, timezone
from backend.core.schemas import Occupation, ProviderContext
from backend.providers.base import ProviderAdapter


class NptelSwayamProvider(ProviderAdapter):
    """
    NPTEL / SWAYAM course-catalog provider (P1 knowledge source).

    STATUS (verified 2026-09-26): BLOCKED — neither NPTEL nor SWAYAM exposes
    a public documented API. Direct probes of the candidate REST endpoints
    all return 404:

      - https://nptel.ac.in/api/v1/courses
      - https://swayam.gov.in/api/v1/courses
      - https://onlinecourses.nptel.ac.in/api/courses

    Neither site's frontend exposes an XHR/JSON course endpoint either.
    (NPTEL content is reachable via YouTube Data API / Internet Archive, but
    those are video mirrors, not a course catalog with stable ids, and are
    out of scope for this provider.)

    Honesty contract: this provider reports SOURCE_UNAVAILABLE and returns
    zero results rather than fabricating course data. The provider slot is
    wired into KnowledgeService so that when an official catalog API
    appears, only this module's endpoint map and response parsing change.
    """

    # Candidate endpoints, re-probed on each health check in case an
    # official API appears later. Empty mapping = known-unavailable.
    CANDIDATE_SEARCH_ENDPOINTS: List[str] = [
        "https://nptel.ac.in/api/v1/courses",
        "https://swayam.gov.in/api/v1/courses",
        "https://onlinecourses.nptel.ac.in/api/courses",
    ]

    def __init__(self):
        self.version = "unavailable-2026-09-26"
        self._live_endpoint: Optional[str] = None

    @property
    def provider_name(self) -> str:
        return "nptel_swayam"

    def _create_context(self, source_url: Optional[str] = None) -> ProviderContext:
        return ProviderContext(
            provider=self.provider_name,
            retrieved_at=datetime.now(timezone.utc).isoformat(),
            version=self.version,
            source_url=source_url,
        )

    async def check_health(self) -> str:
        """
        Probe candidate catalog endpoints. Returns CONNECTED only if one
        answers 200 with a JSON body; otherwise SOURCE_UNAVAILABLE.
        Never claims connectivity that was not observed.
        """
        self._live_endpoint = None
        for url in self.CANDIDATE_SEARCH_ENDPOINTS:
            try:
                async with httpx.AsyncClient() as client:
                    resp = await client.get(url, timeout=5.0)
                    if resp.status_code == 200:
                        try:
                            resp.json()
                        except Exception:
                            continue
                        self._live_endpoint = url
                        return "CONNECTED"
            except Exception:
                continue
        return "SOURCE_UNAVAILABLE"

    async def search_occupations(self, query: str, limit: int = 10) -> List[Occupation]:
        """
        Search the NPTEL/SWAYAM catalog. With no live endpoint this returns
        an empty list honestly — course entries are never invented.
        """
        if not self._live_endpoint:
            health = await self.check_health()
            if health != "CONNECTED" or not self._live_endpoint:
                return []
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.get(
                    self._live_endpoint,
                    params={"q": query, "limit": limit},
                    timeout=8.0,
                )
                resp.raise_for_status()
                data = resp.json()
        except Exception:
            self._live_endpoint = None
            return []

        # Generic parse: only map fields actually present in the payload.
        # Unknown payload shapes yield zero results, not guessed ones.
        items = data.get("courses") or data.get("results") or data.get("items") or []
        occupations: List[Occupation] = []
        for item in items[:limit]:
            if not isinstance(item, dict):
                continue
            title = item.get("title") or item.get("name")
            if not title:
                continue
            occupations.append(
                Occupation(
                    id=str(item.get("id") or item.get("course_id") or title),
                    title=str(title),
                    description=item.get("description"),
                    source_context=self._create_context(
                        source_url=item.get("url") or item.get("course_url")
                    ),
                )
            )
        return occupations

    async def get_occupation_details(self, occupation_id: str) -> Optional[Occupation]:
        # No public detail endpoint exists; never synthesize one.
        return None
