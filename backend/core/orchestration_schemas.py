import uuid
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field, ConfigDict
from datetime import datetime, timezone

class AgentContract(BaseModel):
    agent_id: str
    name: str
    purpose: str
    allowed_inputs: List[str] = Field(default_factory=list)
    allowed_tools: List[str] = Field(default_factory=list)
    output_schema: str
    side_effects: List[str] = Field(default_factory=list)
    forbidden_operations: List[str] = Field(default_factory=list)
    dependencies: List[str] = Field(default_factory=list)
    failure_states: List[str] = Field(default_factory=list)

    model_config = ConfigDict(populate_by_name=True)

class ActionProposal(BaseModel):
    proposal_id: str = Field(default_factory=lambda: f"prop_{int(datetime.now(timezone.utc).timestamp()*1000)}_{uuid.uuid4().hex[:6]}")
    workflow_id: str
    person_id: str
    action_type: str  # UPDATE_GOAL, CREATE_ROADMAP_VERSION, UNLOCK_STAGE, SPAWN_EXECUTION_ACTION, PROMOTE_EVIDENCE, UPDATE_PREFERENCE
    target_entity: str
    target_entity_id: str
    proposed_change: Dict[str, Any]
    reason: str
    supporting_evidence: List[str] = Field(default_factory=list)
    requires_confirmation: bool = True
    status: str = "PENDING"  # PENDING, APPROVED, REJECTED, APPLIED
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    model_config = ConfigDict(populate_by_name=True)

class AgentStepTrace(BaseModel):
    step_id: str = Field(default_factory=lambda: f"step_{uuid.uuid4().hex[:8]}")
    agent_id: str
    status: str = "SUCCESS"  # SUCCESS, PARTIAL, FAILED, TIMEOUT, RATE_LIMITED, SOURCE_UNAVAILABLE, REQUIRES_INPUT, INVALID_OUTPUT, CANCELLED
    input_summary: str
    output_summary: str
    duration_ms: int = 0
    error: Optional[str] = None
    action_proposals: List[ActionProposal] = Field(default_factory=list)

    model_config = ConfigDict(populate_by_name=True)

class OrchestrationTrace(BaseModel):
    workflow_id: str
    person_id: str
    task_type: str
    status: str = "SUCCESS"  # SUCCESS, PARTIAL, FAILED, WAITING_FOR_USER_APPROVAL, TIMEOUT, ORCHESTRATION_LOOP_DETECTED
    started_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    completed_at: Optional[str] = None
    total_duration_ms: int = 0
    steps: List[AgentStepTrace] = Field(default_factory=list)
    agents_invoked: List[str] = Field(default_factory=list)
    action_proposals: List[ActionProposal] = Field(default_factory=list)
    cost_metrics: Dict[str, Any] = Field(default_factory=dict)

    model_config = ConfigDict(populate_by_name=True)

class OrchestrationRequest(BaseModel):
    task_type: Optional[str] = None
    intent: str
    payload: Dict[str, Any] = Field(default_factory=dict)
    idempotency_key: Optional[str] = None

    model_config = ConfigDict(populate_by_name=True)

class OrchestrationResponse(BaseModel):
    workflow_id: str
    person_id: str
    task_type: str
    status: str  # SUCCESS, PARTIAL, FAILED, WAITING_FOR_USER_APPROVAL, TIMEOUT
    final_answer: str
    structured_result: Dict[str, Any] = Field(default_factory=dict)
    action_proposals: List[ActionProposal] = Field(default_factory=list)
    requires_approval: bool = False
    trace: OrchestrationTrace

    model_config = ConfigDict(populate_by_name=True)
