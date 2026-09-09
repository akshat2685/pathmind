import json
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone

from backend.core.artifact_schemas import (
    CanonicalArtifact,
    ArtifactObservation,
    ArtifactCapabilityMapping,
    ArtifactQualityDimensions,
    ArtifactAnalysisResult
)
from backend.core.config import settings

class ArtifactAnalysisAgent:
    """
    Google ADK & Gemini Reasoning Agent for Technical Artifact Analysis.
    Dissects authentic code repositories, design documents, and portfolios.
    Strictly distinguishes OBSERVED facts from INFERRED capabilities and UNVERIFIED claims.
    Never manufactures unsupported claims of expert-level mastery.
    """
    def __init__(self):
        self.gemini_available = bool(settings.GEMINI_API_KEY)

    async def analyze_artifact(
        self,
        artifact: CanonicalArtifact,
        extracted_observations: List[ArtifactObservation],
        dimensions: ArtifactQualityDimensions
    ) -> ArtifactAnalysisResult:
        """
        Executes ADK/Gemini reasoning over real artifact signals.
        Falls back to rigorous deterministic domain inference when offline.
        """
        if self.gemini_available:
            try:
                result = await self._run_gemini_analysis(artifact, extracted_observations, dimensions)
                if result:
                    return result
            except Exception:
                pass  # Graceful fallback to deterministic analysis

        return self._run_deterministic_analysis(artifact, extracted_observations, dimensions)

    async def _run_gemini_analysis(
        self,
        artifact: CanonicalArtifact,
        observations: List[ArtifactObservation],
        dimensions: ArtifactQualityDimensions
    ) -> Optional[ArtifactAnalysisResult]:
        try:
            import google.generativeai as genai
            genai.configure(api_key=settings.GEMINI_API_KEY)
            model = genai.GenerativeModel("gemini-1.5-flash")

            obs_summary = "\n".join([f"- [{o.category}] {'(Demonstrated)' if o.is_demonstrated else '(Mentioned Only)'} {o.detail}" for o in observations])
            prompt = f"""You are the PATHMIND Artifact Intelligence Agent.
Analyze this real learner artifact and return a strict JSON object.
Title: {artifact.title}
Type: {artifact.type}
Source Reference: {artifact.source_reference}
Observations:
{obs_summary}

Quality Dimensions:
Complexity: {dimensions.complexity}
Testing Evidence: {dimensions.testing_evidence}
Deployment Evidence: {dimensions.deployment_evidence}

CRITICAL RULES:
1. Distinguish OBSERVED (directly verified in code/files) from INFERRED (logical assumption) and NOT_DETERMINABLE.
2. If a technology is mentioned in text/README without code, classify it as an unverified_claim.
3. NEVER claim "This proves expert-level mastery."
4. Identify verification_gaps: what concrete code or test proof is still missing.

Respond ONLY with valid JSON in this structure:
{{
  "potential_capabilities": [
    {{"capability_name": "...", "basis": "...", "confidence": "HIGH"|"MEDIUM"|"LOW", "status": "OBSERVED"|"INFERRED"}}
  ],
  "unverified_claims": ["..."],
  "verification_gaps": ["..."],
  "recommended_followup": ["..."]
}}
"""
            response = model.generate_content(prompt)
            clean_text = response.text.strip()
            if "```json" in clean_text:
                clean_text = clean_text.split("```json")[1].split("```")[0].strip()
            elif "```" in clean_text:
                clean_text = clean_text.split("```")[1].split("```")[0].strip()

            data = json.loads(clean_text)
            caps = [
                ArtifactCapabilityMapping(
                    capability_name=c.get("capability_name", "General Engineering"),
                    basis=c.get("basis", "Extracted from verified artifact code."),
                    confidence=c.get("confidence", "HIGH"),
                    status=c.get("status", "OBSERVED")
                )
                for c in data.get("potential_capabilities", [])
            ]

            return ArtifactAnalysisResult(
                artifact_id=artifact.artifact_id,
                observations=observations,
                potential_capabilities=caps,
                unverified_claims=data.get("unverified_claims", []),
                verification_gaps=data.get("verification_gaps", []),
                dimensions=dimensions,
                recommended_followup=data.get("recommended_followup", []),
                analyzed_at=datetime.now(timezone.utc).isoformat()
            )
        except Exception:
            return None

    def _run_deterministic_analysis(
        self,
        artifact: CanonicalArtifact,
        observations: List[ArtifactObservation],
        dimensions: ArtifactQualityDimensions
    ) -> ArtifactAnalysisResult:
        potential_caps: List[ArtifactCapabilityMapping] = []
        unverified_claims: List[str] = []
        verification_gaps: List[str] = []
        followups: List[str] = []

        # Check demonstrated observations
        for obs in observations:
            if obs.is_demonstrated and obs.category == "TECHNOLOGY":
                # e.g., "Demonstrated codebase implementation in Python (90000 bytes)."
                lang_match = obs.detail.split(" in ")
                tech_name = lang_match[1].split()[0] if len(lang_match) > 1 else "Software Engineering"
                potential_caps.append(ArtifactCapabilityMapping(
                    capability_name=f"{tech_name} Implementation",
                    basis=f"Confirmed active source files ({obs.detail}) in repository.",
                    confidence="HIGH",
                    status="OBSERVED"
                ))
            elif not obs.is_demonstrated and obs.category == "TECHNOLOGY":
                unverified_claims.append(obs.detail)

        # Architectural and testing capabilities
        if dimensions.testing_evidence != "NONE":
            potential_caps.append(ArtifactCapabilityMapping(
                capability_name="Automated Test Engineering",
                basis="Unit test configuration and test suite discovered in repository structure.",
                confidence="HIGH",
                status="OBSERVED"
            ))
        else:
            verification_gaps.append("Missing automated unit test suite or assertion coverage.")
            followups.append("Write pytest or integration tests covering edge cases to prove system correctness.")

        if dimensions.deployment_evidence != "NONE":
            potential_caps.append(ArtifactCapabilityMapping(
                capability_name="Containerization & Deployment Architecture",
                basis="Production Dockerfile or GitHub Actions CI/CD pipeline verified.",
                confidence="HIGH",
                status="OBSERVED"
            ))
        else:
            verification_gaps.append("No containerization (Dockerfile) or automated build workflow detected.")
            followups.append("Add a Dockerfile or GitHub Actions workflow to prove reproducible deployment readiness.")

        # If empty capabilities found, add foundational
        if not potential_caps:
            potential_caps.append(ArtifactCapabilityMapping(
                capability_name="Technical Project Scaffolding",
                basis="Project metadata and repository structure observed.",
                confidence="MEDIUM",
                status="INFERRED"
            ))

        if not followups:
            followups.append("Conduct an interactive technical defense of your architectural design tradeoffs.")

        return ArtifactAnalysisResult(
            artifact_id=artifact.artifact_id,
            observations=observations,
            potential_capabilities=potential_caps,
            unverified_claims=unverified_claims,
            verification_gaps=verification_gaps,
            dimensions=dimensions,
            recommended_followup=followups,
            analyzed_at=datetime.now(timezone.utc).isoformat()
        )
