import pytest
from datetime import datetime, timezone, timedelta
from backend.services.execution_engine import ExecutionEngine
from backend.core.execution_schemas import (
    CompleteActionRequest,
    CreateActionRequest,
    TrackApplicationRequest
)
from backend.services.store import FirestoreStore

@pytest.fixture
def clean_store():
    store = FirestoreStore()
    store._in_memory_persons.clear()
    return store

@pytest.fixture
def execution_engine(clean_store):
    return ExecutionEngine(store=clean_store)

@pytest.mark.asyncio
async def test_stage_action_decomposition(execution_engine):
    person_id = "person_alex"
    actions = await execution_engine.decompose_stage_to_actions(
        person_id=person_id,
        stage_id="stage_01",
        stage_title="Python Systems & Testing",
        skills=["Python", "Pytest", "AsyncIO"],
        goal_title="Applied AI Specialist"
    )

    assert len(actions) == 3
    assert actions[0].priority == "NOW"
    assert actions[0].action_type == "LEARNING"
    assert actions[0].dependencies == []

    # Action 2 depends on Action 1
    assert actions[1].priority == "NEXT"
    assert actions[1].dependencies == [actions[0].action_id]

    # Action 3 depends on Action 2
    assert actions[2].priority == "LATER"
    assert actions[2].dependencies == [actions[1].action_id]

@pytest.mark.asyncio
async def test_daily_execution_plan_primary_action(execution_engine):
    person_id = "person_alex"
    await execution_engine.decompose_stage_to_actions(
        person_id=person_id,
        stage_id="stage_01",
        stage_title="Python Systems & Testing",
        skills=["Python", "Pytest"],
        goal_title="Applied AI Specialist"
    )

    plan = await execution_engine.get_daily_execution_plan(person_id)
    assert plan.is_paused is False
    assert plan.primary_action is not None
    assert plan.primary_action.priority == "NOW"
    assert "Applied AI Specialist" in plan.why_it_matters
    assert len(plan.evidence_proof_required) > 0
    assert len(plan.secondary_actions) >= 1

@pytest.mark.asyncio
async def test_dependency_enforcement(execution_engine):
    person_id = "person_alex"
    actions = await execution_engine.decompose_stage_to_actions(
        person_id=person_id,
        stage_id="stage_01",
        stage_title="Python Systems & Testing",
        skills=["Python"],
        goal_title="AI Specialist"
    )

    # Action 2 depends on Action 1. Trying to start Action 2 prematurely must fail
    with pytest.raises(ValueError) as exc:
        await execution_engine.start_action(person_id, actions[1].action_id)
    assert "Prerequisite dependency" in str(exc.value)

@pytest.mark.asyncio
async def test_start_and_complete_action_with_outcome(execution_engine):
    person_id = "person_alex"
    actions = await execution_engine.decompose_stage_to_actions(
        person_id=person_id,
        stage_id="stage_01",
        stage_title="Python Systems & Testing",
        skills=["Python"],
        goal_title="AI Specialist"
    )

    # Start Action 1
    started = await execution_engine.start_action(person_id, actions[0].action_id)
    assert started.status == "IN_PROGRESS"
    assert started.started_at is not None

    # Complete Action 1
    completed = await execution_engine.complete_action(
        person_id=person_id,
        action_id=actions[0].action_id,
        req=CompleteActionRequest(outcome="COMPLETED_SUCCESSFULLY")
    )
    assert completed.status == "COMPLETED"
    assert completed.outcome == "COMPLETED_SUCCESSFULLY"

    # Now Action 2 can be started
    started_2 = await execution_engine.start_action(person_id, actions[1].action_id)
    assert started_2.status == "IN_PROGRESS"

@pytest.mark.asyncio
async def test_completion_vs_outcome_distinction(execution_engine):
    person_id = "person_alex"
    actions = await execution_engine.decompose_stage_to_actions(
        person_id=person_id,
        stage_id="stage_01",
        stage_title="Python Systems & Testing",
        skills=["Python"],
        goal_title="AI Specialist"
    )

    # Action 2 requires EVIDENCE_SUBMISSION. If completed without evidence, outcome is COMPLETED_NOT_VERIFIED
    completed_gap = await execution_engine.complete_action(
        person_id=person_id,
        action_id=actions[1].action_id,
        req=CompleteActionRequest(outcome="COMPLETED_SUCCESSFULLY", evidence_id=None)
    )
    assert completed_gap.status == "COMPLETED"
    assert completed_gap.outcome == "COMPLETED_NOT_VERIFIED"

@pytest.mark.asyncio
async def test_reschedule_preserves_history(execution_engine):
    person_id = "person_alex"
    actions = await execution_engine.decompose_stage_to_actions(
        person_id=person_id,
        stage_id="stage_01",
        stage_title="Python Systems & Testing",
        skills=["Python"],
        goal_title="AI Specialist"
    )

    original_due = actions[0].due_at
    new_due = (datetime.now(timezone.utc) + timedelta(days=5)).isoformat()
    reason = "University final exams; shifting study window by 3 days."

    rescheduled = await execution_engine.reschedule_action(person_id, actions[0].action_id, new_due, reason)
    assert rescheduled.due_at == new_due
    assert len(rescheduled.reschedule_history) == 1
    assert rescheduled.reschedule_history[0].original_due_at == original_due
    assert rescheduled.reschedule_history[0].reason == reason

@pytest.mark.asyncio
async def test_blocker_diagnosis_and_resolution(execution_engine):
    person_id = "person_alex"
    actions = await execution_engine.decompose_stage_to_actions(
        person_id=person_id,
        stage_id="stage_01",
        stage_title="Python Systems & Testing",
        skills=["Python"],
        goal_title="AI Specialist"
    )

    # Block Action 1
    blocked = await execution_engine.block_action(
        person_id=person_id,
        action_id=actions[0].action_id,
        blocker_type="FINANCIAL_CONSTRAINT",
        description="Certification exam fee is currently unaffordable."
    )
    assert blocked.status == "BLOCKED"
    assert blocked.blocking_reason is not None
    assert "open-source repository" in blocked.blocking_reason.workaround.lower() or len(blocked.blocking_reason.workaround) > 10

    # Resolve Blocker
    resolved = await execution_engine.resolve_blocker(person_id, actions[0].action_id)
    assert resolved.status == "READY"
    assert resolved.blocking_reason is None

@pytest.mark.asyncio
async def test_pause_freezes_accountability(execution_engine):
    person_id = "person_alex"
    actions = await execution_engine.decompose_stage_to_actions(
        person_id=person_id,
        stage_id="stage_01",
        stage_title="Python Systems & Testing",
        skills=["Python"],
        goal_title="AI Specialist"
    )

    # Set action due date to yesterday
    past_date = (datetime.now(timezone.utc) - timedelta(days=2)).isoformat()
    actions[0].due_at = past_date
    await execution_engine.store.save_action(person_id, actions[0].model_dump())

    # When active: triggers accountability intervention
    interventions = await execution_engine.get_accountability_status(person_id)
    assert len(interventions) >= 1
    assert interventions[0].days_overdue >= 1
    assert "Life constraints happen" in interventions[0].non_judgmental_message

    # When paused: freezes accountability (zero false overdue alarms)
    await execution_engine.pause_execution(person_id, "Taking a week off for personal travel.")
    paused_interventions = await execution_engine.get_accountability_status(person_id)
    assert len(paused_interventions) == 0

    plan = await execution_engine.get_daily_execution_plan(person_id)
    assert plan.is_paused is True
    assert "travel" in plan.pause_reason.lower()

    # Resume execution
    await execution_engine.resume_execution(person_id)
    resumed_plan = await execution_engine.get_daily_execution_plan(person_id)
    assert resumed_plan.is_paused is False

@pytest.mark.asyncio
async def test_opportunity_application_tracking(execution_engine):
    person_id = "person_alex"
    req = TrackApplicationRequest(
        opportunity_id="opp_101",
        opportunity_title="AI Research Intern",
        organization="Verified AI Lab",
        status="PREPARING",
        notes="Tailoring resume with verified Pytest and AsyncIO project evidence."
    )

    tracked = await execution_engine.track_opportunity_application(
        person_id=person_id,
        opp_id=req.opportunity_id,
        opp_title=req.opportunity_title,
        organization=req.organization,
        status=req.status,
        notes=req.notes
    )
    assert tracked.status == "PREPARING"
    assert tracked.applied_at is None

    # Submit application
    applied = await execution_engine.track_opportunity_application(
        person_id=person_id,
        opp_id=req.opportunity_id,
        opp_title=req.opportunity_title,
        organization=req.organization,
        status="APPLIED"
    )
    assert applied.status == "APPLIED"
    assert applied.applied_at is not None

@pytest.mark.asyncio
async def test_tenant_isolation_actions(execution_engine):
    await execution_engine.decompose_stage_to_actions(
        person_id="person_alex",
        stage_id="stage_01",
        stage_title="Python Systems",
        skills=["Python"]
    )

    alex_actions = await execution_engine.store.get_person_actions("person_alex")
    bob_actions = await execution_engine.store.get_person_actions("person_bob")

    assert len(alex_actions) >= 3
    assert len(bob_actions) == 0

@pytest.mark.asyncio
async def test_user_created_action(execution_engine):
    person_id = "person_alex"
    req = CreateActionRequest(
        title="Attend PyData Meetup & Present Prototype",
        description="Present AsyncIO pipeline architecture to peer engineers.",
        action_type="NETWORKING",
        priority="NEXT",
        goal_id="career_goal_applied_ai",
        stage_id="stage_01",
        capability_ids=["Public Speaking", "System Architecture"],
        verification_requirement="SIMPLE_CONFIRMATION"
    )

    action = await execution_engine.create_user_action(person_id, req)
    assert action.title == req.title
    assert action.source == "USER_CREATED"
    assert action.status == "READY"
    assert "Public Speaking" in action.capability_ids

    # Verify action persists in store
    retrieved = await execution_engine.store.get_action(person_id, action.action_id)
    assert retrieved is not None
    assert retrieved["title"] == req.title

@pytest.mark.asyncio
async def test_execution_api_routes():
    from fastapi.testclient import TestClient
    from backend.main import app

    client = TestClient(app)
    headers = {"x-person-id": "test-runner-alex"}

    # 1. Get Daily Plan
    res = client.get("/api/execution/daily", headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert "person_id" in data
    assert "why_it_matters" in data

    # 2. Create User Action via API
    create_res = client.post("/api/execution/actions", headers=headers, json={
        "title": "Build Custom PyTorch Data Pipeline",
        "action_type": "PROJECT",
        "priority": "NOW"
    })
    assert create_res.status_code == 200
    action_data = create_res.json()
    action_id = action_data["action_id"]

    # 3. Start Action
    start_res = client.post(f"/api/execution/actions/{action_id}/start", headers=headers)
    assert start_res.status_code == 200
    assert start_res.json()["status"] == "IN_PROGRESS"

    # 4. Reschedule Action
    resched_res = client.post(f"/api/execution/actions/{action_id}/reschedule", headers=headers, json={
        "new_due_at": "2026-10-01T00:00:00Z",
        "reason": "Prioritizing work commitments."
    })
    assert resched_res.status_code == 200
    assert len(resched_res.json()["reschedule_history"]) >= 1

    # 5. Complete Action
    comp_res = client.post(f"/api/execution/actions/{action_id}/complete", headers=headers, json={
        "outcome": "COMPLETED_SUCCESSFULLY"
    })
    assert comp_res.status_code == 200
    assert comp_res.json()["status"] == "COMPLETED"

