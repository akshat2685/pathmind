from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
from backend.core.context_schemas import (
    NextActionRecommendation,
    CommandCenterOverview,
    DecisionRecord,
    PersonalContextGraph
)
from backend.services.context_graph_service import ContextGraphService
from backend.services.store import FirestoreStore

class DecisionIntelligenceService:
    """
    Decision Intelligence Engine for PATHMIND.
    Computes context-aware next actions, generates 6-question command center overviews,
    and maintains transparent decision history traces.
    """
    def __init__(
        self,
        store: Optional[FirestoreStore] = None,
        context_service: Optional[ContextGraphService] = None
    ):
        self.store = store or FirestoreStore()
        self.context_service = context_service or ContextGraphService(store=self.store)

    async def compute_next_action(self, person_id: str) -> NextActionRecommendation:
        graph = await self.context_service.assemble_context_graph(person_id)

        current_stage_title = graph.learning_context.get("current_stage_title", "Stage 01")
        current_stage_id = graph.learning_context.get("current_stage_id", "stage_01")
        current_stage_num = graph.learning_context.get("current_stage_number", 1)
        skills = graph.capability_context.get("developing_skills", [])
        demonstrated = graph.capability_context.get("demonstrated_skills", [])
        target_role = graph.goal_context.get("primary_target_role", "Applied AI Specialist")

        # 1. Check if there are regression risks
        if graph.capability_context.get("skills_at_risk"):
            risk_skill = graph.capability_context["skills_at_risk"][0]
            return NextActionRecommendation(
                action_title=f"Refresh and Validate {risk_skill}",
                action_type="REFRESH_SKILL",
                priority="NOW",
                target_skill=risk_skill,
                target_stage_id=current_stage_id,
                facts=[
                    f"Mastery risk flagged for '{risk_skill}' due to recent test or benchmark inconsistencies.",
                    f"Prerequisite competency in {risk_skill} is required before advancing deep into {current_stage_title}."
                ],
                interpretation=[
                    "Targeted remediation of this specific concept will prevent cumulative debt downstream."
                ],
                tradeoffs=[
                    f"Pauses forward progress on Stage 0{current_stage_num} for ~2 hours, but ensures long-term retention."
                ],
                recommendation_rationale=f"Reinforce '{risk_skill}' with a targeted debugging exercise before proceeding.",
                downstream_consequence="Restores full verified mastery badge and unlocks downstream stage validation."
            )

        # 2. Check if verified opportunities have upcoming deadlines
        if graph.opportunity_context and len(demonstrated) >= 2:
            top_opp = graph.opportunity_context[0]
            opp_title = top_opp.get("title", "Open Source Fellowship")
            opp_org = top_opp.get("organization", "Verified Partner")
            return NextActionRecommendation(
                action_title=f"Review & Apply: {opp_title} at {opp_org}",
                action_type="APPLY_OPPORTUNITY",
                priority="NEXT",
                target_opportunity_id=top_opp.get("opportunity_id"),
                facts=[
                    f"You have verified skills in {', '.join(demonstrated[:3])}.",
                    f"'{opp_title}' directly values your demonstrated background in machine systems."
                ],
                interpretation=[
                    "Applying to verified opportunities early builds real industry traction in parallel with roadmap progression."
                ],
                tradeoffs=[
                    "Requires 30 minutes to review application prompt and attach your verified evidence portfolio."
                ],
                recommendation_rationale=f"Submit your candidate profile to {opp_org} while matching criteria are fresh.",
                downstream_consequence="Enters candidate selection pool with direct evidence verification provenance."
            )

        # 3. Default: Complete active stage milestone proof
        return NextActionRecommendation(
            action_title=f"Submit Code Evidence for {current_stage_title}",
            action_type="COMPLETE_STAGE_EVIDENCE",
            priority="NOW",
            target_stage_id=current_stage_id,
            target_skill=skills[0] if skills else None,
            facts=[
                f"Currently working on Stage 0{current_stage_num}: {current_stage_title}.",
                f"Required skills to prove: {', '.join(skills)}.",
                f"Target career outcome: {target_role}."
            ],
            interpretation=[
                f"Completing this stage's code milestone satisfies {len(skills)} prerequisite requirements in your career readiness graph."
            ],
            tradeoffs=[
                "Requires implementing executable code with unit tests rather than merely reading notes."
            ],
            recommendation_rationale=f"Build and submit your {current_stage_title} script or repository to unlock downstream milestones.",
            downstream_consequence=f"Unlocks Stage 0{current_stage_num + 1} and advances career readiness toward {target_role}."
        )

    async def get_command_center_overview(self, person_id: str) -> CommandCenterOverview:
        graph = await self.context_service.assemble_context_graph(person_id)
        next_action = await self.compute_next_action(person_id)

        # 1. Where Am I?
        where_am_i = {
            "current_stage": graph.learning_context.get("current_stage_title", "Stage 01"),
            "stage_number": graph.learning_context.get("current_stage_number", 1),
            "progress_percent": graph.learning_context.get("progress_percent", 0.0),
            "completed_stages": graph.learning_context.get("completed_stages", 0),
            "total_stages": graph.learning_context.get("total_stages", 5),
            "verified_skills_count": graph.capability_context.get("total_verified_skills", 0)
        }

        # 2. Where Am I Going?
        where_am_i_going = {
            "target_role": graph.goal_context.get("primary_target_role", "Applied AI Specialist"),
            "readiness_tier": graph.career_context.get("readiness_tier", "DEVELOPING"),
            "match_score": graph.career_context.get("overall_match_score", 65.0),
            "target_timeline": graph.goal_context.get("timeline", "6 Months")
        }

        # 3. What Changed?
        recent_mem = graph.memory_context[0] if graph.memory_context else None
        what_changed = {
            "event_title": recent_mem.get("topic", "Roadmap Active") if recent_mem else "Roadmap Synthesized",
            "observation": recent_mem.get("observation", "Active personalized pathway ready for progression.") if recent_mem else "Personalized pathway synthesized with continuous adaptation.",
            "timestamp": recent_mem.get("timestamp", datetime.now(timezone.utc).isoformat()) if recent_mem else datetime.now(timezone.utc).isoformat()
        }

        # 4. What Is Blocking Me?
        blocker = None
        if graph.learning_context.get("current_blocker"):
            blocker = {
                "title": "Prerequisite Stage Locked",
                "description": f"Stage 0{graph.learning_context.get('current_stage_number')} requires verified code evidence before downstream stages unlock.",
                "missing_requirements": graph.capability_context.get("developing_skills", [])
            }

        return CommandCenterOverview(
            person_id=person_id,
            where_am_i=where_am_i,
            where_am_i_going=where_am_i_going,
            what_changed=what_changed,
            what_is_blocking_me=blocker,
            what_should_i_do_now=next_action,
            what_happens_after_that=next_action.downstream_consequence,
            recent_decisions=graph.recent_decisions[:5],
            active_conflicts=graph.active_conflicts
        )

    async def record_user_decision(
        self,
        person_id: str,
        decision_type: str,
        title: str,
        user_choice: str,
        alternatives: Optional[List[str]] = None,
        supporting_evidence_ids: Optional[List[str]] = None
    ) -> DecisionRecord:
        graph = await self.context_service.assemble_context_graph(person_id)

        context_summary = {
            "active_target_role": graph.goal_context.get("primary_target_role"),
            "current_stage": graph.learning_context.get("current_stage_title"),
            "verified_skills": graph.capability_context.get("demonstrated_skills", []),
            "weekly_hours": graph.constraint_context.get("weekly_hours", 10)
        }

        decision = DecisionRecord(
            person_id=person_id,
            decision_type=decision_type,
            title=title,
            user_choice=user_choice,
            alternatives_considered=alternatives or [],
            supporting_evidence_ids=supporting_evidence_ids or [],
            context_snapshot_summary=context_summary,
            outcome_state="PENDING"
        )

        await self.store.save_decision_record(person_id, decision.model_dump())
        return decision

    async def record_decision_outcome(
        self,
        person_id: str,
        decision_id: str,
        outcome_state: str,
        outcome_note: str
    ) -> bool:
        return await self.store.update_decision_outcome(
            person_id=person_id,
            decision_id=decision_id,
            outcome_state=outcome_state,
            outcome_note=outcome_note
        )
