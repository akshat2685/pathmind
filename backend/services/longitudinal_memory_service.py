"""
Longitudinal memory service for the PathMind main product.

Ported from the college MVP's CollegeMemoryService — three tiers:
  - short-term: working context for the active session (ephemeral, pruned)
  - long-term: durable memories across the learner's whole journey
  - signals: learning signals (observations about how they learn)

All tiers persist to pm_* tables via PmStore. Short-term memories older
than 7 days are pruned on read.
"""

from typing import List, Dict, Any, Optional
import asyncio
import uuid
from datetime import datetime, timezone, timedelta

from backend.services.pm_store import get_pm_store


SHORT_TERM_TTL_DAYS = 7

MEMORY_TYPES = ("EPISODIC", "SEMANTIC", "PROCEDURAL")
SIGNAL_TYPES = (
    "STRENGTH_OBSERVED", "GAP_OBSERVED", "PREFERENCE", "MILESTONE",
    "STRUGGLING_TOPIC", "PACE_SIGNAL",
)


class LongitudinalMemoryService:
    def __init__(self, store=None):
        self._store = store

    @property
    def store(self):
        if self._store is None:
            from backend.services.pm_store import get_pm_store
            self._store = get_pm_store()
        return self._store

    # ------------------------------------------------------------------
    # Short-term (session working context)
    # ------------------------------------------------------------------
    async def record_short_term(
        self,
        person_id: str,
        content: str,
        topic: Optional[str] = None,
        session_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        mem = {
            "memory_id": str(uuid.uuid4()),
            "content": content,
            "topic": topic,
            "session_id": session_id,
            "metadata": metadata or {},
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        await self.store._insert("pm_short_term_memories", person_id, mem)
        return mem

    async def get_short_term(
        self, person_id: str, session_id: Optional[str] = None, limit: int = 20
    ) -> List[Dict[str, Any]]:
        rows = await self.store._rows("pm_short_term_memories", person_id)
        cutoff = datetime.now(timezone.utc) - timedelta(days=SHORT_TERM_TTL_DAYS)
        fresh: List[Dict[str, Any]] = []
        stale_ids: List[str] = []
        for r in rows:
            d = r["data"]
            try:
                created = datetime.fromisoformat(str(d.get("created_at")))
            except (ValueError, TypeError):
                created = None
            if created and created < cutoff:
                stale_ids.append(r["id"])
                continue
            if session_id and d.get("session_id") not in (None, session_id):
                continue
            fresh.append(d)
        if stale_ids:
            # Best-effort prune; never fail the read.
            try:
                await asyncio.to_thread(self._prune, stale_ids)
            except Exception:
                pass
        fresh.sort(key=lambda m: m.get("created_at") or "", reverse=True)
        return fresh[:limit]

    def _prune(self, row_ids: List[str]) -> None:
        for rid in row_ids:
            try:
                (self.store._db().table("pm_short_term_memories")
                 .delete().eq("id", rid).execute())
            except Exception:
                continue

    # ------------------------------------------------------------------
    # Long-term (durable journey memory)
    # ------------------------------------------------------------------
    async def record_long_term(
        self,
        person_id: str,
        content: str,
        title: str,
        memory_type: str = "EPISODIC",
        importance: str = "MEDIUM",
        related_domain: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        if memory_type not in MEMORY_TYPES:
            raise ValueError(f"memory_type must be one of {MEMORY_TYPES}")
        mem = {
            "memory_id": str(uuid.uuid4()),
            "title": title,
            "content": content,
            "memory_type": memory_type,
            "importance": importance,
            "related_domain": related_domain,
            "metadata": metadata or {},
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        await self.store._insert("pm_long_term_memories", person_id, mem)
        return mem

    async def get_long_term(
        self, person_id: str, limit: int = 50
    ) -> List[Dict[str, Any]]:
        rows = await self.store._rows("pm_long_term_memories", person_id)
        mems = [r["data"] for r in rows]
        mems.sort(key=lambda m: m.get("created_at") or "", reverse=True)
        return mems[:limit]

    # ------------------------------------------------------------------
    # Learning signals (how this learner learns)
    # ------------------------------------------------------------------
    async def record_signal(
        self,
        person_id: str,
        signal_type: str,
        content: str,
        related_domain: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        if signal_type not in SIGNAL_TYPES:
            raise ValueError(f"signal_type must be one of {SIGNAL_TYPES}")
        sig = {
            "signal_id": str(uuid.uuid4()),
            "signal_type": signal_type,
            "content": content,
            "related_domain": related_domain,
            "metadata": metadata or {},
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        await self.store._insert("pm_longitudinal_signals", person_id, sig)
        return sig

    async def get_signals(
        self, person_id: str, signal_type: Optional[str] = None, limit: int = 50
    ) -> List[Dict[str, Any]]:
        rows = await self.store._rows("pm_longitudinal_signals", person_id)
        sigs = [r["data"] for r in rows]
        if signal_type:
            sigs = [s for s in sigs if s.get("signal_type") == signal_type]
        sigs.sort(key=lambda s: s.get("created_at") or "", reverse=True)
        return sigs[:limit]

    # ------------------------------------------------------------------
    # Journey context assembly (for prompts that need "memory")
    # ------------------------------------------------------------------
    async def journey_context(self, person_id: str) -> Dict[str, Any]:
        """Compact memory snapshot for grounding prompts."""
        long_term = await self.get_long_term(person_id, limit=10)
        signals = await self.get_signals(person_id, limit=10)
        return {
            "long_term": [
                {"title": m.get("title"), "content": m.get("content"),
                 "type": m.get("memory_type"), "importance": m.get("importance")}
                for m in long_term
            ],
            "signals": [
                {"type": s.get("signal_type"), "content": s.get("content")}
                for s in signals
            ],
        }
