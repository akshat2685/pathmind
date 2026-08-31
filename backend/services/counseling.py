import os
import json
from datetime import datetime
import google.generativeai as genai
from typing import List, Dict, Any
from backend.core.config import settings
from backend.core.assessment_schemas import CounselingProfile, AssessmentResult

class CounselingAgent:
    def __init__(self):
        # Configure Gemini
        genai.configure(api_key=settings.GEMINI_API_KEY)
        self.model = genai.GenerativeModel('gemini-2.5-flash')

    def synthesize_profile(self, person_id: str, assessment_results: List[AssessmentResult], background_context: str = "") -> CounselingProfile:
        """
        Synthesize a strict, unbiased, evidence-grounded career counseling profile.
        Strictly applies Holland RIASEC psychometrics and SCCT (Social Cognitive Career Theory).
        Demands proof/portfolio when critical evidence is missing and refuses to make assumptions.
        """
        
        # Serialize inputs
        results_json = json.dumps([r.model_dump(mode='json') for r in assessment_results], indent=2)
        
        system_prompt = f"""You are the PATHMIND Strict Career Counseling & Psychometric Reasoning Agent.
Your duty is to deliver an UNBIASED, SCIENTIFICALLY GROUNDED, and STRICT assessment synthesis.

CRITICAL INSTRUCTIONS & STRICTNESS RULES:
1. ZERO-ASSUMPTION POLICY (EVIDENCE-GROUNDED):
   - DO NOT assume or fabricate any candidate capability, project history, or technical mastery that has not been explicitly provided in observable evidence.
   - If NO portfolio, transcripts, GitHub/code links, or verifiable artifacts are provided, you MUST:
     a) Explicitly list what is missing in `evidence_gaps` (e.g. "Missing verifiable portfolio / code repositories to evaluate engineering competency").
     b) Set confidence to "INSUFFICIENT_EVIDENCE" or "LOW" on unverified capability claims.
     c) Prompt the candidate directly in `next_questions` for specific portfolio or work sample proof.

2. STRICT PSYCHOMETRIC & PERSONALITY TEST COMPLIANCE (Holland RIASEC & SCCT):
   - You MUST interpret the psychometric test results strictly according to Holland RIASEC dimensions and Social Cognitive Career Theory (Self-Efficacy & Outcome Expectations):
     * Realistic (R): Hands-on, mechanical, physical/systems implementation.
     * Investigative (I): Analytical, abstract problem solving, research, data science.
     * Artistic (A): Expressive, design, UX, creative computation.
     * Social (S): Collaborative, teaching, counseling, people orientation.
     * Enterprising (E): Leadership, persuasion, entrepreneurship, product management.
     * Conventional (C): Structured, detail-oriented, systematic, data governance.
   - Ground `candidate_directions` directly on the assessed RIASEC score profile and Self-Efficacy level.
   - If a candidate's stated aspiration conflicts with their psychometric profile (e.g. wants pure systems engineering but scored 1 on Realistic and Investigative, or low self-efficacy), you MUST:
     a) Flag it under `contradictions` (Reported preference vs psychometric reality).
     b) State the exact gap objectively without sycophantic praise or false flattery.
     c) Recommend prerequisite exploration/bridge paths in `candidate_directions`.

3. TRUE PREDICTIVE FUTURE OUTCOMES:
   - Provide realistic, calibrated predictive trajectories based on empirical psychometric fit + demonstrated evidence.
   - Categorize facts accurately: OBSERVED (direct evidence), ASSESSED (psychometrics), INFERRED (logical deduction), EVIDENCE_GAP (missing proof), UNKNOWN.

Background Context & Provided Evidence:
{background_context}

Psychometric Assessment Results:
{results_json}
"""
        
        try:
            response = self.model.generate_content(
                system_prompt,
                generation_config=genai.GenerationConfig(
                    response_mime_type="application/json",
                    response_schema=CounselingProfile,
                    temperature=0.1 # Low temperature for strict adherence to facts & psychometrics
                )
            )
            
            profile_data = json.loads(response.text)
            profile_data["person_id"] = person_id
            profile_data["timestamp"] = datetime.utcnow().isoformat()
            
            return CounselingProfile(**profile_data)
            
        except Exception as e:
            print(f"Error in strict counseling synthesis: {str(e)}")
            raise ValueError("Failed to synthesize profile: " + str(e))
