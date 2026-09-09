from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field, ConfigDict
from datetime import datetime, timezone

class EducationItem(BaseModel):
    degree: str
    field_of_study: str
    institution: str
    year: Optional[str] = None
    grade_or_score: Optional[str] = None
    is_verified: bool = True

    model_config = ConfigDict(populate_by_name=True)

class ExperienceItem(BaseModel):
    role: str
    organization: str
    duration: str
    description: str
    skills_used: List[str] = Field(default_factory=list)
    is_verified: bool = True

    model_config = ConfigDict(populate_by_name=True)

class ProjectItem(BaseModel):
    title: str
    technologies: List[str] = Field(default_factory=list)
    description: str
    repository_url: Optional[str] = None
    live_url: Optional[str] = None
    provenance: str = "Self-reported or Verified in Roadmap Milestone"
    is_verified: bool = True

    model_config = ConfigDict(populate_by_name=True)

class CredentialItem(BaseModel):
    title: str
    issuer: str
    issue_date: Optional[str] = None
    credential_id: Optional[str] = None
    verification_url: Optional[str] = None
    is_verified: bool = True

    model_config = ConfigDict(populate_by_name=True)

class UniversalCareerProfile(BaseModel):
    """
    Canonical single-source-of-truth profile for a person.
    Supports students, graduates, researchers, working professionals, and career switchers without fragmentation.
    """
    person_id: str
    current_role: str = "Student / Aspiring Technologist"
    current_state_type: str = "college_student"  # school_student, college_student, graduate, working_professional, career_switcher, researcher, founder
    education: List[EducationItem] = Field(default_factory=list)
    experience: List[ExperienceItem] = Field(default_factory=list)
    skills: List[str] = Field(default_factory=list)
    projects: List[ProjectItem] = Field(default_factory=list)
    credentials: List[CredentialItem] = Field(default_factory=list)
    portfolio_links: List[str] = Field(default_factory=list)
    achievements: List[str] = Field(default_factory=list)
    current_country: str = "India"
    current_city: str = "Bengaluru"
    target_country: str = "India & Global"
    target_city: Optional[str] = None
    remote_preference: str = "HYBRID"  # REMOTE, HYBRID, ONSITE, ANY
    work_authorization: str = "Citizen (India)"
    goals: List[str] = Field(default_factory=list)
    constraints: Dict[str, Any] = Field(default_factory=dict)
    last_updated: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    model_config = ConfigDict(populate_by_name=True)

class TargetOutcome(BaseModel):
    """
    Structured target definition for career aspirations.
    """
    goal_id: str
    person_id: str
    goal_type: str = "career"  # career, internship, certification, promotion, graduate_program, career_transition, entrepreneurship, research
    target_role: str = "Applied Machine Learning Systems Engineer"
    target_industry: str = "Artificial Intelligence & Software Engineering"
    geography: str = "India & Global"
    target_timeline: Optional[str] = "12–18 Months"
    priority: str = "HIGH"  # HIGH, MEDIUM, LOW
    version: int = 1
    constraints: Dict[str, Any] = Field(default_factory=dict)
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    model_config = ConfigDict(populate_by_name=True)

# Alias for backwards compatibility
CareerGoal = TargetOutcome

class RequirementNode(BaseModel):
    name: str
    category: str  # CORE_SKILL, SUPPORTING_SKILL, EDUCATION, CREDENTIAL, EXPERIENCE, PROJECT_EVIDENCE, PORTFOLIO_EVIDENCE, ELIGIBILITY, MARKET_CONTEXT
    importance: str = "HIGH"  # HIGH, MEDIUM, LOW
    description: str
    source: str = "ESCO / NCO Official Occupational Standards"
    status_for_person: str = "MISSING"  # AVAILABLE, TRANSFERABLE, MISSING, UNCERTAIN

    model_config = ConfigDict(populate_by_name=True)

class CareerRequirementGraph(BaseModel):
    """
    Structured representation of all verified prerequisites and requirements for a target role.
    """
    target_role: str
    target_industry: str
    source_standards: List[str] = Field(default_factory=list)
    core_skills: List[RequirementNode] = Field(default_factory=list)
    supporting_skills: List[RequirementNode] = Field(default_factory=list)
    education_requirements: List[RequirementNode] = Field(default_factory=list)
    credential_recommendations: List[RequirementNode] = Field(default_factory=list)
    experience_requirements: List[RequirementNode] = Field(default_factory=list)
    project_evidence_requirements: List[RequirementNode] = Field(default_factory=list)
    eligibility_criteria: List[RequirementNode] = Field(default_factory=list)
    market_context_notes: List[str] = Field(default_factory=list)
    generated_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    model_config = ConfigDict(populate_by_name=True)

class CategorizedGap(BaseModel):
    gap_id: str
    gap_type: str  # SKILL, EXPERIENCE, EVIDENCE, EDUCATION, CREDENTIAL, PORTFOLIO, ELIGIBILITY, EXPOSURE
    title: str
    description: str
    importance: str = "HIGH"  # HIGH, MEDIUM, LOW
    source: str = "Requirement Graph Comparison"
    reason: str = "Required for target baseline competencies."
    recommended_action: str

    model_config = ConfigDict(populate_by_name=True)

class TransferableSkillsAnalysis(BaseModel):
    already_have: List[str] = Field(default_factory=list)
    can_transfer: List[str] = Field(default_factory=list)
    need_to_develop: List[str] = Field(default_factory=list)
    analysis_summary: str

    model_config = ConfigDict(populate_by_name=True)

class VerifiedCredential(BaseModel):
    credential_id: str
    title: str
    issuer: str
    classification: str = "STRONGLY_USEFUL"  # MANDATORY, STRONGLY_USEFUL, OPTIONAL, LOW_VALUE, NOT_RELEVANT
    target_roles: List[str] = Field(default_factory=list)
    prerequisites: List[str] = Field(default_factory=list)
    preparation_effort: str = "8–12 Weeks"
    verified_cost: Optional[str] = None
    geographic_relevance: str = "Global"
    official_url: str
    source: str = "Verified Industry Standard"
    strategic_advice: str = "Focus on verifiable GitHub project repositories before paying for standalone certifications."
    decision_rationale: str = "Evaluated against target role requirement graph."
    last_verified: str = "2026-09-01"

    model_config = ConfigDict(populate_by_name=True)

class ExperienceGap(BaseModel):
    gap_id: str
    experience_type: str  # PROJECT, INTERNSHIP, RESEARCH, FREELANCE, OPEN_SOURCE, LEADERSHIP, INTERNAL_EXPERIENCE
    title: str
    why_it_matters: str
    how_to_obtain: str
    evidence_to_prove: str
    associated_roadmap_stage: Optional[str] = None

    model_config = ConfigDict(populate_by_name=True)

class EvidenceRequirementStatus(BaseModel):
    requirement: str
    category: str  # SKILL, PROJECT, WORK, RESEARCH, CERTIFICATION, PORTFOLIO, ACHIEVEMENT
    status: str = "MISSING"  # SATISFIED, PARTIALLY_SATISFIED, MISSING, UNKNOWN
    grounding_evidence: List[str] = Field(default_factory=list)

    model_config = ConfigDict(populate_by_name=True)

class EvidencePortfolio(BaseModel):
    person_id: str
    skill_evidence: List[EvidenceRequirementStatus] = Field(default_factory=list)
    project_evidence: List[EvidenceRequirementStatus] = Field(default_factory=list)
    work_evidence: List[EvidenceRequirementStatus] = Field(default_factory=list)
    research_evidence: List[EvidenceRequirementStatus] = Field(default_factory=list)
    certification_evidence: List[EvidenceRequirementStatus] = Field(default_factory=list)
    portfolio_evidence: List[EvidenceRequirementStatus] = Field(default_factory=list)
    achievement_evidence: List[EvidenceRequirementStatus] = Field(default_factory=list)
    updated_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    model_config = ConfigDict(populate_by_name=True)

class MarketContext(BaseModel):
    salary_range: Optional[str] = None
    employment_outlook: str = "Stable / High Growth"
    geography: str = "India & Global"
    data_period: str = "2025–2026"
    source: str = "ESCO / NCO / Verified Labor Analytics"
    retrieved_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    model_config = ConfigDict(populate_by_name=True)

class VerifiedOpportunity(BaseModel):
    opportunity_id: str
    title: str
    organization: str
    location: str
    employment_type: str = "INTERNSHIP"  # INTERNSHIP, FULL_TIME, APPRENTICESHIP, RESEARCH, FELLOWSHIP, GRADUATE
    eligibility: str
    required_skills: List[str] = Field(default_factory=list)
    preferred_skills: List[str] = Field(default_factory=list)
    deadline: str
    apply_url: str
    source: str = "Verified Official Career Portal / Open Source Program"
    retrieved_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    status: str = "ACTIVE"  # ACTIVE, EXPIRED, UPCOMING
    fit_level: str = "HIGH"  # HIGH, MEDIUM, LOW
    fit_reasons: List[str] = Field(default_factory=list)
    missing_requirements: List[str] = Field(default_factory=list)
    eligibility_blockers: List[str] = Field(default_factory=list)
    pre_application_advice: str = "Complete verified project repository before applying."
    market_context: Optional[MarketContext] = None

    model_config = ConfigDict(populate_by_name=True)

class TailoredResume(BaseModel):
    resume_id: str
    person_id: str
    target_role: str
    target_opportunity_id: Optional[str] = None
    summary: str
    highlighted_skills: List[str] = Field(default_factory=list)
    tailored_projects: List[Dict[str, Any]] = Field(default_factory=list)
    verified_experience: List[Dict[str, Any]] = Field(default_factory=list)
    education: List[Dict[str, Any]] = Field(default_factory=list)
    certifications: List[Dict[str, Any]] = Field(default_factory=list)
    provenance_map: Dict[str, str] = Field(default_factory=dict)
    ats_match_score: int = 85
    ats_matched_keywords: List[str] = Field(default_factory=list)
    ats_missing_keywords: List[str] = Field(default_factory=list)
    ats_recommendations: List[str] = Field(default_factory=list)
    fact_validation_status: str = "PASSED"  # PASSED, FAILED
    unsupported_claims_rejected: List[str] = Field(default_factory=list)
    generated_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    model_config = ConfigDict(populate_by_name=True)

class AccountabilityStatus(BaseModel):
    status: str = "ON_TRACK"  # ON_TRACK, AT_RISK, DELAYED, BLOCKED, COMPLETED, PAUSED, REPLANNING
    current_streak_days: int = 4
    weekly_commitment_hours: int = 10
    mentor_observation: str
    suggested_adjustment: Optional[str] = None
    next_checkpoint: str = "Friday Milestone Check-in"
    last_check_in: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    model_config = ConfigDict(populate_by_name=True)

class CareerCheckpoint(BaseModel):
    checkpoint_id: str
    person_id: str
    current_role_status: str
    target: str
    progress: str
    what_changed: str
    skills_gained: List[str] = Field(default_factory=list)
    remaining_gaps: List[str] = Field(default_factory=list)
    credential_status: str
    experience_status: str
    opportunity_readiness: str
    next_best_action: str
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    model_config = ConfigDict(populate_by_name=True)

class ReadinessTransitionRecord(BaseModel):
    from_state: str
    to_state: str
    trigger_evidence: str
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    model_config = ConfigDict(populate_by_name=True)

class CareerReadinessReport(BaseModel):
    person_id: str
    target_goal: TargetOutcome
    current_person_state: str = "college_student"
    readiness_state: str = "DEVELOPING"  # FOUNDATIONAL, DEVELOPING, INTERNSHIP_READY, ENTRY_LEVEL_READY, TRANSITION_READY, TARGET_READY, ADVANCED
    readiness_explanation: str
    next_readiness_milestone: str
    requirement_graph: Optional[CareerRequirementGraph] = None
    categorized_gaps: List[CategorizedGap] = Field(default_factory=list)
    transferable_skills: TransferableSkillsAnalysis
    credentials_strategy: List[VerifiedCredential] = Field(default_factory=list)
    experience_gaps: List[ExperienceGap] = Field(default_factory=list)
    evidence_portfolio: Optional[EvidencePortfolio] = None
    accountability: AccountabilityStatus
    matched_opportunities: List[VerifiedOpportunity] = Field(default_factory=list)
    tailored_resume_preview: Optional[TailoredResume] = None
    readiness_history: List[ReadinessTransitionRecord] = Field(default_factory=list)
    error_state: Optional[str] = None  # None, OPPORTUNITY_SOURCE_UNAVAILABLE, OPPORTUNITY_AUTH_REQUIRED, MARKET_DATA_UNAVAILABLE, CREDENTIAL_DATA_UNAVAILABLE, RESUME_FACT_VALIDATION_FAILED, READINESS_INSUFFICIENT
    generated_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    model_config = ConfigDict(populate_by_name=True)
