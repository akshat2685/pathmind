import pytest
from datetime import datetime, timezone
from backend.services.progress_analysis_service import ProgressAnalysisService
from backend.services.learner_evolution_agent import LearnerEvolutionAgent
from backend.services.store import FirestoreStore

@pytest.mark.asyncio
async def test_capability_evolution_and_progress_classification():
    """
    ProgressAnalysisService reconstructs capability trajectories and classifies progress accurately.
    """
    store = FirestoreStore()
    progress_service = ProgressAnalysisService(store=store)
    person_id = "test-longitudinal-learner-1"

    # Save skill profile
    await store.save_skill_mastery_profile(person_id, "Python Concurrency", {
        "skill_name": "Python Concurrency",
        "mastery_state": "APPLICATION",
        "is_regression_risk": False,
        "last_verified_at": datetime.now(timezone.utc).isoformat()
    })

    # Save 2 evidence artifacts
    await store.save_canonical_evidence(person_id, {
        "evidence_id": "ev_conc_1",
        "person_id": person_id,
        "title": "Async Task Pool",
        "associated_skills": ["Python Concurrency"],
        "created_at": "2026-08-15T10:00:00Z"
    })
    await store.save_canonical_evidence(person_id, {
        "evidence_id": "ev_conc_2",
        "person_id": person_id,
        "title": "Multiprocessing Pipeline",
        "associated_skills": ["Python Concurrency"],
        "created_at": "2026-08-28T14:00:00Z"
    })

    caps = await progress_service.reconstruct_capability_evolution(person_id)
    assert len(caps) >= 1
    conc_cap = next(c for c in caps if c.skill_name == "Python Concurrency")

    assert conc_cap.progress_classification == "IMPROVING"
    assert conc_cap.evidence_count == 2
    assert len(conc_cap.evidence_ids) == 2

@pytest.mark.asyncio
async def test_recurring_misconception_detection():
    """
    Two or more failed evaluation attempts on a concept trigger a RecurringMisconception signal.
    """
    store = FirestoreStore()
    progress_service = ProgressAnalysisService(store=store)
    person_id = "test-misconception-learner"

    # Save 2 failed attempts
    await store.save_evaluation_attempt(person_id, {
        "attempt_id": "att_fail_1",
        "stage_id": "stage_01_distributed_locks",
        "person_id": person_id,
        "status": "REINFORCE"
    })
    await store.save_evaluation_attempt(person_id, {
        "attempt_id": "att_fail_2",
        "stage_id": "stage_01_distributed_locks",
        "person_id": person_id,
        "status": "REINFORCE"
    })

    miscs = await progress_service.detect_recurring_misconceptions(person_id)
    assert len(miscs) >= 1
    lock_misc = next(m for m in miscs if m.concept_area == "stage_01_distributed_locks")

    assert lock_misc.occurrence_count == 2
    assert lock_misc.status == "ACTIVE"
    assert "parameterized test suites" in lock_misc.remediation_strategy

@pytest.mark.asyncio
async def test_learning_strategy_evaluation():
    """
    ProgressAnalysisService evaluates learning strategy effectiveness from real evaluation attempts.
    """
    store = FirestoreStore()
    progress_service = ProgressAnalysisService(store=store)
    person_id = "test-strategy-learner"

    # Save a successful pass
    await store.save_evaluation_attempt(person_id, {
        "attempt_id": "att_pass_1",
        "stage_id": "stage_01_algorithms",
        "person_id": person_id,
        "status": "PASS"
    })

    strats = await progress_service.evaluate_strategy_profiles(person_id)
    proj_strat = next(s for s in strats if s.strategy_dimension == "PROJECT_BASED")

    assert proj_strat.effectiveness_status == "SUPPORTED"
    assert proj_strat.successful_evaluations == 1

@pytest.mark.asyncio
async def test_temporal_queries_with_grounded_provenance():
    """
    LearnerEvolutionAgent answers temporal questions with exact timestamps and falls back cleanly.
    """
    store = FirestoreStore()
    agent = LearnerEvolutionAgent(store=store)
    person_id = "test-temporal-query-learner"

    # 1. Initialize roadmap & capability
    await agent.context_service.roadmap_engine.get_or_create_roadmap(person_id)
    await store.save_skill_mastery_profile(person_id, "Python", {
        "skill_name": "Python",
        "mastery_state": "APPLICATION",
        "last_verified_at": "2026-08-10T12:00:00Z"
    })
    await store.save_canonical_evidence(person_id, {
        "evidence_id": "ev_py_1",
        "person_id": person_id,
        "title": "Python AST Parser",
        "associated_skills": ["Python"],
        "created_at": "2026-08-10T12:00:00Z"
    })

    # Query existing skill
    res1 = await agent.answer_temporal_query(person_id, "When did I first learn Python?")
    assert res1.status == "ANSWERED"
    assert "2026-08-10" in res1.answer
    assert "ev_py_1" in res1.supporting_event_ids

    # Query unrecorded skill
    res2 = await agent.answer_temporal_query(person_id, "When did I study Quantum Computing?")
    assert res2.status == "INSUFFICIENT_HISTORY"

@pytest.mark.asyncio
async def test_progress_insight_dispute_lifecycle():
    """
    Learner can dispute an insight, updating its status to DISPUTED with reason.
    """
    store = FirestoreStore()
    agent = LearnerEvolutionAgent(store=store)
    person_id = "test-dispute-learner"

    # Save an insight
    ins_data = {
        "insight_id": "ins_test_123",
        "person_id": person_id,
        "type": "GROWTH_OBSERVATION",
        "claim": "Observed rapid growth in functional programming.",
        "status": "ACTIVE"
    }
    await store.save_progress_insight(person_id, ins_data)

    disputed = await agent.dispute_insight(
        person_id=person_id,
        insight_id="ins_test_123",
        dispute_reason="I have prior industry experience with functional programming."
    )
    assert disputed is True

    updated_ins = await store.get_progress_insight_by_id(person_id, "ins_test_123")
    assert updated_ins["status"] == "DISPUTED"
    assert "prior industry experience" in updated_ins["dispute_reason"]

@pytest.mark.asyncio
async def test_tenant_isolation_for_longitudinal_state():
    """
    Person A's longitudinal state and turning points cannot be accessed by Person B.
    """
    store = FirestoreStore()
    person_a = "person-longitudinal-a"
    person_b = "person-longitudinal-b"

    await store.save_turning_point(person_a, {
        "turning_point_id": "tp_a",
        "person_id": person_a,
        "title": "Alpha Breakthrough",
        "what_happened": "Major progress",
        "why_significant": "Significant",
        "what_changed_afterward": "Changed",
        "timestamp": datetime.now(timezone.utc).isoformat()
    })

    tps_b = await store.get_turning_points(person_b)
    assert len(tps_b) == 0

    tps_a = await store.get_turning_points(person_a)
    assert len(tps_a) == 1
    assert tps_a[0]["turning_point_id"] == "tp_a"
