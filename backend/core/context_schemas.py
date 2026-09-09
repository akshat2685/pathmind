from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field, ConfigDict
from datetime import datetime, timezone

class ContextConflict(BaseModel):
    conflict_id: str = Field(default_factory=lambda: f"conf_{int(datetime.now(timezone.utc).timestamp()*1000)}")
    conflict_type: str  # GOAL_CONFLICT, EVIDENCE_CONFLICT, CONSTRAINT_CONFLICT, PROFILE_CONFLICT, OPPORTUNITY_CONFLICT, MEMORY_CONFLICT
    description: str
    source_a: str
    source_b: str
    status: str = "ACTIVE"  # ACTIVE, RESOLVED
    detected_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    resolution_note: Optional[str] = None

    model_config = ConfigDict(populate_by_name=True)

class DecisionRecord(BaseModel):
    decision_id: str = Field(default_factory=lambda: f"dec_{int(datetime.now(timezone.utc).timestamp()*1000)}")
    person_id: str
    decision_type: str  # CAREER_DIRECTION, ROADMAP_ADAPTATION, LEARNING_STRATEGY, OPPORTUNITY_CHOICE, EVALUATION_CHALLENGE, TARGET_ROLE_CHANGE
    title: str
    user_choice: str
    alternatives_considered: List[str] = Field(default_factory=list)
    supporting_evidence_ids: List[str] = Field(default_factory=list)
    context_snapshot_summary: Dict[str, Any] = Field(default_factory=dict)
    outcome_state: str = "PENDING"  # PENDING, POSITIVE, NEGATIVE, MIXED, SUPERSEDED
    outcome_note: Optional[str] = None
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    model_config = ConfigDict(populate_by_name=True)

class NextActionRecommendation(BaseModel):
    action_id: str = Field(default_factory=lambda: f"act_{int(datetime.now(timezone.utc).timestamp()*1000)}")
    action_title: str
    action_type: str  # COMPLETE_STAGE_EVIDENCE, REINFORCE_PREREQUISITE, APPLY_OPPORTUNITY, REVIEW_ADAPTATION, VERIFY_TRANSFER, REFRESH_SKILL, UPDATE_CONSTRAINTS
    priority: str = "NOW"  # NOW, NEXT, LATER, OPTIONAL
    target_stage_id: Optional[str] = None
    target_skill: Optional[str] = None
    target_opportunity_id: Optional[str] = None
    facts: List[str] = Field(default_factory=list)
    interpretation: List[str] = Field(default_factory=list)
    tradeoffs: List[str] = Field(default_factory=list)
    recommendation_rationale: str
    downstream_consequence: str

    model_config = ConfigDict(populate_by_name=True)

class PersonalContextGraph(BaseModel):
    person_id: str
    identity_context: Dict[str, Any] = Field(default_factory=dict)
    goal_context: Dict[str, Any] = Field(default_factory=dict)
    capability_context: Dict[str, Any] = Field(default_factory=dict)
    learning_context: Dict[str, Any] = Field(default_factory=dict)
    career_context: Dict[str, Any] = Field(default_factory=dict)
    constraint_context: Dict[str, Any] = Field(default_factory=dict)
    memory_context: List[Dict[str, Any]] = Field(default_factory=list)
    opportunity_context: List[Dict[str, Any]] = Field(default_factory=list)
    recent_decisions: List[DecisionRecord] = Field(default_factory=list)
    active_conflicts: List[ContextConflict] = Field(default_factory=list)
    last_materialized_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    model_config = ConfigDict(populate_by_name=True)

class CommandCenterOverview(BaseModel):
    person_id: str
    where_am_i: Dict[str, Any]
    where_am_i_going: Dict[str, Any]
    what_changed: Dict[str, Any]
    what_is_blocking_me: Optional[Dict[str, Any]] = None
    what_should_i_do_now: NextActionRecommendation
    what_happens_after_that: str
    recent_decisions: List[DecisionRecord] = Field(default_factory=list)
    active_conflicts: List[ContextConflict] = Field(default_factory=list)
    assembled_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    model_config = ConfigDict(populate_by_name=True)

class TaskContextPackage(BaseModel):
    task_type: str
    relevant_goal: str
    relevant_stage_id: Optional[str] = None
    relevant_skills: List[str] = Field(default_factory=list)
    verified_evidence_summaries: List[str] = Field(default_factory=list)
    active_constraints: Dict[str, Any] = Field(default_factory=dict)
    relevant_memories: List[str] = Field(default_factory=list)
    relevant_opportunities: List[str] = Field(default_factory=list)

    model_config = ConfigDict(populate_by_name=True)
