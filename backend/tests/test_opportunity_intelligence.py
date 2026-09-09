import pytest
from datetime import datetime, timezone, timedelta
from fastapi.testclient import TestClient

from backend.main import app
from backend.services.opportunity_matching_engine import OpportunityMatchingEngine
from backend.providers.opportunity_provider import (
    VerifiedOpenOpportunityProvider,
    ExternalPublicOpportunityProviderAdapter,
    deduplicate_opportunities
)
from backend.core.opportunity_schemas import (
    CanonicalOpportunity,
    CreatePreparationPlanRequest
)
from backend.services.store import FirestoreStore

@pytest.fixture
def clean_store():
    store = FirestoreStore()
    store._in_memory_persons.clear()
    return store

@pytest.fixture
def matching_engine(clean_store):
    return OpportunityMatchingEngine(store=clean_store)

@pytest.mark.asyncio
async def test_provider_fetch_and_deduplication(matching_engine):
    opps = await matching_engine.get_all_opportunities()
    assert len(opps) >= 4
    
    # Verify provenance and authentic fields
    for o in opps:
        assert o.verification_status == "VERIFIED"
        assert o.application_url.startswith("https://")
        assert len(o.requirements) > 0
        assert o.provider is not None

    # Test deduplication
    duplicated = opps + [opps[0]]
    deduped = deduplicate_opportunities(duplicated)
    assert len(deduped) == len(opps)

@pytest.mark.asyncio
async def test_expired_opportunities_excluded():
    provider = VerifiedOpenOpportunityProvider()
    # Add an expired opportunity
    past_date = (datetime.now(timezone.utc) - timedelta(days=10)).isoformat()
    expired_opp = CanonicalOpportunity(
        provider="Expired Provider",
        provider_record_id="exp_01",
        type="INTERNSHIP",
        title="Expired Summer Internship",
        organization="Past Organization",
        description="Expired posting",
        location="Remote",
        eligibility="Open",
        requirements=["Python"],
        deadline=past_date,
        application_url="https://example.com/apply",
        source_url="https://example.com/source",
        status="ACTIVE"
    )
    provider._opportunities.append(expired_opp)

    active_opps = await provider.fetch_opportunities()
    assert not any(o.provider_record_id == "exp_01" for o in active_opps)

@pytest.mark.asyncio
async def test_explainable_match_result(matching_engine):
    person_id = "person_alex"
    # Seed an artifact with verified skills
    await matching_engine.store.save_canonical_artifact(person_id, {
        "artifact_id": "art_alex_test",
        "title": "Python Data Processing Pipeline",
        "type": "CODE_REPOSITORY",
        "analysis": {
            "capability_mappings": [
                {"capability_name": "Python", "status": "VERIFIED", "is_promoted_to_evidence": True},
                {"capability_name": "Git", "status": "VERIFIED", "is_promoted_to_evidence": True}
            ]
        }
    })

    matches = await matching_engine.match_opportunities_for_person(person_id)
    assert len(matches) > 0

    first = matches[0]
    assert first.fit_state in ["STRONG_MATCH", "GOOD_MATCH", "PARTIAL_MATCH"]
    assert len(first.matched_requirements) > 0
    assert any("Python" in mr for mr in first.matched_requirements)
    assert len(first.why_it_matters) > 0
    assert len(first.next_step) > 0

@pytest.mark.asyncio
async def test_unknown_profile_fields_rule(matching_engine):
    person_id = "person_alex_unspecified"
    # Ensure profile has no education explicitly set
    profile = await matching_engine.career_engine.get_or_create_canonical_profile(person_id)
    profile.education = []
    await matching_engine.store.save_career_profile(person_id, profile.model_dump())

    matches = await matching_engine.match_opportunities_for_person(person_id)
    assert len(matches) > 0

    # Rule: Missing education must be flagged in unknowns, NEVER marked as INELIGIBLE
    opp_match = next((m for m in matches if m.opportunity.education_requirements), None)
    if opp_match:
        assert len(opp_match.unknowns) >= 1
        assert any("education" in u.lower() for u in opp_match.unknowns)
        assert opp_match.fit_state != "INELIGIBLE"

@pytest.mark.asyncio
async def test_fit_vs_readiness_separation(matching_engine):
    person_id = "person_beginner_student"
    # New student with Python only
    profile = await matching_engine.career_engine.get_or_create_canonical_profile(person_id)
    profile.skills = ["Python"]
    await matching_engine.store.save_career_profile(person_id, profile.model_dump())

    matches = await matching_engine.match_opportunities_for_person(person_id)
    assert len(matches) > 0

    # For specialized roles requiring PyTorch/ROS/C++, candidate has goal alignment but gaps
    stretch_match = next((m for m in matches if len(m.gaps) >= 2), None)
    if stretch_match:
        assert stretch_match.readiness_state in ["STRETCH", "NEAR_READY"]
        assert stretch_match.decision_recommendation == "RECOMMEND_PREPARING_FIRST"
        assert len(stretch_match.tradeoffs) > 0

@pytest.mark.asyncio
async def test_goal_relevance_dominance(matching_engine):
    person_id = "person_alex"
    # Set explicit goal
    await matching_engine.store.save_career_goal(
        person_id,
        {
            "goal_id": "goal_ai",
            "person_id": person_id,
            "target_role": "Applied Machine Learning Systems Engineer",
            "target_industry": "Artificial Intelligence",
            "version": 1
        }
    )

    matches = await matching_engine.match_opportunities_for_person(person_id)
    top_matches = matches[:2]
    # AI / Open Source ML opportunities should rank higher than generic roles
    assert any("ai" in m.opportunity.title.lower() or "machine learning" in m.opportunity.title.lower() or "open source" in m.opportunity.title.lower() for m in top_matches)

@pytest.mark.asyncio
async def test_opportunity_driven_execution_plan(matching_engine):
    person_id = "person_alex"
    opps = await matching_engine.get_all_opportunities()
    target_opp = opps[0]

    plan = await matching_engine.generate_preparation_plan(
        person_id=person_id,
        opportunity_id=target_opp.opportunity_id,
        spawn_to_execution_engine=True
    )

    assert plan.opportunity_id == target_opp.opportunity_id
    assert len(plan.required_actions) >= 3
    assert plan.deadline_feasibility == "FEASIBLE"

    # Verify actions were created in Execution Engine
    actions = await matching_engine.store.get_person_actions(person_id)
    assert len(actions) >= 3
    assert any(target_opp.organization in a["title"] or "Resume" in a["title"] for a in actions)

@pytest.mark.asyncio
async def test_artifact_grounded_interview_prep(matching_engine):
    person_id = "person_alex"
    opps = await matching_engine.get_all_opportunities()
    target_opp = opps[0]

    prep = await matching_engine.generate_interview_prep(person_id, target_opp.opportunity_id)
    assert prep.opportunity_id == target_opp.opportunity_id
    assert len(prep.technical_competency_questions) >= 3
    assert len(prep.project_defense_questions) >= 1
    assert len(prep.gap_reinforcement_focus) >= 1

@pytest.mark.asyncio
async def test_provider_outage_source_unavailable():
    adapter = ExternalPublicOpportunityProviderAdapter(endpoint_url="https://invalid-non-existent-domain-xyz.org/api")
    opps = await adapter.fetch_opportunities()
    assert opps == []
    assert adapter.get_status_code() == "OPPORTUNITY_SOURCE_UNAVAILABLE"
    assert adapter.is_connected() is False

@pytest.mark.asyncio
async def test_tenant_isolation_opportunities(matching_engine):
    # Person A generates a preparation plan
    opps = await matching_engine.get_all_opportunities()
    await matching_engine.generate_preparation_plan(
        person_id="person_alex",
        opportunity_id=opps[0].opportunity_id,
        spawn_to_execution_engine=True
    )

    alex_actions = await matching_engine.store.get_person_actions("person_alex")
    bob_actions = await matching_engine.store.get_person_actions("person_bob")

    assert len(alex_actions) >= 3
    assert len(bob_actions) == 0

def test_fastapi_opportunity_endpoints():
    client = TestClient(app)
    headers = {"x-person-id": "test-scholar-alex"}

    # 1. List opportunities
    res = client.get("/api/opportunities")
    assert res.status_code == 200
    opps = res.json()
    assert len(opps) >= 4
    opp_id = opps[0]["opportunity_id"]

    # 2. Matched opportunities
    match_res = client.get("/api/opportunities/matched", headers=headers)
    assert match_res.status_code == 200
    matched = match_res.json()
    assert len(matched) >= 4
    assert "fit_state" in matched[0]
    assert "readiness_state" in matched[0]

    # 3. Preparation Plan
    plan_res = client.post(f"/api/opportunities/{opp_id}/preparation-plan", headers=headers, json={"spawn_actions_to_execution_engine": True})
    assert plan_res.status_code == 200
    assert "required_actions" in plan_res.json()

    # 4. Interview Prep
    prep_res = client.get(f"/api/opportunities/{opp_id}/interview-prep", headers=headers)
    assert prep_res.status_code == 200
    assert len(prep_res.json()["technical_competency_questions"]) >= 3
