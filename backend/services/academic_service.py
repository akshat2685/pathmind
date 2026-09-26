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
        # Resolve the canonical program; None when knowledge tables are unseeded
        # (program_id is nullable — never invent one).
        program_id = await self.store.find_program_id(university_id, [branch.value, branch.name])

        context = AcademicContext(
            context_id=f"ctx_{uid}_{semester}",
            user_id=uid,
            university_id=university_id,
            program_id=program_id,
            semester=semester,
            exam_window=exam_window or {},
            available_hours_per_week=available_hours_per_week,
            learning_style_preferences=learning_style_preferences or []
        )

        context_data = context.model_dump(mode="json")
        context_data["subjects"] = subjects
        await self.store.save_college_academic_context(uid, context_data)

        # Sync denormalized profile fields. The learner profile must already exist
        # (created via POST /profile during onboarding) — never fabricate one here.
        user_prof = await self.store.get_college_user_profile(uid)
        if not user_prof:
            raise ValueError("PROFILE_NOT_FOUND: create the learner profile before saving academic context")
        await self.store.save_college_user_profile(uid, {
            "primary_university_id": university_id,
            "primary_program_id": program_id,
            "current_semester": semester,
            "supported_path": branch.value,
            "profile_status": "CONTEXT_SET",
        })

        # Return the re-read context: it carries the persisted subjects from the
        # mapping table (the in-memory object above never had them). Single
        # source of truth, no stale fields.
        saved = await self.get_learner_academic_context(uid)
        if saved is None:  # pragma: no cover - defensive; save just succeeded
            raise RuntimeError("PERSISTENCE_UNAVAILABLE")
        return saved

    async def get_learner_academic_context(self, uid: str) -> Optional[AcademicContext]:
        raw = await self.store.get_college_academic_context(uid)
        if raw:
            return AcademicContext(**raw)
        return None
