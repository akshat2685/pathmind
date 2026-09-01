import pytest
import asyncio
from backend.services.roadmap_engine import RoadmapEngine
from backend.services.personal_agent_engine import PersonalAgentEngine
from backend.services.store import FirestoreStore
from backend.core.roadmap_schemas import (
    EvidenceSubmission,
    AdaptConstraintRequest
)

@pytest.fixture
def engine():
    return RoadmapEngine()

@pytest.fixture
def personal_agent():
    return PersonalAgentEngine()

@pytest.fixture
def store():
    return FirestoreStore()

@pytest.mark.asyncio
async def test_roadmap_generation_and_progressive_disclosure(engine):
    person_id = "scholar-roadmap-test-1"
    roadmap = await engine.get_or_create_roadmap(person_id=person_id)
    
    assert roadmap.person_id == person_id
    assert roadmap.total_stages == 5
    assert roadmap.current_stage_id == "stage_01_python_foundations"
    
    # Check progressive disclosure view
    view = engine.build_disclosed_view(roadmap)
    assert view.total_stages == 5
    assert view.completed_stages == 0
    assert view.overall_progress_percent == 0.0
    assert view.active_stage is not None
    assert view.active_stage.stage_id == "stage_01_python_foundations"
    assert view.active_stage.locked is False
    assert len(view.active_stage.missions) >= 1

    # Check future stages are locked and redacted
    locked_stage_2 = next(s for s in view.stages if s.stage_id == "stage_02_math_and_linear_algebra")
    assert locked_stage_2.locked is True
    assert locked_stage_2.status == "LOCKED"
    assert locked_stage_2.current_mission is None
    assert len(locked_stage_2.resources) == 0

@pytest.mark.asyncio
async def test_backend_lock_enforcement(engine):
    person_id = "scholar-lock-enforce-test"
    roadmap = await engine.get_or_create_roadmap(person_id=person_id)
    
    # Attempting to submit evidence for locked Stage 2 must raise PermissionError
    sub_locked = EvidenceSubmission(
        person_id=person_id,
        roadmap_id=roadmap.roadmap_id,
        stage_id="stage_02_math_and_linear_algebra",
        evidence_type="CODE_REPO",
        content_payload={"code": "import numpy as np; def gradient(): pass"}
    )
    
    with pytest.raises(PermissionError):
        await engine.evaluate_evidence_and_progress(person_id, sub_locked)

@pytest.mark.asyncio
async def test_successful_evidence_evaluation_and_unlock_loop(engine, personal_agent):
    person_id = "scholar-unlock-test"
    roadmap = await engine.get_or_create_roadmap(person_id=person_id)
    
    # Valid submission for Stage 1
    valid_sub = EvidenceSubmission(
        person_id=person_id,
        roadmap_id=roadmap.roadmap_id,
        stage_id="stage_01_python_foundations",
        mission_id="mission_01_modular_parser",
        evidence_type="CODE_REPO",
        content_payload={
            "code": "def parse_records(stream): import pytest; return [r for r in stream]\ndef test_parser(): assert True"
        }
    )
    
    eval_result = await engine.evaluate_evidence_and_progress(person_id, valid_sub)
    assert eval_result.status == "PASS"
    assert eval_result.mastery_dimensions.accuracy >= 80.0
    assert len(eval_result.demonstrated) >= 2

    # Verify Stage 1 is COMPLETED and Stage 2 is UNLOCKED
    updated_roadmap = await engine.get_or_create_roadmap(person_id)
    assert updated_roadmap.completed_stages == 1
    assert updated_roadmap.current_stage_id == "stage_02_math_and_linear_algebra"
    
    flat = engine.get_all_stages_flat(updated_roadmap)
    stage_1 = next(s for s in flat if s.stage_id == "stage_01_python_foundations")
    stage_2 = next(s for s in flat if s.stage_id == "stage_02_math_and_linear_algebra")
    
    assert stage_1.status == "COMPLETED"
    assert stage_2.locked is False
    assert stage_2.status == "ACTIVE"

    # Verify Personal Agent Learning Loop
    agent_model = await personal_agent.get_or_create_agent_model(person_id)
    assert agent_model.version >= 2
    assert "Python Foundations & Object-Oriented Engineering" in agent_model.strengths
    assert len(agent_model.longitudinal_memories) >= 2

@pytest.mark.asyncio
async def test_reinforcement_path_on_insufficient_evidence(engine):
    person_id = "scholar-reinforce-test"
    roadmap = await engine.get_or_create_roadmap(person_id=person_id)
    
    # Insufficient submission (too short, no tests)
    weak_sub = EvidenceSubmission(
        person_id=person_id,
        roadmap_id=roadmap.roadmap_id,
        stage_id="stage_01_python_foundations",
        evidence_type="CODE_REPO",
        content_payload={"code": "x = 1"}
    )
    
    eval_result = await engine.evaluate_evidence_and_progress(person_id, weak_sub)
    assert eval_result.status == "REINFORCE"
    assert len(eval_result.missing) >= 1

    # Verify Stage 1 remains in REINFORCEMENT status and Stage 2 remains LOCKED
    updated_roadmap = await engine.get_or_create_roadmap(person_id)
    assert updated_roadmap.completed_stages == 0
    assert updated_roadmap.current_stage_id == "stage_01_python_foundations"
    
    flat = engine.get_all_stages_flat(updated_roadmap)
    stage_1 = next(s for s in flat if s.stage_id == "stage_01_python_foundations")
    stage_2 = next(s for s in flat if s.stage_id == "stage_02_math_and_linear_algebra")
    
    assert stage_1.status == "REINFORCEMENT"
    assert stage_2.locked is True
    # Reinforcement mission inserted
    assert any("reinf" in m.mission_id for m in stage_1.missions)

@pytest.mark.asyncio
async def test_constraint_adaptation_preserves_progress(engine):
    person_id = "scholar-adapt-test"
    roadmap = await engine.get_or_create_roadmap(person_id=person_id)
    
    # Adapt to 5 hours/week
    adapted_roadmap = await engine.adapt_constraints(
        person_id=person_id,
        req=AdaptConstraintRequest(person_id=person_id, weekly_hours=5)
    )
    
    assert adapted_roadmap.constraints["weekly_hours"] == 5
    assert adapted_roadmap.version >= 2
    assert "Adjusted roadmap pacing for 5 hours/week" in adapted_roadmap.revision_reason

@pytest.mark.asyncio
async def test_person_isolation_and_cross_stage_memory(personal_agent):
    person_a = "person-alice-1"
    person_b = "person-bob-2"
    
    model_a = await personal_agent.get_or_create_agent_model(person_a)
    model_b = await personal_agent.get_or_create_agent_model(person_b)
    
    assert model_a.person_id == person_a
    assert model_b.person_id == person_b
    
    # Cross-stage concept lookup
    memory = await personal_agent.retrieve_cross_stage_memory(person_a, "Tree Traversal and Graph Search")
    assert memory is not None
    assert "Recursion" in memory["related_concept"]
    assert "Stage 1: Python Foundations" in memory["stage_learned"]
