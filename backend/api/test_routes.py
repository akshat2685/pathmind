"""
Aspiration test routes (onboarding TEST step).

Correct answers never leave this module: generation responses are stripped
by the service, and evaluation never echoes them.
Auth: person_id always comes from the verified JWT (get_authenticated_person).
"""

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from backend.core.gemini import GeminiUnavailable
from backend.core.security import get_authenticated_person
from backend.services.aspiration_test_service import (
    _sanitize_questions,
    get_test_service,
)

router = APIRouter(prefix="/api/test", tags=["Aspiration Test"])
get_person_id = get_authenticated_person


class GenerateTestRequest(BaseModel):
    aspiration: str = Field(..., min_length=5)
    stage: str = Field(default="")
    user_type: str = Field(default="")
    verification_data: Optional[Dict[str, Any]] = None


class SubmitAnswer(BaseModel):
    question_id: str
    answer: Any = None


class SubmitTestRequest(BaseModel):
    answers: List[SubmitAnswer] = Field(default_factory=list)


@router.post("/generate")
async def generate_test(
    request: GenerateTestRequest,
    person_id: str = Depends(get_person_id),
):
    """Generate a domain-aware entrance test for the learner's aspiration."""
    try:
        return await get_test_service().generate_test(
            person_id=person_id,
            aspiration=request.aspiration,
            stage=request.stage,
            user_type=request.user_type,
            verification_data=request.verification_data,
        )
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except GeminiUnavailable as e:
        raise HTTPException(
            status_code=503,
            detail=f"Test generation is temporarily unavailable ({e}). "
                   "Please try again in a few minutes — no test was created.",
        )
    except RuntimeError as e:
        # PmStore fail-fast (persistence unavailable): surface honestly
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate test: {e}")


@router.post("/{test_id}/submit")
async def submit_test(
    test_id: str,
    request: SubmitTestRequest,
    person_id: str = Depends(get_person_id),
):
    """Submit answers for a test; returns the evaluation (never correct answers)."""
    try:
        return await get_test_service().evaluate_test(
            person_id=person_id,
            test_id=test_id,
            answers=[a.model_dump() for a in request.answers],
        )
    except KeyError as ke:
        raise HTTPException(status_code=404, detail=str(ke))
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to evaluate test: {e}")


@router.get("/current")
async def current_test(person_id: str = Depends(get_person_id)):
    """
    Latest generated test for this user (answers stripped). Includes
    `submitted: true` + the evaluation when already attempted, so the
    frontend can resume or show results directly.
    """
    try:
        service = get_test_service()
        test = await service.store.get_latest_aspiration_test(person_id)
        if not test:
            raise HTTPException(status_code=404, detail="No test generated yet.")
        result = await service.store.get_test_result_for_test(
            person_id, test.get("test_id", "")
        )
        payload: Dict[str, Any] = {
            "test_id": test.get("test_id"),
            "aspiration": test.get("aspiration"),
            "stage": test.get("stage"),
            "user_type": test.get("user_type"),
            "questions": _sanitize_questions(test.get("questions", [])),
            "total_points": test.get("total_points"),
            "time_suggestion_minutes": test.get("time_suggestion_minutes"),
            "submitted": result is not None,
        }
        if result:
            payload["evaluation"] = result
        return payload
    except HTTPException:
        raise
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to load test: {e}")
