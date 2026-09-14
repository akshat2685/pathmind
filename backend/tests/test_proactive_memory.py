import pytest
from fastapi.testclient import TestClient
from backend.main import app
from backend.services.store import FirestoreStore
from backend.services.second_brain_service import SecondBrainService
from backend.services.proactive_memory_service import ProactiveMemoryService
from backend.services.context_graph_service import ContextGraphService
from backend.core.memory_schemas import ProactiveMemoryContext

@pytest.fixture
def clean_store():
    store = FirestoreStore()
    store._in_memory_persons.clear()
    return store

@pytest.fixture
def proactive_service(clean_store):
    return ProactiveMemoryService(store=clean_store)

@pytest.fixture
def second_brain(clean_store):
    return SecondBrainService(store=clean_store)

@pytest.fixture
def client():
    return TestClient(app)

# -------------------------------------------------------------------------
# Test 1 & 2: Automatic proactive recall without user search or client query
# -------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_automatic_proactive_recall_during_learning_task(clean_store, proactive_service, second_brain):
    person_id = "test-learner-autocall"
    
    # Ingest a prior struggle memory
    await second_brain.ingest_memory(person_id, {
        "title": "Struggled with API Rate Limits and 429 Retry Backoff",
        "topic": "API Design & Rate Limiting",
        "content": "Spent 3 days debugging exponential backoff and jitter algorithms under concurrent loads.",
        "nature": "EXPERIENCE",
        "importance": "HIGH",
        "related_concepts": ["API Rate Limits", "Distributed Caching", "Exponential Backoff"]
    })

    # Proactively retrieve context for a new learning action on Distributed Caching
    ctx: ProactiveMemoryContext = await proactive_service.get_proactive_memory_context(
        person_id=person_id,
        task_type="NEXT_LEARNING_ACTION",
        current_concept="Distributed Caching"
    )

    assert ctx.status == "ACTIVE_RECALL"
    assert len(ctx.retrieved_memories) >= 1
    assert any(m.title == "Struggled with API Rate Limits and 429 Retry Backoff" for m in ctx.retrieved_memories)
    assert "PRIOR_STRUGGLE" in ctx.relevance_reasons
    assert "Rate Limit" in ctx.proactive_summary or "Distributed Caching" in ctx.proactive_summary

@pytest.mark.asyncio
async def test_context_graph_service_integrates_proactive_memory(clean_store, second_brain):
    person_id = "test-learner-graph"
    
    await second_brain.ingest_memory(person_id, {
        "title": "Mastered PostgreSQL Indexing Strategies",
        "topic": "Database Optimization",
        "content": "Implemented B-Tree and GIN indexes reducing query latency by 85%.",
        "nature": "SKILL_KNOWLEDGE",
        "importance": "HIGH",
        "related_concepts": ["Database Optimization", "Query Planning"]
    })

    graph_service = ContextGraphService(store=clean_store)
    pkg = await graph_service.extract_task_context_package(
        person_id=person_id,
        task_type="NEXT_LEARNING_ACTION",
        current_concept="Database Optimization"
    )

    assert len(pkg.relevant_memories) >= 1
    assert any("PostgreSQL Indexing Strategies" in m for m in pkg.relevant_memories)

# -------------------------------------------------------------------------
# Test 3: Unrelated task returns explicit NO_RELEVANT_MEMORY (no hallucination)
# -------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_unrelated_task_returns_no_relevant_memory(clean_store, proactive_service, second_brain):
    person_id = "test-learner-unrelated"
    
    await second_brain.ingest_memory(person_id, {
        "title": "Sourdough Bread Fermentation Notes",
        "topic": "Baking",
        "content": "Fermentation rate at 78F is optimal for levain development.",
        "nature": "EXPERIENCE",
        "importance": "LOW"
    })

    ctx = await proactive_service.get_proactive_memory_context(
        person_id=person_id,
        task_type="NEXT_LEARNING_ACTION",
        current_concept="Kubernetes Ingress Controllers"
    )

    assert ctx.status == "NO_RELEVANT_MEMORY"
    assert len(ctx.retrieved_memories) == 0
    assert ctx.proactive_summary == ""

# -------------------------------------------------------------------------
# Test 4: Current explicit user input overrides older memory
# -------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_current_explicit_input_overrides_older_memory(clean_store, proactive_service, second_brain):
    person_id = "test-learner-override"
    
    await second_brain.ingest_memory(person_id, {
        "title": "Primary Goal: Full Stack Web Developer",
        "topic": "Career Aspiration",
        "content": "User expressed strong interest in React, Next.js and Tailwind.",
        "nature": "GOAL",
        "importance": "CRITICAL"
    })

    # User currently explicitly requested Embedded Systems Firmware
    ctx = await proactive_service.get_proactive_memory_context(
        person_id=person_id,
        task_type="CAREER_DIRECTION",
        current_goal="Embedded Systems Firmware Engineer"
    )

    assert ctx.status == "SUPERSEDED_BY_CURRENT_INPUT"
    assert "Embedded Systems Firmware Engineer" in ctx.proactive_summary
    assert "supersedes historical memory" in ctx.proactive_summary

# -------------------------------------------------------------------------
# Test 5: New verified state supersedes conflicting historical memory
# -------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_new_verified_state_supersedes_historical_memory(clean_store, proactive_service, second_brain):
    person_id = "test-learner-verified-state"
    
    # Historical struggle with C++ pointers
    mem = await second_brain.ingest_memory(person_id, {
        "title": "Struggled with C++ Pointer Arithmetic",
        "topic": "C++ Basics",
        "content": "Confused about double pointers and memory leaks in linked lists.",
        "nature": "EXPERIENCE",
        "importance": "HIGH"
    })

    # Now supersede it with verified mastery
    await second_brain.supersede_memory(
        person_id=person_id,
        old_memory_id=mem.memory_id,
        reason="Verified passing of Advanced C++ Embedded Memory Management assessment",
        new_memory_payload={
            "title": "Verified C++ Embedded Systems Mastery",
            "topic": "C++ Systems",
            "content": "Successfully implemented custom arena allocator without leaks.",
            "nature": "SKILL_KNOWLEDGE",
            "importance": "HIGH",
            "evidence_verification_status": "VERIFIED"
        }
    )

    ctx = await proactive_service.get_proactive_memory_context(
        person_id=person_id,
        task_type="NEXT_LEARNING_ACTION",
        current_concept="C++ Systems"
    )

    assert any(m.title == "Verified C++ Embedded Systems Mastery" for m in ctx.retrieved_memories)
    assert not any(m.title == "Struggled with C++ Pointer Arithmetic" for m in ctx.retrieved_memories)

# -------------------------------------------------------------------------
# Test 6 & 7: Person Isolation and Shared Intelligence Anonymity
# -------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_strict_person_isolation(clean_store, proactive_service, second_brain):
    # Person Alice records confidential memory
    await second_brain.ingest_memory("person_alice_proactive", {
        "title": "Alice Confidential Medical Diagnostics Research",
        "topic": "Bioinformatics",
        "content": "Proprietary sequence alignment technique using Smith-Waterman optimizations.",
        "nature": "DECISION",
        "importance": "CRITICAL"
    })

    # Person Bob queries proactive memory on Bioinformatics
    ctx_bob = await proactive_service.get_proactive_memory_context(
        person_id="person_bob_proactive",
        task_type="NEXT_LEARNING_ACTION",
        current_concept="Bioinformatics"
    )

    assert len(ctx_bob.retrieved_memories) == 0
    assert ctx_bob.status == "NO_RELEVANT_MEMORY"

@pytest.mark.asyncio
async def test_shared_learning_patterns_scrub_identity(client):
    res = client.get("/api/memory/shared-patterns")
    assert res.status_code == 200
    patterns = res.json()
    assert isinstance(patterns, list)
    for p in patterns:
        assert "person_id" not in p
        assert "evidence_count" in p
        assert "effective_intervention" in p

# -------------------------------------------------------------------------
# Test 8: Resume generation rejects memory-only claims
# -------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_resume_generation_rejects_memory_inferences(clean_store, proactive_service, second_brain):
    person_id = "test-learner-resume"
    
    await second_brain.ingest_memory(person_id, {
        "title": "Learner spent 4 hours reading PyTorch internals",
        "topic": "PyTorch",
        "content": "Reading session on autograd engine architecture.",
        "nature": "EXPERIENCE",
        "importance": "LOW"
    })

    ctx = await proactive_service.get_proactive_memory_context(
        person_id=person_id,
        task_type="RESUME_GENERATION"
    )

    assert ctx.status == "UNVERIFIED_MEMORY_ONLY"
    assert "Memory inferences are excluded from resume generation" in ctx.proactive_summary
    assert len(ctx.retrieved_memories) == 0

# -------------------------------------------------------------------------
# Test 9 & 10: Smallest useful set (top-2) and task-specific filtering
# -------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_smallest_useful_set_capped_at_two(clean_store, proactive_service, second_brain):
    person_id = "test-learner-cap2"
    
    for i in range(5):
        await second_brain.ingest_memory(person_id, {
            "title": f"Distributed Caching Milestone {i}",
            "topic": "Distributed Caching",
            "content": f"Experience with Redis cluster node {i}.",
            "nature": "SKILL_KNOWLEDGE",
            "importance": "HIGH"
        })

    ctx = await proactive_service.get_proactive_memory_context(
        person_id=person_id,
        task_type="NEXT_LEARNING_ACTION",
        current_concept="Distributed Caching"
    )

    assert len(ctx.retrieved_memories) <= 2

# -------------------------------------------------------------------------
# Test 11 & 12: Durable storage vs transient rejection
# -------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_durable_event_stored_and_transient_rejected(clean_store, proactive_service):
    person_id = "test-learner-durable"
    
    # Transient UI event should be rejected
    transient_evt = {"event_type": "PAGE_VIEW", "url": "/journey", "action": "click"}
    assert not proactive_service.should_create_memory(transient_evt)
    res_transient = await proactive_service.record_durable_memory_if_eligible(person_id, transient_evt)
    assert res_transient is None

    # Durable milestone event should be stored
    durable_evt = {
        "event_type": "MILESTONE_COMPLETED",
        "title": "Completed Distributed Systems Stage 2",
        "topic": "Distributed Systems",
        "content": "Built Raft consensus protocol from scratch.",
        "nature": "EXPERIENCE",
        "importance": "HIGH"
    }
    assert proactive_service.should_create_memory(durable_evt)
    mem = await proactive_service.record_durable_memory_if_eligible(person_id, durable_evt)
    assert mem is not None
    assert mem.title == "Completed Distributed Systems Stage 2"

# -------------------------------------------------------------------------
# Test 13: Memory conflict detection
# -------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_memory_conflict_detection(clean_store, proactive_service, second_brain):
    person_id = "test-learner-conflicts"
    
    await second_brain.ingest_memory(person_id, {
        "title": "Goal: Cloud Architect",
        "topic": "Career Goal",
        "content": "Targeting cloud infrastructure and AWS solutions architecture.",
        "nature": "GOAL",
        "importance": "HIGH"
    })

    await second_brain.ingest_memory(person_id, {
        "title": "Goal: Mobile iOS Developer",
        "topic": "Career Goal",
        "content": "Committed to Swift and SwiftUI mobile apps.",
        "nature": "GOAL",
        "importance": "HIGH"
    })

    ctx = await proactive_service.get_proactive_memory_context(
        person_id=person_id,
        task_type="CAREER_DIRECTION"
    )

    assert ctx.status == "CONFLICT_DETECTED"
    assert len(ctx.conflicting_memories) >= 2
    assert "CONFLICT DETECTED" in ctx.proactive_summary

# -------------------------------------------------------------------------
# Test 14: Superseded memory preserved for historical reflection
# -------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_superseded_memory_preserved(clean_store, second_brain):
    person_id = "test-learner-preserve"
    
    old_m = await second_brain.ingest_memory(person_id, {
        "title": "Old Career Direction",
        "topic": "Career",
        "content": "Targeting Graphic Design.",
        "nature": "GOAL",
        "importance": "HIGH"
    })

    new_m = await second_brain.supersede_memory(
        person_id=person_id,
        old_memory_id=old_m.memory_id,
        reason="Pivoted to UX Engineering after frontend development exposure",
        new_memory_payload={
            "title": "Target Direction: UX Engineering",
            "topic": "Career",
            "content": "Focused on design systems and React accessibility.",
            "nature": "GOAL",
            "importance": "HIGH"
        }
    )

    # Stored memories include both the superseded record and the current record
    all_mems = await clean_store.get_personal_memories(person_id)
    assert len(all_mems) == 2
    superseded = [m for m in all_mems if m.get("lifecycle_status") == "SUPERSEDED"]
    current = [m for m in all_mems if m.get("lifecycle_status") == "CURRENT"]
    assert len(superseded) == 1
    assert len(current) == 1
    assert superseded[0]["superseded_by"] == new_m.memory_id

# -------------------------------------------------------------------------
# Test 15: Scenarios A–E from Prompt 24 Step 18
# -------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_scenarios_a_through_e(clean_store, proactive_service, second_brain):
    # Scenario A: Prior struggle scaffolding
    await second_brain.ingest_memory("learner_a", {
        "title": "Struggled with API Rate Limiting algorithms",
        "topic": "API Design",
        "content": "Had difficulty implementing token bucket algorithm.",
        "nature": "EXPERIENCE",
        "importance": "HIGH",
        "related_concepts": ["Distributed Caching", "API Design"]
    })
    ctx_a = await proactive_service.get_proactive_memory_context(
        "learner_a", "NEXT_LEARNING_ACTION", current_concept="Distributed Caching"
    )
    assert "PRIOR_STRUGGLE" in ctx_a.relevance_reasons

    # Scenario B: Switched goal does not get forced old stack
    await second_brain.ingest_memory("learner_b", {
        "title": "Switched from Data Science to Autonomous Robotics",
        "topic": "Career Pivot",
        "content": "Formally pivoted away from pandas and tabular data science toward ROS2 and robotics.",
        "nature": "DECISION",
        "importance": "CRITICAL",
        "related_concepts": ["Robotics", "ROS2"]
    })
    ctx_b = await proactive_service.get_proactive_memory_context(
        "learner_b", "ROADMAP_GENERATION", target_direction="Robotics Engineer"
    )
    assert ctx_b.status == "ACTIVE_RECALL"
    assert "Robotics" in ctx_b.proactive_summary

    # Scenario C: Verified mastery prevents redundant syntax retake
    await second_brain.ingest_memory("learner_c", {
        "title": "Verified C++ Core Language Mastery",
        "topic": "C++",
        "content": "Scored 96% in advanced C++ systems programming.",
        "nature": "SKILL_KNOWLEDGE",
        "importance": "HIGH",
        "evidence_verification_status": "VERIFIED"
    })
    ctx_c = await proactive_service.get_proactive_memory_context(
        "learner_c", "NEXT_LEARNING_ACTION", current_concept="C++ Memory Models"
    )
    assert any("Verified C++" in m.title for m in ctx_c.retrieved_memories)

    # Scenario D: Conflicting goals flagged with ambiguity warning
    await second_brain.ingest_memory("learner_d", {
        "title": "Aspiring Quantitative Trader",
        "topic": "Career",
        "content": "High frequency trading focus.",
        "nature": "GOAL",
        "importance": "HIGH"
    })
    await second_brain.ingest_memory("learner_d", {
        "title": "Aspiring Wildlife Conservationist",
        "topic": "Career",
        "content": "Ecology and fieldwork focus.",
        "nature": "GOAL",
        "importance": "HIGH"
    })
    ctx_d = await proactive_service.get_proactive_memory_context("learner_d", "CAREER_DIRECTION")
    assert ctx_d.status == "CONFLICT_DETECTED"
    assert len(ctx_d.conflicting_memories) == 2

    # Scenario E: Resume generation rejects memory inference facts
    await second_brain.ingest_memory("learner_e", {
        "title": "Observed reading PyTorch documentation",
        "topic": "PyTorch",
        "content": "Read 2 articles on neural networks.",
        "nature": "EXPERIENCE",
        "importance": "LOW"
    })
    ctx_e = await proactive_service.get_proactive_memory_context("learner_e", "RESUME_GENERATION")
    assert ctx_e.status == "UNVERIFIED_MEMORY_ONLY"
    assert len(ctx_e.retrieved_memories) == 0

# -------------------------------------------------------------------------
# Test 16: Debug API Endpoint
# -------------------------------------------------------------------------
def test_debug_proactive_context_endpoint(client):
    res = client.get(
        "/api/memory/debug/proactive-context?task_type=NEXT_LEARNING_ACTION&current_concept=Tree%20Traversal",
        headers={"X-Person-ID": "test-debug-client"}
    )
    assert res.status_code == 200
    data = res.json()
    assert "status" in data
    assert "retrieved_memories" in data
    assert "relevance_reasons" in data
    assert "proactive_summary" in data
