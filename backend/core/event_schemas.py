from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field, ConfigDict
from datetime import datetime, timezone

class EventRecord(BaseModel):
    event_id: str = Field(default_factory=lambda: f"evt_{int(datetime.now(timezone.utc).timestamp()*1000)}")
    person_id: str
    event_type: str  # GOAL_CHANGED, PROFILE_CHANGED, CONSTRAINT_CHANGED, ROADMAP_CHANGED, STAGE_COMPLETED, STAGE_BLOCKED, EVIDENCE_SUBMITTED, EVIDENCE_FAILED, MASTERY_CHANGED, MASTERY_AT_RISK, OPPORTUNITY_FOUND, OPPORTUNITY_DEADLINE_APPROACHING, DECISION_MADE, PAUSE_STARTED, RETURNED_TO_LEARNING, MEMORY_EVENT_CREATED
    occurred_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    source: str = "SYSTEM_STATE_DETECTOR"
    source_reference: Optional[str] = None
    entity_type: Optional[str] = None
    entity_id: Optional[str] = None
    importance: str = "RELEVANT"  # IGNORE, BACKGROUND, RELEVANT, IMPORTANT, URGENT
    processed_state: str = "PENDING"  # PENDING, PROCESSED, DISMISSED, DEDUPLICATED
    metadata: Dict[str, Any] = Field(default_factory=dict)

    model_config = ConfigDict(populate_by_name=True)

class Intervention(BaseModel):
    intervention_id: str = Field(default_factory=lambda: f"intv_{int(datetime.now(timezone.utc).timestamp()*1000)}")
    person_id: str
    event_id: str
    type: str  # SUBMIT_EVIDENCE, REVIEW_REINFORCEMENT, CONTINUE_STAGE, REVIEW_PATH_CHANGE, REVIEW_OPPORTUNITY, APPLY_OPPORTUNITY, REASSESS, CONFIRM_DECISION, CELEBRATE_MASTERY, GENTLE_REENTRY
    priority: str = "NORMAL"  # LOW, NORMAL, HIGH, CRITICAL
    title: str
    what_happened: str
    why_it_matters: str
    what_should_i_do: str
    what_happens_if_ignored: str
    action_url: str = "/journey"
    related_entity_type: Optional[str] = None
    related_entity_id: Optional[str] = None
    status: str = "PENDING"  # PENDING, SEEN, ACTED_ON, DISMISSED, EXPIRED
    requires_confirmation: bool = False
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    expires_at: Optional[str] = None

    model_config = ConfigDict(populate_by_name=True)

class InterventionOutcome(BaseModel):
    intervention_id: str
    person_id: str
    outcome: str  # ACTED, DISMISSED, EXPIRED, IGNORED
    feedback_note: Optional[str] = None
    acted_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    model_config = ConfigDict(populate_by_name=True)

class NotificationPreferences(BaseModel):
    person_id: str
    enable_opportunity_alerts: bool = True
    enable_mastery_alerts: bool = True
    enable_blocker_alerts: bool = True
    enable_reinforcement_alerts: bool = True
    quiet_hours_enabled: bool = False
    quiet_hours_start: str = "22:00"
    quiet_hours_end: str = "08:00"
    updated_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    model_config = ConfigDict(populate_by_name=True)
