"""
Longitudinal Memory & Second Brain Service for PATHMIND College Engineering MVP.
Maintains short-term session context and persistent long-term learning signals
(stable preferences, recurring misconceptions, observed study habits).
Strictly isolated by authenticated UID. Never fabricates memories.
"""

from typing import List, Dict, Any, Optional
import uuid
from datetime import datetime, timezone
from backend.core.college_schemas import (
    CollegeShortMemory,
    CollegeLongMemory,
    LearningSignal
)
from backend.services.store import FirestoreStore

class CollegeMemoryService:
    def __init__(self, store: Optional[FirestoreStore] = None):
        self.store = store or FirestoreStore()

    async def record_short_term_context(
        self,
        uid: str,
        content: str,
        session_id: Optional[str] = None,
        conversation_id: Optional[str] = None,
        topic: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> CollegeShortMemory:
        """Stores immediate working context for active study session."""
        mem = CollegeShortMemory(
            memory_id=str(uuid.uuid4()),
            user_id=uid,
            session_id=session_id,
            conversation_id=conversation_id,
            content=content,
            topic=topic,
            metadata=metadata or {}
        )
        await self.store.save_college_short_memory(uid, mem.model_dump(mode="json"))
        return mem

    async def get_short_term_memories(self, uid: str) -> List[CollegeShortMemory]:
        raw = await self.store.get_college_short_memories(uid)
        return [CollegeShortMemory(**m) for m in raw]

    async def record_long_term_memory(
        self,
        uid: str,
        content: str,
        title: str,
        memory_type: str = "EPISODIC",
        nature: str = "EXPERIENCE",
        source_type: str = "OBSERVED_BEHAVIOR",
        confidence: str = "HIGH",
        importance: str = "MEDIUM",
        related_subject: Optional[str] = None,
        related_topic: Optional[str] = None
    ) -> CollegeLongMemory:
        """Stores persistent longitudinal learning signals and verified milestones."""
        mem = CollegeLongMemory(
            memory_id=str(uuid.uuid4()),
            user_id=uid,
            title=title,
            memory_type=memory_type,
            nature=nature,
            content=content,
            source_type=source_type,
            confidence=confidence,
            importance=importance,
            related_subject=related_subject,
            related_topic=related_topic
        )
        await self.store.save_college_long_memory(uid, mem.model_dump(mode="json"))
        return mem

    async def supersede_long_term_memory(
        self,
        uid: str,
        old_memory_id: str,
        new_content: str,
        new_title: str
    ) -> CollegeLongMemory:
        """Marks an old memory as SUPERSEDED and creates a new CURRENT memory representing updated reality."""
        # Create new memory first
        new_mem = await self.record_long_term_memory(
            uid=uid,
            title=new_title,
            content=new_content,
            memory_type="EPISODIC",
            source_type="OBSERVED_BEHAVIOR",
            confidence="HIGH"
        )
        # Update old memory to supersede it
        await self.store.update_long_memory_status(
            uid=uid, 
            memory_id=old_memory_id, 
            status="SUPERSEDED",
            supersedes_id=new_mem.memory_id
        )
        return new_mem

    async def get_long_term_memories(self, uid: str) -> List[CollegeLongMemory]:
        raw = await self.store.get_college_long_memories(uid)
        return [CollegeLongMemory(**m) for m in raw]

    async def record_learning_signal(
        self,
        uid: str,
        signal_type: str,
        description: str,
        recommended_intervention: str,
        subject_id: Optional[str] = None,
        topic_id: Optional[str] = None,
        confidence: float = 0.88
    ) -> LearningSignal:
        """Catalogues an actionable pedagogical insight (e.g. repeated error pattern)."""
        signal = LearningSignal(
            signal_id=f"sig_{uuid.uuid4().hex[:6]}",
            user_id=uid,
            signal_type=signal_type,
            subject_id=subject_id,
            topic_id=topic_id,
            description=description,
            recommended_intervention=recommended_intervention,
            confidence=confidence
        )
        await self.store.save_learning_signal(uid, signal.model_dump(mode="json"))
        return signal

    async def get_learning_signals(self, uid: str) -> List[LearningSignal]:
        raw = await self.store.get_learning_signals(uid)
        return [LearningSignal(**s) for s in raw]
