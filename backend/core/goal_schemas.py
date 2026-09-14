from enum import Enum
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
from pydantic import BaseModel, Field, ConfigDict

class GoalType(str, Enum):
    CAREER_ROLE = "CAREER_ROLE"
    CAREER_TRANSITION = "CAREER_TRANSITION"
    EDUCATION = "EDUCATION"
    CREDENTIAL = "CREDENTIAL"
    EXAM = "EXAM"
    ENTREPRENEURSHIP = "ENTREPRENEURSHIP"
    RESEARCH = "RESEARCH"
    COMPETENCY = "COMPETENCY"
    PROFESSIONAL_OUTCOME = "PROFESSIONAL_OUTCOME"
    OTHER = "OTHER"

class GoalStatus(str, Enum):
    ACTIVE = "ACTIVE"
    RESOLVED = "RESOLVED"
    NEEDS_USER_INPUT = "NEEDS_USER_INPUT"
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"
    GOAL_NOT_RESOLVED = "GOAL_NOT_RESOLVED"
    NO_VERIFIED_PATH = "NO_VERIFIED_PATH"
    SOURCE_UNAVAILABLE = "SOURCE_UNAVAILABLE"

class CanonicalGoal(BaseModel):
    """
    Canonical Goal Model for PATHMIND.
    Truly goal-conditioned and domain-agnostic.
    """
    goal_id: str
    person_id: str
    raw_user_goal: str
    normalized_goal: str
    goal_type: GoalType = GoalType.CAREER_ROLE
    target_domain: Optional[str] = None
    target_subfield: Optional[str] = None
    target_role: Optional[str] = None
    target_outcome: str
    geography: Optional[str] = "India & Global"
    timeline: Optional[str] = None
    constraints: Dict[str, Any] = Field(default_factory=dict)
    motivation: Optional[str] = None
    confidence: str = "HIGH"  # HIGH, MEDIUM, LOW, INSUFFICIENT_EVIDENCE, GOAL_NOT_RESOLVED
    provenance: Dict[str, Any] = Field(default_factory=dict)
    status: GoalStatus = GoalStatus.RESOLVED
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    model_config = ConfigDict(populate_by_name=True)

class GoalResolutionRequest(BaseModel):
    raw_intent: str
    geography: Optional[str] = "India & Global"
    timeline: Optional[str] = None
    constraints: Optional[Dict[str, Any]] = None
    motivation: Optional[str] = None

class GoalResolutionResponse(BaseModel):
    resolved_goal: Optional[CanonicalGoal] = None
    status: GoalStatus
    message: str
    suggested_clarifications: List[str] = Field(default_factory=list)
    confidence: str = "HIGH"
    provenance: Dict[str, Any] = Field(default_factory=dict)
