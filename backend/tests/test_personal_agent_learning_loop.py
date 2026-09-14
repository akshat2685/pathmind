import pytest
from datetime import datetime, timezone
from backend.services.mastery_engine import MasteryEngine
from backend.services.personal_agent_engine import PersonalAgentEngine
from backend.services.adaptation_service import AdaptationService
from backend.services.store import FirestoreStore
from backend.core.adaptation_schemas import LearningSignal, UserAdaptationDecision
from backend.core.evidence_schemas import CanonicalEvidence

@pytest.fixture
def store():
    return FirestoreStore()

@pytest.fixture
def personal_agent(store):
    return PersonalAgentEngine()

@pytest.fixture
def mastery_engine(store, personal_agent):
    return MasteryEngine(store=store, personal_agent=personal_agent)

@pytest.fixture
def adaptation_service(store, personal_agent):
    return AdaptationService(store=store, personal_agent=personal_agent)

@pytest.mark.asyncio
async def test_strong_evidence_advances_mastery_and_updates_personal_model(mastery_engine, personal_agent):
    """Test #1 & #15: Strong evidence advances mastery and updates personal model without LLM mechanics."""
    person_id = "test-learner-loop-1"
    await mastery_engine.roadmap_engine.get_or_create_roadmap(person_id)

    # Submit strong code evidence
    attempt = await mastery_engine.submit_and_evaluate_evidence(
        person_id=person_id,
        stage_id="stage_01_python_foundations",
        evidence_type="CODE_REPO",
        title="Passing Unit Test Suite",
        source_reference="github.com/scholar/parser",
        payload={
            "code": "def parse(): pass\ndef test_parse(): assert True"
        }
    )

    assert attempt.status == "PASS"

    # Verify skill mastery profile transition
    profiles = await mastery_engine.store.get_skill_mastery_profiles(person_id)
    python_oop = profiles.get("Python OOP")
    assert python_oop is not None
    assert python_oop["mastery_state"] in ["DEMONSTRATED", "TRANSFER", "APPLICATION"]
    assert len(python_oop["transition_history"]) > 0
    assert python_oop["transition_history"][-1]["to_state"] == python_oop["mastery_state"]

    # Verify personal model updated via learning signal
    model = await personal_agent.get_or_create_agent_model(person_id)
    assert "Python Foundations & Object-Oriented Engineering" in model.demonstrated_capabilities

@pytest.mark.asyncio
async def test_plan_stability_on_isolated_failure(mastery_engine, adaptation_service):
    """Test #3: One failed attempt triggers micro-adaptation, not an entire roadmap rewrite."""
    person_id = "test-learner-loop-2"
    rm1 = await mastery_engine.roadmap_engine.get_or_create_roadmap(person_id)
    v1 = rm1.version

    attempt = await mastery_engine.submit_and_evaluate_evidence(
        person_id=person_id,
        stage_id="stage_01_python_foundations",
        evidence_type="CODE_REPO",
        title="Failing Test Suite",
        source_reference="github.com/scholar/parser",
        payload={"code": "x = 1"}  # Weak evidence -> fails verification -> REINFORCE
    )

    assert attempt.status == "REINFORCE"
    
    # Active roadmap version should not have bumped
    rm2 = await mastery_engine.roadmap_engine.get_or_create_roadmap(person_id)
    assert rm2.version == v1

    # Check that a micro-adaptation was generated
    micros = await adaptation_service.store.get_active_micro_adaptations(person_id)
    assert len(micros) >= 1
    assert micros[0]["adaptation_type"] in ["INJECT_REINFORCEMENT", "EXPLANATION_STYLE"]

@pytest.mark.asyncio
async def test_misconception_lifecycle(personal_agent):
    """Test #6: Misconception detected -> tracked -> resolved upon verified demonstration."""
    person_id = "test-learner-loop-3"
    
    # Simulate signal with misconception
    signal1 = LearningSignal(
        person_id=person_id,
        type="MISCONCEPTION_DETECTED",
        subject="Recursion",
        source_event_id="sub_1",
        evidence_ids=["sub_1"],
        impact_scope="MISSION_ONLY"
    )
    await personal_agent.process_learning_signal(person_id, signal1, {"observable_misconceptions": ["Base case omitted"]})
    
    model = await personal_agent.get_or_create_agent_model(person_id)
    assert len(model.recurring_misconceptions) == 1
    assert model.recurring_misconceptions[0].concept == "Recursion"
    assert model.recurring_misconceptions[0].misconception == "Base case omitted"
    assert not model.recurring_misconceptions[0].resolved

    # Simulate passing signal
    signal2 = LearningSignal(
        person_id=person_id,
        type="MASTERY_DEMONSTRATED",
        subject="Recursion",
        source_event_id="sub_2",
        evidence_ids=["sub_2"],
        impact_scope="STAGE"
    )
    await personal_agent.process_learning_signal(person_id, signal2)

    model2 = await personal_agent.get_or_create_agent_model(person_id)
    assert model2.recurring_misconceptions[0].resolved
    assert model2.recurring_misconceptions[0].resolution_evidence_id == "sub_2"

@pytest.mark.asyncio
async def test_regression_risk_detection(mastery_engine, personal_agent):
    """Test #7: Subsequent failure on previously mastered prerequisite flags REGRESSION_RISK."""
    person_id = "test-learner-loop-4"
    await mastery_engine.roadmap_engine.get_or_create_roadmap(person_id)
    
    # 1. Force state to DEMONSTRATED
    profile = {
        "skill_name": "Python OOP",
        "category": "Stage 01: Python Foundations",
        "mastery_state": "DEMONSTRATED",
        "evidence_count": 1,
        "is_regression_risk": False,
        "transition_history": []
    }
    await mastery_engine.store.save_skill_mastery_profile(person_id, "Python OOP", profile)
    
    model = await personal_agent.get_or_create_agent_model(person_id)
    model.demonstrated_capabilities.append("Python Foundations & Object-Oriented Engineering")
    await personal_agent.update_agent_model(person_id, model)

    # 2. Submit failing evidence for the same stage
    attempt = await mastery_engine.submit_and_evaluate_evidence(
        person_id=person_id,
        stage_id="stage_01_python_foundations",
        evidence_type="CODE_REPO",
        title="Regression Test",
        source_reference="notes",
        payload={"code": "x = 1"}
    )
    
    assert attempt.status == "REINFORCE"
    
    # 3. Check that it was flagged as REGRESSION_RISK
    profiles = await mastery_engine.store.get_skill_mastery_profiles(person_id)
    assert profiles["Python OOP"]["mastery_state"] == "REGRESSION_RISK"
    
    model2 = await personal_agent.get_or_create_agent_model(person_id)
    assert "Python Foundations & Object-Oriented Engineering" in model2.regression_risks

@pytest.mark.asyncio
async def test_rejection_memory_suppresses_recommendation(personal_agent, adaptation_service):
    """Test #13: Rejected recommendation is stored and not endlessly re-proposed."""
    person_id = "test-learner-loop-5"
    
    # 1. Reject an action
    await personal_agent.record_rejected_recommendation(person_id, "EXPLANATION_STYLE", "MISSION_ONLY", "User wants practical code.")
    
    # 2. Trigger learning signal that would normally suggest EXPLANATION_STYLE
    signal = LearningSignal(
        person_id=person_id,
        type="REPEATED_STRUGGLE",
        subject="Recursion",
        source_event_id="sub_3",
        evidence_ids=["sub_3"],
        impact_scope="MISSION_ONLY"
    )
    
    micro = await adaptation_service.handle_learning_signal_adaptation(person_id, signal, "stage_01")
    
    # The micro-adaptation should be suppressed because it was rejected
    assert micro is None
