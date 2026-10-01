"""
College round-12 regression test (final pass, 2026-10-01).

Checkpoint (phase) assessments were the one generated artifact with no
provenance: generate_phase_assessment never set authored_by, so the
response and the DB row carried null even when Gemini demonstrably
authored the questions (verified live on the round-8 build: real
questions in 9s, authored_by null in the assessments table). AJ's
verifiability rule — never claim a component is in use without a
checkable label — applies to every generated artifact. The generator
now stamps "gemini_direct" when the model produced the questions and
"static_fallback" when it fell back.
"""
import json

import pytest
from fastapi.testclient import TestClient

import backend.main as main_mod
import backend.core.gemini as gemini_mod
from college_testkit import install_fake_adapter

client = TestClient(main_mod.app)

ALICE = {"Authorization": "Bearer alice-token", "Content-Type": "application/json"}

CHECKPOINT = [
    {"id": "x1", "text": "What does the perception layer do in IoT?",
     "type": "MCQ",
     "options": ["Aggregates sensor data", "Routes packets",
                 "Renders dashboards", "Stores archives"],
     "answer": "A", "topic": "IoT Basics", "marks": 5},
    {"id": "x2", "text": "Which protocol is publish/subscribe?",
     "type": "MCQ",
     "options": ["MQTT", "FTP", "SMTP", "SSH"],
     "answer": "A", "topic": "IoT Basics", "marks": 5},
    {"id": "x3", "text": "Explain why edge processing reduces latency.",
     "type": "SHORT_ANSWER", "topic": "IoT Basics", "marks": 10},
]


class _Resp:
    def __init__(self, text):
        self.text = text


class _CheckpointModel:
    def generate_content(self, prompt):
        return _Resp(json.dumps(CHECKPOINT))


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


def _generate():
    return client.post("/api/college/assessments/generate", json={
        "plan_id": "plan_test", "phase_id": "phase_test",
        "subject_id": "CS-301", "topic_title": "IoT Basics",
    }, headers=ALICE)


def test_checkpoint_stamps_gemini_direct(monkeypatch):
    _setup_alice()
    monkeypatch.setattr(gemini_mod, "get_gemini_model",
                        lambda: _CheckpointModel())
    r = _generate()
    assert r.status_code == 200, r.text
    assert r.json()["authored_by"] == "gemini_direct"


def test_checkpoint_stamps_static_fallback_without_model(monkeypatch):
    _setup_alice()
    monkeypatch.setattr(gemini_mod, "get_gemini_model", lambda: None)
    r = _generate()
    assert r.status_code == 200, r.text
    assert r.json()["authored_by"] == "static_fallback"
