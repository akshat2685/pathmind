from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field, ConfigDict
from datetime import datetime, timezone

class CapabilityEvolutionRecord(BaseModel):
    skill_name: str
    first_demonstrated_at: Optional[str] = None
    latest_evaluated_at: Optional[str] = None
    current_mastery_state: str = "INTRODUCED"  # EXPOSED, UNDERSTANDING, APPLICATION, TRANSFER, DEMONSTRATED_MASTERY, MASTERY_AT_RISK
    mastery_trajectory: List[Dict[str, Any]] = Field(default_factory=list)
    evidence_ids: List[str] = Field(default_factory=list)
    evidence_count: int = 0
    progress_classification: str = "INSUFFICIENT_DATA"  # IMPROVING, STABLE, REGRESSING, RECOVERING, INSUFFICIENT_DATA
    regression_events: List[str] = Field(default_factory=list)
    recovery_events: List[str] = Field(default_factory=list)
    transfer_domains: List[str] = Field(default_factory=list)

    model_config = ConfigDict(populate_by_name=True)

class LearningStrategyProfile(BaseModel):
    strategy_id: str = Field(default_factory=lambda: f"strat_{int(datetime.now(timezone.utc).timestamp()*1000)}")
    person_id: str
    strategy_dimension: str  # PROJECT_BASED, PRACTICAL_DEBUGGING, THEORETICAL_READING, GUIDED_PROBLEM_SOLVING
    observed_attempts_count: int = 0
    successful_evaluations: int = 0
    effectiveness_status: str = "EMERGING"  # SUPPORTED, EMERGING, WEAKLY_SUPPORTED, OUTDATED
    supporting_event_ids: List[str] = Field(default_factory=list)
    first_observed: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    last_confirmed: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    model_config = ConfigDict(populate_by_name=True)

class RecurringMisconception(BaseModel):
    misconception_id: str = Field(default_factory=lambda: f"misc_{int(datetime.now(timezone.utc).timestamp()*1000)}")
    person_id: str
    concept_area: str
    description: str
    occurrence_count: int = 1
    trigger_event_ids: List[str] = Field(default_factory=list)
    remediation_strategy: str
    status: str = "ACTIVE"  # ACTIVE, RESOLVED, MONITORING
    detected_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    model_config = ConfigDict(populate_by_name=True)

class TurningPoint(BaseModel):
    turning_point_id: str = Field(default_factory=lambda: f"tp_{int(datetime.now(timezone.utc).timestamp()*1000)}")
    person_id: str
    event_type: str  # GOAL_TRANSITION, CAPABILITY_BREAKTHROUGH, MAJOR_RECOVERY, OPPORTUNITY_SELECTION, ROADMAP_TRANSFORMATION
    title: str
    what_happened: str
    why_significant: str
    what_changed_afterward: str
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    supporting_event_ids: List[str] = Field(default_factory=list)

    model_config = ConfigDict(populate_by_name=True)

class ProgressInsight(BaseModel):
    insight_id: str = Field(default_factory=lambda: f"ins_{int(datetime.now(timezone.utc).timestamp()*1000)}")
    person_id: str
    type: str  # GROWTH_OBSERVATION, STRATEGY_EFFECTIVENESS, RECOVERY_MILESTONE, TRANSFER_ACHIEVEMENT
    claim: str
    supporting_events: List[str] = Field(default_factory=list)
    supporting_evidence: List[str] = Field(default_factory=list)
    time_range: str = "Past 30 Days"
    confidence: str = "HIGH"  # HIGH, MEDIUM, LOW, INSUFFICIENT_EVIDENCE
    status: str = "ACTIVE"  # ACTIVE, SUPERSEDED, DISPUTED
    dispute_reason: Optional[str] = None
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    model_config = ConfigDict(populate_by_name=True)

class TemporalQueryResponse(BaseModel):
    query_text: str
    answer: str
    status: str = "ANSWERED"  # ANSWERED, INSUFFICIENT_HISTORY, INSUFFICIENT_EVIDENCE
    supporting_event_ids: List[str] = Field(default_factory=list)
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    model_config = ConfigDict(populate_by_name=True)

class LongitudinalLearnerState(BaseModel):
    person_id: str
    current_state_summary: Dict[str, Any] = Field(default_factory=dict)
    capability_history: List[CapabilityEvolutionRecord] = Field(default_factory=list)
    goal_history: List[Dict[str, Any]] = Field(default_factory=list)
    roadmap_evolution: List[Dict[str, Any]] = Field(default_factory=list)
    decision_history: List[Dict[str, Any]] = Field(default_factory=list)
    strategy_profiles: List[LearningStrategyProfile] = Field(default_factory=list)
    recurring_misconceptions: List[RecurringMisconception] = Field(default_factory=list)
    turning_points: List[TurningPoint] = Field(default_factory=list)
    historical_then_transition_now_next: Dict[str, Any] = Field(default_factory=dict)
    last_updated: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    model_config = ConfigDict(populate_by_name=True)
