import pytest
import asyncio
from backend.services.career_readiness_engine import CareerReadinessEngine
from backend.services.opportunity_service import OpportunityService
from backend.services.store import FirestoreStore

@pytest.fixture
def career_engine():
    return CareerReadinessEngine()

@pytest.fixture
def opp_service():
    return OpportunityService()

@pytest.fixture
def store():
    return FirestoreStore()

@pytest.mark.asyncio
async def test_career_goal_creation_and_persistence(career_engine, store):
    person_id = "test-scholar-career-goal"
    goal = await career_engine.get_or_create_career_goal(person_id, "Applied Machine Learning Systems Engineer")
    
    assert goal.person_id == person_id
    assert goal.target_role == "Applied Machine Learning Systems Engineer"
    assert goal.priority == "HIGH"
    
    saved_goal = await store.get_career_goal(person_id)
    assert saved_goal is not None
    assert saved_goal.get("target_role") == "Applied Machine Learning Systems Engineer"

@pytest.mark.asyncio
async def test_career_readiness_gaps_and_state(career_engine):
    person_id = "test-scholar-readiness-gaps"
    report = await career_engine.generate_career_readiness_report(person_id, current_state="college_student")
    
    assert report.person_id == person_id
    assert report.readiness_state == "DEVELOPING"
    assert "DEVELOPING" in report.readiness_explanation
    assert len(report.categorized_gaps) >= 4
    
    gap_types = {g.gap_type for g in report.categorized_gaps}
    assert "SKILL_GAP" in gap_types
    assert "EXPERIENCE_GAP" in gap_types
    assert "EVIDENCE_GAP" in gap_types
    assert "CREDENTIAL_GAP" in gap_types

@pytest.mark.asyncio
async def test_transferable_skills_for_career_switchers(career_engine):
    # Test for Mechanical Engineer career switcher
    analysis_mech = career_engine.analyze_transferable_skills(
        current_state="mechanical_engineer",
        current_skills=["Calculus", "Linear Algebra", "MATLAB", "Physics"],
        target_role="Data Engineer"
    )
    assert len(analysis_mech.already_have) >= 3
    assert len(analysis_mech.can_reuse) >= 2
    assert len(analysis_mech.need_to_build) >= 2
    assert "transfer directly" in analysis_mech.analysis_summary.lower()

    # Test for Frontend Developer career switcher
    analysis_fe = career_engine.analyze_transferable_skills(
        current_state="frontend_developer",
        current_skills=["JavaScript", "TypeScript", "React", "REST APIs"],
        target_role="Machine Learning Engineer"
    )
    assert "API Integration" in analysis_fe.can_reuse or "Client-Server Data Flow" in analysis_fe.can_reuse

@pytest.mark.asyncio
async def test_strategic_credential_classification(career_engine):
    creds = career_engine.analyze_credentials_strategy("Machine Learning Engineer")
    assert len(creds) >= 2
    
    for c in creds:
        assert c.classification in ["MANDATORY", "STRONGLY_USEFUL", "OPTIONAL", "LOW_VALUE", "NOT_RELEVANT"]
        assert c.official_url.startswith("https://")
        assert "git" in c.strategic_advice.lower() or "repository" in c.strategic_advice.lower() or "project" in c.strategic_advice.lower()

@pytest.mark.asyncio
async def test_accountability_agent_mentor_behavior(career_engine):
    person_id = "test-scholar-mentor"
    
    # Completed stage -> ON_TRACK
    status_on_track = career_engine.evaluate_accountability(person_id, completed_stages=1, weekly_hours=10)
    assert status_on_track.status == "ON_TRACK"
    assert "on schedule" in status_on_track.mentor_observation.lower()

    # Incomplete stage -> AT_RISK with supportive adjustment
    status_at_risk = career_engine.evaluate_accountability(person_id, completed_stages=0, weekly_hours=10)
    assert status_at_risk.status == "AT_RISK"
    assert status_at_risk.suggested_adjustment is not None
    assert "smaller" in status_at_risk.mentor_observation.lower() or "bite-sized" in status_at_risk.suggested_adjustment.lower()

@pytest.mark.asyncio
async def test_opportunity_matching_and_apply_urls(opp_service):
    matched = opp_service.match_opportunities_for_person(
        skills_held=["Python", "Linear Algebra", "Pytest", "Git"],
        target_role="Machine Learning Engineer",
        readiness_state="DEVELOPING"
    )
    assert len(matched) >= 2
    
    for opp in matched:
        assert opp.fit_level in ["HIGH", "MEDIUM", "LOW"]
        assert len(opp.fit_reasons) >= 1
        assert len(opp.missing_requirements) >= 1
        assert opp.apply_url.startswith("https://")

@pytest.mark.asyncio
async def test_tailored_resume_fact_integrity_and_ats(career_engine):
    person_id = "test-scholar-resume-integrity"
    verified_skills = ["Python 3.12", "Pytest", "Linear Algebra", "Pydantic", "Git"]
    
    resume = career_engine.generate_tailored_resume(
        person_id=person_id,
        target_role="Applied Machine Learning Systems Engineer",
        verified_skills=verified_skills,
        projects=[]
    )
    
    assert resume.person_id == person_id
    assert resume.ats_match_score >= 80
    assert "Python" in resume.ats_matched_keywords
    assert len(resume.ats_missing_keywords) >= 1
    assert len(resume.tailored_projects) >= 1
    
    # Verify provenance grounding
    for proj in resume.tailored_projects:
        assert "provenance" in proj
        assert "Verified" in proj["provenance"]

@pytest.mark.asyncio
async def test_career_readiness_cross_person_isolation(store):
    person_a = "career-alice-isolation"
    person_b = "career-bob-isolation"
    
    goal_a = {"goal_id": "goal_a_private", "person_id": person_a, "target_role": "Quantum Cryptography Lead"}
    await store.save_career_goal(person_a, goal_a)
    
    goal_b = await store.get_career_goal(person_b)
    assert goal_b is None or goal_b.get("target_role") != "Quantum Cryptography Lead"
