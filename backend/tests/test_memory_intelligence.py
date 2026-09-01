import pytest
import asyncio
from backend.services.memory_engine import MemoryEngine
from backend.services.store import FirestoreStore
from backend.core.memory_schemas import (
    MemoryRecallQuery,
    MemoryItem
)

@pytest.fixture
def memory_engine():
    return MemoryEngine()

@pytest.fixture
def store():
    return FirestoreStore()

@pytest.mark.asyncio
async def test_demo_memories_seeding_and_types(memory_engine):
    person_id = "scholar-memory-test-1"
    memories = await memory_engine.seed_demo_memories_if_needed(person_id)
    
    assert len(memories) >= 5
    types = {m.memory_type for m in memories}
    assert "EPISODIC" in types
    assert "SEMANTIC_LEARNING" in types
    assert "PREFERENCE" in types
    assert "STRATEGY" in types
    assert "GOAL" in types
    
    for m in memories:
        assert m.person_id == person_id
        assert m.confidence in ["HIGH", "MEDIUM", "LOW"]
        assert m.importance in ["LOW", "MEDIUM", "HIGH", "CRITICAL"]
        assert m.lifecycle_status == "ACTIVE"

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
async def test_natural_memory_recall_engine(memory_engine):
    person_id = "scholar-recall-test"
    await memory_engine.seed_demo_memories_if_needed(person_id)
    
    # Test recall for Recursion
    rec_resp = await memory_engine.recall_natural_memory(
        MemoryRecallQuery(person_id=person_id, query="How did I learn recursion and what worked for me?")
    )
    assert rec_resp.person_id == person_id
    assert rec_resp.confidence == "HIGH"
    assert "call-stack" in rec_resp.answer.lower() or "visual" in rec_resp.answer.lower()
    assert rec_resp.grounded_concept_bridge is not None

    # Test recall for unknown topic
    rec_unknown = await memory_engine.recall_natural_memory(
        MemoryRecallQuery(person_id=person_id, query="What did I do during quantum physics thermodynamics?")
    )
    assert rec_unknown.confidence == "LOW"
    assert "do not have a recorded memory" in rec_unknown.answer.lower()

@pytest.mark.asyncio
async def test_past_to_present_cross_stage_transfer(memory_engine):
    person_id = "scholar-bridge-test"
    bridge = await memory_engine.get_cross_stage_bridge(
        person_id=person_id,
        current_concept="Tree Traversal & Depth-First Search"
    )
    
    assert bridge.person_id == person_id
    assert "Recursion" in bridge.past_concept
    assert "Stage 01: Python Foundations" in bridge.past_stage
    assert "tree traversal" in bridge.connection_explanation.lower()

@pytest.mark.asyncio
async def test_shared_learning_patterns_privacy_filtering(store):
    patterns = await store.get_shared_patterns()
    assert len(patterns) >= 1
    
    for p in patterns:
        p_str = str(p).lower()
        # Verify strict privacy filtering: Zero PII or private IDs
        assert "alice" not in p_str
        assert "bob" not in p_str
        assert "@" not in p_str
        assert "person_id" not in p
        assert p.get("evidence_count", 0) >= 1

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
