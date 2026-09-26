from typing import Dict, Any, List, Optional, Any
from datetime import datetime, timezone
from backend.core.context_schemas import (
    PersonalContextGraph,
    ContextConflict,
    DecisionRecord,
    TaskContextPackage
)
from backend.services.pm_store import get_pm_store
from backend.services.roadmap_engine import RoadmapEngine
from backend.services.memory_engine import MemoryEngine
from backend.services.career_readiness_engine import CareerReadinessEngine
from backend.services.mastery_engine import MasteryEngine
from backend.providers.opportunity_provider import JobOpportunitiesProvider

from backend.services.proactive_memory_service import ProactiveMemoryService

class ContextGraphService:
    """
    Contextual Interpretation Layer for PATHMIND.
    Synthesizes Identity, Goals, Capabilities, Learning State, Career Readiness,
    Constraints, Memories, Opportunities, and Decision History without duplicating canonical models.
    """
    def __init__(
        self,
        store: Optional[Any] = None,
        roadmap_engine: Optional[RoadmapEngine] = None,
        memory_engine: Optional[MemoryEngine] = None,
        readiness_engine: Optional[CareerReadinessEngine] = None,
        mastery_engine: Optional[MasteryEngine] = None
    ):
        self.store = store or get_pm_store()
        self.roadmap_engine = roadmap_engine or RoadmapEngine()
        self.memory_engine = memory_engine or MemoryEngine()
        self.readiness_engine = readiness_engine or CareerReadinessEngine()
        self.mastery_engine = mastery_engine or MasteryEngine()
        self.opp_provider = JobOpportunitiesProvider()
        self.proactive_memory = ProactiveMemoryService(self.store)

    async def assemble_context_graph(self, person_id: str) -> PersonalContextGraph:
        # 1. Identity & Profile
        profile_raw = await self.store.get_profile(person_id) or {}
        identity_context = {
            "person_id": person_id,
            "education_level": profile_raw.get("education_level") or "UNKNOWN",
            "background": profile_raw.get("background") or "UNKNOWN",
            "location": profile_raw.get("location") or "UNKNOWN",
            "status": "CURRENT"
        }

        # 2. Roadmap & Learning State
        roadmap = await self.roadmap_engine.get_or_create_roadmap(person_id)
        flat_stages = self.roadmap_engine.get_all_stages_flat(roadmap)
        active_stage = next((s for s in flat_stages if s.stage_id == roadmap.current_stage_id), flat_stages[0] if flat_stages else None)
        
        learning_context = {
            "roadmap_id": roadmap.roadmap_id,
            "version": roadmap.version,
            "current_stage_id": roadmap.current_stage_id,
            "current_stage_title": active_stage.title if active_stage else "Stage 01",
            "current_stage_number": active_stage.stage_number if active_stage else 1,
            "completed_stages": roadmap.completed_stages,
            "total_stages": roadmap.total_stages,
            "progress_percent": round((roadmap.completed_stages / max(1, roadmap.total_stages)) * 100, 1),
            "current_blocker": active_stage.title if active_stage and active_stage.locked else None
        }

        # 3. Goal Context
        goal_context = {
            "primary_target_role": roadmap.target_outcome or "UNKNOWN",
            "confidence": "HIGH",
            "status": "CURRENT",
            "timeline": (roadmap.constraints or {}).get("timeline") or "NOT_SPECIFIED",
            "revision_reason": roadmap.revision_reason
        }

        # 4. Capability & Mastery Context
        profiles_raw = await self.store.get_skill_mastery_profiles(person_id)
        demonstrated = []
        at_risk = []
        for sk_name, prof in profiles_raw.items():
            if prof.get("is_regression_risk"):
                at_risk.append(sk_name)
            elif prof.get("mastery_state") in ["DEMONSTRATED_MASTERY", "TRANSFER", "APPLICATION"]:
                demonstrated.append(sk_name)

        capability_context = {
            "demonstrated_skills": demonstrated,
            "skills_at_risk": at_risk,
            "total_verified_skills": len(demonstrated),
            "developing_skills": active_stage.skills if active_stage else []
        }

        # 5. Career Readiness Context
        readiness = await self.readiness_engine.generate_career_readiness_report(person_id, roadmap.target_outcome)
        total_reqs = len(readiness.transferable_skills.already_have) + len(readiness.categorized_gaps)
        calc_match = round((len(readiness.transferable_skills.already_have) / max(1, total_reqs)) * 100, 1) if total_reqs > 0 else 0.0
        career_context = {
            "target_role": roadmap.target_outcome,
            "readiness_tier": readiness.readiness_state,
            "overall_match_score": calc_match,
            "alignment_level": "STRONG" if calc_match >= 70 else ("PROMISING" if calc_match >= 30 else "DEVELOPING"),
            "critical_skill_gaps": [g.title for g in readiness.categorized_gaps if g.importance in ["HIGH", "CRITICAL"]],
            "verified_requirements_count": len(readiness.transferable_skills.already_have)
        }

        # 6. Constraints Context
        constraints = roadmap.constraints or {}
        constraint_context = {
            "weekly_hours": constraints.get("weekly_hours", 10),
            "format_preference": constraints.get("format_preference") or "NOT_SPECIFIED",
            "schedule_pacing": "Moderate",
            "status": "CURRENT"
        }

        # 7. Memory Context (Proactive & Task-Conditioned)
        proactive_mem = await self.proactive_memory.get_proactive_memory_context(
            person_id=person_id,
            task_type="GENERAL_CONTEXT",
            current_goal=roadmap.target_outcome
        )
        memory_context = [m.model_dump(mode="json") for m in proactive_mem.retrieved_memories]

        # 8. Verified Opportunities Context
        opp_records = await self.opp_provider.fetch_opportunities(
            role_filter=roadmap.target_outcome
        )
        opportunity_context = [o.model_dump() for o in opp_records[:3]]

        # 9. Recent Decisions & Conflicts
        recent_decisions = [DecisionRecord(**d) for d in await self.store.get_decision_records(person_id)]
        active_conflicts = [ContextConflict(**c) for c in await self.store.get_context_conflicts(person_id)]

        return PersonalContextGraph(
            person_id=person_id,
            identity_context=identity_context,
            goal_context=goal_context,
            capability_context=capability_context,
            learning_context=learning_context,
            career_context=career_context,
            constraint_context=constraint_context,
            memory_context=memory_context,
            opportunity_context=opportunity_context,
            recent_decisions=recent_decisions,
            active_conflicts=active_conflicts
        )

    async def extract_task_context_package(
        self,
        person_id: str,
        task_type: str = "NEXT_ACTION",
        current_concept: Optional[str] = None,
        current_goal: Optional[str] = None
    ) -> TaskContextPackage:
        """
        Relevance filter: Returns only the necessary structured context package for a specific task.
        Uses ProactiveMemoryService for task-specific, non-flooding contextual retrieval.
        """
        graph = await self.assemble_context_graph(person_id)

        target_role = current_goal or str(graph.goal_context.get("primary_target_role") or "Career Goal")
        current_stage = str(graph.learning_context.get("current_stage_id") or "stage_01")
        concept = current_concept or str(graph.learning_context.get("current_stage_title") or "")

        proactive_mem = await self.proactive_memory.get_proactive_memory_context(
            person_id=person_id,
            task_type=task_type,
            current_goal=target_role,
            current_stage=current_stage,
            current_concept=concept
        )

        mem_summaries = [
            f"[{m.nature}] {m.title}: {m.content or m.summary}"
            for m in proactive_mem.retrieved_memories
        ]
        if not mem_summaries and proactive_mem.proactive_summary:
            mem_summaries.append(proactive_mem.proactive_summary)

        opp_summaries = [
            f"{o.get('title')} at {o.get('organization')} (Deadline: {o.get('deadline', 'Open')})"
            for o in graph.opportunity_context[:2]
        ]

        return TaskContextPackage(
            task_type=task_type,
            relevant_goal=target_role,
            relevant_stage_id=current_stage,
            relevant_skills=list(graph.capability_context.get("developing_skills", [])),
            verified_evidence_summaries=list(graph.capability_context.get("demonstrated_skills", [])),
            active_constraints=dict(graph.constraint_context),
            relevant_memories=mem_summaries,
            relevant_opportunities=opp_summaries
        )
