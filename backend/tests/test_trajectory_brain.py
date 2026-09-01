import pytest
import asyncio
from backend.services.trajectory_corpus import TrajectoryCorpusService
from backend.services.trajectory_engine import TrajectoryEngine
from backend.core.trajectory_schemas import (
    CandidatePath,
    PathSelectionRecord,
    CounterfactualRequest
)
from backend.core.assessment_schemas import CounselingProfile, CounselingFact, Contradiction
from backend.services.store import FirestoreStore

@pytest.fixture
def corpus():
    return TrajectoryCorpusService()

@pytest.fixture
def engine():
    return TrajectoryEngine()

@pytest.fixture
def store():
    return FirestoreStore()

def test_trajectory_corpus_and_similarity_matching(corpus):
    trajectories = corpus.get_all_trajectories()
    assert len(trajectories) >= 4
    
    # Check source_type attribution
    for t in trajectories:
        assert t.source_type in ["DEMO_ATTRIBUTED", "ATTRIBUTED_CASE_STUDY"]
        assert len(t.learning_milestones) >= 3
        assert len(t.obstacles_and_failures) >= 1

    # Match AI domain
    ai_matches = corpus.match_similar_trajectories(["ai", "machine learning"], {"I": 90.0, "R": 75.0}, limit=1)
    assert len(ai_matches) == 1
    assert "AI" in ai_matches[0].outcome_role or "Applied AI" in ai_matches[0].title

def test_cross_trajectory_patterns_extraction(corpus):
    patterns = corpus.get_all_patterns()
    assert len(patterns) >= 3
    for p in patterns:
        assert p.evidence_trajectories_count >= 2
        assert p.confidence in ["HIGH", "MEDIUM", "LOW"]
        assert len(p.pattern_title) > 5

@pytest.mark.asyncio
async def test_discover_candidate_paths_generation(engine):
    counseling_profile = CounselingProfile(
        person_id="scholar-test-1",
        timestamp="2026-09-01T00:00:00Z",
        is_preliminary=True,
        interest_vector={"R": 87.5, "I": 100.0, "A": 37.5, "S": 50.0, "E": 75.0, "C": 50.0},
        strongest_interests=["Investigative", "Realistic"],
        strengths=[
            CounselingFact(
                category="ASSESSED",
                claim="High quantitative reasoning interest",
                evidence=["RIASEC Investigative: 100%"],
                confidence="HIGH"
            )
        ],
        contradictions=[
            Contradiction(
                reported_preference="Dislike heavy theory without coding",
                observed_evidence="Built autonomous robot and ML classifier",
                suggested_clarification="Focus on applied systems engineering rather than pure abstract math."
            )
        ]
    )

    response = await engine.discover_candidate_paths(
        person_id="scholar-test-1",
        counseling_profile=counseling_profile,
        goals=["Explore AI/ML and Robotics"],
        constraints=["Class 12 Student"]
    )

    assert response.person_id == "scholar-test-1"
    assert len(response.candidate_paths) >= 2
    assert len(response.candidate_paths) <= 3
    
    path_ids = [p.path_id for p in response.candidate_paths]
    assert "path_applied_ai_ml_systems" in path_ids
    assert "path_robotics_embedded_systems" in path_ids

    # Verify skill gap taxonomy
    ai_path = next(p for p in response.candidate_paths if p.path_id == "path_applied_ai_ml_systems")
    categories = {gap.category for gap in ai_path.skill_gaps}
    assert "CORE" in categories
    assert "FOUNDATIONAL" in categories or "SPECIALIZED" in categories

    # Verify India vs Global context
    assert "nco_code" in ai_path.india_context
    assert "esco_uri" in ai_path.global_context or "esco_title" in ai_path.global_context

    # Verify credentials
    assert len(ai_path.credential_options) >= 1
    assert ai_path.credential_options[0].classification in ["MANDATORY", "STRONGLY_USEFUL", "OPTIONAL", "LOW_VALUE"]

def test_counterfactual_what_if_sandbox(engine):
    base_paths = engine.generate_deterministic_candidate_paths(person_id="user-counterfactual")
    base_ai = base_paths[0]

    # Test Low Budget modification
    res_low_budget = engine.generate_counterfactual_path(
        base_path=base_ai,
        modification_type="LOW_BUDGET",
        modification_prompt="What if I cannot afford a four-year private college?"
    )
    assert res_low_budget.base_path_id == base_ai.path_id
    assert any("financial expenditure" in note.lower() or "cost" in note.lower() for note in res_low_budget.trade_off_notes)
    assert res_low_budget.adjusted_path.education_routes[0].route_type == "PROJECT_BASED_ACCELERATED"

    # Test 5 Hours Per Week modification
    res_part_time = engine.generate_counterfactual_path(
        base_path=base_ai,
        modification_type="SELF_PACED_5_HOURS",
        modification_prompt="What if I only have 5 hours per week?"
    )
    assert any("5 hrs/week" in route.estimated_duration or "Extended" in route.estimated_duration for route in res_part_time.adjusted_path.education_routes)

@pytest.mark.asyncio
async def test_path_selection_and_versioning(store, engine):
    person_id = "scholar-versioning-test"
    paths = engine.generate_deterministic_candidate_paths(person_id=person_id)
    
    # Version 1 Selection
    record_v1 = PathSelectionRecord(
        version=1,
        person_id=person_id,
        selected_path_id=paths[0].path_id,
        selected_path=paths[0],
        all_candidate_paths=paths,
        selection_reason="Strongest alignment with Class 12 CS and hackathon classifier"
    )
    v1 = await store.save_selected_path(person_id, record_v1.model_dump(mode="json"))
    assert v1 == 1

    # Version 2 Selection (Scholar later switches to Robotics)
    record_v2 = PathSelectionRecord(
        version=2,
        person_id=person_id,
        selected_path_id=paths[1].path_id,
        selected_path=paths[1],
        all_candidate_paths=paths,
        selection_reason="Decided to specialize in physical robotics hardware"
    )
    v2 = await store.save_selected_path(person_id, record_v2.model_dump(mode="json"))
    assert v2 == 2

    # Verify history preservation
    history = await store.get_path_selection_history(person_id)
    assert len(history) == 2
    assert history[0]["selected_path_id"] == paths[0].path_id
    assert history[1]["selected_path_id"] == paths[1].path_id

    # Verify active path pointer
    active = await store.get_active_selected_path(person_id)
    assert active["selected_path_id"] == paths[1].path_id
    assert active["version"] == 2
