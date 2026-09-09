from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field, ConfigDict
from datetime import datetime, timezone
from backend.core.roadmap_schemas import Roadmap, Stage

class StateChangeEvent(BaseModel):
    event_id: str = Field(default_factory=lambda: f"evt_{int(datetime.now(timezone.utc).timestamp()*1000)}")
    person_id: str
    change_type: str  # GOAL_CHANGE, EVIDENCE_CHANGE, MASTERY_RISK, CONSTRAINT_CHANGE, OPPORTUNITY_CHANGE, INTERRUPTION_RESUME, EVIDENCE_CONFLICT
    title: str
    description: str
    trigger_data: Dict[str, Any] = Field(default_factory=dict)
    detected_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    model_config = ConfigDict(populate_by_name=True)

class ImpactAnalysis(BaseModel):
    impact_level: str = "MODERATE_IMPACT"  # LOW_IMPACT, MODERATE_IMPACT, HIGH_IMPACT, CRITICAL_CHANGE
    what_changed: str
    why: str
    affected_roadmap_stages: List[str] = Field(default_factory=list)
    affected_career_requirements: List[str] = Field(default_factory=list)
    invalidated_assumptions: List[str] = Field(default_factory=list)
    preserved_assets: List[str] = Field(default_factory=list)
    reconsidered_areas: List[str] = Field(default_factory=list)
    requires_user_approval: bool = False
    approval_type: str = "AUTO_ADAPT"  # AUTO_ADAPT, REVIEW, APPROVAL_REQUIRED
    next_action_recommendation: str

    model_config = ConfigDict(populate_by_name=True)

class ProposedAdaptation(BaseModel):
    adaptation_id: str = Field(default_factory=lambda: f"adapt_{int(datetime.now(timezone.utc).timestamp()*1000)}")
    person_id: str
    change_event: StateChangeEvent
    impact_analysis: ImpactAnalysis
    previous_roadmap_version: int
    proposed_roadmap_version: int
    change_summary: str
    changed_stages: List[Dict[str, Any]] = Field(default_factory=list)
    unchanged_stages: List[str] = Field(default_factory=list)
    proposed_roadmap: Optional[Roadmap] = None
    rationale: str
    status: str = "PENDING_APPROVAL"  # PENDING_APPROVAL, APPROVED, REJECTED, AUTO_APPLIED
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    resolved_at: Optional[str] = None

    model_config = ConfigDict(populate_by_name=True)

class UserAdaptationDecision(BaseModel):
    adaptation_id: str
    person_id: str
    action: str  # APPROVE, REJECT, MODIFY
    user_feedback: Optional[str] = None
    decided_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    model_config = ConfigDict(populate_by_name=True)

class AdaptationAuditRecord(BaseModel):
    audit_id: str = Field(default_factory=lambda: f"audit_{int(datetime.now(timezone.utc).timestamp()*1000)}")
    person_id: str
    event_type: str
    detected_change: str
    previous_version: int
    resulting_version: int
    impact_level: str
    approval_state: str
    rationale: str
    actor: str = "USER"  # USER, SYSTEM_AUTO, MENTOR_AGENT
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    model_config = ConfigDict(populate_by_name=True)

class PauseResumeAnalysis(BaseModel):
    person_id: str
    elapsed_days: int = 0
    last_activity_date: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    status: str = "ACTIVE"  # ACTIVE, SHORT_PAUSE, LONG_BREAK
    recommended_action: str = "CONTINUE"  # CONTINUE, REFRESH, REASSESS, REPLAN
    reassessment_rationale: str
    suggested_refresher_concept: Optional[str] = None

    model_config = ConfigDict(populate_by_name=True)

class ConflictDetectionResult(BaseModel):
    person_id: str
    has_conflict: bool = False
    conflict_type: Optional[str] = None  # EVIDENCE_CONFLICT
    self_report_claim: Optional[str] = None
    observed_task_evidence: Optional[str] = None
    explanation: Optional[str] = None
    recommended_verification_task: Optional[str] = None

    model_config = ConfigDict(populate_by_name=True)

class ContinuousIntelligenceState(BaseModel):
    person_id: str
    active_target_role: str
    current_roadmap_version: int
    plan_stability_status: str = "STABLE"  # STABLE, PENDING_REVIEW, REPLANNING_REQUIRED
    pending_adaptations: List[ProposedAdaptation] = Field(default_factory=list)
    recent_audits: List[AdaptationAuditRecord] = Field(default_factory=list)
    pause_status: PauseResumeAnalysis
    conflict_status: ConflictDetectionResult
    last_evaluated_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    model_config = ConfigDict(populate_by_name=True)
