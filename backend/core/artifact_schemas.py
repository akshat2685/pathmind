from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field, ConfigDict
from datetime import datetime, timezone

class ArtifactObservation(BaseModel):
    observation_id: str = Field(default_factory=lambda: f"obs_{int(datetime.now(timezone.utc).timestamp()*1000)}")
    category: str = "TECHNOLOGY"  # TECHNOLOGY, ARCHITECTURE, DOCUMENTATION, TESTING, DEPLOYMENT, METHODOLOGY
    detail: str
    is_demonstrated: bool = True  # True if found in code/manifests; False if only mentioned in text
    basis_file_or_snippet: Optional[str] = None

    model_config = ConfigDict(populate_by_name=True)

class ArtifactCapabilityMapping(BaseModel):
    capability_name: str
    basis: str
    confidence: str = "HIGH"  # HIGH, MEDIUM, LOW
    status: str = "OBSERVED"  # OBSERVED (direct code proof), INFERRED (logical deduction), NOT_DETERMINABLE
    canonical_skill_id: Optional[str] = None
    is_promoted_to_evidence: bool = False
    evidence_id: Optional[str] = None

    model_config = ConfigDict(populate_by_name=True)

class ArtifactQualityDimensions(BaseModel):
    completeness: str = "MODERATE"  # HIGH, MODERATE, LOW, INSUFFICIENT
    complexity: str = "MODERATE"  # ADVANCED, MODERATE, BASIC
    implementation_depth: str = "MODERATE"  # DEEP, MODERATE, SHALLOW
    documentation_quality: str = "MODERATE"  # COMPREHENSIVE, MODERATE, MINIMAL, MISSING
    testing_evidence: str = "NONE"  # AUTOMATED_UNIT_TESTS, INTEGRATION_TESTS, MANUAL_ONLY, NONE
    deployment_evidence: str = "NONE"  # LIVE_URL, CI_CD_WORKFLOW, DOCKERFILE, NONE
    maintenance_activity: str = "ACTIVE"  # ACTIVE, OCCASIONAL, STALE, INSUFFICIENT_DATA

    model_config = ConfigDict(populate_by_name=True)

class ArtifactAnalysisResult(BaseModel):
    artifact_id: str
    observations: List[ArtifactObservation] = Field(default_factory=list)
    potential_capabilities: List[ArtifactCapabilityMapping] = Field(default_factory=list)
    unverified_claims: List[str] = Field(default_factory=list)  # Technologies/skills mentioned but not proved
    verification_gaps: List[str] = Field(default_factory=list)  # What's missing to prove true mastery
    dimensions: ArtifactQualityDimensions = Field(default_factory=ArtifactQualityDimensions)
    recommended_followup: List[str] = Field(default_factory=list)
    analyzed_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    model_config = ConfigDict(populate_by_name=True)

class CanonicalArtifact(BaseModel):
    artifact_id: str = Field(default_factory=lambda: f"art_{int(datetime.now(timezone.utc).timestamp()*1000)}")
    person_id: str
    type: str = "PROJECT"  # PROJECT, CODE_REPOSITORY, DOCUMENT, PRESENTATION, PORTFOLIO, RESEARCH_ARTIFACT, WORK_SAMPLE, CREDENTIAL, CERTIFICATE, ARTICLE, DESIGN, VIDEO, OTHER_SUPPORTED_ARTIFACT
    title: str
    description: str
    source: str = "USER_UPLOAD"  # GITHUB, USER_UPLOAD, PORTFOLIO_URL, CREDENTIAL_PROVIDER
    source_reference: str  # Repo URL, file path, certificate ID, website URL
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    verification_status: str = "UNVERIFIED"  # VERIFIED, PARTIALLY_VERIFIED, UNVERIFIED, FAILED_VERIFICATION, REVOKED
    ownership_status: str = "UNVERIFIED"  # VERIFIED, PARTIALLY_VERIFIED, UNVERIFIED, FAILED_VERIFICATION
    visibility: str = "PORTFOLIO_VISIBLE"  # PUBLIC, PRIVATE, PORTFOLIO_VISIBLE
    content_reference: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
    provenance: Dict[str, Any] = Field(default_factory=dict)
    version: int = 1
    history: List[Dict[str, Any]] = Field(default_factory=list)
    analysis: Optional[ArtifactAnalysisResult] = None

    model_config = ConfigDict(populate_by_name=True)

class DefenseQuestion(BaseModel):
    question_id: str = Field(default_factory=lambda: f"q_{int(datetime.now(timezone.utc).timestamp()*1000)}")
    category: str = "ARCHITECTURE"  # ARCHITECTURE, TRADEOFF, DEBUGGING, TESTING, SECURITY, SCALABILITY
    prompt: str
    target_capability: str
    evaluation_criteria: List[str] = Field(default_factory=list)

    model_config = ConfigDict(populate_by_name=True)

class DefenseAnswer(BaseModel):
    question_id: str
    answer_text: str

    model_config = ConfigDict(populate_by_name=True)

class ArtifactDefenseSession(BaseModel):
    session_id: str = Field(default_factory=lambda: f"def_{int(datetime.now(timezone.utc).timestamp()*1000)}")
    artifact_id: str
    person_id: str
    target_role: Optional[str] = None
    questions: List[DefenseQuestion] = Field(default_factory=list)
    answers: List[DefenseAnswer] = Field(default_factory=list)
    status: str = "IN_PROGRESS"  # IN_PROGRESS, EVALUATED, DEFENSE_ACCEPTED, DEFENSE_REJECTED
    evaluation_feedback: Optional[str] = None
    capabilities_upgraded: List[str] = Field(default_factory=list)
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    evaluated_at: Optional[str] = None

    model_config = ConfigDict(populate_by_name=True)

class ClaimValidationRequest(BaseModel):
    claim_text: str
    target_capability: Optional[str] = None

class ClaimValidationResult(BaseModel):
    claim_id: str = Field(default_factory=lambda: f"claim_{int(datetime.now(timezone.utc).timestamp()*1000)}")
    person_id: str
    claim_text: str
    status: str = "UNVERIFIED"  # SUPPORTED, PARTIALLY_SUPPORTED, UNVERIFIED, CONTRADICTED
    supporting_artifacts: List[str] = Field(default_factory=list)
    contradicting_evidence: List[str] = Field(default_factory=list)
    missing_proof: List[str] = Field(default_factory=list)
    reasoning: str
    validated_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    model_config = ConfigDict(populate_by_name=True)

class PortfolioProjectCard(BaseModel):
    artifact_id: str
    title: str
    type: str
    source: str
    source_reference: str
    verification_status: str
    ownership_status: str
    demonstrated_capabilities: List[str] = Field(default_factory=list)
    inferred_capabilities: List[str] = Field(default_factory=list)
    role_relevance_score: float = 0.0  # 0.0 to 100.0
    role_fit_reason: Optional[str] = None
    evidence_strength: str = "MODERATE"
    version: int = 1

    model_config = ConfigDict(populate_by_name=True)

class PortfolioGraphResponse(BaseModel):
    person_id: str
    total_artifacts: int = 0
    verified_count: int = 0
    artifacts: List[PortfolioProjectCard] = Field(default_factory=list)
    top_recommended_for_role: Dict[str, List[str]] = Field(default_factory=dict)  # role -> list of artifact_ids
    generated_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    model_config = ConfigDict(populate_by_name=True)
