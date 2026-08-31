from typing import Dict, Any
from adk import tool
from backend.services.knowledge import KnowledgeService
import json

knowledge_service = KnowledgeService()

@tool
async def search_occupations_tool(query: str, limit: int = 5) -> str:
    """
    Search for occupations across configured knowledge providers (e.g. ESCO, NCO).
    Returns structured data with provenance.
    
    Args:
        query: The search term (e.g. "software engineer")
        limit: Maximum number of results to return
    """
    response = await knowledge_service.search_occupations(query=query, limit=limit)
    return response.model_dump_json(indent=2)
