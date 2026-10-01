"""
College round-9 tests (final pass, 2026-10-01):

- Error observability: every AI failure path used to collapse into one
  opaque code (LLM_UNAVAILABLE / AI_UNAVAILABLE / "no final text"),
  while the real provider error sat in unreachable server logs. ADK
  delivers model failures as error EVENTS, not exceptions — the runtime
  now extracts that detail into the raised error, the mentor ERROR
  shape carries a bounded `error_detail` (plus `adk_error_detail` when
  the ADK attempt also failed), and the enrich 503 names the last
  generation error. Provider messages are truncated; no secrets are
  ever included (provider errors do not carry the API key).
- Output caps: the diagnostic authoring legs (ADK twin + direct) get
  4096 tokens so a 5-6 question JSON set cannot truncate mid-object;
  the plan twin gets 3072.
"""
import pytest

import backend.services.college_adk_runtime as runtime_mod
import backend.services.college_orchestrator as orchestrator_mod
from backend.agents.college_adk_agents import build_generation_agent
from backend.core.gemini import LLMServiceError
from backend.services.college_assessment_service import (
    CollegeAssessmentService,
)


class _Event:
    def __init__(self, error_code=None, error_message=None):
        self.error_code = error_code
        self.error_message = error_message


def test_event_error_detail_extracts_first_error():
    events = [_Event(), _Event("429", "Quota exceeded for this key"),
              _Event("500", "later error")]
    detail = runtime_mod._event_error_detail(events)
    assert detail.startswith("429: Quota exceeded")


def test_event_error_detail_empty_without_errors():
    assert runtime_mod._event_error_detail([_Event(), _Event()]) == ""
    assert runtime_mod._event_error_detail([]) == ""


def test_event_error_detail_is_bounded():
    detail = runtime_mod._event_error_detail(
        [_Event("400", "x" * 500)])
    assert len(detail) <= 210


def test_error_detail_walks_llm_service_error_cause():
    cause = RuntimeError("404 model not found: gemini-x")
    err = LLMServiceError("LLM_MODEL_NOT_FOUND", cause)
    detail = orchestrator_mod._error_detail(err)
    assert "LLMServiceError" in detail
    assert "404 model not found" in detail


def test_error_detail_handles_plain_exception():
    detail = orchestrator_mod._error_detail(ValueError("boom"))
    assert detail == "ValueError: boom"


def test_generation_agent_caps_per_key():
    assessment = build_generation_agent("assessment")
    plan = build_generation_agent("plan")
    assert assessment.generate_content_config.max_output_tokens == 4096
    assert plan.generate_content_config.max_output_tokens == 3072


class _RecordingModel:
    def __init__(self):
        self.calls = []

    def generate_content(self, prompt, config=None):
        self.calls.append((prompt, config))

        class R:
            text = "[]"
        return R()


def test_diagnostic_direct_leg_uses_4096_cap():
    model = _RecordingModel()
    CollegeAssessmentService._generate_content_or_unavailable(
        model, "prompt", "DIAGNOSTIC", max_output_tokens=4096)
    assert len(model.calls) == 1
    cfg = model.calls[0][1]
    assert cfg is not None
    assert cfg.max_output_tokens == 4096


def test_generate_content_or_unavailable_wraps_errors():
    class _Boom:
        def generate_content(self, prompt, config=None):
            raise RuntimeError("provider exploded")

    with pytest.raises(ValueError) as excinfo:
        CollegeAssessmentService._generate_content_or_unavailable(
            _Boom(), "prompt", "DIAGNOSTIC")
    assert "DIAGNOSTIC_UNAVAILABLE" in str(excinfo.value)
    assert "RuntimeError" in str(excinfo.value)
