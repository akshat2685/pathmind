import json
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone
from backend.core.config import settings
from backend.core.assessment_schemas import AssessmentDefinition, AssessmentItem

class GoalAssessmentService:
    def __init__(self):
        self.gemini_available = bool(settings.GEMINI_API_KEY)
        self.model = None

        if self.gemini_available:
            try:
                import google.generativeai as genai
                genai.configure(api_key=settings.GEMINI_API_KEY)
                self.model = genai.GenerativeModel('gemini-2.5-flash')
            except Exception as e:
                print(f"Warning: Failed to initialize Gemini model in GoalAssessmentService: {e}")
                self.model = None

    def validate_question_relevance(self, question_text: str, goal: str, domain: str) -> bool:
        """
        Aggressively filters out questions unrelated to the goal domain.
        Uses a prompt to ask Gemini if the question is strictly relevant,
        returning True or False. If Gemini is unavailable, falls back to keyword matching.
        """
        if not self.model:
            # Fallback primitive check: block obvious programming bias unless goal explicitly involves it
            if "python" in question_text.lower() or "software" in question_text.lower() or "coding" in question_text.lower():
                if "python" not in goal.lower() and "software" not in goal.lower() and "coding" not in goal.lower():
                    return False
            return True

        prompt = f"""You are a Relevance Gatekeeper for PATHMIND.
Goal: "{goal}"
Domain: "{domain}"
Question: "{question_text}"

Does this question STRICTLY belong to the goal's domain? 
It MUST NOT contain any technical, software, or AI/ML bias unless the goal is specifically about those fields.
Answer with exactly "YES" or "NO".
"""
        try:
            resp = self.model.generate_content(prompt)
            return "YES" in resp.text.strip().upper()
        except Exception:
            return True

    def generate_goal_assessment(
        self,
        goal: str,
        domain: str = "General",
        core_skills: List[str] = None
    ) -> AssessmentDefinition:
        """
        Dynamically generates 5-10 targeted assessment questions using Gemini.
        Returns an AssessmentDefinition object.
        """
        core_skills = core_skills or []
        
        if not self.model:
            raise ValueError("Gemini is required for dynamic goal assessment generation.")

        prompt = f"""You are the PATHMIND Goal Assessment Generator.
Target Goal: "{goal}"
Domain: "{domain}"
Core Skills/Requirements: {json.dumps(core_skills)}

Generate 5-10 multiple-choice or likert-scale assessment questions strictly tailored to evaluate a candidate's current capability and situational judgment in this specific goal and domain.
DO NOT invent software, AI, or Python questions unless the goal explicitly demands it. A cricket goal must have cricket questions. A law goal must have law questions.

Your response MUST be valid JSON matching this structure:
{{
    "items": [
        {{
            "id": "item_1",
            "construct": "string (e.g., Tactical Judgment, Domain Knowledge)",
            "text": "The question text",
            "response_type": "likert",
            "scale": [
                {{"value": 1, "label": "Beginner / Strongly Disagree"}},
                {{"value": 5, "label": "Expert / Strongly Agree"}}
            ],
            "expected_capability": "string"
        }}
    ]
}}
"""
        try:
            response = self.model.generate_content(
                prompt,
                generation_config={
                    "response_mime_type": "application/json",
                    "temperature": 0.4
                }
            )
            data = json.loads(response.text)
            
            raw_items = data.get("items", [])
            valid_items = []
            
            for i, raw_item in enumerate(raw_items):
                if self.validate_question_relevance(raw_item.get("text", ""), goal, domain):
                    # Ensure ID is unique and construct is mapped to construct_name by pydantic alias
                    raw_item["id"] = f"dyn_{i+1}"
                    # Ensure scale is well-formed
                    if not raw_item.get("scale"):
                        raw_item["scale"] = [
                            {"value": 1, "label": "1 - Novice"},
                            {"value": 2, "label": "2 - Beginner"},
                            {"value": 3, "label": "3 - Competent"},
                            {"value": 4, "label": "4 - Proficient"},
                            {"value": 5, "label": "5 - Expert"}
                        ]
                    valid_items.append(AssessmentItem(**raw_item))

            if not valid_items:
                raise ValueError("All generated items were rejected by the relevance gate.")

            now_ts = int(datetime.now(timezone.utc).timestamp())
            return AssessmentDefinition(
                id=f"assess_dyn_{now_ts}",
                name=f"Dynamic Assessment for {goal}",
                version="1.0",
                construct=domain,
                source="PATHMIND AI Synthesis",
                license="Internal",
                limitations="AI-generated assessment for preliminary capability probing.",
                items=valid_items,
                scoring_method="Aggregated sum of responses matched against expected domain maturity.",
                interpretation_rules="Higher scores indicate greater familiarity with domain concepts."
            )

        except Exception as e:
            print(f"GoalAssessmentService error: {e}")
            raise ValueError(f"Failed to generate assessment for goal '{goal}'. Error: {e}")
