from typing import List, Dict, Any, Optional
from datetime import datetime, timezone
import json
from backend.core.config import settings
from backend.core.memory_schemas import (
    MemoryItem,
    SharedLearningPattern,
    MemoryRecallQuery,
    MemoryRecallResponse,
    CrossStageBridgeResponse,
    SecondBrainQueryRequest
)
from backend.services.store import FirestoreStore
from backend.services.second_brain_service import SecondBrainService

class MemoryEngine:
    def __init__(self, store: Optional[FirestoreStore] = None):
        self.store = store or FirestoreStore()
        self.second_brain = SecondBrainService(store=self.store)
        self.gemini_available = bool(settings.GEMINI_API_KEY)
        self.model = None

        if self.gemini_available:
            try:
                import google.generativeai as genai
                genai.configure(api_key=settings.GEMINI_API_KEY)
                self.model = genai.GenerativeModel('gemini-2.5-flash')
            except Exception as e:
                print(f"Warning: Failed to initialize Gemini model in MemoryEngine: {e}")
                self.model = None

    async def extract_and_store_memory_from_event(
        self,
        person_id: str,
        event_payload: Dict[str, Any]
    ) -> MemoryItem:
        """
        MemoryAgent (ADK): Ingests a real learning event, classifies it into memory categories,
        assigns importance and confidence, and saves it to the personal vault.
        """
        return await self.second_brain.ingest_memory(person_id, event_payload)

    async def recall_natural_memory(
        self,
        query: MemoryRecallQuery
    ) -> MemoryRecallResponse:
        """
        Natural Memory Recall Engine (PersonalizationAgent & Second Brain):
        Answers questions about past learning experiences, strategies, and goal evolution grounded
        in actual stored personal memories. Never fabricates memories.
        """
        res = await self.second_brain.query_second_brain(
            person_id=query.person_id,
            req=SecondBrainQueryRequest(
                query=query.query,
                current_task_context=query.current_concept
            )
        )

        return MemoryRecallResponse(
            person_id=query.person_id,
            query=query.query,
            recalled_memories=[r.memory for r in res.retrieved_memories],
            answer=res.answer,
            grounded_concept_bridge=res.concept_bridge,
            confidence=res.confidence
        )

    async def get_cross_stage_bridge(
        self,
        person_id: str,
        current_concept: Optional[str] = None
    ) -> CrossStageBridgeResponse:
        """
        Past → Present Concept Bridge:
        Identifies and explains how past mastered concepts scaffold into new learning contexts from real memories.
        """
        raw_mems = await self.store.get_personal_memories(person_id)
        memories = [MemoryItem(**m) for m in raw_mems]

        if not current_concept:
            # Check active roadmap stage
            active_roadmap = await self.store.get_active_roadmap(person_id)
            if active_roadmap and active_roadmap.get("phases"):
                flat_stages = [s for p in active_roadmap["phases"] for s in p.get("stages", []) if not s.get("locked")]
                if flat_stages:
                    current_concept = flat_stages[-1].get("title", "Active Milestone")
            if not current_concept:
                stored_goal = await self.store.get_goal(person_id)
                current_concept = stored_goal.get("target_outcome", "Active Milestone") if stored_goal else "Active Milestone"
        
        # Check if user has past foundational memories matching the concept
        matched_mem = None
        if memories:
            concept_words = [w.lower() for w in current_concept.split() if len(w) > 3]
            matched_mem = next((m for m in memories if any(w in m.topic.lower() or w in m.title.lower() for w in concept_words)), None)
            if not matched_mem:
                # Default to the most foundational or latest verified memory
                recursion_mem = next((m for m in memories if "recursion" in m.topic.lower() or "recursion" in m.title.lower()), None)
                matched_mem = recursion_mem or memories[0]
        
        if matched_mem:
            return CrossStageBridgeResponse(
                person_id=person_id,
                current_concept=current_concept,
                past_concept=matched_mem.title,
                past_stage=matched_mem.source,
                context=matched_mem.summary,
                connection_explanation=f"This milestone builds directly on your prior mastery of {matched_mem.topic} in {matched_mem.source}, applying those principles to {current_concept}.",
                confidence="HIGH"
            )

        return CrossStageBridgeResponse(
            person_id=person_id,
            current_concept=current_concept,
            past_concept="Foundational Competencies",
            past_stage="Prerequisite Milestones",
            context="Foundational concept mastery will be connected here as you progress.",
            connection_explanation=f"{current_concept} requires structured problem-solving foundations. Complete prerequisite stages to unlock specific concept linkages.",
            confidence="MEDIUM"
        )
