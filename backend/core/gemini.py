"""
Shared Gemini model accessor for the PathMind College MVP.

Every college service gets its model from here — never a hardcoded model
id. The model id lives in settings.GEMINI_MODEL (env GEMINI_MODEL), so a
Google model retirement is a Vercel dashboard change, not a code deploy.

Returns None when the key is missing or the client cannot be built; callers
must treat None as "AI unavailable" and degrade honestly (never invent).
"""

from typing import Optional

from backend.core.college_logging import log_event


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
