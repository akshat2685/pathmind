"""
Phase 3 contract tests for the PathMind College MVP (onboarding honesty).

Covers the frontend <-> backend contracts reconciled against
CollegeOnboardingFlow.tsx:

  1. POST /api/college/assessments/diagnostic (success shape with an LLM
     present, then submit -> result -> baseline derived from the per-topic
     mastery store).
  2. GET /api/college/baseline — honest empty state (no masteries) and the
     strengths/weaknesses/gaps buckets once evidence exists.
  3. Resources enrich flow: POST /api/college/resources/enrich budget
     clamping + result shape, then GET /api/college/resources serving the
     cached VERIFIED rows.
  4. POST /api/college/agent/interact with no GEMINI_API_KEY — the legacy
     deterministic orchestrator answers with the same {message, state,
     ui_blocks, sources} shape.
  5. Aspiration persistence: the free-text aspiration stored at
     exam_window.aspiration must round-trip and must not corrupt the exam
     countdown (which reads only exam_window.start).

Runs against the in-memory fake Supabase adapter: no network, no
credentials, no real writes. LLM calls are stubbed via monkeypatch.
"""
import json
from datetime import date, timedelta

import pytest
from fastapi.testclient import TestClient

from backend.main import app
from college_testkit import install_fake_adapter
import backend.services.college_assessment_service as assessment_service_module
from backend.services.college_resource_pipeline import CollegeResourcePipeline
from backend.agents import college_adk_agents as adk_agents_module


@pytest.fixture(scope="module", autouse=True)
def fake_backend():
    """Install the seeded fake Supabase adapter for this whole module."""
    adapter, restore = install_fake_adapter()
    yield adapter
    restore()


@pytest.fixture(autouse=True)
def no_llm_key(monkeypatch):
    """No Gemini key anywhere: exercises the honest no-LLM fallback paths."""
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
    import backend.core.config as config_mod
    monkeypatch.setattr(config_mod.settings, "GEMINI_API_KEY", "",
                        raising=False)


client = TestClient(app)

AUTH_ALICE = {"Authorization": "Bearer alice-token"}
AUTH_BOB = {"Authorization": "Bearer bob-token"}
ALICE_UID = "11111111-1111-4111-8111-111111111111"
BOB_UID = "22222222-2222-4222-8222-222222222222"


# ---------------------------------------------------------------------------
# Baseline endpoint: honest empty state
# ---------------------------------------------------------------------------

def test_baseline_empty_state_is_honest():
    """GET /baseline with no mastery evidence returns empty buckets, not guesses."""
    resp = client.get("/api/college/baseline", headers=AUTH_ALICE)
    assert resp.status_code == 200
    body = resp.json()
    assert body["strengths"] == []
    assert body["weaknesses"] == []
    assert body["gaps"] == []
    assert body["topic_count"] == 0
    assert body["updated_at"]  # present but ignorable extra key


# ---------------------------------------------------------------------------
# Diagnostic endpoint: success shape -> submit -> baseline from mastery store
# ---------------------------------------------------------------------------

class _StubLLMResponse:
    def __init__(self, text):
        self.text = text


def _fake_diagnostic_model():
    """Stub Gemini model returning a fixed 5-question diagnostic (JSON text)."""
    questions = [
        {"id": "dq1", "text": "What is the time complexity of binary search?",
         "type": "MCQ", "options": ["O(n)", "O(log n)", "O(n log n)", "O(1)"],
         "answer": "O(log n)", "rubric": None, "marks": 5,
         "topic": "Arrays", "subject_id": "CS-301"},
        {"id": "dq2", "text": "Inorder traversal of a BST yields what order?",
         "type": "MCQ", "options": ["Preorder", "Sorted", "Reverse", "Random"],
         "answer": "Sorted", "rubric": None, "marks": 5,
         "topic": "Trees", "subject_id": "CS-301"},
        {"id": "dq3", "text": "BFS uses which auxiliary structure?",
         "type": "MCQ", "options": ["Stack", "Queue", "Heap", "Tree"],
         "answer": "Queue", "rubric": None, "marks": 5,
         "topic": "Graphs", "subject_id": "CS-301"},
        {"id": "dq4", "text": "State the LIFO principle in one line.",
         "type": "SHORT_ANSWER", "options": [], "answer": "last in first out",
         "rubric": "mention last-in-first-out order", "marks": 10,
         "topic": "Stacks", "subject_id": "CS-301"},
        {"id": "dq5", "text": "Define a singly linked list node.",
         "type": "SHORT_ANSWER", "options": [], "answer": "data and next",
         "rubric": "mention data payload and next pointer", "marks": 10,
         "topic": "Linked Lists", "subject_id": "CS-301"},
    ]

    class _Model:
        def generate_content(self, prompt):  # noqa: ARG002 - signature parity
            return _StubLLMResponse(json.dumps(questions))

    return _Model()


def test_diagnostic_submit_and_baseline_flow(monkeypatch):
    """Full onboarding-diagnostic contract: generate -> submit -> baseline."""
    # Stub the LLM so the diagnostic author runs without network.
    monkeypatch.setattr(assessment_service_module, "_get_gemini_model",
                        _fake_diagnostic_model)

    # 1. Profile + academic context (diagnostic requires a profile).
    prof = client.post("/api/college/profile", json={"name": "Bob Tester"},
                       headers=AUTH_BOB)
    assert prof.status_code == 200
    ctx = client.post(
        "/api/college/academic-context",
        json={"university_id": "univ_aicte_model",
              "branch": "COMPUTER_SCIENCE_ENGINEER", "semester": 3,
              "subjects": ["CS-301"], "exam_window": {}},
        headers=AUTH_BOB,
    )
    assert ctx.status_code == 200

    # 2. Generate the diagnostic: matches the frontend's expected shape.
    resp = client.post("/api/college/assessments/diagnostic",
                       headers=AUTH_BOB)
    assert resp.status_code == 200
    diag = resp.json()
    assert diag["assessment_id"].startswith("diag_")
    assert diag["title"]
    questions = diag["questions"]
    assert len(questions) == 5
    for q in questions:
        assert q["question_id"] and q["question_text"]
        assert q["question_type"] in ("MCQ", "SHORT_ANSWER")
        assert q["topic"]

    # 3. Submit: 4 correct, 1 wrong (dq3) -> exercises both buckets.
    answers = {"dq1": "O(log n)", "dq2": "Sorted", "dq3": "Stack",
               "dq4": "last in first out", "dq5": "data and next"}
    sub = client.post("/api/college/assessments/submit",
                      json={"assessment_id": diag["assessment_id"],
                            "answers": answers},
                      headers=AUTH_BOB)
    assert sub.status_code == 200
    result = sub.json()
    # 30/35 = 85.7%
    assert result["score"] == pytest.approx(85.7, abs=0.1)
    assert result["mastery_status"] in ("MASTERED", "PARTIALLY_MASTERED")
    assert result["feedback"]
    assert len(result["topic_results"]) == 5
    assert all(t["topic"] for t in result["topic_results"])

    # 4. Baseline derives strengths/weaknesses/gaps from the mastery store.
    base = client.get("/api/college/baseline", headers=AUTH_BOB)
    assert base.status_code == 200
    body = base.json()
    assert body["topic_count"] == 5  # one mastery record per topic
    by_topic = {}
    for bucket in ("strengths", "weaknesses", "gaps"):
        for entry in body[bucket]:
            by_topic[entry["topic"]] = bucket
            assert "mastery_score" in entry and "outcome" in entry
    assert by_topic["Arrays"] == "strengths"          # 5/5 -> MASTERED
    assert by_topic["Trees"] == "strengths"           # 5/5 -> MASTERED
    assert by_topic["Stacks"] == "strengths"          # 10/10 -> MASTERED
    assert by_topic["Linked Lists"] == "strengths"    # 10/10 -> MASTERED
    assert by_topic["Graphs"] in ("weaknesses", "gaps")  # 0/5 -> not mastered
    assert sum(len(body[b]) for b in ("strengths", "weaknesses", "gaps")) == 5


# ---------------------------------------------------------------------------
# Resources enrich flow: POST /resources/enrich + GET /resources
# ---------------------------------------------------------------------------

def test_resources_enrich_flow_with_budget_clamp(monkeypatch):
    """Enrich returns the research result shape; budget is clamped to [5, 45]."""
    captured = {}

    async def _stub_research(self, subject_id, topic, university_name=None,
                             subject_name=None, time_budget_seconds=45.0):
        captured["budget"] = time_budget_seconds
        captured["subject_id"] = subject_id
        captured["topic"] = topic
        return {"status": "ENRICHED", "resources_added": 2,
                "resources": [{"url": "https://example.edu/notes/trees",
                               "title": "Trees notes"}]}

    monkeypatch.setattr(CollegeResourcePipeline, "research_topic",
                        _stub_research)

    # Oversized budget clamps to 45.
    resp = client.post("/api/college/resources/enrich",
                       json={"subject_id": "CS-301", "topic": "Trees",
                             "time_budget_seconds": 999},
                       headers=AUTH_ALICE)
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ENRICHED"
    assert body["resources_added"] == 2
    assert captured["budget"] == 45
    assert captured["subject_id"] == "CS-301"
    assert captured["topic"] == "Trees"

    # Undersized budget clamps to 5.
    resp = client.post("/api/college/resources/enrich",
                       json={"subject_id": "CS-301", "topic": "Trees",
                             "time_budget_seconds": 1},
                       headers=AUTH_ALICE)
    assert resp.status_code == 200
    assert captured["budget"] == 5

    # GET /resources afterwards serves the cached VERIFIED rows (kit seeds
    # two for CS-301); no URLs are ever invented by the enrich path itself.
    get = client.get("/api/college/resources?subject_id=CS-301",
                     headers=AUTH_ALICE)
    assert get.status_code == 200
    cached = get.json()
    assert cached["status"] == "VERIFIED"
    assert len(cached["resources"]) == 2
    assert all(r["url"].startswith("https://example.edu/")
               for r in cached["resources"])


# ---------------------------------------------------------------------------
# Interact endpoint: no-key fallback keeps the response shape
# ---------------------------------------------------------------------------

def test_interact_fallback_legacy_shape_without_llm_key():
    """No GEMINI_API_KEY -> legacy orchestrator, same shape contract."""
    assert not adk_agents_module._gemini_available()
    resp = client.post("/api/college/agent/interact",
                       json={"message": "How do I prepare for Data Structures?"},
                       headers=AUTH_ALICE)
    assert resp.status_code == 200
    body = resp.json()
    assert set(body) >= {"message", "state", "ui_blocks", "sources"}
    assert isinstance(body["message"], str) and body["message"]
    assert isinstance(body["state"], str) and body["state"]
    assert isinstance(body["ui_blocks"], list)
    assert isinstance(body["sources"], list)


# ---------------------------------------------------------------------------
# Aspiration persistence: free text in exam_window must not corrupt countdown
# ---------------------------------------------------------------------------

def test_aspiration_in_exam_window_keeps_countdown_honest():
    """exam_window.aspiration round-trips; countdown still reads only .start."""
    aspiration = ("I want to clear my 3rd semester with a strong CGPA, "
                  "especially in Data Structures — trees and DP. "
                  "Exam on 2027-06-01? no, just studying.")
    future = date.today() + timedelta(days=60)

    # Bob already has a profile + context from the diagnostic test above;
    # re-save the context with an aspiration alongside a valid start date.
    ctx = client.post(
        "/api/college/academic-context",
        json={"university_id": "univ_aicte_model",
              "branch": "COMPUTER_SCIENCE_ENGINEER", "semester": 3,
              "subjects": ["CS-301"],
              "exam_window": {"start": future.isoformat(),
                              "aspiration": aspiration,
                              "target_score": "8.5"}},
        headers=AUTH_BOB,
    )
    assert ctx.status_code == 200

    # The aspiration round-trips through the stored academic context.
    fetched = client.get("/api/college/academic-context", headers=AUTH_BOB)
    assert fetched.status_code == 200
    assert fetched.json()["exam_window"]["aspiration"] == aspiration
    assert fetched.json()["exam_window"]["start"] == future.isoformat()

    # The countdown still computes exactly from `start`, untouched by the
    # free-text aspiration (which even contains date-like noise).
    today = client.get("/api/college/accountability/today",
                       headers=AUTH_BOB)
    assert today.status_code == 200
    assert today.json()["exam_days_remaining"] == (future - date.today()).days

    # Aspiration with no exam date: countdown is honestly None, no crash.
    ctx2 = client.post(
        "/api/college/academic-context",
        json={"university_id": "univ_aicte_model",
              "branch": "COMPUTER_SCIENCE_ENGINEER", "semester": 3,
              "subjects": ["CS-301"],
              "exam_window": {"aspiration": aspiration}},
        headers=AUTH_BOB,
    )
    assert ctx2.status_code == 200
    today2 = client.get("/api/college/accountability/today",
                        headers=AUTH_BOB)
    assert today2.status_code == 200
    assert today2.json()["exam_days_remaining"] is None
