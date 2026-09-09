from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
from backend.core.evidence_schemas import (
    CanonicalEvidence,
    EvaluationAttempt,
    EvidenceDispute,
    SkillMasteryProfile,
    LockedStageReason,
    MasteryDashboardState,
    StructuredEvaluationDetail
)
from backend.services.evidence_verification_service import EvidenceVerificationService
from backend.services.evidence_evaluation_agent import EvidenceEvaluationAgent
from backend.services.store import FirestoreStore
from backend.services.roadmap_engine import RoadmapEngine
from backend.services.memory_engine import MemoryEngine
from backend.services.personal_agent_engine import PersonalAgentEngine

class MasteryEngine:
    def __init__(
        self,
        store: Optional[FirestoreStore] = None,
        verification_service: Optional[EvidenceVerificationService] = None,
        evaluation_agent: Optional[EvidenceEvaluationAgent] = None,
        roadmap_engine: Optional[RoadmapEngine] = None,
        memory_engine: Optional[MemoryEngine] = None,
        personal_agent: Optional[PersonalAgentEngine] = None
    ):
        self.store = store or FirestoreStore()
        self.verification_service = verification_service or EvidenceVerificationService()
        self.evaluation_agent = evaluation_agent or EvidenceEvaluationAgent()
        self.roadmap_engine = roadmap_engine or RoadmapEngine()
        self.memory_engine = memory_engine or MemoryEngine()
        self.personal_agent = personal_agent or PersonalAgentEngine()

    async def submit_and_evaluate_evidence(
        self,
        person_id: str,
        stage_id: str,
        evidence_type: str,
        title: str,
        source_reference: str,
        payload: Dict[str, Any],
        is_transfer_task: bool = False
    ) -> EvaluationAttempt:
        # 1. Check roadmap lock status (Backend lock enforcement)
        roadmap = await self.roadmap_engine.get_or_create_roadmap(person_id)
        flat_stages = self.roadmap_engine.get_all_stages_flat(roadmap)
        target_stage = next((s for s in flat_stages if s.stage_id == stage_id), None)

        if not target_stage:
            raise ValueError(f"Stage {stage_id} not found in active roadmap.")

        if target_stage.locked and target_stage.stage_id != roadmap.current_stage_id and not is_transfer_task:
            raise PermissionError("UNLOCK_REJECTED: Cannot submit evidence for a locked stage. Complete prerequisites first.")

        # 2. Build CanonicalEvidence record
        evidence = CanonicalEvidence(
            person_id=person_id,
            evidence_type=evidence_type,
            title=title,
            description=f"Evidence artifact submitted for {target_stage.title}.",
            source="USER_SUBMISSION",
            source_reference=source_reference,
            related_skill_ids=target_stage.skills,
            related_stage_id=stage_id,
            related_goal_id=roadmap.target_outcome,
            metadata={"payload": payload}
        )

        # 3. Deterministic Verification
        v_status, quality, confidence = self.verification_service.verify_artifact(evidence, payload)
        evidence.verification_status = v_status
        evidence.quality = quality
        evidence.confidence = confidence

        await self.store.save_canonical_evidence(person_id, evidence.model_dump())

        # 4. ADK Agent Evaluation
        eval_detail = await self.evaluation_agent.evaluate_evidence(
            evidence=evidence,
            stage_title=target_stage.title,
            required_skills=target_stage.skills,
            verification_quality=quality,
            is_transfer_task=is_transfer_task
        )

        is_pass = quality in ["STRONG", "VERIFIED_STRONG"] and v_status == "VERIFIED"
        status = "PASS" if is_pass else "REINFORCE"

        # 5. Record Attempt in Sequential History
        past_attempts = await self.store.get_evaluation_attempts(person_id, stage_id)
        attempt = EvaluationAttempt(
            submission_id=evidence.evidence_id,
            evidence_id=evidence.evidence_id,
            stage_id=stage_id,
            person_id=person_id,
            attempt_number=len(past_attempts) + 1,
            status=status,
            score_accuracy=92.0 if is_pass else 65.0,
            evaluation_detail=eval_detail
        )
        await self.store.save_evaluation_attempt(person_id, attempt.model_dump())

        # 6. Update Skill Mastery Profiles
        for skill in target_stage.skills:
            mastery_state = eval_detail.mastery_state_achieved if is_pass else "NEEDS_REINFORCEMENT"
            profile = SkillMasteryProfile(
                skill_name=skill,
                category=target_stage.title,
                mastery_state=mastery_state,
                evidence_count=len(past_attempts) + 1,
                primary_evidence_id=evidence.evidence_id,
                is_regression_risk=False
            )
            await self.store.save_skill_mastery_profile(person_id, skill, profile.model_dump())

        # 7. If PASS: Unlock next stage & Ingest Memory
        if is_pass:
            target_stage.status = "COMPLETED"
            roadmap.completed_stages += 1

            # Unlock next stage
            current_idx = next(i for i, s in enumerate(flat_stages) if s.stage_id == target_stage.stage_id)
            if current_idx + 1 < len(flat_stages):
                next_stage = flat_stages[current_idx + 1]
                next_stage.locked = False
                next_stage.status = "ACTIVE"
                if next_stage.missions:
                    next_stage.missions[0].status = "ACTIVE"
                roadmap.current_stage_id = next_stage.stage_id
                roadmap.current_mission_id = next_stage.missions[0].mission_id if next_stage.missions else None

            await self.store.update_active_roadmap(person_id, roadmap.model_dump(mode="json"))

            # Log breakthrough memory
            await self.memory_engine.extract_and_store_memory_from_event(
                person_id=person_id,
                event_payload={
                    "topic": target_stage.title,
                    "observation": f"Successfully verified mastery in {', '.join(target_stage.skills)} via {title}.",
                    "intervention": "Stage prerequisite unlocked.",
                    "event_type": "MASTERY_DEMONSTRATED"
                }
            )

        return attempt

    async def record_mastery_regression(
        self,
        person_id: str,
        skill_name: str,
        reason: str
    ) -> SkillMasteryProfile:
        """
        Flags a previously demonstrated skill as MASTERY_AT_RISK without erasing historical data.
        """
        profiles = await self.store.get_skill_mastery_profiles(person_id)
        current_data = profiles.get(skill_name, {})
        
        updated = SkillMasteryProfile(
            skill_name=skill_name,
            category=current_data.get("category", "Technical Skill"),
            mastery_state="MASTERY_AT_RISK",
            evidence_count=current_data.get("evidence_count", 1),
            primary_evidence_id=current_data.get("primary_evidence_id"),
            is_regression_risk=True,
            regression_reason=reason
        )
        await self.store.save_skill_mastery_profile(person_id, skill_name, updated.model_dump())
        return updated

    async def file_dispute(
        self,
        person_id: str,
        attempt_id: str,
        reason: str,
        additional_evidence_reference: Optional[str] = None
    ) -> EvidenceDispute:
        dispute = EvidenceDispute(
            person_id=person_id,
            attempt_id=attempt_id,
            reason=reason,
            additional_evidence_reference=additional_evidence_reference,
            status="PENDING_REVIEW"
        )
        await self.store.save_evidence_dispute(person_id, dispute.model_dump())
        return dispute

    async def resolve_dispute(
        self,
        person_id: str,
        dispute_id: str,
        new_status: str = "UPHELD",
        resolution_note: Optional[str] = None
    ) -> bool:
        return await self.store.update_evidence_dispute(
            person_id=person_id,
            dispute_id=dispute_id,
            status=new_status,
            resolution_note=resolution_note or "Dispute reviewed and resolved."
        )

    async def get_mastery_dashboard_state(self, person_id: str) -> MasteryDashboardState:
        roadmap = await self.roadmap_engine.get_or_create_roadmap(person_id)
        flat_stages = self.roadmap_engine.get_all_stages_flat(roadmap)
        
        # 1. Skills Mastered
        profiles_raw = await self.store.get_skill_mastery_profiles(person_id)
        skills_mastered = [SkillMasteryProfile(**p) for p in profiles_raw.values()]

        # 2. Capabilities Working On
        active_stage = next((s for s in flat_stages if s.stage_id == roadmap.current_stage_id), flat_stages[0] if flat_stages else None)
        working_on = []
        evidence_needed = []
        if active_stage:
            working_on.append({
                "stage_id": active_stage.stage_id,
                "stage_number": active_stage.stage_number,
                "title": active_stage.title,
                "objective": active_stage.objective,
                "skills": active_stage.skills
            })
            evidence_needed.append({
                "stage_id": active_stage.stage_id,
                "requirements": active_stage.evidence_requirements or ["Code repository or verified script with unit tests."],
                "minimum_quality": "STRONG (passing tests + type safety)",
                "accepted_formats": ["Python Script (.py)", "GitHub Repository URL", "Test Execution Log"]
            })

        # 3. Locked Stages with Concrete Reasons
        locked_stages = []
        for i, s in enumerate(flat_stages):
            if s.locked:
                prereq_stage = flat_stages[i - 1] if i > 0 else s
                locked_stages.append(LockedStageReason(
                    stage_id=s.stage_id,
                    stage_number=s.stage_number,
                    title=s.title,
                    prerequisite_stage_id=prereq_stage.stage_id,
                    prerequisite_title=prereq_stage.title,
                    missing_capabilities=prereq_stage.skills,
                    unlock_rule=f"Submit passing code evidence for Stage 0{prereq_stage.stage_number} ({prereq_stage.title})."
                ))

        # 4. Recent Evaluations & Disputes
        recent_evals = [EvaluationAttempt(**a) for a in await self.store.get_evaluation_attempts(person_id)]
        disputes = [EvidenceDispute(**d) for d in await self.store.get_evidence_disputes(person_id)]

        return MasteryDashboardState(
            person_id=person_id,
            skills_mastered=skills_mastered,
            capabilities_working_on=working_on,
            evidence_needed=evidence_needed,
            locked_stages=locked_stages,
            recent_evaluations=recent_evals[:10],
            active_disputes=disputes
        )
