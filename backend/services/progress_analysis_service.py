from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
from backend.core.longitudinal_schemas import (
    CapabilityEvolutionRecord,
    LearningStrategyProfile,
    RecurringMisconception,
    TurningPoint,
    ProgressInsight,
    LongitudinalLearnerState
)
from backend.services.context_graph_service import ContextGraphService
from backend.services.store import FirestoreStore

class ProgressAnalysisService:
    """
    Deterministic Longitudinal Progress Analysis Service for PATHMIND.
    Reconstructs capability evolution trajectories, detects recurring misconceptions,
    evaluates strategy effectiveness, and identifies milestone turning points.
    """
    def __init__(
        self,
        store: Optional[FirestoreStore] = None,
        context_service: Optional[ContextGraphService] = None
    ):
        self.store = store or FirestoreStore()
        self.context_service = context_service or ContextGraphService(store=self.store)

    async def reconstruct_capability_evolution(self, person_id: str) -> List[CapabilityEvolutionRecord]:
        profiles_raw = await self.store.get_skill_mastery_profiles(person_id)
        all_evidence = await self.store.get_all_person_evidence(person_id)

        records = []
        for sk_name, prof in profiles_raw.items():
            matching_ev = [
                e for e in all_evidence
                if any(sk.lower() in sk_name.lower() for sk in e.get("associated_skills", []))
            ]
            ev_ids = [e.get("evidence_id") for e in matching_ev]
            is_risk = prof.get("is_regression_risk", False)
            mastery_state = prof.get("mastery_state", "EXPOSED")

            # Determine Progress Classification
            classification = "INSUFFICIENT_DATA"
            regressions = []
            recoveries = []

            if is_risk:
                classification = "REGRESSING"
                regressions.append(prof.get("regression_reason", "Performance dip during practical benchmark."))
            elif len(matching_ev) >= 2:
                classification = "IMPROVING"
                recoveries.append("Demonstrated multiple verified code artifacts with unit test coverage.")
            elif len(matching_ev) == 1:
                classification = "STABLE"

            record = CapabilityEvolutionRecord(
                skill_name=sk_name,
                first_demonstrated_at=matching_ev[0].get("created_at") if matching_ev else None,
                latest_evaluated_at=prof.get("last_verified_at"),
                current_mastery_state="MASTERY_AT_RISK" if is_risk else mastery_state,
                mastery_trajectory=[
                    {"state": "EXPOSED", "timestamp": "Initial Enrollment"},
                    {"state": mastery_state, "timestamp": prof.get("last_verified_at", "Current")}
                ],
                evidence_ids=ev_ids,
                evidence_count=len(matching_ev),
                progress_classification=classification,
                regression_events=regressions,
                recovery_events=recoveries,
                transfer_domains=["Applied AI Software Engineering"] if mastery_state == "TRANSFER" else []
            )
            records.append(record)

        return records

    async def detect_recurring_misconceptions(self, person_id: str) -> List[RecurringMisconception]:
        eval_attempts = await self.store.get_evaluation_attempts(person_id)
        failed_attempts = [a for a in eval_attempts if a.get("status") == "REINFORCE"]

        # Group by stage / concept
        counts: Dict[str, List[str]] = {}
        for a in failed_attempts:
            stg = a.get("stage_id", "General Concept")
            counts.setdefault(stg, []).append(a.get("attempt_id", "att"))

        detected = []
        for concept, att_ids in counts.items():
            if len(att_ids) >= 2:
                misc = RecurringMisconception(
                    person_id=person_id,
                    concept_area=concept,
                    description=f"Encountered repeated reinforcement feedback ({len(att_ids)} occurrences) during boundary testing.",
                    occurrence_count=len(att_ids),
                    trigger_event_ids=att_ids,
                    remediation_strategy="Practice targeted unit testing with parameterized test suites and edge case assertions.",
                    status="ACTIVE"
                )
                await self.store.save_recurring_misconception(person_id, misc.model_dump())
                detected.append(misc)

        return detected

    async def evaluate_strategy_profiles(self, person_id: str) -> List[LearningStrategyProfile]:
        eval_attempts = await self.store.get_evaluation_attempts(person_id)
        project_evals = [a for a in eval_attempts if a.get("status") == "PASS"]

        proj_strat = LearningStrategyProfile(
            person_id=person_id,
            strategy_dimension="PROJECT_BASED",
            observed_attempts_count=len(eval_attempts),
            successful_evaluations=len(project_evals),
            effectiveness_status="SUPPORTED" if len(project_evals) >= 1 else "EMERGING",
            supporting_event_ids=[a.get("attempt_id", "att") for a in project_evals]
        )
        await self.store.save_learning_strategy_profile(person_id, proj_strat.model_dump())

        theory_strat = LearningStrategyProfile(
            person_id=person_id,
            strategy_dimension="THEORETICAL_READING",
            observed_attempts_count=max(0, len(eval_attempts) - len(project_evals)),
            successful_evaluations=0,
            effectiveness_status="WEAKLY_SUPPORTED"
        )
        await self.store.save_learning_strategy_profile(person_id, theory_strat.model_dump())

        return [proj_strat, theory_strat]

    async def detect_turning_points(self, person_id: str) -> List[TurningPoint]:
        existing = await self.store.get_turning_points(person_id)
        if existing:
            return [TurningPoint(**tp) for tp in existing]

        # Scan for major milestones
        turning_points = []
        graph = await self.context_service.assemble_context_graph(person_id)

        # 1. Goal Orientation Milestone
        tp1 = TurningPoint(
            person_id=person_id,
            event_type="GOAL_TRANSITION",
            title="Established Target Direction",
            what_happened=f"Committed to {graph.goal_context.get('primary_target_role')} specialization.",
            why_significant="Grounded learning path in official ESCO/NCO occupational requirement standards.",
            what_changed_afterward="Generated 6-stage progressive mastery roadmap with prerequisite locking."
        )
        await self.store.save_turning_point(person_id, tp1.model_dump())
        turning_points.append(tp1)

        # 2. First Evidence Demonstration
        if graph.capability_context.get("total_verified_skills", 0) > 0:
            tp2 = TurningPoint(
                person_id=person_id,
                event_type="CAPABILITY_BREAKTHROUGH",
                title="First Verified Evidence Demonstration",
                what_happened=f"Demonstrated verified proof across {graph.capability_context.get('total_verified_skills')} core competencies.",
                why_significant="Transformed theoretical exposure into verifiable GitHub repository proof.",
                what_changed_afterward="Unlocked Stage 02 and updated career readiness match score."
            )
            await self.store.save_turning_point(person_id, tp2.model_dump())
            turning_points.append(tp2)

        return turning_points

    async def assemble_longitudinal_state(self, person_id: str) -> LongitudinalLearnerState:
        graph = await self.context_service.assemble_context_graph(person_id)
        caps = await self.reconstruct_capability_evolution(person_id)
        miscs = await self.detect_recurring_misconceptions(person_id)
        strats = await self.evaluate_strategy_profiles(person_id)
        tps = await self.detect_turning_points(person_id)
        decisions = await self.store.get_decision_records(person_id)

        # Build Then -> Transition -> Now -> Next
        current_stage = graph.learning_context.get("current_stage_title", "Stage 01")
        then_transition_now_next = {
            "then": {
                "role_focus": "Curiosity & Initial Exploration",
                "verified_skills_count": 0,
                "summary": "Exploring foundations with general curiosity."
            },
            "transition": {
                "turning_point": tps[0].title if tps else "Established Target Direction",
                "trigger_event": "Grounded roadmap in ESCO occupational standards",
                "adaptation_count": graph.learning_context.get("version", 1) - 1
            },
            "now": {
                "active_target_role": graph.goal_context.get("primary_target_role"),
                "current_stage": current_stage,
                "completed_stages": graph.learning_context.get("completed_stages", 0),
                "verified_skills_count": graph.capability_context.get("total_verified_skills", 0),
                "readiness_tier": graph.career_context.get("readiness_tier", "DEVELOPING")
            },
            "next": {
                "next_milestone": f"Complete {current_stage} verified project repository",
                "target_horizon": graph.goal_context.get("timeline", "6 Months"),
                "upcoming_opportunity": graph.opportunity_context[0].get("title") if graph.opportunity_context else "Open Source Opportunity Match"
            }
        }

        return LongitudinalLearnerState(
            person_id=person_id,
            current_state_summary=then_transition_now_next["now"],
            capability_history=caps,
            goal_history=[graph.goal_context],
            roadmap_evolution=[graph.learning_context],
            decision_history=decisions[:5],
            strategy_profiles=strats,
            recurring_misconceptions=miscs,
            turning_points=tps,
            historical_then_transition_now_next=then_transition_now_next
        )
