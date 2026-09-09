from typing import Dict, Any, List, Optional
import json
from datetime import datetime, timezone
from backend.core.config import settings
from backend.core.adaptation_schemas import (
    StateChangeEvent,
    ImpactAnalysis,
    ProposedAdaptation
)

class AdaptivePlanningAgent:
    """
    Google ADK / Gemini-powered Adaptive Planning Agent.
    Reasons over structured state (person profile, goals, evidence, memory, constraints)
    to formulate causal, explainable adaptation proposals while preserving the Plan Stability Principle.
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
                print(f"Warning: Failed to initialize Gemini model in AdaptivePlanningAgent: {e}")
                self.model = None

    async def formulate_adaptation(
        self,
        person_id: str,
        current_roadmap: Dict[str, Any],
        event: StateChangeEvent,
        impact: ImpactAnalysis,
        personal_context: Optional[Dict[str, Any]] = None
    ) -> ProposedAdaptation:
        current_version = current_roadmap.get("version", 1)
        next_version = current_version + 1 if impact.impact_level in ["HIGH_IMPACT", "CRITICAL_CHANGE"] else current_version
        
        # Build deterministic baseline proposal
        change_summary = (
            f"Transitioning active trajectory to support {event.trigger_data.get('new_target_role', event.title)}. "
            f"Preserved {len(impact.preserved_assets)} core foundational assets while updating downstream specialized milestones."
        )

        rationale = (
            f"PATHMIND detected a {event.change_type.lower().replace('_', ' ')} event. {impact.why} "
            f"Under the Plan Stability Principle, existing completed milestones remain locked-in and reusable. "
            f"{impact.next_action_recommendation}"
        )

        changed_stages = []
        unchanged_stages = ["stage_01_python_foundations", "stage_02_math_and_linear_algebra"]

        if event.change_type == "GOAL_CHANGE":
            new_role = event.trigger_data.get("new_target_role", "Target Role")
            changed_stages = [
                {
                    "stage_id": "stage_03_specialized_domain",
                    "title": f"Domain Specialization: {new_role} Foundations",
                    "action": "REPLACED_TRACK",
                    "rationale": f"Aligned with official ESCO/NCO occupational requirements for {new_role}."
                },
                {
                    "stage_id": "stage_04_target_capstone",
                    "title": f"Production Portfolio: {new_role} Capstone System",
                    "action": "ADDED_MILESTONE",
                    "rationale": f"High-signal verified project evidence demonstrating {new_role} capabilities."
                }
            ]
        elif event.change_type == "MASTERY_RISK":
            stage_id = event.trigger_data.get("stage_id", "current_stage")
            changed_stages = [
                {
                    "stage_id": f"{stage_id}_reinforcement",
                    "title": "Targeted Concept Reinforcement & Guided Code Review",
                    "action": "INJECTED_REINFORCEMENT",
                    "rationale": "Resolves observed misconception patterns with practical, step-by-step guidance."
                }
            ]
        elif event.change_type == "OPPORTUNITY_CHANGE":
            opp_title = event.trigger_data.get("opportunity_title", "Verified Program")
            changed_stages = [
                {
                    "stage_id": "stage_04_capstone_prioritized",
                    "title": f"Fast-Track Project Evidence: {opp_title} Focus",
                    "action": "PRIORITIZED_SEQUENCE",
                    "rationale": f"Positions portfolio for verified application deadline at {event.trigger_data.get('organization', 'Host Organization')}."
                }
            ]

        # Use Gemini for enhanced causal explanation if available
        if self.model and event.change_type in ["GOAL_CHANGE", "CRITICAL_CHANGE"]:
            try:
                prompt = f"""
You are the PATHMIND Adaptive Planning Agent.
Reason about this user adaptation event:
Person ID: {person_id}
Current Target: {event.trigger_data.get('previous_role', 'Previous Goal')}
New Target: {event.trigger_data.get('new_target_role', 'New Goal')}
Impact Level: {impact.impact_level}
Preserved Assets: {', '.join(impact.preserved_assets)}

Provide a concise 2-sentence causal explanation of:
1. Exactly what changed and why existing foundations are preserved.
2. What happens next.
Avoid buzzwords. Be direct, respectful, and grounded.
"""
                response = self.model.generate_content(prompt)
                if response and response.text:
                    rationale = response.text.strip()
            except Exception:
                pass

        return ProposedAdaptation(
            person_id=person_id,
            change_event=event,
            impact_analysis=impact,
            previous_roadmap_version=current_version,
            proposed_roadmap_version=next_version,
            change_summary=change_summary,
            changed_stages=changed_stages,
            unchanged_stages=unchanged_stages,
            rationale=rationale,
            status="PENDING_APPROVAL" if impact.requires_user_approval else "AUTO_APPLIED"
        )
