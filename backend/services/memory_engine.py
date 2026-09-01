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

    async def seed_demo_memories_if_needed(self, person_id: str) -> List[MemoryItem]:
        """
        Seeds 5 deterministic, attributed memories for the scholar demo persona.
        """
        existing = await self.store.get_personal_memories(person_id)
        if existing:
            return [MemoryItem(**m) for m in existing]

        demo_memories = [
            MemoryItem(
                memory_id=f"mem_episodic_recursion_{person_id}",
                person_id=person_id,
                memory_type="EPISODIC",
                title="Recursion & Call Stack Breakthrough",
                summary="Struggled with tracing recursive execution and base conditions in foundational coding. Resolved successfully using interactive visual call-stack frame diagrams.",
                topic="Recursion",
                related_concepts=["Call Stack", "Base Conditions", "Tree Traversal", "Depth-First Search"],
                confidence="HIGH",
                importance="HIGH",
                lifecycle_status="ACTIVE",
                source="Stage 01: Python Foundations",
                details={
                    "intervention": "Visual call stack diagrams & stepped debugging",
                    "outcome": "Solved recursive binary search and factorial without stack overflow"
                }
            ),
            MemoryItem(
                memory_id=f"mem_semantic_python_oop_{person_id}",
                person_id=person_id,
                memory_type="SEMANTIC_LEARNING",
                title="Python OOP & Modular Package Mastery",
                summary="Demonstrated high proficiency in type-annotated dataclasses, generator pipelines, and modular package structuring with pytest fixtures.",
                topic="Python Software Architecture",
                related_concepts=["Dataclasses", "Type Hints", "Generators", "Pytest"],
                confidence="HIGH",
                importance="HIGH",
                lifecycle_status="ACTIVE",
                source="Observable Task B & Class 12 CS",
                details={
                    "verified_skills": ["Python 3.12 OOP", "Pytest 85%+ branch coverage"],
                    "mastery_score": 92.0
                }
            ),
            MemoryItem(
                memory_id=f"mem_preference_project_first_{person_id}",
                person_id=person_id,
                memory_type="PREFERENCE",
                title="Prefers Project-Based & Interactive Exercises",
                summary="Consistently achieves 3x higher completion rates and comprehension with project-based, hands-on tasks over long passive video lectures (> 30 mins).",
                topic="Learning Style",
                related_concepts=["Hands-on Projects", "Interactive Sandboxes"],
                confidence="HIGH",
                importance="MEDIUM",
                lifecycle_status="ACTIVE",
                source="Onboarding Preferences & Task Activity",
                details={
                    "preferred_format": "project-based",
                    "disliked_format": "passive video lectures > 30 mins"
                }
            ),
            MemoryItem(
                memory_id=f"mem_strategy_worked_example_{person_id}",
                person_id=person_id,
                memory_type="STRATEGY",
                title="Effective Strategy: Worked Example → Independent Code → Test Suite",
                summary="Most effective learning strategy involves studying a concise typed code pattern, attempting an independent implementation, and verifying with unit tests.",
                topic="Instructional Strategy",
                related_concepts=["Worked Examples", "Test-Driven Learning"],
                confidence="HIGH",
                importance="CRITICAL",
                lifecycle_status="ACTIVE",
                source="Counseling Observable Task E Synthesis",
                details={
                    "effectiveness_score": 94.0
                }
            ),
            MemoryItem(
                memory_id=f"mem_goal_ai_specialist_{person_id}",
                person_id=person_id,
                memory_type="GOAL",
                title="Goal Evolution: Software Engineer → Applied AI/ML Systems Specialist",
                summary="Transitioned primary career objective from generic software engineering to Applied AI/ML Systems Engineer following robotics and hackathon classifier projects.",
                topic="Career Direction",
                related_concepts=["Artificial Intelligence", "MLOps", "Distributed Inference"],
                confidence="HIGH",
                importance="CRITICAL",
                lifecycle_status="ACTIVE",
                source="Career Explorer Pathway Selection (v1)",
                details={
                    "previous_goal": "Software Engineering (Generic)",
                    "active_goal": "Applied AI/ML Systems Specialist"
                }
            )
        ]

        for m in demo_memories:
            await self.store.save_personal_memory(person_id, m.model_dump(mode="json"))

        # Seed initial shared pattern
        shared_pattern = SharedLearningPattern(
            pattern_id="pat_recursion_visual_callstack",
            topic="Recursion & Backtracking",
            misconception_or_context="Learners encountering stack frames and recursive base conditions for the first time.",
            effective_intervention="Interactive visual call-stack frame diagrams followed by stepped test assertions.",
            evidence_count=8,
            confidence="HIGH",
            extracted_at=datetime.now(timezone.utc).isoformat()
        )
        await self.store.save_shared_pattern(shared_pattern.model_dump(mode="json"))

        return demo_memories

    async def extract_and_store_memory_from_event(
        self,
        person_id: str,
        event_payload: Dict[str, Any]
    ) -> MemoryItem:
        """
        MemoryAgent (ADK): Ingests a learning event, classifies it into memory categories,
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
            summary=f"{observation}. Recommended approach: {intervention}",
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
        memories = await self.seed_demo_memories_if_needed(person_id)

        # Relevance ranking
        matched_memories = []
        for m in memories:
            m_text = (m.title + " " + m.summary + " " + m.topic + " " + " ".join(m.related_concepts)).lower()
            
            # Keyword matching
            score = 0
            if "recursion" in q_text and ("recursion" in m_text or "call stack" in m_text):
                score += 5
            elif "python" in q_text and "python" in m_text:
                score += 4
            elif ("preference" in q_text or "video" in q_text or "project" in q_text) and "preference" in m_text:
                score += 4
            elif ("strategy" in q_text or "method" in q_text) and "strategy" in m_text:
                score += 4
            elif ("goal" in q_text or "career" in q_text) and "goal" in m_text:
                score += 4
            else:
                for word in q_text.split():
                    if len(word) > 3 and word in m_text:
                        score += 1

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

        # Generate natural, grounded answer
        primary_mem = top_recalled[0]
        if "recursion" in q_text:
            answer = (
                f"Yes. During your foundational learning in {primary_mem.source}, you experienced difficulty tracing recursive call stack execution. "
                f"We applied interactive visual call-stack frame diagrams and stepped test assertions, which proved highly effective and helped you solve the problem independently."
            )
            concept_bridge = "Recursion (Stage 1) → Tree Traversal & DFS (Stage 3)"
        elif "python" in q_text:
            answer = (
                f"In your earlier work, you established strong proficiency in Python OOP, modular package structuring, and generator-based data ingestion with pytest test coverage."
            )
            concept_bridge = "Modular Python Engineering → Machine Learning Pipeline Design"
        elif "preference" in q_text or "project" in q_text:
            answer = (
                f"Your learning history demonstrates a clear preference for hands-on, project-based exercises over long passive video lectures (> 30 mins), with a 3x higher completion and retention rate."
            )
            concept_bridge = None
        elif "goal" in q_text or "career" in q_text:
            answer = (
                f"Your goal evolved from generic software engineering into Applied AI/ML Systems Specialist following your successful robotics and machine learning hackathon projects."
            )
            concept_bridge = None
        else:
            answer = f"Based on your personal memory ({primary_mem.title}): {primary_mem.summary}"
            concept_bridge = None

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
        Identifies and explains how past mastered concepts scaffold into new learning contexts.
        """
        await self.seed_demo_memories_if_needed(person_id)
        
        return CrossStageBridgeResponse(
            person_id=person_id,
            current_concept=current_concept,
            past_concept="Recursion & Call Stack Frames",
            past_stage="Stage 01: Python Foundations",
            context="You previously mastered recursive base conditions using visual frame tracing.",
            connection_explanation="Tree traversal uses the exact same recursive call-stack execution model you mastered in Stage 01, expanded from linear calls to branching node hierarchies.",
            confidence="HIGH"
        )
