import json
from typing import List, Dict, Any, Optional
from backend.core.memory_schemas import MemoryItem
from backend.core.config import settings

class MemoryReasoningAgent:
    """
    Google ADK & Gemini Reasoning Agent for Personal Second Brain.
    Synthesizes grounded historical recall answers based solely on retrieved personal memories.
    Strictly forbidden from inventing memories, conversations, or dates.
    """
    def __init__(self):
        self.gemini_available = bool(settings.GEMINI_API_KEY)

    async def synthesize_recall_answer(
        self,
        query: str,
        retrieved_memories: List[MemoryItem],
        current_task_context: Optional[str] = None,
        target_role: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Synthesizes a grounded answer from actual retrieved memories.
        If no memories exist, returns an explicit INSUFFICIENT_HISTORY / NO_RELEVANT_MEMORY response.
        """
        if not retrieved_memories:
            return {
                "status": "NO_RELEVANT_MEMORY",
                "answer": "I searched your personal memory vault, but I do not have a recorded memory matching this specific inquiry.",
                "confidence": "LOW"
            }

        # Format retrieved memories for context package
        mem_summaries = []
        for m in retrieved_memories:
            mem_summaries.append(
                f"- [{m.nature}] '{m.title}' (Source: {m.source_reference}, Status: {m.lifecycle_status}): {m.content or m.summary}"
            )

        context_str = "\n".join(mem_summaries)

        # Deterministic default response
        primary = retrieved_memories[0]
        deterministic_answer = (
            f"Based on your recorded memory ({primary.title}): {primary.content or primary.summary} "
            f"[Source: {primary.source_reference}]"
        )
        if len(retrieved_memories) > 1:
            deterministic_answer += f" You also have related history from '{retrieved_memories[1].title}'."

        if self.gemini_available:
            try:
                import google.generativeai as genai
                genai.configure(api_key=settings.GEMINI_API_KEY)
                model = genai.GenerativeModel("gemini-1.5-flash")

                prompt = f"""You are PATHMIND's Personal Second Brain Reasoning Agent.
You answer the user's question about their own learning, project, or career history.
CRITICAL RULE: Rely ONLY on the provided retrieved memories. NEVER invent conversations, projects, dates, or decisions.
If the retrieved memories are insufficient to fully answer, explicitly state what is known and what remains unrecorded.

User Query: "{query}"
Current Task Context: {current_task_context or 'None'}
Current Target Role: {target_role or 'None'}

Retrieved Memories:
{context_str}

Respond ONLY with valid JSON:
{{"status": "RESOLVED", "answer": "...", "confidence": "HIGH"}}
"""
                response = model.generate_content(prompt)
                clean_text = response.text.strip()
                if "```json" in clean_text:
                    clean_text = clean_text.split("```json")[1].split("```")[0].strip()
                elif "```" in clean_text:
                    clean_text = clean_text.split("```")[1].split("```")[0].strip()
                data = json.loads(clean_text)
                return {
                    "status": data.get("status", "RESOLVED"),
                    "answer": data.get("answer", deterministic_answer),
                    "confidence": data.get("confidence", "HIGH")
                }
            except Exception:
                pass

        return {
            "status": "RESOLVED",
            "answer": deterministic_answer,
            "confidence": "HIGH"
        }
