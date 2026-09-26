"""
Shared Gemini model accessor for the PATHMIND main product.

Every main-product service gets its model from here — never a hardcoded model
id. The model id lives in settings.GEMINI_MODEL (env GEMINI_MODEL), so a
Google model retirement is a dashboard env change, not a code deploy.

`generate_text_resilient()` is the only call path user-facing features should
use. It absorbs the free tier's per-minute throttling transparently (retry
with backoff + jitter), fails fast and honestly on daily quota exhaustion
(retrying that is pointless), and optionally falls over to
GEMINI_FALLBACK_MODEL — each model carries its own free quota, so a fallback
configured in the dashboard multiplies effective capacity with zero code
changes.

Raises GeminiUnavailable on terminal failure; callers must degrade honestly
(never invent a reply). `quota_scope` is "minute" (transient), "day" (daily
budget spent), or None (not a quota problem).
"""

import logging
import random
import time
from typing import List, Optional

logger = logging.getLogger(__name__)


class GeminiUnavailable(Exception):
    """Gemini could not serve this request after retries/fallback."""

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
        logger.warning("gemini.unavailable error=%s", type(exc).__name__)
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
        logger.warning("gemini.unavailable model=%s error=%s", model_id, type(exc).__name__)
        return None


def _model_chain() -> List[str]:
    """Primary model first, then the optional fallback (deduped, non-empty)."""
    from backend.core.config import settings
    chain = [(settings.GEMINI_MODEL or "").strip()]
    fallback = (settings.GEMINI_FALLBACK_MODEL or "").strip()
    if fallback and fallback not in chain:
        chain.append(fallback)
    return [m for m in chain if m]


def _quota_scope(exc: BaseException) -> Optional[str]:
    """Classify a provider failure as 'day', 'minute', or None (not quota)."""
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

    - Retries per-minute 429s / transient 503s with exponential backoff + jitter.
    - Fails fast on daily quota exhaustion.
    - Falls over to GEMINI_FALLBACK_MODEL when the primary is exhausted.
    - Raises GeminiUnavailable on terminal failure; never returns fabricated text.

    Blocking (generate_content is sync): callers on the event loop must run
    this in a thread via asyncio.to_thread.
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
                    logger.info("gemini.fallback_used feature=%s model=%s", feature, model_id)
                return text
            except Exception as exc:
                last_exc = exc
                scope = _quota_scope(exc)
                logger.warning(
                    "gemini.attempt_failed feature=%s error=%s scope=%s",
                    feature, type(exc).__name__, scope or "non_quota",
                )
                if scope == "day":
                    break  # daily budget spent on this model; try fallback
                if scope is None:
                    raise GeminiUnavailable(str(exc), quota_scope=None) from exc
                if attempt < max_attempts_per_model - 1:
                    delay = base_delay_seconds * (2 ** attempt)
                    delay = delay * (0.7 + 0.6 * random.random())
                    time.sleep(delay)

    scope = _quota_scope(last_exc) if last_exc else None
    raise GeminiUnavailable(
        f"Gemini unavailable after retries ({type(last_exc).__name__ if last_exc else 'no model'}: "
        f"{str(last_exc)[:200] if last_exc else ''})",
        quota_scope=scope,
    ) from last_exc
