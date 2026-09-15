import pytest
from datetime import datetime, timezone

from backend.core.career_schemas import UniversalCareerProfile, CanonicalGoal, ProjectItem, ExperienceItem, EducationItem
from backend.core.opportunity_schemas import CanonicalOpportunity
from backend.services.resume_generation_service import ResumeGenerationService
from backend.services.resume_validator import ResumeFactValidator

@pytest.fixture
def service():
    return ResumeGenerationService()

@pytest.fixture
def empty_profile():
    return UniversalCareerProfile(
        person_id="test-person",
        current_role="Unknown",
        current_state_type="Unknown",
        education=[],
        experience=[],
        skills=[],
        projects=[]
    )

def test_resume_generation_strictly_factual(service, empty_profile):
    """Test 4: No verified experience -> Resume MUST NOT invent experience."""
    goal = CanonicalGoal(id="g1", person_id="test-person", target_role="Software Engineer", domain="Software Engineering")
    version = service.generate_fact_grounded_resume(empty_profile, goal)
    
    assert len(version.content["experience"]) == 0
    assert len(version.content["projects"]) == 0
    assert len(version.content["skills"]) == 0
    assert "Software Engineer" in version.content["summary"]

def test_cricket_domain_no_software_leakage(service):
    """Adversarial Test 1: Cricketer should not have Python or Software Engineer leaked."""
    profile = UniversalCareerProfile(
        person_id="cricketer-01",
        current_role="Athlete",
        current_state_type="professional",
        education=[],
        experience=[
            ExperienceItem(role="Batsman", organization="District Cricket Club", duration="2020-2023", description="Played 50 matches.")
        ],
        skills=["Batting", "Fielding"],
        projects=[]
    )
    goal = CanonicalGoal(id="g2", person_id="cricketer-01", target_role="Professional Cricketer", domain="Cricket")
    
    version = service.generate_fact_grounded_resume(profile, goal)
    resume_str = str(version.content).lower()
    
    assert "python" not in resume_str
    assert "github" not in resume_str
    assert "software engineer" not in resume_str
    assert "batsman" in resume_str

def test_law_domain_no_software_leakage(service):
    """Adversarial Test 2: Lawyer should not have software projects."""
    profile = UniversalCareerProfile(
        person_id="lawyer-01",
        current_role="Law Student",
        current_state_type="student",
        education=[],
        experience=[],
        skills=["Legal Research", "Writing"],
        projects=[
            ProjectItem(title="Moot Court Brief", technologies=["Word"], description="Wrote a legal brief.", provenance="Verified Document")
        ]
    )
    goal = CanonicalGoal(id="g3", person_id="lawyer-01", target_role="Lawyer", domain="Law")
    
    version = service.generate_fact_grounded_resume(profile, goal)
    resume_str = str(version.content).lower()
    
    assert "github" not in resume_str
    assert "coding" not in resume_str
    assert "moot court brief" in resume_str

def test_fabrication_attack_tests(service, empty_profile):
    """Fabrication Attack Tests: Ensure we cannot inject unverified facts via target or goal."""
    # Attempt to inject via target_role
    goal = CanonicalGoal(id="g4", person_id="test", target_role="I led a 20-person engineering team.", domain="Software")
    version = service.generate_fact_grounded_resume(empty_profile, goal)
    
    # It might be in the summary as the target role, but it must NOT be in experience
    assert len(version.content["experience"]) == 0
    assert len(version.content["projects"]) == 0

def test_opportunity_integration_test(service, empty_profile):
    """Opportunity Integration Test: Match requirements correctly."""
    empty_profile.skills = ["Python", "FastAPI"]
    goal = CanonicalGoal(id="g5", person_id="test", target_role="Backend Engineer", domain="Software")
    
    class MockOpp:
        id = "opp_1"
        requirements = ["Python", "Docker", "Kubernetes"]
    
    version = service.generate_fact_grounded_resume(empty_profile, goal, MockOpp())
    ats = version.content["ats_analysis"]
    
    assert "Python" in ats["matched"]
    assert "Docker" in ats["missing"]
    assert "Kubernetes" in ats["missing"]

def test_versioning_test(service, empty_profile):
    """Versioning Test: Generate v1, then change opportunity and generate v2."""
    goal = CanonicalGoal(id="g6", person_id="test", target_role="Engineer", domain="Software")
    
    # V1
    v1 = service.generate_fact_grounded_resume(empty_profile, goal)
    
    class MockOpp:
        id = "opp_2"
        requirements = ["AWS"]
    
    # V2
    v2 = service.generate_fact_grounded_resume(empty_profile, goal, MockOpp())
    
    assert v1.id != v2.id
    assert v1.opportunity_id is None
    assert v2.opportunity_id == "opp_2"
    # v1 must remain unchanged
    assert "ats_analysis" not in v1.content
    assert "ats_analysis" in v2.content
