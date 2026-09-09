import pytest
from datetime import datetime, timezone
from backend.core.career_schemas import (
    UniversalCareerProfile,
    EducationItem,
    ExperienceItem,
    ProjectItem,
    TailoredResume
)
from backend.services.resume_validator import ResumeFactValidator

@pytest.fixture
def validator():
    return ResumeFactValidator()

@pytest.fixture
def sample_profile():
    return UniversalCareerProfile(
        person_id="scholar-fact-test",
        current_role="Student Scholar",
        current_state_type="college_student",
        education=[
            EducationItem(
                degree="Senior Secondary (CBSE STEM)",
                field_of_study="Computer Science & Mathematics",
                institution="Central Board of Secondary Education",
                year="2026"
            )
        ],
        experience=[
            ExperienceItem(
                role="Student Contributor",
                organization="PATHMIND Learning Program",
                duration="2026 – Present",
                description="Built modular data pipelines."
            )
        ],
        skills=["Python 3.12", "Pytest", "Linear Algebra", "Git", "Dataclasses"],
        projects=[
            ProjectItem(
                title="Modular Data Parser & Stream Ingestion Pipeline",
                technologies=["Python", "Pytest", "Dataclasses"],
                description="Engineered data parser.",
                provenance="Verified in Stage 01 Milestone"
            )
        ]
    )

def test_resume_valid_claims_pass_validation(validator, sample_profile):
    valid_resume = TailoredResume(
        resume_id="res_valid_01",
        person_id="scholar-fact-test",
        target_role="Applied Machine Learning Systems Engineer",
        summary="Aspiring engineer with verified Python and Mathematics foundations.",
        highlighted_skills=["Python 3.12", "Pytest", "Linear Algebra"],
        tailored_projects=[
            {
                "title": "Modular Data Parser & Stream Ingestion Pipeline",
                "technologies": ["Python", "Pytest"],
                "description": "Engineered data parser with 85%+ branch coverage.",
                "provenance": "Verified in Stage 01 Milestone"
            }
        ],
        verified_experience=[
            {
                "role": "Student Contributor",
                "organization": "PATHMIND Learning Program",
                "duration": "2026 – Present",
                "description": "Built modular data pipelines."
            }
        ],
        education=[
            {
                "degree": "Senior Secondary (CBSE STEM)",
                "field": "Computer Science & Mathematics",
                "institution": "Central Board of Secondary Education",
                "year": "2026"
            }
        ]
    )

    sanitized, is_valid = validator.validate_and_sanitize(valid_resume, sample_profile)
    assert is_valid is True
    assert sanitized.fact_validation_status == "PASSED"
    assert len(sanitized.tailored_projects) == 1
    assert len(sanitized.unsupported_claims_rejected) == 0

def test_resume_hallucinated_project_is_rejected(validator, sample_profile):
    hallucinated_resume = TailoredResume(
        resume_id="res_hallucinated_01",
        person_id="scholar-fact-test",
        target_role="Machine Learning Engineer",
        summary="Experienced engineer with fabricated systems.",
        highlighted_skills=["Python 3.12"],
        tailored_projects=[
            {
                "title": "Fabricated Enterprise Kubernetes Cluster Manager",
                "technologies": ["Kubernetes", "Golang", "AWS"],
                "description": "Led production cluster management at high scale.",
                "provenance": "Unverified Fake Claim"
            }
        ],
        verified_experience=[],
        education=[]
    )

    sanitized, is_valid = validator.validate_and_sanitize(hallucinated_resume, sample_profile)
    assert is_valid is False
    assert sanitized.fact_validation_status == "FAILED"
    assert len(sanitized.tailored_projects) == 0
    assert len(sanitized.unsupported_claims_rejected) >= 1
    assert any("Fabricated" in r or "removed" in r for r in sanitized.unsupported_claims_rejected)

def test_resume_hallucinated_company_is_stripped(validator, sample_profile):
    resume_with_fake_job = TailoredResume(
        resume_id="res_fake_job_01",
        person_id="scholar-fact-test",
        target_role="Machine Learning Engineer",
        summary="Summary text",
        highlighted_skills=["Python 3.12"],
        tailored_projects=[
            {
                "title": "Modular Data Parser & Stream Ingestion Pipeline",
                "technologies": ["Python", "Pytest"],
                "description": "Engineered data parser.",
                "provenance": "Verified in Stage 01 Milestone"
            }
        ],
        verified_experience=[
            {
                "role": "Principal AI Architect",
                "organization": "Imaginary Deep Learning Corp",
                "duration": "2020 – 2026",
                "description": "Invented role with zero backing evidence."
            }
        ],
        education=[]
    )

    sanitized, is_valid = validator.validate_and_sanitize(resume_with_fake_job, sample_profile)
    assert len(sanitized.verified_experience) == 0
    assert any("Imaginary Deep Learning Corp" in r for r in sanitized.unsupported_claims_rejected)
