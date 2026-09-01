from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field, ConfigDict
from datetime import datetime, timezone

class Resource(BaseModel):
    title: str
    url: str
    resource_type: str = "DOCUMENTATION"  # COURSE, DOCUMENTATION, VIDEO, BOOK, EXERCISE, PROJECT, PAPER, PLATFORM
    estimated_duration: str = "1–2 hours"
    provenance: str = "Official Open Source / Verified Provider"
    is_free: bool = True

    model_config = ConfigDict(populate_by_name=True)

class Mission(BaseModel):
    mission_id: str
    stage_id: str
    objective: str
    why: str
    estimated_time: str = "3–5 hours"
    steps: List[str] = Field(default_factory=list)
    resources: List[Resource] = Field(default_factory=list)
    evidence_requirements: List[str] = Field(default_factory=list)
    completion_criteria: str
    status: str = "ACTIVE"  # ACTIVE, COMPLETED, PENDING, REINFORCING

    model_config = ConfigDict(populate_by_name=True)

class Stage(BaseModel):
    stage_id: str
    phase_id: str
    stage_number: int
    title: str
    objective: str
    skills: List[str] = Field(default_factory=list)
    prerequisites: List[str] = Field(default_factory=list)
    missions: List[Mission] = Field(default_factory=list)
    resources: List[Resource] = Field(default_factory=list)
    evidence_requirements: List[str] = Field(default_factory=list)
    completion_rules: Dict[str, Any] = Field(default_factory=dict)
    estimated_effort: str = "1–2 Weeks"
    fallback_strategy: str = "Review core concept fundamentals and re-attempt guided practical task."
    locked: bool = True
    status: str = "LOCKED"  # LOCKED, ACTIVE, COMPLETED, REINFORCEMENT

    model_config = ConfigDict(populate_by_name=True)

class RoadmapPhase(BaseModel):
    phase_id: str
    title: str
    description: str
    stages: List[Stage] = Field(default_factory=list)

    model_config = ConfigDict(populate_by_name=True)

class Roadmap(BaseModel):
    roadmap_id: str
    person_id: str
    path_id: str
    version: int = 1
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    target_outcome: str
    phases: List[RoadmapPhase] = Field(default_factory=list)
    current_stage_id: str
    current_mission_id: Optional[str] = None
    total_stages: int = 0
    completed_stages: int = 0
    checkpoint_interval: int = 5
    revision_reason: str = "Initial personalized synthesis from selected pathway."
    constraints: Dict[str, Any] = Field(default_factory=dict)

    model_config = ConfigDict(populate_by_name=True)

class EvidenceSubmission(BaseModel):
    submission_id: str = Field(default_factory=lambda: f"sub_{int(datetime.now(timezone.utc).timestamp()*1000)}")
    person_id: str
    roadmap_id: str
    stage_id: str
    mission_id: Optional[str] = None
    evidence_type: str = "CODE_REPO"  # CODE_REPO, PROJECT_DEMO, EXPLANATION, QUIZ, TASK_ARTIFACT
    content_payload: Dict[str, Any] = Field(default_factory=dict)
    submitted_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    model_config = ConfigDict(populate_by_name=True)

class MasteryDimensions(BaseModel):
    understanding: float = 85.0
    application: float = 80.0
    transfer: float = 75.0
    accuracy: float = 90.0
    explanation: float = 85.0

    model_config = ConfigDict(populate_by_name=True)

class EvaluationResult(BaseModel):
    submission_id: str
    stage_id: str
    mission_id: Optional[str] = None
    status: str = "PASS"  # PASS, REINFORCE, INSUFFICIENT_EVIDENCE
    mastery_dimensions: MasteryDimensions = Field(default_factory=MasteryDimensions)
    demonstrated: List[str] = Field(default_factory=list)
    missing: List[str] = Field(default_factory=list)
    feedback: str
    recommended_next_action: str
    confidence: str = "HIGH"  # HIGH, MEDIUM, LOW
    evaluated_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    model_config = ConfigDict(populate_by_name=True)

class LearningEvent(BaseModel):
    event_id: str = Field(default_factory=lambda: f"event_{int(datetime.now(timezone.utc).timestamp()*1000)}")
    person_id: str
    stage_id: str
    topic: str
    event_type: str = "MASTERY_DEMONSTRATED"  # CONCEPTUAL_BREAKTHROUGH, RECURRING_MISCONCEPTION, FORMAT_PREFERENCE, PACE_CHANGE, MASTERY_DEMONSTRATED
    observation: str
    intervention: str
    result: str
    learning_signal: str
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    model_config = ConfigDict(populate_by_name=True)

class LongitudinalMemory(BaseModel):
    memory_id: str = Field(default_factory=lambda: f"mem_{int(datetime.now(timezone.utc).timestamp()*1000)}")
    person_id: str
    concept: str
    context: str
    stage_learned: str
    confidence: str = "HIGH"  # HIGH, MEDIUM, LOW
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    model_config = ConfigDict(populate_by_name=True)

class PersonalAgentModel(BaseModel):
    person_id: str
    version: int = 1
    learning_preferences: Dict[str, Any] = Field(default_factory=lambda: {
        "preferred_format": "project-based",
        "weekly_hours": 10,
        "explanation_style": "practical-code-first"
    })
    strengths: List[str] = Field(default_factory=list)
    weaknesses: List[str] = Field(default_factory=list)
    recurring_misconceptions: List[str] = Field(default_factory=list)
    successful_interventions: List[str] = Field(default_factory=list)
    unsuccessful_interventions: List[str] = Field(default_factory=list)
    pace: str = "NORMAL"  # ACCELERATED, NORMAL, REINFORCED
    skill_evidence: Dict[str, str] = Field(default_factory=dict)
    longitudinal_memories: List[LongitudinalMemory] = Field(default_factory=list)
    updated_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    model_config = ConfigDict(populate_by_name=True)

class AdaptConstraintRequest(BaseModel):
    person_id: str
    weekly_hours: Optional[int] = None
    preferred_format: Optional[str] = None
    notes: Optional[str] = None

    model_config = ConfigDict(populate_by_name=True)

class DisclosedStageView(BaseModel):
    stage_id: str
    phase_id: str
    stage_number: int
    title: str
    objective: str
    skills: List[str] = Field(default_factory=list)
    estimated_effort: str
    locked: bool
    status: str
    # Revealed only when NOT locked:
    current_mission: Optional[Mission] = None
    resources: List[Resource] = Field(default_factory=list)
    evidence_requirements: List[str] = Field(default_factory=list)

    model_config = ConfigDict(populate_by_name=True)

class DisclosedRoadmapView(BaseModel):
    roadmap_id: str
    person_id: str
    path_id: str
    version: int
    target_outcome: str
    current_stage_id: str
    total_stages: int
    completed_stages: int
    overall_progress_percent: float
    stages: List[DisclosedStageView] = Field(default_factory=list)
    active_stage: Optional[Stage] = None
    active_mission: Optional[Mission] = None
    personal_agent_note: Optional[str] = None
    memory_moment: Optional[Dict[str, Any]] = None

    model_config = ConfigDict(populate_by_name=True)
