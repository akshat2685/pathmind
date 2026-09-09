from typing import Dict, Any, List, Optional
from datetime import datetime, timezone, timedelta
from backend.core.event_schemas import EventRecord
from backend.services.store import FirestoreStore

class EventBusService:
    """
    Event Ingestion & Deduplication Bus for PATHMIND Proactive Intelligence.
    Ensures real state changes are captured with structured provenance,
    while suppressing redundant duplicate triggers within a deterministic cooldown window.
    """
    def __init__(self, store: Optional[FirestoreStore] = None):
        self.store = store or FirestoreStore()
        self.cooldown_seconds = 3600  # 1 hour cooldown for duplicate event types on same entity

    async def publish_event(
        self,
        person_id: str,
        event_type: str,
        source: str = "SYSTEM_STATE_DETECTOR",
        source_reference: Optional[str] = None,
        entity_type: Optional[str] = None,
        entity_id: Optional[str] = None,
        importance: str = "RELEVANT",
        metadata: Optional[Dict[str, Any]] = None
    ) -> EventRecord:
        # 1. Deduplication check
        recent_events = await self.store.get_event_records(person_id, event_type=event_type)
        is_duplicate = False
        now_dt = datetime.now(timezone.utc)

        for e in recent_events[:5]:
            if e.get("entity_id") == entity_id and e.get("event_type") == event_type:
                occ_str = e.get("occurred_at", "")
                try:
                    occ_dt = datetime.fromisoformat(occ_str)
                    if (now_dt - occ_dt).total_seconds() < self.cooldown_seconds:
                        is_duplicate = True
                        break
                except Exception:
                    pass

        event = EventRecord(
            person_id=person_id,
            event_type=event_type,
            source=source,
            source_reference=source_reference,
            entity_type=entity_type,
            entity_id=entity_id,
            importance=importance,
            processed_state="DEDUPLICATED" if is_duplicate else "PENDING",
            metadata=metadata or {}
        )

        await self.store.save_event_record(person_id, event.model_dump())
        return event

    async def get_recent_events(
        self,
        person_id: str,
        event_type: Optional[str] = None
    ) -> List[EventRecord]:
        raw = await self.store.get_event_records(person_id, event_type=event_type)
        return [EventRecord(**e) for e in raw]
