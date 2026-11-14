"""
Regression tests for the college AI mentor failure mode found live on
2026-09-30: when the Gemini call failed in production, the orchestrator's
error handler itself crashed (``log_event`` was used without being
imported), so a designed honest degradation collapsed into the ADK
runtime's opaque last-resort message and the mentor looked dead.

These tests pin the contract instead:
- a failing LLM produces the honest ERROR shape (never an exception),
- the failure is classified (LLM_QUOTA / LLM_AUTH / LLM_MODEL_NOT_FOUND /
  LLM_UNAVAILABLE / LLM_NOT_CONFIGURED) and surfaced as ``error_code``,
- quota/auth/model failures fail fast (one call, no retry burn),
- transient failures still retry before degrading,
- a working model yields the LEARNING shape.
"""

import asyncio

import pytest

from college_testkit import install_fake_adapter

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
    """Counts calls; raises `error` or returns `text` like a Gemini model."""

    def __init__(self, error=None, text=""):
        self.error = error
        self.text = text
        self.calls = 0

    def generate_content(self, prompt):
        self.calls += 1
        if self.error is not None:
            raise self.error
        return type("R", (), {"text": self.text})()


def _run_interact(monkeypatch, model):
    import backend.core.gemini as gemini_mod
    monkeypatch.setattr(gemini_mod, "get_gemini_model", lambda: model)
    from backend.services.college_orchestrator import CollegeOrchestrator
    from backend.services.store import FirestoreStore
    orch = CollegeOrchestrator(FirestoreStore())
    return asyncio.run(
        orch.interact(ALICE_UID, "How should I start learning?",
                      session_id="sess_test"))


class _HttpError(Exception):
    def __init__(self, code, text):
        super().__init__(text)
        self.code = code


def test_quota_failure_degrades_honestly_and_fails_fast(monkeypatch):
    model = _StubModel(error=_HttpError(
        429, "429 RESOURCE_EXHAUSTED: You exceeded your current quota"))
    out = _run_interact(monkeypatch, model)
    assert out["state"] == "ERROR"
    assert out["error_code"] == "LLM_QUOTA"
    assert "usage limit" in out["message"]
    assert "study plan, assessments and PYQs below are unaffected" \
        in out["message"]
    assert [b["type"] for b in out["ui_blocks"]] == ["NEXT_ACTION"]
    assert model.calls == 1  # no retry burn on an exhausted quota


def test_auth_failure_fails_fast(monkeypatch):
    model = _StubModel(error=_HttpError(
        400, "API_KEY_INVALID: API key not valid. Please pass a valid API key."))
    out = _run_interact(monkeypatch, model)
    assert out["state"] == "ERROR"
    assert out["error_code"] == "LLM_AUTH"
    assert model.calls == 1


def test_missing_model_fails_fast(monkeypatch):
    model = _StubModel(error=_HttpError(
        404, "models/retired-model is not found for API version v1beta"))
    out = _run_interact(monkeypatch, model)
    assert out["state"] == "ERROR"
    assert out["error_code"] == "LLM_MODEL_NOT_FOUND"
    assert model.calls == 1


def test_transient_failure_retries_then_degrades(monkeypatch):
    async def _no_sleep(_seconds):
        return None
    import backend.services.college_orchestrator as orch_mod
    monkeypatch.setattr(orch_mod.asyncio, "sleep", _no_sleep)
    model = _StubModel(error=ConnectionError("503 backend unavailable"))
    out = _run_interact(monkeypatch, model)
    assert out["state"] == "ERROR"
    assert out["error_code"] == "LLM_UNAVAILABLE"
    assert model.calls == 3  # transient failures still get their retries


def test_no_key_configured_reports_not_configured(monkeypatch):
    import backend.core.config as config_mod
    monkeypatch.setattr(config_mod.settings, "GEMINI_API_KEY", "",
                        raising=False)
    import backend.core.gemini as gemini_mod

    def _must_not_be_called():
        raise AssertionError("model must not be consulted without a key")
    monkeypatch.setattr(gemini_mod, "get_gemini_model", _must_not_be_called)
    from backend.services.college_orchestrator import CollegeOrchestrator
    from backend.services.store import FirestoreStore
    out = asyncio.run(CollegeOrchestrator(FirestoreStore()).interact(
        ALICE_UID, "How should I start learning?", session_id="sess_test"))
    assert out["state"] == "ERROR"
    assert out["error_code"] == "LLM_NOT_CONFIGURED"


def test_working_model_returns_learning_shape(monkeypatch):
    model = _StubModel(text="Start with Unit 1 definitions today.")
    out = _run_interact(monkeypatch, model)
    assert out["state"] == "LEARNING"
    assert out["message"] == "Start with Unit 1 definitions today."
    assert model.calls == 1


def test_runtime_returns_orchestrator_shape_not_last_resort(monkeypatch):
    """The ADK runtime must pass the legacy honest shape through, not
    replace it with its own bare last-resort (ui_blocks: [])."""
    import backend.core.gemini as gemini_mod
    model = _StubModel(error=_HttpError(429, "RESOURCE_EXHAUSTED"))
    monkeypatch.setattr(gemini_mod, "get_gemini_model", lambda: model)
    from backend.services.college_adk_runtime import run_agent_interact
    from backend.services.college_store import college_store
    out = asyncio.run(run_agent_interact(
        ALICE_UID, "How should I start learning?", store=college_store))
    assert out["state"] == "ERROR"
    assert out["error_code"] == "LLM_QUOTA"
    assert out["ui_blocks"], "last-resort shape has empty ui_blocks"
    assert "PYQs below are unaffected" in out["message"]


def test_classify_llm_error_units():
    from backend.core.gemini import classify_llm_error
    assert classify_llm_error(_HttpError(429, "slow down")) == "LLM_QUOTA"
    assert classify_llm_error(Exception("RESOURCE_EXHAUSTED")) == "LLM_QUOTA"
    assert classify_llm_error(
        _HttpError(400, "API_KEY_INVALID")) == "LLM_AUTH"
    assert classify_llm_error(_HttpError(403, "forbidden")) == "LLM_AUTH"
    assert classify_llm_error(
        _HttpError(404, "model is not found")) == "LLM_MODEL_NOT_FOUND"
    assert classify_llm_error(ConnectionError("boom")) == "LLM_UNAVAILABLE"
