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
    # Optional fallback model id. Each model carries its own free-tier quota,
    # so setting this (Vercel dashboard, no code deploy) multiplies effective
    # AI capacity: generate_text_resilient() tries the primary first, then
    # this one when the primary's quota is exhausted. Empty = disabled.
    GEMINI_FALLBACK_MODEL: str = Field(default="", validation_alias="GEMINI_FALLBACK_MODEL")
    
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
