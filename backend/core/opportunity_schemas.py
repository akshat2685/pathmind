import uuid
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field, ConfigDict, model_validator
from datetime import datetime, timezone
from backend.core.career_schemas import VerifiedOpportunity

class CanonicalOpportunity(VerifiedOpportunity):
    """
    Canonical single-source-of-truth opportunity object.
    Subclasses VerifiedOpportunity for 100% interoperability with existing career readiness engines.
    Preserves strict provider provenance, verification status, and expiration.
    """
    opportunity_id: str = Field(default_factory=lambda: f"opp_{int(datetime.now(timezone.utc).timestamp()*1000)}_{uuid.uuid4().hex[:6]}")
    provider: str = "Verified Provider"
    provider_record_id: str = Field(default_factory=lambda: f"rec_{uuid.uuid4().hex[:6]}")
    type: str = "INTERNSHIP"  # INTERNSHIP, FULL_TIME, APPRENTICESHIP, RESEARCH, FELLOWSHIP, SCHOLARSHIP, COMPETITION, HACKATHON, OPEN_SOURCE, GRADUATE, CERTIFICATION, BOOTCAMP
    title: str
    organization: str
    description: str = ""
    location: str
    remote_status: str = "HYBRID"  # REMOTE, HYBRID, ONSITE
    eligibility: str
    requirements: List[str] = Field(default_factory=list)
    preferred_requirements: List[str] = Field(default_factory=list)
    skills: List[str] = Field(default_factory=list)
    education_requirements: List[str] = Field(default_factory=list)
    experience_requirements: List[str] = Field(default_factory=list)
    credential_requirements: List[str] = Field(default_factory=list)
    compensation: Optional[str] = None
    deadline: str = ""
    start_date: Optional[str] = None
    application_url: str = ""
    source_url: str = ""
    status: str = "ACTIVE"  # DISCOVERED, VERIFIED, ACTIVE, EXPIRING, EXPIRED, CLOSED, WITHDRAWN, UNVERIFIED, SOURCE_UNAVAILABLE
    retrieved_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    expires_at: Optional[str] = None
    source_version: Optional[str] = None
    verification_status: str = "VERIFIED"  # VERIFIED, UNVERIFIED

    # Backwards compatibility fields from VerifiedOpportunity
    apply_url: str = ""
    required_skills: List[str] = Field(default_factory=list)
    preferred_skills: List[str] = Field(default_factory=list)
    fit_level: str = "HIGH"
    fit_reasons: List[str] = Field(default_factory=list)
    missing_requirements: List[str] = Field(default_factory=list)
    eligibility_blockers: List[str] = Field(default_factory=list)
    pre_application_advice: str = ""

    model_config = ConfigDict(populate_by_name=True, extra="allow")

    @model_validator(mode="before")
    @classmethod
    def sync_urls_and_requirements(cls, data: Any) -> Any:
        if isinstance(data, dict):
            if "application_url" in data and not data.get("apply_url"):
                data["apply_url"] = data["application_url"]
            elif "apply_url" in data and not data.get("application_url"):
                data["application_url"] = data["apply_url"]
            if "requirements" in data and not data.get("required_skills"):
                data["required_skills"] = data["requirements"]
            elif "required_skills" in data and not data.get("requirements"):
                data["requirements"] = data["required_skills"]
            if "preferred_requirements" in data and not data.get("preferred_skills"):
                data["preferred_skills"] = data["preferred_requirements"]
            elif "preferred_skills" in data and not data.get("preferred_requirements"):
                data["preferred_requirements"] = data["preferred_skills"]
        return data

class OpportunityMatchResult(BaseModel):
    """
    Explainable match result for an opportunity evaluated against real person state.
    Distinguishes fit from readiness and guarantees missing profile fields are marked UNKNOWN, not failure.
    """
    opportunity: CanonicalOpportunity
    fit_state: str = "GOOD_MATCH"  # STRONG_MATCH, GOOD_MATCH, PARTIAL_MATCH, LOW_MATCH, INELIGIBLE, INSUFFICIENT_INFORMATION
    readiness_state: str = "NEAR_READY"  # READY_NOW, NEAR_READY, STRETCH, NOT_RECOMMENDED
    matched_requirements: List[str] = Field(default_factory=list)
    gaps: List[str] = Field(default_factory=list)
    unknowns: List[str] = Field(default_factory=list)
    why_it_matters: str
    next_step: str
    decision_recommendation: str = "RECOMMEND_PREPARING_FIRST"  # RECOMMEND_APPLYING, RECOMMEND_PREPARING_FIRST, LOW_PRIORITY, INSUFFICIENT_INFORMATION
    tradeoffs: List[str] = Field(default_factory=list)

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
