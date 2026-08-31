from fastapi import APIRouter, Depends
from backend.services.knowledge import KnowledgeService

router = APIRouter(prefix="/api/v1/health", tags=["health"])
knowledge_service = KnowledgeService()

@router.get("/providers")
async def get_providers_health():
    """
    Developer-facing endpoint to check provider connectivity status.
    Returns the health of each registered provider.
    """
    status = await knowledge_service.get_health_status()
    return {"providers": status}

@router.get("/integration_test")
async def integration_test_query(query: str = "engineer"):
    """
    Integration test endpoint to verify the full flow:
    query -> KnowledgeService -> Provider -> Normalize -> Response
    """
    response = await knowledge_service.search_occupations(query=query, limit=2)
    return response.model_dump()
