from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
from backend.core.context_schemas import (
    PersonalContextGraph,
    ContextConflict,
    DecisionRecord,
    TaskContextPackage
)
from backend.services.store import FirestoreStore
from backend.services.roadmap_engine import RoadmapEngine
from backend.services.memory_engine import MemoryEngine
from backend.services.career_readiness_engine import CareerReadinessEngine
from backend.services.mastery_engine import MasteryEngine
from backend.providers.opportunity_provider import VerifiedOpenOpportunityProvider

class ContextGraphService:
    """
    Contextual Interpretation Layer for PATHMIND.
    Synthesizes Identity, Goals, Capabilities, Learning State, Career Readiness,
    Constraints, Memories, Opportunities, and Decision History without duplicating canonical models.
    """
    def __init__(
        self,
        store: Optional[FirestoreStore] = None,
        roadmap_engine: Optional[RoadmapEngine] = None,
        memory_engine: Optional[MemoryEngine] = None,
        readiness_engine: Optional[CareerReadinessEngine] = None,
        mastery_engine: Optional[MasteryEngine] = None
    ):
        self.store = store or FirestoreStore()
        self.roadmap_engine = roadmap_engine or RoadmapEngine()
        self.memory_engine = memory_engine or MemoryEngine()
        self.readiness_engine = readiness_engine or CareerReadinessEngine()
        self.mastery_engine = mastery_engine or MasteryEngine()
        self.opp_provider = VerifiedOpenOpportunityProvider()

    async def assemble_context_graph(self, person_id: str) -> PersonalContextGraph:
        # 1. Identity & Profile
        profile_raw = await self.store.get_profile(person_id) or {}
        identity_context = {
            "person_id": person_id,
            "education_level": profile_raw.get("education_level", "Undergraduate"),
            "background": profile_raw.get("background", "Computer Science & Engineering"),
            "location": profile_raw.get("location", "Global / Remote"),
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
            "primary_target_role": roadmap.target_outcome,
            "confidence": "HIGH",
            "status": "CURRENT",
            "timeline": "6 Months",
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
        career_context = {
            "target_role": roadmap.target_outcome,
            "readiness_tier": readiness.readiness_state,
            "overall_match_score": 75.0 if readiness.readiness_state != "FOUNDATIONAL" else 60.0,
            "critical_skill_gaps": [g.title for g in readiness.categorized_gaps if g.importance in ["HIGH", "CRITICAL"]],
            "verified_requirements_count": len(readiness.transferable_skills.already_have)
        }

        # 6. Constraints Context
        constraints = roadmap.constraints or {"weekly_hours": 10, "format_preference": "project-based"}
        constraint_context = {
            "weekly_hours": constraints.get("weekly_hours", 10),
            "format_preference": constraints.get("format_preference", "project-based"),
            "schedule_pacing": "Moderate",
            "status": "CURRENT"
        }

        # 7. Memory Context
        memories_raw = await self.store.get_memories(person_id)
        memory_context = memories_raw[:5] if memories_raw else []

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
        task_type: str = "NEXT_ACTION"
    ) -> TaskContextPackage:
        """
        Relevance filter: Returns only the necessary structured context package for a specific task.
        """
        graph = await self.assemble_context_graph(person_id)

        mem_summaries = [
            f"[{m.get('event_type', 'EVENT')}] {m.get('topic', '')}: {m.get('observation', '')}"
            for m in graph.memory_context[:3]
        ]
        opp_summaries = [
            f"{o.get('title')} at {o.get('organization')} (Deadline: {o.get('deadline', 'Open')})"
            for o in graph.opportunity_context[:2]
        ]

        return TaskContextPackage(
            task_type=task_type,
            relevant_goal=str(graph.goal_context.get("primary_target_role", "Applied AI Specialist")),
            relevant_stage_id=str(graph.learning_context.get("current_stage_id", "stage_01")),
            relevant_skills=list(graph.capability_context.get("developing_skills", [])),
            verified_evidence_summaries=list(graph.capability_context.get("demonstrated_skills", [])),
            active_constraints=dict(graph.constraint_context),
            relevant_memories=mem_summaries,
            relevant_opportunities=opp_summaries
        )
