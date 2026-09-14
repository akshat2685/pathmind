from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field, ConfigDict
from datetime import datetime, timezone
from enum import Enum

class ClaimCategory(str, Enum):
    FACT = "FACT"
    USER_STATED = "USER_STATED"
    OBSERVATION = "OBSERVATION"
    ASSESSMENT = "ASSESSMENT"
    EXTERNAL_SOURCE = "EXTERNAL_SOURCE"
    INFERENCE = "INFERENCE"
    RECOMMENDATION = "RECOMMENDATION"
    UNKNOWN = "UNKNOWN"

class ProvenanceOrigin(str, Enum):
    USER_STATED = "USER_STATED"
    USER_SUBMITTED = "USER_SUBMITTED"
    ASSESSMENT = "ASSESSMENT"
    OBSERVED = "OBSERVED"
    EXTERNAL_SOURCE = "EXTERNAL_SOURCE"
    MEMORY = "MEMORY"
    SYSTEM_INFERENCE = "SYSTEM_INFERENCE"

class VerificationStatus(str, Enum):
    VERIFIED = "VERIFIED"
    UNVERIFIED = "UNVERIFIED"
    INFERRED = "INFERRED"
    UNKNOWN = "UNKNOWN"
    SUPERSEDED = "SUPERSEDED"
    EXPIRED = "EXPIRED"
    STALE = "STALE"

class ConfidenceCategory(str, Enum):
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"

class DecisionReversibility(str, Enum):
    REVERSIBLE = "REVERSIBLE"
    PARTIALLY_REVERSIBLE = "PARTIALLY_REVERSIBLE"
    HIGH_COST_TO_REVERSE = "HIGH_COST_TO_REVERSE"
    UNKNOWN = "UNKNOWN"

class SourceFreshness(BaseModel):
    retrieved_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    source_version: str = "2026.1"
    valid_from: Optional[str] = None
    valid_until: Optional[str] = None

    def is_current(self) -> bool:
        if not self.valid_until:
            return True
        try:
            exp = datetime.fromisoformat(self.valid_until.replace("Z", "+00:00"))
            return datetime.now(timezone.utc) < exp
        except Exception:
            return True

    model_config = ConfigDict(populate_by_name=True)

class ProvenanceRecord(BaseModel):
    provenance_id: str = Field(default_factory=lambda: f"prov_{int(datetime.now(timezone.utc).timestamp()*1000)}")
    claim_id: Optional[str] = None
    source_type: str = "EXTERNAL_SOURCE"  # USER_STATED, USER_SUBMITTED, ASSESSMENT, OBSERVED, EXTERNAL_SOURCE, MEMORY, SYSTEM_INFERENCE, ESCO, NCO, O_NET, OPPORTUNITY_PROVIDER, VERIFIED_PROVIDER
    origin: str = "EXTERNAL_SOURCE"  # USER_STATED, USER_SUBMITTED, ASSESSMENT, OBSERVED, EXTERNAL_SOURCE, MEMORY, SYSTEM_INFERENCE
    source_id: Optional[str] = None
    source_url: Optional[str] = None
    provider: str = "ESCO / NCO Occupational Standard Graph"
    retrieved_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    source_version: str = "2026.1"
    valid_from: Optional[str] = None
    valid_until: Optional[str] = None
    verification_status: str = "VERIFIED"  # VERIFIED, UNVERIFIED, INFERRED, UNKNOWN, SUPERSEDED, EXPIRED, STALE
    confidence: str = "HIGH"  # HIGH, MEDIUM, LOW, INSUFFICIENT_EVIDENCE
    freshness: Optional[SourceFreshness] = None

    model_config = ConfigDict(populate_by_name=True)

ProvenanceMetadata = ProvenanceRecord

class TraceableClaim(BaseModel):
    claim_id: str = Field(default_factory=lambda: f"clm_{int(datetime.now(timezone.utc).timestamp()*1000)}")
    claim_text: str
    claim_category: str  # FACT, USER_STATED, OBSERVATION, ASSESSMENT, EXTERNAL_SOURCE, INFERENCE, RECOMMENDATION, UNKNOWN
    origin: str = "EXTERNAL_SOURCE"  # USER_STATED, USER_SUBMITTED, ASSESSMENT, OBSERVED, EXTERNAL_SOURCE, MEMORY, SYSTEM_INFERENCE
    provenance: Optional[ProvenanceRecord] = None
    supporting_evidence_ids: List[str] = Field(default_factory=list)
    confidence: str = "HIGH"  # HIGH, MEDIUM, LOW, INSUFFICIENT_EVIDENCE

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
    confidence_category: str = "MEDIUM"  # HIGH, MEDIUM, LOW, INSUFFICIENT_EVIDENCE
    reversibility: str = "REVERSIBLE"  # REVERSIBLE, PARTIALLY_REVERSIBLE, HIGH_COST_TO_REVERSE, UNKNOWN
    reversibility_rationale: Optional[str] = None
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
    assessment_summary: List[str] = Field(default_factory=list)
    inference_summary: List[str] = Field(default_factory=list)
    unknowns_summary: List[str] = Field(default_factory=list)
    what_could_change_this: List[str] = Field(default_factory=list)
    confidence_category: str = "MEDIUM"
    reversibility: str = "REVERSIBLE"
    sources_used: List[Dict[str, str]] = Field(default_factory=list)
    safety_disclaimer: str = "Guidance is grounded in official occupational standards and your verified evidence. You retain full autonomy over your learning choices."
    generated_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    model_config = ConfigDict(populate_by_name=True)

class DecisionRecord(BaseModel):
    decision_id: str = Field(default_factory=lambda: f"dec_{int(datetime.now(timezone.utc).timestamp()*1000)}")
    person_id: str
    decision_type: str = "CAREER_PATH_CHOICE"  # CAREER_PATH_CHOICE, STAGE_ELECTIVE, OPPORTUNITY_APPLICATION, WORKLOAD_ADJUSTMENT, TRAJECTORY_RECOMMENDATION
    decision: Optional[str] = None
    recommended_choice: Optional[str] = None
    confidence: str = "MEDIUM"
    confidence_justification: Optional[str] = None
    alternatives: List[str] = Field(default_factory=list)
    supporting_evidence: List[str] = Field(default_factory=list)
    context: str = ""
    reason: Optional[str] = None
    reversibility: str = "REVERSIBLE"  # REVERSIBLE, PARTIALLY_REVERSIBLE, HIGH_COST_TO_REVERSE, UNKNOWN
    reversibility_rationale: Optional[str] = None
    reversal_cost_notes: Optional[str] = None
    grounding_claims: List[TraceableClaim] = Field(default_factory=list)
    conflict_notices: List["ConflictNotice"] = Field(default_factory=list)
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    outcome: Optional[str] = None

    model_config = ConfigDict(populate_by_name=True)

class ConflictNotice(BaseModel):
    conflict_id: str = Field(default_factory=lambda: f"cnf_{int(datetime.now(timezone.utc).timestamp()*1000)}")
    person_id: Optional[str] = None
    conflict_type: str = "EVIDENCE_VS_CLAIM"  # GOAL_VS_HISTORY, ASSESSMENT_VS_GOAL, EVIDENCE_VS_CLAIM, REQUIREMENT_CONFLICT
    summary: Optional[str] = None
    details: Optional[str] = None
    clarification_prompt: Optional[str] = None
    what_conflicts: List[str] = Field(default_factory=list)
    discrepancy_description: Optional[str] = None
    resolution_strategy: str = "user_clarification"  # user_clarification, fresher_source_preferred, higher_verifiability_preferred, both_presented
    user_action_needed: Optional[str] = None
    detected_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

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
