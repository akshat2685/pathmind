"""
College round-10 regression test (final pass, 2026-10-01).

Root cause found live via the round-9 error_detail surface: the mentor
prompt builder referenced ctx.university_name and ctx.branch.value,
which do not exist on the college AcademicContext (university_id is
the field; the branch lives on the profile as supported_path). Every
mentor call for a learner WITH a saved academic context crashed with
AttributeError before any LLM call and was misclassified as
LLM_UNAVAILABLE — the mentor looked like an AI outage while never
reaching the AI. The existing mentor tests never seeded a context, so
ctx was None and the broken attributes were never evaluated.

This test seeds a real context (profile + academic-context via the
API), then drives CollegeOrchestrator.interact with a stub model:
the reply must come back as a LEARNING shape, and the prompt the
model received must carry the learner's real university + branch.
"""
import asyncio

import pytest
from fastapi.testclient import TestClient

import backend.main as main_mod
import backend.core.gemini as gemini_mod
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


class _StubModel:
    def __init__(self, text="Focus on MQTT first: it is the lighter "
                             "protocol and shows up in most IoT exams."):
        self.text = text
        self.prompts = []

    def generate_content(self, prompt):
        self.prompts.append(prompt)
        return type("R", (), {"text": self.text})()


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


def test_mentor_reply_with_saved_context(monkeypatch):
    _setup_alice()
    model = _StubModel()
    monkeypatch.setattr(gemini_mod, "get_gemini_model", lambda: model)
    from backend.services.college_orchestrator import CollegeOrchestrator
    from backend.services.store import FirestoreStore
    orch = CollegeOrchestrator(FirestoreStore())
    out = asyncio.run(orch.interact(
        ALICE_UID, "Should I focus on MQTT or CoAP first?",
        session_id="sess_round10"))
    assert out["state"] != "ERROR", out
    assert "MQTT" in out["message"]
    assert model.prompts, "the model was never called"
    prompt = model.prompts[0]
    # The prompt is built from fields that actually exist on the
    # college models: university_id + the profile's branch.
    assert "univ_aicte_model" in prompt
    assert "Computer Science Engineer" in prompt
