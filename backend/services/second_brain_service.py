from typing import List, Dict, Any, Optional, Any
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
from backend.core.deterministic_rules import promote_memory
from backend.services.memory_reasoning_agent import MemoryReasoningAgent
from backend.services.pm_store import get_pm_store

class SecondBrainService:
    """
    PATHMIND Personal Second Brain & Hybrid Semantic Retrieval Engine.
    Enforces strict server-side person isolation, multi-factor ranking, source linking,
    conflict detection, and non-destructive memory consolidation.
    """
    def __init__(
        self,
        store: Optional[Any] = None,
        agent: Optional[MemoryReasoningAgent] = None
    ):
        self.store = store or get_pm_store()
        self.agent = agent or MemoryReasoningAgent()

    async def ingest_memory(
        self,
        person_id: str,
        payload: Dict[str, Any],
        skip_dedup: bool = False
    ) -> MemoryItem:
        """
        Ingests and validates a memory item with write-validation and source linking.
        Enforces evidence ceiling rule (unverified evidence cannot claim verified status).

        Promotion wiring (spec §13): before creating a new record, checks for an
        existing similar memory (same person + topic + similar title). If found,
        increments its observation_count and re-runs the pure promote_memory()
        rule — promoting OBSERVED -> CANDIDATE -> DURABLE instead of creating a
        duplicate. New memories start as OBSERVED (or CANDIDATE when marked
        HIGH/CRITICAL importance, per the promotion rule).
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

        title = payload.get("title", "Milestone Memory")
        topic = payload.get("topic", "General")
        content = payload.get("content") or payload.get("summary", "")

        # 2. Dedup + promotion: serialize per person so concurrent ingests of the
        #    same observation increment one record instead of creating duplicates.
        #    The lock covers check-and-insert so the pair is atomic.
        lock = self.store.get_person_lock(person_id) if not skip_dedup else None
        if lock is not None:
            await lock.acquire()
        try:
            if not skip_dedup:
                existing = await self._find_similar_memory(person_id, topic, title, content)
                if existing is not None:
                    return await self._reinforce_memory(existing, payload, ev_status)

            return await self._create_memory(
                person_id, payload, mem_type, nature, importance,
                title, topic, content, source_type, source_ref, ev_status
            )
        finally:
            if lock is not None:
                lock.release()

    async def _create_memory(
        self,
        person_id: str,
        payload: Dict[str, Any],
        mem_type: str,
        nature: str,
        importance: str,
        title: str,
        topic: str,
        content: str,
        source_type: str,
        source_ref: str,
        ev_status: str
    ) -> MemoryItem:
        """Creates a brand-new memory record (no similar memory exists)."""
        """Creates a brand-new memory record (no similar memory exists)."""
        mem_id = payload.get("memory_id") or f"mem_{int(datetime.now(timezone.utc).timestamp()*1000)}_{uuid.uuid4().hex[:6]}"
        initial_status = promote_memory(
            current_status=payload.get("promotion_status", "OBSERVED"),
            observation_count=int(payload.get("observation_count", 1)),
            importance=importance,
            evidence_verified=(ev_status == "VERIFIED"),
        )
        mem = MemoryItem(
            memory_id=mem_id,
            person_id=person_id,
            memory_type=mem_type,
            nature=nature,
            title=title,
            content=content,
            summary=payload.get("summary") or payload.get("content", ""),
            topic=topic,
            related_concepts=payload.get("related_concepts", []),
            source_type=source_type,
            source_reference=source_ref,
            source_event_id=payload.get("source_event_id"),
            related_goal_ids=payload.get("related_goal_ids", []),
            related_skill_ids=payload.get("related_skill_ids", []),
            related_artifact_ids=payload.get("related_artifact_ids", []),
            related_decision_ids=payload.get("related_decision_ids", []),
            confidence=payload.get("confidence", "HIGH"),
            importance=importance,
            lifecycle_status=payload.get("lifecycle_status", "CURRENT"),
            promotion_status=initial_status,
            observation_count=int(payload.get("observation_count", 1)),
            parent_memory_id=payload.get("parent_memory_id"),
            superseded_by=payload.get("superseded_by"),
            supersedes_reason=payload.get("supersedes_reason"),
            evidence_verification_status=ev_status,
            details=payload.get("details", {})
        )

        await self.store.save_personal_memory(person_id, mem.model_dump(mode="json"))
        return mem

    @staticmethod
    def _normalize_text(text: str) -> str:
        return re.sub(r"\s+", " ", re.sub(r"[^\w\s]", " ", (text or "").lower())).strip()

    @classmethod
    def _titles_similar(cls, a: str, b: str) -> bool:
        """
        Deterministic title similarity: exact normalized match, containment,
        or high token overlap. Conservative on purpose — false negatives only
        create a duplicate, false positives would merge distinct memories.
        """
        na, nb = cls._normalize_text(a), cls._normalize_text(b)
        if not na or not nb:
            return False
        if na == nb:
            return True
        if na in nb or nb in na:
            return True
        ta, tb = set(na.split()), set(nb.split())
        if not ta or not tb:
            return False
        jaccard = len(ta & tb) / len(ta | tb)
        return jaccard >= 0.6

    async def _find_similar_memory(
        self,
        person_id: str,
        topic: str,
        title: str,
        content: str
    ) -> Optional[MemoryItem]:
        """
        Internal lookup (bypasses the promotion read-filter on purpose):
        finds an existing CURRENT memory with the same topic and similar title
        so repeated observations reinforce it instead of duplicating it.
        """
        raw_mems = await self.store.get_personal_memories(person_id)
        topic_norm = self._normalize_text(topic)
        for m in raw_mems:
            try:
                mem = MemoryItem(**m)
            except Exception:
                continue
            if mem.lifecycle_status != "CURRENT":
                continue
            if self._normalize_text(mem.topic) != topic_norm:
                continue
            if self._titles_similar(mem.title, title):
                return mem
        return None

    async def _reinforce_memory(
        self,
        existing: MemoryItem,
        payload: Dict[str, Any],
        ev_status: str
    ) -> MemoryItem:
        """Re-observes an existing memory: bumps count, re-runs promotion rule."""
        existing.observation_count = int(existing.observation_count or 0) + 1
        new_status = promote_memory(
            current_status=existing.promotion_status,
            observation_count=existing.observation_count,
            importance=payload.get("importance", existing.importance),
            evidence_verified=(
                existing.evidence_verification_status == "VERIFIED" or ev_status == "VERIFIED"
            ),
        )
        existing.promotion_status = new_status
        # Merge forward: keep the strongest importance seen, union related concepts.
        rank = {"LOW": 0, "MEDIUM": 1, "HIGH": 2, "CRITICAL": 3}
        new_imp = payload.get("importance")
        if new_imp and rank.get(new_imp, 0) > rank.get(existing.importance, 0):
            existing.importance = new_imp
        for c in payload.get("related_concepts", []):
            if c not in existing.related_concepts:
                existing.related_concepts.append(c)
        existing.updated_at = datetime.now(timezone.utc).isoformat()
        await self.store.save_personal_memory(existing.person_id, existing.model_dump(mode="json"))
        return existing

    async def search_memories(
        self,
        person_id: str,
        query: str,
        current_task_context: Optional[str] = None,
        target_role: Optional[str] = None,
        status_filter: Optional[str] = None,
        include_observed: bool = False
    ) -> List[MemorySearchResultItem]:
        """
        Hybrid semantic + metadata retrieval strictly scoped to person_id.
        Multi-factor ranking:
          score = (semantic_match) * importance_weight * temporal_weight + task_context_bonus + evidence_bonus

        Promotion filter (spec §13): OBSERVED memories are single unconfirmed
        observations — too weak to drive behavior. Only CANDIDATE/DURABLE
        memories are returned unless include_observed=True opts in.
        """
        # Server-side person isolation
        raw_mems = await self.store.get_personal_memories(person_id)
        memories = [MemoryItem(**m) for m in raw_mems]

        if not include_observed:
            memories = [m for m in memories if m.promotion_status in ("CANDIDATE", "DURABLE")]

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
            target_role=req.target_role,
            include_observed=req.include_observed
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

        # Ingest new memory (skip dedup: the replacement intentionally resembles
        # the record it supersedes, and must not merge back into it).
        new_mem = await self.ingest_memory(person_id, new_memory_payload, skip_dedup=True)

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
