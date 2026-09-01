import pytest
from datetime import datetime, timezone
from backend.services.counseling import CounselingAgent
from backend.core.assessment_schemas import (
    AssessmentResult,
    AssessmentResponse,
    CounselingProfile,
    CounselingFact,
    Contradiction,
    CounselingChatRequest,
    CounselingMessage
)
from backend.services.store import FirestoreStore

def test_evidence_classification_and_weighting():
    agent = CounselingAgent()
    
    # 1. Project Evidence + Investigative RIASEC
    riasec_res = AssessmentResult(
        person_id="scholar-1",
        assessment_id="riasec_v1",
        version="1.0.0",
        timestamp=datetime.now(timezone.utc).isoformat(),
        raw_responses=[
            AssessmentResponse(item_id="r1", response_value=5),
            AssessmentResponse(item_id="i1", response_value=5),
            AssessmentResponse(item_id="a1", response_value=2),
            AssessmentResponse(item_id="s1", response_value=3),
            AssessmentResponse(item_id="e1", response_value=4),
            AssessmentResponse(item_id="c1", response_value=3)
        ],
        calculated_scores={
            "normalized_vector": {"R": 80.0, "I": 100.0, "A": 20.0, "S": 50.0, "E": 75.0, "C": 50.0}
        },
        dimension_scores={"R": 80.0, "I": 100.0, "A": 20.0, "S": 50.0, "E": 75.0, "C": 50.0}
    )

    evidence = [{
        "name": "Robotics Navigation Stack",
        "description": "C++ ROS2 package implementing SLAM on differential drive robot",
        "type": "project"
    }]

    profile = agent.synthesize_profile(
        person_id="scholar-1",
        assessment_results=[riasec_res],
        goals=["Build intelligent robotics systems"],
        constraints=["Undergraduate 2nd year"],
        evidence_items=evidence
    )

    assert profile.person_id == "scholar-1"
    assert profile.is_preliminary is True
    assert profile.overall_confidence in ["HIGH", "MEDIUM"]

    # Verify categories are strictly distinguished
    categories = {fact.category for fact in profile.strengths + profile.capability_signals}
    assert "ASSESSED" in categories
    assert "OBSERVED" in categories
    assert "INFERRED" in categories

def test_contradiction_detection_dislike_coding_vs_repo():
    agent = CounselingAgent()

    riasec_res = AssessmentResult(
        person_id="scholar-conflict",
        assessment_id="riasec_v1",
        version="1.0.0",
        timestamp=datetime.now(timezone.utc).isoformat(),
        raw_responses=[],
        calculated_scores={"normalized_vector": {"R": 60.0, "I": 70.0, "A": 40.0, "S": 40.0, "E": 40.0, "C": 40.0}},
        dimension_scores={"R": 60.0, "I": 70.0, "A": 40.0, "S": 40.0, "E": 40.0, "C": 40.0}
    )

    evidence = [{
        "name": "GitHub Fullstack Repo",
        "description": "React and FastAPI web application repository",
        "type": "project"
    }]

    contradictions = agent.detect_contradictions(
        stated_goals=["I hate coding and want non-technical work."],
        stated_constraints=[],
        evidence_items=evidence,
        riasec_scores={"R": 60.0, "I": 70.0, "A": 40.0, "S": 40.0, "E": 40.0, "C": 40.0}
    )

    assert len(contradictions) >= 1
    assert "Disinterest" in contradictions[0].reported_preference
    assert "programming" in contradictions[0].observed_evidence.lower()
    assert "clarification" in contradictions[0].suggested_clarification.lower() or "hesitation" in contradictions[0].suggested_clarification.lower()

def test_categorical_confidence_insufficient_evidence():
    agent = CounselingAgent()
    conf = agent.compute_categorical_confidence(evidence_count=0, assessment_count=0, contradiction_count=0)
    assert conf == "INSUFFICIENT_EVIDENCE"

    conf_high = agent.compute_categorical_confidence(evidence_count=3, assessment_count=2, contradiction_count=0)
    assert conf_high == "HIGH"

def test_counseling_chat_and_memory_isolation():
    agent = CounselingAgent()
    store = FirestoreStore()

    profile = agent.synthesize_deterministic_profile(
        person_id="user-chat-test",
        assessment_results=[],
        goals=["AI research"],
        constraints=[],
        evidence_items=[]
    )

    message = agent.counsel_chat(
        person_id="user-chat-test",
        user_message="What should I focus on first?",
        profile=profile,
        history=[]
    )

    assert message.role == "counselor"
    assert len(message.content) > 10

def test_deterministic_demo_scenario_synthesis():
    agent = CounselingAgent()
    
    demo_evidence = [
        {"name": "Autonomous Line-Following & Maze Robot", "description": "Hardware build Arduino/C++"},
        {"name": "Hackathon AI Data Classifier", "description": "Python scikit-learn app"}
    ]

    demo_riasec = AssessmentResult(
        person_id="demo-person",
        assessment_id="riasec_v1",
        version="1.0.0",
        timestamp=datetime.now(timezone.utc).isoformat(),
        raw_responses=[],
        calculated_scores={
            "normalized_vector": {"R": 87.5, "I": 100.0, "A": 37.5, "S": 50.0, "E": 75.0, "C": 50.0}
        },
        dimension_scores={"R": 87.5, "I": 100.0, "A": 37.5, "S": 50.0, "E": 75.0, "C": 50.0}
    )

    profile = agent.synthesize_deterministic_profile(
        person_id="demo-person",
        assessment_results=[demo_riasec],
        goals=["Explore AI/ML and engineering"],
        constraints=["Class 12 Student"],
        evidence_items=demo_evidence
    )

    assert profile.person_id == "demo-person"
    assert "Investigative" in profile.strongest_interests[0] or "Realistic" in profile.strongest_interests[0]
    assert len(profile.candidate_directions) >= 2
    assert any("Artificial Intelligence" in d or "Robotics" in d for d in profile.candidate_directions)
    assert profile.is_preliminary is True
