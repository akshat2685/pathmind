from typing import Dict, Any, List, Optional
from datetime import datetime, timezone, timedelta
from backend.core.adaptation_schemas import (
    StateChangeEvent,
    PauseResumeAnalysis,
    ConflictDetectionResult
)
from backend.services.store import FirestoreStore

class StateChangeService:
    def __init__(self, store: Optional[FirestoreStore] = None):
        self.store = store or FirestoreStore()

    async def detect_goal_change(
        self,
        person_id: str,
        new_target_role: str,
        target_industry: Optional[str] = None,
        geography: Optional[str] = None,
        target_timeline: Optional[str] = None
    ) -> StateChangeEvent:
        current_goal = await self.store.get_career_goal(person_id)
        prev_role = current_goal.get("target_role", "Applied Machine Learning Systems Engineer") if current_goal else "Applied Machine Learning Systems Engineer"
        
        return StateChangeEvent(
            person_id=person_id,
            change_type="GOAL_CHANGE",
            title=f"Target Goal Changed: {prev_role} → {new_target_role}",
            description=f"Person updated target career goal from {prev_role} to {new_target_role}.",
            trigger_data={
                "previous_role": prev_role,
                "new_target_role": new_target_role,
                "target_industry": target_industry or (current_goal.get("target_industry") if current_goal else "Applied AI & Tech"),
                "geography": geography or (current_goal.get("geography") if current_goal else "Global / India"),
                "target_timeline": target_timeline or (current_goal.get("target_timeline") if current_goal else "6–9 Months")
            }
        )

    async def detect_evidence_change(
        self,
        person_id: str,
        stage_id: str,
        demonstrated_skills: List[str],
        artifact_title: str
    ) -> StateChangeEvent:
        return StateChangeEvent(
            person_id=person_id,
            change_type="EVIDENCE_CHANGE",
            title=f"New Evidence Demonstrated: {artifact_title}",
            description=f"Successfully demonstrated competency in {', '.join(demonstrated_skills)} for stage {stage_id}.",
            trigger_data={
                "stage_id": stage_id,
                "demonstrated_skills": demonstrated_skills,
                "artifact_title": artifact_title
            }
        )

    async def detect_mastery_risk(
        self,
        person_id: str,
        stage_id: str,
        failed_count: int,
        struggling_concepts: List[str]
    ) -> StateChangeEvent:
        return StateChangeEvent(
            person_id=person_id,
            change_type="MASTERY_RISK",
            title=f"Mastery Risk Flagged: Stage {stage_id}",
            description=f"Repeated evidence struggles ({failed_count} attempts) detected for concepts: {', '.join(struggling_concepts)}.",
            trigger_data={
                "stage_id": stage_id,
                "failed_count": failed_count,
                "struggling_concepts": struggling_concepts
            }
        )

    async def detect_constraint_change(
        self,
        person_id: str,
        weekly_hours: int,
        previous_hours: int,
        preferred_format: Optional[str] = None
    ) -> StateChangeEvent:
        return StateChangeEvent(
            person_id=person_id,
            change_type="CONSTRAINT_CHANGE",
            title=f"Time Constraint Shift: {previous_hours}h/wk → {weekly_hours}h/wk",
            description=f"Available study time adjusted from {previous_hours} hours/week to {weekly_hours} hours/week.",
            trigger_data={
                "previous_hours": previous_hours,
                "weekly_hours": weekly_hours,
                "preferred_format": preferred_format or "project-based"
            }
        )

    async def detect_opportunity_change(
        self,
        person_id: str,
        opportunity_id: str,
        opportunity_title: str,
        organization: str,
        required_milestones: List[str]
    ) -> StateChangeEvent:
        return StateChangeEvent(
            person_id=person_id,
            change_type="OPPORTUNITY_CHANGE",
            title=f"Target Opportunity Emerged: {opportunity_title} ({organization})",
            description=f"Verified opportunity matches profile. Suggesting prioritization of {', '.join(required_milestones)}.",
            trigger_data={
                "opportunity_id": opportunity_id,
                "opportunity_title": opportunity_title,
                "organization": organization,
                "required_milestones": required_milestones
            }
        )

    async def analyze_pause_and_resume(
        self,
        person_id: str,
        simulated_last_activity: Optional[datetime] = None
    ) -> PauseResumeAnalysis:
        # Determine last activity from learning events, submissions, or check-ins
        events = await self.store.get_learning_events(person_id)
        now = datetime.now(timezone.utc)
        
        last_dt = simulated_last_activity
        if not last_dt and events:
            # find latest timestamp
            try:
                latest_ts = max(e.get("timestamp", "") for e in events if e.get("timestamp"))
                if latest_ts:
                    last_dt = datetime.fromisoformat(latest_ts.replace("Z", "+00:00"))
            except Exception:
                pass
        
        if not last_dt:
            last_dt = now

        elapsed_days = max(0, (now - last_dt).days)
        
        if elapsed_days >= 90:
            status = "LONG_BREAK"
            action = "REASSESS"
            rationale = (
                f"You have been away for {elapsed_days} days. Before diving into advanced milestones, "
                "PATHMIND recommends a brief 10-minute diagnostic refresher to verify retained fundamentals."
            )
            refresher = "Core System Fundamentals & Syntax Refresher"
        elif elapsed_days >= 30:
            status = "SHORT_PAUSE"
            action = "REFRESH"
            rationale = (
                f"Welcome back after {elapsed_days} days. Your active stage and completed milestones remain fully preserved. "
                "A brief warm-up task is recommended before your next code submission."
            )
            refresher = "Active Milestone Concept Warmup"
        else:
            status = "ACTIVE"
            action = "CONTINUE"
            rationale = "Active momentum maintained. Continue seamlessly with your current stage mission."
            refresher = None

        return PauseResumeAnalysis(
            person_id=person_id,
            elapsed_days=elapsed_days,
            last_activity_date=last_dt.isoformat(),
            status=status,
            recommended_action=action,
            reassessment_rationale=rationale,
            suggested_refresher_concept=refresher
        )

    async def detect_evidence_conflict(
        self,
        person_id: str,
        claimed_skill: str,
        self_report_level: str = "CONFIDENT"
    ) -> ConflictDetectionResult:
        # Check task evaluation history for this claimed skill
        events = await self.store.get_learning_events(person_id)
        skill_failures = [
            e for e in events 
            if claimed_skill.lower() in e.get("topic", "").lower() and e.get("event_type") == "RECURRING_MISCONCEPTION"
        ]

        if len(skill_failures) >= 2 and self_report_level.upper() in ["CONFIDENT", "EXPERT", "ADVANCED"]:
            return ConflictDetectionResult(
                person_id=person_id,
                has_conflict=True,
                conflict_type="EVIDENCE_CONFLICT",
                self_report_claim=f"Self-assessed as {self_report_level} in {claimed_skill}",
                observed_task_evidence=f"{len(skill_failures)} repeated misconceptions recorded during practical execution tasks.",
                explanation=(
                    f"Your self-assessment indicates high confidence in {claimed_skill}, but recent task submissions "
                    f"encountered friction with concrete implementation details. PATHMIND recommends a quick 1-task "
                    f"verification checkpoint rather than skipping prerequisites."
                ),
                recommended_verification_task=f"Practical {claimed_skill} Verification Benchmark"
            )

        return ConflictDetectionResult(
            person_id=person_id,
            has_conflict=False,
            explanation="No contradictions detected between self-assessment claims and task execution evidence."
        )
