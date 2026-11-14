import re
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional, Any
from backend.core.memory_schemas import (
    MemoryItem,
    ProactiveMemoryContext,
    MemoryRelevanceReason
)
from backend.services.pm_store import get_pm_store

class ProactiveMemoryService:
    """
    Invisible Cognitive Memory Subsystem for PATHMIND (Prompt 24).
    Retrieves task-conditioned personal context automatically without requiring
    the user to visit a memory page, search a vault, or ask questions.
    
    Adheres strictly to:
    1. Zero fabrication (missing memory -> NO_RELEVANT_MEMORY).
    2. Person isolation (person A never sees person B's memory).
    3. Smallest useful set (max 2 items).
    4. Current explicit input / newer verified state dominance over historical memory.
    5. Durable memory-write policy (ignoring trivial UI interactions).
    """
    def __init__(self, store: Optional[Any] = None, memory_service: Optional[Any] = None):
        # Unified constructor: main callers pass store= (PmStore);
        # college callers pass memory_service= (CollegeMemoryService) or
        # pass it positionally. A CollegeMemoryService wraps a store in
        # its .store attribute — unwrap it so the store-based
        # implementation below always works against a real store.
        # The memory service itself is kept for the college agent-tool
        # methods (retrieve/promote/supersede), which operate on
        # CollegeMemoryService, not on the raw store. Default store is
        # PmStore (main); a bare CollegeMemoryService() would default
        # its own store to FirestoreStore, which must never leak into
        # the main path.
        # Positional compatibility: college callers pass a CollegeMemoryService
        # positionally — college's signature was (memory_service, store),
        # main's is (store, memory_service). A memory service is not a
        # store: real stores (PmStore / FirestoreStore / InMemoryStore)
        # all expose get_personal_memories, CollegeMemoryService does not.
        if memory_service is None and store is not None and not hasattr(store, "get_personal_memories"):
            memory_service = store
            store = None
        if store is None and memory_service is not None:
            store = getattr(memory_service, "store", None) or memory_service
        if store is None:
            store = get_pm_store()
        self.store = store
        if memory_service is None:
            from backend.services.college_memory_service import CollegeMemoryService
            memory_service = CollegeMemoryService(store=store)
        self.memory_service = memory_service

    # --- Step 8: Explicit Memory-Write Policy ---
    DURABLE_EVENT_TYPES = {
        "MASTERY_DEMONSTRATED",
        "RECURRING_MISCONCEPTION",
        "GOAL_CHANGE",
        "PREFERENCE_CONFIRMED",
        "DECISION_RECORDED",
        "EVIDENCE_VERIFIED",
        "EVALUATION_PASSED",
        "EVALUATION_FAILED",
        "ROADMAP_ADAPTATION_ACCEPTED",
        "ROADMAP_ADAPTATION_REJECTED",
        "MILESTONE_COMPLETED",
        "STAGE_COMPLETED",
        "PROJECT_SUBMITTED",
        "EVIDENCE_SUBMITTED"
    }

    TRANSIENT_EVENT_TYPES = {
        "PAGE_VIEW",
        "NAVIGATE",
        "MODAL_OPEN",
        "MODAL_CLOSE",
        "SEARCH_QUERY",
        "BUTTON_CLICK",
        "TELEMETRY_PING",
        "HEARTBEAT",
        "TAB_SWITCH"
    }

    def should_create_memory(self, event_payload: Dict[str, Any]) -> bool:
        """
        Determines whether an event represents durable learning or personalization value,
        filtering out transient UI interactions.
        """
        raw_type = (event_payload.get("event_type") or "").upper()
        if raw_type in self.TRANSIENT_EVENT_TYPES:
            return False
        
        if raw_type in self.DURABLE_EVENT_TYPES:
            return True

        # Check content markers for durability
        nature = (event_payload.get("nature") or "").upper()
        if nature in ["DECISION", "GOAL", "STRATEGY", "PREFERENCE", "FACT"]:
            return True
        
        if nature == "EXPERIENCE":
            importance = (event_payload.get("importance") or "").upper()
            if importance in ["HIGH", "CRITICAL"] or "milestone" in str(event_payload).lower():
                return True

        # Discard if merely a transient UI click or telemetry
        title = (event_payload.get("title") or "").lower()
        if any(t in title for t in ["click", "view", "open", "close", "scroll"]):
            return False

        return False

    async def record_durable_memory_if_eligible(
        self,
        person_id: str,
        event_payload: Dict[str, Any]
    ) -> Optional[MemoryItem]:
        """
        Records an event into long-term personal memory only if it passes the durability policy.
        """
        if not self.should_create_memory(event_payload):
            return None

        from backend.services.second_brain_service import SecondBrainService
        sb = SecondBrainService(store=self.store)
        return await sb.ingest_memory(person_id, event_payload)

    async def get_proactive_memory_context(
        self,
        person_id: str,
        task_type: str = "NEXT_LEARNING_ACTION",
        current_goal: Optional[str] = None,
        current_stage: Optional[str] = None,
        current_concept: Optional[str] = None,
        current_decision: Optional[str] = None,
        constraints: Optional[Dict[str, Any]] = None,
        explicit_user_input: Optional[str] = None,
        target_direction: Optional[str] = None,
        include_observed: bool = False,
        uid: Optional[str] = None,
        current_task: Optional[str] = None
    ) -> ProactiveMemoryContext:
        """
        Proactively retrieves the smallest useful set of relevant personal memories
        for a given task context.

        Promotion filter (spec §13): only CANDIDATE/DURABLE memories drive
        proactive behavior. OBSERVED memories are single unconfirmed sightings —
        pass include_observed=True to opt in (e.g. for debugging).
        """
        # College call style: get_proactive_memory_context(uid, "free-text
        # query") or (uid=..., current_task=...). The 2nd positional is then
        # a relevance query, not a task-type enum — normalize it and use
        # the text as the relevance query (concept) for scoring.
        _KNOWN_TASK_TYPES = {"NEXT_LEARNING_ACTION", "RESUME_GENERATION",
            "ROADMAP_GENERATION", "GOAL_CHANGE", "CAREER_DIRECTION",
            "EVIDENCE_EVALUATION", "OPPORTUNITY_MATCHING",
            "DECISION_SUPPORT", "GENERAL_CONTEXT"}
        person_id = person_id or uid
        _college_style = (uid is not None or current_task is not None
                          or task_type not in _KNOWN_TASK_TYPES)
        _query_text = current_task
        if _query_text is None and task_type not in _KNOWN_TASK_TYPES:
            _query_text = task_type
            task_type = "NEXT_LEARNING_ACTION"
        if _college_style and _query_text and not current_concept:
            current_concept = _query_text

        raw_mems = await self.store.get_personal_memories(person_id)
        all_memories = [MemoryItem(**m) for m in raw_mems]

        # College long-term memories live in the CollegeMemoryService, not
        # in the personal-memories store. Merge them (college-style calls
        # only) so the college mentor / pipeline see promoted memories.
        if _college_style and _query_text and hasattr(
                self.memory_service, "get_long_term_memories"):
            try:
                for _d in await self.retrieve_relevant_memories(
                        person_id, _query_text):
                    all_memories.append(MemoryItem(
                        memory_id=_d.get("memory_id") or f"mem_college_{len(all_memories)}",
                        person_id=person_id,
                        title=_d.get("title", ""),
                        content=_d.get("content", ""),
                        topic=_d.get("topic", "General"),
                        nature=_d.get("nature", "EXPERIENCE"),
                        promotion_status="DURABLE",
                        lifecycle_status="CURRENT",
                        source_type="COLLEGE_LONG_TERM",
                        source_reference="College long-term memory",
                    ))
            except Exception:
                pass

        if not all_memories:
            return ProactiveMemoryContext(
                person_id=person_id,
                task_type=task_type,
                retrieved_memories=[],
                status="NO_RELEVANT_MEMORY",
                proactive_summary=""
            )

        # 1. RESUME_GENERATION SAFETY CHECK (Rule 16)
        # Memory inferences may NEVER become resume facts.
        if task_type == "RESUME_GENERATION":
            return ProactiveMemoryContext(
                person_id=person_id,
                task_type=task_type,
                retrieved_memories=[],
                status="UNVERIFIED_MEMORY_ONLY",
                proactive_summary="Resume generation relies strictly on canonical verified profile facts. Memory inferences are excluded from resume generation."
            )

        # Promotion filter (spec §13): only CANDIDATE/DURABLE memories drive
        # proactive behavior. Applied after the safety checks above so they
        # keep their exact statuses regardless of promotion state.
        if not include_observed:
            all_memories = [m for m in all_memories if m.promotion_status in ("CANDIDATE", "DURABLE")]

        if not all_memories:
            return ProactiveMemoryContext(
                person_id=person_id,
                task_type=task_type,
                retrieved_memories=[],
                status="NO_RELEVANT_MEMORY",
                proactive_summary=""
            )

        active_goal = current_goal or target_direction

        # 2. Check for explicit user input / current direction overriding older memory (Rule 11)
        if explicit_user_input or active_goal:
            input_text = (explicit_user_input or active_goal or "").lower()
            conflicting_historical = [
                m for m in all_memories
                if m.nature in ["GOAL", "DECISION"] and
                m.lifecycle_status == "CURRENT" and
                any(w in m.title.lower() or w in m.topic.lower() for w in ["web", "developer", "engineer", "designer", "architect", "scientist", "trader"]) and
                not any(w in input_text for w in m.title.lower().split() if len(w) > 3)
            ]
            if conflicting_historical:
                return ProactiveMemoryContext(
                    person_id=person_id,
                    task_type=task_type,
                    retrieved_memories=conflicting_historical[:2],
                    relevance_reasons=[MemoryRelevanceReason.GOAL_HISTORY.value],
                    temporal_state="SUPERSEDED",
                    status="SUPERSEDED_BY_CURRENT_INPUT",
                    proactive_summary=f"Current explicit direction '{active_goal or explicit_user_input}' supersedes historical memory."
                )

        # Filter out SUPERSEDED or EXPIRED memories for active reasoning
        active_memories = [m for m in all_memories if m.lifecycle_status == "CURRENT"]
        if not active_memories:
            active_memories = [m for m in all_memories if m.lifecycle_status != "SUPERSEDED"]

        candidates: List[tuple[MemoryItem, float, List[str]]] = []

        # 3. Task-Conditioned Scoring & Selection
        for mem in active_memories:
            score = 0.0
            reasons = []
            mem_text = f"{mem.title} {mem.topic} {mem.content} {mem.summary} {' '.join(mem.related_concepts)}".lower()

            if task_type == "NEXT_LEARNING_ACTION":
                # Check concept relevance
                if current_concept:
                    concept_words = [w.lower() for w in re.sub(r'[^\w\s]', '', current_concept).split() if len(w) > 2]
                    matches = [w for w in concept_words if w in mem_text]
                    if matches:
                        score += 5.0 * len(matches)
                        reasons.append(MemoryRelevanceReason.RELATED_CONCEPT.value)

                # Previous struggles or misconceptions
                if "misconception" in mem.topic.lower() or "struggle" in mem_text or "rate limit" in mem_text:
                    score += 6.0
                    reasons.append(MemoryRelevanceReason.PRIOR_STRUGGLE.value)
                elif mem.nature == "STRATEGY" or "strategy" in mem.topic.lower():
                    score += 4.0
                    reasons.append(MemoryRelevanceReason.PAST_STRATEGY.value)
                elif mem.nature == "PREFERENCE":
                    score += 2.0
                    reasons.append(MemoryRelevanceReason.LEARNING_PREFERENCE.value)
                elif mem.nature == "SKILL_KNOWLEDGE":
                    score += 3.0
                    reasons.append(MemoryRelevanceReason.SKILL_HISTORY.value)

            elif task_type in ["ROADMAP_GENERATION", "GOAL_CHANGE"]:
                if mem.nature in ["GOAL", "DECISION"]:
                    score += 5.0
                    reasons.append(MemoryRelevanceReason.GOAL_HISTORY.value if mem.nature == "GOAL" else MemoryRelevanceReason.PAST_DECISION.value)
                elif mem.nature == "PREFERENCE":
                    score += 4.0
                    reasons.append(MemoryRelevanceReason.LEARNING_PREFERENCE.value)
                elif constraints and any(k.lower() in mem_text for k in constraints.keys()):
                    score += 3.0
                    reasons.append(MemoryRelevanceReason.KNOWN_CONSTRAINT.value)
                
                if active_goal:
                    goal_words = [w.lower() for w in re.sub(r'[^\w\s]', '', active_goal).split() if len(w) > 2]
                    if any(w in mem_text for w in goal_words):
                        score += 4.0
                        reasons.append(MemoryRelevanceReason.CAREER_PREFERENCE.value)

            elif task_type == "CAREER_DIRECTION":
                if mem.nature in ["GOAL", "DECISION"]:
                    score += 5.0
                    reasons.append(MemoryRelevanceReason.CAREER_PREFERENCE.value)
                    reasons.append(MemoryRelevanceReason.GOAL_HISTORY.value)
                elif active_goal and any(w in mem_text for w in active_goal.lower().split() if len(w) > 3):
                    score += 4.0
                    reasons.append(MemoryRelevanceReason.GOAL_HISTORY.value)

            elif task_type == "EVIDENCE_EVALUATION":
                if mem.nature in ["FACT", "EXPERIENCE"] or mem.source_type in ["EVIDENCE", "ARTIFACT"]:
                    score += 5.0
                    reasons.append(MemoryRelevanceReason.SKILL_HISTORY.value)
                if current_concept and any(w in mem_text for w in current_concept.lower().split() if len(w) > 3):
                    score += 3.0
                    reasons.append(MemoryRelevanceReason.RELATED_CONCEPT.value)

            elif task_type == "OPPORTUNITY_MATCHING":
                if mem.nature == "PREFERENCE" and any(w in mem_text for w in ["remote", "hybrid", "onsite", "relocation", "city"]):
                    score += 5.0
                    reasons.append(MemoryRelevanceReason.KNOWN_CONSTRAINT.value)
                elif mem.nature == "DECISION":
                    score += 3.0
                    reasons.append(MemoryRelevanceReason.PAST_DECISION.value)

            elif task_type == "DECISION_SUPPORT":
                if mem.nature == "DECISION":
                    score += 5.0
                    reasons.append(MemoryRelevanceReason.PAST_DECISION.value)
                elif mem.nature == "STRATEGY":
                    score += 3.0
                    reasons.append(MemoryRelevanceReason.PAST_STRATEGY.value)

            else:
                if current_concept and any(w in mem_text for w in current_concept.lower().split() if len(w) > 3):
                    score += 3.0
                    reasons.append(MemoryRelevanceReason.RELATED_CONCEPT.value)
                if active_goal and any(w in mem_text for w in active_goal.lower().split() if len(w) > 3):
                    score += 2.0
                    reasons.append(MemoryRelevanceReason.GOAL_HISTORY.value)

            if score > 0:
                candidates.append((mem, score, reasons))

        if not candidates:
            return ProactiveMemoryContext(
                person_id=person_id,
                task_type=task_type,
                retrieved_memories=[],
                status="NO_RELEVANT_MEMORY",
                proactive_summary=""
            )

        # Sort and take smallest useful set (strictly capped at 2 items)
        candidates.sort(key=lambda x: x[1], reverse=True)
        top_candidates = candidates[:2]

        retrieved = [c[0] for c in top_candidates]
        all_reasons = []
        for c in top_candidates:
            for r in c[2]:
                if r not in all_reasons:
                    all_reasons.append(r)
        
        if not all_reasons:
            all_reasons = [MemoryRelevanceReason.RELATED_CONCEPT.value]

        provenance = [f"{m.source_type} ({m.source_reference})" for m in retrieved]

        # Conflict Detection: multiple active memories with opposing directions/goals
        conflicts = []
        if len(retrieved) > 1:
            if retrieved[0].nature == retrieved[1].nature == "GOAL" and retrieved[0].title.lower() != retrieved[1].title.lower():
                conflicts = retrieved
            elif retrieved[0].nature == retrieved[1].nature == "PREFERENCE" and "remote" in retrieved[0].content.lower() and "onsite" in retrieved[1].content.lower():
                conflicts = retrieved

        if conflicts:
            status = "CONFLICT_DETECTED"
            summary = f"CONFLICT DETECTED: Multiple active records assert differing directions ({', '.join(m.title for m in conflicts)}). Clarification required."
        else:
            status = "ACTIVE_RECALL"
            top_mem = retrieved[0]
            if top_mem.nature == "STRATEGY":
                summary = f"Prior experience demonstrated that '{top_mem.title}' was effective."
            elif top_mem.nature == "PREFERENCE":
                summary = f"Maintains learning preference: {top_mem.summary or top_mem.title}."
            elif top_mem.nature == "GOAL":
                summary = f"Prior declared direction: {top_mem.title}."
            elif MemoryRelevanceReason.PRIOR_STRUGGLE.value in all_reasons:
                summary = f"Relevant prior learning context: {top_mem.title}."
            else:
                summary = f"Relevant prior learning context: {top_mem.title}."

        return ProactiveMemoryContext(
            person_id=person_id,
            task_type=task_type,
            retrieved_memories=retrieved,
            relevance_reasons=all_reasons,
            confidence="HIGH" if top_candidates[0][1] >= 4.0 else "MEDIUM",
            source_provenance=provenance,
            conflicting_memories=conflicts,
            temporal_state="CURRENT",
            evidence_status=retrieved[0].evidence_verification_status,
            status=status,
            proactive_summary=summary
        )

    # --- College agent tools (unified app) -------------------------------
    # These operate on CollegeMemoryService (long-term college memories).
    # Main callers never invoke them; college callers (orchestrator, tests)
    # rely on them. Kept verbatim from the college branch.

    async def retrieve_relevant_memories(self, uid: str, query: str) -> List[Dict[str, Any]]:
        """
        Agent Tool: Retrieves relevant long-term memories for a user given a query.
        """
        mems = await self.memory_service.get_long_term_memories(uid)
        active_mems = [m for m in mems if m.status == "CURRENT"]

        # Simple relevance: check if any query word is in the content or title
        query_words = set(query.lower().split())
        relevant = []
        for mem in active_mems:
            content_words = set(f"{mem.title} {mem.content}".lower().split())
            if query_words.intersection(content_words):
                relevant.append(mem)

        # Fallback to all if no strong match found
        if not relevant:
            relevant = active_mems

        return [m.model_dump(mode="json") for m in relevant[:5]]

    async def promote_to_long_term_memory(
        self,
        uid: str,
        title: str,
        content: str,
        nature: str = "EXPERIENCE"
    ) -> Dict[str, Any]:
        """
        Agent Tool: Promotes a new insight or preference to long-term memory.
        """
        mem = await self.memory_service.record_long_term_memory(
            uid=uid,
            title=title,
            content=content,
            nature=nature,
            source_type="AGENT_INFERENCE",
            confidence="HIGH",
            importance="MEDIUM"
        )
        return mem.model_dump(mode="json")

    async def supersede_memory(
        self,
        uid: str,
        old_memory_id: str,
        new_title: str,
        new_content: str
    ) -> Dict[str, Any]:
        """
        Agent Tool: Replaces an outdated memory with a new current memory.
        """
        mem = await self.memory_service.supersede_long_term_memory(
            uid=uid,
            old_memory_id=old_memory_id,
            new_title=new_title,
            new_content=new_content
        )
        return mem.model_dump(mode="json")
