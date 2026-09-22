"""
Academic Service for PATHMIND College Engineering MVP.
Manages university search, canonical academic programs, and verified curriculum retrieval.
"""

from typing import List, Optional, Dict, Any
from backend.core.college_schemas import (
    UniversityRecord,
    CurriculumRecord,
    SubjectRecord,
    EngineeringBranch,
    AcademicContext,
    VerificationStatus
)
from backend.providers.curriculum_registry import (
    search_universities,
    get_all_universities,
    get_university_by_id,
    get_curriculum
)
from backend.services.store import FirestoreStore

class AcademicService:
    def __init__(self, store: Optional[FirestoreStore] = None):
        self.store = store or FirestoreStore()

    async def list_universities(self, query: str = "") -> List[UniversityRecord]:
        """Search or list verified canonical engineering universities."""
        return await search_universities(query)

    async def get_university(self, university_id: str) -> Optional[UniversityRecord]:
        return await get_university_by_id(university_id)

    async def resolve_curriculum(
        self,
        university_id: str,
        branch: EngineeringBranch,
        semester: int
    ) -> Optional[CurriculumRecord]:
        """
        Retrieves authentic curriculum for university, engineering branch, and semester.
        """
        return await get_curriculum(university_id, branch, semester)

    async def save_learner_academic_context(
        self,
        uid: str,
        university_id: str,
        branch: EngineeringBranch,
        semester: int,
        subjects: List[str],
        exam_window: Optional[Dict[str, Any]] = None,
        available_hours_per_week: int = 12,
        learning_style_preferences: Optional[List[str]] = None
    ) -> AcademicContext:
        """Stores authenticated learner's validated academic context."""
        univ = await self.get_university(university_id)
        univ_name = univ.name if univ else university_id

        context = AcademicContext(
            context_id=f"ctx_{uid}_{semester}",
            uid=uid,
            university_id=university_id,
            university_name=univ_name,
            branch=branch,
            semester=semester,
            subjects=subjects,
            exam_window=exam_window or {},
            available_hours_per_week=available_hours_per_week,
            learning_style_preferences=learning_style_preferences or []
        )

        await self.store.save_college_academic_context(uid, context.model_dump(mode="json"))

        # Update user profile
        user_prof = await self.store.get_or_create_college_user(uid)
        user_prof["primary_university_id"] = university_id
        user_prof["primary_branch"] = branch.value
        user_prof["current_semester"] = semester
        user_prof["supported_path"] = branch.value
        user_prof["profile_status"] = "CONTEXT_SET"
        await self.store.save_college_user_profile(uid, user_prof)

        return context

    async def get_learner_academic_context(self, uid: str) -> Optional[AcademicContext]:
        raw = await self.store.get_college_academic_context(uid)
        if raw:
            return AcademicContext(**raw)
        return None
