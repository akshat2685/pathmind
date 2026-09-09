from typing import Dict, Any, List, Optional
from datetime import datetime, timezone, timedelta
from backend.core.event_schemas import (
    EventRecord,
    Intervention,
    InterventionOutcome,
    NotificationPreferences
)
from backend.services.event_bus_service import EventBusService
from backend.services.context_graph_service import ContextGraphService
from backend.services.store import FirestoreStore

class ProactiveInterventionEngine:
    """
    Proactive Intelligence & Personal Intervention Engine for PATHMIND.
    Detects meaningful changes across Evidence, Opportunities, Milestones, and Inactivity,
    generating high-relevance, non-intrusive interventions with clear 4-part explanations.
    """
    def __init__(
        self,
        store: Optional[FirestoreStore] = None,
        event_bus: Optional[EventBusService] = None,
        context_service: Optional[ContextGraphService] = None
    ):
        self.store = store or FirestoreStore()
        self.event_bus = event_bus or EventBusService(store=self.store)
        self.context_service = context_service or ContextGraphService(store=self.store)

    async def scan_and_generate_interventions(self, person_id: str) -> List[Intervention]:
        graph = await self.context_service.assemble_context_graph(person_id)
        prefs_raw = await self.store.get_notification_preferences(person_id) or {}
        prefs = NotificationPreferences(**prefs_raw) if prefs_raw else NotificationPreferences(person_id=person_id)

        generated = []
        now_iso = datetime.now(timezone.utc).isoformat()

        # 1. Rule: Check Repeated Evidence Failures on Active Stage
        active_stage_id = graph.learning_context.get("current_stage_id")
        eval_attempts = await self.store.get_evaluation_attempts(person_id, stage_id=active_stage_id)
        failed_attempts = [a for a in eval_attempts if a.get("status") == "REINFORCE"]

        if len(failed_attempts) >= 2 and prefs.enable_reinforcement_alerts:
            # Publish event
            evt = await self.event_bus.publish_event(
                person_id=person_id,
                event_type="EVIDENCE_FAILED",
                entity_type="STAGE",
                entity_id=active_stage_id,
                importance="IMPORTANT",
                metadata={"consecutive_failures": len(failed_attempts)}
            )
            if evt.processed_state != "DEDUPLICATED":
                intv = Intervention(
                    person_id=person_id,
                    event_id=evt.event_id,
                    type="REVIEW_REINFORCEMENT",
                    priority="HIGH",
                    title="Targeted Skill Reinforcement Recommended",
                    what_happened=f"Observed {len(failed_attempts)} consecutive preliminary submissions for {graph.learning_context.get('current_stage_title')}.",
                    why_it_matters="Boundary tests and error-handling assertions need strengthening before advancing downstream.",
                    what_should_i_do="Review the targeted debugging guidance and write 2 unit tests with pytest.",
                    what_happens_if_ignored="Cumulative test gaps could cause friction when working on PyTorch neural network modules later.",
                    action_url="/journey",
                    related_entity_type="STAGE",
                    related_entity_id=active_stage_id
                )
                await self.store.save_intervention(person_id, intv.model_dump())
                generated.append(intv)

        # 2. Rule: Check Approaching Opportunity Deadlines (Urgent)
        if graph.opportunity_context and prefs.enable_opportunity_alerts:
            top_opp = graph.opportunity_context[0]
            deadline_str = top_opp.get("deadline", "")
            if deadline_str and "202" in deadline_str:
                evt = await self.event_bus.publish_event(
                    person_id=person_id,
                    event_type="OPPORTUNITY_DEADLINE_APPROACHING",
                    entity_type="OPPORTUNITY",
                    entity_id=top_opp.get("opportunity_id"),
                    importance="URGENT",
                    metadata={"deadline": deadline_str}
                )
                if evt.processed_state != "DEDUPLICATED":
                    intv = Intervention(
                        person_id=person_id,
                        event_id=evt.event_id,
                        type="APPLY_OPPORTUNITY",
                        priority="CRITICAL",
                        title=f"Application Closing Soon: {top_opp.get('title')}",
                        what_happened=f"Verified opportunity at {top_opp.get('organization')} closes on {deadline_str}.",
                        why_it_matters=f"Matches your verified background in {', '.join(graph.capability_context.get('demonstrated_skills', [])[:2]) or 'Applied AI'}.",
                        what_should_i_do="Review the verified application prompt and submit your proof portfolio.",
                        what_happens_if_ignored="The current cohort application window will close until the next seasonal cycle.",
                        action_url="/readiness",
                        related_entity_type="OPPORTUNITY",
                        related_entity_id=top_opp.get("opportunity_id")
                    )
                    await self.store.save_intervention(person_id, intv.model_dump())
                    generated.append(intv)

        # 3. Rule: Check Mastery Breakthrough (Positive Intelligence)
        if graph.capability_context.get("total_verified_skills", 0) > 0 and prefs.enable_mastery_alerts:
            skills_count = graph.capability_context["total_verified_skills"]
            evt = await self.event_bus.publish_event(
                person_id=person_id,
                event_type="MASTERY_CHANGED",
                entity_type="SKILLS",
                entity_id=f"skills_{skills_count}",
                importance="RELEVANT",
                metadata={"verified_skills": skills_count}
            )
            if evt.processed_state != "DEDUPLICATED":
                intv = Intervention(
                    person_id=person_id,
                    event_id=evt.event_id,
                    type="CELEBRATE_MASTERY",
                    priority="NORMAL",
                    title="Milestone Breakthrough: Verified Capabilities Proven",
                    what_happened=f"You have verified mastery across {skills_count} core competencies in {graph.goal_context.get('primary_target_role')}.",
                    why_it_matters="Demonstrated proof has updated your career readiness graph and unlocked downstream milestones.",
                    what_should_i_do="Continue directly with the next active stage or inspect your updated career readiness report.",
                    what_happens_if_ignored="Your progress remains securely recorded in your permanent longitudinal memory.",
                    action_url="/evidence",
                    related_entity_type="EVIDENCE",
                    related_entity_id=None
                )
                await self.store.save_intervention(person_id, intv.model_dump())
                generated.append(intv)

        return generated

    async def get_active_interventions(self, person_id: str) -> List[Intervention]:
        await self.scan_and_generate_interventions(person_id)
        raw = await self.store.get_interventions(person_id, status="PENDING")
        return [Intervention(**i) for i in raw]

    async def act_on_intervention(
        self,
        person_id: str,
        intervention_id: str,
        feedback_note: Optional[str] = None
    ) -> bool:
        success = await self.store.update_intervention_status(person_id, intervention_id, "ACTED_ON")
        if success:
            outcome = InterventionOutcome(
                intervention_id=intervention_id,
                person_id=person_id,
                outcome="ACTED",
                feedback_note=feedback_note
            )
            # Log memory signal for Personal Agent Loop
            await self.context_service.memory_engine.extract_and_store_memory_from_event(
                person_id=person_id,
                event_payload={
                    "topic": "Proactive Intervention Acted On",
                    "observation": f"Learner acted on intervention {intervention_id}.",
                    "intervention": feedback_note or "Action completed.",
                    "event_type": "INTERVENTION_ACTED"
                }
            )
        return success

    async def dismiss_intervention(
        self,
        person_id: str,
        intervention_id: str
    ) -> bool:
        return await self.store.update_intervention_status(person_id, intervention_id, "DISMISSED")
