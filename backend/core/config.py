import os
from pydantic import Field, ConfigDict
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    PROJECT_NAME: str = "PATHMIND MVP API"
    GEMINI_API_KEY: str = Field(default="", validation_alias="GEMINI_API_KEY")
    
    # ESCO Configuration
    ESCO_API_URL: str = "https://ec.europa.eu/esco/api"
    
    # Firebase / Firestore config
    GOOGLE_APPLICATION_CREDENTIALS: str | None = None
    FIRESTORE_PROJECT_ID: str | None = None

    model_config = ConfigDict(env_file=".env", extra="ignore")

settings = Settings()
