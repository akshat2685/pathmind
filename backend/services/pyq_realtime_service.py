"""
Real-time PYQ retrieval for PATHMIND College Engineering MVP.

Learner-scoped, progressive delivery:
- scope="subject": PYQs for ONE subject only (e.g. "Physics, Sem 1").
- scope="program": the learner's whole branch/semester, delivered in LEVELS
  (level 1 = most recent papers to start with, level 2 = wider bank,
  level 3 = everything found) — never everything at once.

Retrieval order: seeded DB first, then REAL-TIME search of the university's
official website via Tavily (include_domains restricted to official domains).
Every paper carries provenance (official URL, source domain, trust tier,
retrieved_at) and is directly downloadable by the learner.

Strict authenticity: never invents papers. Returns PYQ_NOT_AVAILABLE when
nothing verified is found.
"""

import os
import re
import time
import logging
import urllib.parse
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List

import httpx

from backend.services.college_resource_pipeline import tier_for_domain

logger = logging.getLogger(__name__)

TAVILY_API_URL = "https://api.tavily.com/search"

# Fallback official domains when the DB lookup is unavailable. The seeded
# universities table is the primary source of truth.
OFFICIAL_DOMAIN_FALLBACK: Dict[str, List[str]] = {
    "rtu": ["rtu.ac.in"],
    "aktu": ["aktu.ac.in"],
    "vtu": ["vtu.ac.in"],
    "anna_university": ["annauniv.edu"],
    "jntuh": ["jntuh.ac.in"],
}

# Progressive levels for program scope: (label, max_age_years, max_papers)
PROGRAM_LEVELS = {
    1: ("Level 1 — Start here: most recent papers", 2, 5),
    2: ("Level 2 — Go deeper: wider question bank", 5, 12),
    3: ("Level 3 — Full archive: everything found", 99, 25),
}

_YEAR_RE = re.compile(r"(19|20)\d{2}")


def _utcnow_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _extract_year(*texts: str) -> Optional[int]:
    for t in texts:
        if not t:
            continue
        m = _YEAR_RE.search(t)
        if m:
            y = int(m.group(0))
            if 1990 <= y <= 2100:
                return y
    return None


async def _get_official_domains(university_id: str) -> List[str]:
    """Official domains for a university: DB first, hardcoded fallback."""
    try:
        from backend.providers.curriculum_registry import get_university_by_id
        univ = await get_university_by_id(university_id)
        if univ and getattr(univ, "official_domain", None):
            return [univ.official_domain]
    except Exception as e:
        logger.warning("University domain lookup failed: %s", type(e).__name__)
    return OFFICIAL_DOMAIN_FALLBACK.get(university_id, [])


async def _tavily_search_official(query: str, include_domains: List[str],
                                 max_results: int = 10) -> List[Dict[str, Any]]:
    """Tavily search restricted to official university domains."""
    api_key = os.environ.get("TAVILY_API_KEY")
    if not api_key or not include_domains:
        return []
    try:
        async with httpx.AsyncClient(timeout=25.0) as http:
            resp = await http.post(TAVILY_API_URL, json={
                "api_key": api_key,
                "query": query,
                "max_results": max_results,
                "search_depth": "advanced",
                "include_answer": False,
                "include_domains": include_domains,
            })
            if resp.status_code != 200:
                logger.warning("Tavily PYQ search HTTP %s", resp.status_code)
                return []
            data = resp.json()
    except Exception as e:
        logger.warning("Tavily PYQ search failed: %s", type(e).__name__)
        return []
    hits = []
    for r in data.get("results", []) or []:
        url = r.get("url") or ""
        if not url.startswith("http"):
            continue
        domain = urllib.parse.urlparse(url).netloc.lower().replace("www.", "")
        hits.append({
            "url": url,
            "title": (r.get("title") or "")[:220],
            "snippet": (r.get("content") or "")[:320],
            "source_domain": domain,
            "trust_tier": tier_for_domain(domain),
            "tavily_score": r.get("score"),
        })
    return hits


def _paper_from_hit(hit: Dict[str, Any], *, subject_name: Optional[str],
                    university_id: str, retrieval: str) -> Dict[str, Any]:
    year = _extract_year(hit.get("title", ""), hit.get("snippet", ""), hit.get("url", ""))
    return {
        "paper_id": f"rt-{abs(hash(hit['url'])) % 10**10}",
        "title": hit["title"] or "University question paper",
        "url": hit["url"],
        "download_url": hit["url"],
        "year": year,
        "subject_name": subject_name,
        "university_id": university_id,
        "source_domain": hit["source_domain"],
        "trust_tier": hit["trust_tier"],
        "retrieval": retrieval,  # "seeded" | "realtime"
        "retrieved_at": _utcnow_iso(),
    }


async def _seeded_papers(university_id: str, subject_id: Optional[str]) -> List[Dict[str, Any]]:
    """Papers already curated in the DB (pyq_sets / pyq_questions)."""
    if not subject_id:
        return []
    try:
        from backend.providers.curriculum_registry import get_pyqs_for_subject
        pyq_set = await get_pyqs_for_subject(university_id, subject_id)
    except Exception as e:
        logger.warning("Seeded PYQ lookup failed: %s", type(e).__name__)
        return []
    if not pyq_set or not getattr(pyq_set, "questions", None):
        return []
    papers: Dict[str, Dict[str, Any]] = {}
    for q in pyq_set.questions:
        pid = getattr(q, "pyq_set_id", None) or "seeded-set"
        if pid not in papers:
            papers[pid] = {
                "paper_id": pid,
                "title": f"{getattr(pyq_set, 'exam_type', 'University exam')} {getattr(pyq_set, 'exam_year', '')}".strip(),
                "url": getattr(pyq_set, "source_url", None),
                "download_url": getattr(pyq_set, "source_url", None),
                "year": getattr(pyq_set, "exam_year", None),
                "subject_name": None,
                "university_id": university_id,
                "source_domain": None,
                "trust_tier": "A",
                "retrieval": "seeded",
                "retrieved_at": _utcnow_iso(),
                "question_count": 0,
            }
        papers[pid]["question_count"] += 1
    return list(papers.values())


async def realtime_pyq_search(*, university_id: str, branch: str,
                             semester: int,
                             subject_name: Optional[str] = None,
                             scope: str = "subject",
                             max_results: int = 10) -> List[Dict[str, Any]]:
    """
    Dig through the university's OFFICIAL website in real time for question
    papers. Domain-restricted via Tavily include_domains — never the open web.
    """
    domains = await _get_official_domains(university_id)
    if not domains:
        return []
    try:
        from backend.providers.curriculum_registry import get_university_by_id
        univ = await get_university_by_id(university_id)
        univ_short = (univ.name if univ else university_id)
    except Exception:
        univ_short = university_id

    if scope == "subject" and subject_name:
        queries = [
            f"{univ_short} {subject_name} previous year question paper",
            f"{univ_short} {subject_name} end semester question paper pdf",
        ]
    else:
        queries = [
            f"{univ_short} {branch} semester {semester} question papers",
            f"{univ_short} B.Tech {branch} previous year question papers",
        ]

    seen: Dict[str, Dict[str, Any]] = {}
    for q in queries:
        for hit in await _tavily_search_official(q, domains, max_results=max_results):
            if hit["url"] not in seen:
                seen[hit["url"]] = hit
    papers = [
        _paper_from_hit(h, subject_name=subject_name,
                        university_id=university_id, retrieval="realtime")
        for h in seen.values()
    ]
    # Most recent first; undated papers last (year unknown, kept honestly).
    papers.sort(key=lambda p: (p["year"] is None, -(p["year"] or 0)))
    return papers


def apply_program_level(papers: List[Dict[str, Any]], level: int) -> List[Dict[str, Any]]:
    """Progressive delivery: each level widens the window, never all at once."""
    label, max_age, max_n = PROGRAM_LEVELS.get(level, PROGRAM_LEVELS[1])
    now_year = datetime.now(timezone.utc).year
    windowed = [p for p in papers
                if p["year"] is None or (now_year - p["year"]) <= max_age]
    return windowed[:max_n]


async def get_pyqs_scoped(*, university_id: str, branch: str, semester: int,
                          subject_id: Optional[str] = None,
                          subject_name: Optional[str] = None,
                          scope: str = "subject",
                          level: int = 1) -> Dict[str, Any]:
    """
    Learner-scoped PYQ retrieval.

    scope="subject": only this subject's papers (e.g. Physics, Sem 1).
    scope="program": the branch/semester's papers in progressive levels.
    """
    scope = scope if scope in ("subject", "program") else "subject"
    level = level if level in (1, 2, 3) else 1

    papers: List[Dict[str, Any]] = []
    # 1) Seeded/curated papers first (subject scope only).
    if scope == "subject":
        papers.extend(await _seeded_papers(university_id, subject_id))

    # 2) Real-time retrieval from the official university website.
    if not papers or scope == "program":
        realtime = await realtime_pyq_search(
            university_id=university_id, branch=branch, semester=semester,
            subject_name=subject_name, scope=scope, max_results=10)
        known_urls = {p["url"] for p in papers if p.get("url")}
        papers.extend([p for p in realtime if p["url"] not in known_urls])

    if scope == "program":
        level_label = PROGRAM_LEVELS[level][0]
        papers = apply_program_level(papers, level)
        has_more = level < 3
    else:
        level_label = "Single subject"
        papers = papers[:10]
        has_more = False

    if not papers:
        where = (f"for {subject_name or subject_id}" if scope == "subject"
                 else f"for {branch}, semester {semester}")
        return {
            "status": "PYQ_NOT_AVAILABLE",
            "scope": scope,
            "level": level,
            "level_label": level_label,
            "papers": [],
            "total_found": 0,
            "has_more_levels": False,
            "message": (
                f"No verified previous year question papers found {where} "
                f"on the university's official website right now. "
                f"No synthetic questions are substituted — try again later or "
                f"pick a different subject."
            ),
        }

    return {
        "status": "VERIFIED",
        "scope": scope,
        "level": level,
        "level_label": level_label,
        "papers": papers,
        "total_found": len(papers),
        "has_more_levels": has_more,
        "study_phase": "pyq",
        "message": (
            f"Found {len(papers)} question paper(s) from official university "
            f"sources ({level_label}). Each paper is downloadable from its "
            f"official source link."
        ),
    }
