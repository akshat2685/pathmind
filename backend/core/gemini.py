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


class _GenaiModelWrapper:
    """
    Wraps the new google.genai Client to provide the legacy
    `generate_content(prompt)` interface expected by callers.
    """
    def __init__(self, client, model_id: str):
        self._client = client
        self._model_id = model_id

    def generate_content(self, prompt: str):
        return self._client.models.generate_content(
            model=self._model_id,
            contents=prompt,
        )


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
