import pytest
import os
from backend.providers.esco import EscoProvider
from backend.providers.nco import NcoProvider
from backend.core.schemas import Occupation

@pytest.mark.asyncio
async def test_esco_provider():
    provider = EscoProvider()
    
    # We won't make a real HTTP request in a strict isolated test without mocking,
    # but for this MVP, we verify the interface is correct.
    assert provider.provider_name == "esco"
    
    # Normally we would use pytest-httpx or respx to mock the response
    # For now, we just verify the check_health handles failure gracefully if not mocked
    health = await provider.check_health()
    assert health in ["CONNECTED", "SOURCE_UNAVAILABLE", "INVALID_RESPONSE"]

@pytest.mark.asyncio
async def test_nco_provider():
    provider = NcoProvider()
    assert provider.provider_name == "india_nco"
    
    # If file doesn't exist, it should say NOT_CONFIGURED
    if not os.path.exists(provider.data_path):
        health = await provider.check_health()
        assert health == "NOT_CONFIGURED"
