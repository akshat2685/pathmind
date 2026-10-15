"""
PathMind intelligence pack — internal endpoints.

The counselor calls these server-side; they are also the smoke-test surface
for the pack (see the integration report). Auth is consistent with other
reads (authenticated person via Depends).

Guardrails (non-negotiable):
  - readiness output is a SCREENING HEURISTIC, never a diagnosis — the
    disclaimer travels in every response.
  - profession salaries are ESTIMATES, always labeled as such.
"""

from typing import Any, Dict, List, Optional
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from backend.core.security import get_authenticated_person
from backend.services.intelligence_service import (
    PROFESSIONS_KB_VERSION,
    READINESS_MODEL_VERSION,
    RESOURCES_KB_VERSION,
    get_intelligence_service,
)

router = APIRouter(prefix="/api/intelligence", tags=["Intelligence Pack"])


class ReadinessRequest(BaseModel):
    text: str


@router.post("/readiness")
async def predict_readiness(
    req: ReadinessRequest,
    person_id: str = Depends(get_authenticated_person),
) -> Dict[str, Any]:
    """
    Classify free text into a readiness-to-change stage.
    Returns {stage, confidence, note, model_version, assessed_at}.
    `note` carries the screening-heuristic disclaimer — it must travel
    with the prediction into storage and any downstream use.
    """
    service = get_intelligence_service()
    if not service.available:
        raise HTTPException(
            status_code=503,
            detail=f"Readiness classifier unavailable: {service.load_error}",
        )
    result = service.predict_readiness(req.text)
    if result is None:
        raise HTTPException(status_code=500, detail="Readiness prediction failed")
    return result


@router.get("/resources")
async def search_resources(
    q: str = Query(..., min_length=2, description="Search query"),
    k: int = Query(5, ge=1, le=20),
    person_id: str = Depends(get_authenticated_person),
) -> Dict[str, Any]:
    """
    Retrieve Indian learning-resource entries (curated, verified, ML-indexed
    knowledge — NOT a "trained model"). Names/URLs/costs come from the entry.
    """
    service = get_intelligence_service()
    if not service.available:
        raise HTTPException(
            status_code=503,
            detail=f"Resources KB unavailable: {service.load_error}",
        )
    hits = service.retrieve_resources(q, k=k)
    return {
        "query": q,
        "kb_version": RESOURCES_KB_VERSION,
        "results": [
            {"entry": h["entry"], "score": round(h["score"], 4)} for h in hits
        ],
    }


@router.get("/professions")
async def search_professions(
    q: str = Query(..., min_length=2, description="Search query"),
    k: int = Query(5, ge=1, le=20),
    person_id: str = Depends(get_authenticated_person),
) -> Dict[str, Any]:
    """
    Retrieve profession entries with balanced pros/cons and entry paths.
    Salaries in entries are ESTIMATES — always labeled as such downstream.
    """
    service = get_intelligence_service()
    if not service.available:
        raise HTTPException(
            status_code=503,
            detail=f"Professions KB unavailable: {service.load_error}",
        )
    hits = service.retrieve_professions(q, k=k)
    return {
        "query": q,
        "kb_version": PROFESSIONS_KB_VERSION,
        "results": [
            {"entry": h["entry"], "score": round(h["score"], 4)} for h in hits
        ],
    }


@router.get("/health")
async def intelligence_health() -> Dict[str, Any]:
    """Pack health without auth (mirrors /health/live pattern)."""
    service = get_intelligence_service()
    return {
        "available": service.available,
        "load_error": service.load_error,
        "readiness_model_version": READINESS_MODEL_VERSION,
        "resources_kb_version": RESOURCES_KB_VERSION,
        "professions_kb_version": PROFESSIONS_KB_VERSION,
    }


def fetch_live_jobs(
    query: str, limit: int = 5, _get=None
) -> List[Dict[str, Any]]:
    """
    Live job postings via the Arbeitnow API (free, no key).
    Every result is labeled with source + fetched_at — observed data, never
    presented as PathMind-curated. Fail-soft: [] on any failure. `_get` is
    injectable for hermetic tests.
    """
    get = _get or __import__("httpx").get
    try:
        resp = get(
            "https://www.arbeitnow.com/api/job-board-api",
            params={"search": query},
            timeout=8,
        )
        data = resp.json().get("data") or []
    except Exception:
        return []
    out = []
    for j in data[: max(1, min(limit, 20))]:
        if not isinstance(j, dict):
            continue
        out.append({
            "title": j.get("title"),
            "company": j.get("company_name"),
            "location": j.get("location"),
            "remote": j.get("remote"),
            "url": j.get("url"),
            "posted_at": j.get("created_at"),
            "source": "arbeitnow.com",
            "fetched_at": datetime.now(timezone.utc).isoformat(),
        })
    return [j for j in out if j.get("title") and j.get("url")]


@router.get("/jobs")
async def search_jobs(
    q: str = Query(..., min_length=2, description="Job search query"),
    k: int = Query(5, ge=1, le=20),
    person_id: str = Depends(get_authenticated_person),
) -> Dict[str, Any]:
    """
    Live open roles (observed postings, source-labeled) to ground the
    professions KB's estimates in reality. Empty list when the upstream is
    unreachable — never fabricated.
    """
    return {
        "query": q,
        "results": fetch_live_jobs(q, limit=k),
        "disclaimer": "Live postings via arbeitnow.com (free API). "
                      "Listings change constantly — verify on the source page.",
    }
