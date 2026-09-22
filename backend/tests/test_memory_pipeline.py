import pytest
import uuid
import os
import asyncio
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

from backend.services.supabase_adapter import get_supabase_adapter
from backend.services.store import FirestoreStore
from backend.services.college_memory_service import CollegeMemoryService
from backend.services.proactive_memory_service import ProactiveMemoryService
from backend.services.college_orchestrator import CollegeOrchestrator
import pytest_asyncio

pytestmark = pytest.mark.asyncio

@pytest_asyncio.fixture(scope="function")
async def test_user():
    adapter = get_supabase_adapter()
    email = f"testuser_{uuid.uuid4().hex[:6]}@example.com"
    user = adapter.client.auth.admin.create_user({
        "email": email,
        "password": "password123",
        "email_confirm": True
    })
    uid = user.user.id
    yield uid
    try:
        adapter.client.auth.admin.delete_user(uid)
    except Exception as e:
        print(f"Failed to delete test user: {e}")

@pytest_asyncio.fixture(scope="function")
async def test_user_2():
    adapter = get_supabase_adapter()
    email = f"testuser_{uuid.uuid4().hex[:6]}@example.com"
    user = adapter.client.auth.admin.create_user({
        "email": email,
        "password": "password123",
        "email_confirm": True
    })
    uid = user.user.id
    yield uid
    try:
        adapter.client.auth.admin.delete_user(uid)
    except:
        pass

@pytest.fixture
def memory_service():
    store = FirestoreStore()
    return CollegeMemoryService(store)

@pytest.fixture
def proactive_service(memory_service):
    return ProactiveMemoryService(memory_service)

async def test_short_term_persistence(memory_service, test_user):
    """Verify short-term memory can be saved and retrieved accurately using Supabase."""
    mem = await memory_service.record_short_term_context(
        uid=test_user,
        content="Learner struggled with Thermodynamics laws.",
        session_id="session_123"
    )
    
    assert mem.content == "Learner struggled with Thermodynamics laws."
    assert mem.user_id == test_user
    
    mems = await memory_service.get_short_term_memories(test_user)
    assert any(m.memory_id == mem.memory_id for m in mems)

async def test_long_term_persistence(memory_service, test_user):
    """Verify long-term durable memories are persisted securely."""
    mem = await memory_service.record_long_term_memory(
        uid=test_user,
        content="Learner prefers visual diagrams over text.",
        title="Visual Learner",
        memory_type="LEARNING_PREFERENCE"
    )
    
    assert mem.user_id == test_user
    assert mem.status == "CURRENT"
    
    mems = await memory_service.get_long_term_memories(test_user)
    assert any(m.memory_id == mem.memory_id for m in mems)

async def test_learner_isolation(memory_service, test_user, test_user_2):
    """Ensure User A cannot retrieve User B's memories."""
    mem1 = await memory_service.record_long_term_memory(
        uid=test_user,
        content="Secret memory for User 1",
        title="Secret 1"
    )
    
    mem2 = await memory_service.record_long_term_memory(
        uid=test_user_2,
        content="Secret memory for User 2",
        title="Secret 2"
    )
    
    user1_mems = await memory_service.get_long_term_memories(test_user)
    
    assert any(m.memory_id == mem1.memory_id for m in user1_mems)
    assert not any(m.memory_id == mem2.memory_id for m in user1_mems)

async def test_memory_supersession(memory_service, proactive_service, test_user):
    """Verify that replacing a memory marks the old one as SUPERSEDED and links the new one."""
    mem_v1 = await proactive_service.promote_to_long_term_memory(
        uid=test_user,
        title="Study Goal",
        content="Focusing on Frontend Web Dev."
    )
    
    assert mem_v1["status"] == "CURRENT"
    
    mem_v2 = await proactive_service.supersede_memory(
        uid=test_user,
        old_memory_id=mem_v1["memory_id"],
        new_title="Study Goal",
        new_content="Focusing on Backend AI Dev."
    )
    
    assert mem_v2["status"] == "CURRENT"
    
    all_mems = await memory_service.get_long_term_memories(test_user)
    old_fetched = next(m for m in all_mems if m.memory_id == mem_v1["memory_id"])
    assert old_fetched.status == "SUPERSEDED"
    assert old_fetched.supersedes_memory_id == mem_v2["memory_id"]

async def test_proactive_relevance_filtering(proactive_service, test_user):
    """Test that context retrieval pulls relevant memories for the task."""
    await proactive_service.promote_to_long_term_memory(
        uid=test_user,
        title="AI Career Path",
        content="Goal is to build Backend AI systems."
    )
    
    ctx = await proactive_service.get_proactive_memory_context(test_user, "How do I build an AI backend?")
    
    assert ctx["status"] == "ACTIVE_RECALL"
    assert len(ctx["retrieved_memories"]) > 0
    assert any("Backend AI" in str(m) for m in ctx["retrieved_memories"])

async def test_persistence_failure_handling():
    """Verify that when persistence is unavailable, the system handles it gracefully."""
    store = FirestoreStore()
    store._available = False # Simulate failure
    
    mem_svc = CollegeMemoryService(store)
    
    # Expect RuntimeError("PERSISTENCE_UNAVAILABLE")
    with pytest.raises(RuntimeError, match="PERSISTENCE_UNAVAILABLE"):
        await mem_svc.record_long_term_memory(
            uid="some_uid",
            content="test",
            title="test"
        )
        
async def test_orchestrator_gemini_integration(test_user):
    """Ensure the orchestrator successfully passes memories to Gemini and extracts memory actions if requested."""
    orchestrator = CollegeOrchestrator()
    
    await orchestrator.memory_service.record_long_term_memory(
        uid=test_user,
        title="Language Preference",
        content="Prefer to read responses entirely in French."
    )
    
    result = await orchestrator.interact(test_user, "I also want to learn Python.")
    
    assert result["state"] == "LEARNING"
    assert result["message"] is not None
