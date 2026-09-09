import json
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone

from backend.core.execution_schemas import CanonicalAction, ActionBlocker, AccountabilityIntervention
from backend.core.config import settings

class ExecutionIntelligenceAgent:
    """
    Google ADK & Gemini Reasoning Agent for Action Execution & Accountability.
    Provides non-judgmental blocker resolution, actionable workarounds, and
    outcome-oriented guidance without inventing fake productivity scores.
    """
    def __init__(self):
        self.gemini_available = bool(settings.GEMINI_API_KEY)

    async def diagnose_blocker(
        self,
        action: CanonicalAction,
        blocker_type: str,
        description: str
    ) -> Dict[str, str]:
        """
        Diagnoses a blocker and suggests a realistic workaround and resolution action.
        """
        workaround = "Break the implementation into a 30-minute minimal working prototype."
        resolution_action = "Build minimal reproduction script to isolate the blocking dependency."

        if blocker_type == "FINANCIAL_CONSTRAINT":
            workaround = "Substitute costly paid certification with verified open-source repository evidence + unit test proof."
            resolution_action = "Implement and verify real GitHub repository satisfying the same capability requirements."
        elif blocker_type == "TIME_CONSTRAINT":
            workaround = "Temporarily narrow action scope to core logic; defer ancillary documentation to next iteration."
            resolution_action = "Execute focused 45-minute implementation sprint covering primary happy path."
        elif blocker_type == "KNOWLEDGE_GAP":
            workaround = "Consult official reference documentation and inspect canonical starter repository before coding."
            resolution_action = "Complete Step 1 & 2 conceptual review from the phase learning guide."
        elif blocker_type == "TECHNICAL_BLOCKER":
            workaround = "Isolate failing assertion or dependency with minimal unit test reproduction."
            resolution_action = "Add debugging print statements and inspect stack trace in clean environment."

        if self.gemini_available:
            try:
                import google.generativeai as genai
                genai.configure(api_key=settings.GEMINI_API_KEY)
                model = genai.GenerativeModel("gemini-1.5-flash")
                prompt = f"""You are the PATHMIND Execution Intelligence Agent.
Action: {action.title} ({action.action_type})
Blocker Type: {blocker_type}
Description: {description}

Suggest a realistic, zero-assumption workaround and a small concrete next action.
Respond ONLY with JSON:
{{"workaround": "...", "resolution_action": "..."}}
"""
                response = model.generate_content(prompt)
                clean_text = response.text.strip()
                if "```json" in clean_text:
                    clean_text = clean_text.split("```json")[1].split("```")[0].strip()
                elif "```" in clean_text:
                    clean_text = clean_text.split("```")[1].split("```")[0].strip()
                data = json.loads(clean_text)
                return {
                    "workaround": data.get("workaround", workaround),
                    "resolution_action": data.get("resolution_action", resolution_action)
                }
            except Exception:
                pass

        return {
            "workaround": workaround,
            "resolution_action": resolution_action
        }

    async def generate_accountability_intervention(
        self,
        person_id: str,
        action: CanonicalAction,
        days_overdue: int
    ) -> AccountabilityIntervention:
        """
        Produces supportive, non-judgmental accountability check-ins without shaming.
        """
        msg = (
            f"'{action.title}' was scheduled for completion by {action.due_at or 'earlier this week'}. "
            f"Your active roadmap is currently paused at this step. "
            f"Life constraints happen—choose whether to continue with the current plan, "
            f"reschedule by a few days, or adjust your weekly commitment."
        )

        options = [
            "Continue with active plan (work on it today)",
            "Reschedule deadline by 3 days",
            "Report a blocker and explore a workaround",
            "Adjust weekly study hours"
        ]

        return AccountabilityIntervention(
            person_id=person_id,
            missed_action_id=action.action_id,
            action_title=action.title,
            original_due_at=action.due_at or datetime.now(timezone.utc).isoformat(),
            days_overdue=max(1, days_overdue),
            non_judgmental_message=msg,
            suggested_options=options
        )
