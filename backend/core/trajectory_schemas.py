from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field, ConfigDict
from datetime import datetime, timezone

class SkillGap(BaseModel):
    skill_name: str
    category: str = "CORE"  # FOUNDATIONAL, CORE, SPECIALIZED, EXPERIENCE, EVIDENCE, CREDENTIAL
    current_status: str = "MISSING"  # HELD, PARTIAL, MISSING
    description: str
    recommended_action: str

    model_config = ConfigDict(populate_by_name=True)

class EducationRoute(BaseModel):
    route_type: str = "TRADITIONAL_DEGREE"  # TRADITIONAL_DEGREE, PROJECT_BASED_ACCELERATED, DEGREE_PLUS_SPECIALIZATION, VOCATIONAL_DIRECT
    title: str
    description: str
    estimated_duration: str
    institutions_or_paths: List[str] = Field(default_factory=list)
    geographic_relevance: str = "Hybrid"  # India, Global, Hybrid

    model_config = ConfigDict(populate_by_name=True)

class CredentialOption(BaseModel):
    title: str
    issuer: str
    classification: str = "STRONGLY_USEFUL"  # MANDATORY, STRONGLY_USEFUL, OPTIONAL, LOW_VALUE
    purpose: str
    prerequisites: List[str] = Field(default_factory=list)
    verified_cost: Optional[str] = None
    preparation_effort: str = "Moderate"
    official_url: Optional[str] = None
    provenance: Optional[str] = None

    model_config = ConfigDict(populate_by_name=True)

class TrajectoryCase(BaseModel):
    trajectory_id: str
    title: str
    archetype: str
    source_type: str = "DEMO_ATTRIBUTED"  # DEMO_ATTRIBUTED, ATTRIBUTED_CASE_STUDY
    starting_conditions: Dict[str, Any] = Field(default_factory=dict)
    learning_milestones: List[str] = Field(default_factory=list)
    major_transitions: List[str] = Field(default_factory=list)
    obstacles_and_failures: List[str] = Field(default_factory=list)
    outcome_role: str
    similarity_rationale: str
    important_differences: str

    model_config = ConfigDict(populate_by_name=True)

class TrajectoryPattern(BaseModel):
    pattern_title: str
    description: str
    evidence_trajectories_count: int
    evidence_summary: str
    confidence: str = "MEDIUM"  # HIGH, MEDIUM, LOW

    model_config = ConfigDict(populate_by_name=True)

class CandidatePath(BaseModel):
    path_id: str
    title: str
    domain: str
    description: str
    fit_score: float
    fit_level: str = "STRONG"  # HIGH, STRONG, MODERATE
    confidence: str = "HIGH"  # HIGH, MEDIUM, LOW, INSUFFICIENT_EVIDENCE
    
    # Explainability & Evidence
    why_it_matches: List[str] = Field(default_factory=list)
    supporting_evidence: List[str] = Field(default_factory=list)
    missing_evidence: List[str] = Field(default_factory=list)
    
    # Skills Breakdown
    required_skills: List[str] = Field(default_factory=list)
    current_skills_held: List[str] = Field(default_factory=list)
    transferable_skills: List[str] = Field(default_factory=list)
    skill_gaps: List[SkillGap] = Field(default_factory=list)
    
    # Routes & Credentials
    education_routes: List[EducationRoute] = Field(default_factory=list)
    credential_options: List[CredentialOption] = Field(default_factory=list)
    
    # Geographic Context
    india_context: Dict[str, Any] = Field(default_factory=dict)
    global_context: Dict[str, Any] = Field(default_factory=dict)
    
    # Trade-offs
    experience_requirements: List[str] = Field(default_factory=list)
    advantages: List[str] = Field(default_factory=list)
    disadvantages: List[str] = Field(default_factory=list)
    risks: List[str] = Field(default_factory=list)
    alternatives: List[str] = Field(default_factory=list)
    
    # Empirical Grounding & Provenance
    similar_trajectories: List[TrajectoryCase] = Field(default_factory=list)
    source_references: List[Dict[str, Any]] = Field(default_factory=list)

    model_config = ConfigDict(populate_by_name=True)

class DiscoveryRequest(BaseModel):
    person_id: str = "demo-user"
    goals: Optional[List[str]] = Field(default_factory=list)
    constraints: Optional[List[str]] = Field(default_factory=list)
    geographic_preference: Optional[str] = "India & Global"

    model_config = ConfigDict(populate_by_name=True)

class DiscoveryResponse(BaseModel):
    person_id: str
    target_domain_decomposed: str
    candidate_paths: List[CandidatePath]
    extracted_patterns: List[TrajectoryPattern] = Field(default_factory=list)
    overall_reasoning: str
    generated_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    model_config = ConfigDict(populate_by_name=True)

class CounterfactualRequest(BaseModel):
    person_id: str = "demo-user"
    base_path_id: str
    modification_type: str = "CUSTOM"  # LOW_BUDGET, SELF_PACED_5_HOURS, ACCELERATED_NON_DEGREE, GLOBAL_MIGRATION, CUSTOM
    modification_prompt: str

    model_config = ConfigDict(populate_by_name=True)

class CounterfactualResponse(BaseModel):
    base_path_id: str
    modification_applied: str
    adjusted_path: CandidatePath
    trade_off_notes: List[str] = Field(default_factory=list)
    generated_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    model_config = ConfigDict(populate_by_name=True)

class PathSelectionRecord(BaseModel):
    version: int = 1
    person_id: str
    selected_path_id: str
    selected_path: CandidatePath
    all_candidate_paths: List[CandidatePath] = Field(default_factory=list)
    selection_reason: Optional[str] = None
    selected_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    model_config = ConfigDict(populate_by_name=True)
