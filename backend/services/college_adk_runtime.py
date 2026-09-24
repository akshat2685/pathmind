"""
ADK Runner wiring for POST /api/college/agent/interact (TRD §4–5).

Flow per turn:
  1. Persist the user message to Supabase chat_sessions/chat_messages.
  2. Load recent chat history + short/long-term memory into a context brief
     so the agent actually remembers across turns (and cold starts).
  3. Build CollegeRootAgent + six sub-agents bound to the TRD §5 tool set.
  4. Run via the real ADK Runner (InMemorySessionService), bounded to stay
     under the 60s Vercel cap.
  5. Parse the root agent's structured JSON reply into the preserved
     {message, state, ui_blocks, sources} shape (TRD §23).
  6. Persist the assistant message.

Fallbacks (honest, never fake):
  - No GEMINI_API_KEY → the legacy deterministic orchestrator answers.
  - Runner timeout / LLM error / unparsable reply → legacy orchestrator.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import re
from typing import Any, Dict, List, Optional

from backend.agents.college_adk_agents import _gemini_available, build_agents
from backend.agents.college_adk_tools import CollegeToolKit
from backend.core.college_logging import log_event, timed_stage
from backend.core.config import settings
from backend.services.college_memory_service import CollegeMemoryService
from backend.services.college_store import CollegeStore

logger = logging.getLogger(__name__)

APP_NAME = "pathmind_college"
RUNNER_TIMEOUT_SECONDS = 50.0
_HISTORY_LIMIT = 10

_session_service = None
_runner = None


def _get_session_service():
    global _session_service
    if _session_service is None:
        from google.adk.sessions import InMemorySessionService
        _session_service = InMemorySessionService()
    return _session_service


def _ensure_llm_key() -> bool:
    """
    ADK's Gemini model reads GOOGLE_API_KEY; the backend configures
    GEMINI_API_KEY. Map env->env (never log or expose the value).
    """
    if os.environ.get("GOOGLE_API_KEY"):
        return True
    key = settings.GEMINI_API_KEY or os.environ.get("GEMINI_API_KEY")
    if key:
        os.environ["GOOGLE_API_KEY"] = key
        return True
    return False


async def _build_context_brief(uid: str, store: CollegeStore,
                               history: List[Dict[str, Any]]) -> str:
    """Short, privacy-conscious brief: recent turns + memory summaries."""
    parts: List[str] = []
    if history:
        lines = []
        for m in history[-_HISTORY_LIMIT:]:
            role = "Learner" if m.get("role") == "user" else "PATHMIND"
            text = (m.get("content") or "")[:400]
            lines.append(f"{role}: {text}")
        parts.append("Recent conversation:\n" + "\n".join(lines))
    mem_service = CollegeMemoryService(store)
    try:
        long_mems = await mem_service.get_long_term_memories(uid)
        durable = [m for m in long_mems
                   if getattr(m, "status", "CURRENT") == "CURRENT"]
        if durable:
            parts.append("Durable learner facts:\n" + "\n".join(
                f"- {m.title}: {(m.content or '')[:200]}"
                for m in durable[:8]))
    except Exception as e:
        logger.warning("Memory brief failed: %s", type(e).__name__)
    try:
        masteries = await store.get_topic_masteries(uid)
        weak = [m for m in masteries
                if (getattr(m, "outcome", "") or "") in
                ("REINFORCEMENT_REQUIRED", "PARTIALLY_MASTERED")][:6]
        if weak:
            parts.append("Known weak topics: " + ", ".join(
                f"{getattr(m, 'subject_id', '')}/{getattr(m, 'topic', '')}"
                for m in weak))
    except Exception as e:
        logger.warning("Mastery brief failed: %s", type(e).__name__)
    return "\n\n".join(parts) or "No prior context."


def _extract_final_text(events: List[Any]) -> Optional[str]:
    text: Optional[str] = None
    for event in events:
        try:
            if event.is_final_response():
                content = getattr(event, "content", None)
                if content and getattr(content, "parts", None):
                    joined = "".join(
                        getattr(p, "text", "") or "" for p in content.parts)
                    if joined.strip():
                        text = joined.strip()
        except Exception:
            continue
    return text


def _parse_structured_reply(raw: str) -> Dict[str, Any]:
    """Parse the root agent's JSON contract into the TRD §23 shape."""
    text = (raw or "").strip()
    payload: Optional[Dict[str, Any]] = None
    fence = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    candidate = fence.group(1) if fence else text
    try:
        parsed = json.loads(candidate)
        if isinstance(parsed, dict) and "message" in parsed:
            payload = parsed
    except Exception:
        payload = None
    if payload is None:
        # Honest wrap: the reply is still the agent's words, but we do not
        # pretend it satisfied the contract.
        return {
            "message": text[:2000] if text else
                       "I couldn't form a structured answer this time.",
            "state": "LEARNING",
            "ui_blocks": [{"type": "TEXT",
                           "data": {"text": text[:2000]}}],
            "sources": [],
        }
    return {
        "message": str(payload.get("message", ""))[:4000],
        "state": str(payload.get("state", "LEARNING")),
        "ui_blocks": payload.get("ui_blocks") or [],
        "sources": [s for s in (payload.get("sources") or [])
                    if isinstance(s, str) and s.startswith("http")],
    }


async def _run_with_runner(uid: str, message: str, session_id: str,
                           store: CollegeStore,
                           context_brief: str) -> Dict[str, Any]:
    from google.adk.runners import Runner
    from google.genai import types

    toolkit = CollegeToolKit(store)
    agents = build_agents(toolkit, context_brief=context_brief)
    root = agents["root"]

    session_service = _get_session_service()
    existing = await session_service.get_session(
        app_name=APP_NAME, user_id=uid, session_id=session_id)
    if existing is None:
        await session_service.create_session(
            app_name=APP_NAME, user_id=uid, session_id=session_id,
            state={"uid": uid})

    global _runner
    if _runner is None:
        _runner = Runner(agent=root, app_name=APP_NAME,
                         session_service=session_service)
    else:
        _runner.agent = root

    async def _collect() -> List[Any]:
        events: List[Any] = []
        async for event in _runner.run_async(
                user_id=uid, session_id=session_id,
                new_message=types.Content(
                    role="user",
                    parts=[types.Part(text=message)])):
            events.append(event)
            log_event("college.adk.event", user_id=uid,
                      event_type=type(event).__name__, outcome="ok")
        return events

    events = await asyncio.wait_for(_collect(),
                                    timeout=RUNNER_TIMEOUT_SECONDS)
    final_text = _extract_final_text(events)
    if not final_text:
        raise RuntimeError("ADK produced no final response")
    return _parse_structured_reply(final_text)


async def _legacy_fallback(uid: str, message: str,
                           session_id: Optional[str],
                           store: CollegeStore) -> Dict[str, Any]:
    """
    Deterministic pre-ADK orchestrator: same response shape, no LLM loop.
    The legacy orchestrator expects the dict-returning legacy FirestoreStore,
    which delegates college reads to the CollegeStore.
    """
    from backend.services.college_orchestrator import CollegeOrchestrator
    from backend.services.store import FirestoreStore
    orchestrator = CollegeOrchestrator(FirestoreStore())
    return await orchestrator.interact(
        uid=uid, user_message=message, session_id=session_id)


async def run_agent_interact(uid: str, user_message: str,
                             session_id: Optional[str] = None,
                             store: Optional[CollegeStore] = None
                             ) -> Dict[str, Any]:
    """
    Serve POST /api/college/agent/interact through the ADK Runner.

    Returns the preserved shape {message, state, ui_blocks, sources}.
    """
    store = store or CollegeStore()
    with timed_stage("college.adk.interact", user_id=uid):
        # 1. Chat session + persist user turn.
        session_row = await store.get_or_create_chat_session(uid, session_id)
        adk_session_id = (session_row or {}).get("session_id") \
            or session_id or f"chat_{uid[:8]}"
        history = await store.get_chat_history(uid, adk_session_id)
        await store.save_chat_message(uid, adk_session_id, "user",
                                      user_message)

        # 2. Context brief from history + memory.
        context_brief = await _build_context_brief(uid, store, history)

        # 3. Record short-term session context (legacy behavior).
        try:
            mem_service = CollegeMemoryService(store)
            await mem_service.record_short_term_context(
                uid=uid, session_id=adk_session_id,
                content=f"Learner asked: {user_message[:300]}")
        except Exception as e:
            logger.warning("Short-term memory write failed: %s",
                           type(e).__name__)

        # 4. ADK run, or honest fallback when no LLM is configured.
        used_adk = False
        shape: Optional[Dict[str, Any]] = None
        if _gemini_available() and _ensure_llm_key():
            try:
                shape = await _run_with_runner(
                    uid, user_message, adk_session_id, store, context_brief)
                used_adk = True
                log_event("college.adk.interact_ok", user_id=uid,
                          outcome="ok")
            except Exception as e:
                logger.warning("ADK run failed, falling back: %s",
                               type(e).__name__)
                log_event("college.adk.interact_fallback", user_id=uid,
                          outcome="error",
                          error_code=type(e).__name__)
        if shape is None:
            shape = await _legacy_fallback(uid, user_message,
                                           adk_session_id, store)

        # 5. Persist assistant turn.
        try:
            await store.save_chat_message(
                uid, adk_session_id, "assistant",
                shape.get("message", ""),
                source_refs=shape.get("sources") or [])
        except Exception as e:
            logger.warning("Assistant message persist failed: %s",
                           type(e).__name__)

        shape.setdefault("session_id", adk_session_id)
        log_event("college.agent.interact", user_id=uid,
                  via_adk=used_adk, state=shape.get("state"),
                  outcome="ok")
        return shape
