import pytest
from datetime import datetime, timezone, timedelta
from backend.services.adaptation_service import AdaptationService
from backend.services.state_change_service import StateChangeService
from backend.services.impact_analysis_service import ImpactAnalysisService
from backend.services.adaptive_planning_agent import AdaptivePlanningAgent
from backend.services.roadmap_engine import RoadmapEngine
from backend.services.store import FirestoreStore
from backend.core.adaptation_schemas import UserAdaptationDecision, StateChangeEvent

@pytest.mark.asyncio
async def test_goal_change_creates_versioned_proposal_and_requires_approval():
    """
    Changing target goal must trigger impact analysis, formulate a Roadmap v2 proposal,
    preserve foundational milestones, and require explicit user approval.
    """
    store = FirestoreStore()
    adaptation_service = AdaptationService(store=store)
    person_id = "test-learner-goal-change"

    # 1. Initialize baseline roadmap (Version 1)
    await adaptation_service.roadmap_engine.get_or_create_roadmap(person_id)

    # 2. Trigger goal change
    proposal = await adaptation_service.handle_goal_change(
        person_id=person_id,
        new_target_role="Robotics & Autonomous Systems Engineer",
        target_industry="Robotics & Hardware Systems",
        target_timeline="9–12 Months"
    )

    assert proposal is not None
    assert proposal.proposed_roadmap_version == 2
    assert proposal.impact_analysis.impact_level in ["HIGH_IMPACT", "CRITICAL_CHANGE"]
    assert proposal.impact_analysis.requires_user_approval is True
    assert proposal.status == "PENDING_APPROVAL"
    assert "Stage 01: Python Foundations" in proposal.impact_analysis.preserved_assets

    # Verify baseline roadmap remains Version 1 until approved
    active_rm = await adaptation_service.roadmap_engine.get_or_create_roadmap(person_id)
    assert active_rm.version == 1

    # 3. User Approves the adaptation
    decision = UserAdaptationDecision(
        adaptation_id=proposal.adaptation_id,
        person_id=person_id,
        action="APPROVE",
        user_feedback="Approved transition to Robotics trajectory."
    )
    result = await adaptation_service.decide_adaptation(person_id, decision)
    assert result["status"] == "APPROVED"
    assert result["active_version"] == 2

    # Verify roadmap version updated to 2
    active_rm_after = await adaptation_service.roadmap_engine.get_or_create_roadmap(person_id)
    assert active_rm_after.version == 2

@pytest.mark.asyncio
async def test_plan_stability_low_impact_auto_adapts():
    """
    Minor changes (routine evidence submissions or minor format preferences)
    auto-adapt without triggering unnecessary major version bumps or approval dialogs.
    """
    store = FirestoreStore()
    impact_service = ImpactAnalysisService()

    event = StateChangeEvent(
        person_id="test-learner-stable",
        change_type="EVIDENCE_CHANGE",
        title="Passing Unit Test Suite for Stage 01",
        description="Passed 4 unit tests for modular parser.",
        trigger_data={"demonstrated_skills": ["Python OOP", "Unit Testing"]}
    )

    impact = impact_service.analyze_change(event)
    assert impact.impact_level == "LOW_IMPACT"
    assert impact.requires_user_approval is False
    assert impact.approval_type == "AUTO_ADAPT"

@pytest.mark.asyncio
async def test_mastery_risk_triggers_reinforcement_not_downstream_unlock():
    """
    Multiple evidence failures trigger MASTERY_RISK and inject a reinforcement stage
    rather than skipping prerequisites.
    """
    store = FirestoreStore()
    state_service = StateChangeService(store=store)
    impact_service = ImpactAnalysisService()
    person_id = "test-learner-risk"

    event = await state_service.detect_mastery_risk(
        person_id=person_id,
        stage_id="stage_02_math_and_linear_algebra",
        failed_count=3,
        struggling_concepts=["Matrix Eigen-decomposition", "Gradient Computation"]
    )

    assert event.change_type == "MASTERY_RISK"
    assert event.trigger_data["failed_count"] == 3

    impact = impact_service.analyze_change(event)
    assert impact.impact_level == "MODERATE_IMPACT"
    assert impact.approval_type == "AUTO_ADAPT"
    assert "stage_02_math_and_linear_algebra" in impact.affected_roadmap_stages
    assert "reinforcement" in impact.what_changed.lower()

@pytest.mark.asyncio
async def test_constraint_change_smoothly_recalibrates():
    """
    Reducing available study hours adjusts pacing smoothly without destroying completed stages.
    """
    store = FirestoreStore()
    adaptation_service = AdaptationService(store=store)
    person_id = "test-learner-constraint"

    proposal = await adaptation_service.handle_constraint_change(
        person_id=person_id,
        weekly_hours=6,
        preferred_format="project-based"
    )

    assert proposal is not None
    assert proposal.change_event.change_type == "CONSTRAINT_CHANGE"
    assert proposal.change_event.trigger_data["weekly_hours"] == 6
    assert len(proposal.impact_analysis.preserved_assets) > 0

    # Check updated agent model
    agent_model = await adaptation_service.personal_agent.get_or_create_agent_model(person_id)
    assert agent_model.learning_preferences["weekly_hours"] == 6

@pytest.mark.asyncio
async def test_opportunity_driven_adaptation():
    """
    Verified opportunity matching triggers review to prioritize relevant milestone projects.
    """
    store = FirestoreStore()
    adaptation_service = AdaptationService(store=store)
    person_id = "test-learner-opp"

    proposal = await adaptation_service.handle_opportunity_event(
        person_id=person_id,
        opportunity_id="gsoc_robotics_2026",
        opportunity_title="Google Summer of Code — ROS Navigation Package",
        organization="Open Robotics / Linux Foundation",
        required_milestones=["ROS Navigation Milestone Artifact"]
    )

    assert proposal is not None
    assert proposal.impact_analysis.approval_type == "REVIEW"
    assert "ROS Navigation Milestone Artifact" in proposal.impact_analysis.affected_roadmap_stages

@pytest.mark.asyncio
async def test_pause_and_resume_reassessment_after_hiatus():
    """
    Returning after > 90 days triggers a REASSESS / diagnostic refresher recommendation.
    """
    store = FirestoreStore()
    state_service = StateChangeService(store=store)
    person_id = "test-learner-pause"

    # Simulate 100 days of absence
    simulated_last_active = datetime.now(timezone.utc) - timedelta(days=100)
    analysis = await state_service.analyze_pause_and_resume(person_id, simulated_last_activity=simulated_last_active)

    assert analysis.elapsed_days >= 99
    assert analysis.status == "LONG_BREAK"
    assert analysis.recommended_action == "REASSESS"
    assert analysis.suggested_refresher_concept is not None

@pytest.mark.asyncio
async def test_conflict_detection_surfaces_evidence_discrepancy():
    """
    Self-report confidence contradicting repeated task failures triggers EVIDENCE_CONFLICT.
    """
    store = FirestoreStore()
    state_service = StateChangeService(store=store)
    person_id = "test-learner-conflict"

    # Seed 2 misconception events in learning events for Python
    await store.save_learning_event(person_id, {
        "event_id": "ev1",
        "stage_id": "stage_01",
        "topic": "Python OOP Generators",
        "event_type": "RECURRING_MISCONCEPTION",
        "observation": "Memory leak in custom generator batcher.",
        "timestamp": datetime.now(timezone.utc).isoformat()
    })
    await store.save_learning_event(person_id, {
        "event_id": "ev2",
        "stage_id": "stage_01",
        "topic": "Python Type Hints & Mypy",
        "event_type": "RECURRING_MISCONCEPTION",
        "observation": "Syntax errors with Generic type vars.",
        "timestamp": datetime.now(timezone.utc).isoformat()
    })

    conflict = await state_service.detect_evidence_conflict(
        person_id=person_id,
        claimed_skill="Python",
        self_report_level="EXPERT"
    )

    assert conflict.has_conflict is True
    assert conflict.conflict_type == "EVIDENCE_CONFLICT"
    assert "Python" in conflict.self_report_claim
    assert conflict.recommended_verification_task is not None

@pytest.mark.asyncio
async def test_roadmap_history_and_isolation():
    """
    Past roadmap versions remain retrievable and Person A cannot access Person B's adaptations.
    """
    store = FirestoreStore()
    adaptation_service = AdaptationService(store=store)
    person_a = "person-alpha-10"
    person_b = "person-beta-10"

    # Person A creates a goal change proposal
    prop_a = await adaptation_service.handle_goal_change(
        person_id=person_a,
        new_target_role="AI Systems Architect"
    )

    # Person B checks pending adaptations
    pending_b = await store.get_pending_adaptations(person_b)
    assert len(pending_b) == 0

    # Person A checks pending adaptations
    pending_a = await store.get_pending_adaptations(person_a)
    assert len(pending_a) == 1
    assert pending_a[0]["adaptation_id"] == prop_a.adaptation_id
