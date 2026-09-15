from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field, ConfigDict
from datetime import datetime, timezone

class VerifiedClaim(BaseModel):
    """
    Atomic verified fact for the user. Cannot be fabricated by AI.
    """
    id: str
    person_id: str
    category: str  # EDUCATION, EXPERIENCE, PROJECT, SKILL, CREDENTIAL, AWARD, COMPETITION, PUBLICATION, PERFORMANCE, VOLUNTEERING, LEADERSHIP, PORTFOLIO, OTHER
    statement: str
    evidence_ids: List[str] = Field(default_factory=list)
    source: str
    source_url: Optional[str] = None
    verified_at: Optional[str] = None
    verification_status: str  # VERIFIED, PARTIALLY_VERIFIED, USER_STATED, INFERRED, UNVERIFIED, REJECTED, EXPIRED
    confidence: str  # HIGH, MODERATE, LOW
    provenance: str
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    model_config = ConfigDict(populate_by_name=True)

class PortfolioProject(BaseModel):
    """
    Domain-neutral portfolio entry.
    """
    id: str
    person_id: str
    title: str
    domain: str
    description: str
    evidence_ids: List[str] = Field(default_factory=list)
    skills_demonstrated: List[str] = Field(default_factory=list)
    outcome: str
    artifacts: List[str] = Field(default_factory=list)
    source: str
    verification_status: str  # VERIFIED, UNVERIFIED_PORTFOLIO_ITEM, etc.
    goal_relevance: str
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    model_config = ConfigDict(populate_by_name=True)

class ResumeRequirementAnalysis(BaseModel):
    requirement_name: str
    classification: str  # MATCHED, PARTIALLY_MATCHED, MISSING, UNKNOWN, NOT_RELEVANT
    matched_claim_ids: List[str] = Field(default_factory=list)
    missing_reason: Optional[str] = None

class ResumeFact(BaseModel):
    statement: str
    claim_ids: List[str] = Field(default_factory=list)
    evidence_ids: List[str] = Field(default_factory=list)
    generation_reason: str
    status: str = "DRAFT"  # DRAFT, APPROVED, REJECTED

class ResumeVersion(BaseModel):
    """
    Immutable snapshot of a generated resume state.
    """
    id: str
    person_id: str
    goal_id: str
    opportunity_id: Optional[str] = None
    version: int
    content: Dict[str, Any]  # The structured resume content
    claim_ids: List[str] = Field(default_factory=list)
    state: str = "DRAFT"  # DRAFT, REVIEW_REQUIRED, APPROVED, EXPORTED, ARCHIVED
    change_reason: str
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    model_config = ConfigDict(populate_by_name=True)
