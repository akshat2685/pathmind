"""
College round-11 regression tests (final pass, 2026-10-01).

Root cause found live via round 9's adk_error_detail surface: the ADK
toolkit and runtime construct the college services with a CollegeStore,
whose getters return pydantic MODELS — but the services were written
against the legacy FirestoreStore, whose getters return DICTS. Every
`Model(**raw)` / `raw.get(...)` on a store result crashed under the
CollegeStore wiring ("AcademicContext() argument after ** must be a
mapping, not AcademicContext"), so the ADK mentor path died inside its
tools before any model call. Round 11 added coerce_model/model_as_dict
to college_schemas and applied them at every unguarded site.

These tests wire the services with a CollegeStore — the exact ADK
configuration — against the fake adapter. The route-level tests all
use the FirestoreStore wiring, which is why this shipped green.
"""
import asyncio

import pytest
from fastapi.testclient import TestClient

import backend.main as main_mod
import backend.core.gemini as gemini_mod
import backend.services.college_learning_service as learning_mod
from backend.core.college_schemas import (
    AcademicContext, CollegeShortMemory, TodaySchedule,
    coerce_model, model_as_dict,
)
from college_testkit import install_fake_adapter

client = TestClient(main_mod.app)

ALICE = {"Authorization": "Bearer alice-token", "Content-Type": "application/json"}
ALICE_UID = "11111111-1111-4111-8111-111111111111"


@pytest.fixture(scope="module", autouse=True)
def fake_backend():
    adapter, restore = install_fake_adapter()
    yield adapter
    restore()


@pytest.fixture(autouse=True)
def clean_llm_env(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
    import backend.core.config as config_mod
    monkeypatch.setattr(config_mod.settings, "GEMINI_API_KEY",
                        "test-key", raising=False)
    yield


def _setup_alice():
    r = client.post("/api/college/profile",
                    json={"name": "Alice", "email": "alice@example.com"},
                    headers=ALICE)
    assert r.status_code == 200, r.text
    r = client.post("/api/college/academic-context", json={
        "university_id": "univ_aicte_model",
        "branch": "COMPUTER_SCIENCE_ENGINEER",
        "semester": 3, "subjects": ["CS-301", "CS-302"],
        "available_hours_per_week": 10,
    }, headers=ALICE)
    assert r.status_code == 200, r.text


def _college_store():
    from backend.services.college_store import CollegeStore
    return CollegeStore()


def test_coerce_helpers_accept_both_store_shapes():
    ctx = AcademicContext(context_id="c1", user_id="u1",
                          university_id="rtu", semester=7)
    assert coerce_model(AcademicContext, ctx) is ctx
    assert coerce_model(AcademicContext, ctx.model_dump()).context_id == "c1"
    assert coerce_model(AcademicContext, None) is None
    assert model_as_dict(ctx)["university_id"] == "rtu"
    assert model_as_dict({"a": 1}) == {"a": 1}
    assert model_as_dict(None) is None


def test_academic_context_via_college_store():
    _setup_alice()
    from backend.services.academic_service import AcademicService
    svc = AcademicService(_college_store())
    ctx = asyncio.run(svc.get_learner_academic_context(ALICE_UID))
    assert isinstance(ctx, AcademicContext)
    assert ctx.university_id == "univ_aicte_model"
    assert ctx.semester == 3


def test_accountability_via_college_store(monkeypatch):
    _setup_alice()
    # Static plan via API (ADK seam + model down -> honest fallback),
    # so the CollegeStore plan walk has real phases to traverse.
    async def _adk_down(agent_key, prompt, **kwargs):
        raise RuntimeError("ADK unavailable in tests")
    monkeypatch.setattr(learning_mod, "run_agent_generation", _adk_down)

    def _no_model():
        raise RuntimeError("no model in tests")
    monkeypatch.setattr(gemini_mod, "get_gemini_model", _no_model)

    r = client.post("/api/college/plans/generate",
                    json={"scope": "SEMESTER"}, headers=ALICE)
    assert r.status_code == 200, r.text

    from backend.services.college_accountability_service import (
        CollegeAccountabilityService)
    svc = CollegeAccountabilityService(_college_store())
    countdown = asyncio.run(svc.calculate_exam_countdown(ALICE_UID))
    assert countdown is None or isinstance(countdown, int)
    schedule = asyncio.run(svc.get_today_schedule(ALICE_UID))
    assert isinstance(schedule, TodaySchedule)
    assert isinstance(schedule.active_activities, list)

    from backend.services.college_learning_service import (
        CollegeLearningService)
    plan = asyncio.run(
        CollegeLearningService(_college_store()).get_current_plan(ALICE_UID))
    assert plan is not None
    assert plan.plan_id == r.json()["plan_id"]


def test_memory_reads_via_college_store():
    _setup_alice()
    from backend.services.college_memory_service import CollegeMemoryService
    svc = CollegeMemoryService(_college_store())
    asyncio.run(svc.record_short_term_context(
        uid=ALICE_UID, session_id="sess_r11",
        content="Learner asked: how do I revise MQTT?"))
    memories = asyncio.run(svc.get_short_term_memories(ALICE_UID))
    assert memories
    assert all(isinstance(m, CollegeShortMemory) for m in memories)


def test_toolkit_current_subjects_via_college_store():
    _setup_alice()
    from backend.agents.college_adk_tools import CollegeToolKit

    class _ToolCtx:
        state = {"uid": ALICE_UID}

    kit = CollegeToolKit(_college_store())
    out = asyncio.run(kit.get_current_subjects(_ToolCtx()))
    assert out["status"] == "ok", out
    assert out["subjects"] == ["CS-301", "CS-302"]
