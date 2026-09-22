import logging
from typing import List, Dict, Any, Optional
from backend.services.college_memory_service import CollegeMemoryService
from backend.core.college_schemas import CollegeLongMemory

logger = logging.getLogger(__name__)

class ProactiveMemoryService:
    def __init__(self, memory_service: Optional[CollegeMemoryService] = None, store=None):
        if memory_service:
            self.memory_service = memory_service
        else:
            from backend.services.college_memory_service import CollegeMemoryService
            self.memory_service = CollegeMemoryService(store=store)

    async def retrieve_relevant_memories(self, uid: str, query: str) -> List[Dict[str, Any]]:
        """
        Agent Tool: Retrieves relevant long-term memories for a user given a query.
        """
        # MVP: fetch all active long-term memories and filter by simple keyword match
        mems = await self.memory_service.get_long_term_memories(uid)
        active_mems = [m for m in mems if m.status == "CURRENT"]
        
        # Simple relevance: check if any query word is in the content or title
        query_words = set(query.lower().split())
        relevant = []
        for mem in active_mems:
            content_words = set(f"{mem.title} {mem.content}".lower().split())
            if query_words.intersection(content_words):
                relevant.append(mem)
        
        # Fallback to all if no strong match found
        if not relevant:
            relevant = active_mems

        return [m.model_dump(mode="json") for m in relevant[:5]]

    async def promote_to_long_term_memory(
        self, 
        uid: str, 
        title: str, 
        content: str, 
        nature: str = "EXPERIENCE"
    ) -> Dict[str, Any]:
        """
        Agent Tool: Promotes a new insight or preference to long-term memory.
        """
        mem = await self.memory_service.record_long_term_memory(
            uid=uid,
            title=title,
            content=content,
            nature=nature,
            source_type="AGENT_INFERENCE",
            confidence="HIGH",
            importance="MEDIUM"
        )
        return mem.model_dump(mode="json")

    async def supersede_memory(
        self, 
        uid: str, 
        old_memory_id: str, 
        new_title: str, 
        new_content: str
    ) -> Dict[str, Any]:
        """
        Agent Tool: Replaces an outdated memory with a new current memory.
        """
        mem = await self.memory_service.supersede_long_term_memory(
            uid=uid,
            old_memory_id=old_memory_id,
            new_title=new_title,
            new_content=new_content
        )
        return mem.model_dump(mode="json")

    async def get_proactive_memory_context(self, uid: str = None, person_id: str = None, current_task: str = None, task_type: str = None, current_goal: str = None) -> Dict[str, Any]:
        """
        Retrieves proactive context for the Orchestrator before hitting the LLM.
        """
        actual_uid = uid or person_id
        if not actual_uid:
            return {"retrieved_memories": [], "status": "NO_RELEVANT_MEMORY"}
            
        task_query = current_task or task_type or current_goal or "general context"
        memories = await self.retrieve_relevant_memories(actual_uid, task_query)
        return {
            "retrieved_memories": memories,
            "status": "ACTIVE_RECALL" if memories else "NO_RELEVANT_MEMORY"
        }
