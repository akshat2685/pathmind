"""
Shared Gemini model accessor for the PathMind College MVP.

Every college service gets its model from here — never a hardcoded model
id. The model id lives in settings.GEMINI_MODEL (env GEMINI_MODEL), so a
Google model retirement is a Vercel dashboard change, not a code deploy.

`generate_text_resilient()` is the only call path student-facing features
should use. It absorbs the free tier's per-minute throttling transparently
(retry with backoff + jitter), fails fast and honestly on daily quota
exhaustion (retrying that is pointless), and optionally falls over to
GEMINI_FALLBACK_MODEL — each model carries its own free quota, so a
fallback configured in the Vercel dashboard multiplies effective capacity
with zero code changes.

Returns None when the key is missing or the client cannot be built; callers
must treat None as "AI unavailable" and degrade honestly (never invent).
"""

import random
import time
from typing import List, Optional

from backend.core.college_logging import log_event


class GeminiUnavailable(Exception):
    """Gemini could not serve this request after retries/fallback.

    Callers must degrade honestly (never invent a reply). `quota_scope` is
    "minute" (transient — a retry moments later will likely succeed),
    "day" (daily budget spent — further calls today are pointless), or None
    (not a quota problem: bad key, retired model, network, ...).
    """

    def __init__(self, message: str, *, quota_scope: Optional[str] = None):
        super().__init__(message)
        self.quota_scope = quota_scope


def get_gemini_model() -> Optional[object]:
    from backend.core.config import settings
    if not settings.GEMINI_API_KEY:
        return None
    try:
        import google.generativeai as genai
        genai.configure(api_key=settings.GEMINI_API_KEY)
        return genai.GenerativeModel(settings.GEMINI_MODEL)
    except Exception as exc:
        log_event("college.llm.unavailable",
                  outcome="error", error_code=type(exc).__name__)
        return None


def _build_model(model_id: str) -> Optional[object]:
    from backend.core.config import settings
    if not settings.GEMINI_API_KEY:
        return None
    try:
        import google.generativeai as genai
        genai.configure(api_key=settings.GEMINI_API_KEY)
        return genai.GenerativeModel(model_id)
    except Exception as exc:
        log_event("college.llm.unavailable",
                  outcome="error", error_code=type(exc).__name__)
        return None


def _model_chain() -> List[str]:
    """Primary model first, then the optional fallback (deduped, non-empty)."""
    from backend.core.config import settings
    chain = [settings.GEMINI_MODEL.strip()]
    fallback = (settings.GEMINI_FALLBACK_MODEL or "").strip()
    if fallback and fallback not in chain:
        chain.append(fallback)
    return [m for m in chain if m]


def _quota_scope(exc: BaseException) -> Optional[str]:
    """Classify a provider failure.

    Returns "day" for daily-budget exhaustion (never worth retrying today),
    "minute" for per-minute/throughput throttling and transient 503s (worth
    a short backoff), or None when it is not a quota problem at all.
    """
    text = f"{type(exc).__name__}: {exc}".lower()
    quota_markers = ("429", "resource_exhausted", "rate limit", "ratelimit",
                     "quota", "quota_exceeded", "503", "overloaded",
                     "service unavailable", "temporarily unavailable")
    if not any(m in text for m in quota_markers):
        return None
    day_markers = ("per day", "per-day", "daily", "day quota", "rpd",
                   "daily quota", "quota per day")
    if any(m in text for m in day_markers):
        return "day"
    return "minute"


def generate_text_resilient(
    prompt: str,
    *,
    feature: str,
    max_attempts_per_model: int = 3,
    base_delay_seconds: float = 2.0,
) -> str:
    """Generate text via Gemini, absorbing transient throttling.

    - Retries per-minute 429s / transient 503s with exponential backoff +
      jitter (bounded: worst added latency is ~base*(2^attempts) seconds).
    - Fails fast on daily quota exhaustion — no pointless waiting.
    - Falls over to GEMINI_FALLBACK_MODEL when the primary is exhausted.
    - Raises GeminiUnavailable on any terminal failure; never returns
      fabricated text.

    Blocking (generate_content is sync): callers on the event loop must run
    this in a thread via asyncio.to_thread, as they already do today.
    """
    chain = _model_chain()
    if not chain:
        raise GeminiUnavailable("no Gemini model configured", quota_scope=None)

    last_exc: Optional[BaseException] = None
    for model_id in chain:
        model = _build_model(model_id)
        if model is None:
            last_exc = RuntimeError(f"could not build model {model_id}")
            continue
        for attempt in range(max_attempts_per_model):
            try:
                resp = model.generate_content(prompt)
                text = (getattr(resp, "text", None) or "").strip()
                if not text:
                    raise RuntimeError("LLM returned an empty response")
                if model_id != chain[0]:
                    log_event("college.llm.fallback_used", feature=feature,
                              outcome="ok", error_code=model_id)
                return text
            except Exception as exc:
                last_exc = exc
                scope = _quota_scope(exc)
                log_event(
                    f"college.llm.{feature}.attempt_failed",
                    outcome="error",
                    error_code=f"{type(exc).__name__}:{scope or 'non_quota'}",
                )
                if scope == "day":
                    # Daily budget spent: further attempts on THIS model
                    # today are pointless. Move to the fallback model.
                    break
                if scope is None:
                    # Not a quota problem (bad key, retired model id,
                    # network). Retrying the same call will not help.
                    raise GeminiUnavailable(str(exc), quota_scope=None) from exc
                if attempt < max_attempts_per_model - 1:
                    delay = base_delay_seconds * (2 ** attempt)
                    delay = delay * (0.7 + 0.6 * random.random())  # jitter
                    time.sleep(delay)
                # else: attempts exhausted for this model -> try fallback

    scope = _quota_scope(last_exc) if last_exc else None
    raise GeminiUnavailable(
        f"Gemini unavailable after retries ({type(last_exc).__name__ if last_exc else 'no model'}: "
        f"{str(last_exc)[:200] if last_exc else ''})",
        quota_scope=scope,
    ) from last_exc
