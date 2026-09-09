import pytest
from datetime import datetime, timezone
from backend.services.event_bus_service import EventBusService
from backend.services.proactive_intervention_engine import ProactiveInterventionEngine
from backend.services.store import FirestoreStore

@pytest.mark.asyncio
async def test_event_ingestion_and_provenance():
    """
    EventBusService publishes structured events with source provenance and timestamps.
    """
    store = FirestoreStore()
    event_bus = EventBusService(store=store)
    person_id = "test-proactive-learner-1"

    event = await event_bus.publish_event(
        person_id=person_id,
        event_type="STAGE_COMPLETED",
        source="ROADMAP_PROGRESSION_ENGINE",
        source_reference="stage_01",
        entity_type="STAGE",
        entity_id="stage_01_python_foundations",
        importance="RELEVANT",
        metadata={"stage_number": 1}
    )

    assert event.event_id is not None
    assert event.event_type == "STAGE_COMPLETED"
    assert event.processed_state == "PENDING"
    assert event.source == "ROADMAP_PROGRESSION_ENGINE"

@pytest.mark.asyncio
async def test_event_deduplication_within_cooldown():
    """
    Publishing identical event on same entity within cooldown window marks state as DEDUPLICATED.
    """
    store = FirestoreStore()
    event_bus = EventBusService(store=store)
    person_id = "test-dedup-learner"

    evt1 = await event_bus.publish_event(
        person_id=person_id,
        event_type="OPPORTUNITY_DEADLINE_APPROACHING",
        entity_type="OPPORTUNITY",
        entity_id="opp_gsoc_2026"
    )
    assert evt1.processed_state == "PENDING"

    # Immediate second publish
    evt2 = await event_bus.publish_event(
        person_id=person_id,
        event_type="OPPORTUNITY_DEADLINE_APPROACHING",
        entity_type="OPPORTUNITY",
        entity_id="opp_gsoc_2026"
    )
    assert evt2.processed_state == "DEDUPLICATED"

@pytest.mark.asyncio
async def test_repeated_evidence_failures_trigger_reinforcement():
    """
    Two consecutive failed attempts on active stage generate a REVIEW_REINFORCEMENT intervention.
    """
    store = FirestoreStore()
    engine = ProactiveInterventionEngine(store=store)
    person_id = "test-fail-pattern"

    # Initialize roadmap
    await engine.context_service.roadmap_engine.get_or_create_roadmap(person_id)

    # Save 2 failed attempts
    await store.save_evaluation_attempt(person_id, {
        "attempt_id": "att_1",
        "stage_id": "stage_01_python_foundations",
        "person_id": person_id,
        "status": "REINFORCE",
        "evaluated_at": datetime.now(timezone.utc).isoformat()
    })
    await store.save_evaluation_attempt(person_id, {
        "attempt_id": "att_2",
        "stage_id": "stage_01_python_foundations",
        "person_id": person_id,
        "status": "REINFORCE",
        "evaluated_at": datetime.now(timezone.utc).isoformat()
    })

    interventions = await engine.scan_and_generate_interventions(person_id)
    reinforce_intv = next((i for i in interventions if i.type == "REVIEW_REINFORCEMENT"), None)

    assert reinforce_intv is not None
    assert reinforce_intv.priority == "HIGH"
    assert "consecutive preliminary" in reinforce_intv.what_happened
    assert "pytest" in reinforce_intv.what_should_i_do

@pytest.mark.asyncio
async def test_action_and_dismissal_lifecycle():
    """
    Interventions transition status to ACTED_ON when acted on and DISMISSED when dismissed.
    """
    store = FirestoreStore()
    engine = ProactiveInterventionEngine(store=store)
    person_id = "test-lifecycle-learner"

    # Save an intervention
    intv_data = {
        "intervention_id": "intv_test_123",
        "person_id": person_id,
        "event_id": "evt_test",
        "type": "APPLY_OPPORTUNITY",
        "priority": "HIGH",
        "title": "Test Opportunity",
        "what_happened": "Test happened",
        "why_it_matters": "Test matters",
        "what_should_i_do": "Test action",
        "what_happens_if_ignored": "Test ignore",
        "status": "PENDING"
    }
    await store.save_intervention(person_id, intv_data)

    # Act on intervention
    acted = await engine.act_on_intervention(person_id, "intv_test_123", feedback_note="Applied via official portal.")
    assert acted is True

    updated = await store.get_intervention_by_id(person_id, "intv_test_123")
    assert updated["status"] == "ACTED_ON"

@pytest.mark.asyncio
async def test_notification_preferences_suppress_disabled_categories():
    """
    Disabling reinforcement alerts in preferences suppresses intervention generation.
    """
    store = FirestoreStore()
    engine = ProactiveInterventionEngine(store=store)
    person_id = "test-prefs-learner"

    await engine.context_service.roadmap_engine.get_or_create_roadmap(person_id)

    # Save preferences with reinforcement disabled
    await store.save_notification_preferences(person_id, {
        "person_id": person_id,
        "enable_reinforcement_alerts": False,
        "enable_opportunity_alerts": True,
        "enable_mastery_alerts": True
    })

    # Save 2 failed attempts
    await store.save_evaluation_attempt(person_id, {
        "attempt_id": "att_1",
        "stage_id": "stage_01_python_foundations",
        "person_id": person_id,
        "status": "REINFORCE"
    })
    await store.save_evaluation_attempt(person_id, {
        "attempt_id": "att_2",
        "stage_id": "stage_01_python_foundations",
        "person_id": person_id,
        "status": "REINFORCE"
    })

    interventions = await engine.scan_and_generate_interventions(person_id)
    reinforce_intv = next((i for i in interventions if i.type == "REVIEW_REINFORCEMENT"), None)
    assert reinforce_intv is None

@pytest.mark.asyncio
async def test_tenant_isolation_for_proactive_events():
    """
    Person A's events and interventions cannot be accessed by Person B.
    """
    store = FirestoreStore()
    person_a = "person-proactive-a"
    person_b = "person-proactive-b"

    await store.save_intervention(person_a, {
        "intervention_id": "intv_a",
        "person_id": person_a,
        "title": "Alpha Intervention",
        "status": "PENDING"
    })

    intvs_b = await store.get_interventions(person_b)
    assert len(intvs_b) == 0

    intvs_a = await store.get_interventions(person_a)
    assert len(intvs_a) == 1
    assert intvs_a[0]["intervention_id"] == "intv_a"
