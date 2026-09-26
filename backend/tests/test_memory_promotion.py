"""
Tests for memory promotion lifecycle (spec §13):
OBSERVED -> CANDIDATE -> DURABLE via deterministic dedup + promote_memory().
"""
import pytest

from backend.services.second_brain_service import SecondBrainService
from backend.services.memory_engine import MemoryEngine
from backend.services.proactive_memory_service import ProactiveMemoryService
from backend.services.store import FirestoreStore


@pytest.fixture
def clean_store():
    store = FirestoreStore()
    store._in_memory_persons.clear()
    return store


@pytest.fixture
def second_brain(clean_store):
    return SecondBrainService(store=clean_store)


def _payload(**kw):
    base = {
        "title": "Struggles with recursion base cases",
        "topic": "Recursion",
        "content": "Missed base-case questions twice this week.",
        "importance": "MEDIUM",
        "evidence_verification_status": "UNVERIFIED",
    }
    base.update(kw)
    return base


@pytest.mark.asyncio
async def test_repeated_observations_promote_instead_of_duplicating(second_brain, clean_store):
    pid = "promo-person"
    m1 = await second_brain.ingest_memory(pid, _payload())
    assert m1.promotion_status == "OBSERVED"
    assert m1.observation_count == 1

    m2 = await second_brain.ingest_memory(pid, _payload())
    assert m2.memory_id == m1.memory_id  # same record, not a duplicate
    assert m2.promotion_status == "CANDIDATE"
    assert m2.observation_count == 2

    m3 = await second_brain.ingest_memory(pid, _payload())
    assert m3.memory_id == m1.memory_id
    assert m3.promotion_status == "DURABLE"
    assert m3.observation_count == 3

    raw = await clean_store.get_personal_memories(pid)
    assert len(raw) == 1


@pytest.mark.asyncio
async def test_dissimilar_memories_do_not_merge(second_brain, clean_store):
    pid = "promo-person-2"
    await second_brain.ingest_memory(pid, _payload())
    other = await second_brain.ingest_memory(pid, _payload(
        title="Prefers morning study sessions", topic="Schedule"))
    raw = await clean_store.get_personal_memories(pid)
    assert len(raw) == 2
    assert other.promotion_status == "OBSERVED"


@pytest.mark.asyncio
async def test_critical_importance_promotes_on_first_observation(second_brain):
    pid = "promo-person-3"
    mem = await second_brain.ingest_memory(pid, _payload(
        title="Career goal: robotics engineer", topic="Career",
        importance="CRITICAL"))
    assert mem.promotion_status == "CANDIDATE"


@pytest.mark.asyncio
async def test_search_excludes_observed_by_default(second_brain):
    pid = "promo-person-4"
    # One DURABLE memory on Recursion
    for _ in range(3):
        await second_brain.ingest_memory(pid, _payload())
    # One fresh OBSERVED memory on UI
    await second_brain.ingest_memory(pid, _payload(
        title="Opened the dashboard", topic="UI",
        content="single page view", importance="LOW"))

    res = await second_brain.search_memories(pid, query="recursion")
    assert len(res) == 1
    assert res[0].memory.promotion_status == "DURABLE"

    res_ui = await second_brain.search_memories(pid, query="dashboard")
    assert len(res_ui) == 0  # OBSERVED too weak to drive behavior

    res_ui_all = await second_brain.search_memories(pid, query="dashboard", include_observed=True)
    assert len(res_ui_all) == 1
    assert res_ui_all[0].memory.promotion_status == "OBSERVED"


@pytest.mark.asyncio
async def test_proactive_context_filters_observed_by_default(clean_store):
    pid = "promo-person-5"
    sb = SecondBrainService(store=clean_store)
    for _ in range(3):
        await sb.ingest_memory(pid, _payload(
            title="Recurring misconception: mutable default args",
            topic="Python Pitfalls", nature="EXPERIENCE",
            content="struggle with mutable defaults"))
    await sb.ingest_memory(pid, _payload(
        title="Saw a python logo", topic="Python Pitfalls",
        content="trivial", importance="LOW"))

    svc = ProactiveMemoryService(store=clean_store)
    ctx = await svc.get_proactive_memory_context(pid, task_type="NEXT_LEARNING_ACTION",
                                                 current_concept="python")
    assert all(m.promotion_status in ("CANDIDATE", "DURABLE") for m in ctx.retrieved_memories)

    ctx_all = await svc.get_proactive_memory_context(pid, task_type="NEXT_LEARNING_ACTION",
                                                     current_concept="python",
                                                     include_observed=True)
    assert len(ctx_all.retrieved_memories) >= len(ctx.retrieved_memories)


@pytest.mark.asyncio
async def test_cross_stage_bridge_filters_observed_by_default(clean_store):
    pid = "promo-person-6"
    sb = SecondBrainService(store=clean_store)
    await sb.ingest_memory(pid, _payload(title="Single glimpse of trees",
                                         topic="Trees", importance="LOW"))
    engine = MemoryEngine(store=clean_store)
    bridge = await engine.get_cross_stage_bridge(pid, current_concept="Tree Traversal")
    assert bridge.past_concept == "NO_RECORDED_MEMORY"
    bridge_all = await engine.get_cross_stage_bridge(pid, current_concept="Tree Traversal",
                                                     include_observed=True)
    assert bridge_all.past_concept != "NO_RECORDED_MEMORY"


@pytest.mark.asyncio
async def test_supersede_skips_dedup(second_brain, clean_store):
    pid = "promo-person-7"
    old = await second_brain.ingest_memory(pid, _payload())
    new = await second_brain.supersede_memory(
        pid, old.memory_id, reason="updated understanding",
        new_memory_payload=_payload(content="Now understands base cases."))
    assert new.memory_id != old.memory_id
    raw = await clean_store.get_personal_memories(pid)
    assert len(raw) == 2
