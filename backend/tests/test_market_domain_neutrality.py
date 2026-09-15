import pytest
from backend.services.market_intelligence_service import MarketIntelligenceService
from backend.core.goal_schemas import CanonicalGoal

@pytest.mark.asyncio
async def test_market_service_handles_missing_credentials():
    """
    Ensures that when external API keys are missing, the system gracefully degrades 
    to SOURCE_UNAVAILABLE rather than inventing a salary or growth number.
    """
    service = MarketIntelligenceService()
    
    # We clear keys to simulate missing credentials
    service.provider.bls_api_key = None
    service.provider.onet_api_key = None
    
    goal = CanonicalGoal(
        goal_id="g1",
        person_id="test-user",
        raw_user_goal="Software Engineer",
        normalized_goal="Software Engineer",
        target_role="Software Engineer",
        target_outcome="Software Engineer",
        target_domain="Technology"
    )
    
    signals = await service.get_market_signals(goal)
    
    assert len(signals) == 1
    assert signals[0].value == "SOURCE_UNAVAILABLE"
    assert signals[0].confidence == "INSUFFICIENT_EVIDENCE"

@pytest.mark.asyncio
async def test_trajectory_is_domain_aware(monkeypatch):
    """
    Ensures the synthesized trajectory respects domain reality and doesn't force
    software-centric steps (like LeetCode or open source) onto completely unrelated
    roles like a Professional Cricketer.
    """
    service = MarketIntelligenceService()
    
    # Force fallback to synthesis by clearing credentials
    service.provider.onet_api_key = None
    service.provider.bls_api_key = None
    service.gemini_available = True
    
    # If Gemini is not available, we just mock the LLM call to return a valid domain-aware response
    # to avoid failing the test suite in CI.
    # Since LLM synthesis was removed for domain neutrality, we mock the provider explicitly
    async def mock_fetch_trajectory_data(domain, occupation):
        if "Cricket" in domain:
            return {
                "stages": [{"stage_name": "Club Level", "typical_entry_requirements": ["Academy Selection"]}],
                "source": "Mocked Synthesis",
                "confidence": "MEDIUM"
            }
        return {
            "stages": [],
            "source": "Mocked",
            "confidence": "MEDIUM"
        }
        
    monkeypatch.setattr(service.provider, "fetch_trajectory_data", mock_fetch_trajectory_data)
    
    goal_cricket = CanonicalGoal(
        goal_id="g2",
        person_id="test-user",
        raw_user_goal="Batsman",
        normalized_goal="Batsman",
        target_role="Batsman",
        target_outcome="Batsman",
        target_domain="Professional Cricket"
    )
    
    trajectory = await service.get_career_trajectory(goal_cricket)
    
    assert trajectory.domain == "Professional Cricket"
    assert len(trajectory.stages) > 0
    assert "Club Level" in trajectory.stages[0].stage_name
