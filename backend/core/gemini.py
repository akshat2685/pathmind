"""
Shared Gemini model accessor for the PathMind College MVP.

Every college service gets its model from here — never a hardcoded model
id. The model id lives in settings.GEMINI_MODEL (env GEMINI_MODEL), so a
Google model retirement is a Vercel dashboard change, not a code deploy.

Returns None when the key is missing or the client cannot be built; callers
must treat None as "AI unavailable" and degrade honestly (never invent).

Uses the new `google.genai` SDK (the old `google.generativeai` is deprecated
and does not support newer models like gemini-3.5-flash).
"""

from typing import Optional

from backend.core.college_logging import log_event


def classify_llm_error(exc: BaseException) -> str:
    """
    Map an LLM SDK exception to a safe, user-presentable error class.

    Returns a stable code — LLM_QUOTA, LLM_AUTH, LLM_MODEL_NOT_FOUND or
    LLM_UNAVAILABLE — never the exception message (which may echo request
    details). Callers use the class to fail fast (retrying an exhausted
    quota or a rejected key only burns time) and to tell the learner the
    truth about why AI is unavailable.
    """
    code = getattr(exc, "code", None) or getattr(exc, "status_code", None)
    text = f"{type(exc).__name__} {exc}".upper()
    if (code == 429 or "RESOURCE_EXHAUSTED" in text or "QUOTA" in text
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


class _GenaiResponseWrapper:
    """
    Wraps the new google.genai GenerateContentResponse to provide a safe
    `.text` attribute. The new SDK's `.text` property can raise if the
    response has no parts (e.g., blocked content); this wrapper guarantees
    `.text` always returns a string (possibly empty) and never raises.
    """
    def __init__(self, raw_response):
        self._raw = raw_response

    @property
    def text(self) -> str:
        try:
            t = self._raw.text
            return t if isinstance(t, str) else ""
        except Exception:
            # Fall back to manually concatenating parts
            try:
                parts = []
                for cand in (getattr(self._raw, "candidates", None) or []):
                    content = getattr(cand, "content", None)
                    for part in (getattr(content, "parts", None) or []):
                        pt = getattr(part, "text", None)
                        if isinstance(pt, str):
                            parts.append(pt)
                return "".join(parts)
            except Exception:
                return ""

    def __getattr__(self, name):
        # Delegate everything else to the raw response
        return getattr(self._raw, name)


class _GenaiModelWrapper:
    """
    Wraps the new google.genai Client to provide the legacy
    `generate_content(prompt)` interface expected by callers.
    """
    def __init__(self, client, model_id: str):
        self._client = client
        self._model_id = model_id

    def generate_content(self, prompt: str):
        raw = self._client.models.generate_content(
            model=self._model_id,
            contents=prompt,
        )
        return _GenaiResponseWrapper(raw)


def get_gemini_model() -> Optional[object]:
    from backend.core.config import settings
    if not settings.GEMINI_API_KEY:
        log_event("college.llm.unavailable",
                  outcome="error", error_code="missing_api_key")
        return None
    # Prefer the new google.genai SDK (supports gemini-3.5-flash and later)
    try:
        from google import genai as new_genai
        client = new_genai.Client(api_key=settings.GEMINI_API_KEY)
        return _GenaiModelWrapper(client, settings.GEMINI_MODEL)
    except Exception as exc:
        log_event("college.llm.new_sdk_failed",
                  outcome="error", error_code=type(exc).__name__)
    # Fallback to the legacy SDK for older environments
    try:
        import google.generativeai as genai
        genai.configure(api_key=settings.GEMINI_API_KEY)
        return genai.GenerativeModel(settings.GEMINI_MODEL)
    except Exception as exc:
        log_event("college.llm.unavailable",
                  outcome="error", error_code=type(exc).__name__)
        return None
