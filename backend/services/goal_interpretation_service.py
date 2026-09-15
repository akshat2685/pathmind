from typing import Dict, Any, Optional
import json
from datetime import datetime, timezone
from backend.core.config import settings
from backend.core.career_schemas import CanonicalGoal
from backend.services.store import FirestoreStore

class GoalInterpretationService:
    """
    Interprets raw user input into a CanonicalGoal.
    Includes deterministic validation to ensure domain neutrality and prevent AI hallucinations.
    """
    def __init__(self, store: Optional[FirestoreStore] = None):
        self.store = store or FirestoreStore()
        self.gemini_available = bool(settings.GEMINI_API_KEY)
        self.model = None

        if self.gemini_available:
            try:
                import google.generativeai as genai
                genai.configure(api_key=settings.GEMINI_API_KEY)
                self.model = genai.GenerativeModel('gemini-2.5-flash')
            except Exception as e:
                print(f"Warning: Failed to initialize Gemini in GoalInterpretationService: {e}")
                self.model = None

    async def interpret_goal(self, person_id: str, raw_statement: str) -> CanonicalGoal:
        """
        Takes a raw user statement, interprets it into a CanonicalGoal, runs deterministic validation,
        and saves it.
        """
        # 1. Base interpretation (Rule-based or LLM)
        interpreted_data = await self._generate_interpretation(raw_statement)

        # 2. Schema instantiation (Validation Layer 1: Schema)
        # If the LLM misses fields, Pydantic will complain or defaults will apply.
        goal = CanonicalGoal(
            person_id=person_id,
            raw_statement=raw_statement,
            normalized_statement=interpreted_data.get("normalized_statement", raw_statement),
            domain=interpreted_data.get("domain", "Unknown"),
            field=interpreted_data.get("field", "Unknown"),
            target_role=interpreted_data.get("target_role", "Unknown"),
            target_outcome=interpreted_data.get("target_outcome", "Unknown"),
            confidence=interpreted_data.get("confidence", "HIGH"),
            target_level=interpreted_data.get("target_level"),
            target_context=interpreted_data.get("target_context"),
            geography="Global",
            provenance="USER_DECLARED"
        )

        # 3. Deterministic Validation Layer (Ambiguity & Bias check)
        self._validate_interpretation(goal)

        # 4. Save (Goal Replacement Invariant is handled at the API layer, but we persist here)
        await self.store.save_career_goal(person_id, goal.model_dump(mode="json"))
        return goal

    async def _generate_interpretation(self, raw_statement: str) -> Dict[str, Any]:
        """
        Calls LLM to extract structured domain information from natural language.
        """
        # Fallback for exploration or missing inputs
        if not raw_statement or "don't know" in raw_statement.lower() or "explore" in raw_statement.lower():
            return {
                "normalized_statement": "Explore potential domains",
                "domain": "Exploration",
                "field": "Exploration",
                "target_role": "Unknown",
                "target_outcome": "Identify a suitable career path",
                "confidence": "LOW"
            }

        if not self.model:
            # Fallback simple heuristic for tests if LLM is unavailable
            return {
                "normalized_statement": raw_statement.title(),
                "domain": "Custom",
                "field": "Custom",
                "target_role": raw_statement.title(),
                "target_outcome": "Achieve professional level in " + raw_statement,
                "confidence": "MEDIUM"
            }

        prompt = f"""
        You are a highly analytical, ZERO-BIAS Goal Interpretation Engine.
        Analyze the following raw user goal statement.
        
        Raw Statement: "{raw_statement}"
        
        Extract the following strictly. DO NOT invent an IT/Software/AI career if the user does not mention one.
        If they say "I want to become a cricketer", the domain is "Sports" and field is "Cricket".
        If they say "I want to be a doctor", the domain is "Healthcare" and field is "Medicine".
        
        Return valid JSON with these exact keys:
        {{
            "normalized_statement": "Clear professional formulation of the goal",
            "domain": "Broad industry category (e.g., Sports, Healthcare, Law, Technology)",
            "field": "Specific sub-field (e.g., Cricket, Medicine, Fashion Design)",
            "target_role": "The specific role they want to become",
            "target_outcome": "What they ultimately want to achieve",
            "target_level": "Inferred level (e.g., Entry, Professional, Expert)",
            "target_context": "Any specific context (e.g., competitive, corporate)",
            "confidence": "HIGH, MEDIUM, or LOW based on specificity"
        }}
        """

        try:
            resp = await self.model.generate_content_async(prompt)
            text = resp.text
            if "```json" in text:
                text = text.split("```json")[1].split("```")[0].strip()
            elif "```" in text:
                text = text.split("```")[1].strip()
            return json.loads(text)
        except Exception as e:
            print(f"GoalInterpretationService LLM parsing failed: {e}")
            return {
                "normalized_statement": raw_statement.title(),
                "domain": "Custom",
                "field": "Custom",
                "target_role": raw_statement.title(),
                "target_outcome": "Achieve professional level in " + raw_statement,
                "confidence": "LOW"
            }

    def _validate_interpretation(self, goal: CanonicalGoal):
        """
        Deterministic Validation Layer.
        Enforces that the interpretation did not secretly hallucinate an AI/Software target 
        when the raw statement has absolutely nothing to do with it.
        """
        raw = goal.raw_statement.lower()
        
        # If the user did not mention tech, software, AI, ML, computer, data, code, robotics
        tech_keywords = ["tech", "software", "ai", "ml", "computer", "data", "code", "robotics", "engineer", "develop", "program"]
        has_tech_intent = any(k in raw for k in tech_keywords)

        if not has_tech_intent:
            # The model better not have generated a tech domain
            inferred = f"{goal.domain} {goal.field} {goal.target_role}".lower()
            if "software" in inferred or "artificial intelligence" in inferred or "machine learning" in inferred or "applied ai" in inferred:
                # OVERRIDE the hallucination
                goal.domain = "Custom"
                goal.field = "Custom"
                goal.target_role = goal.raw_statement.title()
                goal.confidence = "LOW"
                goal.normalized_statement = goal.raw_statement.title()
