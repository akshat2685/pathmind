from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field, ConfigDict
from datetime import datetime, timezone

class MarketSignal(BaseModel):
    id: str
    goal_id: Optional[str] = None
    occupation_id: Optional[str] = None
    domain: str
    field_name: str = Field(alias="field")
    geography: str
    signal_type: str  # e.g., employment, demand, wage, compensation, growth, openings, education, competition, participation, industry_trend
    metric: str
    value: Optional[str] = None
    unit: Optional[str] = None
    period: str
    source: str
    source_id: Optional[str] = None
    source_url: Optional[str] = None
    retrieved_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    source_version: Optional[str] = None
    confidence: str = "UNKNOWN"  # HIGH, MEDIUM, LOW, INSUFFICIENT_EVIDENCE
    freshness_status: str = "UNKNOWN"  # CURRENT, RECENT, AGING, STALE, UNKNOWN
    notes: Optional[str] = None
    model_config = ConfigDict(populate_by_name=True)
class TrajectoryStage(BaseModel):
    stage_name: str
    typical_entry_requirements: List[str] = Field(default_factory=list)
    common_next_steps: List[str] = Field(default_factory=list)
    alternative_transitions: List[str] = Field(default_factory=list)

class CareerTrajectory(BaseModel):
    goal_id: Optional[str] = None
    occupation: str
    domain: str
    stages: List[TrajectoryStage] = Field(default_factory=list)
    evidence: List[str] = Field(default_factory=list)
    source: str = "SOURCE_UNAVAILABLE"
    confidence: str = "INSUFFICIENT_EVIDENCE"
    model_config = ConfigDict(populate_by_name=True)
