"""
PYQ (Previous Year Questions) Service for PATHMIND College Engineering MVP.
Enforces strict authenticity: Retrieves genuine past exam papers mapped to topics,
and returns explicit PYQ_NOT_AVAILABLE when authentic papers do not exist.
"""

from typing import Optional, Dict, Any, List
from backend.core.college_schemas import PYQSetRecord, PYQQuestionRecord
from backend.providers.curriculum_registry import get_pyqs_for_subject

class PYQService:
    @staticmethod
    async def get_pyqs(university_id: Optional[str], subject_id: str) -> Dict[str, Any]:
        """
        Retrieves authentic previous year exam questions for a subject.
        Returns explicit status='PYQ_NOT_AVAILABLE' if unverified or unavailable.
        university_id is optional: without it, the latest verified set for the
        subject across universities is returned.
        """
        pyq_set = await get_pyqs_for_subject(university_id, subject_id)
        if not pyq_set or not pyq_set.questions:
            return {
                "status": "PYQ_NOT_AVAILABLE",
                "subject_id": subject_id,
                "message": "Verified previous year examination questions are currently unavailable for this subject from official repositories.",
                "pyq_set": None
            }

        return {
            "status": "VERIFIED",
            "subject_id": subject_id,
            "message": f"Retrieved {len(pyq_set.questions)} verified previous year exam questions from official repositories.",
            "pyq_set": pyq_set.model_dump(mode="json")
        }

    @staticmethod
    async def get_pyq_questions_for_topics(university_id: str, subject_id: str, topic_ids: List[str]) -> List[PYQQuestionRecord]:
        """Filters authentic PYQ questions matching specific topics."""
        pyq_set = await get_pyqs_for_subject(university_id, subject_id)
        if not pyq_set:
            return []
        
        matches = []
        for q in pyq_set.questions:
            if any(t.lower() in [qt.lower() for qt in q.topic_ids] for t in topic_ids):
                matches.append(q)
        return matches
