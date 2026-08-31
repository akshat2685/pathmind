import pytest
from backend.services.assessment import AssessmentEngine
from backend.core.assessment_schemas import AssessmentResponse

@pytest.fixture
def engine():
    return AssessmentEngine()

def test_riasec_scoring(engine):
    responses = [
        AssessmentResponse(item_id="r1", response_value=4, timestamp="now"),
        AssessmentResponse(item_id="i1", response_value=5, timestamp="now"),
        AssessmentResponse(item_id="a1", response_value=2, timestamp="now"),
        AssessmentResponse(item_id="s1", response_value=3, timestamp="now"),
        AssessmentResponse(item_id="e1", response_value=4, timestamp="now"),
        AssessmentResponse(item_id="c1", response_value=3, timestamp="now")
    ]
    
    result = engine.process_submission("test-user-1", "riasec_v1", responses)
    
    assert result.calculated_scores["R"] == 4
    assert result.calculated_scores["I"] == 5
    assert result.calculated_scores["A"] == 2
    assert result.calculated_scores["S"] == 3
    assert result.calculated_scores["E"] == 4
    assert result.calculated_scores["C"] == 3
    assert result.person_id == "test-user-1"
    assert result.assessment_id == "riasec_v1"

def test_invalid_assessment_id(engine):
    with pytest.raises(ValueError):
        engine.process_submission("test-user", "invalid_id", [])

def test_get_all_assessments(engine):
    assessments = engine.get_all_assessments()
    assert len(assessments) == 3
    ids = [a.id for a in assessments]
    assert "riasec_v1" in ids
    assert "scct_v1" in ids
    assert "learning_v1" in ids
