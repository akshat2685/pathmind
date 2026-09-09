import re
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timezone

from backend.core.artifact_schemas import (
    CanonicalArtifact,
    ArtifactObservation,
    ArtifactCapabilityMapping,
    ArtifactQualityDimensions,
    ArtifactAnalysisResult,
    ArtifactDefenseSession,
    DefenseQuestion,
    DefenseAnswer,
    ClaimValidationResult,
    PortfolioProjectCard,
    PortfolioGraphResponse
)
from backend.core.evidence_schemas import CanonicalEvidence, SkillMasteryProfile
from backend.providers.artifact_provider import (
    BaseArtifactProvider,
    GitHubArtifactProvider,
    UserUploadArtifactProvider,
    CredentialArtifactProvider
)
from backend.services.artifact_analysis_agent import ArtifactAnalysisAgent
from backend.services.store import FirestoreStore
from backend.services.memory_engine import MemoryEngine

class ArtifactService:
    """
    Central Artifact Intelligence, Verification & Portfolio Service.
    Integrates provider adapters, Google ADK artifact analysis, defense mode,
    claim validation, and canonical evidence promotion.
    """
    def __init__(
        self,
        store: Optional[FirestoreStore] = None,
        analysis_agent: Optional[ArtifactAnalysisAgent] = None,
        memory_engine: Optional[MemoryEngine] = None
    ):
        self.store = store or FirestoreStore()
        self.analysis_agent = analysis_agent or ArtifactAnalysisAgent()
        self.memory_engine = memory_engine or MemoryEngine()
        self.providers: Dict[str, BaseArtifactProvider] = {
            "GITHUB": GitHubArtifactProvider(),
            "USER_UPLOAD": UserUploadArtifactProvider(),
            "CREDENTIAL_PROVIDER": CredentialArtifactProvider()
        }

    def _get_provider(self, source_type: str) -> BaseArtifactProvider:
        return self.providers.get(source_type.upper(), self.providers["USER_UPLOAD"])

    def _normalize_url(self, url: str) -> str:
        clean = url.strip().lower()
        if clean.endswith("/"):
            clean = clean[:-1]
        if clean.endswith(".git"):
            clean = clean[:-4]
        return clean

    async def ingest_artifact(
        self,
        person_id: str,
        payload: Dict[str, Any],
        person_context: Optional[Dict[str, Any]] = None
    ) -> CanonicalArtifact:
        """
        Full Pipeline: Ingest -> Normalize -> Verify Ownership -> Extract Observations -> Analyze -> Persist
        """
        source_type = payload.get("source", "GITHUB").upper()
        if "github.com" in str(payload.get("url", "")).lower() or "github.com" in str(payload.get("source_reference", "")).lower():
            source_type = "GITHUB"
        elif payload.get("credential_id") or payload.get("issuer"):
            source_type = "CREDENTIAL_PROVIDER"

        provider = self._get_provider(source_type)
        person_ctx = person_context or {"name": "Scholar User", "github_username": "scholar-user"}

        # 1. Normalize
        artifact = await provider.normalize_and_ingest(person_id, payload)

        # 2. Verify Ownership
        ownership_status, reason = await provider.verify_ownership(artifact, person_ctx)
        artifact.ownership_status = ownership_status
        artifact.provenance["ownership_reason"] = reason

        # 3. Extract Observations
        observations = await provider.extract_observations(artifact)

        # 4. Derive Quality Dimensions
        dimensions = provider.derive_quality_dimensions(artifact)

        # 5. ADK Agent Analysis (Separates OBSERVED vs INFERRED and flags gaps)
        analysis_result = await self.analysis_agent.analyze_artifact(artifact, observations, dimensions)
        artifact.analysis = analysis_result

        # Overall Verification Status
        if ownership_status == "VERIFIED" and any(o.is_demonstrated for o in observations):
            artifact.verification_status = "VERIFIED"
        elif ownership_status in ["VERIFIED", "PARTIALLY_VERIFIED"]:
            artifact.verification_status = "PARTIALLY_VERIFIED"
        else:
            artifact.verification_status = "UNVERIFIED"

        # 6. Duplicate Detection & Versioning
        existing_artifacts = await self.store.get_person_artifacts(person_id)
        norm_ref = self._normalize_url(artifact.source_reference)
        matching_existing = next(
            (a for a in existing_artifacts if self._normalize_url(a.get("source_reference", "")) == norm_ref),
            None
        )

        if matching_existing:
            # Upgrade existing version rather than creating duplicate
            artifact.artifact_id = matching_existing["artifact_id"]
            artifact.version = matching_existing.get("version", 1) + 1
            artifact.history = matching_existing.get("history", [])
            artifact.history.append({
                "version": matching_existing.get("version", 1),
                "archived_at": datetime.now(timezone.utc).isoformat(),
                "observations_count": len(matching_existing.get("analysis", {}).get("observations", []))
            })

        # 7. Persist
        await self.store.save_canonical_artifact(person_id, artifact.model_dump())

        # 8. Longitudinal & Memory Integration
        if artifact.verification_status == "VERIFIED":
            await self.memory_engine.extract_and_store_memory_from_event(
                person_id=person_id,
                event_payload={
                    "topic": f"Verified Technical Artifact: {artifact.title}",
                    "milestone": f"Ingested and verified {artifact.type} ({artifact.source_reference}) with confirmed ownership.",
                    "source": "ArtifactService",
                    "capabilities": [c.capability_name for c in analysis_result.potential_capabilities if c.status == "OBSERVED"]
                }
            )

        return artifact

    async def promote_capability_to_evidence(
        self,
        person_id: str,
        artifact_id: str,
        capability_name: str,
        stage_id: str = "stage_general"
    ) -> CanonicalEvidence:
        artifact_dict = await self.store.get_canonical_artifact(person_id, artifact_id)
        if not artifact_dict:
            raise ValueError(f"Artifact {artifact_id} not found for person {person_id}.")

        artifact = CanonicalArtifact(**artifact_dict)
        if not artifact.analysis:
            raise ValueError("Artifact has not been analyzed yet.")

        target_cap = next(
            (c for c in artifact.analysis.potential_capabilities if c.capability_name.lower() == capability_name.lower()),
            None
        )
        if not target_cap:
            # Create ad-hoc capability from observed tech
            target_cap = ArtifactCapabilityMapping(
                capability_name=capability_name,
                basis=f"Promoted directly from verified artifact {artifact.title}.",
                confidence="HIGH",
                status="OBSERVED" if artifact.verification_status == "VERIFIED" else "INFERRED"
            )

        # Build CanonicalEvidence
        is_verified = artifact.verification_status == "VERIFIED" and target_cap.status == "OBSERVED"
        evidence = CanonicalEvidence(
            person_id=person_id,
            evidence_type="PORTFOLIO_ARTIFACT",
            title=f"{artifact.title} — {target_cap.capability_name}",
            description=f"Evidence derived from authentic {artifact.source} artifact: {target_cap.basis}",
            source="OFFICIAL_PROVIDER" if artifact.source == "CREDENTIAL_PROVIDER" else "USER_SUBMISSION",
            source_reference=artifact.source_reference,
            related_skill_ids=[target_cap.capability_name],
            related_stage_id=stage_id,
            verification_status="VERIFIED" if is_verified else "UNVERIFIED",
            quality="VERIFIED_STRONG" if is_verified else "STRONG",
            strength="HIGH" if is_verified else "MEDIUM",
            confidence="HIGH",
            metadata={
                "artifact_id": artifact.artifact_id,
                "artifact_type": artifact.type,
                "version": artifact.version
            }
        )

        await self.store.save_canonical_evidence(person_id, evidence.model_dump())

        # Update Skill Mastery Profile
        mastery_state = "APPLICATION" if is_verified else "UNDERSTANDING"
        skill_profile = SkillMasteryProfile(
            skill_name=target_cap.capability_name,
            category=artifact.title,
            mastery_state=mastery_state,
            evidence_count=1,
            primary_evidence_id=evidence.evidence_id,
            is_regression_risk=False
        )
        await self.store.save_skill_mastery_profile(person_id, target_cap.capability_name, skill_profile.model_dump())

        # Update artifact record with promotion status
        target_cap.is_promoted_to_evidence = True
        target_cap.evidence_id = evidence.evidence_id
        await self.store.save_canonical_artifact(person_id, artifact.model_dump())

        return evidence

    async def start_artifact_defense(
        self,
        person_id: str,
        artifact_id: str,
        target_role: Optional[str] = None
    ) -> ArtifactDefenseSession:
        artifact_dict = await self.store.get_canonical_artifact(person_id, artifact_id)
        if not artifact_dict:
            raise ValueError(f"Artifact {artifact_id} not found.")

        artifact = CanonicalArtifact(**artifact_dict)
        meta = artifact.metadata
        languages = list(meta.get("languages", {}).keys()) or ["Architecture"]
        primary_lang = languages[0] if languages else "Core Stack"

        questions: List[DefenseQuestion] = [
            DefenseQuestion(
                category="ARCHITECTURE",
                prompt=f"Explain the high-level architecture of {artifact.title}. Why did you choose {primary_lang} and how are key modules separated?",
                target_capability=f"{primary_lang} Architecture",
                evaluation_criteria=["Clarity of module separation", "Explicit architectural rationale", "Component boundaries"]
            ),
            DefenseQuestion(
                category="TRADEOFF",
                prompt="What was the most significant technical tradeoff you encountered during development, and why did you reject the primary alternative?",
                target_capability="Engineering Tradeoff Analysis",
                evaluation_criteria=["Identification of alternative solution", "Discussion of constraints", "Objective evaluation criteria"]
            ),
            DefenseQuestion(
                category="DEBUGGING",
                prompt="Describe the most challenging bug or edge-case you resolved in this codebase. What diagnostic tools or mental models did you use?",
                target_capability="Root Cause Debugging",
                evaluation_criteria=["Precise symptom description", "Root cause explanation", "Verification test or fix confirmation"]
            )
        ]

        session = ArtifactDefenseSession(
            artifact_id=artifact_id,
            person_id=person_id,
            target_role=target_role,
            questions=questions,
            status="IN_PROGRESS"
        )
        await self.store.save_defense_session(person_id, session.model_dump())
        return session

    async def submit_artifact_defense(
        self,
        person_id: str,
        session_id: str,
        answers: List[Dict[str, str]]
    ) -> ArtifactDefenseSession:
        session_dict = await self.store.get_defense_session(person_id, session_id)
        if not session_dict:
            raise ValueError(f"Defense session {session_id} not found.")

        session = ArtifactDefenseSession(**session_dict)
        session.answers = [DefenseAnswer(question_id=a.get("question_id", ""), answer_text=a.get("answer_text", "")) for a in answers]
        session.evaluated_at = datetime.now(timezone.utc).isoformat()

        # Evaluate answers (Zero-assumption heuristic: requires substantive technical answers)
        valid_answers = [a for a in session.answers if len(a.answer_text.strip()) >= 50 and any(w in a.answer_text.lower() for w in ["because", "architecture", "state", "tradeoff", "tested", "design", "bug"])]

        if len(valid_answers) >= 2:
            session.status = "DEFENSE_ACCEPTED"
            session.evaluation_feedback = "Technical defense successfully demonstrated! You articulated sound architectural rationale and engineering tradeoffs."
            
            # Upgrade capabilities
            artifact_dict = await self.store.get_canonical_artifact(person_id, session.artifact_id)
            if artifact_dict:
                artifact = CanonicalArtifact(**artifact_dict)
                upgraded: List[str] = []
                if artifact.analysis:
                    for cap in artifact.analysis.potential_capabilities:
                        if cap.status == "INFERRED":
                            cap.status = "OBSERVED"
                            upgraded.append(cap.capability_name)
                    artifact.verification_status = "VERIFIED"
                    artifact.ownership_status = "VERIFIED"
                    await self.store.save_canonical_artifact(person_id, artifact.model_dump())
                session.capabilities_upgraded = upgraded or ["Demonstrated Code Authorship"]
        else:
            session.status = "DEFENSE_REJECTED"
            session.evaluation_feedback = "Defense answers were too brief or lacked concrete technical reasoning. Please elaborate on your architectural tradeoffs and debugging process."

        await self.store.save_defense_session(person_id, session.model_dump())
        return session

    async def validate_claim(
        self,
        person_id: str,
        claim_text: str
    ) -> ClaimValidationResult:
        artifacts_raw = await self.store.get_person_artifacts(person_id)
        artifacts = [CanonicalArtifact(**a) for a in artifacts_raw]

        claim_lower = claim_text.lower()
        supporting: List[str] = []
        contradicting: List[str] = []
        missing: List[str] = []

        for art in artifacts:
            art_text = f"{art.title} {art.description} {str(art.metadata)}".lower()
            if any(term in art_text for term in claim_lower.split() if len(term) > 4):
                if art.verification_status == "VERIFIED":
                    supporting.append(f"{art.title} ({art.source_reference})")
                else:
                    missing.append(f"{art.title} is unverified or lacks confirmed ownership.")

        if supporting:
            status = "SUPPORTED"
            reasoning = f"Claim is directly supported by {len(supporting)} verified project artifacts: {', '.join(supporting[:2])}."
        elif missing:
            status = "PARTIALLY_SUPPORTED"
            reasoning = f"Project mentions related concepts, but verification is incomplete: {', '.join(missing[:2])}."
        else:
            status = "UNVERIFIED"
            reasoning = "No ingested or verified artifacts in the learner's portfolio provide evidence supporting this claim."

        result = ClaimValidationResult(
            person_id=person_id,
            claim_text=claim_text,
            status=status,
            supporting_artifacts=supporting,
            contradicting_evidence=contradicting,
            missing_proof=missing,
            reasoning=reasoning
        )
        await self.store.save_claim_validation(person_id, result.model_dump())
        return result

    async def get_portfolio_graph(
        self,
        person_id: str,
        target_role: Optional[str] = None
    ) -> PortfolioGraphResponse:
        raw_artifacts = await self.store.get_person_artifacts(person_id)
        artifacts = [CanonicalArtifact(**a) for a in raw_artifacts]

        role = target_role or "Full-Stack Software Engineer"
        cards: List[PortfolioProjectCard] = []
        role_ranking: List[str] = []

        for art in artifacts:
            demo_caps = [c.capability_name for c in art.analysis.potential_capabilities if c.status == "OBSERVED"] if art.analysis else []
            inf_caps = [c.capability_name for c in art.analysis.potential_capabilities if c.status == "INFERRED"] if art.analysis else []

            # Compute role relevance score based on skill overlap
            role_keywords = ["python", "api", "react", "backend", "frontend", "full-stack", "system", "test", "docker"]
            overlap = sum(1 for kw in role_keywords if kw in art.title.lower() or any(kw in c.lower() for c in demo_caps))
            score = min(100.0, 40.0 + (overlap * 20.0)) if art.verification_status == "VERIFIED" else min(70.0, 20.0 + (overlap * 15.0))

            card = PortfolioProjectCard(
                artifact_id=art.artifact_id,
                title=art.title,
                type=art.type,
                source=art.source,
                source_reference=art.source_reference,
                verification_status=art.verification_status,
                ownership_status=art.ownership_status,
                demonstrated_capabilities=demo_caps,
                inferred_capabilities=inf_caps,
                role_relevance_score=score,
                role_fit_reason=f"Matches {overlap} key capability requirements for {role}." if overlap else "Foundational software artifact.",
                evidence_strength="STRONG" if art.verification_status == "VERIFIED" else "MODERATE",
                version=art.version
            )
            cards.append(card)
            if score >= 60.0:
                role_ranking.append(art.artifact_id)

        verified_count = sum(1 for a in artifacts if a.verification_status == "VERIFIED")
        return PortfolioGraphResponse(
            person_id=person_id,
            total_artifacts=len(artifacts),
            verified_count=verified_count,
            artifacts=cards,
            top_recommended_for_role={role: role_ranking}
        )

    async def revoke_or_delete_artifact(self, person_id: str, artifact_id: str) -> bool:
        art_dict = await self.store.get_canonical_artifact(person_id, artifact_id)
        if not art_dict:
            return False
        art = CanonicalArtifact(**art_dict)
        art.verification_status = "REVOKED"
        art.provenance["revoked_at"] = datetime.now(timezone.utc).isoformat()
        await self.store.save_canonical_artifact(person_id, art.model_dump())
        return True
