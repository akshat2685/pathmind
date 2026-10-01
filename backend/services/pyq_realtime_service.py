"""
Real-time PYQ retrieval for PATHMIND College Engineering MVP.

Learner-scoped, progressive delivery:
- scope="subject": PYQs for ONE subject only (e.g. "Physics, Sem 1").
- scope="program": the learner's whole branch/semester, delivered in LEVELS
  (level 1 = most recent papers to start with, level 2 = wider bank,
  level 3 = everything found) — never everything at once.

Retrieval order: seeded DB first, then REAL-TIME search of the university's
official website via Tavily (include_domains restricted to official domains).
When the official website yields nothing verified, a second stage searches
public exam archives (no domain restriction) — a hit counts only if it is
attributable to this university (subject code or university name present),
and every paper is labeled with its source domain and trust tier, so an
archive mirror is never presented as the university's own website.
Every paper is directly downloadable by the learner.

Strict authenticity: never invents papers. Returns PYQ_NOT_AVAILABLE when
nothing verified is found.
"""

import asyncio
import os
import re
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
    # Exam years must be plausible: 1990..current year. Page numbers or PDF
    # metadata often produce bogus matches (e.g. 2072, 2092) — reject those
    # rather than showing impossible "exam years" to the learner.
    now_year = datetime.now(timezone.utc).year
    for t in texts:
        if not t:
            continue
        m = _YEAR_RE.search(t)
        if m:
            y = int(m.group(0))
            if 1990 <= y <= now_year:
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


async def _tavily_search(query: str, include_domains: Optional[List[str]],
                         max_results: int = 10) -> List[Dict[str, Any]]:
    """One Tavily search. include_domains=None searches the open web."""
    api_key = os.environ.get("TAVILY_API_KEY")
    if not api_key:
        return []
    if include_domains is not None and not include_domains:
        return []
    payload: Dict[str, Any] = {
        "api_key": api_key,
        "query": query,
        "max_results": max_results,
        "search_depth": "advanced",
        "include_answer": False,
    }
    if include_domains:
        payload["include_domains"] = include_domains
    try:
        async with httpx.AsyncClient(timeout=25.0) as http:
            resp = await http.post(TAVILY_API_URL, json=payload)
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


async def _tavily_search_official(query: str, include_domains: List[str],
                                  max_results: int = 10) -> List[Dict[str, Any]]:
    """Tavily search restricted to official university domains."""
    return await _tavily_search(query, include_domains, max_results=max_results)


async def _tavily_search_web(query: str,
                             max_results: int = 10) -> List[Dict[str, Any]]:
    """Tavily search over the open web (public exam archives)."""
    return await _tavily_search(query, None, max_results=max_results)


def _attested(hit: Dict[str, Any], univ_terms: List[str],
              subject_code: Optional[str]) -> bool:
    """Attribution guard for open-web hits.

    A public-archive hit counts as THIS university's paper only when the
    subject code or the university's name appears in its title, snippet or
    URL. Without this, an unrestricted search returns other universities'
    papers for the same subject name and the vault would show the wrong
    exam — worse than showing nothing.
    """
    blob = f"{hit.get('title', '')} {hit.get('snippet', '')} {hit.get('url', '')}".lower()
    code_l = (subject_code or "").strip().lower()
    if code_l and code_l in blob:
        return True
    return any(
        t and re.search(rf"\b{re.escape(t)}\b", blob) for t in univ_terms)


def _is_lab_subject(subject_name: Optional[str]) -> bool:
    return bool(re.search(r"\blab\b|laboratory", (subject_name or "").lower()))


def _paper_from_hit(hit: Dict[str, Any], *, subject_name: Optional[str],
                    university_id: str, retrieval: str,
                    source_kind: str = "official") -> Dict[str, Any]:
    year = _extract_year(hit.get("title", ""), hit.get("snippet", ""), hit.get("url", ""))
    return {
        "paper_id": f"rt-{abs(hash(hit['url'])) % 10**10}",
        "title": hit["title"] or "University question paper",
        "url": hit["url"],
        "download_url": hit["url"],
        "year": year,
        "subject_name": subject_name,
        "university_id": university_id,
        # "official" = the university's own website; "archive" = a public
        # exam-archive mirror. The UI shows this on every paper so a
        # mirror is never mistaken for the university's own site.
        "source_kind": source_kind,
        "source_domain": hit["source_domain"],
        "trust_tier": hit["trust_tier"],
        "retrieval": retrieval,  # "seeded" | "realtime" | "archive"
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
                "source_kind": "official",
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
                             subject_code: Optional[str] = None,
                             topic: Optional[str] = None,
                             scope: str = "subject",
                             max_results: int = 10) -> List[Dict[str, Any]]:
    """
    Find real question papers for a subject (or the whole program).

    Stage 1 searches the university's OFFICIAL website (Tavily
    include_domains). Stage 2 — only when stage 1 finds nothing
    verified, as for universities that publish no papers on their own
    domain — searches public exam archives, with an attribution guard
    and per-paper source labeling. Never invents papers.
    """
    domains = await _get_official_domains(university_id)
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
        if subject_code:
            # University paper archives are indexed by subject CODE
            # (e.g. RTU files IoT under 7CS4-01), not by subject name —
            # name-only queries miss the real papers entirely.
            queries = [
                f"{univ_short} {subject_code} question paper",
                f"{subject_code} {subject_name} question paper pdf",
            ] + queries
        if topic:
            # The learner's current level (plan phase): bias retrieval
            # toward papers for this unit instead of the whole subject.
            queries.append(
                f"{univ_short} {subject_code or subject_name} {topic} "
                f"question paper")
    else:
        queries = [
            f"{univ_short} {branch} semester {semester} question papers",
            f"{univ_short} B.Tech {branch} previous year question papers",
        ]

    code_l = (subject_code or "").strip().lower()
    topic_tokens = {
        t for t in re.findall(r"[a-z0-9]+", (topic or "").lower())
        if len(t) >= 4 and t not in ("unit", "part", "course", "subject")
    }

    def _relevance(p: Dict[str, Any]) -> int:
        # Prefer hits that actually look like question papers over generic
        # university PDFs (syllabi, notices) that Tavily also returns.
        blob = f"{p['title']} {p['url']}".lower()
        score = 0
        if code_l and code_l in blob:
            score += 3
        for kw in ("question paper", "questionpaper", "previous year", "end semester",
                   "mid semester", "model paper", "sample paper"):
            if kw in blob:
                score += 2
        if blob.rstrip("/").endswith(".pdf"):
            score += 1
        # Official archives index syllabi, schemes and notices by the same
        # subject code — they are not previous-year papers and must never
        # reach the vault, even when the code matches.
        for kw in ("syllabus", "scheme of", "curriculum", "notice",
                   "circular", "timetable", "time table", "date sheet",
                   "datesheet", "result"):
            if kw in blob:
                score -= 4
        if topic_tokens:
            blob_tokens = set(re.findall(r"[a-z0-9]+", blob))
            score += 2 * min(len(topic_tokens & blob_tokens), 2)
        return score

    official = set(domains)

    def _collect(hits: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Hits → papers with provenance, relevance filter, best first.

        provenance is by the hit's actual domain: anything on the
        university's official domain is "official"; anything else is a
        public exam-archive mirror and is labeled as such.
        """
        out = []
        for h in hits:
            is_official = h["source_domain"] in official
            out.append(_paper_from_hit(
                h, subject_name=subject_name, university_id=university_id,
                retrieval="realtime" if is_official else "archive",
                source_kind="official" if is_official else "archive"))
        # The vault shows previous-year papers only — never every PDF the
        # search happens to surface. Hits with no paper signal at all
        # (syllabi, notices, circulars) are dropped, not just ranked last.
        out = [p for p in out if _relevance(p) >= 2]
        # Most relevant first, then most recent; undated papers last.
        out.sort(key=lambda p: (-_relevance(p), p["year"] is None,
                                -(p["year"] or 0)))
        return out

    # Stage 1: the university's official website only. Some universities
    # (RTU among them) publish no indexable question papers on their own
    # domain — their official pages that do surface are syllabi and
    # notices, which the relevance filter correctly rejects. Queries run
    # in parallel: sequentially this took ~25s and made the vault feel
    # broken before it had even answered.
    stage1 = await asyncio.gather(*(
        _tavily_search_official(q, domains, max_results=max_results)
        for q in queries))
    seen: Dict[str, Dict[str, Any]] = {}
    for hits in stage1:
        for hit in hits:
            seen.setdefault(hit["url"], hit)
    papers = _collect(list(seen.values()))

    if not papers:
        # Stage 2: public exam archives (aggregator mirrors of the same
        # real papers). Every hit must be attributable to THIS university
        # (subject code or university name) and still passes the paper
        # relevance bar. Papers carry their source domain + trust tier,
        # and mirrors are labeled — never shown as official sources.
        univ_terms = list({univ_short.lower(), university_id.lower()})
        stage2 = await asyncio.gather(*(
            _tavily_search_web(q, max_results=max_results)
            for q in queries))
        web_seen: Dict[str, Dict[str, Any]] = {}
        for hits in stage2:
            for hit in hits:
                if hit["url"] in seen:
                    continue
                if _attested(hit, univ_terms, subject_code):
                    web_seen.setdefault(hit["url"], hit)
        papers = _collect(list(web_seen.values()))
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
                          subject_code: Optional[str] = None,
                          topic: Optional[str] = None,
                          scope: str = "subject",
                          level: int = 1) -> Dict[str, Any]:
    """
    Learner-scoped PYQ retrieval.

    scope="subject": only this subject's papers (e.g. Physics, Sem 1).
    Level-windowed like the program scope: start with the most recent
    papers, unlock older ones on demand.
    scope="program": the branch/semester's papers in progressive levels.
    """
    scope = scope if scope in ("subject", "program") else "subject"
    level = level if level in (1, 2, 3) else 1

    papers: List[Dict[str, Any]] = []
    # 1) Seeded/curated papers first (subject scope only).
    if scope == "subject":
        papers.extend(await _seeded_papers(university_id, subject_id))

    # 2) Real-time retrieval: the university's official website first,
    # public exam archives (attested, labeled) when the official site
    # has nothing verified.
    if not papers or scope == "program":
        realtime = await realtime_pyq_search(
            university_id=university_id, branch=branch, semester=semester,
            subject_name=subject_name, subject_code=subject_code,
            topic=topic, scope=scope, max_results=10)
        known_urls = {p["url"] for p in papers if p.get("url")}
        papers.extend([p for p in realtime if p["url"] not in known_urls])

    # Progressive levels for BOTH scopes: start with the most recent
    # papers, unlock older ones on demand — never the whole archive
    # at once.
    level_label = PROGRAM_LEVELS[level][0]
    windowed = apply_program_level(papers, level)
    # Computed against the un-windowed list and the WIDEST level: a
    # paper from 2019 is invisible at Levels 1 AND 2, so "next level
    # has more" would dead-end the learner one step early. The empty
    # case must never report no-more-levels while papers exist.
    has_more = (level < 3
                and len(apply_program_level(papers, 3)) > len(windowed))
    papers = windowed

    if not papers:
        where = (f"for {subject_name or subject_id}" if scope == "subject"
                 else f"for {branch}, semester {semester}")
        if has_more:
            message = (
                f"No recent papers {where} at Level {level} — but older "
                f"papers exist in the wider archive. Unlock Level "
                f"{level + 1} to see them. No synthetic questions are "
                f"substituted."
            )
        elif scope == "subject" and _is_lab_subject(subject_name):
            # Labs are normally assessed by practical work + viva, not a
            # written end-semester paper — say so instead of implying the
            # archive is merely empty.
            message = (
                f"No written question papers found {where}. Lab subjects "
                f"are usually assessed by practical work and a viva "
                f"rather than a written end-semester paper, so verified "
                f"papers may not exist for this subject. Try Whole "
                f"program for this semester's written papers. "
                f"No synthetic questions are substituted."
            )
        else:
            message = (
                f"No verified previous year question papers found {where} "
                f"on the university's official website or in public exam "
                f"archives right now. No synthetic questions are "
                f"substituted — try again later or pick a different "
                f"subject."
            )
        return {
            "status": "PYQ_NOT_AVAILABLE",
            "scope": scope,
            "level": level,
            "level_label": level_label,
            "papers": [],
            "total_found": 0,
            "has_more_levels": has_more,
            "message": message,
        }

    if any(p.get("source_kind") == "archive" for p in papers):
        # Some papers are public-archive mirrors: say so plainly. Each
        # paper still shows its own source domain and trust tier.
        message = (
            f"Found {len(papers)} real question paper(s) ({level_label}). "
            f"Every paper shows its source — the university's official "
            f"website or a public exam archive. Nothing here is invented."
        )
    else:
        message = (
            f"Found {len(papers)} question paper(s) from official "
            f"university sources ({level_label}). Each paper is "
            f"downloadable from its official source link."
        )
    return {
        "status": "VERIFIED",
        "scope": scope,
        "level": level,
        "level_label": level_label,
        "papers": papers,
        "total_found": len(papers),
        "has_more_levels": has_more,
        "study_phase": "pyq",
        "message": message,
    }
