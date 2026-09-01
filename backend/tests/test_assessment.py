import pytest
from backend.services.assessment import AssessmentEngine
from backend.core.assessment_schemas import AssessmentResponse, AssessmentDraft

@pytest.fixture
def engine():
    return AssessmentEngine()

def test_riasec_scoring_all_six_dimensions(engine):
    responses = [
        AssessmentResponse(item_id="r1", response_value=5),
        AssessmentResponse(item_id="r2", response_value=4),
        AssessmentResponse(item_id="i1", response_value=5),
        AssessmentResponse(item_id="i2", response_value=5),
        AssessmentResponse(item_id="a1", response_value=2),
        AssessmentResponse(item_id="a2", response_value=1),
        AssessmentResponse(item_id="s1", response_value=3),
        AssessmentResponse(item_id="s2", response_value=3),
        AssessmentResponse(item_id="e1", response_value=4),
        AssessmentResponse(item_id="e2", response_value=4),
        AssessmentResponse(item_id="c1", response_value=3),
        AssessmentResponse(item_id="c2", response_value=3)
    ]
    
    result = engine.process_submission("test-user-1", "riasec_v1", responses)
    
    assert result.person_id == "test-user-1"
    assert result.assessment_id == "riasec_v1"
    assert "normalized_vector" in result.calculated_scores
    norm = result.calculated_scores["normalized_vector"]
    assert norm["I"] == 100.0
    assert norm["R"] == 87.5
    assert norm["A"] == 12.5
    assert "strongest_dimensions" in result.calculated_scores
    assert "I" in result.calculated_scores["strongest_dimensions"]

def test_scct_scoring_and_context(engine):
    responses = [
        AssessmentResponse(item_id="se1", response_value=5),
        AssessmentResponse(item_id="se2", response_value=4),
        AssessmentResponse(item_id="oe1", response_value=5),
        AssessmentResponse(item_id="oe2", response_value=4),
        AssessmentResponse(item_id="cs1", response_value="School lab, AI Mentor"),
        AssessmentResponse(item_id="cb1", response_value="Limited hardware GPU budget")
    ]
    
    result = engine.process_submission("test-user-2", "scct_v1", responses)
    assert result.person_id == "test-user-2"
    assert result.calculated_scores["self_efficacy_level"] == "HIGH"
    assert result.calculated_scores["self_efficacy_average"] == 4.5
    assert "School lab, AI Mentor" in result.calculated_scores["contextual_supports"]
    assert "Limited hardware GPU budget" in result.calculated_scores["contextual_barriers"]

def test_learning_tasks_submission(engine):
    responses = [
        AssessmentResponse(item_id="lt_recall", response_value="Stack is LIFO, Queue is FIFO"),
        AssessmentResponse(item_id="lt_explain", response_value="Indexing uses balanced trees"),
        AssessmentResponse(item_id="lt_apply", response_value="Process in streaming chunks"),
        AssessmentResponse(item_id="lt_error", response_value="Boundary error <= instead of <"),
        AssessmentResponse(item_id="lt_reason", response_value="Monolith decreases initial network overhead")
    ]
    
    result = engine.process_submission("test-user-3", "learning_v1", responses)
    assert result.calculated_scores["tasks_submitted"] == 5
    assert result.calculated_scores["status"] == "ready_for_agent_evaluation"

def test_invalid_assessment_id(engine):
    with pytest.raises(ValueError) as exc:
        engine.process_submission("test-user", "non_existent_assessment", [
            AssessmentResponse(item_id="r1", response_value=5)
        ])
    assert "not found" in str(exc.value)

def test_empty_responses_rejected(engine):
    with pytest.raises(ValueError) as exc:
        engine.process_submission("test-user", "riasec_v1", [])
    assert "empty assessment" in str(exc.value)

def test_get_all_assessments(engine):
    assessments = engine.get_all_assessments()
    assert len(assessments) == 3
    ids = [a.id for a in assessments]
    assert "riasec_v1" in ids
    assert "scct_v1" in ids
    assert "learning_v1" in ids
