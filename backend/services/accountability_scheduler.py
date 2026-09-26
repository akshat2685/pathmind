import logging
from typing import Dict, Any, List, Optional

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from backend.services.store import FirestoreStore
from backend.services.proactive_intervention_engine import ProactiveInterventionEngine

logger = logging.getLogger("pathmind.accountability_scheduler")


class AccountabilityScheduler:
    """
    Background accountability sweep for PATHMIND (spec §15).

    Every `interval_hours` (default 6), iterates all persons with an active
    roadmap and runs the proactive intervention check for each — turning the
    previously on-demand-only ProactiveInterventionEngine into a real
    longitudinal accountability loop:

      "You planned this for Sunday and it is incomplete."
      "You are two tasks behind."

    Idempotency: interventions are generated through
    generate_interventions_deduplicated(), which retires any duplicate of a
    recent live intervention instead of stacking identical nudges.

    Failure semantics: start() refuses to start when the datastore is
    unreachable (raises loudly — never silently skips). A per-person failure
    during a sweep is recorded in the sweep report and does not abort the
    remaining persons.
    """

    def __init__(
        self,
        store: Optional[FirestoreStore] = None,
        engine: Optional[ProactiveInterventionEngine] = None,
        interval_hours: float = 6.0,
    ):
        self.store = store or FirestoreStore()
        self.engine = engine or ProactiveInterventionEngine(store=self.store)
        self.interval_hours = interval_hours
        self.scheduler = AsyncIOScheduler()
        self.scheduler.add_job(
            self.run_accountability_sweep,
            "interval",
            hours=interval_hours,
            id="accountability_sweep",
            name="PATHMIND accountability sweep",
            max_instances=1,      # never overlap two sweeps
            coalesce=True,        # if a run is missed, run once not N times
            misfire_grace_time=1800,
        )

    async def start(self) -> None:
        """
        Starts the scheduler. Fails loudly if the datastore is unreachable —
        an accountability loop that silently runs against nothing is worse
        than not running at all.
        """
        health = await self.store.check_health()
        if health == "CONNECTED":
            logger.info("Datastore CONNECTED — starting accountability scheduler (every %.1fh).", self.interval_hours)
        elif health == "IN_MEMORY_ACTIVE":
            logger.warning(
                "Datastore is IN_MEMORY_ACTIVE (no persistent backend configured). "
                "Accountability scheduler starting in volatile dev mode — sweeps will "
                "not survive restarts."
            )
        else:
            raise RuntimeError(
                f"ACCOUNTABILITY_SCHEDULER_DB_UNREACHABLE: datastore health={health}. "
                "Refusing to start the accountability scheduler."
            )
        self.scheduler.start()

    async def shutdown(self) -> None:
        self.scheduler.shutdown(wait=False)
        logger.info("Accountability scheduler shut down.")

    async def run_accountability_sweep(self) -> Dict[str, Any]:
        """
        One full sweep: check every person with an active roadmap.
        Returns a report dict; per-person errors are captured, not raised.
        """
        person_ids: List[str] = await self.store.list_person_ids_with_active_roadmaps()
        report: Dict[str, Any] = {
            "persons_checked": 0,
            "interventions_generated": 0,  # after scheduler-level dedup
            "errors": [],
        }
        for person_id in person_ids:
            try:
                async with self.store.get_person_lock(person_id):
                    generated = await self.engine.generate_interventions_deduplicated(
                        person_id, window_hours=self.interval_hours
                    )
                report["persons_checked"] += 1
                report["interventions_generated"] += len(generated)
            except Exception as e:
                logger.exception("Accountability sweep failed for person %s", person_id)
                report["errors"].append({"person_id": person_id, "error": str(e)})
        logger.info(
            "Accountability sweep complete: %d persons checked, %d interventions generated, %d errors.",
            report["persons_checked"], report["interventions_generated"], len(report["errors"]),
        )
        return report
