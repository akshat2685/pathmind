from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field, ConfigDict, model_validator
from datetime import datetime, timezone
import uuid

class MemoryItem(BaseModel):
    """
    Canonical single-source-of-truth memory model for PATHMIND's Personal Second Brain.
    Preserves auditability, source linking, temporal validity, and evidence grounding.
    """
    memory_id: str = Field(default_factory=lambda: f"mem_{int(datetime.now(timezone.utc).timestamp()*1000)}_{uuid.uuid4().hex[:6]}")
    person_id: str
    memory_type: str = "EPISODIC"  # EPISODIC, SEMANTIC, LEARNING_EVENT, EVIDENCE, DECISION, GOAL, STRATEGY, CAREER, ARTIFACT, OPPORTUNITY, PREFERENCE, CONSTRAINT
    nature: str = "EXPERIENCE"  # EVENT, FACT, EXPERIENCE, DECISION, SKILL_KNOWLEDGE, STRATEGY, RESOURCE, GOAL, PREFERENCE, INFERENCE, UNKNOWN
    title: str
    content: str = ""
    summary: str = ""
    topic: str = "General"
    related_concepts: List[str] = Field(default_factory=list)
    source_type: str = "ROADMAP_STAGE"  # ASSESSMENT, ROADMAP_STAGE, EVIDENCE_SUBMISSION, ARTIFACT, CAREER_DECISION, EXECUTION_ACTION, OPPORTUNITY_APPLICATION, DIRECT_PREFERENCE, UNKNOWN
    source_reference: str = "General Milestone"
    source_event_id: Optional[str] = None
    source: str = "General Milestone"
    related_goal_ids: List[str] = Field(default_factory=list)
    related_skill_ids: List[str] = Field(default_factory=list)
    related_artifact_ids: List[str] = Field(default_factory=list)
    related_decision_ids: List[str] = Field(default_factory=list)
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    confidence: str = "HIGH"  # HIGH, MEDIUM, LOW, UNKNOWN
    importance: str = "HIGH"  # LOW, MEDIUM, HIGH, CRITICAL
    lifecycle_status: str = "CURRENT"  # CURRENT, HISTORICAL, SUPERSEDED, EXPIRED, UNKNOWN (also accepts ACTIVE)
    valid_from: Optional[str] = None
    valid_until: Optional[str] = None
    parent_memory_id: Optional[str] = None
    superseded_by: Optional[str] = None
    supersedes_reason: Optional[str] = None
    is_consolidated: bool = False
    consolidated_source_ids: List[str] = Field(default_factory=list)
    evidence_verification_status: str = "VERIFIED"  # VERIFIED, UNVERIFIED, OBSERVED, SELF_REPORTED
    details: Dict[str, Any] = Field(default_factory=dict)

    model_config = ConfigDict(populate_by_name=True, extra="allow")

    @model_validator(mode="before")
    @classmethod
    def sync_content_and_sources(cls, data: Any) -> Any:
        if isinstance(data, dict):
            if not data.get("content") and data.get("summary"):
                data["content"] = data["summary"]
            elif not data.get("summary") and data.get("content"):
                data["summary"] = data["content"]
            if not data.get("source_reference") and data.get("source"):
                data["source_reference"] = data["source"]
            elif not data.get("source") and data.get("source_reference"):
                data["source"] = data["source_reference"]
            # Map legacy ACTIVE to CURRENT
            if data.get("lifecycle_status") == "ACTIVE":
                data["lifecycle_status"] = "CURRENT"
        return data

class SharedLearningPattern(BaseModel):
    pattern_id: str
    topic: str
    misconception_or_context: str
    effective_intervention: str
    evidence_count: int = 1
    confidence: str = "HIGH"  # HIGH, MEDIUM, LOW
    extracted_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    model_config = ConfigDict(populate_by_name=True)

class MemoryRecallQuery(BaseModel):
    person_id: str = "scholar-user"
    query: str
    current_concept: Optional[str] = None

    model_config = ConfigDict(populate_by_name=True)

class MemoryRecallResponse(BaseModel):
    person_id: str
    query: str
    recalled_memories: List[MemoryItem] = Field(default_factory=list)
    answer: str
    grounded_concept_bridge: Optional[str] = None
    confidence: str = "HIGH"  # HIGH, MEDIUM, LOW

    model_config = ConfigDict(populate_by_name=True)

class CrossStageBridgeResponse(BaseModel):
    person_id: str
    current_concept: str
    past_concept: str
    past_stage: str
    context: str
    connection_explanation: str
    confidence: str = "HIGH"

    model_config = ConfigDict(populate_by_name=True)

class MemorySearchResultItem(BaseModel):
    memory: MemoryItem
    relevance_score: float
    relevance_reason: str
    provenance_chain: List[str] = Field(default_factory=list)

    model_config = ConfigDict(populate_by_name=True)

class SecondBrainQueryRequest(BaseModel):
    query: str
    current_task_context: Optional[str] = None
    target_role: Optional[str] = None

    model_config = ConfigDict(populate_by_name=True)

class SecondBrainQueryResponse(BaseModel):
    person_id: str
    query: str
    status: str = "RESOLVED"  # RESOLVED, NO_RELEVANT_MEMORY, INSUFFICIENT_HISTORY, INSUFFICIENT_CONTEXT, MEMORY_CONFLICT
    answer: str
    retrieved_memories: List[MemorySearchResultItem] = Field(default_factory=list)
    conflicting_memories: List[MemoryItem] = Field(default_factory=list)
    confidence: str = "HIGH"  # HIGH, MEDIUM, LOW
    concept_bridge: Optional[str] = None

    model_config = ConfigDict(populate_by_name=True)

class ConsolidateMemoriesRequest(BaseModel):
    topic: str
    source_memory_ids: List[str]
    consolidated_title: str
    consolidated_summary: str

    model_config = ConfigDict(populate_by_name=True)

class ConsolidateMemoriesResponse(BaseModel):
    consolidated_memory: MemoryItem
    archived_source_count: int

    model_config = ConfigDict(populate_by_name=True)

class SupersedeMemoryRequest(BaseModel):
    old_memory_id: Optional[str] = None
    reason: str
    new_memory_payload: Dict[str, Any]

    model_config = ConfigDict(populate_by_name=True)
