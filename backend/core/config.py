import os
from pathlib import Path
from pydantic import Field, ConfigDict
from pydantic_settings import BaseSettings

_BACKEND_DIR = Path(__file__).resolve().parent.parent
_ENV_FILES = [
    str(_BACKEND_DIR / ".env"),
    str(_BACKEND_DIR.parent / ".env"),
    ".env",
]

class Settings(BaseSettings):
    PROJECT_NAME: str = "PATHMIND MVP API"
    GEMINI_API_KEY: str = Field(default="", validation_alias="GEMINI_API_KEY")
    # Model ids live in env so a Google model retirement is a dashboard
    # change, not a code deploy. Never hardcode a model id in services.
    # gemini-2.0-flash was retired by Google (404); gemini-3.5-flash is verified working.
    GEMINI_MODEL: str = Field(default="gemini-3.5-flash", validation_alias="GEMINI_MODEL")
    GEMINI_FALLBACK_MODEL: str = Field(default="", validation_alias="GEMINI_FALLBACK_MODEL")

    # Groq is the college MVP's ONLY active LLM provider (AJ's call,
    # 2026-10-01: Gemini's free-tier daily cap kept exhausting under
    # pilot testing). Groq's free quotas are PER MODEL, so each task
    # class gets its own pool — see backend/core/llm.py. Every id is
    # env-overridable so a Groq model retirement/rename is a Vercel
    # dashboard change, not a code deploy.
    GROQ_API_KEY: str = Field(default="", validation_alias="GROQ_API_KEY")
    # ADK mentor hierarchy (many tool-calling turns per conversation).
    GROQ_MODEL_MENTOR: str = Field(default="openai/gpt-oss-120b", validation_alias="GROQ_MODEL_MENTOR")
    # ADK one-shot authoring twins (diagnostic + plan generation).
    # gpt-oss-20b, NOT llama-3.3-70b-versatile: live A/B on 2026-10-01
    # showed the llama pool silently failing every ADK generation run
    # (both twins fell back) while gpt-oss-20b authored end-to-end
    # (provenance adk:assessment_agent / adk:plan_agent). Same model
    # as the direct pool — one authoring pool, honestly shared.
    GROQ_MODEL_GENERATION: str = Field(default="openai/gpt-oss-20b", validation_alias="GROQ_MODEL_GENERATION")
    # Direct one-shot legs (phase assessments, plan enrich, fallbacks).
    GROQ_MODEL_DIRECT: str = Field(default="openai/gpt-oss-20b", validation_alias="GROQ_MODEL_DIRECT")
    # Light work (short-answer grading).
    GROQ_MODEL_LIGHT: str = Field(default="llama-3.1-8b-instant", validation_alias="GROQ_MODEL_LIGHT")
    
    # ESCO Configuration
    ESCO_API_URL: str = "https://ec.europa.eu/esco/api"
    
    # Supabase config (shared project with College MVP; auth verification
    # only — does not touch college tables)
    SUPABASE_URL: str | None = None
    SUPABASE_SECRET_KEY: str | None = None


    # CORS Configuration
    FRONTEND_ORIGIN: str = Field(default="http://localhost:3000", validation_alias="FRONTEND_ORIGIN")
    model_config = ConfigDict(env_file=_ENV_FILES, extra="ignore")

settings = Settings()
