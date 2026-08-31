from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from datetime import datetime

class AssessmentItem(BaseModel):
    id: str
    construct: str
    text: str
    response_type: str = "likert" # likert, open, boolean, etc.
    scale: Optional[List[Dict[str, Any]]] = None # e.g. [{"value": 1, "label": "Strongly Dislike"}, ...]

class AssessmentDefinition(BaseModel):
    id: str
    name: str
    version: str
    construct: str
    source: str
    license: str
    limitations: str
    items: List[AssessmentItem]
    scoring_method: str
    interpretation_rules: str

class AssessmentResponse(BaseModel):
    item_id: str
    response_value: Any
    timestamp: str

class AssessmentResult(BaseModel):
    person_id: str
    assessment_id: str
    version: str
    timestamp: str
    raw_responses: List[AssessmentResponse]
    calculated_scores: Dict[str, Any]

class CounselingFact(BaseModel):
    category: str # OBSERVED, ASSESSED, INFERRED, UNKNOWN, EVIDENCE_GAP, RECOMMENDATION
    claim: str
    evidence: List[str]
    confidence: str # HIGH, MEDIUM, LOW, INSUFFICIENT_EVIDENCE

class Contradiction(BaseModel):
    reported_preference: str
    observed_evidence: str
    suggested_clarification: str

class CounselingProfile(BaseModel):
    person_id: str
    timestamp: str
    strengths: List[CounselingFact]
    interest_patterns: List[CounselingFact]
    capability_signals: List[CounselingFact]
    constraints: List[CounselingFact]
    unknowns: List[str]
    candidate_directions: List[str]
    contradictions: List[Contradiction]
    next_questions: List[str]
    evidence_gaps: Optional[List[str]] = Field(
        default_factory=list,
        description="Crucial portfolio, transcripts, or verifiable proof items that the candidate must provide."
    )
