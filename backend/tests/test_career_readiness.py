import pytest
import asyncio
from backend.services.career_readiness_engine import CareerReadinessEngine
from backend.services.opportunity_service import OpportunityService
from backend.services.store import FirestoreStore
from backend.core.career_schemas import UniversalCareerProfile, ProjectItem, ExperienceItem, EducationItem

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
async def test_universal_career_profile_and_target_goal(career_engine, store):
    person_id = "test-scholar-universal-profile"
    
    # 1. Canonical Profile
    profile = await career_engine.get_or_create_canonical_profile(person_id, current_state_type="college_student")
    assert profile.person_id == person_id
    assert len(profile.skills) >= 3
    assert len(profile.education) >= 1
    assert len(profile.projects) >= 1

    # 2. Target Goal with Versioning
    goal = await career_engine.get_or_create_career_goal(person_id, "Applied Machine Learning Systems Engineer")
    assert goal.person_id == person_id
    assert goal.target_role == "Applied Machine Learning Systems Engineer"
    assert goal.version >= 1
    assert goal.priority == "HIGH"

@pytest.mark.asyncio
async def test_career_requirement_graph_and_gaps(career_engine):
    person_id = "test-scholar-requirement-graph"
    report = await career_engine.generate_career_readiness_report(person_id, current_state_type="college_student")
    
    assert report.person_id == person_id
    assert report.requirement_graph is not None
    assert len(report.requirement_graph.core_skills) >= 3
    assert len(report.requirement_graph.project_evidence_requirements) >= 1
    
    assert len(report.categorized_gaps) >= 3
    gap_types = {g.gap_type for g in report.categorized_gaps}
    assert "SKILL" in gap_types
    assert "EXPERIENCE" in gap_types
    assert "EVIDENCE" in gap_types

@pytest.mark.asyncio
async def test_transferable_skills_for_switchers_and_students(career_engine):
    person_mech = "test-mech-switcher"
    profile_mech = await career_engine.get_or_create_canonical_profile(person_mech, current_state_type="mechanical_engineer")
    
    analysis_mech = career_engine.analyze_transferable_skills(profile_mech, "Machine Learning Engineer")
    assert len(analysis_mech.already_have) >= 3
    assert len(analysis_mech.can_transfer) >= 2
    assert len(analysis_mech.need_to_develop) >= 2
    assert "transfer directly" in analysis_mech.analysis_summary.lower()

    person_web = "test-web-switcher"
    profile_web = await career_engine.get_or_create_canonical_profile(person_web, current_state_type="frontend_developer")
    analysis_web = career_engine.analyze_transferable_skills(profile_web, "Machine Learning Engineer")
    assert len(analysis_web.can_transfer) >= 2
    assert "API Integration" in analysis_web.can_transfer[0] or "Schema Contracts" in analysis_web.can_transfer[0]

@pytest.mark.asyncio
async def test_credential_agent_decision_logic(career_engine):
    creds = career_engine.credential_agent.evaluate_credentials("Machine Learning Engineer")
    assert len(creds) >= 2
    
    for c in creds:
        assert c.classification in ["MANDATORY", "STRONGLY_USEFUL", "OPTIONAL", "LOW_VALUE", "NOT_RELEVANT"]
        assert c.official_url.startswith("https://")
        assert len(c.decision_rationale) > 5
        assert "git" in c.strategic_advice.lower() or "repository" in c.strategic_advice.lower() or "project" in c.strategic_advice.lower()

@pytest.mark.asyncio
async def test_experience_gap_engine_and_roadmap_linkage(career_engine):
    profile = await career_engine.get_or_create_canonical_profile("test-exp-person")
    graph = career_engine.build_requirement_graph("Applied Machine Learning Systems Engineer", profile.skills)
    
    exp_gaps = career_engine.analyze_experience_gaps(profile, "Applied Machine Learning Systems Engineer", graph)
    assert len(exp_gaps) >= 2
    for exp in exp_gaps:
        assert exp.experience_type in ["PROJECT", "INTERNSHIP", "RESEARCH", "FREELANCE", "OPEN_SOURCE", "LEADERSHIP", "INTERNAL_EXPERIENCE"]
        assert exp.associated_roadmap_stage is not None
        assert len(exp.evidence_to_prove) > 10

@pytest.mark.asyncio
async def test_career_checkpoint_recording_and_history(career_engine, store):
    person_id = "test-scholar-checkpoint"
    checkpoint = await career_engine.record_career_checkpoint(person_id)
    
    assert checkpoint.person_id == person_id
    assert "DEVELOPING" in checkpoint.progress or "FOUNDATIONAL" in checkpoint.progress or "INTERNSHIP" in checkpoint.progress
    assert len(checkpoint.skills_gained) >= 1
    assert len(checkpoint.next_best_action) > 10
    
    history = await store.get_career_checkpoints(person_id)
    assert len(history) >= 1
    assert history[0]["person_id"] == person_id

@pytest.mark.asyncio
async def test_career_data_person_isolation(career_engine, store):
    person_a = "career-alice-iso"
    person_b = "career-bob-iso"
    
    profile_a = await career_engine.get_or_create_canonical_profile(person_a, "mechanical_engineer")
    profile_b = await career_engine.get_or_create_canonical_profile(person_b, "college_student")
    
    assert "Mechanical" in profile_a.current_role
    assert "Secondary" in profile_b.current_role or "Student" in profile_b.current_role
    
    stored_a = await store.get_career_profile(person_a)
    stored_b = await store.get_career_profile(person_b)
    assert stored_a["current_state_type"] == "mechanical_engineer"
    assert stored_b["current_state_type"] == "college_student"
