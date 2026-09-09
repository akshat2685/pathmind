from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field, ConfigDict
from datetime import datetime, timezone

class ProvenanceRecord(BaseModel):
    provenance_id: str = Field(default_factory=lambda: f"prov_{int(datetime.now(timezone.utc).timestamp()*1000)}")
    claim_id: str
    source_type: str  # USER, ASSESSMENT, EVIDENCE, INTERNAL_DETERMINISTIC, ESCO, NCO, O_NET, OPPORTUNITY_PROVIDER, VERIFIED_PROVIDER
    source_id: Optional[str] = None
    source_url: Optional[str] = None
    provider: str = "ESCO / NCO Occupational Standard Graph"
    retrieved_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    source_version: str = "2026.1"
    verification_status: str = "VERIFIED"  # VERIFIED, UNVERIFIED, STALE
    confidence: str = "HIGH"  # HIGH, MEDIUM, LOW, INSUFFICIENT_EVIDENCE

    model_config = ConfigDict(populate_by_name=True)

class TraceableClaim(BaseModel):
    claim_id: str = Field(default_factory=lambda: f"clm_{int(datetime.now(timezone.utc).timestamp()*1000)}")
    claim_text: str
    claim_category: str  # FACT, USER_STATED, OBSERVATION, INFERENCE, RECOMMENDATION, UNKNOWN
    provenance: Optional[ProvenanceRecord] = None
    supporting_evidence_ids: List[str] = Field(default_factory=list)

    model_config = ConfigDict(populate_by_name=True)

class StructuredRecommendation(BaseModel):
    recommendation_id: str = Field(default_factory=lambda: f"rec_{int(datetime.now(timezone.utc).timestamp()*1000)}")
    person_id: str
    type: str  # NEXT_ACTION, CAREER_DIRECTION, SKILL_REINFORCEMENT, OPPORTUNITY_APPLICATION, CREDENTIAL_PURSUIT, ROADMAP_ADAPTATION
    title: str
    summary: str
    target_role: str
    goal_id: Optional[str] = None
    why_now: str
    grounding_claims: List[TraceableClaim] = Field(default_factory=list)
    options: List[Dict[str, Any]] = Field(default_factory=list)
    tradeoffs: List[str] = Field(default_factory=list)
    uncertainties: List[str] = Field(default_factory=list)
    recommended_choice: str
    alternative_choices: List[str] = Field(default_factory=list)
    status: str = "ACTIVE"  # ACTIVE, ACCEPTED, REJECTED, SUPERSEDED, EXPIRED
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    expires_at: Optional[str] = None

    model_config = ConfigDict(populate_by_name=True)

class RecommendationExplanation(BaseModel):
    explanation_id: str = Field(default_factory=lambda: f"exp_{int(datetime.now(timezone.utc).timestamp()*1000)}")
    recommendation_id: str
    person_id: str
    why_this: str
    why_not_alternative: str
    facts_summary: List[str] = Field(default_factory=list)
    evidence_summary: List[str] = Field(default_factory=list)
    inference_summary: List[str] = Field(default_factory=list)
    unknowns_summary: List[str] = Field(default_factory=list)
    safety_disclaimer: str = "Guidance is grounded in official occupational standards and your verified evidence. You retain full autonomy over your learning choices."
    generated_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    model_config = ConfigDict(populate_by_name=True)

class SafetyGuardrailResult(BaseModel):
    is_safe: bool = True
    rejected_claims: List[str] = Field(default_factory=list)
    safety_category: str = "PASSED"  # PASSED, UNSUPPORTED_FACT, PSYCHOLOGICAL_OVERREACH, EMPLOYMENT_GUARANTEE_VIOLATION, UNVERIFIED_OPPORTUNITY
    remediation_notes: Optional[str] = None

    model_config = ConfigDict(populate_by_name=True)

class UserRecommendationFeedback(BaseModel):
    feedback_id: str = Field(default_factory=lambda: f"fb_{int(datetime.now(timezone.utc).timestamp()*1000)}")
    recommendation_id: str
    person_id: str
    feedback_type: str  # HELPFUL, NOT_HELPFUL, INCORRECT, MISSING_CONTEXT, OUTDATED, WRONG_SOURCE, DISAGREE
    notes: Optional[str] = None
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    model_config = ConfigDict(populate_by_name=True)
