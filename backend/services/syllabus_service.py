"""
Syllabus source service for PATHMIND College Engineering MVP.

Given university + branch + semester, returns the syllabus the learner
should study from:
1. Seeded verified curriculum (subjects + units) when present.
2. Otherwise REAL-TIME lookup: dig through the university's official website
   (Tavily, domain-restricted) for the official syllabus PDF.

Never invents syllabus content. SYLLABUS_NOT_AVAILABLE when nothing
verifiable is found.
"""

import logging
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List

from backend.services.pyq_realtime_service import (
    _get_official_domains,
    _tavily_search_official,
    _utcnow_iso,
)
from backend.services.college_resource_pipeline import tier_for_domain
from backend.core.college_schemas import EngineeringBranch

logger = logging.getLogger(__name__)


def _to_branch(branch: str) -> EngineeringBranch:
    try:
        return EngineeringBranch(branch)
    except ValueError:
        return EngineeringBranch.GENERAL_OTHER


async def get_syllabus_source(*, university_id: str, branch: str,
                             semester: int) -> Dict[str, Any]:
    # 1) Seeded verified curriculum.
    subjects: list = []
    try:
        from backend.providers.curriculum_registry import get_curriculum
        curriculum = await get_curriculum(university_id, _to_branch(branch), semester)
        if curriculum and getattr(curriculum, "subjects", None):
            subjects = curriculum.subjects
    except Exception as e:
        logger.warning("Seeded curriculum lookup failed: %s", type(e).__name__)
    if subjects:
        return {
            "status": "VERIFIED",
            "source": "seeded",
            "university_id": university_id,
            "branch": branch,
            "semester": semester,
            "subjects": [
                {
                    "subject_id": getattr(s, "subject_id", None),
                    "code": getattr(s, "code", None),
                    "name": getattr(s, "name", None),
                    "credits": getattr(s, "credits", None),
                }
                for s in subjects
            ],
            "syllabus_url": None,
            "message": (
                f"Verified syllabus for {branch}, semester {semester}: "
                f"{len(subjects)} subjects from the curated curriculum."
            ),
        }

    # 2) Real-time: find the official syllabus PDF on the university site.
    domains = await _get_official_domains(university_id)
    hits: List[Dict[str, Any]] = []
    if domains:
        try:
            from backend.providers.curriculum_registry import get_university_by_id
            univ = await get_university_by_id(university_id)
            univ_name = univ.name if univ else university_id
        except Exception:
            univ_name = university_id
        query = f"{univ_name} {branch} semester {semester} syllabus pdf"
        for hit in await _tavily_search_official(query, domains, max_results=6):
            url = hit["url"].lower()
            if url.endswith(".pdf") or "syllabus" in url or "syllabus" in hit["title"].lower():
                hits.append({
                    "title": hit["title"],
                    "url": hit["url"],
                    "download_url": hit["url"],
                    "source_domain": hit["source_domain"],
                    "trust_tier": hit["trust_tier"],
                    "retrieval": "realtime",
                    "retrieved_at": _utcnow_iso(),
                })
    if hits:
        return {
            "status": "REALTIME",
            "source": "realtime",
            "university_id": university_id,
            "branch": branch,
            "semester": semester,
            "subjects": [],
            "syllabus_url": hits[0]["url"],
            "candidates": hits,
            "message": (
                f"No curated syllabus on file — found the official syllabus "
                f"document on the university website in real time. Verify it "
                f"matches your scheme year before studying from it."
            ),
        }

    return {
        "status": "SYLLABUS_NOT_AVAILABLE",
        "source": None,
        "university_id": university_id,
        "branch": branch,
        "semester": semester,
        "subjects": [],
        "syllabus_url": None,
        "message": (
            f"No verifiable syllabus found for {branch}, semester {semester} "
            f"right now — neither curated nor on the official university "
            f"website. Nothing is guessed."
        ),
    }
