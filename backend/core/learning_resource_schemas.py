from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field, ConfigDict
from datetime import datetime, timezone

class VerifiedResource(BaseModel):
    resource_id: str
    title: str
    url: str  # Must be an authentic, verified URL
    resource_type: str  # YOUTUBE_VIDEO, GITHUB_REPO, OFFICIAL_DOCS, INTERACTIVE_LAB
    channel_or_author: str
    description: str
    estimated_minutes: int = 45
    verified_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    model_config = ConfigDict(populate_by_name=True)

class ProceduralLearningStep(BaseModel):
    step_number: int  # 1, 2, 3, 4
    title: str  # e.g. "Step 1: Conceptual Foundation & Video Deep-Dive"
    phase_category: str  # THEORY, CODE_STUDY, HANDS_ON, VERIFICATION
    instruction: str  # Precise instructions on what to do first, then next
    primary_resource: VerifiedResource
    additional_resources: List[VerifiedResource] = Field(default_factory=list)
    required_evidence_type: str  # e.g., CODE_REPO, WRITTEN_DEFENSE, TEST_EXECUTION_OUTPUT
    verification_criteria: List[str] = Field(default_factory=list)

    model_config = ConfigDict(populate_by_name=True)

class PhaseLearningGuide(BaseModel):
    stage_id: str
    stage_title: str
    phase_number: int = 1
    target_capability: str
    procedural_steps: List[ProceduralLearningStep] = Field(default_factory=list)
    verified_resources: List[VerifiedResource] = Field(default_factory=list)
    agent_note: str

    model_config = ConfigDict(populate_by_name=True)

class StepVerificationSubmission(BaseModel):
    stage_id: str
    step_number: int
    payload: Dict[str, Any] = Field(default_factory=dict)  # {"code": ..., "repo_url": ..., "explanation": ..., "tests_output": ...}

class StepVerificationResult(BaseModel):
    verification_id: str = Field(default_factory=lambda: f"vstep_{int(datetime.now(timezone.utc).timestamp()*1000)}")
    stage_id: str
    step_number: int
    person_id: str
    status: str = "VERIFIED"  # VERIFIED, REINFORCE_REQUIRED, INSUFFICIENT_EVIDENCE
    observed_facts: List[str] = Field(default_factory=list)
    missing_criteria: List[str] = Field(default_factory=list)
    agent_feedback: str
    agent_learned_insight: str  # What the personal agent learned about the student's problem solving
    verified_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    model_config = ConfigDict(populate_by_name=True)
