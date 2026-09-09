import uuid
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field, ConfigDict
from datetime import datetime, timezone

class ActionBlocker(BaseModel):
    blocker_id: str = Field(default_factory=lambda: f"blk_{int(datetime.now(timezone.utc).timestamp()*1000)}_{uuid.uuid4().hex[:6]}")
    blocker_type: str = "TECHNICAL_BLOCKER"  # KNOWLEDGE_GAP, EVIDENCE_GAP, RESOURCE_GAP, TIME_CONSTRAINT, FINANCIAL_CONSTRAINT, ACCESS_CONSTRAINT, TECHNICAL_BLOCKER, DECISION_REQUIRED, EXTERNAL_DEPENDENCY, OPPORTUNITY_CHANGE, USER_PAUSE, OTHER
    description: str
    workaround: Optional[str] = None
    suggested_resolution_action: Optional[str] = None
    is_active: bool = True
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    model_config = ConfigDict(populate_by_name=True)

class RescheduleEvent(BaseModel):
    original_due_at: str
    new_due_at: str
    reason: str
    rescheduled_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    model_config = ConfigDict(populate_by_name=True)

class CanonicalAction(BaseModel):
    action_id: str = Field(default_factory=lambda: f"act_{int(datetime.now(timezone.utc).timestamp()*1000)}_{uuid.uuid4().hex[:6]}")
    person_id: str
    title: str
    description: str
    action_type: str = "LEARNING"  # LEARNING, PRACTICE, EVIDENCE, PROJECT, ASSESSMENT, REINFORCEMENT, CAREER_RESEARCH, APPLICATION, INTERVIEW_PREPARATION, NETWORKING, CREDENTIAL, DECISION, REASSESSMENT, ADMINISTRATIVE
    goal_id: Optional[str] = None
    goal_title: Optional[str] = None
    roadmap_version: int = 1
    stage_id: Optional[str] = None
    stage_title: Optional[str] = None
    capability_ids: List[str] = Field(default_factory=list)
    evidence_requirement_ids: List[str] = Field(default_factory=list)
    priority: str = "NOW"  # NOW, NEXT, LATER, OPTIONAL
    status: str = "READY"  # NOT_STARTED, READY, IN_PROGRESS, BLOCKED, COMPLETED, ABANDONED, SKIPPED, SUPERSEDED, EXPIRED
    dependencies: List[str] = Field(default_factory=list)
    blocking_reason: Optional[ActionBlocker] = None
    verification_requirement: str = "SIMPLE_CONFIRMATION"  # SIMPLE_CONFIRMATION, EVIDENCE_SUBMISSION, EXTERNAL_STATE, CAREER_APPLICATION, MASTERY_EVIDENCE
    outcome: str = "NO_RESULT"  # COMPLETED_SUCCESSFULLY, COMPLETED_WITH_GAP, COMPLETED_NOT_VERIFIED, FAILED, PARTIALLY_COMPLETED, NO_RESULT
    outcome_notes: Optional[str] = None
    source: str = "ROADMAP_DECOMPOSITION"  # ROADMAP_DECOMPOSITION, USER_CREATED, ACCOUNTABILITY_PARTNER, INTERVENTION, CAREER_OPPORTUNITY
    source_reference: Optional[str] = None
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    due_at: Optional[str] = None
    reschedule_history: List[RescheduleEvent] = Field(default_factory=list)

    model_config = ConfigDict(populate_by_name=True)

class OpportunityApplicationTracker(BaseModel):
    application_id: str = Field(default_factory=lambda: f"app_{int(datetime.now(timezone.utc).timestamp()*1000)}_{uuid.uuid4().hex[:6]}")
    person_id: str
    opportunity_id: str
    opportunity_title: str
    organization: str
    status: str = "SAVED"  # DISCOVERED, SAVED, PREPARING, APPLIED, INTERVIEWING, OFFER, REJECTED, WITHDRAWN, EXPIRED
    tailored_resume_id: Optional[str] = None
    notes: Optional[str] = None
    applied_at: Optional[str] = None
    updated_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    model_config = ConfigDict(populate_by_name=True)

class DailyExecutionPlan(BaseModel):
    person_id: str
    primary_action: Optional[CanonicalAction] = None
    secondary_actions: List[CanonicalAction] = Field(default_factory=list)
    why_it_matters: str
    evidence_proof_required: str
    active_blockers: List[ActionBlocker] = Field(default_factory=list)
    next_subsequent_step: str
    is_paused: bool = False
    pause_reason: Optional[str] = None
    as_of_date: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    model_config = ConfigDict(populate_by_name=True)

class AccountabilityIntervention(BaseModel):
    intervention_id: str = Field(default_factory=lambda: f"acc_{int(datetime.now(timezone.utc).timestamp()*1000)}_{uuid.uuid4().hex[:6]}")
    person_id: str
    missed_action_id: str
    action_title: str
    original_due_at: str
    days_overdue: int = 1
    non_judgmental_message: str
    suggested_options: List[str] = Field(default_factory=list)
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    model_config = ConfigDict(populate_by_name=True)

class CreateActionRequest(BaseModel):
    title: str
    description: Optional[str] = ""
    action_type: Optional[str] = "LEARNING"
    priority: Optional[str] = "NOW"
    goal_id: Optional[str] = None
    stage_id: Optional[str] = None
    capability_ids: Optional[List[str]] = None
    evidence_requirement_ids: Optional[List[str]] = None
    due_at: Optional[str] = None
    verification_requirement: Optional[str] = "SIMPLE_CONFIRMATION"

class RescheduleActionRequest(BaseModel):
    new_due_at: str
    reason: str

class BlockActionRequest(BaseModel):
    blocker_type: str = "TECHNICAL_BLOCKER"
    description: str
    workaround: Optional[str] = None

class CompleteActionRequest(BaseModel):
    outcome: Optional[str] = "COMPLETED_SUCCESSFULLY"
    outcome_notes: Optional[str] = None
    evidence_id: Optional[str] = None
    submission_payload: Optional[Dict[str, Any]] = None

class PauseExecutionRequest(BaseModel):
    reason: str

class TrackApplicationRequest(BaseModel):
    opportunity_id: str
    opportunity_title: str
    organization: str
    status: str = "SAVED"
    notes: Optional[str] = None
    applied_at: Optional[str] = None
