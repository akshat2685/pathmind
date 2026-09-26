"""
Longitudinal memory tier routes: short-term session memory, long-term
journey memory, and learning signals.

Auth: person_id always comes from the verified JWT.
"""

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from backend.core.security import get_authenticated_person
from backend.services.longitudinal_memory_service import (
    LongitudinalMemoryService,
    MEMORY_TYPES,
    SIGNAL_TYPES,
    SHORT_TERM_TTL_DAYS,
)

router = APIRouter(prefix="/api/memory-tiers", tags=["Memory Tiers"])
get_person_id = get_authenticated_person

_service: Optional[LongitudinalMemoryService] = None


def get_service() -> LongitudinalMemoryService:
    global _service
    if _service is None:
        _service = LongitudinalMemoryService()
    return _service


class ShortTermRequest(BaseModel):
    content: str = Field(..., min_length=1, max_length=4000)
    topic: Optional[str] = None
    session_id: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class LongTermRequest(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    content: str = Field(..., min_length=1, max_length=8000)
    memory_type: str = "EPISODIC"
    importance: str = "MEDIUM"
    related_domain: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class SignalRequest(BaseModel):
    signal_type: str
    content: str = Field(..., min_length=1, max_length=4000)
    related_domain: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


@router.post("/short-term")
async def record_short_term(req: ShortTermRequest, person_id: str = Depends(get_person_id)):
    return await get_service().record_short_term(
        person_id, req.content, topic=req.topic,
        session_id=req.session_id, metadata=req.metadata,
    )


@router.get("/short-term")
async def get_short_term(
    session_id: Optional[str] = Query(None),
    limit: int = Query(20, ge=1, le=100),
    person_id: str = Depends(get_person_id),
):
    return {
        "ttl_days": SHORT_TERM_TTL_DAYS,
        "memories": await get_service().get_short_term(person_id, session_id=session_id, limit=limit),
    }


@router.post("/long-term")
async def record_long_term(req: LongTermRequest, person_id: str = Depends(get_person_id)):
    if req.memory_type not in MEMORY_TYPES:
        raise HTTPException(status_code=400, detail=f"memory_type must be one of {MEMORY_TYPES}")
    return await get_service().record_long_term(
        person_id, req.content, req.title, memory_type=req.memory_type,
        importance=req.importance, related_domain=req.related_domain,
        metadata=req.metadata,
    )


@router.get("/long-term")
async def get_long_term(
    limit: int = Query(50, ge=1, le=200),
    person_id: str = Depends(get_person_id),
):
    return await get_service().get_long_term(person_id, limit=limit)


@router.post("/signals")
async def record_signal(req: SignalRequest, person_id: str = Depends(get_person_id)):
    if req.signal_type not in SIGNAL_TYPES:
        raise HTTPException(status_code=400, detail=f"signal_type must be one of {SIGNAL_TYPES}")
    return await get_service().record_signal(
        person_id, req.signal_type, req.content,
        related_domain=req.related_domain, metadata=req.metadata,
    )


@router.get("/signals")
async def get_signals(
    signal_type: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    person_id: str = Depends(get_person_id),
):
    if signal_type and signal_type not in SIGNAL_TYPES:
        raise HTTPException(status_code=400, detail=f"signal_type must be one of {SIGNAL_TYPES}")
    return await get_service().get_signals(person_id, signal_type=signal_type, limit=limit)


@router.get("/journey-context")
async def journey_context(person_id: str = Depends(get_person_id)):
    """Compact memory snapshot for grounding prompts."""
    return await get_service().journey_context(person_id)
