import pytest
import asyncio
from backend.services.opportunity_matching_engine import OpportunityMatchingEngine
from backend.core.career_schemas import CanonicalGoal
from backend.core.opportunity_schemas import CanonicalOpportunity

# Mock structures
class MockStore:
    async def get_person_artifacts(self, person_id: str):
        return [
            {
                "analysis": {
                    "capability_mappings": [
                        {"capability_name": "batting", "status": "VERIFIED"},
                        {"capability_name": "python", "status": "VERIFIED"}
                    ]
                }
            }
        ]

class MockCareerEngine:
    async def get_or_create_canonical_profile(self, person_id: str):
        class Profile:
            skills = ["fielding", "fast bowling", "c++"]
            current_country = "India"
        return Profile()

    async def get_or_create_career_goal(self, person_id: str):
        return CanonicalGoal(
            person_id=person_id,
            target_role="Professional Cricketer",
            target_domain="Sports/Cricket"
        )

class MockProvider:
    def __init__(self, mock_opps):
        self.mock_opps = mock_opps
    async def fetch_opportunities(self, domain_filter=None, role_filter=None, geography=None):
        return self.mock_opps
    def get_provider_name(self): return "MockProvider"
    def is_connected(self): return True
    def get_status_code(self): return "OK"

@pytest.mark.asyncio
async def test_adversarial_opportunity_matching():
    cricket_opp = CanonicalOpportunity(
        title="Domestic Cricket League Trial",
        organization="BCCI",
        domain="Sports",
        location="Mumbai, India",
        requirements=["batting", "fielding", "fitness"]
    )
    software_opp = CanonicalOpportunity(
        title="Software Engineer",
        organization="Google",
        domain="Technology",
        location="Bangalore, India",
        requirements=["python", "c++", "system design"]
    )

    engine = OpportunityMatchingEngine(
        provider=MockProvider([cricket_opp, software_opp]),
        career_engine=MockCareerEngine(),
        store=MockStore()
    )

    matches = await engine.match_opportunities_for_person("user_1")

    # Both opportunities should be processed
    assert len(matches) == 2
    
    cricket_match = next(m for m in matches if m.opportunity.title == "Domestic Cricket League Trial")
    software_match = next(m for m in matches if m.opportunity.title == "Software Engineer")

    # Fit should be based on the goal (Professional Cricketer)
    # The title "Domestic Cricket League Trial" doesn't strictly contain "Professional Cricketer", but it does contain "Cricket" which is in target_domain "Sports/Cricket"
    # Actually my logic was:
    # if target_role.lower() in opp.title.lower() or target_domain.lower() in opp.title.lower():
    # Since "cricket" is in both, it might match. Let's see.

    assert cricket_match.readiness_status in ["READY", "PARTIALLY_READY"]
    assert software_match.readiness_status in ["READY", "PARTIALLY_READY"]

    assert len(cricket_match.requirement_matches) >= 2 # batting (verified), fielding (self-reported)
    assert len(cricket_match.requirement_gaps) == 1 # fitness

    assert len(software_match.requirement_matches) >= 2 # python (verified), c++ (self-reported)
    assert len(software_match.requirement_gaps) == 1 # system design
