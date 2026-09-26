"""
Tests for the accountability scheduler (spec §15):
6-hour sweeps over active roadmaps, idempotent intervention generation,
and loud failure when the datastore is unreachable.
"""
import pytest
from datetime import datetime, timezone, timedelta

from backend.services.store import FirestoreStore
from backend.services.proactive_intervention_engine import ProactiveInterventionEngine
from backend.services.accountability_scheduler import AccountabilityScheduler


@pytest.fixture
def clean_store():
    store = FirestoreStore()
    store._in_memory_persons.clear()
    return store


def _roadmap(pid: str):
    return {
        "roadmap_id": "rm1", "person_id": pid, "path_id": "p1",
        "target_outcome": "Robotics Engineer", "current_stage_id": "s1",
        "phases": [{"phase_id": "ph1", "title": "Foundations", "description": "d",
                    "stages": [{"stage_id": "s1", "phase_id": "ph1", "stage_number": 1,
                                "title": "Python Basics", "objective": "learn python",
                                "locked": False}]}],
    }


@pytest.mark.asyncio
async def test_sweep_generates_intervention_for_struggling_learner(requires_live_db, clean_store):
    pid = "sweep-learner"
    await clean_store.save_roadmap(pid, _roadmap(pid))
    await clean_store.save_evaluation_attempt(pid, {"stage_id": "s1", "status": "REINFORCE"})
    await clean_store.save_evaluation_attempt(pid, {"stage_id": "s1", "status": "REINFORCE"})

    sched = AccountabilityScheduler(store=clean_store)
    report = await sched.run_accountability_sweep()

    assert report["persons_checked"] == 1
    assert report["interventions_generated"] == 1
    assert report["errors"] == []
    live = [i for i in await clean_store.get_interventions(pid)
            if i.get("status") in ("PENDING", "SEEN")]
    assert len(live) == 1
    assert live[0]["type"] == "REVIEW_REINFORCEMENT"


@pytest.mark.asyncio
async def test_sweep_is_idempotent_across_runs(requires_live_db, clean_store):
    pid = "sweep-learner-2"
    await clean_store.save_roadmap(pid, _roadmap(pid))
    await clean_store.save_evaluation_attempt(pid, {"stage_id": "s1", "status": "REINFORCE"})
    await clean_store.save_evaluation_attempt(pid, {"stage_id": "s1", "status": "REINFORCE"})

    sched = AccountabilityScheduler(store=clean_store)
    first = await sched.run_accountability_sweep()
    second = await sched.run_accountability_sweep()

    assert first["interventions_generated"] == 1
    assert second["interventions_generated"] == 0  # no duplicate nudge
    live = [i for i in await clean_store.get_interventions(pid)
            if i.get("status") in ("PENDING", "SEEN")]
    assert len(live) == 1


@pytest.mark.asyncio
async def test_dedup_retires_duplicate_of_recent_live_intervention(requires_live_db, clean_store):
    pid = "sweep-learner-3"
    await clean_store.save_roadmap(pid, _roadmap(pid))
    await clean_store.save_evaluation_attempt(pid, {"stage_id": "s1", "status": "REINFORCE"})
    await clean_store.save_evaluation_attempt(pid, {"stage_id": "s1", "status": "REINFORCE"})
    two_h = (datetime.now(timezone.utc) - timedelta(hours=2)).isoformat()
    # Event 2h ago: bypasses the 1h event-bus cooldown, so the engine generates.
    await clean_store.save_event_record(pid, {"event_id": "e1", "event_type": "EVIDENCE_FAILED",
                                              "entity_id": "s1", "occurred_at": two_h,
                                              "processed_state": "PENDING"})
    # Live intervention 2h ago, same type+entity: within the 6h dedup window.
    await clean_store.save_intervention(pid, {"intervention_id": "intv_old", "person_id": pid,
                                              "type": "REVIEW_REINFORCEMENT",
                                              "related_entity_type": "STAGE",
                                              "related_entity_id": "s1",
                                              "status": "PENDING", "created_at": two_h,
                                              "title": "old"})

    engine = ProactiveInterventionEngine(store=clean_store)
    kept = await engine.generate_interventions_deduplicated(pid, window_hours=6)

    assert kept == []
    intvs = await clean_store.get_interventions(pid)
    live = [i for i in intvs if i.get("status") in ("PENDING", "SEEN")]
    retired = [i for i in intvs if i.get("status") == "DEDUPLICATED"]
    assert len(live) == 1 and live[0]["intervention_id"] == "intv_old"
    assert len(retired) == 1


@pytest.mark.asyncio
async def test_sweep_skips_persons_without_roadmaps(clean_store):
    await clean_store.save_roadmap("has-roadmap", _roadmap("has-roadmap"))
    # person without roadmap: only a memory, no sweep
    from backend.services.second_brain_service import SecondBrainService
    sb = SecondBrainService(store=clean_store)
    await sb.ingest_memory("no-roadmap", {"title": "x", "topic": "y"})

    ids = await clean_store.list_person_ids_with_active_roadmaps()
    assert ids == ["has-roadmap"]


@pytest.mark.asyncio
async def test_scheduler_start_fails_loudly_when_db_unreachable(requires_live_db, clean_store):
    class DeadStore(FirestoreStore):
        async def check_health(self):
            return "SOURCE_UNAVAILABLE"

    sched = AccountabilityScheduler(store=DeadStore())
    with pytest.raises(RuntimeError, match="ACCOUNTABILITY_SCHEDULER_DB_UNREACHABLE"):
        await sched.start()
    assert not sched.scheduler.running


@pytest.mark.asyncio
async def test_scheduler_job_runs_every_six_hours(requires_live_db, clean_store):
    sched = AccountabilityScheduler(store=clean_store, interval_hours=6)
    jobs = sched.scheduler.get_jobs()
    assert len(jobs) == 1
    assert jobs[0].id == "accountability_sweep"
    assert jobs[0].trigger.interval.total_seconds() == 6 * 3600
