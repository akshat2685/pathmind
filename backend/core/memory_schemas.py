from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field, ConfigDict
from datetime import datetime, timezone

class MemoryItem(BaseModel):
    memory_id: str
    person_id: str
    memory_type: str = "EPISODIC"  # EPISODIC, SEMANTIC_LEARNING, PREFERENCE, STRATEGY, GOAL, EVIDENCE
    title: str
    summary: str
    topic: str
    related_concepts: List[str] = Field(default_factory=list)
    source_event_id: Optional[str] = None
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    confidence: str = "HIGH"  # HIGH, MEDIUM, LOW
    importance: str = "HIGH"  # LOW, MEDIUM, HIGH, CRITICAL
    lifecycle_status: str = "ACTIVE"  # NEW, ACTIVE, UPDATED, SUPERSEDED, ARCHIVED
    valid_from: Optional[str] = None
    valid_until: Optional[str] = None
    source: str = "Learning Milestone"
    details: Dict[str, Any] = Field(default_factory=dict)

    model_config = ConfigDict(populate_by_name=True)

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
    person_id: str = "demo-user"
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
