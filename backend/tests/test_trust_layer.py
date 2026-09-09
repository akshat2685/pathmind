import pytest
from datetime import datetime, timezone
from backend.services.trust_provenance_service import TrustProvenanceService
from backend.services.recommendation_explanation_service import RecommendationExplanationService
from backend.services.store import FirestoreStore

@pytest.mark.asyncio
async def test_provenance_grounding_and_epistemic_classification():
    """
    TrustProvenanceService validates factual claims and assigns structured provenance with source type.
    """
    store = FirestoreStore()
    trust_service = TrustProvenanceService(store=store)
    person_id = "test-trust-learner-1"

    claim = await trust_service.verify_claim_provenance(
        person_id=person_id,
        claim_text="Robotics Software Engineers require proficiency in ROS2 and C++.",
        claim_category="FACT",
        source_type="ESCO",
        source_url="https://esco.ec.europa.eu/occupations/2152"
    )

    assert claim.claim_category == "FACT"
    assert claim.provenance is not None
    assert claim.provenance.source_type == "ESCO"
    assert claim.provenance.verification_status == "VERIFIED"
    assert claim.provenance.confidence == "HIGH"

@pytest.mark.asyncio
async def test_missing_evidence_resolves_to_unknown():
    """
    If a claim references a non-existent personal evidence ID, it resolves to UNKNOWN.
    """
    store = FirestoreStore()
    trust_service = TrustProvenanceService(store=store)
    person_id = "test-unknown-evidence"

    claim = await trust_service.verify_claim_provenance(
        person_id=person_id,
        claim_text="Learner has demonstrated Kubernetes cluster deployment.",
        claim_category="OBSERVATION",
        supporting_evidence_ids=["non_existent_ev_999"]
    )

    assert claim.claim_category == "UNKNOWN"
    assert claim.provenance.verification_status == "UNVERIFIED"
    assert claim.provenance.confidence == "INSUFFICIENT_EVIDENCE"

@pytest.mark.asyncio
async def test_safety_guardrails_block_clinical_and_guarantee_claims():
    """
    Deterministic safety guardrails block clinical diagnoses and salary/employment guarantees.
    """
    store = FirestoreStore()
    trust_service = TrustProvenanceService(store=store)

    # 1. Clinical Diagnosis Check
    res1 = trust_service.validate_safety_guardrails("Learner has symptoms of ADHD and bipolar disorder.")
    assert res1.is_safe is False
    assert res1.safety_category == "PSYCHOLOGICAL_OVERREACH"

    # 2. Employment Guarantee Check
    res2 = trust_service.validate_safety_guardrails("Completing this path provides a 100% guarantee you will be hired at Google.")
    assert res2.is_safe is False
    assert res2.safety_category == "EMPLOYMENT_GUARANTEE_VIOLATION"

    # 3. Safe Pedagogical Guidance
    res3 = trust_service.validate_safety_guardrails("Targeted unit test coverage will strengthen your software engineering portfolio.")
    assert res3.is_safe is True
    assert res3.safety_category == "PASSED"

@pytest.mark.asyncio
async def test_why_this_and_why_not_explainability():
    """
    RecommendationExplanationService provides grounded 'Why This?' and 'Why Not?' explanations.
    """
    store = FirestoreStore()
    explanation_service = RecommendationExplanationService(store=store)
    person_id = "test-explain-learner"

    await explanation_service.context_service.roadmap_engine.get_or_create_roadmap(person_id)

    rec = await explanation_service.generate_structured_recommendation(
        person_id=person_id,
        rec_type="NEXT_ACTION",
        title="Implement Asynchronous Message Broker",
        summary="Build distributed pub/sub pipeline in Python.",
        why_now="Satisfies Stage 02 distributed systems competency.",
        recommended_choice="Hands-on Redis Pub/Sub Project",
        alternative_choices=["Theoretical Lecture Series", "Fast Exam Certification"],
        options=[
            {"name": "Redis Project", "pace": "Self-paced", "proof": "Git Repo"},
            {"name": "Theory Course", "pace": "Fast", "proof": "Certificate"}
        ],
        tradeoffs=[
            "Practical code evidence satisfies hiring standards, whereas video certificates show exposure only."
        ],
        uncertainties=[
            "Concurrency throughput under 10k connections has not yet been benchmarked."
        ],
        facts=["Distributed systems role requirements demand practical concurrency evidence."],
        inferences=["Project evidence provides verifiable proof for hiring evaluations."]
    )

    explanation = await explanation_service.explain_recommendation(person_id, rec.recommendation_id)

    assert explanation.recommendation_id == rec.recommendation_id
    assert "Redis Pub/Sub" in explanation.why_this
    assert "Alternative options" in explanation.why_not_alternative
    assert len(explanation.facts_summary) > 0
    assert len(explanation.unknowns_summary) > 0

@pytest.mark.asyncio
async def test_user_autonomy_decision_and_feedback():
    """
    Learner can accept, decline, or choose alternatives, and provide structured feedback.
    """
    store = FirestoreStore()
    explanation_service = RecommendationExplanationService(store=store)
    person_id = "test-autonomy-learner"

    rec = await explanation_service.generate_structured_recommendation(
        person_id=person_id,
        rec_type="CAREER_DIRECTION",
        title="Target Specialization",
        summary="Choose Robotics or Backend Path",
        why_now="Foundational stage completed.",
        recommended_choice="Autonomous Robotics Path",
        alternative_choices=["Classical Backend Path"],
        options=[],
        tradeoffs=["Robotics requires physics simulation evidence."],
        uncertainties=[],
        facts=["Robotics roles list ROS2 as core requirement."],
        inferences=["Alignment with stated curiosity in autonomous systems."]
    )

    # 1. User accepts
    decided = await explanation_service.record_user_decision(
        person_id=person_id,
        recommendation_id=rec.recommendation_id,
        user_choice="Autonomous Robotics Path",
        notes="Learner confirmed preference."
    )
    assert decided is True

    updated_rec = await store.get_structured_recommendation_by_id(person_id, rec.recommendation_id)
    assert updated_rec["status"] == "ACCEPTED"

    # 2. User feedback
    fb = await explanation_service.record_feedback(
        person_id=person_id,
        recommendation_id=rec.recommendation_id,
        feedback_type="HELPFUL",
        notes="Grounded explanation helped clarify the tradeoffs."
    )
    assert fb.feedback_type == "HELPFUL"

@pytest.mark.asyncio
async def test_tenant_isolation_for_trust_layer():
    """
    Person A's recommendations and provenance records cannot be accessed by Person B.
    """
    store = FirestoreStore()
    person_a = "person-trust-a"
    person_b = "person-trust-b"

    await store.save_structured_recommendation(person_a, {
        "recommendation_id": "rec_a",
        "person_id": person_a,
        "title": "Alpha Recommendation",
        "status": "ACTIVE"
    })

    recs_b = await store.get_structured_recommendations(person_b)
    assert len(recs_b) == 0

    recs_a = await store.get_structured_recommendations(person_a)
    assert len(recs_a) == 1
    assert recs_a[0]["recommendation_id"] == "rec_a"
