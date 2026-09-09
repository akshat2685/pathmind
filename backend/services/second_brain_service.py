from typing import List, Dict, Any, Optional
from datetime import datetime, timezone
import re
import uuid

from backend.core.memory_schemas import (
    MemoryItem,
    MemorySearchResultItem,
    SecondBrainQueryRequest,
    SecondBrainQueryResponse,
    ConsolidateMemoriesResponse
)
from backend.services.memory_reasoning_agent import MemoryReasoningAgent
from backend.services.store import FirestoreStore

class SecondBrainService:
    """
    PATHMIND Personal Second Brain & Hybrid Semantic Retrieval Engine.
    Enforces strict server-side person isolation, multi-factor ranking, source linking,
    conflict detection, and non-destructive memory consolidation.
    """
    def __init__(
        self,
        store: Optional[FirestoreStore] = None,
        agent: Optional[MemoryReasoningAgent] = None
    ):
        self.store = store or FirestoreStore()
        self.agent = agent or MemoryReasoningAgent()

    async def ingest_memory(
        self,
        person_id: str,
        payload: Dict[str, Any]
    ) -> MemoryItem:
        """
        Ingests and validates a memory item with write-validation and source linking.
        Enforces evidence ceiling rule (unverified evidence cannot claim verified status).
        """
        # 1. Verify source entities where referenced
        source_type = payload.get("source_type", "ROADMAP_STAGE")
        source_ref = payload.get("source_reference") or payload.get("source", "General Milestone")
        ev_status = payload.get("evidence_verification_status", "VERIFIED")

        # Evidence ceiling check:
        nature = payload.get("nature")
        if source_type in ["EVIDENCE", "EVIDENCE_SUBMISSION", "ARTIFACT"]:
            if payload.get("is_unverified"):
                ev_status = "UNVERIFIED"
                payload["confidence"] = "LOW"
                nature = "INFERENCE"

        event_type = payload.get("event_type", "").lower()
        mem_type = payload.get("memory_type")
        importance = payload.get("importance", "HIGH")

        if not nature:
            if "preference" in event_type:
                nature = "PREFERENCE"
            elif "goal" in event_type:
                nature = "GOAL"
            elif "strategy" in event_type:
                nature = "STRATEGY"
            elif "decision" in event_type:
                nature = "DECISION"
            elif "evidence" in event_type or "artifact" in event_type:
                nature = "FACT"
            else:
                nature = "EXPERIENCE"

        if not mem_type:
            if nature in ["PREFERENCE", "GOAL", "STRATEGY", "DECISION", "EVIDENCE"]:
                mem_type = nature
            elif "preference" in event_type:
                mem_type = "PREFERENCE"
            elif "goal" in event_type:
                mem_type = "GOAL"
            elif "strategy" in event_type:
                mem_type = "STRATEGY"
            else:
                mem_type = "EPISODIC"

        if nature in ["GOAL", "STRATEGY"] and "importance" not in payload:
            importance = "CRITICAL"
        elif nature == "PREFERENCE" and "importance" not in payload:
            importance = "MEDIUM"

        mem_id = payload.get("memory_id") or f"mem_{int(datetime.now(timezone.utc).timestamp()*1000)}_{uuid.uuid4().hex[:6]}"
        mem = MemoryItem(
            memory_id=mem_id,
            person_id=person_id,
            memory_type=mem_type,
            nature=nature,
            title=payload.get("title", "Milestone Memory"),
            content=payload.get("content") or payload.get("summary", ""),
            summary=payload.get("summary") or payload.get("content", ""),
            topic=payload.get("topic", "General"),
            related_concepts=payload.get("related_concepts", []),
            source_type=source_type,
            source_reference=source_ref,
            source_event_id=payload.get("source_event_id"),
            related_goal_ids=payload.get("related_goal_ids", []),
            related_skill_ids=payload.get("related_skill_ids", []),
            related_artifact_ids=payload.get("related_artifact_ids", []),
            related_decision_ids=payload.get("related_decision_ids", []),
            confidence=payload.get("confidence", "HIGH"),
            importance=payload.get("importance", "HIGH"),
            lifecycle_status=payload.get("lifecycle_status", "CURRENT"),
            parent_memory_id=payload.get("parent_memory_id"),
            superseded_by=payload.get("superseded_by"),
            supersedes_reason=payload.get("supersedes_reason"),
            evidence_verification_status=ev_status,
            details=payload.get("details", {})
        )

        await self.store.save_personal_memory(person_id, mem.model_dump(mode="json"))
        return mem

    async def search_memories(
        self,
        person_id: str,
        query: str,
        current_task_context: Optional[str] = None,
        target_role: Optional[str] = None,
        status_filter: Optional[str] = None
    ) -> List[MemorySearchResultItem]:
        """
        Hybrid semantic + metadata retrieval strictly scoped to person_id.
        Multi-factor ranking:
          score = (semantic_match) * importance_weight * temporal_weight + task_context_bonus + evidence_bonus
        """
        # Server-side person isolation
        raw_mems = await self.store.get_personal_memories(person_id)
        memories = [MemoryItem(**m) for m in raw_mems]

        if status_filter:
            memories = [m for m in memories if m.lifecycle_status == status_filter]

        if not memories:
            return []

        # Tokenize query terms
        clean_q = re.sub(r'[^\w\s]', ' ', query.lower()).split()
        q_tokens = {w for w in clean_q if len(w) > 2}

        # Concept taxonomy expansions
        concept_expansions = {
            "recursion": ["call stack", "stack frame", "base case", "dfs", "tree", "traversal"],
            "tree": ["recursion", "call stack", "stack frame", "traversal", "dfs"],
            "api": ["fastapi", "rest", "endpoint", "backend", "http"],
            "ml": ["machine learning", "pytorch", "scikit-learn", "classifier", "inference"],
            "backend": ["database", "sql", "api", "server", "fastapi"],
            "robotics": ["ros", "ros2", "slam", "gazebo", "perception", "lidar"]
        }

        expanded_tokens = set(q_tokens)
        for t in list(q_tokens):
            if t in concept_expansions:
                expanded_tokens.update(concept_expansions[t])

        if current_task_context:
            clean_ctx = re.sub(r'[^\w\s]', ' ', current_task_context.lower()).split()
            for w in clean_ctx:
                if len(w) > 2:
                    expanded_tokens.add(w)
                    if w in concept_expansions:
                        expanded_tokens.update(concept_expansions[w])

        scored_items: List[MemorySearchResultItem] = []

        importance_multipliers = {
            "CRITICAL": 1.5,
            "HIGH": 1.2,
            "MEDIUM": 1.0,
            "LOW": 0.7
        }

        temporal_multipliers = {
            "CURRENT": 1.3,
            "HISTORICAL": 1.0,
            "SUPERSEDED": 0.5,
            "EXPIRED": 0.2,
            "UNKNOWN": 0.8
        }

        for mem in memories:
            raw_text = f"{mem.title} {mem.content} {mem.summary} {mem.topic} {' '.join(mem.related_concepts)} {mem.source_reference}".lower()

            # Base semantic score
            base_score = 0.0
            matched_terms = []
            for token in expanded_tokens:
                if token in mem.title.lower():
                    base_score += 4.0
                    matched_terms.append(f"Title contains '{token}'")
                elif token in mem.topic.lower():
                    base_score += 3.0
                    matched_terms.append(f"Topic matches '{token}'")
                elif any(token in c.lower() for c in mem.related_concepts):
                    base_score += 3.0
                    matched_terms.append(f"Concept matches '{token}'")
                elif token in raw_text:
                    base_score += 1.5
                    matched_terms.append(f"Content mentions '{token}'")

            if base_score == 0.0:
                continue

            # Multi-factor adjustments
            imp_mult = importance_multipliers.get(mem.importance, 1.0)
            temp_mult = temporal_multipliers.get(mem.lifecycle_status, 1.0)
            final_score = base_score * imp_mult * temp_mult

            # Context boost
            if current_task_context:
                ct_clean = current_task_context.lower()
                if any(c in ct_clean for c in mem.related_concepts) or mem.topic.lower() in ct_clean:
                    final_score += 3.0
                    matched_terms.append("Directly relevant to current task context")

            # Evidence boost
            if mem.evidence_verification_status == "VERIFIED":
                final_score += 2.0
                matched_terms.append("Verified by evidence assertion")

            provenance = [
                f"Source: {mem.source_type} ({mem.source_reference})",
                f"Nature: {mem.nature}",
                f"Status: {mem.lifecycle_status}"
            ]

            relevance_reason = "; ".join(matched_terms[:3]) if matched_terms else "Conceptually relevant"
            scored_items.append(
                MemorySearchResultItem(
                    memory=mem,
                    relevance_score=round(final_score, 2),
                    relevance_reason=relevance_reason,
                    provenance_chain=provenance
                )
            )

        scored_items.sort(key=lambda x: x.relevance_score, reverse=True)
        return scored_items

    async def query_second_brain(
        self,
        person_id: str,
        req: SecondBrainQueryRequest
    ) -> SecondBrainQueryResponse:
        """
        Executes hybrid semantic search over authenticated person's vault,
        detects memory conflicts, and synthesizes a grounded recall answer.
        """
        search_results = await self.search_memories(
            person_id=person_id,
            query=req.query,
            current_task_context=req.current_task_context,
            target_role=req.target_role
        )

        if not search_results:
            return SecondBrainQueryResponse(
                person_id=person_id,
                query=req.query,
                status="NO_RELEVANT_MEMORY",
                answer="I searched your personal memory vault, but do not have a recorded memory matching this specific inquiry (no recorded memory found).",
                retrieved_memories=[],
                conflicting_memories=[],
                confidence="LOW"
            )

        # Conflict Detection: check if multiple CURRENT memories make contradictory assertions
        conflicting: List[MemoryItem] = []
        current_mems = [r.memory for r in search_results if r.memory.lifecycle_status == "CURRENT"]

        # Check for conflicting goals or career paths
        goal_mems = [m for m in current_mems if m.memory_type == "GOAL" or m.nature == "GOAL"]
        if len(goal_mems) > 1:
            topics = {m.topic.lower() for m in goal_mems}
            if len(topics) > 1:
                conflicting = goal_mems

        top_memories = [r.memory for r in search_results[:5]]

        # Concept bridge detection
        concept_bridge = None
        if req.current_task_context and top_memories:
            concept_bridge = f"{top_memories[0].topic} → Scaffolding to {req.current_task_context}"

        # Synthesize answer with MemoryReasoningAgent
        synth = await self.agent.synthesize_recall_answer(
            query=req.query,
            retrieved_memories=top_memories,
            current_task_context=req.current_task_context,
            target_role=req.target_role
        )

        status = "MEMORY_CONFLICT" if conflicting else synth.get("status", "RESOLVED")

        return SecondBrainQueryResponse(
            person_id=person_id,
            query=req.query,
            status=status,
            answer=synth.get("answer", "Recalled memory"),
            retrieved_memories=search_results[:5],
            conflicting_memories=conflicting,
            confidence=synth.get("confidence", "HIGH"),
            concept_bridge=concept_bridge
        )

    async def supersede_memory(
        self,
        person_id: str,
        old_memory_id: str,
        reason: str,
        new_memory_payload: Dict[str, Any]
    ) -> MemoryItem:
        """
        Replaces an obsolete memory: marks previous memory as SUPERSEDED with reason,
        and creates the new memory with lifecycle_status=CURRENT.
        """
        raw_mems = await self.store.get_personal_memories(person_id)
        old_mem_dict = next((m for m in raw_mems if m.get("memory_id") == old_memory_id), None)
        if not old_mem_dict:
            raise ValueError(f"Memory {old_memory_id} not found.")

        old_mem = MemoryItem(**old_mem_dict)
        new_memory_payload["parent_memory_id"] = old_mem.memory_id
        new_memory_payload["lifecycle_status"] = "CURRENT"

        # Ingest new memory
        new_mem = await self.ingest_memory(person_id, new_memory_payload)

        # Update old memory to SUPERSEDED
        old_mem.lifecycle_status = "SUPERSEDED"
        old_mem.superseded_by = new_mem.memory_id
        old_mem.supersedes_reason = reason
        old_mem.updated_at = datetime.now(timezone.utc).isoformat()

        await self.store.save_personal_memory(person_id, old_mem.model_dump(mode="json"))
        return new_mem

    async def consolidate_memories(
        self,
        person_id: str,
        source_memory_ids: List[str],
        consolidated_title: str,
        consolidated_summary: str,
        topic: str
    ) -> ConsolidateMemoriesResponse:
        """
        Summarizes multiple related low-level memories into a consolidated memory.
        Crucial rule: original source memories are preserved as HISTORICAL, never deleted.
        """
        raw_mems = await self.store.get_personal_memories(person_id)
        source_mems = [MemoryItem(**m) for m in raw_mems if m.get("memory_id") in source_memory_ids]

        if not source_mems:
            raise ValueError("No matching source memories found to consolidate.")

        # Create consolidated memory
        cons_mem = MemoryItem(
            memory_id=f"mem_cons_{int(datetime.now(timezone.utc).timestamp()*1000)}_{uuid.uuid4().hex[:6]}",
            person_id=person_id,
            memory_type="SEMANTIC",
            nature="STRATEGY",
            title=consolidated_title,
            content=consolidated_summary,
            summary=consolidated_summary,
            topic=topic,
            related_concepts=list({c for m in source_mems for c in m.related_concepts}),
            source_type="CONSOLIDATED_SUMMARY",
            source_reference=f"Consolidated from {len(source_mems)} milestone events",
            is_consolidated=True,
            consolidated_source_ids=source_memory_ids,
            importance="HIGH",
            confidence="HIGH",
            lifecycle_status="CURRENT"
        )
        await self.store.save_personal_memory(person_id, cons_mem.model_dump(mode="json"))

        # Mark source memories as HISTORICAL
        for sm in source_mems:
            sm.lifecycle_status = "HISTORICAL"
            sm.updated_at = datetime.now(timezone.utc).isoformat()
            await self.store.save_personal_memory(person_id, sm.model_dump(mode="json"))

        return ConsolidateMemoriesResponse(
            consolidated_memory=cons_mem,
            archived_source_count=len(source_mems)
        )

    async def update_memory(
        self,
        person_id: str,
        memory_id: str,
        updates: Dict[str, Any]
    ) -> MemoryItem:
        """
        Allows student to annotate or correct their own personal memory.
        """
        raw_mems = await self.store.get_personal_memories(person_id)
        target_dict = next((m for m in raw_mems if m.get("memory_id") == memory_id), None)
        if not target_dict:
            raise ValueError(f"Memory {memory_id} not found.")

        target = MemoryItem(**target_dict)
        if "title" in updates:
            target.title = updates["title"]
        if "content" in updates:
            target.content = updates["content"]
            target.summary = updates["content"]
        if "importance" in updates:
            target.importance = updates["importance"]
        if "lifecycle_status" in updates:
            target.lifecycle_status = updates["lifecycle_status"]

        target.updated_at = datetime.now(timezone.utc).isoformat()
        await self.store.save_personal_memory(person_id, target.model_dump(mode="json"))
        return target

    async def delete_memory(self, person_id: str, memory_id: str) -> bool:
        return await self.store.delete_personal_memory(person_id, memory_id)
