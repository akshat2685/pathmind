import pytest
from datetime import datetime, timezone
from backend.services.context_graph_service import ContextGraphService
from backend.services.decision_intelligence_service import DecisionIntelligenceService
from backend.services.store import FirestoreStore

@pytest.mark.asyncio
async def test_personal_context_graph_assembly():
    """
    ContextGraphService dynamically synthesizes all 9 context domains without duplicating canonical models.
    """
    store = FirestoreStore()
    context_service = ContextGraphService(store=store)
    person_id = "test-context-learner-1"

    # Initialize underlying roadmap & mastery
    await context_service.roadmap_engine.get_or_create_roadmap(person_id)

    graph = await context_service.assemble_context_graph(person_id)

    assert graph is not None
    assert graph.person_id == person_id
    assert graph.identity_context["status"] == "CURRENT"
    assert graph.goal_context["primary_target_role"] is not None
    assert graph.learning_context["total_stages"] > 0
    assert graph.career_context["target_role"] is not None
    assert graph.constraint_context["weekly_hours"] >= 5
    assert isinstance(graph.opportunity_context, list)

@pytest.mark.asyncio
async def test_task_context_relevance_filtering():
    """
    extract_task_context_package extracts concise task-specific packages to avoid model context flooding.
    """
    store = FirestoreStore()
    context_service = ContextGraphService(store=store)
    person_id = "test-context-filter"

    await context_service.roadmap_engine.get_or_create_roadmap(person_id)

    pkg = await context_service.extract_task_context_package(person_id, task_type="NEXT_ACTION")

    assert pkg.task_type == "NEXT_ACTION"
    assert pkg.relevant_goal is not None
    assert isinstance(pkg.relevant_skills, list)
    assert isinstance(pkg.active_constraints, dict)

@pytest.mark.asyncio
async def test_command_center_six_answers_generation():
    """
    Command Center accurately answers:
    1. Where Am I?
    2. Where Am I Going?
    3. What Changed?
    4. What Is Blocking Me?
    5. What Should I Do Now?
    6. What Happens After That?
    """
    store = FirestoreStore()
    context_service = ContextGraphService(store=store)
    decision_service = DecisionIntelligenceService(store=store, context_service=context_service)
    person_id = "test-context-cc"

    await context_service.roadmap_engine.get_or_create_roadmap(person_id)

    overview = await decision_service.get_command_center_overview(person_id)

    assert overview.where_am_i["current_stage"] is not None
    assert overview.where_am_i_going["target_role"] is not None
    assert overview.what_changed["event_title"] is not None
    assert overview.what_should_i_do_now.action_title is not None
    assert len(overview.what_should_i_do_now.facts) > 0
    assert len(overview.what_should_i_do_now.interpretation) > 0
    assert len(overview.what_should_i_do_now.tradeoffs) > 0
    assert len(overview.what_happens_after_that) > 0

@pytest.mark.asyncio
async def test_decision_recording_and_outcome_learning():
    """
    User decisions are canonically persisted with context snapshots, and later outcome learning attaches.
    """
    store = FirestoreStore()
    context_service = ContextGraphService(store=store)
    decision_service = DecisionIntelligenceService(store=store, context_service=context_service)
    person_id = "test-decision-learner"

    await context_service.roadmap_engine.get_or_create_roadmap(person_id)

    # 1. Record Decision
    decision = await decision_service.record_user_decision(
        person_id=person_id,
        decision_type="CAREER_DIRECTION",
        title="Choose Robotics Autonomous Systems Path",
        user_choice="Robotics & Autonomous Systems Engineer",
        alternatives=["Classical Backend Software Engineer", "Data Analyst"],
        supporting_evidence_ids=["ev_123"]
    )

    assert decision.decision_id is not None
    assert decision.user_choice == "Robotics & Autonomous Systems Engineer"
    assert decision.outcome_state == "PENDING"
    assert "active_target_role" in decision.context_snapshot_summary

    # 2. Attach Outcome Learning
    updated = await decision_service.record_decision_outcome(
        person_id=person_id,
        decision_id=decision.decision_id,
        outcome_state="POSITIVE",
        outcome_note="Successfully completed ROS simulation milestone with 95% pass rate."
    )
    assert updated is True

    # 3. Retrieve Decision Records
    records = await store.get_decision_records(person_id)
    assert len(records) == 1
    assert records[0]["outcome_state"] == "POSITIVE"

@pytest.mark.asyncio
async def test_next_action_adapts_to_mastery_risk():
    """
    When a mastery risk is flagged, NextAction prioritizes concept remediation before forward progression.
    """
    store = FirestoreStore()
    context_service = ContextGraphService(store=store)
    decision_service = DecisionIntelligenceService(store=store, context_service=context_service)
    person_id = "test-risk-next-action"

    await context_service.roadmap_engine.get_or_create_roadmap(person_id)

    # Flag a skill at risk
    await context_service.mastery_engine.record_mastery_regression(
        person_id=person_id,
        skill_name="Python Threading",
        reason="Race condition detected during multi-threaded parser benchmark."
    )

    next_action = await decision_service.compute_next_action(person_id)

    assert next_action.action_type == "REFRESH_SKILL"
    assert "Python Threading" in next_action.action_title
    assert next_action.priority == "NOW"

@pytest.mark.asyncio
async def test_tenant_isolation_for_context_and_decisions():
    """
    Person A's decision records and context conflicts cannot be accessed by Person B.
    """
    store = FirestoreStore()
    person_a = "person-ctx-alpha"
    person_b = "person-ctx-beta"

    await store.save_decision_record(person_a, {
        "decision_id": "dec_alpha",
        "person_id": person_a,
        "title": "Alpha Decision",
        "user_choice": "Choice A"
    })

    decs_b = await store.get_decision_records(person_b)
    assert len(decs_b) == 0

    decs_a = await store.get_decision_records(person_a)
    assert len(decs_a) == 1
    assert decs_a[0]["decision_id"] == "dec_alpha"
