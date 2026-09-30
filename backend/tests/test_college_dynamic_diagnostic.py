"""
Dynamic/hybrid diagnostic + plan-generation hardening tests.

Covers the reworked onboarding diagnostic (retrieval-grounded, Gemini as
reasoning layer, honest fallback) and the plan-generation failure contract.
All Gemini access is stubbed via backend.core.gemini.get_gemini_model —
no real API key is ever consumed here.
"""
import json

import pytest
from fastapi.testclient import TestClient

from backend.main import app
from college_testkit import install_fake_adapter
import backend.core.gemini as gemini_mod
import backend.api.college_routes as routes_mod
import backend.services.college_diagnostic_retrieval as retrieval_mod

client = TestClient(app, raise_server_exceptions=False)
ALICE = {"Authorization": "Bearer " + "alice" + "-token"}
BOB = {"Authorization": "Bearer " + "bob" + "-token"}


class Resp:
    def __init__(self, text):
        self.text = text


CS_DIAGNOSTIC = [
    {"id": "dq1", "text": "What is the time complexity of head insertion in a singly linked list?",
     "type": "MCQ", "options": ["O(1)", "O(n)", "O(log n)", "O(n log n)"], "answer": "A",
     "topic": "Linked Lists", "marks": 5, "probe": "concept",
     "source": "verified_curriculum"},
    {"id": "dq2", "text": "Which scheduling algorithm can cause starvation?",
     "type": "MCQ", "options": ["Round Robin", "SJF", "FCFS", "Multilevel"],
     "answer": "B", "topic": "Scheduling", "marks": 5, "probe": "concept",
     "source": "verified_curriculum"},
    {"id": "dq3", "text": "In paging, a page fault occurs when?",
     "type": "MCQ", "options": ["Page in RAM", "Page not in RAM", "TLB hit", "Cache miss"],
     "answer": "B", "topic": "Paging", "marks": 5, "probe": "misconception",
     "source": "model_generated"},
    {"id": "dq4", "text": "Explain why arrays give O(1) random access but linked lists do not.",
     "type": "SHORT_ANSWER", "rubric": "Contiguous memory + index arithmetic vs pointer traversal",
     "topic": "Arrays", "marks": 5, "probe": "concept",
     "source": "verified_curriculum"},
    {"id": "dq5", "text": "Describe how virtual memory lets processes exceed physical RAM.",
     "type": "SHORT_ANSWER", "rubric": "Pages swapped between disk and RAM on demand",
     "topic": "Virtual Memory", "marks": 5, "probe": "application",
     "source": "model_generated"},
]


class ValidModel:
    def generate_content(self, prompt):
        if "Diagnostic Author" in prompt:
            return Resp(json.dumps(CS_DIAGNOSTIC))
        if "Study Planner" in prompt:
            return Resp(json.dumps([
                {"type": "WATCH", "title": "Watch: core lecture",
                 "instructions": "Watch actively.", "minutes": 30},
                {"type": "PRACTICE", "title": "Practice set",
                 "instructions": "Solve 5 problems.", "minutes": 40},
            ]))
        return Resp(json.dumps(
            {"score": 4.0, "confidence": "high", "reasoning": "Covers the rubric."}))


class MalformedModel:
    def generate_content(self, prompt):
        return Resp("Sorry, I cannot produce JSON right now {{{")


class RaisingModel:
    def generate_content(self, prompt):
        raise RuntimeError("429 RESOURCE_EXHAUSTED: quota exceeded")


class OverclaimingModel:
    """Claims verified_pyq provenance it does not have."""

    def generate_content(self, prompt):
        qs = [dict(q, source="verified_pyq") for q in CS_DIAGNOSTIC]
        return Resp(json.dumps(qs))


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


def _setup_bob_me():
    r = client.post("/api/college/profile",
                    json={"name": "Bob", "email": "bob@example.com"},
                    headers=BOB)
    assert r.status_code == 200, r.text
    r = client.post("/api/college/academic-context", json={
        "university_id": "univ_aicte_model",
        "branch": "MECHANICAL_ENGINEER",
        "semester": 3, "subjects": ["ME-301", "ME-302"],
        "available_hours_per_week": 8,
    }, headers=BOB)
    assert r.status_code == 200, r.text


def test_gemini_diagnostic_grounded_and_evidence_shaped(monkeypatch):
    """Happy path: retrieval + Gemini -> labeled questions -> evidence."""
    _setup_alice()
    monkeypatch.setattr(gemini_mod, "get_gemini_model", lambda: ValidModel())

    r = client.post("/api/college/assessments/diagnostic", json={}, headers=ALICE)
    assert r.status_code == 200, r.text
    asmt = r.json()
    questions = asmt["questions"]
    assert 5 <= len(questions) <= 6
    # Provenance labels survive the round trip; nothing unlabeled.
    assert all(q.get("source") for q in questions)
    assert {q["source"] for q in questions} <= {
        "verified_curriculum", "verified_pyq", "model_generated"}

    # Answer: dq1 correct (O(1)), dq2/dq3 wrong, shorts strong.
    answers = {}
    for q in questions:
        if q["question_type"] == "MCQ":
            answers[q["question_id"]] = (
                q["options"][0] if q["question_id"] == "dq1" else q["options"][2])
        else:
            answers[q["question_id"]] = (
                "Contiguous memory allows index arithmetic; linked lists "
                "must traverse pointers node by node.")
    r2 = client.post("/api/college/assessments/submit",
                     json={"assessment_id": asmt["assessment_id"],
                           "answers": answers}, headers=ALICE)
    assert r2.status_code == 200, r2.text
    result = r2.json()
    # Evidence model: every topic carries an outcome + plain-language label.
    for tr in result["topic_results"]:
        assert tr["outcome"] in {"MASTERED", "PARTIALLY_MASTERED",
                                  "REINFORCEMENT_REQUIRED",
                                  "INSUFFICIENT_EVIDENCE"}
        assert tr["status_label"] in {"Strong", "Partial", "Weak", "Unknown"}
        assert tr["likely_issue"]
    by_topic = {tr["topic"]: tr for tr in result["topic_results"]}
    assert by_topic["Linked Lists"]["status_label"] == "Strong"
    assert by_topic["Scheduling"]["status_label"] in {"Weak", "Partial"}

    r3 = client.get("/api/college/baseline", headers=ALICE)
    assert r3.status_code == 200
    assert r3.json()["topic_count"] >= 1


def test_fallback_diagnostic_is_grounded_and_differs_by_learner(monkeypatch):
    """No Gemini at all: real PYQ/curriculum probes, different per learner."""
    monkeypatch.setattr(gemini_mod, "get_gemini_model", lambda: None)

    r = client.post("/api/college/assessments/diagnostic", json={}, headers=ALICE)
    assert r.status_code == 200, r.text
    alice_qs = r.json()["questions"]
    assert len(alice_qs) >= 3
    # Fallback may only use retrieved, verified material — never invented.
    assert all(q["source"] in {"verified_pyq", "verified_curriculum"}
               for q in alice_qs)
    alice_text = " ".join(q["question_text"] for q in alice_qs)

    _setup_bob_me()
    r = client.post("/api/college/assessments/diagnostic", json={}, headers=BOB)
    assert r.status_code == 200, r.text
    bob_qs = r.json()["questions"]
    assert len(bob_qs) >= 3
    assert all(q["source"] in {"verified_pyq", "verified_curriculum"}
               for q in bob_qs)
    bob_text = " ".join(q["question_text"] for q in bob_qs)

    # The diagnostic actually changes with the learner's branch/subjects.
    assert alice_text != bob_text
    assert "Thermodynamics" in bob_text or "Fluid" in bob_text
    assert "Linked" in alice_text or "Data Structures" in alice_text


def test_fallback_answers_grade_as_unknown_not_fabricated(monkeypatch):
    """Fallback short answers have no rubric: honest Unknown, no fake score."""
    monkeypatch.setattr(gemini_mod, "get_gemini_model", lambda: None)
    r = client.post("/api/college/assessments/diagnostic", json={}, headers=ALICE)
    assert r.status_code == 200, r.text
    asmt = r.json()
    answers = {q["question_id"]: "Some explanation of the topic."
               for q in asmt["questions"]}
    r2 = client.post("/api/college/assessments/submit",
                     json={"assessment_id": asmt["assessment_id"],
                           "answers": answers}, headers=ALICE)
    assert r2.status_code == 200, r2.text
    for tr in r2.json()["topic_results"]:
        assert tr["outcome"] == "INSUFFICIENT_EVIDENCE"
        assert tr["status_label"] == "Unknown"


@pytest.mark.parametrize("model", [MalformedModel(), RaisingModel()])
def test_gemini_failure_never_500_falls_back(monkeypatch, model):
    """Malformed/raising Gemini -> grounded fallback 200, never a 500."""
    monkeypatch.setattr(gemini_mod, "get_gemini_model", lambda: model)
    r = client.post("/api/college/assessments/diagnostic", json={}, headers=ALICE)
    assert r.status_code == 200, r.text
    assert all(q["source"] in {"verified_pyq", "verified_curriculum"}
               for q in r.json()["questions"])


def test_verified_label_downgraded_without_retrieved_pyqs(monkeypatch):
    """Gemini may not claim PYQ provenance the retrieval did not supply."""
    monkeypatch.setattr(gemini_mod, "get_gemini_model",
                        lambda: OverclaimingModel())
    r = client.post("/api/college/assessments/diagnostic", json={}, headers=BOB)
    assert r.status_code == 200, r.text
    # Bob (ME) has no verified PYQs seeded: the claim must be downgraded.
    assert all(q["source"] != "verified_pyq" for q in r.json()["questions"])


def test_diagnostic_unavailable_only_when_nothing_exists(monkeypatch):
    """No model AND no grounded material -> honest 503, still not a 500."""
    monkeypatch.setattr(gemini_mod, "get_gemini_model", lambda: None)

    async def empty_retrieval(store, uid):
        from backend.services.college_diagnostic_retrieval import (
            DiagnosticRetrieval)
        return DiagnosticRetrieval(branch="COMPUTER_SCIENCE_ENGINEER")

    monkeypatch.setattr(retrieval_mod, "retrieve_diagnostic_context",
                        empty_retrieval)
    r = client.post("/api/college/assessments/diagnostic", json={}, headers=ALICE)
    assert r.status_code == 503, r.text
    assert "DIAGNOSTIC_UNAVAILABLE" in r.json()["detail"]


def test_plan_reflects_diagnostic_evidence(monkeypatch):
    """Weak diagnostic topic -> guided phase in the SAME existing planner."""
    monkeypatch.setattr(gemini_mod, "get_gemini_model", lambda: ValidModel())
    r = client.post("/api/college/plans/generate",
                    json={"scope": "SEMESTER"}, headers=ALICE)
    assert r.status_code == 200, r.text
    plan = r.json()
    assert plan["phases"]
    for phase in plan["phases"]:
        guidance = phase["unlock_rule"].get("diagnostic_guidance")
        assert guidance is not None
        assert guidance["band"] in {"weak", "partial", "mastered", "unknown"}
    ll_phase = next(
        p for p in plan["phases"]
        if "Linked Lists" in (p["unlock_rule"].get("required_topics") or []))
    ll_guidance = ll_phase["unlock_rule"]["diagnostic_guidance"]
    assert ll_guidance["topics"]
    # Alice aced the Linked Lists MCQ in the first test -> mastered band,
    # light-revision objective (not a full re-teach).
    assert ll_guidance["band"] == "mastered"
    assert ll_phase["objective"].startswith(
        "Light revision with spaced retrieval")
    # She missed the Scheduling MCQ -> weak band, guided objective.
    sched_phase = next(
        p for p in plan["phases"]
        if "Scheduling" in (p["unlock_rule"].get("required_topics") or []))
    assert sched_phase["unlock_rule"]["diagnostic_guidance"]["band"] == "weak"
    assert sched_phase["objective"].startswith(
        "Guided intensive learning first")


def test_plan_generation_failure_contract(monkeypatch):
    """Unexpected plan errors -> structured 503, never an unexplained 500."""
    async def boom(**kwargs):
        raise TypeError("simulated unexpected failure")

    monkeypatch.setattr(
        routes_mod.learning_service, "generate_learning_plan", boom)
    r = client.post("/api/college/plans/generate",
                    json={"scope": "SEMESTER"}, headers=ALICE)
    assert r.status_code == 503, r.text
    detail = r.json()["detail"]
    assert detail["code"].startswith("PLAN_GENERATION_FAILED")
    assert "simulated unexpected failure" in detail["message"]

    async def persistence_down(**kwargs):
        raise RuntimeError("PERSISTENCE_UNAVAILABLE: simulated outage")

    monkeypatch.setattr(
        routes_mod.learning_service, "generate_learning_plan",
        persistence_down)
    r = client.post("/api/college/plans/generate",
                    json={"scope": "SEMESTER"}, headers=ALICE)
    assert r.status_code == 503, r.text
    assert r.json()["detail"]["code"] == "PERSISTENCE_UNAVAILABLE"


def test_plan_llm_enrichment_bounded_for_large_plans(fake_backend, monkeypatch):
    """26-phase plan: generation-time LLM enrichment capped at 8 phases."""
    client_fake = fake_backend.client
    client_fake.table("universities").insert({
        "university_id": "rtu", "name": "Rajasthan Technical University",
        "normalized_name": "rajasthan technical university",
        "official_domain": "rtu.ac.in", "verification_status": "VERIFIED",
        "country": "India", "state": "Rajasthan",
    }).execute()
    client_fake.table("programs").insert({
        "program_id": "rtu_cse", "university_id": "rtu",
        "branch": "COMPUTER_SCIENCE_ENGINEER", "name": "B.Tech CSE (RTU)",
        "degree_type": "BTECH",
    }).execute()
    client_fake.table("curricula").insert({
        "curriculum_id": "rtu_cse_sem7", "program_id": "rtu_cse",
        "university_id": "rtu", "semester": 7,
        "verification_status": "VERIFIED",
    }).execute()
    subject_ids = []
    for s in range(1, 8):
        sid = f"rtu_cse_7cs{s}_01"
        subject_ids.append(sid)
        client_fake.table("subjects").insert({
            "subject_id": sid, "code": f"7CS{s}-01", "name": f"Subject {s}",
            "credits": 3,
        }).execute()
        client_fake.table("curriculum_subjects").insert({
            "curriculum_id": "rtu_cse_sem7", "subject_id": sid,
        }).execute()
        for u in range(1, (4 if s <= 5 else 3) + 1):
            client_fake.table("curriculum_units").insert({
                "curriculum_id": "rtu_cse_sem7", "subject_id": sid,
                "unit": u, "title": f"Unit {u} of Subject {s}",
                "topics": [f"Topic {s}.{u}.1", f"Topic {s}.{u}.2"],
                "weightage": 0.2, "verification_status": "VERIFIED",
            }).execute()

    r = client.post("/api/college/academic-context", json={
        "university_id": "rtu", "branch": "COMPUTER_SCIENCE_ENGINEER",
        "semester": 7, "subjects": subject_ids, "available_hours_per_week": 12,
    }, headers=BOB)
    assert r.status_code == 200, r.text

    monkeypatch.setattr(gemini_mod, "get_gemini_model", lambda: ValidModel())
    r = client.post("/api/college/plans/generate",
                    json={"scope": "SEMESTER"}, headers=BOB)
    assert r.status_code == 200, r.text
    plan = r.json()
    assert len(plan["phases"]) == 26
    enriched = [p for p in plan["phases"] if p["ai_enriched"]]
    assert len(enriched) == 8
    assert all(p["order"] <= 8 for p in enriched)
    # Tail phases still carry real activities (never empty shells).
    assert all(p["activities"] for p in plan["phases"])
