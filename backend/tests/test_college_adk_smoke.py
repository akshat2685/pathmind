"""
ADK smoke tests for the PathMind College MVP (Phase 1b).

Covers:
  1. Agent construction — CollegeRootAgent + the six sub-agents, with the
     expected TRD §5 tools wired on each.
  2. Tool wiring — tools callable directly, UID isolated via session state
     (missing UID -> AUTH_REQUIRED), honest not-found states.
  3. POST /api/college/agent/interact — response shape {message, state,
     ui_blocks, sources} preserved; chat turns persisted.

Runs against the in-memory fake Supabase adapter: no network, no
credentials, no real writes. Without GEMINI_API_KEY the interact path
exercises the deterministic legacy fallback — the shape contract is what
this test pins.
"""
import pytest
from fastapi.testclient import TestClient

from backend.main import app
from college_testkit import install_fake_adapter
from backend.agents.college_adk_agents import build_agents
from backend.agents.college_adk_tools import CollegeToolKit
from backend.services.college_store import college_store


@pytest.fixture(scope="module", autouse=True)
def fake_backend():
    adapter, restore = install_fake_adapter()
    yield adapter
    restore()


@pytest.fixture(autouse=True)
def no_llm_key(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
    import backend.core.config as config_mod
    monkeypatch.setattr(config_mod.settings, "GEMINI_API_KEY", "",
                        raising=False)


client = TestClient(app)

AUTH_HEADERS = {"Authorization": "Bearer alice-token"}
ALICE_UID = "11111111-1111-4111-8111-111111111111"


class _StubToolContext:
    """Minimal stand-in for ADK ToolContext: only .state is needed."""
    def __init__(self, uid=None):
        self.state = {"uid": uid} if uid else {}


# ---------------------------------------------------------------------------
# 1. Agent construction
# ---------------------------------------------------------------------------

def test_agents_construct_with_six_subagents():
    kit = CollegeToolKit(college_store)
    agents = build_agents(kit)
    assert set(agents) == {"root", "academic", "plan", "assessment",
                           "accountability", "memory", "pyq"}
    root = agents["root"]
    assert root.name == "college_root_agent"
    assert len(root.sub_agents) == 6
    names = {a.name for a in root.sub_agents}
    assert names == {"academic_agent", "plan_agent", "assessment_agent",
                     "accountability_agent", "memory_agent", "pyq_agent"}


def test_subagent_tool_wiring():
    kit = CollegeToolKit(college_store)
    agents = build_agents(kit)
    expected = {
        "academic_agent": {"get_learner_profile", "get_academic_context",
                           "get_current_subjects", "get_active_goal",
                           "search_university_sources",
                           "get_verified_curriculum"},
        "plan_agent": {"create_study_plan", "update_progress",
                       "get_verified_resources", "trigger_resource_research"},
        "assessment_agent": {"create_assessment", "evaluate_assessment",
                              "record_learning_signal",
                              "get_topic_mastery_state"},
        "accountability_agent": {"create_accountability_commitment",
                                 "get_accountability_state",
                                 "update_progress"},
        "memory_agent": {"record_memory", "retrieve_short_term_memory",
                         "retrieve_long_term_memory", "record_learning_signal"},
        "pyq_agent": {"get_verified_pyqs"},
    }
    for agent_name, tool_names in expected.items():
        agent = agents[agent_name.replace("_agent", "")]
        wired = {t.name for t in agent.tools}
        assert tool_names <= wired, f"{agent_name} missing {tool_names - wired}"
    # Root carries memory + mastery reads before delegating.
    root_tools = {t.name for t in agents["root"].tools}
    assert {"retrieve_short_term_memory", "retrieve_long_term_memory",
            "get_topic_mastery_state"} <= root_tools


# ---------------------------------------------------------------------------
# 2. Tool wiring: UID isolation + honest not-found states
# ---------------------------------------------------------------------------

def test_tools_reject_missing_uid():
    kit = CollegeToolKit(college_store)
    ctx = _StubToolContext(uid=None)
    with pytest.raises(PermissionError):
        import asyncio
        asyncio.run(kit.get_learner_profile(ctx))


def test_tools_return_honest_not_found_states():
    import asyncio
    kit = CollegeToolKit(college_store)
    ctx = _StubToolContext(uid=ALICE_UID)

    profile = asyncio.run(kit.get_learner_profile(ctx))
    assert profile["status"] == "PROFILE_NOT_FOUND"

    ctx_state = asyncio.run(kit.get_academic_context(ctx))
    assert ctx_state["status"] == "NEEDS_CONTEXT"

    pyqs = asyncio.run(kit.get_verified_pyqs(ctx, subject_id="NOPE-000"))
    assert pyqs["status"] == "PYQ_NOT_AVAILABLE"

    resources = asyncio.run(
        kit.get_verified_resources(ctx, subject_id="NOPE-000"))
    assert resources["status"] == "RESOURCE_ENRICHMENT_PENDING"
    assert resources["resources"] == []


def test_verified_resources_come_from_cache_not_invention():
    import asyncio
    kit = CollegeToolKit(college_store)
    ctx = _StubToolContext(uid=ALICE_UID)
    result = asyncio.run(kit.get_verified_resources(ctx, subject_id="CS-301"))
    assert result["status"] == "VERIFIED"
    assert len(result["resources"]) == 2
    urls = {r["url"] for r in result["resources"]}
    assert urls == {"https://example.edu/video/cs301-linked-lists",
                    "https://example.edu/notes/cs301"}


# ---------------------------------------------------------------------------
# 3. Interact endpoint: preserved shape + chat persistence
# ---------------------------------------------------------------------------

def test_interact_endpoint_shape_and_chat_persistence():
    resp = client.post(
        "/api/college/agent/interact",
        json={"message": "What should I study today?"},
        headers=AUTH_HEADERS,
    )
    assert resp.status_code == 200
    body = resp.json()
    assert set(body) >= {"message", "state", "ui_blocks", "sources"}
    assert isinstance(body["message"], str) and body["message"]
    assert isinstance(body["ui_blocks"], list)
    assert isinstance(body["sources"], list)

    # Both turns persisted to chat_messages for this learner.
    history = client.post(
        "/api/college/agent/interact",
        json={"message": "hello again", "session_id": body.get("session_id")},
        headers=AUTH_HEADERS,
    )
    assert history.status_code == 200

    import asyncio
    session_id = body.get("session_id")
    assert session_id
    rows = asyncio.run(
        college_store.get_chat_history(ALICE_UID, session_id, limit=10))
    roles = [r["role"] for r in rows]
    assert "user" in roles and "assistant" in roles
    assert all(r["user_id"] == ALICE_UID for r in rows)


def test_resources_endpoints():
    # Cached subject -> VERIFIED.
    resp = client.get("/api/college/resources?subject_id=CS-301",
                      headers=AUTH_HEADERS)
    assert resp.status_code == 200
    assert resp.json()["status"] == "VERIFIED"

    # Uncached subject -> honest pending, never invented URLs.
    resp = client.get("/api/college/resources?subject_id=ZZ-999",
                      headers=AUTH_HEADERS)
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "RESOURCE_ENRICHMENT_PENDING"
    assert body["resources"] == []
