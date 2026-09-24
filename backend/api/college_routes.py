"""
API Routes for PATHMIND College Engineering MVP.
Provides endpoints for authentication profile, university lookup, curriculum resolution,
ordered learning plans, authentic PYQs, checkpoint assessments, accountability, and memory vault.
"""

from fastapi import APIRouter, Depends, HTTPException, Query, Body
from typing import List, Dict, Any, Optional
from pydantic import BaseModel

from backend.core.security import get_authenticated_person
from backend.core.college_schemas import (
    UniversityRecord,
    CurriculumRecord,
    AcademicContext,
    CollegeLearningPlan,
    CollegeAssessment,
    CollegeAssessmentSubmission,
    CollegeAssessmentResult,
    TodaySchedule,
    AccountabilityCommitment,
    CommitmentStatus,
    EngineeringBranch,
    CollegeShortMemory,
    CollegeLongMemory,
    LearningSignal,
    UserProfile
)
from backend.services.academic_service import AcademicService
from backend.services.college_learning_service import CollegeLearningService
from backend.services.pyq_service import PYQService
from backend.services.college_assessment_service import CollegeAssessmentService
from backend.services.college_accountability_service import CollegeAccountabilityService
from backend.services.college_memory_service import CollegeMemoryService
from backend.services.college_orchestrator import CollegeOrchestrator
from backend.services.store import FirestoreStore

router = APIRouter(prefix="/api/college", tags=["College Engineering MVP"])

store = FirestoreStore()
academic_service = AcademicService(store)
learning_service = CollegeLearningService(store)
assessment_service = CollegeAssessmentService(store)
accountability_service = CollegeAccountabilityService(store)
memory_service = CollegeMemoryService(store)
orchestrator = CollegeOrchestrator(store)

# --- 1. User Profile & Registry ---

@router.get("/users", response_model=List[Dict[str, Any]])
async def list_all_college_learners():
    """Lists all registered learners across the system."""
    return await store.list_all_college_users()

@router.get("/profile", response_model=UserProfile)
async def get_learner_profile(person_id: str = Depends(get_authenticated_person)):
    user = await store.get_college_user_profile(person_id)
    if not user:
        raise HTTPException(status_code=404, detail="PROFILE_NOT_FOUND")
    return UserProfile(**user)

class UpdateProfileRequest(BaseModel):
    name: Optional[str] = None
    email: Optional[str] = None
    supported_path: Optional[EngineeringBranch] = None

@router.post("/profile", response_model=UserProfile)
async def update_learner_profile(
    req: UpdateProfileRequest,
    person_id: str = Depends(get_authenticated_person)
):
    # Check existing
    user = await store.get_college_user_profile(person_id)
    if not user:
        # Create new
        if not req.name:
            raise HTTPException(status_code=400, detail="NAME_REQUIRED_FOR_ONBOARDING")
        user = await store.get_or_create_college_user(uid=person_id, name=req.name, email=req.email)
        if not user:
            raise HTTPException(status_code=500, detail="FAILED_TO_CREATE_PROFILE")
            
    if req.name:
        user["name"] = req.name
    if req.email:
        user["email"] = req.email
    if req.supported_path:
        user["supported_path"] = req.supported_path.value
        
    await store.save_college_user_profile(person_id, user)
    return UserProfile(**user)

# --- 2. Universities & Curricula ---

@router.get("/universities", response_model=List[UniversityRecord])
async def search_universities_endpoint(query: str = Query("", description="Search term")):
    return await academic_service.list_universities(query)

@router.get("/curriculum", response_model=CurriculumRecord)
async def get_curriculum_endpoint(
    university_id: str = Query(...),
    branch: EngineeringBranch = Query(...),
    semester: int = Query(...)
):
    curr = await academic_service.resolve_curriculum(university_id, branch, semester)
    if not curr:
        raise HTTPException(status_code=404, detail="CURRICULUM_NOT_FOUND")
    return curr

class SaveAcademicContextRequest(BaseModel):
    university_id: str
    branch: EngineeringBranch
    semester: int
    subjects: List[str]
    exam_window: Optional[Dict[str, Any]] = None
    available_hours_per_week: int = 14
    learning_style_preferences: Optional[List[str]] = None

@router.post("/academic-context", response_model=AcademicContext)
async def save_academic_context(
    req: SaveAcademicContextRequest,
    person_id: str = Depends(get_authenticated_person)
):
    try:
        return await academic_service.save_learner_academic_context(
            uid=person_id,
            university_id=req.university_id,
            branch=req.branch,
            semester=req.semester,
            subjects=req.subjects,
            exam_window=req.exam_window,
            available_hours_per_week=req.available_hours_per_week,
            learning_style_preferences=req.learning_style_preferences
        )
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))

@router.get("/academic-context", response_model=Optional[AcademicContext])
async def get_academic_context(person_id: str = Depends(get_authenticated_person)):
    return await academic_service.get_learner_academic_context(person_id)

# --- 3. Learning Plans & Ordered Activities ---

class GeneratePlanRequest(BaseModel):
    goal_id: Optional[str] = "goal_semester_prep"
    target_subject_code_or_id: Optional[str] = None

@router.post("/plans/generate", response_model=CollegeLearningPlan)
async def generate_plan_endpoint(
    req: GeneratePlanRequest,
    person_id: str = Depends(get_authenticated_person)
):
    try:
        return await learning_service.generate_learning_plan(
            uid=person_id,
            goal_id=req.goal_id or "goal_semester_prep",
            target_subject_code_or_id=req.target_subject_code_or_id
        )
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))

@router.get("/plans/current", response_model=Optional[CollegeLearningPlan])
async def get_current_plan_endpoint(person_id: str = Depends(get_authenticated_person)):
    return await learning_service.get_current_plan(person_id)

class CompleteActivityRequest(BaseModel):
    evidence: Optional[Dict[str, Any]] = None

@router.post("/activities/{activity_id}/complete", response_model=CollegeLearningPlan)
async def complete_activity_endpoint(
    activity_id: str,
    req: CompleteActivityRequest = Body(default=CompleteActivityRequest()),
    person_id: str = Depends(get_authenticated_person)
):
    try:
        return await learning_service.complete_activity(
            uid=person_id,
            activity_id=activity_id,
            completion_evidence=req.evidence
        )
    except ValueError as ve:
        raise HTTPException(status_code=404, detail=str(ve))

# --- 4. Verified Previous Year Questions (PYQs) ---

@router.get("/pyqs")
async def get_pyqs_endpoint(university_id: str = Query(...), subject_id: str = Query(...)):
    """Retrieves verified PYQs or returns explicit PYQ_NOT_AVAILABLE."""
    return await PYQService.get_pyqs(university_id, subject_id)

# --- 5. Checkpoint Assessments & Mastery ---

class GenerateAssessmentRequest(BaseModel):
    plan_id: str
    phase_id: str
    subject_id: str
    topic_title: str

@router.post("/assessments/generate", response_model=CollegeAssessment)
async def generate_assessment_endpoint(
    req: GenerateAssessmentRequest,
    person_id: str = Depends(get_authenticated_person)
):
    return await assessment_service.generate_phase_assessment(
        uid=person_id,
        plan_id=req.plan_id,
        phase_id=req.phase_id,
        subject_id=req.subject_id,
        topic_title=req.topic_title
    )

@router.post("/assessments/submit", response_model=CollegeAssessmentResult)
async def submit_assessment_endpoint(
    submission: CollegeAssessmentSubmission,
    person_id: str = Depends(get_authenticated_person)
):
    try:
        return await assessment_service.evaluate_submission(uid=person_id, submission=submission)
    except ValueError as ve:
        raise HTTPException(status_code=404, detail=str(ve))

# --- 6. Accountability & Daily Trail ---

@router.get("/accountability/today", response_model=TodaySchedule)
async def get_today_schedule_endpoint(person_id: str = Depends(get_authenticated_person)):
    return await accountability_service.get_today_schedule(person_id)

class CreateCommitmentRequest(BaseModel):
    title: str
    due_at: str
    estimated_minutes: int = 60
    plan_id: Optional[str] = None
    phase_id: Optional[str] = None

@router.post("/accountability/commit", response_model=AccountabilityCommitment)
async def create_commitment_endpoint(
    req: CreateCommitmentRequest,
    person_id: str = Depends(get_authenticated_person)
):
    return await accountability_service.create_commitment(
        uid=person_id,
        title=req.title,
        due_at=req.due_at,
        estimated_minutes=req.estimated_minutes,
        plan_id=req.plan_id,
        phase_id=req.phase_id
    )

class UpdateCommitmentStatusRequest(BaseModel):
    status: CommitmentStatus

@router.patch("/accountability/commit/{commitment_id}", response_model=AccountabilityCommitment)
async def update_commitment_status_endpoint(
    commitment_id: str,
    req: UpdateCommitmentStatusRequest,
    person_id: str = Depends(get_authenticated_person)
):
    res = await accountability_service.update_commitment_status(
        uid=person_id,
        commitment_id=commitment_id,
        status=req.status
    )
    if not res:
        raise HTTPException(status_code=404, detail="COMMITMENT_NOT_FOUND")
    return res

# --- 7. Memory & Learning Signals ---

@router.get("/memory")
async def get_learner_memories_endpoint(person_id: str = Depends(get_authenticated_person)):
    short_mems = await memory_service.get_short_term_memories(person_id)
    long_mems = await memory_service.get_long_term_memories(person_id)
    signals = await memory_service.get_learning_signals(person_id)
    return {
        "short_term": [m.model_dump(mode="json") for m in short_mems],
        "long_term": [m.model_dump(mode="json") for m in long_mems],
        "learning_signals": [s.model_dump(mode="json") for s in signals]
    }

# --- 8. Agent Interaction ---

class AgentInteractRequest(BaseModel):
    message: str
    session_id: Optional[str] = None

@router.post("/agent/interact")
async def agent_interact_endpoint(
    req: AgentInteractRequest,
    person_id: str = Depends(get_authenticated_person)
):
    return await orchestrator.interact(
        uid=person_id,
        user_message=req.message,
        session_id=req.session_id
    )
