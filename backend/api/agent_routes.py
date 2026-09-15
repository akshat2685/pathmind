from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Any, Optional

from backend.core.security import get_authenticated_person
from backend.services.adk_agents import RootAgentRunner
from backend.services.store import FirestoreStore

router = APIRouter(prefix="/api/agent", tags=["ADK Agent Orchestration"])

class AgentInteractRequest(BaseModel):
    message: str
    state: Optional[Dict[str, Any]] = None

class AgentInteractResponse(BaseModel):
    message: str
    state: Dict[str, Any]
    ui_blocks: List[str]

store = FirestoreStore()
agent_runner = RootAgentRunner(store=store)

@router.post("/interact", response_model=AgentInteractResponse)
async def interact_with_agent(
    request: AgentInteractRequest,
    person_id: str = Depends(get_authenticated_person)
):
    try:
        response = await agent_runner.run(
            person_id=person_id, 
            message=request.message, 
            client_state=request.state
        )
        return AgentInteractResponse(**response)
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Agent interaction failed: {str(e)}")
