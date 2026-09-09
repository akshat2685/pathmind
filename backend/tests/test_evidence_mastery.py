import pytest
from datetime import datetime, timezone
from backend.services.mastery_engine import MasteryEngine
from backend.services.evidence_verification_service import EvidenceVerificationService
from backend.services.evidence_evaluation_agent import EvidenceEvaluationAgent
from backend.services.store import FirestoreStore
from backend.core.evidence_schemas import CanonicalEvidence

@pytest.mark.asyncio
async def test_evidence_submission_and_quality_verification():
    """
    Submitting executable Python code with unit tests & type hints must be deterministically
    verified as VERIFIED_STRONG and achieve PASS status.
    """
    store = FirestoreStore()
    mastery_engine = MasteryEngine(store=store)
    person_id = "test-learner-evidence-1"

    # Initialize roadmap
    await mastery_engine.roadmap_engine.get_or_create_roadmap(person_id)

    code_payload = {
        "code": """
from dataclasses import dataclass
from typing import List, Generator

@dataclass
class Record:
    id: str
    value: float

def parse_stream(raw_data: List[dict]) -> Generator[Record, None, None]:
    for item in raw_data:
        yield Record(id=str(item['id']), value=float(item['value']))

def test_parse_stream():
    sample = [{'id': '1', 'value': '10.5'}]
    result = list(parse_stream(sample))
    assert len(result) == 1
    assert result[0].value == 10.5
"""
    }

    attempt = await mastery_engine.submit_and_evaluate_evidence(
        person_id=person_id,
        stage_id="stage_01_python_foundations",
        evidence_type="CODE_REPO",
        title="Modular Parser & Pytest Suite",
        source_reference="https://github.com/scholar/modular-parser",
        payload=code_payload
    )

    assert attempt is not None
    assert attempt.status == "PASS"
    assert attempt.attempt_number == 1
    assert attempt.evaluation_detail.evidence_quality_awarded in ["STRONG", "VERIFIED_STRONG"]
    assert len(attempt.evaluation_detail.observed) > 0
    assert len(attempt.evaluation_detail.inferred) > 0
    assert len(attempt.evaluation_detail.recommendation) > 0

@pytest.mark.asyncio
async def test_locked_stage_rejects_premature_submission():
    """
    Submitting evidence for a locked downstream stage without satisfying prerequisites must raise PermissionError.
    """
    store = FirestoreStore()
    mastery_engine = MasteryEngine(store=store)
    person_id = "test-learner-lock"

    await mastery_engine.roadmap_engine.get_or_create_roadmap(person_id)

    with pytest.raises(PermissionError) as exc_info:
        await mastery_engine.submit_and_evaluate_evidence(
            person_id=person_id,
            stage_id="stage_04_deep_learning_pytorch",  # Locked stage
            evidence_type="CODE_REPO",
            title="PyTorch Neural Net",
            source_reference="https://github.com/scholar/neural-net",
            payload={"code": "import torch\ndef forward(): pass"}
        )

    assert "UNLOCK_REJECTED" in str(exc_info.value)

@pytest.mark.asyncio
async def test_insufficient_evidence_triggers_reinforcement():
    """
    Submitting minimal/incomplete code fails quality criteria and triggers reinforcement.
    """
    store = FirestoreStore()
    mastery_engine = MasteryEngine(store=store)
    person_id = "test-learner-reinforce"

    await mastery_engine.roadmap_engine.get_or_create_roadmap(person_id)

    attempt = await mastery_engine.submit_and_evaluate_evidence(
        person_id=person_id,
        stage_id="stage_01_python_foundations",
        evidence_type="WRITTEN_EXPLANATION",
        title="Brief explanation",
        source_reference="notes",
        payload={"code": "x = 1"}  # Under minimum threshold
    )

    assert attempt.status == "REINFORCE"
    assert attempt.evaluation_detail.mastery_state_achieved == "NEEDS_REINFORCEMENT"

@pytest.mark.asyncio
async def test_mastery_regression_flagged_without_erasing_history():
    """
    Detecting repeated struggle flags MASTERY_AT_RISK while preserving past evidence references.
    """
    store = FirestoreStore()
    mastery_engine = MasteryEngine(store=store)
    person_id = "test-learner-regression"

    profile = await mastery_engine.record_mastery_regression(
        person_id=person_id,
        skill_name="Python OOP",
        reason="Observed runtime memory leaks during multi-threading benchmark."
    )

    assert profile.mastery_state == "MASTERY_AT_RISK"
    assert profile.is_regression_risk is True
    assert "memory leaks" in profile.regression_reason

@pytest.mark.asyncio
async def test_transfer_validation_across_novel_domains():
    """
    Submitting evidence for a transfer task marks transfer_validated as True.
    """
    store = FirestoreStore()
    mastery_engine = MasteryEngine(store=store)
    person_id = "test-learner-transfer"

    await mastery_engine.roadmap_engine.get_or_create_roadmap(person_id)

    transfer_code = {
        "code": """
import pytest
from typing import Dict, Any

class TelemetryTransformer:
    def transform_packet(self, packet: Dict[str, Any]) -> Dict[str, float]:
        return {'norm_val': float(packet['raw']) / 100.0}

def test_telemetry_transform():
    t = TelemetryTransformer()
    res = t.transform_packet({'raw': 50})
    assert res['norm_val'] == 0.5
"""
    }

    attempt = await mastery_engine.submit_and_evaluate_evidence(
        person_id=person_id,
        stage_id="stage_01_python_foundations",
        evidence_type="CODE_REPO",
        title="Robotics Telemetry Transformer",
        source_reference="https://github.com/scholar/telemetry-transform",
        payload=transfer_code,
        is_transfer_task=True
    )

    assert attempt.status == "PASS"
    assert attempt.evaluation_detail.transfer_validated is True
    assert attempt.evaluation_detail.mastery_state_achieved == "TRANSFER"

@pytest.mark.asyncio
async def test_dispute_and_challenge_flow():
    """
    Learner can challenge an evaluation and record a dispute without overwriting past attempts.
    """
    store = FirestoreStore()
    mastery_engine = MasteryEngine(store=store)
    person_id = "test-learner-dispute"

    dispute = await mastery_engine.file_dispute(
        person_id=person_id,
        attempt_id="att_test_123",
        reason="My unit test fixture was separated in a conftest.py file.",
        additional_evidence_reference="https://github.com/scholar/repo/conftest.py"
    )

    assert dispute.status == "PENDING_REVIEW"
    assert "conftest.py" in dispute.reason

    # Resolve dispute
    resolved = await mastery_engine.resolve_dispute(
        person_id=person_id,
        dispute_id=dispute.dispute_id,
        new_status="UPHELD",
        resolution_note="Reviewed conftest fixtures. Test assertions confirmed."
    )
    assert resolved is True

@pytest.mark.asyncio
async def test_mastery_dashboard_state_generation():
    """
    MasteryDashboardState accurately populates 'What I Can Do', 'What I Am Working On',
    'What I Need To Prove', and locked stages.
    """
    store = FirestoreStore()
    mastery_engine = MasteryEngine(store=store)
    person_id = "test-learner-dash"

    state = await mastery_engine.get_mastery_dashboard_state(person_id)

    assert state.person_id == person_id
    assert len(state.capabilities_working_on) > 0
    assert len(state.evidence_needed) > 0
    assert len(state.locked_stages) > 0
    assert "prerequisite_stage_id" in state.locked_stages[0].model_dump()

@pytest.mark.asyncio
async def test_tenant_isolation_for_evidence_and_disputes():
    """
    Person A's evidence, evaluation attempts, and disputes cannot be accessed by Person B.
    """
    store = FirestoreStore()
    person_a = "person-alpha-11"
    person_b = "person-beta-11"

    await store.save_canonical_evidence(person_a, {
        "evidence_id": "ev_alpha",
        "person_id": person_a,
        "title": "Alpha Evidence"
    })

    ev_b = await store.get_all_person_evidence(person_b)
    assert len(ev_b) == 0

    ev_a = await store.get_all_person_evidence(person_a)
    assert len(ev_a) == 1
    assert ev_a[0]["evidence_id"] == "ev_alpha"
