import json
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone
import uuid
from backend.core.config import settings
from backend.core.assessment_schemas import AssessmentDefinition, AssessmentItem, AssessmentBlueprint, AssessmentResult
from backend.core.person_schemas import PersonProfile, LearnerBaseline

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
        if not self.model:
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

    def generate_assessment_blueprint(self, profile: PersonProfile) -> AssessmentBlueprint:
        if not self.model:
            raise ValueError("Gemini is required for dynamic blueprint generation.")

        prompt = f"""You are the PATHMIND Assessment Blueprint Architect.
Your task is to determine EXACTLY what must be assessed for this specific learner.
The assessment must be heavily tailored to their CURRENT STAGE and their TARGET ASPIRATION.

Learner Stage: "{profile.learner_stage}"
Target Aspiration: "{profile.aspiration}"
Domain: "{profile.domain}"
Provided Evidence Summary: "{profile.evidence_summary or 'None'}"

CRITICAL RULES:
1. If the learner is a "School Student" aiming for a professional role, test foundational alignment, academic readiness, and extracurricular baseline. Do NOT test professional domain expertise.
2. If the learner is a "Working Professional" or "Career Switcher", test transferable skills, existing career capabilities, and realistic gap analysis.
3. If the learner is a "College Student", test degree-level applied capability, project evidence, and specialization knowledge.
4. The blueprint MUST output a strictly formatted JSON object.

Your JSON output must match exactly:
{{
    "assessment_goal": "String describing the exact purpose of this test for THIS stage.",
    "dimensions": ["dimension_1", "dimension_2", "dimension_3"],
    "evidence_required": ["evidence_1", "evidence_2"],
    "difficulty_level": "String (e.g., Foundation, Intermediate, Advanced Academic, Professional Practical)"
}}
"""
        try:
            response = self.model.generate_content(
                prompt,
                generation_config={"response_mime_type": "application/json", "temperature": 0.3}
            )
            data = json.loads(response.text)
            
            return AssessmentBlueprint(
                id=f"blueprint_{uuid.uuid4().hex[:8]}",
                person_id=profile.person_id,
                learner_stage=profile.learner_stage,
                aspiration=profile.aspiration,
                domain=profile.domain or "General",
                assessment_goal=data.get("assessment_goal", "Determine baseline capability"),
                dimensions=data.get("dimensions", ["General Capability"]),
                evidence_required=data.get("evidence_required", []),
                difficulty_level=data.get("difficulty_level", "Intermediate")
            )
        except Exception as e:
            print(f"GoalAssessmentService error generating blueprint: {e}")
            raise ValueError("Failed to generate assessment blueprint.")

    def generate_goal_assessment(self, blueprint: AssessmentBlueprint) -> AssessmentDefinition:
        """
        Dynamically generates targeted assessment questions using the Blueprint.
        """
        if not self.model:
            raise ValueError("Gemini is required for dynamic goal assessment generation.")

        prompt = f"""You are the PATHMIND Goal Assessment Generator.
Target Goal (Aspiration): "{blueprint.aspiration}"
Domain: "{blueprint.domain}"
Learner Stage: "{blueprint.learner_stage}"
Difficulty Level: "{blueprint.difficulty_level}"
Dimensions to Assess: {json.dumps(blueprint.dimensions)}
Assessment Goal: "{blueprint.assessment_goal}"

Generate 5-10 multiple-choice or likert-scale assessment questions strictly tailored to evaluate a candidate's current capability and situational judgment based on the parameters above.
Crucially, the questions must match the DIFFICULTY LEVEL appropriate for the Learner Stage.
DO NOT invent software, AI, or Python questions unless the goal explicitly demands it. A cricket goal must have cricket questions. A law goal must have law questions.

Your response MUST be valid JSON matching this structure:
{{
    "items": [
        {{
            "id": "item_1",
            "construct": "string matching one of the Dimensions",
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
                generation_config={"response_mime_type": "application/json", "temperature": 0.4}
            )
            data = json.loads(response.text)
            
            raw_items = data.get("items", [])
            valid_items = []
            
            for i, raw_item in enumerate(raw_items):
                if self.validate_question_relevance(raw_item.get("text", ""), blueprint.aspiration, blueprint.domain):
                    raw_item["id"] = f"dyn_{i+1}"
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
                name=f"Dynamic Assessment: {blueprint.aspiration} ({blueprint.learner_stage})",
                version="1.0",
                construct=blueprint.domain,
                source="PATHMIND AI Synthesis",
                license="Internal",
                limitations="AI-generated assessment for preliminary capability probing.",
                items=valid_items,
                scoring_method="Aggregated sum of responses matched against expected domain maturity.",
                interpretation_rules="Higher scores indicate greater familiarity with domain concepts."
            )

        except Exception as e:
            print(f"GoalAssessmentService error generating assessment: {e}")
            raise ValueError(f"Failed to generate assessment for blueprint '{blueprint.id}'. Error: {e}")

    def evaluate_assessment_baseline(self, blueprint: AssessmentBlueprint, result: AssessmentResult) -> LearnerBaseline:
        """
        Synthesizes the raw assessment results into a LearnerBaseline.
        """
        if not self.model:
            raise ValueError("Gemini is required for baseline evaluation.")
            
        prompt = f"""You are the PATHMIND Baseline Evaluator.
Analyze the following assessment results against the original blueprint to determine the learner's baseline.

Learner Stage: "{blueprint.learner_stage}"
Aspiration: "{blueprint.aspiration}"
Blueprint Difficulty: "{blueprint.difficulty_level}"
Dimensions Assessed: {json.dumps(blueprint.dimensions)}
Raw Results JSON: {result.model_dump_json()}

Based on this, output a JSON structure:
{{
    "demonstrated_capabilities": ["list of strings"],
    "weak_areas": ["list of strings"],
    "unknown_areas": ["list of strings"],
    "confidence": "HIGH, MEDIUM, or LOW"
}}
"""
        try:
            response = self.model.generate_content(
                prompt,
                generation_config={"response_mime_type": "application/json", "temperature": 0.2}
            )
            data = json.loads(response.text)
            
            return LearnerBaseline(
                person_id=blueprint.person_id,
                assessment_id=result.assessment_id,
                blueprint_id=blueprint.id,
                demonstrated_capabilities=data.get("demonstrated_capabilities", []),
                weak_areas=data.get("weak_areas", []),
                unknown_areas=data.get("unknown_areas", []),
                confidence=data.get("confidence", "MEDIUM")
            )
        except Exception as e:
            print(f"GoalAssessmentService error evaluating baseline: {e}")
            # Fallback baseline
            return LearnerBaseline(
                person_id=blueprint.person_id,
                assessment_id=result.assessment_id,
                blueprint_id=blueprint.id,
                demonstrated_capabilities=["Preliminary assessment completed"],
                weak_areas=["Requires further manual evaluation"],
                unknown_areas=["Comprehensive gap analysis unavailable due to generation error"],
                confidence="LOW"
            )

