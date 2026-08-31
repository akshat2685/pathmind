import pytest
from backend.services.counseling import CounselingAgent
from backend.core.assessment_schemas import AssessmentResult, AssessmentResponse

def test_counseling_schema_and_agent_structure():
    agent = CounselingAgent()
    assert agent is not None
    assert agent.model is not None

def test_counseling_profile_schema_evidence_gaps():
    from backend.core.assessment_schemas import CounselingProfile, CounselingFact, Contradiction
    
    profile = CounselingProfile(
        person_id="user-123",
        timestamp="2026-08-31T00:00:00Z",
        strengths=[
            CounselingFact(
                category="ASSESSED",
                claim="High quantitative reasoning interest",
                evidence=["RIASEC Investigative: 5"],
                confidence="HIGH"
            )
        ],
        interest_patterns=[],
        capability_signals=[],
        constraints=[],
        unknowns=["No portfolio attached"],
        candidate_directions=["Systems Software Research"],
        contradictions=[],
        next_questions=["Please provide GitHub repo link"],
        evidence_gaps=["Missing verifiable portfolio / code repositories"]
    )
    
    assert len(profile.evidence_gaps) == 1
    assert "Missing" in profile.evidence_gaps[0]
    assert profile.strengths[0].category == "ASSESSED"
