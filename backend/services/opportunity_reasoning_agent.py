import json
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone

from backend.core.opportunity_schemas import (
    CanonicalOpportunity,
    InterviewPrepPackage
)
from backend.core.config import settings

# In a real environment, adk tools are passed to Gemini
try:
    from backend.tools.opportunity_tools import search_opportunities_tool
    HAS_OPP_TOOLS = True
except ImportError:
    HAS_OPP_TOOLS = False

class OpportunityReasoningAgent:
    """
    Google ADK & Gemini Reasoning Agent for Opportunity Preparation.
    Synthesizes interview questions and action plans grounded in the student's canonical domain.
    """
    def __init__(self):
        self.gemini_available = bool(settings.GEMINI_API_KEY)

    async def generate_opportunity_preparation_plan(
        self,
        person_id: str,
        target_role: str,
        opportunity_title: str,
        organization: str,
        requirements: List[str]
    ) -> Dict[str, Any]:
        
        required_actions = [
            {
                "title": f"Review {organization} specific materials",
                "description": f"Understand the core values and recent initiatives for {opportunity_title}.",
                "action_type": "RESEARCH",
                "priority": "HIGH"
            }
        ]

        if requirements:
            required_actions.append({
                "title": f"Demonstrate competency in {requirements[0]}",
                "description": f"Prepare evidence or talking points validating your experience with {requirements[0]}.",
                "action_type": "PREPARATION",
                "priority": "HIGH"
            })

        if self.gemini_available:
            try:
                from backend.core.gemini import get_gemini_model, GeminiUnavailable
                model = get_gemini_model()
                if model is None:
                    raise GeminiUnavailable("Gemini API key not configured")
                prompt = f"""You are the PATHMIND Opportunity Preparation Agent.
Target Role: {target_role}
Opportunity: {opportunity_title} at {organization}
Requirements: {requirements}

Generate an actionable preparation plan with specific required actions tailored to this domain.
Keep it strictly domain-agnostic (don't assume software engineering unless the target_role specifies it).
Respond ONLY with JSON:
{{"required_actions": [{{"title": "...", "description": "...", "action_type": "...", "priority": "..."}}]}}
"""
                tools = [search_opportunities_tool] if HAS_OPP_TOOLS else None
                response = model.generate_content(prompt, tools=tools)
                clean_text = response.text.strip()
                if "```json" in clean_text:
                    clean_text = clean_text.split("```json")[1].split("```")[0].strip()
                elif "```" in clean_text:
                    clean_text = clean_text.split("```")[1].split("```")[0].strip()
                data = json.loads(clean_text)
                required_actions = data.get("required_actions", required_actions)
            except Exception:
                pass

        return {
            "opportunity_id": "UNKNOWN",
            "person_id": person_id,
            "target_role": target_role,
            "required_actions": required_actions,
            "estimated_effort_days": len(required_actions) * 2,
            "deadline_feasibility": "FEASIBLE"
        }

    async def generate_interview_prep_package(
        self,
        person_id: str,
        target_role: str,
        opportunity_title: str,
        organization: str,
        requirements: List[str]
    ) -> Dict[str, Any]:
        """
        Generates interview questions grounded in actual opportunity requirements
        without domain bias.
        """
        tech_questions = [
            f"Explain a complex problem you solved related to {requirements[0] if requirements else target_role} and your methodology.",
            "Walk me through how you evaluate success in your work.",
            "Describe how you handle conflicting priorities or changing requirements in a project."
        ]
        
        project_defense = [
            "What is the most significant project you've completed in this field, and what was your specific contribution?",
            "If you could redo your most challenging project, what fundamental approach would you change and why?"
        ]

        gap_focus = [
            f"Deep-dive into best practices and foundational principles of {req}."
            for req in requirements[:2]
        ]

        if self.gemini_available:
            try:
                from backend.core.gemini import get_gemini_model, GeminiUnavailable
                model = get_gemini_model()
                if model is None:
                    raise GeminiUnavailable("Gemini API key not configured")
                prompt = f"""You are the PATHMIND Interview Prep Agent.
Opportunity: {opportunity_title} at {organization}
Target Role: {target_role}
Requirements: {requirements}

Generate 3 competency questions, 2 project defense questions, and 2 gap reinforcement focus areas tailored to this SPECIFIC domain (e.g., medicine, law, music, software, design).
Respond ONLY with JSON:
{{"technical_competency_questions": ["..."], "project_defense_questions": ["..."], "gap_reinforcement_focus": ["..."]}}
"""
                tools = [search_opportunities_tool] if HAS_OPP_TOOLS else None
                response = model.generate_content(prompt, tools=tools)
                clean_text = response.text.strip()
                if "```json" in clean_text:
                    clean_text = clean_text.split("```json")[1].split("```")[0].strip()
                elif "```" in clean_text:
                    clean_text = clean_text.split("```")[1].split("```")[0].strip()
                data = json.loads(clean_text)
                tech_questions = data.get("technical_competency_questions", tech_questions)
                project_defense = data.get("project_defense_questions", project_defense)
                gap_focus = data.get("gap_reinforcement_focus", gap_focus)
            except Exception:
                pass

        return {
            "opportunity_id": "UNKNOWN",
            "opportunity_title": opportunity_title,
            "organization": organization,
            "technical_competency_questions": tech_questions,
            "project_defense_questions": project_defense,
            "gap_reinforcement_focus": gap_focus
        }
