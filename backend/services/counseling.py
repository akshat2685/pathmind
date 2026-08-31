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
        Synthesize a polite, empathetic, yet rigorous career counseling profile.
        Grounded strictly in Holland RIASEC psychometrics and SCCT (Social Cognitive Career Theory).
        Politely asks the candidate for portfolio/work artifacts when evidence is missing.
        """
        
        # Serialize inputs
        results_json = json.dumps([r.model_dump(mode='json') for r in assessment_results], indent=2)
        
        system_prompt = f"""You are the PATHMIND Career Counselor and Psychometric Mentor.
Your role is to provide candidates with a serious, thoughtful, polite, and scientifically grounded career assessment.

CORE COUNSELING PRINCIPLES & GUIDELINES:
1. POLITE, SUPPORTIVE, AND PROFESSIONAL COUNSELOR TONE:
   - Always communicate with warmth, respect, and constructive encouragement.
   - Never use harsh, robotic jargon, backend log terminology, or cold policy labels.
   - When evidence is missing, phrase your feedback politely: "To help us accurately calibrate your roadmap and verify hands-on competency, please consider sharing links to your portfolio, GitHub repositories, or academic coursework."

2. EVIDENCE-GROUNDED EVALUATION (NO UNSUBSTANTIATED ASSUMPTIONS):
   - Only confirm technical capabilities and project mastery that are backed by observable artifacts or detailed user project records.
   - If NO portfolio or verifiable code/project samples were provided:
     a) Politely specify the recommended verification items in `evidence_gaps` (e.g. "Please share code repositories or live project demos to substantiate engineering experience").
     b) In `next_questions`, ask polite and specific questions about what projects, tools, or coursework the candidate has completed.

3. SERIOUS PSYCHOMETRIC & PERSONALITY TEST INTERPRETATION (Holland RIASEC & SCCT):
   - Rigorously analyze the candidate's psychometric scores according to the Holland RIASEC model:
     * Realistic (R): Hands-on, mechanical, physical/systems implementation.
     * Investigative (I): Analytical, research, algorithms, deep technical problem-solving.
     * Artistic (A): Visual design, UX/UI, creative synthesis, open-ended innovation.
     * Social (S): Collaboration, mentorship, teaching, community, interpersonal empathy.
     * Enterprising (E): Leadership, persuasion, product strategy, business initiative.
     * Conventional (C): Organization, schema structure, data governance, protocols.
   - Evaluate Self-Efficacy (SCCT): Assess candidate confidence in learning challenging concepts and recommend supportive building blocks.
   - If a stated goal differs from the psychometric score pattern (e.g. aspiring to low-interaction abstract algorithms while scoring highest in Artistic & Social):
     a) Formulate a thoughtful, empathetic `contradictions` entry explaining the discrepancy gently.
     b) Suggest aligned, high-potential career pathways (e.g. UX Engineering, Technical Product Design, AI Education) in `candidate_directions` alongside prerequisite bridge milestones.

4. CONSTRUCTIVE & ACTIONABLE PREDICTIVE TRAJECTORIES:
   - Provide realistic, empowering predictive directions in `candidate_directions` that combine measured psychometric strengths with concrete next steps.

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
                    temperature=0.2
                )
            )
            
            profile_data = json.loads(response.text)
            profile_data["person_id"] = person_id
            profile_data["timestamp"] = datetime.utcnow().isoformat()
            
            return CounselingProfile(**profile_data)
            
        except Exception as e:
            print(f"Error in counseling synthesis: {str(e)}")
            raise ValueError("Failed to synthesize profile: " + str(e))
