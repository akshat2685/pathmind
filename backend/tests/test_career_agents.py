import pytest
from backend.core.career_schemas import (
    UniversalCareerProfile,
    EducationItem,
    ExperienceItem,
    ProjectItem,
    TargetOutcome,
    EvidencePortfolio,
    VerifiedOpportunity
)
from backend.services.career_agents import (
    CareerReadinessAgent,
    CredentialAgent,
    OpportunityAgent,
    ResumeAgent,
    AccountabilityAgent
)

@pytest.fixture
def profile():
    return UniversalCareerProfile(
        person_id="scholar-agent-test",
        current_role="Student Scholar",
        current_state_type="college_student",
        education=[
            EducationItem(
                degree="Senior Secondary (CBSE STEM)",
                field_of_study="Mathematics & Computer Science",
                institution="Central Board of Secondary Education",
                year="2026"
            )
        ],
        experience=[
            ExperienceItem(
                role="Technical Contributor",
                organization="PATHMIND Learning Program",
                duration="2026 – Present",
                description="Built data pipelines and test suites."
            )
        ],
        skills=["Python 3.12", "Pytest", "Linear Algebra", "Git", "Algorithms"],
        projects=[
            ProjectItem(
                title="Modular Data Parser & Stream Ingestion Pipeline",
                technologies=["Python", "Pytest", "Dataclasses"],
                description="Engineered parser.",
                provenance="Verified in Stage 01 Milestone"
            )
        ],
        current_country="India"
    )

def test_career_readiness_agent_qualitative_state(profile):
    agent = CareerReadinessAgent()
    goal = TargetOutcome(
        goal_id="g1",
        person_id="scholar-agent-test",
        target_role="Applied Machine Learning Systems Engineer"
    )

    from backend.services.career_readiness_engine import CareerReadinessEngine
    engine = CareerReadinessEngine()
    graph = engine.build_requirement_graph(goal.target_role, profile.skills)
    portfolio = engine.build_evidence_portfolio(profile, graph)

    state, explanation, next_milestone, gaps = agent.evaluate_readiness(
        profile=profile,
        target_goal=goal,
        requirement_graph=graph,
        evidence_portfolio=portfolio
    )

    assert state in ["FOUNDATIONAL", "DEVELOPING", "INTERNSHIP_READY", "ENTRY_LEVEL_READY", "TRANSITION_READY", "TARGET_READY", "ADVANCED"]
    assert len(explanation) > 10
    assert len(next_milestone) > 5
    assert len(gaps) >= 2

def test_credential_agent_strategy():
    agent = CredentialAgent()
    creds = agent.evaluate_credentials("Machine Learning Engineer")
    
    assert len(creds) >= 2
    for c in creds:
        assert c.classification in ["MANDATORY", "STRONGLY_USEFUL", "OPTIONAL", "LOW_VALUE", "NOT_RELEVANT"]
        assert c.official_url.startswith("https://")

def test_opportunity_agent_matching_and_timing(profile):
    agent = OpportunityAgent()
    opps = [
        VerifiedOpportunity(
            opportunity_id="opp_1",
            title="Machine Learning Intern",
            organization="Tech Labs",
            location="Bengaluru, India",
            employment_type="INTERNSHIP",
            eligibility="STEM Students",
            required_skills=["Python", "Linear Algebra"],
            preferred_skills=["PyTorch"],
            deadline="Rolling",
            apply_url="https://careers.google.com/students/",
            source="Verified Portal"
        )
    ]

    matched = agent.match_and_explain(opps, profile, "Machine Learning Engineer", "DEVELOPING")
    assert len(matched) == 1
    assert matched[0].fit_level == "HIGH"
    assert "stage milestone" in matched[0].pre_application_advice.lower() or "apply" in matched[0].pre_application_advice.lower()

def test_resume_agent_ats_and_provenance(profile):
    agent = ResumeAgent()
    resume = agent.generate_tailored_resume(profile, "Applied Machine Learning Systems Engineer")
    
    assert resume.person_id == profile.person_id
    assert resume.ats_match_score >= 50
    assert len(resume.ats_matched_keywords) >= 1
    assert len(resume.tailored_projects) >= 1
    assert resume.fact_validation_status == "PASSED"
    for proj in resume.tailored_projects:
        assert "provenance" in proj

def test_accountability_agent_supportive_interventions():
    agent = AccountabilityAgent()
    
    # Successful on-track progress
    status_on_track = agent.evaluate_accountability("user1", completed_stages=2, total_stages=5, weekly_hours=10, missed_milestones=0)
    assert status_on_track.status == "ON_TRACK"
    assert "on schedule" in status_on_track.mentor_observation.lower()

    # Missed milestones -> adaptive breakdown without shame
    status_risk = agent.evaluate_accountability("user1", completed_stages=1, total_stages=5, weekly_hours=10, missed_milestones=2)
    assert status_risk.status == "AT_RISK"
    assert "smaller" in status_risk.mentor_observation.lower() or "bite-sized" in status_risk.suggested_adjustment.lower()
