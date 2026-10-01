import os
from pydantic import Field, ConfigDict
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    PROJECT_NAME: str = "PATHMIND MVP API"
    GEMINI_API_KEY: str = Field(default="", validation_alias="GEMINI_API_KEY")
    # Gemini model id. Centralized here (env-overridable) so a model
    # retirement is a dashboard change, not a code deploy.
    # gemini-2.5-flash was retired by Google (returns HTTP 404 for newer
    # API keys); gemini-3.5-flash is the current stable replacement.
    GEMINI_MODEL: str = Field(default="gemini-3.5-flash", validation_alias="GEMINI_MODEL")

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
    GROQ_MODEL_GENERATION: str = Field(default="llama-3.3-70b-versatile", validation_alias="GROQ_MODEL_GENERATION")
    # Direct one-shot legs (phase assessments, plan enrich, fallbacks).
    GROQ_MODEL_DIRECT: str = Field(default="openai/gpt-oss-20b", validation_alias="GROQ_MODEL_DIRECT")
    # Light work (short-answer grading).
    GROQ_MODEL_LIGHT: str = Field(default="llama-3.1-8b-instant", validation_alias="GROQ_MODEL_LIGHT")
    
    # ESCO Configuration
    ESCO_API_URL: str = "https://ec.europa.eu/esco/api"
    
    # Firebase / Firestore config
    GOOGLE_APPLICATION_CREDENTIALS: str | None = None
    FIRESTORE_PROJECT_ID: str | None = None

    # CORS Configuration
    FRONTEND_ORIGIN: str = Field(default="http://localhost:3000", validation_alias="FRONTEND_ORIGIN")

    # Supabase Configuration
    SUPABASE_URL: str = Field(default="", validation_alias="SUPABASE_URL")
    SUPABASE_SECRET_KEY: str = Field(default="", validation_alias="SUPABASE_SECRET_KEY")

    model_config = ConfigDict(env_file=".env", extra="ignore")

settings = Settings()
