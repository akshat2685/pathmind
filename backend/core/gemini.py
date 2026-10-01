"""
Compatibility shim — the LLM provider layer lives in backend.core.llm.

The college MVP's only active LLM provider is Groq (AJ's decision,
2026-10-01). This module keeps the historical import path working:
every college service and test stub binds to
`backend.core.gemini.get_gemini_model`, so those names are re-exported
here unchanged. New code should import from backend.core.llm.
"""

from backend.core.llm import (  # noqa: F401
    GROQ_BASE_URL,
    LLMProviderError,
    LLMServiceError,
    classify_llm_error,
    fast_generation_config,
    generate_fast,
    get_gemini_model,
    groq_chat,
    model_id_for_purpose,
)

__all__ = [
    "GROQ_BASE_URL", "LLMProviderError", "LLMServiceError",
    "classify_llm_error", "fast_generation_config", "generate_fast",
    "get_gemini_model", "groq_chat", "model_id_for_purpose",
]
