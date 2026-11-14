"""
MCQ integrity tests (round-2 fix for "MCQ answers not registering").

Root cause class: question construction trusted the model's own "id" field
(models repeat "q1"), never validated that the correct answer is one of the
options, stored letter answers ("B") verbatim, and passed the question type
through unnormalized — a lowercase "mcq" renders no input at all in the
frontend (`question_type === "MCQ"`). Any of these makes a learner's answer
impossible to register or score.

Contract after the fix, for BOTH the checkpoint generator and the diagnostic
validator:
  - question ids are canonical and server-assigned (q1..qn / dq1..dqn),
  - options are deduped strings, at least 2 (checkpoint) / 3 (diagnostic),
  - a letter answer is resolved to the option text at build time,
  - an answer that is not one of the options drops the question,
  - question types are normalized to MCQ / SHORT_ANSWER.

All Gemini access is stubbed; no real API key is consumed.
"""
import json
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from backend.main import app
from college_testkit import install_fake_adapter
import backend.core.gemini as gemini_mod
from backend.services.college_assessment_service import CollegeAssessmentService

client = TestClient(app, raise_server_exceptions=False)
ALICE = {"Authorization": "Bearer " + "alice" + "-token"}


class Resp:
    def __init__(self, text):
        self.text = text


# A deliberately messy model: duplicate ids everywhere, a letter answer,
# a lowercase type, a duplicated option, and one unanswerable MCQ whose
# "answer" is not among its options (must be dropped, not shipped).
MESSY_CHECKPOINT = [
    {"id": "q1", "text": "What does an IoT gateway primarily do?",
     "type": "MCQ",
     "options": ["Aggregates sensor data", "Manufactures sensors",
                 "Replaces cloud storage", "Designs chips"],
     "answer": "A", "marks": 5},
    {"id": "q1", "text": "Which protocol is designed for constrained devices?",
     "type": "mcq",
     "options": ["MQTT", "SMTP", "FTP", "SMTP"],
     "answer": "MQTT", "marks": 5},
    {"id": "q1", "text": "Which layer handles device addressing?",
     "type": "MCQ",
     "options": ["Network layer", "Application layer"],
     "answer": "Physical layer", "marks": 5},
    {"id": "q1", "text": "Explain how you would secure sensor-to-cloud traffic.",
     "type": "SHORT_ANSWER",
     "rubric": "TLS/DTLS, device identity, key rotation", "marks": 10},
]


class MessyCheckpointModel:
    def generate_content(self, prompt):
        return Resp(json.dumps(MESSY_CHECKPOINT))


@pytest.fixture(scope="module", autouse=True)
def fake_backend():
    adapter, restore = install_fake_adapter()
    yield adapter
    restore()


def _service() -> CollegeAssessmentService:
    return CollegeAssessmentService()


def test_checkpoint_questions_get_canonical_ids_and_clean_mcqs():
    svc = _service()
    questions = svc._generate_questions_with_llm(
        MessyCheckpointModel(), "CS-301", "IoT Basics", ["IoT Basics"])

    # The unanswerable MCQ (answer not in options) is dropped; the rest are
    # renumbered canonically — no duplicate ids survive.
    assert [q.question_id for q in questions] == ["q1", "q2", "q3"]

    q1, q2, q3 = questions
    # Letter answer "A" resolved to the option text at build time.
    assert q1.question_type == "MCQ"
    assert q1.correct_answer == "Aggregates sensor data"
    assert q1.correct_answer in q1.options
    # Lowercase "mcq" normalized; duplicate option removed.
    assert q2.question_type == "MCQ"
    assert q2.options == ["MQTT", "SMTP", "FTP"]
    assert q2.correct_answer == "MQTT"
    assert q3.question_type == "SHORT_ANSWER"


def test_checkpoint_drops_everything_malformed():
    svc = _service()
    junk = [
        "not-a-dict",
        {"text": "", "type": "MCQ", "options": ["a", "b"], "answer": "a"},
        {"text": "One option only", "type": "MCQ",
         "options": ["only"], "answer": "only"},
        {"text": "Mystery type", "type": "ESSAY", "options": ["a", "b"],
         "answer": "a"},
    ]

    class JunkModel:
        def generate_content(self, prompt):
            return Resp(json.dumps(junk))

    assert svc._generate_questions_with_llm(
        JunkModel(), "CS-301", "Topic", ["Topic"]) == []
    # No model at all -> empty (caller falls back to static questions).
    assert svc._generate_questions_with_llm(
        None, "CS-301", "Topic", ["Topic"]) == []


def test_diagnostic_validator_canonical_ids_and_letter_resolution():
    retrieval = SimpleNamespace(pyq_questions=[], curriculum_subjects=[])
    gen = [
        {"id": "q1", "text": "Pick the O(1) operation.",
         "type": "MCQ", "options": ["Array index", "List search",
                                   "Tree sort", "Graph BFS"],
         "answer": "A", "topic": "Arrays", "marks": 5,
         "probe": "concept", "source": "model_generated"},
        {"id": "q1", "text": "Pick the starvation-prone scheduler.",
         "type": "MCQ", "options": ["Round Robin", "SJF", "FCFS"],
         "answer": "B", "topic": "Scheduling", "marks": 5,
         "probe": "concept", "source": "model_generated"},
    ]
    questions = CollegeAssessmentService._validate_generated_questions(
        gen, retrieval)
    assert [q.question_id for q in questions] == ["dq1", "dq2"]
    assert questions[0].correct_answer == "Array index"
    assert questions[1].correct_answer == "SJF"
    for q in questions:
        assert q.correct_answer in q.options


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


def test_checkpoint_generate_submit_roundtrip_with_messy_model(monkeypatch):
    """End to end: messy model output still yields a checkpoint whose MCQs
    register and score — the learner-visible contract behind the bug."""
    _setup_alice()
    monkeypatch.setattr(gemini_mod, "get_gemini_model",
                        lambda: MessyCheckpointModel())

    r = client.post("/api/college/assessments/generate", json={
        "plan_id": "plan_test", "phase_id": "phase_test",
        "subject_id": "CS-301", "topic_title": "IoT Basics",
    }, headers=ALICE)
    assert r.status_code == 200, r.text
    assessment = r.json()
    questions = assessment["questions"]
    assert [q["question_id"] for q in questions] == ["q1", "q2", "q3"]
    mcqs = [q for q in questions if q["question_type"] == "MCQ"]
    assert len(mcqs) == 2
    for q in mcqs:
        assert q["correct_answer"] in q["options"]

    answers = {q["question_id"]: q["correct_answer"] for q in mcqs}
    answers["q3"] = "Use TLS with per-device certificates and rotate keys."
    r = client.post("/api/college/assessments/submit", json={
        "assessment_id": assessment["assessment_id"], "answers": answers,
    }, headers=ALICE)
    assert r.status_code == 200, r.text
    result = r.json()
    by_id = {t["question_id"]: t for t in result["topic_results"]}
    # Both MCQs earned full marks — answers registered and scored.
    assert by_id["q1"]["earned_marks"] == by_id["q1"]["total_marks"] == 5
    assert by_id["q2"]["earned_marks"] == by_id["q2"]["total_marks"] == 5
    assert result["score"] >= 50.0
