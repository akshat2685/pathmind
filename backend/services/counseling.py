import os
import json
import google.generativeai as genai
from typing import List, Dict, Any
from backend.core.config import settings
from backend.core.assessment_schemas import CounselingProfile, AssessmentResult

class CounselingAgent:
    def __init__(self):
        # Configure Gemini
        genai.configure(api_key=settings.GEMINI_API_KEY)
        # Use gemini-2.5-flash as it's the recommended model for general tasks
        self.model = genai.GenerativeModel('gemini-2.5-flash')

    def synthesize_profile(self, person_id: str, assessment_results: List[AssessmentResult], background_context: str = "") -> CounselingProfile:
        """
        Synthesize a structured CounselingProfile from assessment results.
        Enforces schema, contradiction detection, and confidence levels.
        """
        
        # Serialize inputs
        results_json = json.dumps([r.model_dump(mode='json') for r in assessment_results], indent=2)
        
        system_prompt = f"""You are the PATHMIND ADK Counseling Agent. 
Your goal is to synthesize a structured career counseling profile based strictly on the provided evidence.

CRITICAL RULES:
1. DO NOT make clinical psychological diagnoses.
2. DO NOT make deterministic personality labels.
3. You MUST distinguish between OBSERVED (direct evidence), ASSESSED (from standardized assessment tools), INFERRED (reasoned from multiple signals), and UNKNOWN.
4. Detect contradictions (e.g., "I hate coding" vs "Built 4 apps").
5. Confidence levels must be HIGH, MEDIUM, LOW, or INSUFFICIENT_EVIDENCE.
6. Provide candidate_directions informed by the data.

Background Context:
{background_context}

Assessment Results:
{results_json}
"""
        
        try:
            # We use the new structured outputs feature for Gemini
            response = self.model.generate_content(
                system_prompt,
                generation_config=genai.GenerationConfig(
                    response_mime_type="application/json",
                    response_schema=CounselingProfile,
                    temperature=0.2 # keep it grounded
                )
            )
            
            profile_data = json.loads(response.text)
            profile_data["person_id"] = person_id
            profile_data["timestamp"] = "generated" # Ideally datetime.utcnow().isoformat()
            
            return CounselingProfile(**profile_data)
            
        except Exception as e:
            # Fallback or error handling if structured output fails
            print(f"Error in counseling synthesis: {str(e)}")
            raise ValueError("Failed to synthesize profile: " + str(e))
