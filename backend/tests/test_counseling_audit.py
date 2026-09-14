import pytest
from backend.services.counseling import CounselingAgent
from backend.core.assessment_schemas import (
    AssessmentResult,
    AssessmentResponse
)

def test_audit_unassessed_user_returns_empty_vector_and_insufficient_evidence():
    """
    Audit Requirement 1 & 3:
    When no RIASEC assessment exists, do NOT invent scores.
    Return an explicit unassessed/insufficient-evidence state.
    Prohibited vector: R=75, I=90, A=45, S=55, E=65, C=50.
    """
    agent = CounselingAgent()
    person_id = "test_unassessed_person_001"
    
    profile = agent.synthesize_profile(
        person_id=person_id,
        assessment_results=[],
        goals=[],
        constraints=[],
        evidence_items=[]
    )
    
    # 1. Verification of empty / unassessed interest vector
    assert profile.interest_vector == {}, "Interest vector must be empty dictionary when unassessed."
    
    # 2. Prohibited fallback scores MUST NOT be present
    prohibited_scores = {"R": 75, "I": 90, "A": 45, "S": 55, "E": 65, "C": 50}
    assert profile.interest_vector != prohibited_scores
    for key, val in prohibited_scores.items():
        assert profile.interest_vector.get(key) != val, f"Prohibited synthetic score {key}={val} detected!"

    # 3. Explicit unassessed status in unknowns and strongest interests
    assert profile.strongest_interests == []
    assert any("unassessed" in u.lower() for u in profile.unknowns), f"Expected unassessed unknown, got {profile.unknowns}"

def test_audit_artistic_social_profile_not_converted_to_aiml():
    """
    Audit Requirement 2 & 6:
    When user has validated Artistic (A=85) and Social (S=80) profile,
    candidate directions must NOT force AI/ML or software engineering.
    """
    agent = CounselingAgent()
    person_id = "test_artistic_social_person_002"

    assessment = AssessmentResult(
        person_id=person_id,
        assessment_id="holland_riasec_v1",
        version="1.0.0",
        raw_responses=[],
        calculated_scores={
            "normalized_vector": {"R": 20.0, "I": 30.0, "A": 85.0, "S": 80.0, "E": 40.0, "C": 25.0}
        }
    )

    profile = agent.synthesize_profile(
        person_id=person_id,
        assessment_results=[assessment],
        goals=[],
        constraints=[],
        evidence_items=[]
    )

    assert profile.interest_vector.get("A") == 85.0
    assert profile.interest_vector.get("S") == 80.0
    assert any("Artistic" in s for s in profile.strongest_interests)
    assert any("Social" in s for s in profile.strongest_interests)

    # Verify candidate directions reflect artistic/social rather than software engineering
    titles = [d.lower() for d in profile.candidate_directions]
    assert any("design" in t or "creative" in t or "instructional" in t or "media" in t for t in titles), f"Expected creative/social directions, got {titles}"
    
    # Ensure neither ML Engineer nor PyTorch is forced into directions
    for t in titles:
        assert "machine learning" not in t
        assert "pytorch" not in t

def test_audit_non_technical_goals_receive_non_technical_candidate_directions():
    """
    Audit Requirement 7:
    Counseling candidate directions must be generated from actual stated goal,
    actual assessment signals, verified evidence, and relevant occupational knowledge.
    """
    agent = CounselingAgent()

    # Law Goal
    law_profile = agent.synthesize_profile(
        person_id="counsel_law_001",
        assessment_results=[],
        goals=["Become a Constitutional Lawyer and Judicial Advocate"],
        constraints=["15 hours/week"]
    )
    law_titles = [d.lower() for d in law_profile.candidate_directions]
    assert any("law" in t or "legal" in t or "advocate" in t for t in law_titles), f"Expected legal directions, got {law_titles}"
    for t in law_titles:
        assert "software" not in t
        assert "machine learning" not in t

    # Biotechnology Goal
    bio_profile = agent.synthesize_profile(
        person_id="counsel_bio_001",
        assessment_results=[],
        goals=["Genomics and Molecular Biotechnology Researcher"],
        constraints=["Full time"]
    )
    bio_titles = [d.lower() for d in bio_profile.candidate_directions]
    assert any("biotech" in t or "genom" in t or "molecular" in t or "research" in t for t in bio_titles), f"Expected biotech directions, got {bio_titles}"

    # Hospitality / Culinary Goal
    chef_profile = agent.synthesize_profile(
        person_id="counsel_chef_001",
        assessment_results=[],
        goals=["Executive Chef and Farm-to-Table Restaurant Owner"],
        constraints=["Evening shifts"]
    )
    chef_titles = [d.lower() for d in chef_profile.candidate_directions]
    assert any("culinary" in t or "restaurant" in t or "hospitality" in t or "beverage" in t for t in chef_titles), f"Expected culinary directions, got {chef_titles}"

def test_audit_target_aware_evidence_requests():
    """
    Audit Requirement 7 & Evidence Requests:
    Evidence requests must match the target domain rather than defaulting
    to code repos or technical git commits.
    """
    agent = CounselingAgent()

    # Law Profile Evidence Requests
    law_profile = agent.synthesize_profile(
        person_id="counsel_law_002",
        assessment_results=[],
        goals=["Corporate Lawyer"],
        constraints=[]
    )
    law_reqs = " ".join(law_profile.evidence_gaps).lower()
    assert "legal" in law_reqs or "brief" in law_reqs or "case" in law_reqs or "jurisprudence" in law_reqs or "bar" in law_reqs

    # Designer Profile Evidence Requests
    design_profile = agent.synthesize_profile(
        person_id="counsel_design_002",
        assessment_results=[],
        goals=["Product Designer"],
        constraints=[]
    )
    design_reqs = " ".join(design_profile.evidence_gaps).lower()
    assert "figma" in design_reqs or "design" in design_reqs or "portfolio" in design_reqs or "prototype" in design_reqs or "ux" in design_reqs

def test_audit_chat_handles_unassessed_without_hallucinating():
    """
    Counsel chat must acknowledge unassessed interest state rather than
    hallucinating high investigative or realistic scores.
    """
    agent = CounselingAgent()
    person_id = "test_chat_unassessed_user"
    
    unassessed_profile = agent.synthesize_profile(
        person_id=person_id,
        assessment_results=[],
        goals=[],
        constraints=[],
        evidence_items=[]
    )

    msg = agent.counsel_chat(
        person_id=person_id,
        user_message="What careers suit my personality best?",
        profile=unassessed_profile
    )
    # Must communicate that psychometric interest profile is unassessed
    assert "unassessed" in msg.content.lower() or "assessment" in msg.content.lower()
    # Must NOT claim high investigative (90%) or realistic (75%) scores
    assert "90%" not in msg.content
    assert "75%" not in msg.content
