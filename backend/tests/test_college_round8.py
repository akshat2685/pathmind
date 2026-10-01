"""
College round-8 regression tests (final pass, 2026-10-01):

- The authored_by persistence defect: round 7 added `authored_by` to
  the assessment/plan payloads but the production tables had no such
  column, and the store upserts model dumps wholesale — PostgREST
  rejected every diagnostic/plan save (503 PERSISTENCE_UNAVAILABLE,
  reproduced live). The columns now exist (migration
  college_authored_by_columns.sql, applied live 2026-10-01) AND the
  store whitelist-filters its dumps to verified columns, so a future
  model-only field can never kill a save again.
- The fake Supabase client is now STRICT for the five wholesale-dump
  tables (PostgREST parity): unknown keys raise. That is the safety
  net whose absence let the defect above ship green.
- Gemini latency: default-config generations measured ~30s+ live,
  starving every chained flow inside the 60s serverless window. One-
  shot authoring now runs with thinking disabled + capped output
  (fast_generation_config / generate_fast; generate_content_config on
  the ADK agents), and the diagnostic chain skips its direct leg when
  the ADK attempt already spent the request budget.
"""
import asyncio
import json
import re
import time as time_mod

import pytest
from fastapi.testclient import TestClient

import backend.main as main_mod
import backend.core.gemini as gemini_mod
import backend.services.college_assessment_service as assessment_mod
import backend.services.college_learning_service as learning_mod
from backend.core.gemini import fast_generation_config, generate_fast
from backend.services.college_store import CollegeStore
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


# ---------------------------------------------------------------------------
# authored_by: persists through the strict fake and round-trips
# ---------------------------------------------------------------------------

def test_diagnostic_authored_by_persists_and_roundtrips(
        monkeypatch, fake_backend):
    _setup_alice()
    recorder = _AdkRecorder(lambda agent_key, prompt: _DIAG_PAYLOAD)
    monkeypatch.setattr(assessment_mod, "run_agent_generation", recorder)
    monkeypatch.setattr(gemini_mod, "get_gemini_model", lambda: None)

    r = client.post("/api/college/assessments/diagnostic", json={},
                    headers=ALICE)
    # Pre-fix (no column / no whitelist) this save 503'd in production.
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["authored_by"] == "adk:assessment_agent"

    # The raw stored row carries the provenance (the strict fake would
    # have raised on the upsert if the key were not a real column).
    rows = fake_backend.client._tables["assessments"]._rows
    stored = [row for row in rows
              if row["assessment_id"] == body["assessment_id"]]
    assert stored and stored[0]["authored_by"] == "adk:assessment_agent"

    # And it reads back through the store onto the model.
    store = CollegeStore()
    loaded = asyncio.run(
        store.get_college_assessment(ALICE_UID, body["assessment_id"]))
    assert loaded is not None
    assert loaded.authored_by == "adk:assessment_agent"


def test_plan_authored_by_persists_and_roundtrips(monkeypatch):
    _setup_alice()

    def responder(agent_key, prompt):
        phase_ids = [p for p in re.findall(
            r'"phase_id":\s*"([^"]+)"', prompt)
            if p.startswith("phase_plan_")]
        return json.dumps({"phases": [
            {"phase_id": pid, "objective": "Personalized objective.",
             "focus_topics": ["Linked Lists"],
             "technique": "Active recall sprints"}
            for pid in phase_ids]})

    recorder = _AdkRecorder(responder)
    monkeypatch.setattr(learning_mod, "run_agent_generation", recorder)

    r = client.post("/api/college/plans/generate",
                    json={"scope": "SEMESTER"}, headers=ALICE)
    assert r.status_code == 200, r.text
    plan = r.json()
    assert plan["authored_by"] == "adk:plan_agent"
    # The personalization seam call carries the tighter round-8 budget.
    assert recorder.calls[0][2].get("timeout") == 25.0

    r = client.get("/api/college/plans/current", headers=ALICE)
    assert r.status_code == 200, r.text
    assert r.json()["authored_by"] == "adk:plan_agent"


# ---------------------------------------------------------------------------
# Store whitelists + strict fake (the safety net)
# ---------------------------------------------------------------------------

def test_store_whitelist_drops_unknown_keys(fake_backend):
    store = CollegeStore()
    asyncio.run(store.save_college_assessment(ALICE_UID, {
        "assessment_id": "assess_r8_whitelist",
        "plan_id": None, "phase_id": None, "subject_id": None,
        "title": "Whitelist probe", "questions": [],
        "status": "DRAFT", "assessment_kind": "DIAGNOSTIC",
        "authored_by": "rag_fallback",
        "model_only_field_from_the_future": "must be dropped",
    }))
    rows = fake_backend.client._tables["assessments"]._rows
    stored = [r for r in rows
              if r["assessment_id"] == "assess_r8_whitelist"]
    assert stored, "assessment row was not stored"
    assert "model_only_field_from_the_future" not in stored[0]
    assert stored[0]["authored_by"] == "rag_fallback"

    asyncio.run(store.save_college_assessment_result(ALICE_UID, {
        "result_id": "result_r8_whitelist",
        "assessment_id": "assess_r8_whitelist",
        "score": 0.0, "normalized_score": 0.0,
        "mastery_status": "REINFORCEMENT_REQUIRED",
        "topic_results": [], "feedback": "",
        "evaluation_confidence": "low",
        "another_future_field": 123,
    }))
    rows = fake_backend.client._tables["assessment_results"]._rows
    stored = [r for r in rows if r["result_id"] == "result_r8_whitelist"]
    assert stored and "another_future_field" not in stored[0]


def test_strict_fake_rejects_unknown_columns(fake_backend):
    fake = fake_backend.client
    with pytest.raises(ValueError):
        fake.table("assessments").upsert(
            {"assessment_id": "assess_r8_bad", "not_a_column": 1},
            on_conflict="assessment_id").execute()
    # A clean row still writes fine.
    resp = fake.table("assessments").upsert(
        {"assessment_id": "assess_r8_good", "user_id": ALICE_UID,
         "title": "ok", "questions": [], "status": "DRAFT",
         "assessment_kind": "DIAGNOSTIC", "authored_by": "rag_fallback"},
        on_conflict="assessment_id").execute()
    assert resp.data and resp.data[0]["assessment_id"] == "assess_r8_good"


# ---------------------------------------------------------------------------
# Gemini fast config: construction, passthrough, agent wiring
# ---------------------------------------------------------------------------

def test_fast_generation_config_shape():
    cfg = fast_generation_config(1234)
    assert cfg is not None
    assert cfg.max_output_tokens == 1234
    assert cfg.thinking_config.thinking_budget == 0


class _ConfigModel:
    def __init__(self):
        self.seen = []

    def generate_content(self, prompt, config=None):
        self.seen.append(config)

        class R:
            text = "ok"
        return R()


class _PlainModel:
    def generate_content(self, prompt):
        class R:
            text = "plain"
        return R()


def test_generate_fast_passes_config_and_falls_back():
    model = _ConfigModel()
    assert generate_fast(model, "p", 777).text == "ok"
    assert model.seen[0].max_output_tokens == 777
    # A model that cannot accept a config still gets its call.
    assert generate_fast(_PlainModel(), "p").text == "plain"


def test_generation_agents_carry_fast_config():
    from backend.agents.college_adk_agents import build_generation_agent
    for key in ("assessment", "plan"):
        agent = build_generation_agent(key)
        cfg = agent.generate_content_config
        assert cfg is not None, key
        assert cfg.max_output_tokens == 2048
        assert cfg.thinking_config.thinking_budget == 0


# ---------------------------------------------------------------------------
# Diagnostic chain budget: the direct leg is skipped when the ADK
# attempt already spent the request budget
# ---------------------------------------------------------------------------

class _RecordingModel:
    def __init__(self):
        self.calls = []

    def generate_content(self, prompt, config=None):
        self.calls.append(prompt)

        class R:
            text = _DIAG_PAYLOAD
        return R()


class _ClockShim:
    """Stand-in for the assessment service's `time` module reference:
    only monotonic() is faked; everything else delegates."""

    def __init__(self, readings):
        self._readings = list(readings)

    def monotonic(self):
        if len(self._readings) > 1:
            return self._readings.pop(0)
        return self._readings[0]

    def __getattr__(self, name):
        return getattr(time_mod, name)


def test_diagnostic_direct_leg_used_when_budget_remains(monkeypatch):
    _setup_alice()
    model = _RecordingModel()
    monkeypatch.setattr(assessment_mod, "run_agent_generation", _adk_down)
    monkeypatch.setattr(gemini_mod, "get_gemini_model", lambda: model)

    r = client.post("/api/college/assessments/diagnostic", json={},
                    headers=ALICE)
    assert r.status_code == 200, r.text
    assert r.json()["authored_by"] == "gemini_direct"
    assert len(model.calls) == 1


def test_diagnostic_direct_leg_skipped_when_budget_spent(monkeypatch):
    _setup_alice()
    model = _RecordingModel()
    monkeypatch.setattr(assessment_mod, "run_agent_generation", _adk_down)
    monkeypatch.setattr(gemini_mod, "get_gemini_model", lambda: model)
    # Chain clock: starts at 1000.0, reads 1031.0 at the gate — the ADK
    # attempt "spent" 31s, so the direct leg must be skipped and the
    # grounded fallback must answer instead of dying at the platform cap.
    monkeypatch.setattr(assessment_mod, "time",
                        _ClockShim([1000.0, 1031.0]))

    r = client.post("/api/college/assessments/diagnostic", json={},
                    headers=ALICE)
    assert r.status_code == 200, r.text
    assert r.json()["authored_by"] == "rag_fallback"
    assert model.calls == []
