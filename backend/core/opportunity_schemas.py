import uuid
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field, ConfigDict
from datetime import datetime, timezone

class CanonicalOpportunity(BaseModel):
    """
    Canonical single-source-of-truth opportunity object.
    Fully decoupled from user readiness/fit.
    """
    id: str = Field(default_factory=lambda: f"opp_{int(datetime.now(timezone.utc).timestamp()*1000)}_{uuid.uuid4().hex[:6]}")
    title: str
    organization: str
    opportunity_type: str = "UNKNOWN"
    domain: str = "UNKNOWN"
    field: str = "UNKNOWN"
    target_roles: List[str] = Field(default_factory=list)
    description: str = ""
    location: str = "UNKNOWN"
    geography: str = "UNKNOWN"
    remote_status: str = "UNKNOWN"
    eligibility: str = "UNKNOWN"
    requirements: List[str] = Field(default_factory=list)
    credentials: List[str] = Field(default_factory=list)
    experience_requirements: List[str] = Field(default_factory=list)
    deadline: str = "UNKNOWN"
    start_date: str = "UNKNOWN"
    source: str = "UNKNOWN"
    source_id: str = "UNKNOWN"
    source_url: str = "UNKNOWN"
    retrieved_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    source_version: str = "1.0"
    freshness_status: str = "FRESH" # FRESH, AGING, STALE, EXPIRED, VERIFICATION_REQUIRED
    verification_status: str = "UNVERIFIED" # VERIFIED, UNVERIFIED
    status: str = "ACTIVE"
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    model_config = ConfigDict(populate_by_name=True, extra="allow")


class OpportunityMatch(BaseModel):
    """
    Explainable match result for an opportunity evaluated against real person state.
    Strictly separates eligibility from fit and readiness.
    """
    opportunity_id: str
    goal_id: str
    match_reasons: List[str] = Field(default_factory=list)
    requirement_matches: List[str] = Field(default_factory=list)
    requirement_gaps: List[str] = Field(default_factory=list)
    eligibility_status: str = "UNKNOWN" # ELIGIBLE, INELIGIBLE, UNKNOWN
    fit_status: str = "UNKNOWN" # HIGH, MEDIUM, LOW, NOT_RELEVANT
    readiness_status: str = "UNKNOWN" # READY, PARTIALLY_READY, NOT_READY, UNKNOWN
    feasibility_status: str = "UNKNOWN" # HIGH, MEDIUM, LOW, UNKNOWN
    confidence: str = "LOW"
    uncertainty: List[str] = Field(default_factory=list)
    evidence: List[str] = Field(default_factory=list)
    generated_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    
    opportunity: Optional[CanonicalOpportunity] = None # Added for convenience of passing the object

    model_config = ConfigDict(populate_by_name=True)


class SavedOpportunity(BaseModel):
    id: str = Field(default_factory=lambda: f"svopp_{int(datetime.now(timezone.utc).timestamp()*1000)}_{uuid.uuid4().hex[:6]}")
    user_id: str
    opportunity_id: str
    goal_id: str
    saved_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    notes: str = ""
    status: str = "SAVED"
    last_reviewed_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    model_config = ConfigDict(populate_by_name=True)


class ApplicationRecord(BaseModel):
    id: str = Field(default_factory=lambda: f"app_{int(datetime.now(timezone.utc).timestamp()*1000)}_{uuid.uuid4().hex[:6]}")
    user_id: str
    opportunity_id: str
    status: str = "DISCOVERED" # DISCOVERED, SAVED, PLANNING, READY_TO_APPLY, APPLIED, ASSESSMENT, INTERVIEW, WAITING, OFFER, REJECTED, WITHDRAWN, COMPLETED
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    model_config = ConfigDict(populate_by_name=True)

class ApplicationPreparationPlan(BaseModel):
    opportunity_id: str
    person_id: str
    target_role: str
    required_actions: List[Dict[str, Any]] = Field(default_factory=list)
    estimated_effort_days: int = 7
    deadline_feasibility: str = "FEASIBLE"  # FEASIBLE, TIGHT, INSUFFICIENT_TIME
    generated_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    model_config = ConfigDict(populate_by_name=True)

class InterviewPrepPackage(BaseModel):
    opportunity_id: str
    opportunity_title: str
    organization: str
    technical_competency_questions: List[str] = Field(default_factory=list)
    project_defense_questions: List[str] = Field(default_factory=list)
    gap_reinforcement_focus: List[str] = Field(default_factory=list)
    generated_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    model_config = ConfigDict(populate_by_name=True)

class CreatePreparationPlanRequest(BaseModel):
    spawn_actions_to_execution_engine: bool = True
