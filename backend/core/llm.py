"""
Shared LLM accessor for the PathMind College MVP — Groq provider.

AJ's decision (2026-10-01): Groq is the ONLY active LLM provider for
the college MVP. Gemini's free-tier daily cap kept exhausting under
pilot testing and blocking every AI feature; Groq's free tier is far
larger and, critically, its quotas are PER MODEL, so task classes get
separate pools (settings.GROQ_MODEL_*):

  purpose="mentor"     → ADK mentor hierarchy (many tool-calling turns)
  purpose="generation" → ADK one-shot authoring twins (diagnostic/plan)
  purpose="direct"     → direct one-shot legs (phase assessments,
                         plan enrich, diagnostic direct fallback,
                         legacy mentor fallback)
  purpose="light"      → short-answer grading

Groq serves an OpenAI-compatible chat-completions API, so both the
direct legs (via the generate_content-compatible wrapper below) and
the ADK agents (via backend.agents.college_groq_llm.GroqLlm) speak to
it with plain httpx — no new dependencies.

Returns None from get_gemini_model() when the key is missing; callers
must treat None as "AI unavailable" and degrade honestly (never
invent). The historical function name get_gemini_model is kept (and
re-exported through backend.core.gemini) because every college service
and test stub binds to it; the name is legacy, the provider is Groq.
"""

from __future__ import annotations

import os
from typing import Any, Dict, List, Optional

from backend.core.college_logging import log_event

GROQ_BASE_URL = "https://api.groq.com/openai/v1"

_PURPOSE_SETTING = {
    "mentor": "GROQ_MODEL_MENTOR",
    "generation": "GROQ_MODEL_GENERATION",
    "direct": "GROQ_MODEL_DIRECT",
    "light": "GROQ_MODEL_LIGHT",
}


def model_id_for_purpose(purpose: str = "direct") -> str:
    """Resolve a task purpose to its configured Groq model id."""
    from backend.core.config import settings
    attr = _PURPOSE_SETTING.get(purpose, "GROQ_MODEL_DIRECT")
    return str(getattr(settings, attr))


def _groq_api_key() -> str:
    from backend.core.config import settings
    return settings.GROQ_API_KEY or os.environ.get("GROQ_API_KEY", "")


def classify_llm_error(exc: BaseException) -> str:
    """
    Map an LLM provider exception to a safe, user-presentable error
    class: LLM_QUOTA, LLM_AUTH, LLM_MODEL_NOT_FOUND or LLM_UNAVAILABLE
    — never the exception message (which may echo request details).
    Callers use the class to fail fast (retrying an exhausted quota or
    a rejected key only burns time) and to tell the learner the truth
    about why AI is unavailable.
    """
    code = getattr(exc, "code", None) or getattr(exc, "status_code", None)
    text = f"{type(exc).__name__} {exc}".upper()
    if (code == 429 or "RESOURCE_EXHAUSTED" in text or "QUOTA" in text
            or "RATE_LIMIT" in text or "RATE LIMIT" in text
            or " 429" in text or "TOO MANY REQUESTS" in text):
        return "LLM_QUOTA"
    if (code in (401, 403) or "API_KEY_INVALID" in text
            or "API KEY NOT VALID" in text or "PERMISSION_DENIED" in text
            or "UNAUTHENTICATED" in text):
        return "LLM_AUTH"
    if code == 404 or "NOT_FOUND" in text or "IS NOT FOUND" in text:
        return "LLM_MODEL_NOT_FOUND"
    return "LLM_UNAVAILABLE"


class LLMServiceError(Exception):
    """An LLM call failed in a classified way; carries the safe error code."""

    def __init__(self, error_code: str, cause: BaseException):
        super().__init__(f"{error_code} ({type(cause).__name__})")
        self.error_code = error_code
        self.cause = cause


class LLMProviderError(Exception):
    """
    One Groq HTTP call failed. Carries the HTTP status (when the
    provider answered at all) so classify_llm_error can map it to the
    safe taxonomy; the message is a bounded provider snippet, safe for
    operator logs (error_detail surfaces show type + this text).
    """

    def __init__(self, status_code: Optional[int], message: str):
        super().__init__(message)
        self.status_code = status_code
        self.provider = "groq"


def groq_chat(model_id: str,
              messages: List[Dict[str, Any]],
              *,
              max_tokens: Optional[int] = None,
              temperature: float = 0.3,
              tools: Optional[List[Dict[str, Any]]] = None,
              reasoning_effort: Optional[str] = None,
              timeout: float = 30.0) -> Dict[str, Any]:
    """
    One bounded Groq chat-completions call. Single attempt, `timeout`
    seconds — retries and fallbacks live with the callers (the
    diagnostic chain ADK → direct → grounded RAG; the orchestrator's
    class-aware loop), which keeps every multi-call flow's worst case
    inside the 60s serverless window. Raises LLMProviderError on any
    failure; returns the parsed response JSON on success.
    """
    import httpx

    key = _groq_api_key()
    if not key:
        raise LLMProviderError(None, "GROQ_API_KEY is not configured")
    payload: Dict[str, Any] = {
        "model": model_id,
        "messages": messages,
        "temperature": temperature,
    }
    if max_tokens:
        payload["max_tokens"] = int(max_tokens)
    if tools:
        payload["tools"] = tools
    # gpt-oss models are reasoning models: their reasoning shares the
    # completion budget, and at the default effort it starved large
    # structured outputs (the phase-activities JSON was truncated
    # mid-string live even under a 4096 cap). Structured one-shot
    # callers pass "low" — enough reasoning to follow the schema, far
    # less budget burned before the actual content.
    if reasoning_effort and model_id.startswith("openai/gpt-oss"):
        payload["reasoning_effort"] = reasoning_effort
    try:
        with httpx.Client(timeout=timeout) as client:
            resp = client.post(
                f"{GROQ_BASE_URL}/chat/completions",
                headers={"Authorization": f"Bearer {key}",
                         "Content-Type": "application/json"},
                json=payload,
            )
    except Exception as exc:  # transport failure — no status at all
        raise LLMProviderError(
            None, f"Groq transport error ({type(exc).__name__})") from exc
    if resp.status_code >= 400:
        detail = ""
        try:
            detail = str((resp.json().get("error") or {}).get("message")
                         or "")[:200]
        except Exception:
            detail = resp.text[:200]
        raise LLMProviderError(
            resp.status_code,
            f"Groq HTTP {resp.status_code}: {detail}".strip())
    try:
        return resp.json()
    except Exception as exc:
        raise LLMProviderError(
            None, "Groq returned an unparsable response") from exc


def fast_generation_config(max_output_tokens: int = 2048):
    """
    Bounded generation config for ONE-SHOT authoring calls (diagnostics,
    plan activities, phase assessments, grading): thinking disabled and
    the output capped.

    Why: live probing on 2026-10-01 showed default-config generations
    taking ~30s+ each, which starved every chained flow inside the 60s
    serverless window. These prompts are bounded authoring tasks with
    strict output schemas; they do not need open-ended reasoning.

    The returned genai config object serves two consumers now: the ADK
    agents carry it (college_groq_llm reads its max_output_tokens) and
    generate_fast extracts the cap for direct Groq calls. Returns None
    when the SDK types cannot be built — callers then call without a
    config, exactly as before (never break a call over this).
    """
    try:
        from google.genai import types as genai_types
        return genai_types.GenerateContentConfig(
            max_output_tokens=max_output_tokens,
            thinking_config=genai_types.ThinkingConfig(thinking_budget=0),
        )
    except Exception:
        return None


def generate_fast(model, prompt: str, max_output_tokens: int = 2048):
    """
    One-shot generation through the shared model wrapper with the fast
    config applied (output capped). Falls back to a plain call when the
    model object does not accept a config (test doubles) — the config
    is an optimization, never a reason to fail a call that would
    otherwise work.
    """
    config = fast_generation_config(max_output_tokens)
    if config is None:
        return model.generate_content(prompt)
    try:
        return model.generate_content(prompt, config=config)
    except TypeError:
        return model.generate_content(prompt)


class _TextResponse:
    """Minimal response wrapper: a safe `.text`, like callers expect."""

    def __init__(self, text: str):
        self.text = text


class _GroqModelWrapper:
    """
    Gives a Groq model id the legacy `generate_content(prompt)` shape
    the college services were written against, so every direct leg
    (diagnostic fallback, phase assessments, enrich, grading, legacy
    mentor) runs on Groq unchanged.
    """

    def __init__(self, model_id: str):
        self._model_id = model_id

    def generate_content(self, prompt: str, config=None):
        max_tokens = getattr(config, "max_output_tokens", None)
        data = groq_chat(
            self._model_id,
            [{"role": "user", "content": prompt}],
            max_tokens=max_tokens,
            temperature=0.3,
            reasoning_effort="low",
        )
        text = ""
        try:
            text = (data.get("choices") or [{}])[0] \
                .get("message", {}).get("content") or ""
        except Exception:
            text = ""
        return _TextResponse(text if isinstance(text, str) else "")


def get_gemini_model(purpose: str = "direct") -> Optional[object]:
    """
    Shared model accessor (legacy name — the provider is Groq; see the
    module docstring). Returns a generate_content-compatible wrapper
    for the purpose's Groq model pool, or None when no Groq key is
    configured (callers degrade honestly).
    """
    if not _groq_api_key():
        log_event("college.llm.unavailable",
                  outcome="error", error_code="missing_api_key")
        return None
    return _GroqModelWrapper(model_id_for_purpose(purpose))


__all__ = [
    "GROQ_BASE_URL", "LLMProviderError", "LLMServiceError",
    "classify_llm_error", "fast_generation_config", "generate_fast",
    "get_gemini_model", "groq_chat", "model_id_for_purpose",
]
