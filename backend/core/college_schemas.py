from enum import Enum
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from datetime import datetime, timezone
import uuid

def current_iso_time() -> str:
    return datetime.now(timezone.utc).isoformat()

# --- Enums ---

class EngineeringBranch(str, Enum):
    MECHANICAL = "MECHANICAL_ENGINEER"
    ELECTRICAL = "ELECTRICAL_ENGINEER"
    COMPUTER_SCIENCE = "COMPUTER_SCIENCE_ENGINEER"
    AI_ENGINEERING = "AI_ENGINEER"
    CIVIL = "CIVIL_ENGINEER"
    GENERAL_OTHER = "GENERAL_OTHER"

class SourceTier(str, Enum):
    A = "A"  # Official university / syllabus / examination
    B = "B"  # NPTEL / SWAYAM / IIT / Government open education
    C = "C"  # Established high-quality publishers / institutions
    D = "D"  # Supporting educator channels / community resources

class VerificationStatus(str, Enum):
    DISCOVERED = "DISCOVERED"
    FETCHED = "FETCHED"
    PARSED = "PARSED"
    VERIFIED = "VERIFIED"
    STALE = "STALE"
    UNVERIFIABLE = "UNVERIFIABLE"
    REJECTED = "REJECTED"

class ActivityType(str, Enum):
    WATCH = "WATCH"
    READ = "READ"
    PRACTICE = "PRACTICE"
    SOLVE_PYQ = "SOLVE_PYQ"
    ASSESS = "ASSESS"
    BUILD = "BUILD"
    EXPLAIN = "EXPLAIN"
    REFLECT = "REFLECT"
    REVIEW = "REVIEW"

class MasteryStatus(str, Enum):
    MASTERED = "MASTERED"
    PARTIALLY_MASTERED = "PARTIALLY_MASTERED"
    REINFORCEMENT_REQUIRED = "REINFORCEMENT_REQUIRED"
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"

class CommitmentStatus(str, Enum):
    PLANNED = "PLANNED"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    MISSED = "MISSED"
    RESCHEDULED = "RESCHEDULED"
    CANCELLED = "CANCELLED"

# --- Academic Models ---

class UniversityRecord(BaseModel):
    university_id: str
    name: str
    normalized_name: str
    country: str = "India"
    state: str
    official_domain: Optional[str] = None
    official_url: Optional[str] = None
    verification_status: VerificationStatus = VerificationStatus.VERIFIED
    source_id: Optional[str] = None
    aliases: List[str] = Field(default_factory=list)
    created_at: str = Field(default_factory=current_iso_time)
    updated_at: str = Field(default_factory=current_iso_time)

class ProgramRecord(BaseModel):
    program_id: str
    university_id: str
    name: str
    normalized_name: str
    degree: str = "BTECH"
    branch: str
    supported_path: str
    duration_semesters: int = 8
    version: int = 1
    verification_status: VerificationStatus = VerificationStatus.VERIFIED

class CurriculumUnit(BaseModel):
    curriculum_id: str
    subject_id: str
    unit: int
    title: str
    topics: List[str] = Field(default_factory=list)
    source_ids: List[str] = Field(default_factory=list)
    verification_status: VerificationStatus = VerificationStatus.VERIFIED

class SubjectRecord(BaseModel):
    subject_id: str
    code: str
    name: str
    credits: Optional[int] = None
    lecture_hours: Optional[int] = None
    practical_hours: Optional[int] = None
    assessment_pattern: Optional[Dict[str, Any]] = None
    verification_status: VerificationStatus = VerificationStatus.VERIFIED
    created_at: str = Field(default_factory=current_iso_time)
    units: List[CurriculumUnit] = Field(default_factory=list)

class CurriculumRecord(BaseModel):
    curriculum_id: str
    university_id: str
    program_id: str
    academic_year: Optional[str] = None
    semester: int
    version: int = 1
    verification_status: VerificationStatus = VerificationStatus.VERIFIED
    created_at: str = Field(default_factory=current_iso_time)
    subjects: List[SubjectRecord] = Field(default_factory=list)

# --- Source & Resource Models ---

class QualitySignals(BaseModel):
    domain_authority: float = 1.0
    curriculum_match: float = 1.0
    freshness: float = 1.0
    reachability: float = 1.0

class SourceRecord(BaseModel):
    source_id: str
    url: str
    canonical_url: Optional[str] = None
    title: str
    domain: str
    provider_name: str
    provider_type: str = "UNIVERSITY"
    source_tier: SourceTier
    source_type: str = "OFFICIAL_SYLLABUS"
    author: Optional[str] = None
    retrieved_at: str = Field(default_factory=current_iso_time)
    last_verified_at: Optional[str] = None
    verification_status: VerificationStatus = VerificationStatus.VERIFIED
    content_hash: Optional[str] = None
    language: str = "en"
    content_available: bool = True
    topic_ids: List[str] = Field(default_factory=list)
    curriculum_ids: List[str] = Field(default_factory=list)
    quality_signals: QualitySignals = Field(default_factory=QualitySignals)
    notes: Optional[str] = None

class VideoTimestamp(BaseModel):
    start_seconds: int
    end_seconds: int
    purpose: str

class DocumentSection(BaseModel):
    start_page: int
    end_page: int
    section_title: str

class ResourceRecord(BaseModel):
    resource_id: str
    title: str
    resource_type: str  # VIDEO, DOCUMENT, NOTES, SIMULATION
    provider: str
    url: str
    source_id: str
    source_tier: SourceTier
    verification_status: VerificationStatus = VerificationStatus.VERIFIED
    difficulty: Optional[str] = None
    estimated_minutes: Optional[int] = None
    cost: Optional[str] = None
    language: str = "en"
    topic_ids: List[str] = Field(default_factory=list)
    curriculum_ids: List[str] = Field(default_factory=list)
    video_timestamps: List[VideoTimestamp] = Field(default_factory=list)
    document_sections: List[DocumentSection] = Field(default_factory=list)
    learner_preference_metadata: Dict[str, Any] = Field(default_factory=dict)
    last_verified_at: Optional[str] = None

# --- PYQ Models ---

class PYQQuestionRecord(BaseModel):
    question_id: str
    pyq_set_id: str
    question_number: str
    question_text: str
    marks: Optional[int] = None
    topic_ids: List[str] = Field(default_factory=list)
    unit: Optional[int] = None
    difficulty: Optional[str] = None
    source_id: Optional[str] = None
    verification_status: VerificationStatus = VerificationStatus.VERIFIED

class PYQSetRecord(BaseModel):
    pyq_set_id: str
    university_id: str
    program_id: str
    curriculum_id: Optional[str] = None
    semester: int
    subject_id: str
    exam_year: int
    exam_type: Optional[str] = None
    source_id: str
    verification_status: VerificationStatus = VerificationStatus.VERIFIED
    created_at: str = Field(default_factory=current_iso_time)
    questions: List[PYQQuestionRecord] = Field(default_factory=list)

# --- User & Context Models ---

class UserProfile(BaseModel):
    user_id: str
    name: str
    email: Optional[str] = None
    primary_university_id: Optional[str] = None
    primary_program_id: Optional[str] = None
    primary_branch: Optional[str] = None
    current_semester: Optional[int] = None
    current_academic_year: Optional[str] = None
    supported_path: str = "GENERAL_OTHER"
    profile_status: str = "INITIALIZED"  # INITIALIZED, CONTEXT_SET, ONBOARDED
    timezone: str = "Asia/Kolkata"
    locale: str = "en-IN"
    created_at: str = Field(default_factory=current_iso_time)
    last_login_at: str = Field(default_factory=current_iso_time)

class LearnerContextSubject(BaseModel):
    context_id: str
    user_id: str
    subject_id: str
    created_at: str = Field(default_factory=current_iso_time)

class AcademicContext(BaseModel):
    context_id: str
    user_id: str
    university_id: str
    program_id: Optional[str] = None  # nullable in DB; None when programs unseeded
    semester: int
    academic_year: Optional[str] = None
    exam_window: Dict[str, Any] = Field(default_factory=dict)
    available_hours_per_week: Optional[int] = None
    learning_style_preferences: List[str] = Field(default_factory=list)
    created_at: str = Field(default_factory=current_iso_time)
    updated_at: str = Field(default_factory=current_iso_time)

class CollegeGoal(BaseModel):
    goal_id: str
    user_id: str
    goal_type: str = "SEMESTER_EXAM"
    raw_goal: str
    normalized_goal: str
    target_subject_ids: List[str] = Field(default_factory=list)
    target_score: Optional[float] = None
    deadline: Optional[str] = None
    status: str = "ACTIVE"
    created_at: str = Field(default_factory=current_iso_time)
    updated_at: str = Field(default_factory=current_iso_time)

# --- Learning Plan & Activities ---

class LearningPlanSubject(BaseModel):
    plan_id: str
    user_id: Optional[str] = None  # not a DB column; kept optional for compat
    subject_id: str
    created_at: str = Field(default_factory=current_iso_time)

class CollegeActivity(BaseModel):
    activity_id: str
    user_id: str
    plan_id: str
    phase_id: str
    activity_type: ActivityType
    title: str
    resource_id: Optional[str] = None
    pyq_question_id: Optional[str] = None
    order: int
    instructions: str
    estimated_minutes: Optional[int] = None
    status: str = "AVAILABLE"  # LOCKED, AVAILABLE, IN_PROGRESS, COMPLETED
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    completion_evidence: Optional[Dict[str, Any]] = None

    # Transient references for API inclusion, not strictly persisted on the row
    resource: Optional[ResourceRecord] = None
    pyq_question: Optional[PYQQuestionRecord] = None

class CollegePlanPhase(BaseModel):
    phase_id: str
    user_id: str
    plan_id: str
    order: int
    title: str
    objective: str
    status: str = "AVAILABLE"  # LOCKED, AVAILABLE, IN_PROGRESS, COMPLETED
    unlock_rule: Dict[str, Any] = Field(default_factory=dict)
    assessment_id: Optional[str] = None
    created_at: str = Field(default_factory=current_iso_time)

    activities: List[CollegeActivity] = Field(default_factory=list)

class CollegeLearningPlan(BaseModel):
    plan_id: str
    user_id: str
    goal_id: str
    plan_type: str = "SEMESTER_PREPARATION"
    version: int = 1
    status: str = "ACTIVE"
    created_at: str = Field(default_factory=current_iso_time)

    phases: List[CollegePlanPhase] = Field(default_factory=list)
    subjects: List[LearningPlanSubject] = Field(default_factory=list)

# --- Assessment Models ---

class CollegeAssessmentQuestion(BaseModel):
    question_id: str
    question_text: str
    question_type: str = "MCQ"
    options: Optional[List[str]] = None
    correct_answer: Optional[str] = None
    rubric: Optional[str] = None
    topic: str
    unit: Optional[int] = None
    marks: Optional[int] = None

class CollegeAssessment(BaseModel):
    assessment_id: str
    user_id: str
    plan_id: str
    phase_id: str
    subject_id: str
    title: str
    questions: List[CollegeAssessmentQuestion] = Field(default_factory=list)
    status: str = "AVAILABLE"
    created_at: str = Field(default_factory=current_iso_time)

class CollegeAssessmentSubmission(BaseModel):
    assessment_id: str
    answers: Dict[str, str] = Field(default_factory=dict)

class CollegeAssessmentResult(BaseModel):
    result_id: str
    user_id: str
    assessment_id: str
    score: float
    normalized_score: float
    mastery_status: str
    topic_results: List[Dict[str, Any]] = Field(default_factory=list)
    feedback: str
    evaluation_confidence: Optional[float] = None
    created_at: str = Field(default_factory=current_iso_time)

# --- Memory & Learning Signals ---

class CollegeShortMemory(BaseModel):
    memory_id: str
    user_id: str
    session_id: Optional[str] = None
    conversation_id: Optional[str] = None
    content: str
    topic: Optional[str] = None
    created_at: str = Field(default_factory=current_iso_time)
    expires_at: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)

class CollegeLongMemory(BaseModel):
    memory_id: str
    user_id: str
    memory_type: str = "EPISODIC"
    nature: str = "EXPERIENCE"
    title: str
    content: str
    source_type: str = "UNKNOWN"
    source_reference: Optional[str] = None
    confidence: Optional[str] = None
    importance: Optional[str] = None
    status: str = "CURRENT"  # CURRENT, SUPERSEDED, ARCHIVED
    created_at: str = Field(default_factory=current_iso_time)
    updated_at: str = Field(default_factory=current_iso_time)
    related_subject: Optional[str] = None
    related_topic: Optional[str] = None
    related_skill: Optional[str] = None
    supersedes_memory_id: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)

class LearningSignal(BaseModel):
    signal_id: str
    user_id: str
    signal_type: str = "REPEATED_MISCONCEPTION"
    subject_id: Optional[str] = None
    topic_id: Optional[str] = None
    description: str
    confidence: Optional[float] = None
    recommended_intervention: str
    created_at: str = Field(default_factory=current_iso_time)

# --- Accountability & Daily Trail ---

class AccountabilityCommitment(BaseModel):
    commitment_id: str
    user_id: str
    title: str
    plan_id: Optional[str] = None
    phase_id: Optional[str] = None
    due_at: str
    estimated_minutes: Optional[int] = None
    status: str = "PLANNED"
    completion_evidence_ref: Optional[str] = None
    created_at: str = Field(default_factory=current_iso_time)
    updated_at: str = Field(default_factory=current_iso_time)

class TodaySchedule(BaseModel):
    date: str
    exam_days_remaining: Optional[int] = None
    commitments: List[AccountabilityCommitment] = Field(default_factory=list)
    active_activities: List[CollegeActivity] = Field(default_factory=list)
    active_assessments: List[CollegeAssessment] = Field(default_factory=list)
    streak_days: int = 1
    total_planned_minutes: int = 0
    total_completed_minutes: int = 0
