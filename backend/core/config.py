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
    GEMINI_MODEL: str = Field(default="gemini-2.0-flash", validation_alias="GEMINI_MODEL")
    GEMINI_FALLBACK_MODEL: str = Field(default="", validation_alias="GEMINI_FALLBACK_MODEL")
    
    # ESCO Configuration
    ESCO_API_URL: str = "https://ec.europa.eu/esco/api"
    
    # Firebase / Firestore config
    GOOGLE_APPLICATION_CREDENTIALS: str | None = None
    FIRESTORE_PROJECT_ID: str | None = None

    # Supabase config (shared project with College MVP; auth verification
    # only — does not touch college tables)
    SUPABASE_URL: str | None = None
    SUPABASE_SECRET_KEY: str | None = None

    model_config = ConfigDict(env_file=_ENV_FILES, extra="ignore")

settings = Settings()
