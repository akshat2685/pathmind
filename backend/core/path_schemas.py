from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field, ConfigDict
from datetime import datetime, timezone

class GoalFitEvaluation(BaseModel):
    """
    Evaluates goal validity independently of the person's current preparation (Step 3).
    """
    is_well_defined: bool = True
    is_resolvable: bool = True
    knowledge_supported: bool = True
    goal_type: str = "OCCUPATION"  # OCCUPATION, ENTREPRENEURSHIP, EDUCATION, EXAM, RESEARCH, COMPETENCY, PROFESSIONAL_OUTCOME
    resolved_title: str
    resolved_domain: str
    evaluation_summary: str

    model_config = ConfigDict(populate_by_name=True)

class PersonFitEvaluation(BaseModel):
    """
    Evaluates person alignment (interests, evidence, skills, experience, constraints) (Step 3).
    """
    alignment_level: str = "HIGH"  # HIGH, MEDIUM, LOW, INSUFFICIENT_EVIDENCE
    interest_signals: List[str] = Field(default_factory=list)
    verified_evidence_items: List[str] = Field(default_factory=list)
    held_skills: List[str] = Field(default_factory=list)
    transferable_assets: List[str] = Field(default_factory=list)
    constraints_addressed: List[str] = Field(default_factory=list)
    self_efficacy: Optional[str] = None
    evaluation_summary: str

    model_config = ConfigDict(populate_by_name=True)

class GapBurdenEvaluation(BaseModel):
    """
    Evaluates preparation gaps without penalizing the intrinsic validity of the goal (Step 3).
    """
    burden_level: str = "MEDIUM"  # HIGH, MEDIUM, LOW, INSUFFICIENT_EVIDENCE
    skill_gaps: List[str] = Field(default_factory=list)
    credential_gaps: List[str] = Field(default_factory=list)
    education_gaps: List[str] = Field(default_factory=list)
    experience_gaps: List[str] = Field(default_factory=list)
    evidence_gaps: List[str] = Field(default_factory=list)
    evaluation_summary: str

    model_config = ConfigDict(populate_by_name=True)

class FeasibilityEvaluation(BaseModel):
    """
    Evaluates practical execution feasibility against real constraints (Step 3 & 16).
    """
    feasibility_level: str = "HIGH"  # HIGH, MEDIUM, LOW, UNCERTAIN
    time_feasible: bool = True
    cost_feasible: bool = True
    geographic_feasible: bool = True
    prerequisite_feasible: bool = True
    notes: List[str] = Field(default_factory=list)

    model_config = ConfigDict(populate_by_name=True)

class UncertaintyEvaluation(BaseModel):
    """
    Evaluates missing evidence, ambiguous goals, and unsupported occupations (Step 3 & 21).
    """
    uncertainty_level: str = "LOW"  # HIGH, MEDIUM, LOW
    missing_evidence_factors: List[str] = Field(default_factory=list)
    ambiguities: List[str] = Field(default_factory=list)
    conflicting_information: List[str] = Field(default_factory=list)

    model_config = ConfigDict(populate_by_name=True)

class CanonicalPath(BaseModel):
    """
    Canonical Path Model for PATHMIND (Step 2).
    Captures defensible paths from current state to target outcome without generic numeric scores.
    """
    path_id: str
    person_id: str
    goal_id: Optional[str] = None
    title: str
    domain: str
    subfield: Optional[str] = None
    target_outcome: str
    fit_summary: str
    alignment_factors: List[str] = Field(default_factory=list)
    tradeoffs: List[str] = Field(default_factory=list)
    requirements: List[str] = Field(default_factory=list)
    gaps: List[str] = Field(default_factory=list)
    transferable_assets: List[str] = Field(default_factory=list)
    new_learning_required: List[str] = Field(default_factory=list)
    credential_requirements: List[str] = Field(default_factory=list)
    education_requirements: List[str] = Field(default_factory=list)
    experience_requirements: List[str] = Field(default_factory=list)
    evidence_requirements: List[str] = Field(default_factory=list)
    constraints: Dict[str, Any] = Field(default_factory=dict)
    geography: str = "India & Global"
    timeline: str = "TIMELINE_UNCERTAIN"  # Derived timeline or explicit uncertainty
    confidence: str = "HIGH"  # HIGH, MEDIUM, LOW, INSUFFICIENT_EVIDENCE
    provenance: str = "ESCO / NCO / Verified Industry Benchmark"
    source_references: List[str] = Field(default_factory=list)
    status: str = "RECOMMENDED"  # RECOMMENDED, EXPLORING, ACTIVE, REJECTED, ARCHIVED

    # Separated evaluations (Step 3)
    goal_fit: Optional[GoalFitEvaluation] = None
    person_fit: Optional[PersonFitEvaluation] = None
    gap_burden: Optional[GapBurdenEvaluation] = None
    feasibility: Optional[FeasibilityEvaluation] = None
    uncertainty: Optional[UncertaintyEvaluation] = None

    # Transparent explainability package (Step 18)
    explainability: Dict[str, Any] = Field(default_factory=dict)
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    model_config = ConfigDict(populate_by_name=True)
