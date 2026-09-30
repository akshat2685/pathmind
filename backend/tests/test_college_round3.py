"""
Round-3 regression tests (college MVP):

1. Plan generation is static-first: generating a plan makes ZERO Gemini
   calls and ships every phase with ai_enriched=False (AI personalization
   stays an explicit on-demand action via "Personalize with AI"). This is
   what keeps plan generation from dying on the ~60s serverless cap when
   the AI endpoint is slow or unreachable — the failure learners hit as a
   dead "Embark on Study Plan" click / runtime error.

2. WHOLE_PROGRAM subject resolution covers every semester that has a
   verified curriculum. The previous threaded fetch raced under
   serverless CPU limits and silently dropped whole semesters (a live
   8-semester program produced a plan covering only 4 semesters).

3. Diagnostic retrieval retries the curriculum fetch once. get_curriculum
   swallows transient registry read failures into None, and an empty
   curriculum dead-ends the diagnostic as DIAGNOSTIC_UNAVAILABLE even
   though verified material exists.
"""
import asyncio
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from backend.main import app
from backend.core.college_schemas import (
    AcademicContext, EngineeringBranch, PlanScope,
)
from college_testkit import install_fake_adapter
import backend.services.college_learning_service as learning_mod
import backend.services.college_diagnostic_retrieval as retrieval_mod
from backend.services.college_learning_service import CollegeLearningService
from backend.services.college_diagnostic_retrieval import (
    retrieve_diagnostic_context,
)


@pytest.fixture(scope="module", autouse=True)
def fake_backend():
    """Install the seeded fake Supabase adapter for this whole module."""
    adapter, restore = install_fake_adapter()
    yield adapter
    restore()


client = TestClient(app)

ALICE_UID = "11111111-1111-4111-8111-111111111111"
AUTH_ALICE = {"Authorization": "Bearer alice-token"}


def _onboard_alice():
    resp = client.post(
        "/api/college/profile",
        json={"name": "Alice Learner", "email": "alice@example.com"},
        headers=AUTH_ALICE)
    assert resp.status_code == 200
    resp = client.post(
        "/api/college/academic-context",
        json={
            "university_id": "univ_aicte_model",
            "branch": EngineeringBranch.COMPUTER_SCIENCE.value,
            "semester": 3,
            "subjects": ["CS-301", "CS-302"],
            "exam_window": {"start": "2026-11-20", "end": "2026-12-05"},
            "available_hours_per_week": 16,
            "learning_style_preferences": ["worked examples first"],
        },
        headers=AUTH_ALICE)
    assert resp.status_code == 200


class _CountingModel:
    """A Gemini stand-in that records every attempted generation call."""

    def __init__(self):
        self.calls = 0

    def generate_content(self, prompt):  # pragma: no cover - must stay 0
        self.calls += 1

        class _Resp:
            text = "[]"

        return _Resp()


# ----------------------------------------------------------------------
# 1. Static-first plan generation (no LLM calls while generating)
# ----------------------------------------------------------------------

def test_plan_generation_makes_zero_llm_calls(monkeypatch):
    _onboard_alice()
    fake_model = _CountingModel()
    monkeypatch.setattr(
        CollegeLearningService, "_get_gemini_model",
        staticmethod(lambda: fake_model))

    resp = client.post(
        "/api/college/plans/generate",
        json={"goal_id": "goal_sem3_prep"},
        headers=AUTH_ALICE)
    assert resp.status_code == 200
    plan = resp.json()

    # The plan is fully usable without the AI: full syllabus coverage
    # (2 subjects x 2 units) shipped as deterministic static phases.
    assert len(plan["phases"]) == 4
    assert all(p["ai_enriched"] is False for p in plan["phases"])
    assert all(len(p["activities"]) >= 1 for p in plan["phases"])
    # ...and generation never touched the model at all.
    assert fake_model.calls == 0


# ----------------------------------------------------------------------
# 2. WHOLE_PROGRAM resolution covers every seeded semester
# ----------------------------------------------------------------------

def _fake_curriculum(subject_id):
    return SimpleNamespace(subjects=[
        SimpleNamespace(
            subject_id=subject_id, code=subject_id, name=subject_id,
            units=[SimpleNamespace(unit=1, title="Unit 1",
                                   topics=["Topic A"])]),
    ])


def test_whole_program_resolution_covers_all_seeded_semesters(monkeypatch):
    seeded = {1: "SUB-S1", 2: "SUB-S2", 3: "SUB-S3"}

    async def fake_get_curriculum(university_id, branch, semester):
        if semester in seeded:
            return _fake_curriculum(seeded[semester])
        return None

    monkeypatch.setattr(learning_mod, "get_curriculum", fake_get_curriculum)

    ctx = AcademicContext(
        context_id="ctx_round3", user_id=ALICE_UID,
        university_id="univ_aicte_model", semester=3)
    svc = CollegeLearningService()
    scoped = asyncio.run(svc._resolve_scoped_subjects(
        ALICE_UID, ctx, EngineeringBranch.COMPUTER_SCIENCE,
        PlanScope.WHOLE_PROGRAM, None))

    # Semesters 1 and 2 (the ones the threaded fetch silently dropped in
    # production) are present alongside semester 3; unseeded semesters
    # (4-8 here) are absent, not fatal.
    assert {semester for semester, _ in scoped} == {1, 2, 3}
    assert {sub.subject_id for _, sub in scoped} == set(seeded.values())


# ----------------------------------------------------------------------
# 3. Diagnostic retrieval retries a transiently-empty curriculum fetch
# ----------------------------------------------------------------------

class _StubStore:
    async def get_college_user_profile(self, uid):
        return {"supported_path":
                EngineeringBranch.COMPUTER_SCIENCE.value}

    async def get_college_academic_context(self, uid):
        return {"context_id": "ctx_round3",
                "university_id": "univ_aicte_model", "semester": 3}

    async def get_college_goal(self, uid):
        return None

    async def get_topic_masteries(self, uid):
        return []

    async def get_context_subject_ids(self, context_id):
        return []


def test_diagnostic_retrieval_retries_empty_curriculum(monkeypatch):
    calls = {"n": 0}

    async def flaky_get_curriculum(university_id, branch, semester):
        calls["n"] += 1
        if calls["n"] == 1:
            return None  # transient registry failure, swallowed upstream
        return _fake_curriculum("CS-301")

    async def no_pyqs(university_id, subject_id):
        return None

    async def no_resources(subject_id):
        return []

    monkeypatch.setattr(retrieval_mod, "get_curriculum", flaky_get_curriculum)
    monkeypatch.setattr(retrieval_mod, "get_pyqs_for_subject", no_pyqs)
    monkeypatch.setattr(retrieval_mod, "get_resources_for_subject",
                        no_resources)

    retrieval = asyncio.run(
        retrieve_diagnostic_context(_StubStore(), ALICE_UID))

    assert calls["n"] == 2
    assert [s["subject_id"] for s in retrieval.curriculum_subjects] == [
        "CS-301"]
