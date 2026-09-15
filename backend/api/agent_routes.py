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
    ui_blocks: List[Dict[str, Any]]

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
        if "429" in str(e) or "ResourceExhausted" in str(e) or "Quota exceeded" in str(e):
            return AgentInteractResponse(
                message="I'm sorry, but my AI reasoning engine has exceeded its daily quota (Google Gemini Free Tier limit reached). Please upgrade the API key or try again tomorrow.",
                state={"status": "API_QUOTA_EXHAUSTED"},
                ui_blocks=[{"type": "ERROR", "data": {"error_code": "429_QUOTA_EXCEEDED"}}]
            )
        raise HTTPException(status_code=500, detail=f"Agent interaction failed: {str(e)}")
