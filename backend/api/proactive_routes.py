from fastapi import APIRouter, Depends, HTTPException, Header, Query
from typing import List, Dict, Any, Optional
from pydantic import BaseModel
from backend.core.event_schemas import (
    EventRecord,
    Intervention,
    NotificationPreferences
)
from backend.services.proactive_intervention_engine import ProactiveInterventionEngine

router = APIRouter(prefix="/api/proactive", tags=["Proactive Intelligence & Intervention Engine"])
proactive_engine = ProactiveInterventionEngine()

from backend.core.security import get_authenticated_person
get_person_id = get_authenticated_person

class ActRequest(BaseModel):
    feedback_note: Optional[str] = None

class UpdatePreferencesRequest(BaseModel):
    enable_opportunity_alerts: Optional[bool] = True
    enable_mastery_alerts: Optional[bool] = True
    enable_blocker_alerts: Optional[bool] = True
    enable_reinforcement_alerts: Optional[bool] = True
    quiet_hours_enabled: Optional[bool] = False
    quiet_hours_start: Optional[str] = "22:00"
    quiet_hours_end: Optional[str] = "08:00"

@router.get("/interventions", response_model=List[Intervention])
async def get_interventions(person_id: str = Depends(get_person_id)):
    try:
        return await proactive_engine.get_active_interventions(person_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve interventions: {str(e)}")

@router.post("/interventions/{intervention_id}/act")
async def act_on_intervention(
    intervention_id: str,
    req: ActRequest,
    person_id: str = Depends(get_person_id)
):
    try:
        success = await proactive_engine.act_on_intervention(
            person_id=person_id,
            intervention_id=intervention_id,
            feedback_note=req.feedback_note
        )
        if not success:
            raise HTTPException(status_code=404, detail="Intervention not found.")
        return {"status": "SUCCESS", "message": "Intervention marked as ACTED_ON."}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to act on intervention: {str(e)}")

@router.post("/interventions/{intervention_id}/dismiss")
async def dismiss_intervention(
    intervention_id: str,
    person_id: str = Depends(get_person_id)
):
    try:
        success = await proactive_engine.dismiss_intervention(
            person_id=person_id,
            intervention_id=intervention_id
        )
        if not success:
            raise HTTPException(status_code=404, detail="Intervention not found.")
        return {"status": "SUCCESS", "message": "Intervention dismissed."}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to dismiss intervention: {str(e)}")

@router.get("/events", response_model=List[EventRecord])
async def get_events(
    event_type: Optional[str] = Query(None),
    person_id: str = Depends(get_person_id)
):
    try:
        return await proactive_engine.event_bus.get_recent_events(person_id, event_type=event_type)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve events: {str(e)}")

@router.get("/preferences", response_model=NotificationPreferences)
async def get_preferences(person_id: str = Depends(get_person_id)):
    try:
        raw = await proactive_engine.store.get_notification_preferences(person_id)
        if raw:
            return NotificationPreferences(**raw)
        return NotificationPreferences(person_id=person_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve preferences: {str(e)}")

@router.post("/preferences", response_model=NotificationPreferences)
async def update_preferences(
    req: UpdatePreferencesRequest,
    person_id: str = Depends(get_person_id)
):
    try:
        prefs = NotificationPreferences(
            person_id=person_id,
            enable_opportunity_alerts=req.enable_opportunity_alerts if req.enable_opportunity_alerts is not None else True,
            enable_mastery_alerts=req.enable_mastery_alerts if req.enable_mastery_alerts is not None else True,
            enable_blocker_alerts=req.enable_blocker_alerts if req.enable_blocker_alerts is not None else True,
            enable_reinforcement_alerts=req.enable_reinforcement_alerts if req.enable_reinforcement_alerts is not None else True,
            quiet_hours_enabled=bool(req.quiet_hours_enabled),
            quiet_hours_start=req.quiet_hours_start or "22:00",
            quiet_hours_end=req.quiet_hours_end or "08:00"
        )
        await proactive_engine.store.save_notification_preferences(person_id, prefs.model_dump())
        return prefs
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save preferences: {str(e)}")

@router.post("/scan-events", response_model=List[Intervention])
async def scan_events(person_id: str = Depends(get_person_id)):
    try:
        return await proactive_engine.scan_and_generate_interventions(person_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to scan events: {str(e)}")
