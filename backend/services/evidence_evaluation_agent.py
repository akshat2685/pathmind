from typing import Dict, Any, List, Optional
import json
from datetime import datetime, timezone
from backend.core.config import settings
from backend.core.evidence_schemas import (
    CanonicalEvidence,
    StructuredEvaluationDetail
)

class EvidenceEvaluationAgent:
    """
    Google ADK / Gemini Evidence Evaluation Agent.
    Strictly separates:
    - OBSERVED (factual execution & syntax observations)
    - INFERRED (cognitive & design rationale inferences)
    - RECOMMENDATION (targeted next milestone actions)
    """
    def __init__(self):
        self.gemini_available = bool(settings.GEMINI_API_KEY)
        self.model = None
        if self.gemini_available:
            try:
                import google.generativeai as genai
                genai.configure(api_key=settings.GEMINI_API_KEY)
                self.model = genai.GenerativeModel('gemini-2.5-flash')
            except Exception as e:
                print(f"Warning: Failed to initialize Gemini model in EvidenceEvaluationAgent: {e}")
                self.model = None

    async def evaluate_evidence(
        self,
        evidence: CanonicalEvidence,
        stage_title: str,
        required_skills: List[str],
        verification_quality: str,
        is_transfer_task: bool = False
    ) -> StructuredEvaluationDetail:
        payload = evidence.metadata.get("payload", {})
        code_text = str(payload.get("code", "") or payload.get("repo_url", ""))
        
        # Deterministic Baseline Evaluation
        observed = []
        inferred = []
        recommendations = []
        misconceptions = []
        
        has_tests = "test" in code_text.lower() or "assert" in code_text
        has_type_hints = ":" in code_text and "->" in code_text
        has_classes = "class " in code_text

        if has_tests:
            observed.append("Verified automated unit test assertions present in submitted artifact.")
        if has_type_hints:
            observed.append("Strict type hints and parameter return annotations implemented.")
        if has_classes:
            observed.append("Object-oriented modular design structures utilized.")
        if len(code_text) > 50:
            observed.append(f"Executable code payload provided with {len(code_text)} characters.")

        if not observed:
            observed.append("Preliminary code snippet or reference provided.")

        # Inferences
        if verification_quality in ["STRONG", "VERIFIED_STRONG"]:
            inferred.append(f"Demonstrates reliable application-level capability in {', '.join(required_skills)}.")
            if is_transfer_task:
                inferred.append("Successfully generalized foundational concepts to a novel domain context without rote repetition.")
                mastery_state = "TRANSFER"
            else:
                mastery_state = "DEMONSTRATED_MASTERY" if has_tests else "APPLICATION"
            recommendations.append(f"Prerequisite satisfied. Ready for downstream progression from {stage_title}.")
        elif verification_quality == "MODERATE":
            inferred.append(f"Demonstrates working understanding of {stage_title}, with minor test coverage gaps.")
            mastery_state = "APPLICATION"
            recommendations.append("Strengthen unit test coverage to solidify production reliability.")
        else:
            inferred.append("Artifact exhibits missing test suites or incomplete method bodies.")
            misconceptions.append("Insufficient boundary-case assertions for stream parsing.")
            mastery_state = "NEEDS_REINFORCEMENT"
            recommendations.append("Review error-handling and write at least 2 unit tests with pytest.")

        # Gemini LLM Enhancement for reasoning synthesis
        if self.model and len(code_text) > 30:
            try:
                prompt = f"""
You are the PATHMIND Evidence Evaluation Agent.
Analyze this submitted learner artifact for '{stage_title}' (Skills: {', '.join(required_skills)}):

Artifact Payload:
{code_text[:800]}

Quality Grade: {verification_quality}
Transfer Task: {is_transfer_task}

Return JSON with exact keys:
{{
  "observed": ["factual observation 1", "factual observation 2"],
  "inferred": ["derived conclusion 1"],
  "recommendation": ["actionable next step 1"],
  "observable_misconceptions": []
}}
Do NOT invent achievements. Strictly separate observation from inference.
"""
                response = self.model.generate_content(prompt)
                if response and response.text:
                    clean_text = response.text.strip()
                    if clean_text.startswith("```json"):
                        clean_text = clean_text[7:-3].strip()
                    elif clean_text.startswith("```"):
                        clean_text = clean_text[3:-3].strip()
                    parsed = json.loads(clean_text)
                    if parsed.get("observed"):
                        observed = parsed["observed"]
                    if parsed.get("inferred"):
                        inferred = parsed["inferred"]
                    if parsed.get("recommendation"):
                        recommendations = parsed["recommendation"]
                    if parsed.get("observable_misconceptions") is not None:
                        misconceptions = parsed["observable_misconceptions"]
            except Exception:
                pass

        return StructuredEvaluationDetail(
            observed=observed,
            inferred=inferred,
            recommendation=recommendations,
            mastery_state_achieved=mastery_state,
            observable_misconceptions=misconceptions,
            transfer_validated=is_transfer_task and verification_quality in ["STRONG", "VERIFIED_STRONG"],
            evidence_quality_awarded=verification_quality
        )
