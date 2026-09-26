from fastapi import APIRouter, Depends, HTTPException, Query
from typing import Dict, Any, List, Optional

from backend.core.security import get_authenticated_person
from backend.services.pm_store import get_pm_store
from backend.services.verification_service import (
    VerificationService,
    get_requirements,
    USER_TYPES,
)

router = APIRouter(prefix="/api/orchestrate/verification", tags=["User Verification"])
get_person_id = get_authenticated_person


def _service() -> VerificationService:
    return VerificationService(store=get_pm_store())


@router.get("/requirements")
async def verification_requirements(
    user_type: str = Query(..., description="One of: " + ", ".join(USER_TYPES)),
) -> Dict[str, Any]:
    """
    Field catalog for the verification step of a given user type.
    Public — it is only the form schema, no personal data.
    """
    try:
        return get_requirements(user_type)
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))


@router.post("/submit")
async def submit_verification(
    request: Dict[str, Any],
    person_id: str = Depends(get_person_id),
) -> Dict[str, Any]:
    """
    Submit verification details for the authenticated person.
    Body: {"user_type": "school|college|...", "data": {...}, "document_urls": [...]}.
    Validates required fields, stores with status PENDING, then runs the
    deterministic evaluation immediately (VERIFIED / NEEDS_REVIEW / REJECTED).
    The person_id always comes from the JWT — never from the request body.
    """
    user_type = request.get("user_type")
    data = request.get("data") or {}
    document_urls = request.get("document_urls") or []
    try:
        return await _service().submit_verification(
            person_id=person_id,
            user_type=user_type,
            data=data,
            document_urls=document_urls,
        )
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except RuntimeError as re:
        raise HTTPException(status_code=503, detail=str(re))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to submit verification: {str(e)}")


@router.get("/status")
async def verification_status(
    person_id: str = Depends(get_person_id),
) -> Dict[str, Any]:
    """
    Current verification record for the authenticated person.
    404 when the person has not submitted verification yet.
    """
    try:
        record = await _service().get_status(person_id)
    except RuntimeError as re:
        raise HTTPException(status_code=503, detail=str(re))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch verification status: {str(e)}")
    if not record:
        raise HTTPException(status_code=404, detail="No verification submitted yet.")
    return record
