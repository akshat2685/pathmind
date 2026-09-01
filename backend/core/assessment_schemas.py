from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field, ConfigDict
from datetime import datetime, timezone

class AssessmentItem(BaseModel):
    id: str
    construct_name: str = Field(..., alias="construct")
    text: str
    response_type: str = "likert"  # likert, open, multiple_choice, task
    scale: Optional[List[Dict[str, Any]]] = None  # e.g. [{"value": 1, "label": "Strongly Dislike"}, ...]
    task_prompt: Optional[str] = None
    expected_capability: Optional[str] = None

    model_config = ConfigDict(populate_by_name=True)

class AssessmentDefinition(BaseModel):
    id: str
    name: str
    version: str
    construct_domain: str = Field(..., alias="construct")
    source: str
    license: str
    limitations: str
    items: List[AssessmentItem]
    scoring_method: str
    interpretation_rules: str

    model_config = ConfigDict(populate_by_name=True)

class AssessmentResponse(BaseModel):
    item_id: str
    response_value: Any
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

class AssessmentDraft(BaseModel):
    person_id: str
    assessment_id: str
    responses: List[AssessmentResponse]
    last_updated: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    is_completed: bool = False

class AssessmentResult(BaseModel):
    person_id: str
    assessment_id: str
    version: str
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    raw_responses: List[AssessmentResponse]
    calculated_scores: Dict[str, Any]
    dimension_scores: Optional[Dict[str, float]] = None

class CounselingFact(BaseModel):
    category: str  # OBSERVED, ASSESSED, INFERRED, UNKNOWN, RECOMMENDATION, EVIDENCE_GAP
    claim: str
    evidence: List[str] = Field(default_factory=list)
    confidence: str = "MEDIUM"  # HIGH, MEDIUM, LOW, INSUFFICIENT_EVIDENCE
    weight: Optional[float] = 1.0
    source: Optional[str] = None

class Contradiction(BaseModel):
    reported_preference: str
    observed_evidence: str
    suggested_clarification: str

class CandidateDirection(BaseModel):
    title: str
    rationale: str
    alignment: str
    related_occupations: List[str] = Field(default_factory=list)
    confidence: str = "MEDIUM"

class CounselingProfile(BaseModel):
    person_id: str
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    is_preliminary: bool = True
    interest_vector: Dict[str, float] = Field(default_factory=dict)
    strongest_interests: List[str] = Field(default_factory=list)
    weaker_interests: List[str] = Field(default_factory=list)
    
    # Granular SCCT & Observational Fact Lists
    academic_strengths: List[CounselingFact] = Field(default_factory=list)
    academic_weaknesses: List[CounselingFact] = Field(default_factory=list)
    demonstrated_capabilities: List[CounselingFact] = Field(default_factory=list)
    demonstrated_experience: List[CounselingFact] = Field(default_factory=list)
    self_efficacy_signals: List[CounselingFact] = Field(default_factory=list)
    outcome_expectations: List[CounselingFact] = Field(default_factory=list)
    contextual_barriers: List[CounselingFact] = Field(default_factory=list)
    contextual_supports: List[CounselingFact] = Field(default_factory=list)
    learning_signals: List[CounselingFact] = Field(default_factory=list)
    
    # Backwards-compatible and synthesized summaries
    strengths: List[CounselingFact] = Field(default_factory=list)
    interest_patterns: List[CounselingFact] = Field(default_factory=list)
    capability_signals: List[CounselingFact] = Field(default_factory=list)
    constraints: List[CounselingFact] = Field(default_factory=list)
    contradictions: List[Contradiction] = Field(default_factory=list)
    unknowns: List[str] = Field(default_factory=list)
    evidence_gaps: List[str] = Field(
        default_factory=list,
        description="Crucial portfolio, transcripts, or verifiable proof items that the candidate must provide."
    )
    candidate_directions: List[str] = Field(default_factory=list)
    candidate_direction_details: Optional[List[CandidateDirection]] = Field(default_factory=list)
    next_questions: List[str] = Field(default_factory=list)
    overall_confidence: str = "MEDIUM"

class CounselingMemoryItem(BaseModel):
    fact_id: str
    person_id: str
    category: str
    claim: str
    evidence: List[str]
    confidence: str
    recorded_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

class CounselingMessage(BaseModel):
    role: str  # "user" | "counselor"
    content: str
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

class CounselingChatRequest(BaseModel):
    person_id: str = "demo-user"
    message: str
    history: Optional[List[CounselingMessage]] = None
