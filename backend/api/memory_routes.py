from fastapi import APIRouter, Depends, HTTPException, Header, Query
from typing import List, Dict, Any, Optional
from backend.core.memory_schemas import (
    MemoryItem,
    SharedLearningPattern,
    MemoryRecallQuery,
    MemoryRecallResponse,
    CrossStageBridgeResponse,
    SecondBrainQueryRequest,
    SecondBrainQueryResponse,
    ConsolidateMemoriesRequest,
    ConsolidateMemoriesResponse,
    SupersedeMemoryRequest
)
from backend.services.memory_engine import MemoryEngine
from backend.services.second_brain_service import SecondBrainService
from backend.services.store import FirestoreStore

from backend.core.security import get_authenticated_person

router = APIRouter(prefix="/api/memory", tags=["Longitudinal Learning Memory"])
store = FirestoreStore()
engine = MemoryEngine(store=store)
second_brain = SecondBrainService(store=store)
get_person_id = get_authenticated_person

@router.get("/personal", response_model=List[MemoryItem])
async def get_personal_memories(
    memory_type: Optional[str] = Query(None),
    topic: Optional[str] = Query(None),
    nature: Optional[str] = Query(None),
    lifecycle_status: Optional[str] = Query(None),
    person_id: str = Depends(get_person_id)
):
    try:
        raw_mems = await store.get_personal_memories(person_id, memory_type=memory_type, topic=topic)
        items = [MemoryItem(**m) for m in raw_mems]
        if nature:
            items = [m for m in items if m.nature == nature]
        if lifecycle_status:
            items = [m for m in items if m.lifecycle_status == lifecycle_status]
        return items
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve personal memories: {str(e)}")

@router.post("/events", response_model=MemoryItem)
async def ingest_learning_event(
    event_payload: Dict[str, Any],
    person_id: str = Depends(get_person_id)
):
    try:
        active_person_id = event_payload.get("person_id") or person_id
        return await second_brain.ingest_memory(active_person_id, event_payload)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to ingest learning event: {str(e)}")

@router.post("/query", response_model=SecondBrainQueryResponse)
async def query_second_brain(
    req: SecondBrainQueryRequest,
    person_id: str = Depends(get_person_id)
):
    try:
        return await second_brain.query_second_brain(person_id, req)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Second brain search failed: {str(e)}")

@router.post("/recall", response_model=MemoryRecallResponse)
async def recall_natural_memory(
    query: MemoryRecallQuery,
    person_id: str = Depends(get_person_id)
):
    try:
        query.person_id = query.person_id or person_id
        return await engine.recall_natural_memory(query)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Memory recall query failed: {str(e)}")

@router.post("/consolidate", response_model=ConsolidateMemoriesResponse)
async def consolidate_memories(
    req: ConsolidateMemoriesRequest,
    person_id: str = Depends(get_person_id)
):
    try:
        return await second_brain.consolidate_memories(
            person_id=person_id,
            source_memory_ids=req.source_memory_ids,
            consolidated_title=req.consolidated_title,
            consolidated_summary=req.consolidated_summary,
            topic=req.topic
        )
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to consolidate memories: {str(e)}")

@router.post("/{memory_id}/supersede", response_model=MemoryItem)
async def supersede_memory(
    memory_id: str,
    req: SupersedeMemoryRequest,
    person_id: str = Depends(get_person_id)
):
    try:
        return await second_brain.supersede_memory(
            person_id=person_id,
            old_memory_id=memory_id,
            reason=req.reason,
            new_memory_payload=req.new_memory_payload
        )
    except ValueError as ve:
        raise HTTPException(status_code=404, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to supersede memory: {str(e)}")

@router.put("/{memory_id}", response_model=MemoryItem)
async def update_memory(
    memory_id: str,
    updates: Dict[str, Any],
    person_id: str = Depends(get_person_id)
):
    try:
        return await second_brain.update_memory(person_id, memory_id, updates)
    except ValueError as ve:
        raise HTTPException(status_code=404, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update memory: {str(e)}")

@router.get("/cross-stage", response_model=CrossStageBridgeResponse)
async def get_cross_stage_bridge(
    concept: Optional[str] = "Tree Traversal & Depth-First Search",
    person_id: str = Depends(get_person_id)
):
    try:
        return await engine.get_cross_stage_bridge(person_id, current_concept=concept or "Tree Traversal")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve cross-stage bridge: {str(e)}")

@router.delete("/personal/{memory_id}")
async def delete_personal_memory(
    memory_id: str,
    person_id: str = Depends(get_person_id)
):
    try:
        success = await store.delete_personal_memory(person_id, memory_id)
        return {"status": "DELETED", "memory_id": memory_id, "success": success}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete memory: {str(e)}")

@router.get("/shared-patterns", response_model=List[SharedLearningPattern])
async def get_shared_learning_patterns():
    try:
        raw_patterns = await store.get_shared_patterns()
        return [SharedLearningPattern(**p) for p in raw_patterns]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve shared patterns: {str(e)}")
