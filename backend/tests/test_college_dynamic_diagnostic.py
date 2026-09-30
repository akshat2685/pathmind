"""
Dynamic/hybrid diagnostic + plan-generation hardening tests.

Covers the onboarding diagnostic (round 7: the ADK assessment agent
AUTHORS on hybrid-RAG evidence; the grounded RAG assembly is the honest
fallback) and the plan-generation failure contract.
The ADK seam is stubbed by patching run_agent_generation in the service
module namespace (recording fakes prove the seam was really invoked);
Gemini access is stubbed via backend.core.gemini.get_gemini_model —
no real API key is ever consumed here.
"""
import json

import pytest
from fastapi.testclient import TestClient

from backend.main import app
from college_testkit import install_fake_adapter
import backend.core.gemini as gemini_mod
import backend.api.college_routes as routes_mod
import backend.services.college_assessment_service as assessment_mod
import backend.services.college_diagnostic_retrieval as retrieval_mod
import backend.services.college_learning_service as learning_mod

client = TestClient(app, raise_server_exceptions=False)
ALICE = {"Authorization": "Bearer " + "alice" + "-token"}
BOB = {"Authorization": "Bearer " + "bob" + "-token"}


class _AdkRecorder:
    """Recording stand-in for the ADK one-shot generation seam.

    Records (agent_key, prompt) calls so tests can assert the seam was
    actually invoked with the right agent — proof the ADK path ran,
    not just that the suite is green.
    """

    def __init__(self, responder):
        self.calls = []
        self._responder = responder

    async def __call__(self, agent_key, prompt):
        self.calls.append((agent_key, prompt))
        return self._responder(agent_key, prompt)


def _adk_returning(text):
    return _AdkRecorder(lambda agent_key, prompt: text)


async def _adk_down(agent_key, prompt):
    raise RuntimeError("ADK unavailable in tests")


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


def test_agent_authored_diagnostic_grounded_and_evidence_shaped(monkeypatch):
    """Round 7: the ADK assessment agent AUTHORS the diagnostic on
    hybrid-RAG evidence; verified PYQs fill only topics the authored
    set left uncovered -> evidence."""
    _setup_alice()
    recorder = _adk_returning(json.dumps(CS_DIAGNOSTIC))
    monkeypatch.setattr(assessment_mod, "run_agent_generation", recorder)
    monkeypatch.setattr(gemini_mod, "get_gemini_model", lambda: ValidModel())

    r = client.post("/api/college/assessments/diagnostic", json={}, headers=ALICE)
    assert r.status_code == 200, r.text
    asmt = r.json()
    # The seam was really invoked, with the assessment agent, and the
    # payload carries the honest provenance of that path.
    assert recorder.calls and recorder.calls[0][0] == "assessment"
    assert asmt["authored_by"] == "adk:assessment_agent"
    questions = asmt["questions"]
    assert 5 <= len(questions) <= 6
    # Provenance labels survive the round trip; nothing unlabeled.
    assert all(q.get("source") for q in questions)
    assert {q["source"] for q in questions} <= {
        "verified_curriculum", "verified_pyq", "model_generated"}
    # The agent authored the set: model-labeled questions are present,
    # topics unique. Both seeded PYQ topics (Linked Lists, Arrays) are
    # already covered by the authored set, so the PYQ fill adds none.
    assert any(q["source"] == "model_generated" for q in questions)
    topics = [q["topic"] for q in questions]
    assert len(topics) == len({t.lower() for t in topics})

    # Answer: Scheduling MCQ correct, Paging MCQ wrong, shorts strong.
    answers = {}
    for q in questions:
        if q["question_type"] == "MCQ":
            answers[q["question_id"]] = (
                q["options"][1] if q["topic"] == "Scheduling"
                else q["options"][2])
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
    assert by_topic["Scheduling"]["status_label"] == "Strong"
    assert by_topic["Paging"]["status_label"] == "Weak"
    # Linked Lists is now a deterministic agent-authored MCQ answered
    # wrong -> real Weak evidence (in round 6 it was the rubric-less
    # PYQ, which graded honestly as Unknown).
    assert by_topic["Linked Lists"]["status_label"] == "Weak"

    r3 = client.get("/api/college/baseline", headers=ALICE)
    assert r3.status_code == 200
    assert r3.json()["topic_count"] >= 1


def test_fallback_diagnostic_is_grounded_and_differs_by_learner(monkeypatch):
    """No LLM at all (ADK seam down, no direct model): the grounded
    round-6 assembly ships, honestly labeled rag_fallback."""
    monkeypatch.setattr(assessment_mod, "run_agent_generation", _adk_down)
    monkeypatch.setattr(gemini_mod, "get_gemini_model", lambda: None)

    r = client.post("/api/college/assessments/diagnostic", json={}, headers=ALICE)
    assert r.status_code == 200, r.text
    assert r.json()["authored_by"] == "rag_fallback"
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
    monkeypatch.setattr(assessment_mod, "run_agent_generation", _adk_down)
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
    """ADK seam down AND direct model malformed/raising -> grounded
    fallback 200, honestly labeled, never a 500."""
    monkeypatch.setattr(assessment_mod, "run_agent_generation", _adk_down)
    monkeypatch.setattr(gemini_mod, "get_gemini_model", lambda: model)
    r = client.post("/api/college/assessments/diagnostic", json={}, headers=ALICE)
    assert r.status_code == 200, r.text
    assert r.json()["authored_by"] == "rag_fallback"
    assert all(q["source"] in {"verified_pyq", "verified_curriculum"}
               for q in r.json()["questions"])


def test_verified_label_downgraded_without_retrieved_pyqs(monkeypatch):
    """The agent may not claim PYQ provenance the retrieval did not
    supply: labels are downgraded even on the ADK path."""
    overclaimed = OverclaimingModel().generate_content("ignored").text
    monkeypatch.setattr(assessment_mod, "run_agent_generation",
                        _adk_returning(overclaimed))
    monkeypatch.setattr(gemini_mod, "get_gemini_model",
                        lambda: OverclaimingModel())
    r = client.post("/api/college/assessments/diagnostic", json={}, headers=BOB)
    assert r.status_code == 200, r.text
    assert r.json()["authored_by"] == "adk:assessment_agent"
    # Bob (ME) has no verified PYQs seeded: the claim must be downgraded.
    assert all(q["source"] != "verified_pyq" for q in r.json()["questions"])


def test_diagnostic_unavailable_only_when_nothing_exists(monkeypatch):
    """No author (seam down, no model) AND no grounded material ->
    honest 503, still not a 500."""
    monkeypatch.setattr(assessment_mod, "run_agent_generation", _adk_down)
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


def test_plan_reflects_diagnostic_evidence(fake_backend, monkeypatch):
    """Diagnostic topic mastery -> planner guidance bands (same planner)."""
    monkeypatch.setattr(gemini_mod, "get_gemini_model", lambda: ValidModel())
    # Plan personalization seam pinned DOWN: this test pins the static
    # guidance bands; the ADK-authored variant is covered in
    # test_college_round7.py.
    monkeypatch.setattr(learning_mod, "run_agent_generation", _adk_down)
    # A unit Alice has fully mastered on earlier evidence (e.g. a prior
    # checkpoint): the planner must plan revision, not a re-teach.
    alice_uid = "11111111-1111-4111-8111-111111111111"
    for topic in ("Trees", "Graphs"):
        fake_backend.client.table("learner_topic_mastery").insert({
            "user_id": alice_uid, "subject_id": "CS-301", "topic": topic,
            "mastery_score": 0.9, "outcome": "MASTERED",
            "evidence_ref": "seeded_prior_checkpoint",
        }).execute()
    r = client.post("/api/college/plans/generate",
                    json={"scope": "SEMESTER"}, headers=ALICE)
    assert r.status_code == 200, r.text
    plan = r.json()
    assert plan["phases"]
    # Seam down -> the static plan ships with honest provenance.
    assert plan["authored_by"] == "static_fallback"
    for phase in plan["phases"]:
        guidance = phase["unlock_rule"].get("diagnostic_guidance")
        assert guidance is not None
        assert guidance["band"] in {"weak", "partial", "mastered", "unknown"}

    def phase_covering(topic):
        return next(
            p for p in plan["phases"]
            if topic in (p["unlock_rule"].get("required_topics") or []))

    # Fully mastered unit -> mastered band, light-revision objective.
    trees_phase = phase_covering("Trees")
    trees_guidance = trees_phase["unlock_rule"]["diagnostic_guidance"]
    assert trees_guidance["topics"]
    assert trees_guidance["band"] == "mastered"
    assert trees_phase["objective"].startswith(
        "Quick revision — you already know this well")
    # Per-topic evidence flows through verbatim: Scheduling was aced in
    # the diagnostic; its phase-mate is still Unknown, so the phase is
    # targeted ("partial"), not a full re-teach.
    sched_phase = phase_covering("Scheduling")
    sched_guidance = sched_phase["unlock_rule"]["diagnostic_guidance"]
    assert {"topic": "Scheduling", "outcome": "MASTERED"} in (
        sched_guidance["topics"])
    assert sched_guidance["band"] == "partial"
    # Paging was missed -> weak band drives its phase, guided objective,
    # even though Virtual Memory in the same unit was mastered.
    paging_phase = phase_covering("Paging")
    paging_guidance = paging_phase["unlock_rule"]["diagnostic_guidance"]
    assert {"topic": "Paging", "outcome": "REINFORCEMENT_REQUIRED"} in (
        paging_guidance["topics"])
    assert paging_guidance["band"] == "weak"
    assert paging_phase["objective"].startswith(
        "Start here — learn the basics step by step")


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


def test_plan_generation_is_static_first_for_large_plans(fake_backend,
                                                        monkeypatch):
    """26-phase plan: generation makes NO LLM calls (static-first).

    Supersedes the round-2 head-8 enrichment cap: generation-time AI
    enrichment put every plan one slow Gemini call away from the ~60s
    serverless cap. All phases now ship static and upgrade on demand.
    """
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

    counting_model = ValidModel()
    llm_calls = []
    _orig_generate = counting_model.generate_content

    def _counting_generate(prompt):
        llm_calls.append(prompt)
        return _orig_generate(prompt)

    counting_model.generate_content = _counting_generate
    monkeypatch.setattr(gemini_mod, "get_gemini_model",
                        lambda: counting_model)
    # The ADK plan-agent seam is also pinned down: static-first means
    # the plan ships with authored_by="static_fallback", not silence.
    monkeypatch.setattr(learning_mod, "run_agent_generation", _adk_down)
    r = client.post("/api/college/plans/generate",
                    json={"scope": "SEMESTER"}, headers=BOB)
    assert r.status_code == 200, r.text
    plan = r.json()
    assert len(plan["phases"]) == 26
    # Static-first: no phase is AI-enriched at generation time...
    assert not [p for p in plan["phases"] if p["ai_enriched"]]
    # ...no LLM call happened while generating...
    assert llm_calls == []
    # ...and every phase still carries real activities (never empty shells).
    assert all(p["activities"] for p in plan["phases"])
