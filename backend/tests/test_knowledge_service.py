import pytest
from backend.services.knowledge import KnowledgeService
from backend.core.schemas import KnowledgeResponse

@pytest.mark.asyncio
async def test_knowledge_service_health():
    service = KnowledgeService()
    status = await service.get_health_status()
    
    assert "esco" in status
    assert "nco" in status
    assert "firestore_cache" in status

@pytest.mark.asyncio
async def test_knowledge_service_search_graceful_fallback():
    service = KnowledgeService()
    # Ensure it doesn't crash on invalid queries or when external APIs are unavailable
    response = await service.search_occupations("test query", limit=1)
    
    assert isinstance(response, KnowledgeResponse)
    assert hasattr(response, "results")
    assert hasattr(response, "sources")
    assert hasattr(response, "confidence")
    assert response.confidence in ["source-backed", "no-results"]
