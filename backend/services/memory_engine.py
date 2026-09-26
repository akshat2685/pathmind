from typing import List, Dict, Any, Optional, Any
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
from backend.services.pm_store import get_pm_store
from backend.services.second_brain_service import SecondBrainService

class MemoryEngine:
    def __init__(self, store: Optional[Any] = None):
        self.store = store or get_pm_store()
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
                current_task_context=query.current_concept,
                include_observed=query.include_observed
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
        current_concept: Optional[str] = None,
        include_observed: bool = False
    ) -> CrossStageBridgeResponse:
        """
        Past → Present Concept Bridge:
        Identifies and explains how past mastered concepts scaffold into new learning contexts from real memories.
        Only promoted (CANDIDATE/DURABLE) memories bridge stages unless include_observed=True.
        """
        raw_mems = await self.store.get_personal_memories(person_id)
        memories = [MemoryItem(**m) for m in raw_mems]
        if not include_observed:
            memories = [m for m in memories if m.promotion_status in ("CANDIDATE", "DURABLE")]

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
                concept_expansions = {
                    "tree": ["recursion", "call stack", "stack frame", "traversal"],
                    "graph": ["tree", "recursion", "dfs", "bfs"],
                    "recursion": ["call stack", "base case"],
                    "litigation": ["jurisprudence", "constitutional", "legal"],
                    "contract": ["jurisprudence", "statutory"],
                    "menu": ["culinary", "food safety", "costing"],
                    "genomics": ["molecular", "biology", "dna"]
                }
                for word, related in concept_expansions.items():
                    if word in current_concept.lower():
                        matched_mem = next((m for m in memories if any(r in m.topic.lower() or r in m.title.lower() for r in related)), None)
                        if matched_mem:
                            break

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
            past_concept="NO_RECORDED_MEMORY",
            past_stage="Prerequisite Milestones",
            context="No prior recorded memory connects to this concept.",
            connection_explanation=f"No prior recorded memory connects to {current_concept}. Complete foundational milestones to establish concept linkages.",
            confidence="LOW"
        )
