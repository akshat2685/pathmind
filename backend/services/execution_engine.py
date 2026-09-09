from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timezone, timedelta

from backend.core.execution_schemas import (
    CanonicalAction,
    ActionBlocker,
    RescheduleEvent,
    DailyExecutionPlan,
    AccountabilityIntervention,
    OpportunityApplicationTracker,
    CompleteActionRequest,
    CreateActionRequest
)
from backend.services.execution_intelligence_agent import ExecutionIntelligenceAgent
from backend.services.store import FirestoreStore
from backend.services.roadmap_engine import RoadmapEngine
from backend.services.memory_engine import MemoryEngine

class ExecutionEngine:
    """
    Core Execution, Action Tracking & Accountability Engine for PATHMIND.
    Translates roadmap milestones and career goals into executable action objects,
    enforces dependency chains, manages authentic action lifecycles, and maintains
    non-judgmental accountability without fake metrics.
    """
    def __init__(
        self,
        store: Optional[FirestoreStore] = None,
        agent: Optional[ExecutionIntelligenceAgent] = None,
        roadmap_engine: Optional[RoadmapEngine] = None,
        memory_engine: Optional[MemoryEngine] = None
    ):
        self.store = store or FirestoreStore()
        self.agent = agent or ExecutionIntelligenceAgent()
        self.roadmap_engine = roadmap_engine or RoadmapEngine()
        self.roadmap_engine.store = self.store
        self.memory_engine = memory_engine or MemoryEngine()
        self.memory_engine.store = self.store

    async def decompose_stage_to_actions(
        self,
        person_id: str,
        stage_id: str,
        stage_title: str,
        skills: List[str],
        goal_title: Optional[str] = None
    ) -> List[CanonicalAction]:
        existing = await self.store.get_person_actions(person_id, stage_id=stage_id)
        if existing:
            return [CanonicalAction(**a) for a in existing]

        primary_skill = skills[0] if skills else "Core Engineering"
        now = datetime.now(timezone.utc)

        # Action 1: Theory & Canonical Architecture Study
        act1 = CanonicalAction(
            person_id=person_id,
            title=f"Study Conceptual Architecture: {stage_title}",
            description=f"Watch verified lecture and inspect canonical reference implementations of {primary_skill}.",
            action_type="LEARNING",
            stage_id=stage_id,
            stage_title=stage_title,
            goal_title=goal_title or "Target Career Outcome",
            capability_ids=skills,
            evidence_requirement_ids=["WRITTEN_CONCEPTUAL_SUMMARY"],
            priority="NOW",
            status="READY",
            dependencies=[],
            verification_requirement="SIMPLE_CONFIRMATION",
            due_at=(now + timedelta(days=2)).isoformat(),
            source="ROADMAP_DECOMPOSITION"
        )

        # Action 2: Hands-on Implementation
        act2 = CanonicalAction(
            person_id=person_id,
            title=f"Implement Hands-on Module: {primary_skill}",
            description=f"Build and structure clean, modular implementation code using official documentation.",
            action_type="PRACTICE",
            stage_id=stage_id,
            stage_title=stage_title,
            goal_title=goal_title or "Target Career Outcome",
            capability_ids=skills,
            evidence_requirement_ids=["SOURCE_CODE_IMPLEMENTATION"],
            priority="NEXT",
            status="READY",
            dependencies=[act1.action_id],
            verification_requirement="EVIDENCE_SUBMISSION",
            due_at=(now + timedelta(days=5)).isoformat(),
            source="ROADMAP_DECOMPOSITION"
        )

        # Action 3: Empirical Unit Test Suite & Edge Case Verification
        act3 = CanonicalAction(
            person_id=person_id,
            title=f"Write Automated Assertions & Test Suite for {primary_skill}",
            description="Construct unit test assertions (pytest) covering happy path and critical edge cases.",
            action_type="EVIDENCE",
            stage_id=stage_id,
            stage_title=stage_title,
            goal_title=goal_title or "Target Career Outcome",
            capability_ids=skills,
            evidence_requirement_ids=["AUTOMATED_TEST_SUITE_EXECUTION"],
            priority="LATER",
            status="READY",
            dependencies=[act2.action_id],
            verification_requirement="MASTERY_EVIDENCE",
            due_at=(now + timedelta(days=7)).isoformat(),
            source="ROADMAP_DECOMPOSITION"
        )

        actions = [act1, act2, act3]
        for a in actions:
            await self.store.save_action(person_id, a.model_dump())

        return actions

    async def get_daily_execution_plan(self, person_id: str) -> DailyExecutionPlan:
        # 1. Check if user is currently paused
        pause_state = await self.store.get_execution_pause_state(person_id)
        if pause_state and pause_state.get("is_paused"):
            return DailyExecutionPlan(
                person_id=person_id,
                primary_action=None,
                secondary_actions=[],
                why_it_matters="Execution is currently paused. Timers and overdue notifications are frozen.",
                evidence_proof_required="None while in pause state.",
                active_blockers=[],
                next_subsequent_step="Resume execution when you are ready to continue.",
                is_paused=True,
                pause_reason=pause_state.get("reason", "Learner initiated pause.")
            )

        # 2. Retrieve existing actions or decompose from active roadmap
        actions_raw = await self.store.get_person_actions(person_id)
        if not actions_raw:
            roadmap = await self.roadmap_engine.get_or_create_roadmap(person_id)
            flat_stages = self.roadmap_engine.get_all_stages_flat(roadmap)
            active_stage = next((s for s in flat_stages if s.status == "ACTIVE"), flat_stages[0] if flat_stages else None)
            if active_stage:
                actions = await self.decompose_stage_to_actions(
                    person_id=person_id,
                    stage_id=active_stage.stage_id,
                    stage_title=active_stage.title,
                    skills=active_stage.skills,
                    goal_title=roadmap.target_outcome
                )
            else:
                actions = []
        else:
            actions = [CanonicalAction(**a) for a in actions_raw]

        # 3. Filter and resolve dependencies
        completed_ids = {a.action_id for a in actions if a.status == "COMPLETED"}
        active_actions: List[CanonicalAction] = []
        active_blockers: List[ActionBlocker] = []

        for a in actions:
            if a.status in ["COMPLETED", "SUPERSEDED", "ABANDONED"]:
                continue

            # Check if dependencies are satisfied
            unmet_deps = [d for d in a.dependencies if d not in completed_ids]
            if unmet_deps:
                a.status = "BLOCKED"
                a.blocking_reason = ActionBlocker(
                    blocker_type="EXTERNAL_DEPENDENCY",
                    description=f"Prerequisite action ({unmet_deps[0]}) must be completed first."
                )
            elif a.status == "BLOCKED" and a.blocking_reason and a.blocking_reason.blocker_type == "EXTERNAL_DEPENDENCY":
                a.status = "READY"
                a.blocking_reason = None

            if a.blocking_reason and a.blocking_reason.is_active:
                active_blockers.append(a.blocking_reason)

            active_actions.append(a)

        # 4. Pick Primary Action (One clear focus for today)
        primary_action = next(
            (a for a in active_actions if a.status == "IN_PROGRESS"),
            next((a for a in active_actions if a.status == "READY" and a.priority == "NOW"),
                 next((a for a in active_actions if a.status == "READY"), None))
        )

        secondary_actions = [a for a in active_actions if a.action_id != (primary_action.action_id if primary_action else "")]

        # 5. Formulate Why, Proof, Next
        if primary_action:
            why = f"Directly demonstrates core competency for '{primary_action.goal_title or 'your target outcome'}' within {primary_action.stage_title or 'active stage'}."
            proof = f"Requires {primary_action.verification_requirement.replace('_', ' ').lower()}: {', '.join(primary_action.evidence_requirement_ids) or 'documented solution'}."
            next_step = secondary_actions[0].title if secondary_actions else "Complete stage milestone unlock."
        else:
            why = "All active roadmap stage actions have been completed."
            proof = "Stage milestone proof verified."
            next_step = "Unlock and activate the next roadmap milestone stage."

        return DailyExecutionPlan(
            person_id=person_id,
            primary_action=primary_action,
            secondary_actions=secondary_actions[:3],
            why_it_matters=why,
            evidence_proof_required=proof,
            active_blockers=active_blockers,
            next_subsequent_step=next_step,
            is_paused=False
        )

    async def create_user_action(
        self,
        person_id: str,
        req: CreateActionRequest
    ) -> CanonicalAction:
        action = CanonicalAction(
            person_id=person_id,
            title=req.title,
            description=req.description or "",
            action_type=req.action_type or "LEARNING",
            priority=req.priority or "NOW",
            goal_id=req.goal_id,
            stage_id=req.stage_id,
            capability_ids=req.capability_ids or [],
            evidence_requirement_ids=req.evidence_requirement_ids or [],
            status="READY",
            verification_requirement=req.verification_requirement or "SIMPLE_CONFIRMATION",
            due_at=req.due_at or (datetime.now(timezone.utc) + timedelta(days=3)).isoformat(),
            source="USER_CREATED"
        )
        await self.store.save_action(person_id, action.model_dump())
        return action

    async def start_action(self, person_id: str, action_id: str) -> CanonicalAction:
        action_dict = await self.store.get_action(person_id, action_id)
        if not action_dict:
            raise ValueError(f"Action {action_id} not found.")

        action = CanonicalAction(**action_dict)

        # Check dependencies
        if action.dependencies:
            all_actions = await self.store.get_person_actions(person_id)
            completed_ids = {a.get("action_id") for a in all_actions if a.get("status") == "COMPLETED"}
            unmet = [d for d in action.dependencies if d not in completed_ids]
            if unmet:
                raise ValueError(f"Cannot start action: Prerequisite dependency '{unmet[0]}' is incomplete.")

        action.status = "IN_PROGRESS"
        action.started_at = datetime.now(timezone.utc).isoformat()
        await self.store.save_action(person_id, action.model_dump())
        return action

    async def complete_action(
        self,
        person_id: str,
        action_id: str,
        req: CompleteActionRequest
    ) -> CanonicalAction:
        action_dict = await self.store.get_action(person_id, action_id)
        if not action_dict:
            raise ValueError(f"Action {action_id} not found.")

        action = CanonicalAction(**action_dict)

        # Audit outcome vs verification requirement
        outcome = req.outcome or "COMPLETED_SUCCESSFULLY"
        if action.verification_requirement in ["EVIDENCE_SUBMISSION", "MASTERY_EVIDENCE"] and not req.evidence_id and not req.submission_payload:
            outcome = "COMPLETED_NOT_VERIFIED"

        action.status = "COMPLETED"
        action.completed_at = datetime.now(timezone.utc).isoformat()
        action.outcome = outcome
        action.outcome_notes = req.outcome_notes

        await self.store.save_action(person_id, action.model_dump())

        # Log milestone to MemoryEngine if successful
        if outcome == "COMPLETED_SUCCESSFULLY":
            await self.memory_engine.extract_and_store_memory_from_event(
                person_id=person_id,
                event_payload={
                    "topic": f"Action Executed: {action.title}",
                    "milestone": f"Completed {action.action_type} action linked to {action.stage_title or 'active stage'}.",
                    "source": "ExecutionEngine",
                    "capabilities": action.capability_ids
                }
            )

        return action

    async def reschedule_action(
        self,
        person_id: str,
        action_id: str,
        new_due_at: str,
        reason: str
    ) -> CanonicalAction:
        action_dict = await self.store.get_action(person_id, action_id)
        if not action_dict:
            raise ValueError(f"Action {action_id} not found.")

        action = CanonicalAction(**action_dict)
        event = RescheduleEvent(
            original_due_at=action.due_at or datetime.now(timezone.utc).isoformat(),
            new_due_at=new_due_at,
            reason=reason
        )
        action.reschedule_history.append(event)
        action.due_at = new_due_at

        await self.store.save_action(person_id, action.model_dump())
        return action

    async def block_action(
        self,
        person_id: str,
        action_id: str,
        blocker_type: str,
        description: str,
        workaround: Optional[str] = None
    ) -> CanonicalAction:
        action_dict = await self.store.get_action(person_id, action_id)
        if not action_dict:
            raise ValueError(f"Action {action_id} not found.")

        action = CanonicalAction(**action_dict)
        
        # Diagnose workaround if not supplied
        if not workaround:
            diag = await self.agent.diagnose_blocker(action, blocker_type, description)
            workaround = diag.get("workaround")
            suggested_res = diag.get("resolution_action")
        else:
            suggested_res = "Execute recommended workaround."

        blocker = ActionBlocker(
            blocker_type=blocker_type,
            description=description,
            workaround=workaround,
            suggested_resolution_action=suggested_res,
            is_active=True
        )

        action.status = "BLOCKED"
        action.blocking_reason = blocker
        await self.store.save_action(person_id, action.model_dump())
        return action

    async def resolve_blocker(
        self,
        person_id: str,
        action_id: str
    ) -> CanonicalAction:
        action_dict = await self.store.get_action(person_id, action_id)
        if not action_dict:
            raise ValueError(f"Action {action_id} not found.")

        action = CanonicalAction(**action_dict)
        if action.blocking_reason:
            action.blocking_reason.is_active = False

        action.status = "READY"
        action.blocking_reason = None
        await self.store.save_action(person_id, action.model_dump())
        return action

    async def pause_execution(self, person_id: str, reason: str) -> Dict[str, Any]:
        pause_data = {
            "is_paused": True,
            "reason": reason,
            "paused_at": datetime.now(timezone.utc).isoformat()
        }
        await self.store.set_execution_pause_state(person_id, pause_data)
        return pause_data

    async def resume_execution(self, person_id: str) -> Dict[str, Any]:
        pause_data = {
            "is_paused": False,
            "resumed_at": datetime.now(timezone.utc).isoformat()
        }
        await self.store.set_execution_pause_state(person_id, pause_data)
        return pause_data

    async def get_accountability_status(self, person_id: str) -> List[AccountabilityIntervention]:
        # If user is paused, do not trigger false overdue alarms
        pause_state = await self.store.get_execution_pause_state(person_id)
        if pause_state and pause_state.get("is_paused"):
            return []

        actions_raw = await self.store.get_person_actions(person_id)
        now = datetime.now(timezone.utc)
        interventions: List[AccountabilityIntervention] = []

        for a_dict in actions_raw:
            a = CanonicalAction(**a_dict)
            if a.status in ["COMPLETED", "SUPERSEDED", "ABANDONED"]:
                continue
            if a.due_at:
                try:
                    due = datetime.fromisoformat(a.due_at.replace("Z", "+00:00"))
                    if due < now:
                        days = (now - due).days
                        inter = await self.agent.generate_accountability_intervention(person_id, a, days)
                        interventions.append(inter)
                except Exception:
                    pass

        return interventions

    async def track_opportunity_application(
        self,
        person_id: str,
        opp_id: str,
        opp_title: str,
        organization: str,
        status: str,
        notes: Optional[str] = None
    ) -> OpportunityApplicationTracker:
        existing = await self.store.get_opportunity_applications(person_id)
        tracker = next((t for t in existing if t.get("opportunity_id") == opp_id), None)

        if tracker:
            tracker_obj = OpportunityApplicationTracker(**tracker)
            tracker_obj.status = status
            tracker_obj.notes = notes or tracker_obj.notes
            tracker_obj.updated_at = datetime.now(timezone.utc).isoformat()
            if status == "APPLIED" and not tracker_obj.applied_at:
                tracker_obj.applied_at = datetime.now(timezone.utc).isoformat()
        else:
            tracker_obj = OpportunityApplicationTracker(
                person_id=person_id,
                opportunity_id=opp_id,
                opportunity_title=opp_title,
                organization=organization,
                status=status,
                notes=notes,
                applied_at=datetime.now(timezone.utc).isoformat() if status == "APPLIED" else None
            )

        await self.store.save_opportunity_application(person_id, tracker_obj.model_dump())
        return tracker_obj
