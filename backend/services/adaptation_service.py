from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
from backend.core.adaptation_schemas import (
    StateChangeEvent,
    ImpactAnalysis,
    ProposedAdaptation,
    UserAdaptationDecision,
    AdaptationAuditRecord,
    ContinuousIntelligenceState,
    PauseResumeAnalysis,
    ConflictDetectionResult
)
from backend.services.state_change_service import StateChangeService
from backend.services.impact_analysis_service import ImpactAnalysisService
from backend.services.adaptive_planning_agent import AdaptivePlanningAgent
from backend.services.roadmap_engine import RoadmapEngine
from backend.services.store import FirestoreStore
from backend.services.memory_engine import MemoryEngine
from backend.services.personal_agent_engine import PersonalAgentEngine

class AdaptationService:
    def __init__(
        self,
        store: Optional[FirestoreStore] = None,
        state_change_service: Optional[StateChangeService] = None,
        impact_service: Optional[ImpactAnalysisService] = None,
        agent: Optional[AdaptivePlanningAgent] = None,
        roadmap_engine: Optional[RoadmapEngine] = None,
        memory_engine: Optional[MemoryEngine] = None,
        personal_agent: Optional[PersonalAgentEngine] = None
    ):
        self.store = store or FirestoreStore()
        self.state_change_service = state_change_service or StateChangeService(self.store)
        self.impact_service = impact_service or ImpactAnalysisService()
        self.agent = agent or AdaptivePlanningAgent()
        self.roadmap_engine = roadmap_engine or RoadmapEngine()
        self.memory_engine = memory_engine or MemoryEngine()
        self.personal_agent = personal_agent or PersonalAgentEngine()

    async def get_continuous_intelligence_state(self, person_id: str) -> ContinuousIntelligenceState:
        roadmap = await self.roadmap_engine.get_or_create_roadmap(person_id)
        current_goal = await self.store.get_career_goal(person_id)
        target_role = current_goal.get("target_role", "Applied Machine Learning Systems Engineer") if current_goal else "Applied Machine Learning Systems Engineer"
        
        pending_raw = await self.store.get_pending_adaptations(person_id)
        pending = [ProposedAdaptation(**p) for p in pending_raw]
        
        audits_raw = await self.store.get_adaptation_audits(person_id)
        audits = [AdaptationAuditRecord(**a) for a in audits_raw]

        pause_status = await self.state_change_service.analyze_pause_and_resume(person_id)
        conflict_status = await self.state_change_service.detect_evidence_conflict(person_id, "Python")

        plan_stability = "STABLE"
        if pending:
            plan_stability = "PENDING_REVIEW"

        return ContinuousIntelligenceState(
            person_id=person_id,
            active_target_role=target_role,
            current_roadmap_version=roadmap.version,
            plan_stability_status=plan_stability,
            pending_adaptations=pending,
            recent_audits=audits[:10],
            pause_status=pause_status,
            conflict_status=conflict_status
        )

    async def handle_goal_change(
        self,
        person_id: str,
        new_target_role: str,
        target_industry: Optional[str] = None,
        geography: Optional[str] = None,
        target_timeline: Optional[str] = None
    ) -> ProposedAdaptation:
        # 1. Detect change event
        event = await self.state_change_service.detect_goal_change(
            person_id=person_id,
            new_target_role=new_target_role,
            target_industry=target_industry,
            geography=geography,
            target_timeline=target_timeline
        )

        # 2. Analyze impact
        current_roadmap = await self.roadmap_engine.get_or_create_roadmap(person_id)
        roadmap_dict = current_roadmap.model_dump()
        impact = self.impact_service.analyze_change(event, current_roadmap=roadmap_dict)

        # 3. Agent formulates adaptation
        proposal = await self.agent.formulate_adaptation(
            person_id=person_id,
            current_roadmap=roadmap_dict,
            event=event,
            impact=impact
        )

        # 4. Save proposal to persistence
        await self.store.save_proposed_adaptation(person_id, proposal.model_dump())

        # 5. Record audit entry
        audit = AdaptationAuditRecord(
            person_id=person_id,
            event_type="GOAL_CHANGE_DETECTED",
            detected_change=event.title,
            previous_version=proposal.previous_roadmap_version,
            resulting_version=proposal.proposed_roadmap_version,
            impact_level=impact.impact_level,
            approval_state="PENDING_APPROVAL" if impact.requires_user_approval else "AUTO_APPLIED",
            rationale=proposal.rationale,
            actor="USER"
        )
        await self.store.save_adaptation_audit(person_id, audit.model_dump())

        # If auto-apply, execute immediately
        if not impact.requires_user_approval:
            await self._apply_adaptation_internal(person_id, proposal)

        return proposal

    async def handle_constraint_change(
        self,
        person_id: str,
        weekly_hours: int,
        preferred_format: Optional[str] = None
    ) -> ProposedAdaptation:
        agent_model = await self.personal_agent.get_or_create_agent_model(person_id)
        prev_hours = agent_model.learning_preferences.get("weekly_hours", 10)

        event = await self.state_change_service.detect_constraint_change(
            person_id=person_id,
            weekly_hours=weekly_hours,
            previous_hours=prev_hours,
            preferred_format=preferred_format
        )

        current_roadmap = await self.roadmap_engine.get_or_create_roadmap(person_id)
        roadmap_dict = current_roadmap.model_dump()
        impact = self.impact_service.analyze_change(event, current_roadmap=roadmap_dict)

        proposal = await self.agent.formulate_adaptation(
            person_id=person_id,
            current_roadmap=roadmap_dict,
            event=event,
            impact=impact
        )

        await self.store.save_proposed_adaptation(person_id, proposal.model_dump())

        audit = AdaptationAuditRecord(
            person_id=person_id,
            event_type="CONSTRAINT_ADAPTED",
            detected_change=event.title,
            previous_version=proposal.previous_roadmap_version,
            resulting_version=proposal.proposed_roadmap_version,
            impact_level=impact.impact_level,
            approval_state=proposal.status,
            rationale=proposal.rationale,
            actor="USER"
        )
        await self.store.save_adaptation_audit(person_id, audit.model_dump())

        # Apply constraint changes to personal agent model
        agent_model.learning_preferences["weekly_hours"] = weekly_hours
        if preferred_format:
            agent_model.learning_preferences["preferred_format"] = preferred_format
        await self.personal_agent.update_agent_model(person_id, agent_model)

        return proposal

    async def handle_opportunity_event(
        self,
        person_id: str,
        opportunity_id: str,
        opportunity_title: str,
        organization: str,
        required_milestones: List[str]
    ) -> ProposedAdaptation:
        event = await self.state_change_service.detect_opportunity_change(
            person_id=person_id,
            opportunity_id=opportunity_id,
            opportunity_title=opportunity_title,
            organization=organization,
            required_milestones=required_milestones
        )

        current_roadmap = await self.roadmap_engine.get_or_create_roadmap(person_id)
        roadmap_dict = current_roadmap.model_dump()
        impact = self.impact_service.analyze_change(event, current_roadmap=roadmap_dict)

        proposal = await self.agent.formulate_adaptation(
            person_id=person_id,
            current_roadmap=roadmap_dict,
            event=event,
            impact=impact
        )

        await self.store.save_proposed_adaptation(person_id, proposal.model_dump())

        audit = AdaptationAuditRecord(
            person_id=person_id,
            event_type="OPPORTUNITY_ADAPTATION_PROPOSED",
            detected_change=event.title,
            previous_version=proposal.previous_roadmap_version,
            resulting_version=proposal.proposed_roadmap_version,
            impact_level=impact.impact_level,
            approval_state=proposal.status,
            rationale=proposal.rationale,
            actor="SYSTEM_AUTO"
        )
        await self.store.save_adaptation_audit(person_id, audit.model_dump())

        return proposal

    async def decide_adaptation(
        self,
        person_id: str,
        decision: UserAdaptationDecision
    ) -> Dict[str, Any]:
        proposal_raw = await self.store.get_proposed_adaptation(person_id, decision.adaptation_id)
        if not proposal_raw:
            raise ValueError(f"Adaptation proposal {decision.adaptation_id} not found.")

        proposal = ProposedAdaptation(**proposal_raw)

        if decision.action == "APPROVE":
            proposal.status = "APPROVED"
            await self._apply_adaptation_internal(person_id, proposal)
            await self.store.update_adaptation_status(person_id, decision.adaptation_id, "APPROVED")

            # Audit record
            audit = AdaptationAuditRecord(
                person_id=person_id,
                event_type="ADAPTATION_APPROVED",
                detected_change=proposal.change_event.title,
                previous_version=proposal.previous_roadmap_version,
                resulting_version=proposal.proposed_roadmap_version,
                impact_level=proposal.impact_analysis.impact_level,
                approval_state="APPROVED",
                rationale=decision.user_feedback or proposal.rationale,
                actor="USER"
            )
            await self.store.save_adaptation_audit(person_id, audit.model_dump())

            # Memory event
            await self.memory_engine.extract_and_store_memory_from_event(
                person_id=person_id,
                event_payload={
                    "topic": proposal.change_event.trigger_data.get("new_target_role", "Target Role"),
                    "observation": proposal.change_summary,
                    "intervention": decision.user_feedback or proposal.rationale,
                    "event_type": "GOAL_CHANGED"
                }
            )

            return {
                "status": "APPROVED",
                "message": f"Adaptation successfully applied. Active roadmap updated to Version {proposal.proposed_roadmap_version}.",
                "active_version": proposal.proposed_roadmap_version
            }

        elif decision.action == "REJECT":
            proposal.status = "REJECTED"
            await self.store.update_adaptation_status(person_id, decision.adaptation_id, "REJECTED")

            audit = AdaptationAuditRecord(
                person_id=person_id,
                event_type="ADAPTATION_REJECTED",
                detected_change=proposal.change_event.title,
                previous_version=proposal.previous_roadmap_version,
                resulting_version=proposal.previous_roadmap_version,
                impact_level=proposal.impact_analysis.impact_level,
                approval_state="REJECTED",
                rationale=decision.user_feedback or "User chose to preserve existing roadmap plan.",
                actor="USER"
            )
            await self.store.save_adaptation_audit(person_id, audit.model_dump())

            return {
                "status": "REJECTED",
                "message": "Proposed adaptation dismissed. Current active roadmap version preserved.",
                "active_version": proposal.previous_roadmap_version
            }

        return {"status": "UNKNOWN_ACTION"}

    async def _apply_adaptation_internal(self, person_id: str, proposal: ProposedAdaptation):
        # Update career goal if it was a goal change
        if proposal.change_event.change_type == "GOAL_CHANGE":
            new_role = proposal.change_event.trigger_data.get("new_target_role")
            if new_role:
                await self.store.save_career_goal(person_id, {
                    "target_role": new_role,
                    "target_industry": proposal.change_event.trigger_data.get("target_industry", "Applied AI"),
                    "geography": proposal.change_event.trigger_data.get("geography", "Global / India"),
                    "target_timeline": proposal.change_event.trigger_data.get("target_timeline", "6–9 Months"),
                    "priority": "PRIMARY",
                    "version": proposal.proposed_roadmap_version
                })

        # Update roadmap version
        current_roadmap = await self.roadmap_engine.get_or_create_roadmap(person_id)
        current_roadmap.version = proposal.proposed_roadmap_version
        current_roadmap.revision_reason = proposal.change_summary
        await self.store.save_roadmap(person_id, current_roadmap.model_dump())
