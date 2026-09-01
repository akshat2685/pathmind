import pytest
import asyncio
from backend.services.memory_engine import MemoryEngine
from backend.services.store import FirestoreStore
from backend.core.memory_schemas import (
    MemoryRecallQuery,
    MemoryItem,
    SharedLearningPattern
)

@pytest.fixture
def memory_engine():
    return MemoryEngine()

@pytest.fixture
def store():
    return FirestoreStore()

@pytest.mark.asyncio
async def test_memory_extraction_and_types(memory_engine, store):
    person_id = "scholar-memory-test-1"
    
    # Ingest diverse real events
    mem_episodic = await memory_engine.extract_and_store_memory_from_event(person_id, {
        "topic": "Recursion",
        "observation": "Struggled with stack frames in binary search.",
        "intervention": "Visual call-stack diagrams",
        "event_type": "MASTERY_DEMONSTRATED",
        "stage_id": "Stage 01"
    })
    
    mem_pref = await memory_engine.extract_and_store_memory_from_event(person_id, {
        "topic": "Learning Format",
        "observation": "3x higher completion on interactive projects",
        "event_type": "PREFERENCE_OBSERVED",
        "stage_id": "Stage 01"
    })
    
    mems = await store.get_personal_memories(person_id)
    assert len(mems) >= 2
    types = {m.get("memory_type") for m in mems}
    assert "EPISODIC" in types
    assert "PREFERENCE" in types

@pytest.mark.asyncio
async def test_strict_cross_person_isolation(memory_engine, store):
    person_a = "person-alice-memory-secure"
    person_b = "person-bob-memory-secure"
    
    # Person A creates a private custom breakthrough memory
    mem_a = MemoryItem(
        memory_id="mem_alice_custom_private_001",
        person_id=person_a,
        memory_type="EPISODIC",
        title="Alice Private Recursion Breakthrough",
        summary="Alice solved custom binary tree recursion using a dual pointer call stack method.",
        topic="Recursion",
        confidence="HIGH",
        importance="CRITICAL"
    )
    await store.save_personal_memory(person_a, mem_a.model_dump(mode="json"))
    
    # Person B queries their personal memories
    mems_b = await store.get_personal_memories(person_b)
    mems_b_ids = [m.get("memory_id") for m in mems_b]
    
    # Person B MUST NOT receive Person A's private memory
    assert "mem_alice_custom_private_001" not in mems_b_ids

@pytest.mark.asyncio
async def test_natural_memory_recall_engine(memory_engine, store):
    person_id = "scholar-recall-test"
    
    # Save real test memory
    mem = MemoryItem(
        memory_id="mem_rec_001",
        person_id=person_id,
        memory_type="EPISODIC",
        title="Recursion & Call Stack Breakthrough",
        summary="Solved recursion difficulty using visual frame diagrams.",
        topic="Recursion",
        related_concepts=["Call Stack", "Trees"],
        source="Stage 01"
    )
    await store.save_personal_memory(person_id, mem.model_dump(mode="json"))
    
    # Test recall for Recursion
    rec_resp = await memory_engine.recall_natural_memory(
        MemoryRecallQuery(person_id=person_id, query="How did I learn recursion?")
    )
    assert rec_resp.person_id == person_id
    assert rec_resp.confidence == "HIGH"
    assert "visual" in rec_resp.answer.lower() or "recursion" in rec_resp.answer.lower()

    # Test recall for unknown topic
    rec_unknown = await memory_engine.recall_natural_memory(
        MemoryRecallQuery(person_id=person_id, query="What did I do during quantum thermodynamics?")
    )
    assert rec_unknown.confidence == "LOW"
    assert "do not have a recorded memory" in rec_unknown.answer.lower()

@pytest.mark.asyncio
async def test_past_to_present_cross_stage_transfer(memory_engine, store):
    person_id = "scholar-bridge-test"
    
    # Save real past memory
    mem = MemoryItem(
        memory_id="mem_past_001",
        person_id=person_id,
        memory_type="EPISODIC",
        title="Recursion & Call Stack Frames",
        summary="Mastered base conditions and frame tracing.",
        topic="Recursion",
        source="Stage 01: Python Foundations"
    )
    await store.save_personal_memory(person_id, mem.model_dump(mode="json"))

    bridge = await memory_engine.get_cross_stage_bridge(
        person_id=person_id,
        current_concept="Tree Traversal & Depth-First Search"
    )
    
    assert bridge.person_id == person_id
    assert "Recursion" in bridge.past_concept
    assert "Stage 01" in bridge.past_stage

@pytest.mark.asyncio
async def test_shared_learning_patterns_privacy_filtering(store):
    pattern = SharedLearningPattern(
        pattern_id="pat_gen_test_001",
        topic="Recursion & Call Stack",
        misconception_or_context="Stack frame tracing difficulty in initial tree search.",
        effective_intervention="Stepped visual call-stack frame diagrams.",
        evidence_count=12,
        confidence="HIGH"
    )
    await store.save_shared_pattern(pattern.model_dump(mode="json"))

    patterns = await store.get_shared_patterns()
    assert len(patterns) >= 1
    
    for p in patterns:
        p_str = str(p).lower()
        # Verify strict privacy filtering: Zero PII or private IDs
        assert "alice" not in p_str
        assert "bob" not in p_str
        assert "@" not in p_str
        assert "person_id" not in p

@pytest.mark.asyncio
async def test_memory_deletion(store):
    person_id = "scholar-del-test"
    mem = MemoryItem(
        memory_id="mem_to_delete_999",
        person_id=person_id,
        memory_type="PREFERENCE",
        title="Temporary Preference",
        summary="Prefers dark mode editor.",
        topic="Editor Preference"
    )
    await store.save_personal_memory(person_id, mem.model_dump(mode="json"))
    
    # Verify created
    mems = await store.get_personal_memories(person_id)
    assert any(m.get("memory_id") == "mem_to_delete_999" for m in mems)
    
    # Delete
    deleted = await store.delete_personal_memory(person_id, "mem_to_delete_999")
    assert deleted is True
    
    # Verify removed
    mems_after = await store.get_personal_memories(person_id)
    assert not any(m.get("memory_id") == "mem_to_delete_999" for m in mems_after)
