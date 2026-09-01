from fastapi import APIRouter, Depends, HTTPException, Header, Query
from typing import List, Dict, Any, Optional
from backend.core.memory_schemas import (
    MemoryItem,
    SharedLearningPattern,
    MemoryRecallQuery,
    MemoryRecallResponse,
    CrossStageBridgeResponse
)
from backend.services.memory_engine import MemoryEngine
from backend.services.store import FirestoreStore

router = APIRouter(prefix="/api/memory", tags=["Longitudinal Memory & Shared Intelligence"])
engine = MemoryEngine()
store = FirestoreStore()

def get_person_id(x_person_id: Optional[str] = Header(None)) -> str:
    if not x_person_id:
        return "demo-user"
    return x_person_id

@router.get("/personal", response_model=List[MemoryItem])
async def get_personal_memories(
    memory_type: Optional[str] = Query(None),
    topic: Optional[str] = Query(None),
    person_id: str = Depends(get_person_id)
):
    try:
        # Seed initial demo memories if person has none
        await engine.seed_demo_memories_if_needed(person_id)
        raw_mems = await store.get_personal_memories(person_id, memory_type=memory_type, topic=topic)
        return [MemoryItem(**m) for m in raw_mems]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve personal memories: {str(e)}")

@router.post("/events", response_model=MemoryItem)
async def ingest_learning_event(
    event_payload: Dict[str, Any],
    person_id: str = Depends(get_person_id)
):
    try:
        active_person_id = event_payload.get("person_id") or person_id
        mem = await engine.extract_and_store_memory_from_event(active_person_id, event_payload)
        return mem
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to ingest learning event: {str(e)}")

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

@router.post("/demo-seed", response_model=List[MemoryItem])
async def seed_demo_memories(person_id: str = Depends(get_person_id)):
    try:
        return await engine.seed_demo_memories_if_needed(person_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to seed demo memories: {str(e)}")
