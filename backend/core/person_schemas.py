from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from datetime import datetime, timezone

class PersonProfile(BaseModel):
    person_id: str
    learner_stage: str  # e.g., "School Student", "College Student", "Graduate", "Working Professional", "Career Switcher", "Independent", "Other"
    aspiration: str
    domain: Optional[str] = "General"
    evidence_summary: Optional[str] = None
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

class LearnerBaseline(BaseModel):
    person_id: str
    assessment_id: str
    blueprint_id: str
    demonstrated_capabilities: List[str] = Field(default_factory=list)
    weak_areas: List[str] = Field(default_factory=list)
    unknown_areas: List[str] = Field(default_factory=list)
    confidence: str = "MEDIUM" # HIGH, MEDIUM, LOW
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
