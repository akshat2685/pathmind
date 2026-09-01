from typing import List, Dict, Any, Optional
from datetime import datetime, timezone
import json
from backend.core.config import settings
from backend.core.memory_schemas import (
    MemoryItem,
    SharedLearningPattern,
    MemoryRecallQuery,
    MemoryRecallResponse,
    CrossStageBridgeResponse
)
from backend.services.store import FirestoreStore

class MemoryEngine:
    def __init__(self):
        self.store = FirestoreStore()
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
        topic = event_payload.get("topic", "Learning Milestone")
        observation = event_payload.get("observation", "")
        intervention = event_payload.get("intervention", "")
        event_type = event_payload.get("event_type", "MASTERY_DEMONSTRATED")

        mem_type = "EPISODIC"
        importance = "HIGH"
        if "preference" in event_type.lower():
            mem_type = "PREFERENCE"
            importance = "MEDIUM"
        elif "goal" in event_type.lower():
            mem_type = "GOAL"
            importance = "CRITICAL"
        elif "strategy" in event_type.lower():
            mem_type = "STRATEGY"
            importance = "CRITICAL"

        mem_item = MemoryItem(
            memory_id=f"mem_{int(datetime.now(timezone.utc).timestamp()*1000)}",
            person_id=person_id,
            memory_type=mem_type,
            title=f"{topic} — {event_type.replace('_', ' ').title()}",
            summary=f"{observation}. Recommended approach: {intervention}" if intervention else observation,
            topic=topic,
            related_concepts=[topic],
            confidence="HIGH",
            importance=importance,
            lifecycle_status="ACTIVE",
            source=event_payload.get("stage_id", "Learning Journey"),
            details=event_payload
        )

        await self.store.save_personal_memory(person_id, mem_item.model_dump(mode="json"))
        return mem_item

    async def recall_natural_memory(
        self,
        query: MemoryRecallQuery
    ) -> MemoryRecallResponse:
        """
        Natural Memory Recall Engine (PersonalizationAgent):
        Answers questions about past learning experiences, strategies, and goal evolution grounded
        in actual stored personal memories. Never fabricates memories.
        """
        person_id = query.person_id
        q_text = query.query.lower().strip()
        raw_mems = await self.store.get_personal_memories(person_id)
        memories = [MemoryItem(**m) for m in raw_mems]

        if not memories:
            return MemoryRecallResponse(
                person_id=person_id,
                query=query.query,
                recalled_memories=[],
                answer="No personal memories recorded in your vault yet. Complete learning milestones or submit evidence along your roadmap to build your memory bank.",
                grounded_concept_bridge=None,
                confidence="LOW"
            )

        # Relevance ranking on actual stored memories
        import re
        clean_words = re.sub(r'[^\w\s]', ' ', q_text).split()
        matched_memories = []
        for m in memories:
            m_text = (m.title + " " + m.summary + " " + m.topic + " " + " ".join(m.related_concepts)).lower()
            
            score = 0
            for word in clean_words:
                if len(word) > 2 and word in m_text:
                    score += 2
            
            if score > 0:
                matched_memories.append((m, score))

        matched_memories.sort(key=lambda x: x[1], reverse=True)
        top_recalled = [m for m, _ in matched_memories[:3]]

        if not top_recalled:
            return MemoryRecallResponse(
                person_id=person_id,
                query=query.query,
                recalled_memories=[],
                answer="I searched your personal memory vault, but I do not have a recorded memory matching this specific inquiry yet.",
                grounded_concept_bridge=None,
                confidence="LOW"
            )

        primary_mem = top_recalled[0]
        answer = f"Based on your recorded memory ({primary_mem.title}): {primary_mem.summary}"
        concept_bridge = f"{primary_mem.topic} → Scaffolding to Active Milestone" if primary_mem.related_concepts else None

        return MemoryRecallResponse(
            person_id=person_id,
            query=query.query,
            recalled_memories=top_recalled,
            answer=answer,
            grounded_concept_bridge=concept_bridge,
            confidence="HIGH"
        )

    async def get_cross_stage_bridge(
        self,
        person_id: str,
        current_concept: str = "Tree Traversal & Depth-First Search"
    ) -> CrossStageBridgeResponse:
        """
        Past → Present Concept Bridge:
        Identifies and explains how past mastered concepts scaffold into new learning contexts from real memories.
        """
        raw_mems = await self.store.get_personal_memories(person_id)
        memories = [MemoryItem(**m) for m in raw_mems]
        
        # Check if user has past foundational memories
        recursion_mem = next((m for m in memories if "recursion" in m.topic.lower() or "recursion" in m.title.lower()), None)
        
        if recursion_mem:
            return CrossStageBridgeResponse(
                person_id=person_id,
                current_concept=current_concept,
                past_concept=recursion_mem.title,
                past_stage=recursion_mem.source,
                context=recursion_mem.summary,
                connection_explanation=f"This milestone builds directly on your prior mastery of {recursion_mem.topic} in {recursion_mem.source}, applying those principles to {current_concept}.",
                confidence="HIGH"
            )

        return CrossStageBridgeResponse(
            person_id=person_id,
            current_concept=current_concept,
            past_concept="Foundational Programming",
            past_stage="Prerequisite Milestones",
            context="Foundational concept mastery will be connected here as you progress.",
            connection_explanation=f"{current_concept} requires structured problem-solving foundations. Complete prerequisite stages to unlock specific concept linkages.",
            confidence="MEDIUM"
        )
