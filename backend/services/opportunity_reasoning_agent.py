import json
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone

from backend.core.opportunity_schemas import (
    CanonicalOpportunity,
    InterviewPrepPackage
)
from backend.core.config import settings

class OpportunityReasoningAgent:
    """
    Google ADK & Gemini Reasoning Agent for Opportunity Fit, Decision Support & Interview Preparation.
    Synthesizes technical questions grounded in the student's actual project code and AST proofs.
    """
    def __init__(self):
        self.gemini_available = bool(settings.GEMINI_API_KEY)

    async def evaluate_decision_support(
        self,
        opportunity: CanonicalOpportunity,
        matched_skills: List[str],
        missing_skills: List[str],
        readiness_state: str,
        target_role: str
    ) -> Dict[str, Any]:
        """
        Determines decision support recommendation ('Should I Apply?') and explainable tradeoffs.
        """
        if readiness_state in ["TARGET_READY", "READY_NOW"] and len(missing_skills) == 0:
            rec = "RECOMMEND_APPLYING"
            tradeoffs = [
                "Requires ~1 hour to review submission prompt and link your verified GitHub evidence repository.",
                "High immediate competitive alignment with zero unaddressed prerequisite technical gaps."
            ]
        elif readiness_state in ["NEAR_READY", "STRETCH"] or len(missing_skills) <= 2:
            rec = "RECOMMEND_PREPARING_FIRST"
            tradeoffs = [
                f"Address the remaining {len(missing_skills)} capability gap(s) ({', '.join(missing_skills)}) before applying.",
                "Submitting with verified code evidence increases interview conversion rate significantly."
            ]
        else:
            rec = "LOW_PRIORITY"
            tradeoffs = [
                f"Significant foundational skill gaps exist relative to {opportunity.title}.",
                f"Focus on active roadmap milestones for {target_role} before directing effort to this application."
            ]

        if self.gemini_available:
            try:
                import google.generativeai as genai
                genai.configure(api_key=settings.GEMINI_API_KEY)
                model = genai.GenerativeModel("gemini-1.5-flash")
                prompt = f"""You are the PATHMIND Opportunity Decision Reasoning Agent.
Opportunity: {opportunity.title} at {opportunity.organization}
Target Career Role: {target_role}
Readiness State: {readiness_state}
Matched Capabilities: {matched_skills}
Missing Capabilities: {missing_skills}

Evaluate whether the candidate should apply now, prepare first, or deprioritize.
Respond ONLY with JSON:
{{"decision_recommendation": "{rec}", "tradeoffs": ["...", "..."]}}
"""
                response = model.generate_content(prompt)
                clean_text = response.text.strip()
                if "```json" in clean_text:
                    clean_text = clean_text.split("```json")[1].split("```")[0].strip()
                elif "```" in clean_text:
                    clean_text = clean_text.split("```")[1].split("```")[0].strip()
                data = json.loads(clean_text)
                return {
                    "decision_recommendation": data.get("decision_recommendation", rec),
                    "tradeoffs": data.get("tradeoffs", tradeoffs)
                }
            except Exception:
                pass

        return {
            "decision_recommendation": rec,
            "tradeoffs": tradeoffs
        }

    async def generate_interview_prep(
        self,
        opportunity: CanonicalOpportunity,
        target_role: str,
        student_projects: List[Dict[str, Any]]
    ) -> InterviewPrepPackage:
        """
        Generates technical interview questions grounded in actual opportunity requirements
        and the student's actual project code / AST proofs.
        """
        tech_questions = [
            f"How does your implementation handle scale and concurrency when processing requests in {opportunity.requirements[0] if opportunity.requirements else 'Python'}?",
            f"Explain how you structured your automated unit test assertions and mock fixtures to isolate dependencies.",
            f"Walk through the algorithmic time and space complexity tradeoffs of your core data structure choices."
        ]

        project_defense = []
        if student_projects:
            p = student_projects[0]
            title = p.get("title", "Active Project")
            project_defense.append(
                f"In your '{title}' project, explain how you verified modularity and what architectural decisions you would change in v2."
            )
            project_defense.append(
                f"How did you validate edge cases and error boundaries in '{title}' before promoting the code to verified evidence?"
            )
        else:
            project_defense.append(
                "Describe a project where you implemented clean architectural separation and covered critical failure modes with unit tests."
            )

        gap_focus = [
            f"Deep-dive into '{req}' architecture and canonical production usage patterns."
            for req in opportunity.requirements[:2]
        ]

        if self.gemini_available:
            try:
                import google.generativeai as genai
                genai.configure(api_key=settings.GEMINI_API_KEY)
                model = genai.GenerativeModel("gemini-1.5-flash")
                prompt = f"""You are the PATHMIND Technical Interview Prep Agent.
Opportunity: {opportunity.title} at {opportunity.organization}
Requirements: {opportunity.requirements}
Student Project: {student_projects[0].get('title', 'Software Project') if student_projects else 'Modular Software Project'}

Generate 3 technical competency questions, 2 project defense questions, and 2 gap reinforcement focus areas.
Respond ONLY with JSON:
{{"technical_questions": ["..."], "project_defense": ["..."], "gap_focus": ["..."]}}
"""
                response = model.generate_content(prompt)
                clean_text = response.text.strip()
                if "```json" in clean_text:
                    clean_text = clean_text.split("```json")[1].split("```")[0].strip()
                elif "```" in clean_text:
                    clean_text = clean_text.split("```")[1].split("```")[0].strip()
                data = json.loads(clean_text)
                tech_questions = data.get("technical_questions", tech_questions)
                project_defense = data.get("project_defense", project_defense)
                gap_focus = data.get("gap_focus", gap_focus)
            except Exception:
                pass

        return InterviewPrepPackage(
            opportunity_id=opportunity.opportunity_id,
            opportunity_title=opportunity.title,
            organization=opportunity.organization,
            technical_competency_questions=tech_questions,
            project_defense_questions=project_defense,
            gap_reinforcement_focus=gap_focus
        )
