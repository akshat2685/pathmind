"""
Tests for college-MVP memory parity on the main product:
- LongitudinalMemoryService.build_context_brief() (short-term + long-term + signals)
- LongitudinalMemoryService.promote_to_long_term() (short -> long promotion)
- Per-user isolation: person A never sees person B's memories
- CounselingAgent.counsel_chat() injects the longitudinal brief
"""
import uuid
from datetime import datetime, timezone, timedelta

import pytest

from backend.services.longitudinal_memory_service import LongitudinalMemoryService


class FakeTierStore:
    """Minimal stand-in for PmStore._insert/_rows used by the tier service."""

    def __init__(self):
        self.tables = {}

    async def _insert(self, table, person_id, data):
        row = {
            "id": str(uuid.uuid4()),
            "person_id": person_id,
            "data": dict(data),
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        self.tables.setdefault(table, []).append(row)
        return row

    async def _rows(self, table, person_id):
        return [r for r in self.tables.get(table, []) if r["person_id"] == person_id]


@pytest.fixture
def svc():
    return LongitudinalMemoryService(store=FakeTierStore())


@pytest.mark.asyncio
async def test_short_term_round_trip_with_session_filter(svc):
    await svc.record_short_term("p1", "User asked: what is recursion?", session_id="s1")
    await svc.record_short_term("p1", "User asked: what is a loop?", session_id="s2")
    got = await svc.get_short_term("p1", session_id="s1")
    assert len(got) == 1
    assert "recursion" in got[0]["content"]
    all_rows = await svc.get_short_term("p1")
    assert len(all_rows) == 2


@pytest.mark.asyncio
async def test_short_term_ttl_prunes_stale(svc):
    old = {
        "memory_id": "old-1",
        "content": "stale",
        "session_id": "s1",
        "created_at": (datetime.now(timezone.utc) - timedelta(days=8)).isoformat(),
    }
    await svc.store._insert("pm_short_term_memories", "p1", old)
    await svc.record_short_term("p1", "fresh turn", session_id="s1")
    got = await svc.get_short_term("p1", session_id="s1")
    assert len(got) == 1
    assert got[0]["content"] == "fresh turn"


@pytest.mark.asyncio
async def test_long_term_and_signals_round_trip(svc):
    await svc.record_long_term("p1", "Prefers morning study", title="Study preference",
                               memory_type="SEMANTIC", importance="HIGH")
    await svc.record_signal("p1", "STRUGGLING_TOPIC", "Recursion base cases")
    mems = await svc.get_long_term("p1")
    assert len(mems) == 1 and mems[0]["title"] == "Study preference"
    sigs = await svc.get_signals("p1")
    assert len(sigs) == 1 and sigs[0]["signal_type"] == "STRUGGLING_TOPIC"


@pytest.mark.asyncio
async def test_build_context_brief_contains_all_tiers(svc):
    await svc.record_short_term("p1", "User asked: explain Big-O", session_id="s1")
    await svc.record_long_term("p1", "Wants to become an AI engineer",
                               title="Career aspiration", importance="HIGH")
    await svc.record_signal("p1", "STRENGTH_OBSERVED", "Strong at algebra")
    brief = await svc.build_context_brief("p1", session_id="s1")
    assert "Big-O" in brief
    assert "Career aspiration" in brief
    assert "STRENGTH_OBSERVED" in brief


@pytest.mark.asyncio
async def test_build_context_brief_empty_memory(svc):
    brief = await svc.build_context_brief("nobody", session_id="s1")
    assert "none recorded yet" in brief


@pytest.mark.asyncio
async def test_promote_to_long_term_links_source(svc):
    short = await svc.record_short_term("p1", "User completed recursion module",
                                        session_id="s1")
    promoted = await svc.promote_to_long_term(
        "p1", short, title="Completed recursion module",
        memory_type="EPISODIC", importance="HIGH",
    )
    assert promoted["title"] == "Completed recursion module"
    assert promoted["metadata"]["promoted_from"] == short["memory_id"]
    mems = await svc.get_long_term("p1")
    assert len(mems) == 1


@pytest.mark.asyncio
async def test_promote_rejects_empty_content(svc):
    with pytest.raises(ValueError):
        await svc.promote_to_long_term("p1", {"content": "  "}, title="empty")


@pytest.mark.asyncio
async def test_person_isolation(svc):
    await svc.record_short_term("alice", "Alice's question", session_id="s1")
    await svc.record_long_term("alice", "Alice fact", title="Alice memory")
    await svc.record_short_term("bob", "Bob's question", session_id="s1")
    brief_bob = await svc.build_context_brief("bob", session_id="s1")
    assert "Bob's question" in brief_bob
    assert "Alice" not in brief_bob


def test_counsel_chat_injects_longitudinal_brief():
    from backend.services.counseling import CounselingAgent
    from backend.core.assessment_schemas import CounselingProfile

    agent = CounselingAgent()
    agent.model = None  # force deterministic fallback path
    profile = CounselingProfile(
        person_id="p1",
        strongest_interests=["Investigative"],
        candidate_directions=["AI engineer"],
    )
    brief = "CONVERSATION CONTEXT\n- Recent: User asked about Big-O"
    reply = agent.counsel_chat(
        person_id="p1",
        user_message="hello",
        profile=profile,
        history=[],
        memories=[],
        longitudinal_brief=brief,
    )
    assert reply.role == "counselor"
    assert reply.content  # deterministic fallback still answers


def test_counsel_chat_brief_reaches_prompt():
    """The brief must be interpolated into the Gemini system prompt."""
    import backend.services.counseling as mod

    captured = {}

    class FakeModel:
        def generate_content(self, prompt, **kw):
            captured["prompt"] = prompt
            class R:
                text = "ok"
            return R()

    agent = mod.CounselingAgent()
    agent.model = FakeModel()
    from backend.core.assessment_schemas import CounselingProfile
    profile = CounselingProfile(person_id="p1")
    brief = "UNIQUE_BRIEF_MARKER_12345"
    agent.counsel_chat(
        person_id="p1", user_message="hi", profile=profile,
        history=[], memories=[], longitudinal_brief=brief,
    )
    assert "UNIQUE_BRIEF_MARKER_12345" in captured["prompt"]
