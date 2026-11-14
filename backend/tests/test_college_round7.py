"""
College round-7 regression tests (AJ's corrected spec + provenance rule):

- Gemini AUTHORS via the real ADK agents: the assessment agent authors
  the diagnostic on hybrid-RAG evidence; the plan agent personalizes
  the path. ADK runs the jobs through college_adk_runtime.
- PROVENANCE IS VERIFIABLE, not claimed: every generated artifact
  carries authored_by naming the path that actually produced it
  ("adk:assessment_agent" / "adk:plan_agent" only when the ADK seam
  returned text that was applied; honest fallback values otherwise).
- These tests PROVE the seam: recording fakes patch
  run_agent_generation in the service module namespaces and assert it
  was invoked with the right agent_key, and that the payload's
  authored_by matches the path taken. A green suite that never
  exercised the seam would not count.
- Resource ranking is quality-first per kind: engagement for videos,
  Tavily search_score (SEO/AEO) for documents/courses.
"""
import asyncio
import json
import re

import pytest
from fastapi.testclient import TestClient

import backend.main as main_mod
import backend.core.gemini as gemini_mod
import backend.services.college_assessment_service as assessment_mod
import backend.services.college_learning_service as learning_mod
from backend.core.college_schemas import ResourceRecord
from backend.services.college_learning_service import _resource_quality
from college_testkit import install_fake_adapter

client = TestClient(main_mod.app)

ALICE = {"Authorization": "Bearer alice-token", "Content-Type": "application/json"}
ALICE_UID = "11111111-1111-4111-8111-111111111111"


@pytest.fixture(scope="module", autouse=True)
def fake_backend():
    adapter, restore = install_fake_adapter()
    yield adapter
    restore()


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


class _AdkRecorder:
    """Recording stand-in for the ADK one-shot generation seam."""

    def __init__(self, responder):
        self.calls = []
        self._responder = responder

    async def __call__(self, agent_key, prompt, **kwargs):
        self.calls.append((agent_key, prompt, kwargs))
        return self._responder(agent_key, prompt)


async def _adk_down(agent_key, prompt, **kwargs):
    raise RuntimeError("ADK unavailable in tests")


# ---------------------------------------------------------------------------
# Diagnostic: the ADK assessment agent authors, provenance proves it
# ---------------------------------------------------------------------------

_DIAG_PAYLOAD = json.dumps([
    {"id": "dq1", "text": "Head insertion complexity in a singly linked list?",
     "type": "MCQ", "options": ["O(1)", "O(n)", "O(log n)", "O(n log n)"],
     "answer": "A", "topic": "Linked Lists", "marks": 5,
     "probe": "concept", "source": "verified_curriculum"},
    {"id": "dq2", "text": "Which scheduling algorithm can starve processes?",
     "type": "MCQ", "options": ["Round Robin", "SJF", "FCFS", "Multilevel"],
     "answer": "B", "topic": "Scheduling", "marks": 5,
     "probe": "concept", "source": "verified_curriculum"},
    {"id": "dq3", "text": "In paging, a page fault occurs when?",
     "type": "MCQ", "options": ["Page in RAM", "Page not in RAM", "TLB hit",
                                "Cache miss"],
     "answer": "B", "topic": "Paging", "marks": 5,
     "probe": "misconception", "source": "model_generated"},
])


def test_diagnostic_adk_provenance_and_seam(monkeypatch):
    _setup_alice()
    recorder = _AdkRecorder(lambda agent_key, prompt: _DIAG_PAYLOAD)
    monkeypatch.setattr(assessment_mod, "run_agent_generation", recorder)
    monkeypatch.setattr(gemini_mod, "get_gemini_model", lambda: None)

    r = client.post("/api/college/assessments/diagnostic", json={},
                    headers=ALICE)
    assert r.status_code == 200, r.text
    body = r.json()
    # Proof the ADK path ran: seam invoked once, with the assessment
    # agent, and the payload says so.
    assert [c[0] for c in recorder.calls] == ["assessment"]
    assert body["authored_by"] == "adk:assessment_agent"
    questions = body["questions"]
    assert 4 <= len(questions) <= 6
    assert any(q["source"] == "model_generated" for q in questions)
    # The authored set covered Linked Lists; the real verified PYQ on
    # Arrays fills the uncovered topic (never displacing authored work).
    assert any(q["source"] == "verified_pyq" and q["topic"] == "Arrays"
               for q in questions)


def test_diagnostic_rag_fallback_provenance(monkeypatch):
    _setup_alice()
    monkeypatch.setattr(assessment_mod, "run_agent_generation", _adk_down)
    monkeypatch.setattr(gemini_mod, "get_gemini_model", lambda: None)

    r = client.post("/api/college/assessments/diagnostic", json={},
                    headers=ALICE)
    assert r.status_code == 200, r.text
    body = r.json()
    # Seam down + no direct model: honest fallback label, real material.
    assert body["authored_by"] == "rag_fallback"
    assert any(q["source"] == "verified_pyq" for q in body["questions"])


# ---------------------------------------------------------------------------
# Plan: the ADK plan agent personalizes, provenance proves it
# ---------------------------------------------------------------------------

def _plan_responder(agent_key, prompt):
    phase_ids = re.findall(r'"phase_id":\s*"([^"]+)"', prompt)
    return json.dumps({"phases": [
        {"phase_id": pid,
         "objective": "Personalized: master this unit first.",
         "focus_topics": ["Linked Lists"],
         "technique": "Active recall sprints"}
        for pid in phase_ids]})


def test_plan_personalization_applied_via_adk(monkeypatch):
    _setup_alice()
    recorder = _AdkRecorder(_plan_responder)
    monkeypatch.setattr(learning_mod, "run_agent_generation", recorder)

    r = client.post("/api/college/plans/generate",
                    json={"scope": "SEMESTER"}, headers=ALICE)
    assert r.status_code == 200, r.text
    plan = r.json()
    # Proof the ADK path ran: seam invoked with the plan agent, payload
    # provenance set, and the authored content actually applied.
    assert [c[0] for c in recorder.calls] == ["plan"]
    assert plan["authored_by"] == "adk:plan_agent"
    first = plan["phases"][0]
    assert first["objective"] == "Personalized: master this unit first."
    guidance = first["unlock_rule"]["diagnostic_guidance"]
    assert guidance["technique"] == "Active recall sprints"
    assert guidance["focus_topics"] == ["Linked Lists"]


def test_plan_static_fallback_when_agent_raises(monkeypatch):
    _setup_alice()
    monkeypatch.setattr(learning_mod, "run_agent_generation", _adk_down)

    r = client.post("/api/college/plans/generate",
                    json={"scope": "SEMESTER"}, headers=ALICE)
    assert r.status_code == 200, r.text
    plan = r.json()
    assert plan["phases"]
    assert plan["authored_by"] == "static_fallback"
    # Static objectives survive untouched (deterministic prefixes).
    assert plan["phases"][0]["objective"]


def test_plan_static_fallback_on_malformed_output(monkeypatch):
    _setup_alice()
    recorder = _AdkRecorder(lambda agent_key, prompt: "not json {{{")
    monkeypatch.setattr(learning_mod, "run_agent_generation", recorder)

    r = client.post("/api/college/plans/generate",
                    json={"scope": "SEMESTER"}, headers=ALICE)
    assert r.status_code == 200, r.text
    plan = r.json()
    assert plan["phases"]
    # The seam returned text, but nothing usable: the label must NOT
    # claim ADK authorship.
    assert plan["authored_by"] == "static_fallback"


def test_plan_ignores_unknown_phase_ids(monkeypatch):
    _setup_alice()

    def responder(agent_key, prompt):
        # The prompt also quotes the output-shape example ("...\"), so
        # keep only real phase ids.
        phase_ids = [p for p in re.findall(r'"phase_id":\s*"([^"]+)"', prompt)
                     if p.startswith("phase_plan_")]
        assert phase_ids
        return json.dumps({"phases": [
            {"phase_id": phase_ids[0], "objective": "Real objective",
             "technique": "Spaced recall"},
            {"phase_id": "phase_bogus_xyz", "objective": "BOGUS-OBJECTIVE",
             "technique": "Bogus method"},
        ]})

    recorder = _AdkRecorder(responder)
    monkeypatch.setattr(learning_mod, "run_agent_generation", recorder)

    r = client.post("/api/college/plans/generate",
                    json={"scope": "SEMESTER"}, headers=ALICE)
    assert r.status_code == 200, r.text
    plan = r.json()
    assert plan["authored_by"] == "adk:plan_agent"
    assert plan["phases"][0]["objective"] == "Real objective"
    assert all(p["objective"] != "BOGUS-OBJECTIVE" for p in plan["phases"])
    assert all(
        (p["unlock_rule"].get("diagnostic_guidance") or {}).get(
            "technique") != "Bogus method"
        for p in plan["phases"])


# ---------------------------------------------------------------------------
# Resource quality: kind-native signal (engagement vs search relevance)
# ---------------------------------------------------------------------------

def _res(resource_type, signals, rid="res_q"):
    return ResourceRecord(
        resource_id=rid, title="Linked Lists Material",
        resource_type=resource_type, provider="Example",
        url=f"https://example.edu/{rid}", source_id="src_t",
        source_tier="C", topic_ids=["Linked Lists"],
        quality_signals=signals)


def test_resource_quality_signal_by_kind():
    # Videos rank by real engagement.
    assert _resource_quality(
        _res("VIDEO", {"engagement_score": 12.5})) == 12.5
    # Documents/courses rank by the Tavily SEO/AEO relevance score.
    assert _resource_quality(
        _res("DOCUMENT", {"search_score": 0.9})) == 0.9
    assert _resource_quality(
        _res("NOTES", {"tavily_score": 0.5})) == 0.5
    # No score: engagement fallback, then honest 0.
    assert _resource_quality(
        _res("DOCUMENT", {"engagement_score": 3.0})) == 3.0
    assert _resource_quality(_res("DOCUMENT", {})) == 0.0


def test_decorate_prefers_highest_search_score_document(monkeypatch):
    from backend.core.college_schemas import (
        ActivityType, CollegeActivity, CollegeLearningPlan, CollegePlanPhase,
    )
    from backend.services.college_learning_service import CollegeLearningService

    low = _res("DOCUMENT", {"search_score": 0.2}, rid="res_low_score")
    high = _res("DOCUMENT", {"search_score": 0.95}, rid="res_high_score")

    async def fake_resources(subject_id):
        return [low, high] if subject_id == "CS-301" else []

    monkeypatch.setattr(learning_mod, "get_resources_for_subject",
                        fake_resources)

    phase = CollegePlanPhase(
        phase_id="phase_plan_seotest_CS-301_s3_u1",
        user_id=ALICE_UID, plan_id="plan_seotest", order=1,
        title="CS-301: Linked Lists", objective="Learn linked lists.",
        status="AVAILABLE",
        activities=[CollegeActivity(
            activity_id="act_seo_u1", user_id=ALICE_UID,
            plan_id="plan_seotest",
            phase_id="phase_plan_seotest_CS-301_s3_u1",
            activity_type=ActivityType.READ,
            title="Read Verified Notes: Linked Lists",
            order=1, instructions="Read the notes.")])
    plan = CollegeLearningPlan(
        plan_id="plan_seotest", user_id=ALICE_UID, goal_id="goal_seotest",
        phases=[phase])

    decorated = asyncio.run(CollegeLearningService()._decorate_plan(plan))
    read = next(a for a in decorated.phases[0].activities
                if a.activity_type == ActivityType.READ)
    assert read.resource is not None
    # Same topic, same tier: the higher Tavily relevance score wins.
    assert read.resource.resource_id == "res_high_score"
