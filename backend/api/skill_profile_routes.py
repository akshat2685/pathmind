"""
Skill profile routes: the verification lifecycle as product surface.

POST /api/skills/claim   — record a self-reported skill (never verified yet)
POST /api/skills/verify  — submit evidence; deterministic evaluation appends
                           the outcome and flips the skill's status
GET  /api/skills/profile — the anti-resume: proven vs claimed vs gaps

Auth: person_id always comes from the verified JWT. Fail-soft reads:
profile problems return empty lists, never 500.
"""
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from backend.core.security import get_authenticated_person
from backend.services.pm_store import get_pm_store
from backend.services.skill_profile_service import SkillProfileService

router = APIRouter(prefix="/api/skills", tags=["Skill Verification"])
get_person_id = get_authenticated_person

_service: Optional[SkillProfileService] = None


def get_service() -> SkillProfileService:
    global _service
    if _service is None:
        _service = SkillProfileService()
    return _service


class ClaimSkillRequest(BaseModel):
    skill: str = Field(..., min_length=1, max_length=80)


class VerifySkillRequest(BaseModel):
    skill: str = Field(..., min_length=1, max_length=80)
    code: Optional[str] = Field(default=None, max_length=20000)
    repo_url: Optional[str] = Field(default=None, max_length=500)
    explanation: Optional[str] = Field(default=None, max_length=5000)


@router.post("/claim")
async def claim_skill(
    req: ClaimSkillRequest,
    person_id: str = Depends(get_person_id),
) -> Dict[str, Any]:
    """Record a self-reported skill. Labeled SELF_REPORTED, never verified."""
    try:
        return await get_service().claim_skill(person_id, req.skill)
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to record claim: {e}")


@router.post("/verify")
async def verify_skill(
    req: VerifySkillRequest,
    person_id: str = Depends(get_person_id),
) -> Dict[str, Any]:
    """
    Submit evidence for a claimed skill. Deterministically evaluated
    (code structure, repo provenance, explanation depth) — no LLM judgment.
    """
    try:
        return await get_service().verify_skill(
            person_id,
            req.skill,
            {"code": req.code or "", "repo_url": req.repo_url or "",
             "explanation": req.explanation or ""},
        )
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Verification failed: {e}")


@router.get("/profile")
async def skill_profile(
    person_id: str = Depends(get_person_id),
) -> Dict[str, Any]:
    """The anti-resume: proven vs claimed vs gaps, side by side."""
    gaps: List[str] = []
    try:
        jstate = await get_pm_store().get_journey_state(person_id)
        if isinstance(jstate, dict):
            raw_gaps = jstate.get("evidence_gaps") or []
            gaps = [g if isinstance(g, str) else str(g.get("gap", g))
                    for g in raw_gaps][:20]
    except Exception:
        pass
    try:
        return await get_service().skill_profile(person_id, gaps=gaps)
    except Exception:
        return {"person_id": person_id, "proven": [], "claimed": [],
                "gaps": gaps, "counts": {"proven": 0, "claimed": 0,
                                         "gaps": len(gaps)}}
