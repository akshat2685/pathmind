from typing import Dict, Any, List, Optional
import json
from google import genai
from google.genai import types

from backend.services.adk_tools import (
    get_learner_profile_tool,
    update_learner_profile_tool,
    get_evidence_requirements_tool,
    submit_evidence_tool,
    generate_stage_aware_assessment_tool,
    save_assessment_result_tool,
    generate_candidate_paths_tool,
    save_selected_path_tool,
    get_current_roadmap_tool,
    unlock_next_phase_tool
)
from backend.services.store import FirestoreStore
from backend.core.config import settings

class RootAgentRunner:
    def __init__(self, store: FirestoreStore):
        self.store = store
        
        self.client = genai.Client(api_key=settings.GEMINI_API_KEY)
        self.model_name = "gemini-2.5-flash"
        
        self.tools = [
            get_learner_profile_tool,
            update_learner_profile_tool,
            get_evidence_requirements_tool,
            submit_evidence_tool,
            generate_stage_aware_assessment_tool,
            save_assessment_result_tool,
            generate_candidate_paths_tool,
            save_selected_path_tool,
            get_current_roadmap_tool,
            unlock_next_phase_tool
        ]
        
        self.instruction = """
You are the PATHMIND Root Agent. You guide the learner through a single guided journey.
You MUST output your final response strictly as a JSON object matching this contract:
{
  "message": "A conversational response to the user.",
  "state": "A short summary of current state (e.g., 'Awaiting evidence').",
  "ui_blocks": ["LIST", "OF", "UI", "BLOCKS"]
}

The ui_blocks list can contain one or more of the following:
- STAGE_SELECTION
- EVIDENCE_REQUEST
- EVIDENCE_STATUS
- ASSESSMENT
- ASSESSMENT_RESULT
- PATHWAYS
- ROADMAP
- LEARNING_PLAN
- MASTERY
- ERROR
- NEXT_ACTION

Your workflow MUST be:
1. If identity (name) or aspiration or stage is missing -> ask for them and emit STAGE_SELECTION block.
2. If profile is complete but evidence requirements are not known -> use get_evidence_requirements_tool, emit EVIDENCE_REQUEST.
3. If evidence is submitted but no assessment exists -> use generate_stage_aware_assessment_tool, emit ASSESSMENT.
4. If assessment is completed but no path selected -> use generate_candidate_paths_tool, emit PATHWAYS.
5. If path is selected -> use get_current_roadmap_tool, emit ROADMAP and LEARNING_PLAN.

You must rely on tools to fetch and mutate state.
DO NOT fabricate evidence or paths.
"""

    async def run(self, person_id: str, message: str, client_state: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        prompt = f"Person ID: {person_id}\nUser Message: {message}\n"
        if client_state:
            prompt += f"Client State: {json.dumps(client_state)}\n"
        
        prompt += "\nRemember to return ONLY a JSON object matching the contract."
        
        try:
            chat = self.client.aio.chats.create(
                model=self.model_name,
                config=types.GenerateContentConfig(
                    system_instruction=self.instruction,
                    tools=self.tools,
                    temperature=0.2
                )
            )
            
            response = await chat.send_message(prompt)
            
            response_text = response.text
            
            # Extract JSON block in case it comes wrapped in markdown
            if "```json" in response_text:
                json_str = response_text.split("```json")[1].split("```")[0].strip()
            elif "```" in response_text:
                json_str = response_text.split("```")[1].split("```")[0].strip()
            else:
                json_str = response_text.strip()
                
            return json.loads(json_str)
        except json.JSONDecodeError:
            return {
                "message": "I encountered an error understanding the state. Let's try again.",
                "state": "Parse Error",
                "ui_blocks": ["ERROR"]
            }
        except Exception as e:
            import traceback
            traceback.print_exc()
            return {
                "message": f"Backend Error: {str(e)}",
                "state": "System Error",
                "ui_blocks": ["ERROR"]
            }
