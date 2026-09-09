import pytest
from fastapi.testclient import TestClient

from backend.main import app
from backend.services.second_brain_service import SecondBrainService
from backend.core.memory_schemas import (
    MemoryItem,
    SecondBrainQueryRequest,
    ConsolidateMemoriesRequest,
    SupersedeMemoryRequest
)
from backend.services.store import FirestoreStore

@pytest.fixture
def clean_store():
    store = FirestoreStore()
    store._in_memory_persons.clear()
    return store

@pytest.fixture
def second_brain(clean_store):
    return SecondBrainService(store=clean_store)

@pytest.mark.asyncio
async def test_memory_ingestion_and_source_linking(second_brain):
    person_id = "scholar-sb-test"
    mem = await second_brain.ingest_memory(person_id, {
        "title": "API Implementation Milestone",
        "topic": "FastAPI",
        "content": "Built production REST API router with automated Pytest suites.",
        "nature": "SKILL_KNOWLEDGE",
        "memory_type": "SEMANTIC",
        "source_type": "ARTIFACT",
        "source_reference": "art_fastapi_core_01",
        "importance": "HIGH",
        "confidence": "HIGH"
    })

    assert mem.memory_id.startswith("mem_")
    assert mem.nature == "SKILL_KNOWLEDGE"
    assert mem.source_type == "ARTIFACT"
    assert mem.source_reference == "art_fastapi_core_01"
    assert mem.lifecycle_status == "CURRENT"

@pytest.mark.asyncio
async def test_strict_server_side_person_isolation(second_brain):
    # Person Alice records confidential memory
    await second_brain.ingest_memory("person_alice", {
        "title": "Alice Confidential Career Pivot",
        "content": "Secretly considering switching from quant to autonomous robotics.",
        "topic": "Career Pivot",
        "nature": "DECISION",
        "importance": "CRITICAL"
    })

    # Person Bob executes search
    results_bob = await second_brain.search_memories("person_bob", "robotics career pivot")
    assert len(results_bob) == 0

    query_res_bob = await second_brain.query_second_brain(
        "person_bob",
        SecondBrainQueryRequest(query="What is my career pivot decision?")
    )
    assert query_res_bob.status == "NO_RELEVANT_MEMORY"
    assert len(query_res_bob.retrieved_memories) == 0

@pytest.mark.asyncio
async def test_hybrid_semantic_search_and_ranking(second_brain):
    person_id = "scholar-ranking-test"

    # Memory 1: Low importance, content match
    await second_brain.ingest_memory(person_id, {
        "title": "Casual Reading",
        "topic": "General",
        "content": "Briefly skimmed an article discussing recursion in lisp.",
        "importance": "LOW",
        "lifecycle_status": "CURRENT"
    })

    # Memory 2: Critical importance, verified evidence, title & concept match
    await second_brain.ingest_memory(person_id, {
        "title": "Recursion Call Stack Breakthrough",
        "topic": "Recursion",
        "content": "Successfully debugged deep binary tree recursion using call stack frame analysis.",
        "related_concepts": ["call stack", "stack frame", "tree traversal"],
        "importance": "CRITICAL",
        "evidence_verification_status": "VERIFIED",
        "lifecycle_status": "CURRENT"
    })

    results = await second_brain.search_memories(person_id, "recursion call stack")
    assert len(results) >= 2
    # The critical verified breakthrough must rank first
    assert results[0].memory.title == "Recursion Call Stack Breakthrough"
    assert results[0].relevance_score > results[1].relevance_score

@pytest.mark.asyncio
async def test_temporal_validity_and_supersession(second_brain):
    person_id = "scholar-supersede-test"

    # 1. Initial goal: Cybersecurity
    old_mem = await second_brain.ingest_memory(person_id, {
        "title": "Target Career: Cybersecurity Analyst",
        "topic": "Cybersecurity",
        "content": "Committed to pursuing network penetration testing and SOC operations.",
        "nature": "GOAL",
        "importance": "HIGH",
        "lifecycle_status": "CURRENT"
    })

    # 2. Supersede: Change to ML Systems
    new_mem = await second_brain.supersede_memory(
        person_id=person_id,
        old_memory_id=old_mem.memory_id,
        reason="Discovered strong aptitude and passion for machine learning systems after Stage 1 projects.",
        new_memory_payload={
            "title": "Target Career: Applied Machine Learning Engineer",
            "topic": "Machine Learning",
            "content": "Transitioned target focus to PyTorch and ML infrastructure.",
            "nature": "GOAL",
            "importance": "CRITICAL"
        }
    )

    assert new_mem.lifecycle_status == "CURRENT"
    assert new_mem.parent_memory_id == old_mem.memory_id

    # Retrieve all memories and verify old memory is preserved as SUPERSEDED
    raw_mems = await second_brain.store.get_personal_memories(person_id)
    historical_old = next((m for m in raw_mems if m["memory_id"] == old_mem.memory_id), None)
    assert historical_old is not None
    assert historical_old["lifecycle_status"] == "SUPERSEDED"
    assert historical_old["supersedes_reason"] is not None

@pytest.mark.asyncio
async def test_do_you_remember_natural_query(second_brain):
    person_id = "scholar-recall-test"

    await second_brain.ingest_memory(person_id, {
        "title": "First Full-Stack API Project",
        "topic": "FastAPI",
        "content": "Built and deployed a REST API with FastAPI and SQLite for task management.",
        "nature": "EXPERIENCE",
        "source_type": "ARTIFACT",
        "source_reference": "repo_fastapi_task_tracker"
    })

    res = await second_brain.query_second_brain(
        person_id,
        SecondBrainQueryRequest(query="What was my first API project?")
    )

    assert res.status == "RESOLVED"
    assert len(res.retrieved_memories) > 0
    assert "FastAPI" in res.answer or "REST API" in res.answer
    assert res.retrieved_memories[0].memory.source_reference == "repo_fastapi_task_tracker"

@pytest.mark.asyncio
async def test_insufficient_history_no_hallucination(second_brain):
    person_id = "scholar-empty-test"

    res = await second_brain.query_second_brain(
        person_id,
        SecondBrainQueryRequest(query="Do you remember when I built an operating system kernel?")
    )

    assert res.status == "NO_RELEVANT_MEMORY"
    assert "no recorded memory" in res.answer.lower()
    assert len(res.retrieved_memories) == 0

@pytest.mark.asyncio
async def test_memory_conflict_detection(second_brain):
    person_id = "scholar-conflict-test"

    # Seed two conflicting CURRENT goals
    await second_brain.ingest_memory(person_id, {
        "title": "Primary Goal: Full-Time Robotics",
        "topic": "Robotics",
        "nature": "GOAL",
        "lifecycle_status": "CURRENT"
    })

    await second_brain.ingest_memory(person_id, {
        "title": "Primary Goal: Full-Time Web Development",
        "topic": "Web Development",
        "nature": "GOAL",
        "lifecycle_status": "CURRENT"
    })

    res = await second_brain.query_second_brain(
        person_id,
        SecondBrainQueryRequest(query="What is my primary career goal?")
    )

    assert res.status == "MEMORY_CONFLICT"
    assert len(res.conflicting_memories) >= 2

@pytest.mark.asyncio
async def test_memory_consolidation_preserves_sources(second_brain):
    person_id = "scholar-consolidation-test"

    # Ingest 3 related unit test passes
    m1 = await second_brain.ingest_memory(person_id, {"title": "Test 1: Recursion Base Case", "topic": "Recursion"})
    m2 = await second_brain.ingest_memory(person_id, {"title": "Test 2: Stack Depth Guard", "topic": "Recursion"})
    m3 = await second_brain.ingest_memory(person_id, {"title": "Test 3: Memoization Cache", "topic": "Recursion"})

    cons_res = await second_brain.consolidate_memories(
        person_id=person_id,
        source_memory_ids=[m1.memory_id, m2.memory_id, m3.memory_id],
        consolidated_title="Recursive Problem-Solving Foundations Mastered",
        consolidated_summary="Consolidated evidence from 3 milestone test suites verifying base cases, depth guards, and memoization.",
        topic="Recursion"
    )

    assert cons_res.consolidated_memory.is_consolidated is True
    assert len(cons_res.consolidated_memory.consolidated_source_ids) == 3

    # Verify original records are preserved as HISTORICAL, NOT deleted!
    raw = await second_brain.store.get_personal_memories(person_id)
    assert len(raw) == 4
    source_statuses = [m["lifecycle_status"] for m in raw if m["memory_id"] in [m1.memory_id, m2.memory_id, m3.memory_id]]
    assert all(s == "HISTORICAL" for s in source_statuses)

@pytest.mark.asyncio
async def test_write_validation_evidence_ceiling(second_brain):
    person_id = "scholar-ceiling-test"

    # Ingest unverified evidence claim
    mem = await second_brain.ingest_memory(person_id, {
        "title": "Unverified PyTorch Architecture",
        "source_type": "EVIDENCE_SUBMISSION",
        "is_unverified": True
    })

    # Must NOT claim verified status
    assert mem.evidence_verification_status == "UNVERIFIED"
    assert mem.confidence == "LOW"
    assert mem.nature == "INFERENCE"

@pytest.mark.asyncio
async def test_context_aware_teaching_retrieval(second_brain):
    person_id = "scholar-teaching-test"

    await second_brain.ingest_memory(person_id, {
        "title": "Recursion Mastery",
        "topic": "Recursion",
        "content": "Overcame mental block by visualizing call stack frames.",
        "related_concepts": ["call stack", "stack frame"]
    })

    # Student asks about active tree traversal milestone
    res = await second_brain.query_second_brain(
        person_id,
        SecondBrainQueryRequest(
            query="How should I approach this tree problem?",
            current_task_context="Tree Traversal & Depth-First Search"
        )
    )

    assert res.status == "RESOLVED"
    assert res.concept_bridge is not None
    assert "Recursion" in res.concept_bridge

@pytest.mark.asyncio
async def test_user_memory_update_and_deletion(second_brain):
    person_id = "scholar-crud-test"

    mem = await second_brain.ingest_memory(person_id, {
        "title": "Original Note",
        "content": "First draft content"
    })

    # Update
    updated = await second_brain.update_memory(person_id, mem.memory_id, {
        "title": "Corrected Title",
        "content": "Refined and accurate content"
    })
    assert updated.title == "Corrected Title"

    # Delete
    deleted = await second_brain.delete_memory(person_id, mem.memory_id)
    assert deleted is True

    remaining = await second_brain.store.get_personal_memories(person_id)
    assert not any(m["memory_id"] == mem.memory_id for m in remaining)

def test_fastapi_second_brain_endpoints():
    client = TestClient(app)
    headers = {"x-person-id": "test-scholar-api"}

    # 1. Ingest event
    res1 = client.post("/api/memory/events", headers=headers, json={
        "title": "FastAPI Route Testing Milestone",
        "topic": "FastAPI",
        "content": "Wrote comprehensive unit and integration tests for memory endpoints.",
        "nature": "SKILL_KNOWLEDGE"
    })
    assert res1.status_code == 200
    mem_id = res1.json()["memory_id"]

    # 2. Query second brain
    res2 = client.post("/api/memory/query", headers=headers, json={
        "query": "What did I test for FastAPI?"
    })
    assert res2.status_code == 200
    assert res2.json()["status"] == "RESOLVED"

    # 3. Supersede memory
    res3 = client.post(f"/api/memory/{mem_id}/supersede", headers=headers, json={
        "reason": "Upgraded test suite to include async fixtures",
        "new_memory_payload": {
            "title": "Advanced FastAPI Async Testing",
            "topic": "FastAPI",
            "content": "Integrated pytest-asyncio with database isolation fixtures."
        }
    })
    assert res3.status_code == 200
    assert res3.json()["parent_memory_id"] == mem_id
