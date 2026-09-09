from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field, ConfigDict
from datetime import datetime, timezone

class CanonicalEvidence(BaseModel):
    evidence_id: str = Field(default_factory=lambda: f"ev_{int(datetime.now(timezone.utc).timestamp()*1000)}")
    person_id: str
    evidence_type: str = "CODE_REPO"  # CODE_REPO, PROJECT_DEMO, WRITTEN_EXPLANATION, ASSESSMENT_TASK, PRACTICAL_DEBUG, PORTFOLIO_ARTIFACT, EXTERNAL_CREDENTIAL, INTERVIEW_SIMULATION
    title: str
    description: str
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    source: str = "USER_SUBMISSION"  # USER_SUBMISSION, GITHUB_INTEGRATION, OFFICIAL_PROVIDER, IN_APP_TASK
    source_reference: str  # GitHub URL, commit hash, file hash, task ID
    related_skill_ids: List[str] = Field(default_factory=list)
    related_stage_id: str
    related_goal_id: Optional[str] = None
    verification_status: str = "UNVERIFIED"  # VERIFIED, UNVERIFIED, VERIFICATION_FAILED, INSUFFICIENT_EVIDENCE
    quality: str = "MODERATE"  # WEAK, MODERATE, STRONG, VERIFIED_STRONG, INSUFFICIENT
    strength: str = "MEDIUM"  # LOW, MEDIUM, HIGH
    confidence: str = "HIGH"  # LOW, MEDIUM, HIGH
    metadata: Dict[str, Any] = Field(default_factory=dict)

    model_config = ConfigDict(populate_by_name=True)

class StructuredEvaluationDetail(BaseModel):
    observed: List[str] = Field(default_factory=list)
    inferred: List[str] = Field(default_factory=list)
    recommendation: List[str] = Field(default_factory=list)
    mastery_state_achieved: str = "APPLICATION"  # NOT_STARTED, EXPOSED, UNDERSTANDING, APPLICATION, TRANSFER, PROVISIONAL_MASTERY, DEMONSTRATED_MASTERY, MASTERY_AT_RISK, NEEDS_REINFORCEMENT, INSUFFICIENT_EVIDENCE
    observable_misconceptions: List[str] = Field(default_factory=list)
    transfer_validated: bool = False
    evidence_quality_awarded: str = "STRONG"

    model_config = ConfigDict(populate_by_name=True)

class EvaluationAttempt(BaseModel):
    attempt_id: str = Field(default_factory=lambda: f"att_{int(datetime.now(timezone.utc).timestamp()*1000)}")
    submission_id: str
    evidence_id: str
    stage_id: str
    person_id: str
    attempt_number: int = 1
    status: str = "PASS"  # PASS, REINFORCE, INSUFFICIENT_EVIDENCE
    score_accuracy: float = 85.0
    evaluation_detail: StructuredEvaluationDetail
    evaluated_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    model_config = ConfigDict(populate_by_name=True)

class EvidenceDispute(BaseModel):
    dispute_id: str = Field(default_factory=lambda: f"disp_{int(datetime.now(timezone.utc).timestamp()*1000)}")
    person_id: str
    attempt_id: str
    reason: str
    additional_evidence_reference: Optional[str] = None
    status: str = "PENDING_REVIEW"  # PENDING_REVIEW, REASSESSED, UPHELD, OVERTURNED
    resolution_note: Optional[str] = None
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    resolved_at: Optional[str] = None

    model_config = ConfigDict(populate_by_name=True)

class SkillMasteryProfile(BaseModel):
    skill_name: str
    category: str = "Technical Competency"
    mastery_state: str = "NOT_STARTED"  # NOT_STARTED, EXPOSED, UNDERSTANDING, APPLICATION, TRANSFER, PROVISIONAL_MASTERY, DEMONSTRATED_MASTERY, MASTERY_AT_RISK, NEEDS_REINFORCEMENT, INSUFFICIENT_EVIDENCE
    evidence_count: int = 0
    primary_evidence_id: Optional[str] = None
    last_verified_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    is_regression_risk: bool = False
    regression_reason: Optional[str] = None

    model_config = ConfigDict(populate_by_name=True)

class LockedStageReason(BaseModel):
    stage_id: str
    stage_number: int
    title: str
    prerequisite_stage_id: str
    prerequisite_title: str
    missing_capabilities: List[str] = Field(default_factory=list)
    required_evidence_type: str = "CODE_REPO"
    unlock_rule: str

    model_config = ConfigDict(populate_by_name=True)

class MasteryDashboardState(BaseModel):
    person_id: str
    skills_mastered: List[SkillMasteryProfile] = Field(default_factory=list)
    capabilities_working_on: List[Dict[str, Any]] = Field(default_factory=list)
    evidence_needed: List[Dict[str, Any]] = Field(default_factory=list)
    locked_stages: List[LockedStageReason] = Field(default_factory=list)
    recent_evaluations: List[EvaluationAttempt] = Field(default_factory=list)
    active_disputes: List[EvidenceDispute] = Field(default_factory=list)
    last_updated_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    model_config = ConfigDict(populate_by_name=True)
