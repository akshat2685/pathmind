from fastapi import APIRouter, Depends, HTTPException, Header, Query
from typing import List, Dict, Any, Optional
from pydantic import BaseModel

from backend.core.artifact_schemas import (
    CanonicalArtifact,
    ArtifactDefenseSession,
    ClaimValidationRequest,
    ClaimValidationResult,
    PortfolioGraphResponse
)
from backend.core.evidence_schemas import CanonicalEvidence
from backend.core.learning_resource_schemas import (
    PhaseLearningGuide,
    StepVerificationSubmission,
    StepVerificationResult
)
from backend.services.artifact_service import ArtifactService
from backend.services.step_verification_service import StepVerificationService

from backend.core.security import get_authenticated_person, validate_safe_url, sanitize_external_content

router = APIRouter(prefix="/api/artifacts", tags=["Artifact Intelligence & Verified Portfolio"])
artifact_service = ArtifactService()
step_verification_service = StepVerificationService()
get_person_id = get_authenticated_person

class IngestArtifactRequest(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    source: Optional[str] = "GITHUB"
    url: Optional[str] = None
    source_reference: Optional[str] = None
    artifact_type: Optional[str] = "PROJECT"
    content_text: Optional[str] = None
    languages: Optional[Dict[str, int]] = None
    has_tests: Optional[bool] = False
    has_ci: Optional[bool] = False
    issuer: Optional[str] = None
    credential_id: Optional[str] = None
    credential_url: Optional[str] = None
    recipient_name: Optional[str] = None

class PromoteEvidenceRequest(BaseModel):
    capability_name: str
    stage_id: Optional[str] = "stage_general"

class DefenseSubmissionRequest(BaseModel):
    session_id: str
    answers: List[Dict[str, str]]

@router.post("/ingest", response_model=CanonicalArtifact)
async def ingest_artifact(
    req: IngestArtifactRequest,
    person_id: str = Depends(get_person_id)
):
    # SSRF & Injection Validation
    if req.url and not validate_safe_url(req.url):
        raise HTTPException(status_code=400, detail="INVALID_URL: Target URL failed SSRF security verification.")
    if req.credential_url and not validate_safe_url(req.credential_url):
        raise HTTPException(status_code=400, detail="INVALID_URL: Target credential URL failed SSRF security verification.")

    try:
        payload = req.model_dump()
        if payload.get("content_text"):
            payload["content_text"] = sanitize_external_content(payload["content_text"])
        person_context = {
            "name": "Scholar User",
            "github_username": person_id if person_id != "scholar-user" else "scholar-user"
        }
        return await artifact_service.ingest_artifact(person_id, payload, person_context)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to ingest artifact: {str(e)}")

@router.get("", response_model=List[CanonicalArtifact])
async def list_artifacts(
    artifact_type: Optional[str] = Query(None),
    person_id: str = Depends(get_person_id)
):
    try:
        raw = await artifact_service.store.get_person_artifacts(person_id, artifact_type)
        return [CanonicalArtifact(**a) for a in raw]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list artifacts: {str(e)}")

@router.get("/portfolio", response_model=PortfolioGraphResponse)
async def get_portfolio_graph(
    target_role: Optional[str] = Query(None),
    person_id: str = Depends(get_person_id)
):
    try:
        return await artifact_service.get_portfolio_graph(person_id, target_role)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate portfolio graph: {str(e)}")

@router.get("/learning-guide/{stage_id}", response_model=PhaseLearningGuide)
async def get_learning_guide(
    stage_id: str,
    stage_title: Optional[str] = Query("Python & Backend Systems"),
    person_id: str = Depends(get_person_id)
):
    try:
        return step_verification_service.generate_learning_guide(stage_id, stage_title)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate learning guide: {str(e)}")

@router.post("/verify-step", response_model=StepVerificationResult)
async def verify_step(
    submission: StepVerificationSubmission,
    person_id: str = Depends(get_person_id)
):
    try:
        return await step_verification_service.verify_step(person_id, submission)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Step verification failed: {str(e)}")

@router.get("/step-verifications", response_model=List[StepVerificationResult])
async def get_step_verifications(
    stage_id: Optional[str] = Query(None),
    person_id: str = Depends(get_person_id)
):
    try:
        raw = await artifact_service.store.get_step_verifications(person_id, stage_id)
        return [StepVerificationResult(**s) for s in raw]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve step verifications: {str(e)}")

@router.get("/{artifact_id}", response_model=CanonicalArtifact)
async def get_artifact_detail(
    artifact_id: str,
    person_id: str = Depends(get_person_id)
):
    art_dict = await artifact_service.store.get_canonical_artifact(person_id, artifact_id)
    if not art_dict:
        raise HTTPException(status_code=404, detail=f"Artifact {artifact_id} not found.")
    return CanonicalArtifact(**art_dict)

@router.post("/{artifact_id}/promote-evidence", response_model=CanonicalEvidence)
async def promote_capability(
    artifact_id: str,
    req: PromoteEvidenceRequest,
    person_id: str = Depends(get_person_id)
):
    try:
        return await artifact_service.promote_capability_to_evidence(
            person_id=person_id,
            artifact_id=artifact_id,
            capability_name=req.capability_name,
            stage_id=req.stage_id or "stage_general"
        )
    except ValueError as ve:
        raise HTTPException(status_code=404, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Evidence promotion failed: {str(e)}")

@router.post("/{artifact_id}/defense/start", response_model=ArtifactDefenseSession)
async def start_defense(
    artifact_id: str,
    target_role: Optional[str] = Query(None),
    person_id: str = Depends(get_person_id)
):
    try:
        return await artifact_service.start_artifact_defense(person_id, artifact_id, target_role)
    except ValueError as ve:
        raise HTTPException(status_code=404, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to start artifact defense: {str(e)}")

@router.post("/{artifact_id}/defense/submit", response_model=ArtifactDefenseSession)
async def submit_defense(
    artifact_id: str,
    req: DefenseSubmissionRequest,
    person_id: str = Depends(get_person_id)
):
    try:
        return await artifact_service.submit_artifact_defense(person_id, req.session_id, req.answers)
    except ValueError as ve:
        raise HTTPException(status_code=404, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to submit defense: {str(e)}")

@router.post("/claim-validation", response_model=ClaimValidationResult)
async def validate_claim(
    req: ClaimValidationRequest,
    person_id: str = Depends(get_person_id)
):
    try:
        return await artifact_service.validate_claim(person_id, req.claim_text)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Claim validation failed: {str(e)}")

@router.delete("/{artifact_id}")
async def revoke_artifact(
    artifact_id: str,
    person_id: str = Depends(get_person_id)
):
    success = await artifact_service.revoke_or_delete_artifact(person_id, artifact_id)
    if not success:
        raise HTTPException(status_code=404, detail=f"Artifact {artifact_id} not found.")
    return {"status": "REVOKED", "artifact_id": artifact_id}
