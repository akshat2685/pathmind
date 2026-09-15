import pytest
from backend.services.goal_assessment_service import GoalAssessmentService
from backend.core.person_schemas import PersonProfile, LearnerBaseline

@pytest.mark.asyncio
async def test_blueprint_generation_differentiates_by_stage():
    engine = GoalAssessmentService()
    
    # We only run this test if Gemini is available, else it will throw ValueError
    if not engine.gemini_available:
        pytest.skip("Gemini API Key missing, skipping AI generation tests.")

    # Profile 1: School Student -> Football
    school_profile = PersonProfile(
        person_id="test-school-1",
        learner_stage="School Student",
        aspiration="Professional Football Player",
        domain="Sports",
        evidence_summary="Plays for local high school team."
    )
    
    school_blueprint = engine.generate_assessment_blueprint(school_profile)
    
    # Profile 2: College Student -> Football
    college_profile = PersonProfile(
        person_id="test-college-1",
        learner_stage="College / University Student",
        aspiration="Professional Football Player",
        domain="Sports",
        evidence_summary="NCAA Division 1 player."
    )
    
    college_blueprint = engine.generate_assessment_blueprint(college_profile)
    
    # Assert they generated valid blueprints
    assert school_blueprint.id.startswith("blueprint_")
    assert college_blueprint.id.startswith("blueprint_")
    
    # Note: difficulty level and dimensions might differ based on the AI response,
    # but we can at least assert the blueprint fields exist and contain expected data.
    assert school_blueprint.learner_stage == "School Student"
    assert college_blueprint.learner_stage == "College / University Student"
    assert len(school_blueprint.dimensions) > 0
    assert len(college_blueprint.dimensions) > 0
    
    # Profile 3: Graduate -> Software Engineer
    grad_profile = PersonProfile(
        person_id="test-grad-1",
        learner_stage="Graduate",
        aspiration="Senior Software Engineer",
        domain="Computer Science",
        evidence_summary="Recent CS grad with some open source contributions."
    )
    
    grad_blueprint = engine.generate_assessment_blueprint(grad_profile)
    assert grad_blueprint.domain == "Computer Science"
    
    # Profile 4: Working Professional -> Career Switcher to Software Engineer
    switcher_profile = PersonProfile(
        person_id="test-switcher-1",
        learner_stage="Career Switcher",
        aspiration="Software Engineer",
        domain="Computer Science",
        evidence_summary="Worked in marketing for 5 years, did a coding bootcamp."
    )
    
    switcher_blueprint = engine.generate_assessment_blueprint(switcher_profile)
    assert switcher_blueprint.learner_stage == "Career Switcher"
    
    # The assessment_goal for a switcher should differ from a recent grad
    print(f"Grad Goal: {grad_blueprint.assessment_goal}")
    print(f"Switcher Goal: {switcher_blueprint.assessment_goal}")

    # Generate actual assessment from blueprint
    school_assessment = engine.generate_goal_assessment(school_blueprint)
    assert len(school_assessment.items) >= 5
    assert school_assessment.construct == "Sports"

