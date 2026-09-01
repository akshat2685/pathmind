from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field, ConfigDict
from datetime import datetime, timezone

class CareerGoal(BaseModel):
    goal_id: str
    person_id: str
    goal_type: str = "career"  # career, internship, certification, promotion, education, career_transition, research, entrepreneurship, skill_acquisition
    target_role: str
    target_industry: str = "Artificial Intelligence & Software Engineering"
    geography: str = "India & Global"
    target_timeline: Optional[str] = "12–18 Months"
    priority: str = "HIGH"  # HIGH, MEDIUM, LOW
    constraints: Dict[str, Any] = Field(default_factory=dict)
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    model_config = ConfigDict(populate_by_name=True)

class CategorizedGap(BaseModel):
    gap_id: str
    gap_type: str  # SKILL_GAP, EXPERIENCE_GAP, EVIDENCE_GAP, EDUCATION_GAP, CREDENTIAL_GAP, PORTFOLIO_GAP, ELIGIBILITY_GAP
    title: str
    description: str
    severity: str = "HIGH"  # HIGH, MEDIUM, LOW
    recommended_action: str

    model_config = ConfigDict(populate_by_name=True)

class TransferableSkillsAnalysis(BaseModel):
    already_have: List[str] = Field(default_factory=list)
    can_reuse: List[str] = Field(default_factory=list)
    need_to_build: List[str] = Field(default_factory=list)
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
    last_verified: str = "2026-09-01"

    model_config = ConfigDict(populate_by_name=True)

class AccountabilityStatus(BaseModel):
    status: str = "ON_TRACK"  # ON_TRACK, AT_RISK, DELAYED, BLOCKED, COMPLETED, PAUSED, REPLANNING
    current_streak_days: int = 4
    weekly_commitment_hours: int = 10
    mentor_observation: str
    suggested_adjustment: Optional[str] = None
    next_checkpoint: str = "Friday Check-in"
    last_check_in: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    model_config = ConfigDict(populate_by_name=True)

class VerifiedOpportunity(BaseModel):
    opportunity_id: str
    title: str
    organization: str
    location: str
    employment_type: str = "INTERNSHIP"  # INTERNSHIP, ENTRY_LEVEL, FULL_TIME, FELLOWSHIP
    eligibility: str
    required_skills: List[str] = Field(default_factory=list)
    preferred_skills: List[str] = Field(default_factory=list)
    deadline: str
    apply_url: str
    source: str = "Verified Employer / Official Career Portal"
    fit_level: str = "HIGH"  # HIGH, MEDIUM, LOW
    fit_reasons: List[str] = Field(default_factory=list)
    missing_requirements: List[str] = Field(default_factory=list)
    retrieved_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

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
    ats_match_score: int = 88
    ats_matched_keywords: List[str] = Field(default_factory=list)
    ats_missing_keywords: List[str] = Field(default_factory=list)
    ats_recommendations: List[str] = Field(default_factory=list)
    generated_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    model_config = ConfigDict(populate_by_name=True)

class CareerReadinessReport(BaseModel):
    person_id: str
    target_goal: CareerGoal
    current_person_state: str = "college_student"  # school_student, college_student, graduate, working_professional, career_switcher, founder, researcher, lifelong_learner
    readiness_state: str = "DEVELOPING"  # NOT_READY, FOUNDATIONAL, DEVELOPING, INTERNSHIP_READY, ENTRY_LEVEL_READY, TARGET_READY, ADVANCED
    readiness_explanation: str
    next_readiness_milestone: str
    categorized_gaps: List[CategorizedGap] = Field(default_factory=list)
    transferable_skills: TransferableSkillsAnalysis
    credentials_strategy: List[VerifiedCredential] = Field(default_factory=list)
    accountability: AccountabilityStatus
    matched_opportunities: List[VerifiedOpportunity] = Field(default_factory=list)
    tailored_resume_preview: Optional[TailoredResume] = None
    generated_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    model_config = ConfigDict(populate_by_name=True)
