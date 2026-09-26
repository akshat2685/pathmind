"""
Resource research pipeline for the PathMind College MVP (TRD §7–9, §13).

Live internet research for plan-time resources. Honest by construction:

  - Every resource URL comes from a real search/API result, never fabricated.
  - Every URL is reachability-checked (HTTP HEAD/GET) before being marked
    VERIFIED. Unreachable URLs are rejected, never promoted.
  - Aggressive caching in Supabase (source_records / resource_records /
    learning_resources) so repeated plans do not re-research.
  - Video resources carry timestamps: real chapters parsed from YouTube
    descriptions where available, clearly labeled "estimated" otherwise.

Provider priority (free-tier only, no keys required for the primary):
  1. DuckDuckGo HTML endpoint (no API key)
  2. Tavily search API (backup; needs TAVILY_API_KEY env)
  3. YouTube Data API v3 (video metadata + statistics; needs YOUTUBE_API_KEY)
  4. youtube-transcript-api (transcript/chapter extraction; no key)

All network I/O is async httpx with short timeouts and a global time budget
(Vercel caps execution at 60s). No LLM calls in this module — verification
signals are deterministic (status codes, domain tiers, view/like counts).
"""

from __future__ import annotations

import hashlib
import logging
import os
import re
import time
import urllib.parse
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import httpx

from backend.core.college_logging import log_event, timed_stage

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Deterministic tier rules (TRD §9). Domain authority is observable, not
# model-judged: suffix/infix lists only.
# ---------------------------------------------------------------------------

_TIER_A_INFIXES = (
    ".ac.in",          # Indian universities
    ".edu",            # generic universities
    "ugc.gov.in",
    "aicte-india.org",
)
_TIER_B_INFIXES = (
    "nptel.ac.in",
    "swayam.gov.in",
    "iitb.ac.in", "iitm.ac.in", "iitd.ac.in", "iitkgp.ac.in",
    "iitk.ac.in", "iitr.ac.in", "iitg.ac.in",
)
_TIER_C_DOMAINS = (
    "geeksforgeeks.org",
    "tutorialspoint.com",
    "javatpoint.com",
    "coursera.org",
    "edx.org",
    "khanacademy.org",
    "udemy.com",
)
# Official YouTube channels of tier-A/B institutions are promoted.
_OFFICIAL_YT_HANDLES = ("nptel", "iit", "swayam", "ugc")

YOUTUBE_API_URL = "https://www.googleapis.com/youtube/v3"
TAVILY_API_URL = "https://api.tavily.com/search"
DDG_HTML_URL = "https://html.duckduckgo.com/html/"


def tier_for_domain(domain: str) -> str:
    """Deterministic TRD §9 tier assignment from an observable domain."""
    d = (domain or "").lower()
    if any(inf in d for inf in _TIER_A_INFIXES):
        return "A"
    if any(inf in d for inf in _TIER_B_INFIXES):
        return "B"
    if d in _TIER_C_DOMAINS or any(d.endswith(x) for x in _TIER_C_DOMAINS):
        return "C"
    if "youtube.com" in d or "youtu.be" in d:
        return "D"  # promoted to B only if an official channel is confirmed
    return "D"


def _chapter_ts_to_seconds(ts: str) -> int:
    parts = [int(p) for p in ts.split(":")]
    total = 0
    for p in parts:
        total = total * 60 + p
    return total


_TIMESTAMP_RE = re.compile(
    r"(?P<ts>(?:\d{1,2}:)?\d{1,2}:\d{2})\s+[-–—:\s]*(?P<label>[^\n]{3,80})"
)


def parse_video_chapters(description: str) -> List[Dict[str, Any]]:
    """
    Parse real chapter timestamps from a YouTube description.
    Only real timestamped lines are kept; nothing is invented.
    """
    chapters: List[Dict[str, Any]] = []
    for match in _TIMESTAMP_RE.finditer(description or ""):
        try:
            start = _chapter_ts_to_seconds(match.group("ts"))
        except ValueError:
            continue
        label = match.group("label").strip()
        if label and start >= 0:
            chapters.append({"start_seconds": start, "label": label})
    # Deduplicate while preserving order.
    seen = set()
    unique: List[Dict[str, Any]] = []
    for ch in sorted(chapters, key=lambda c: c["start_seconds"]):
        key = (ch["start_seconds"], ch["label"].lower())
        if key not in seen:
            seen.add(key)
            unique.append(ch)
    return unique


class CollegeResourcePipeline:
    """Live research + verification + caching for learning resources."""

    def __init__(self, store=None):
        # Imported lazily to avoid circulars in test collection.
        from backend.services.college_store import college_store as _default_store
        self.store = store or _default_store
        self._tavily_key = os.environ.get("TAVILY_API_KEY")
        self._youtube_key = os.environ.get("YOUTUBE_API_KEY")

    # ------------------------------------------------------------------
    # Public entry points
    # ------------------------------------------------------------------

    async def get_verified_resources(
        self,
        subject_id: str,
        topic: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Return VERIFIED cached resources for a subject (+ optional topic).

        Never fabricates: when nothing cached is verified, returns an explicit
        RESOURCE_ENRICHMENT_PENDING status so the caller can offer the
        /resources/enrich endpoint instead of showing unverified links.
        """
        try:
            rows = self._read_cache(subject_id, topic)
        except Exception as e:  # pragma: no cover - defensive
            logger.error("Resource cache read failed: %s", str(e))
            return {"status": "RESOURCE_UNAVAILABLE", "resources": [],
                    "message": "PERSISTENCE_UNAVAILABLE"}
        if rows:
            return {"status": "VERIFIED", "resources": rows}
        return {
            "status": "RESOURCE_ENRICHMENT_PENDING",
            "resources": [],
            "message": (
                "No verified resources are cached for this topic yet. "
                "Run POST /api/college/resources/enrich to research them live."
            ),
        }

    async def research_topic(
        self,
        subject_id: str,
        topic: str,
        university_name: Optional[str] = None,
        subject_name: Optional[str] = None,
        time_budget_seconds: float = 45.0,
    ) -> Dict[str, Any]:
        """
        Bounded live research for one topic. Writes VERIFIED records into
        source_records / resource_records / learning_resources.

        Returns {"status": ..., "resources_added": int, "resources": [...]}.
        """
        deadline = time.monotonic() + max(5.0, float(time_budget_seconds))
        with timed_stage("college.resources.research", subject_id=subject_id,
                         topic=topic):
            queries = self._build_queries(
                subject_id=subject_id, subject_name=subject_name,
                topic=topic, university_name=university_name)
            candidates: List[Dict[str, Any]] = []
            seen_urls: set = set()

            # 1. Web search: DuckDuckGo primary, Tavily backup.
            for q in queries[:3]:
                if time.monotonic() > deadline:
                    break
                for hit in await self._search_web(q, deadline):
                    url = hit.get("url", "")
                    if not url or url in seen_urls:
                        continue
                    seen_urls.add(url)
                    candidates.append({
                        "kind": "WEB", "url": url, "title": hit.get("title", ""),
                        "snippet": hit.get("snippet", ""),
                        "provider": hit.get("provider", "web"),
                        "quality_signals": hit.get("quality_signals", {}),
                    })

            # 2. YouTube research (metadata + statistics + chapters).
            if time.monotonic() <= deadline:
                for q in queries[:2]:
                    if time.monotonic() > deadline:
                        break
                    for video in await self._search_youtube(q, deadline):
                        url = video.get("url", "")
                        if not url or url in seen_urls:
                            continue
                        seen_urls.add(url)
                        candidates.append({"kind": "VIDEO", **video})

            # 3. Verify reachability + persist the survivors.
            added: List[Dict[str, Any]] = []
            async with httpx.AsyncClient(
                    timeout=12.0, follow_redirects=True,
                    headers={"User-Agent": "PathMind-CollegeMVP/1.0"}) as http:
                for cand in candidates:
                    if time.monotonic() > deadline:
                        break
                    record = await self._verify_and_persist(
                        http, cand, subject_id, topic)
                    if record:
                        added.append(record)

            outcome = "ok" if added else "skipped"
            log_event("college.resources.researched", subject_id=subject_id,
                      topic=topic, candidates=len(candidates),
                      added=len(added), outcome=outcome)
            return {
                "status": "VERIFIED" if added else "RESOURCE_ENRICHMENT_PENDING",
                "resources_added": len(added),
                "resources": added,
            }

    # ------------------------------------------------------------------
    # Cache reads/writes
    # ------------------------------------------------------------------

    def _read_cache(self, subject_id: str, topic: Optional[str]) -> List[Dict]:
        adapter = getattr(self.store, "adapter", None)
        client = getattr(adapter, "client", None)
        if client is None:
            return []
        res = (client.table("learning_resources").select("*")
               .eq("subject_id", subject_id)
               .eq("verification_status", "VERIFIED")
               .execute())
        rows = list(res.data or [])
        if topic:
            needle = topic.lower()
            rows = [r for r in rows
                    if needle in (r.get("title") or "").lower()
                    or any(needle in str(t).lower()
                           for t in (r.get("topic_ids") or []))]
        return rows

    async def _verify_and_persist(
        self, http: httpx.AsyncClient, cand: Dict[str, Any],
        subject_id: str, topic: str,
    ) -> Optional[Dict[str, Any]]:
        """Reachability check; persist VERIFIED records. Returns None if rejected."""
        url = cand["url"]
        parsed = urllib.parse.urlparse(url)
        domain = (parsed.netloc or "").lower().replace("www.", "")
        tier = tier_for_domain(domain)

        # Promote official-institution YouTube channels to tier B.
        if cand["kind"] == "VIDEO" and tier == "D":
            channel = (cand.get("quality_signals", {}).get("channel_title") or "").lower()
            if any(h in channel for h in _OFFICIAL_YT_HANDLES):
                tier = "B"

        # Reachability is mandatory — unverifiable URLs are REJECTED.
        try:
            resp = await http.head(url)
            if resp.status_code >= 400:
                get_resp = await http.get(url)
                if get_resp.status_code >= 400:
                    log_event("college.resources.url_rejected", subject_id=subject_id,
                              outcome="error", error_code="URL_UNREACHABLE")
                    return None
            canonical = str(resp.url)
        except Exception:
            log_event("college.resources.url_rejected", subject_id=subject_id,
                      outcome="error", error_code="URL_UNREACHABLE")
            return None

        # Deduplicate against cache by canonical URL.
        if self._url_known(subject_id, canonical):
            return None

        source_id = f"src_{hashlib.sha256(canonical.encode()).hexdigest()[:12]}"
        resource_id = f"res_{uuid.uuid4().hex[:12]}"
        now = datetime.now(timezone.utc).isoformat()

        quality_signals = dict(cand.get("quality_signals", {}))
        quality_signals.update({
            "domain": domain, "tier": tier,
            "reachability_checked_at": now, "reachable": True,
        })

        if cand["kind"] == "VIDEO":
            timestamps = await self._video_timestamps(cand, http)
            resource_type = "VIDEO"
        else:
            timestamps = []
            resource_type = "DOCUMENT"

        adapter = getattr(self.store, "adapter", None)
        client = getattr(adapter, "client", None)
        if client is None:
            return None  # honest: no persistence available, do not fake cache

        try:
            client.table("source_records").upsert({
                "source_id": source_id,
                "url": canonical,
                "canonical_url": canonical,
                "title": cand.get("title") or canonical,
                "domain": domain,
                "provider_name": cand.get("provider", domain),
                "provider_type": "VIDEO" if cand["kind"] == "VIDEO" else "WEB",
                "source_tier": tier,
                "verification_status": "VERIFIED",
                "quality_signals": quality_signals,
                "topic_ids": [topic],
                "last_verified_at": now,
            }, on_conflict="source_id").execute()

            row = {
                "resource_id": resource_id,
                "title": cand.get("title") or canonical,
                "resource_type": resource_type,
                "provider": cand.get("provider", domain),
                "url": canonical,
                "source_id": source_id,
                "source_tier": tier,
                "estimated_minutes": cand.get("estimated_minutes"),
                "topic_ids": [topic],
                "video_timestamps": timestamps,
                "document_sections": [],
                "verification_status": "VERIFIED",
                "last_verified_at": now,
                "learner_preference_metadata": {"researched": True},
            }
            client.table("resource_records").insert(row).execute()
            # learning_resources is the read-model get_verified_resources serves.
            client.table("learning_resources").upsert({
                **row, "subject_id": subject_id,
            }, on_conflict="resource_id").execute()
        except Exception as e:
            logger.error("Resource persist failed: %s", str(e))
            return None

        log_event("college.resources.verified", subject_id=subject_id,
                  resource_id=resource_id, tier=tier, outcome="ok")
        return row

    def _url_known(self, subject_id: str, url: str) -> bool:
        try:
            adapter = getattr(self.store, "adapter", None)
            client = getattr(adapter, "client", None)
            if client is None:
                return False
            res = (client.table("learning_resources").select("resource_id")
                   .eq("subject_id", subject_id).eq("url", url).execute())
            return bool(res.data)
        except Exception:
            return False

    # ------------------------------------------------------------------
    # Query building
    # ------------------------------------------------------------------

    def _build_queries(self, *, subject_id: str, subject_name: Optional[str],
                       topic: str, university_name: Optional[str]) -> List[str]:
        subject_label = subject_name or subject_id
        base = f"{subject_label} {topic}".strip()
        queries = [
            f"{base} nptel lecture",
            f"{base} site:youtube.com lecture tutorial",
            f"{base} notes pdf",
        ]
        if university_name:
            queries.insert(0, f"{university_name} {base} syllabus")
        return queries

    # ------------------------------------------------------------------
    # Search providers
    # ------------------------------------------------------------------

    async def _search_web(self, query: str, deadline: float) -> List[Dict]:
        """DuckDuckGo primary, Tavily backup. Returns [{url, title, snippet}]."""
        if time.monotonic() > deadline:
            return []
        hits = await self._search_duckduckgo(query)
        if not hits and self._tavily_key and time.monotonic() <= deadline:
            hits = await self._search_tavily(query)
        return hits

    async def _search_duckduckgo(self, query: str) -> List[Dict]:
        """DuckDuckGo HTML endpoint: no API key, real organic results."""
        try:
            async with httpx.AsyncClient(
                    timeout=15.0,
                    headers={"User-Agent": "Mozilla/5.0"}) as http:
                resp = await http.post(
                    DDG_HTML_URL, data={"q": query, "kl": "in-en"})
                if resp.status_code != 200:
                    return []
                html = resp.text
        except Exception as e:
            logger.warning("DuckDuckGo search failed: %s", type(e).__name__)
            return []

        hits: List[Dict] = []
        # result__a anchors carry the real destination in href.
        for m in re.finditer(
                r'class="result__a"[^>]*href="([^"]+)"[^>]*>(.*?)</a>',
                html, re.DOTALL):
            raw_href, raw_title = m.group(1), m.group(2)
            title = re.sub(r"<[^>]+>", "", raw_title).strip()
            url = self._ddg_unwrap(raw_href)
            if not url or not url.startswith("http"):
                continue
            domain = urllib.parse.urlparse(url).netloc.lower()
            if not domain or "duckduckgo.com" in domain:
                continue
            hits.append({
                "url": url, "title": title[:200], "snippet": "",
                "provider": domain.replace("www.", ""),
                "quality_signals": {"search_engine": "duckduckgo"},
            })
            if len(hits) >= 6:
                break
        return hits

    @staticmethod
    def _ddg_unwrap(href: str) -> str:
        """DuckDuckGo wraps destinations as //duckduckgo.com/l/?uddg=<encoded>."""
        parsed = urllib.parse.urlparse(href)
        if "duckduckgo.com" in parsed.netloc:
            qs = urllib.parse.parse_qs(parsed.query)
            uddg = qs.get("uddg")
            if uddg:
                return urllib.parse.unquote(uddg[0])
            return ""
        return href if href.startswith("http") else ""

    async def _search_tavily(self, query: str) -> List[Dict]:
        if not self._tavily_key:
            return []
        try:
            async with httpx.AsyncClient(timeout=20.0) as http:
                resp = await http.post(TAVILY_API_URL, json={
                    "api_key": self._tavily_key,
                    "query": query, "max_results": 6,
                    "include_answer": False,
                    "search_depth": "basic",
                })
                if resp.status_code != 200:
                    return []
                data = resp.json()
        except Exception as e:
            logger.warning("Tavily search failed: %s", type(e).__name__)
            return []
        hits = []
        for r in data.get("results", []) or []:
            url = r.get("url") or ""
            if not url.startswith("http"):
                continue
            hits.append({
                "url": url, "title": (r.get("title") or "")[:200],
                "snippet": (r.get("content") or "")[:300],
                "provider": urllib.parse.urlparse(url).netloc
                    .lower().replace("www.", ""),
                "quality_signals": {
                    "search_engine": "tavily",
                    "tavily_score": r.get("score"),
                },
            })
        return hits

    async def _search_youtube(self, query: str, deadline: float) -> List[Dict]:
        """YouTube Data API v3: real video metadata + statistics."""
        if not self._youtube_key or time.monotonic() > deadline:
            return []
        try:
            async with httpx.AsyncClient(timeout=15.0) as http:
                resp = await http.get(
                    f"{YOUTUBE_API_URL}/search",
                    params={"key": self._youtube_key, "q": query,
                            "part": "snippet", "type": "video",
                            "maxResults": 6, "relevanceLanguage": "en",
                            "safeSearch": "strict"})
                if resp.status_code != 200:
                    return []
                items = resp.json().get("items", [])
                video_ids = [i["id"]["videoId"] for i in items
                             if i.get("id", {}).get("videoId")]
                if not video_ids:
                    return []
                stats_resp = await http.get(
                    f"{YOUTUBE_API_URL}/videos",
                    params={"key": self._youtube_key,
                            "id": ",".join(video_ids),
                            "part": "snippet,statistics,contentDetails"})
                if stats_resp.status_code != 200:
                    return []
                details = {v["id"]: v
                           for v in stats_resp.json().get("items", [])}
        except Exception as e:
            logger.warning("YouTube search failed: %s", type(e).__name__)
            return []

        videos = []
        for vid in video_ids:
            v = details.get(vid)
            if not v:
                continue
            snippet = v.get("snippet", {})
            stats = v.get("statistics", {})
            videos.append({
                "url": f"https://www.youtube.com/watch?v={vid}",
                "video_id": vid,
                "title": snippet.get("title", "")[:200],
                "description": snippet.get("description", ""),
                "snippet": snippet.get("description", "")[:300],
                "provider": snippet.get("channelTitle", "YouTube"),
                "estimated_minutes": self._iso8601_minutes(
                    v.get("contentDetails", {}).get("duration")),
                "quality_signals": {
                    "channel_title": snippet.get("channelTitle"),
                    "view_count": stats.get("viewCount"),
                    "like_count": stats.get("likeCount"),
                    "comment_count": stats.get("commentCount"),
                    "published_at": snippet.get("publishedAt"),
                },
            })
        return videos

    @staticmethod
    def _iso8601_minutes(duration: Optional[str]) -> Optional[int]:
        if not duration:
            return None
        m = re.match(r"PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?", duration)
        if not m:
            return None
        hours = int(m.group(1) or 0)
        minutes = int(m.group(2) or 0)
        seconds = int(m.group(3) or 0)
        return hours * 60 + minutes + (1 if seconds else 0)

    # ------------------------------------------------------------------
    # Video chapters / transcripts
    # ------------------------------------------------------------------

    async def _video_timestamps(
        self, video: Dict[str, Any], http: httpx.AsyncClient,
    ) -> List[Dict[str, Any]]:
        """
        Real chapters parsed from the video description where available.
        If none, clearly labeled "estimated" segments from the duration —
        never presented as real chapters.
        """
        description = video.get("description") or ""
        chapters = parse_video_chapters(description)
        if chapters:
            return [{"start_seconds": c["start_seconds"],
                     "label": c["label"],
                     "source": "video_description"} for c in chapters[:12]]

        # Optional: transcript check that the topic is actually discussed.
        if await self._transcript_confirms_topic(video):
            minutes = video.get("estimated_minutes") or 20
            thirds = [0, minutes * 60 // 3, minutes * 120 // 3]
            return [{"start_seconds": s,
                     "label": "estimated segment (no chapter markers)",
                     "source": "estimated"} for s in thirds]

        # Duration only: still "estimated", never masquerading as chapters.
        minutes = video.get("estimated_minutes")
        if minutes:
            return [{"start_seconds": 0, "label": "full video",
                     "source": "estimated"}]
        return []

    async def _transcript_confirms_topic(self, video: Dict[str, Any]) -> bool:
        """Best-effort: confirm via transcript that content is on-topic."""
        try:
            from youtube_transcript_api import YouTubeTranscriptApi
            video_id = video.get("video_id")
            if not video_id:
                return False
            transcript = YouTubeTranscriptApi.get_transcript(video_id)
            text = " ".join(seg.get("text", "") for seg in transcript).lower()
            title_words = [w for w in re.findall(r"\w{4,}", video.get("title", "").lower())]
            return any(w in text for w in title_words[:5])
        except Exception:
            return False
