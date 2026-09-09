import pytest
from backend.services.artifact_service import ArtifactService
from backend.services.step_verification_service import StepVerificationService
from backend.core.artifact_schemas import CanonicalArtifact
from backend.core.learning_resource_schemas import StepVerificationSubmission
from backend.services.store import FirestoreStore

@pytest.fixture
def clean_store():
    store = FirestoreStore()
    store._in_memory_persons.clear()
    return store

@pytest.fixture
def artifact_service(clean_store):
    return ArtifactService(store=clean_store)

@pytest.fixture
def step_service(clean_store):
    return StepVerificationService(store=clean_store)

@pytest.mark.asyncio
async def test_real_artifact_ingestion_github(artifact_service):
    payload = {
        "source": "GITHUB",
        "url": "https://github.com/scholar-user/fastapi-distributed-engine",
        "title": "FastAPI Distributed Engine",
        "description": "High throughput async backend service.",
        "languages": {"Python": 85000, "Shell": 1200},
        "has_tests": True,
        "has_ci": True,
        "readme": "A robust distributed backend engine with automated unit tests."
    }
    person_ctx = {"name": "Scholar User", "github_username": "scholar-user"}
    
    artifact = await artifact_service.ingest_artifact("person_alex", payload, person_ctx)
    
    assert artifact.artifact_id.startswith("art_")
    assert artifact.source == "GITHUB"
    assert artifact.ownership_status == "VERIFIED"
    assert artifact.verification_status == "VERIFIED"
    assert artifact.analysis is not None
    assert len(artifact.analysis.observations) > 0
    assert any(o.is_demonstrated and "Python" in o.detail for o in artifact.analysis.observations)
    assert artifact.analysis.dimensions.testing_evidence == "AUTOMATED_UNIT_TESTS"

@pytest.mark.asyncio
async def test_mentioned_vs_demonstrated_separation(artifact_service):
    payload = {
        "source": "GITHUB",
        "url": "https://github.com/scholar-user/simple-api",
        "title": "Simple API",
        "languages": {"Python": 15000},
        "has_tests": False,
        "readme": "This project mentions Kubernetes and Kafka integration in the roadmap."
    }
    person_ctx = {"name": "Scholar User", "github_username": "scholar-user"}
    
    artifact = await artifact_service.ingest_artifact("person_alex", payload, person_ctx)
    
    # Python is demonstrated
    demo_obs = [o for o in artifact.analysis.observations if o.is_demonstrated]
    assert any("Python" in o.detail for o in demo_obs)
    
    # Kubernetes and Kafka are mentioned in text only, not demonstrated
    unverified_claims = artifact.analysis.unverified_claims
    assert any("Kubernetes" in c or "Kafka" in c for c in unverified_claims)

@pytest.mark.asyncio
async def test_ownership_verification_and_tenant_isolation(artifact_service):
    # Foreign repo where owner does not match learner
    payload = {
        "source": "GITHUB",
        "url": "https://github.com/random-stranger/unrelated-project",
        "title": "Stranger Project",
        "languages": {"Python": 5000}
    }
    person_ctx = {"name": "Scholar User", "github_username": "scholar-user"}
    
    artifact = await artifact_service.ingest_artifact("person_alex", payload, person_ctx)
    assert artifact.ownership_status == "UNVERIFIED"
    assert artifact.verification_status == "UNVERIFIED"

    # Tenant isolation: Person B cannot view Person A's artifacts
    arts_alex = await artifact_service.store.get_person_artifacts("person_alex")
    arts_bob = await artifact_service.store.get_person_artifacts("person_bob")
    assert len(arts_alex) == 1
    assert len(arts_bob) == 0

@pytest.mark.asyncio
async def test_duplicate_detection_and_versioning(artifact_service):
    url = "https://github.com/scholar-user/evolutionary-repo"
    person_ctx = {"name": "Scholar User", "github_username": "scholar-user"}
    
    # Version 1
    art_v1 = await artifact_service.ingest_artifact("person_alex", {
        "source": "GITHUB", "url": url, "languages": {"Python": 10000}
    }, person_ctx)
    assert art_v1.version == 1
    
    # Version 2 (same repo submitted with updated tests)
    art_v2 = await artifact_service.ingest_artifact("person_alex", {
        "source": "GITHUB", "url": url, "languages": {"Python": 25000}, "has_tests": True
    }, person_ctx)
    
    assert art_v2.version == 2
    assert art_v2.artifact_id == art_v1.artifact_id
    assert len(art_v2.history) == 1
    
    # Should not duplicate in person's list
    all_arts = await artifact_service.store.get_person_artifacts("person_alex")
    assert len(all_arts) == 1

@pytest.mark.asyncio
async def test_candidate_promotion_to_canonical_evidence(artifact_service):
    payload = {
        "source": "GITHUB",
        "url": "https://github.com/scholar-user/verified-backend",
        "title": "Verified Backend",
        "languages": {"Python": 40000},
        "has_tests": True
    }
    person_ctx = {"name": "Scholar User", "github_username": "scholar-user"}
    artifact = await artifact_service.ingest_artifact("person_alex", payload, person_ctx)
    
    evidence = await artifact_service.promote_capability_to_evidence(
        person_id="person_alex",
        artifact_id=artifact.artifact_id,
        capability_name="Python Implementation",
        stage_id="stage_backend_foundation"
    )
    
    assert evidence.evidence_id.startswith("ev_")
    assert evidence.verification_status == "VERIFIED"
    assert evidence.quality == "VERIFIED_STRONG"
    
    # Check SkillMasteryProfile updated
    profiles = await artifact_service.store.get_skill_mastery_profiles("person_alex")
    assert "Python Implementation" in profiles
    assert profiles["Python Implementation"]["mastery_state"] == "APPLICATION"

@pytest.mark.asyncio
async def test_artifact_defense_mode_workflow(artifact_service):
    payload = {
        "source": "GITHUB",
        "url": "https://github.com/scholar-user/architectural-project",
        "title": "Architectural Project",
        "languages": {"Python": 30000}
    }
    person_ctx = {"name": "Scholar User", "github_username": "scholar-user"}
    artifact = await artifact_service.ingest_artifact("person_alex", payload, person_ctx)
    
    # 1. Start defense session
    session = await artifact_service.start_artifact_defense("person_alex", artifact.artifact_id)
    assert len(session.questions) >= 3
    assert session.status == "IN_PROGRESS"
    
    # 2. Submit technical defense answers
    answers = [
        {
            "question_id": session.questions[0].question_id,
            "answer_text": "We chose Python and separated the architecture into controllers, services, and repository layers because of high modularity and strict boundary isolation."
        },
        {
            "question_id": session.questions[1].question_id,
            "answer_text": "The primary tradeoff was in-memory caching vs database roundtrips. We tested both and selected bounded LRU caching to preserve state consistency."
        }
    ]
    
    evaluated = await artifact_service.submit_artifact_defense("person_alex", session.session_id, answers)
    assert evaluated.status == "DEFENSE_ACCEPTED"
    assert len(evaluated.capabilities_upgraded) > 0

@pytest.mark.asyncio
async def test_claim_validation(artifact_service):
    payload = {
        "source": "GITHUB",
        "url": "https://github.com/scholar-user/data-pipeline",
        "title": "Data Pipeline",
        "languages": {"Python": 50000},
        "has_tests": True
    }
    person_ctx = {"name": "Scholar User", "github_username": "scholar-user"}
    await artifact_service.ingest_artifact("person_alex", payload, person_ctx)
    
    # Supported claim
    res_supported = await artifact_service.validate_claim("person_alex", "I have built a Python data pipeline with verified tests.")
    assert res_supported.status == "SUPPORTED"
    assert len(res_supported.supporting_artifacts) > 0
    
    # Unverified claim (technology not in portfolio)
    res_unverified = await artifact_service.validate_claim("person_alex", "I have 5 years experience managing production Rust microservices.")
    assert res_unverified.status == "UNVERIFIED"

@pytest.mark.asyncio
async def test_procedural_learning_guide_and_verified_resources(step_service):
    guide = step_service.generate_learning_guide("stage_backend_core", "FastAPI REST API Systems")
    
    assert guide.stage_id == "stage_backend_core"
    assert len(guide.procedural_steps) == 4
    
    # Verify Step sequence: Theory -> Reference Repo -> Build -> Verify
    assert guide.procedural_steps[0].phase_category == "THEORY"
    assert guide.procedural_steps[1].phase_category == "CODE_STUDY"
    assert guide.procedural_steps[2].phase_category == "HANDS_ON"
    assert guide.procedural_steps[3].phase_category == "VERIFICATION"
    
    # Verify all resource URLs are authentic and verified
    for res in guide.verified_resources:
        assert any(domain in res.url for domain in ["youtube.com", "github.com", "docs.python.org", "fastapi.tiangolo.com", "react.dev", "postgresql.org"])

@pytest.mark.asyncio
async def test_zero_assumption_step_verification(step_service):
    # 1. Empty submission rejected
    empty_sub = StepVerificationSubmission(stage_id="stage_test", step_number=3, payload={})
    res_empty = await step_service.verify_step("person_alex", empty_sub)
    assert res_empty.status == "INSUFFICIENT_EVIDENCE"
    
    # 2. Syntax error in code implementation rejected
    broken_code_sub = StepVerificationSubmission(
        stage_id="stage_test",
        step_number=3,
        payload={"code": "def broken_func(:\n    return True"}
    )
    res_broken = await step_service.verify_step("person_alex", broken_code_sub)
    assert res_broken.status == "REINFORCE_REQUIRED"
    assert any("Syntax error" in c for c in res_broken.missing_criteria)
    
    # 3. Valid code with test assertions passes
    valid_test_sub = StepVerificationSubmission(
        stage_id="stage_test",
        step_number=4,
        payload={
            "code": "def test_calculate_sum():\n    assert 2 + 2 == 4\n    assert sum([1, 2, 3]) == 6\n",
            "tests_output": "2 passed in 0.05s"
        }
    )
    res_valid = await step_service.verify_step("person_alex", valid_test_sub)
    assert res_valid.status == "VERIFIED"
    assert len(res_valid.observed_facts) > 0

@pytest.mark.asyncio
async def test_personal_agent_meta_learning(step_service):
    sub = StepVerificationSubmission(
        stage_id="stage_test",
        step_number=4,
        payload={
            "code": "def test_logic():\n    assert True is True\n",
            "tests_output": "1 passed"
        }
    )
    await step_service.verify_step("person_alex", sub)
    
    profiles = await step_service.store.get_learning_strategy_profiles("person_alex")
    assert len(profiles) > 0
    project_profile = next((p for p in profiles if p["strategy_dimension"] == "PROJECT_BASED"), None)
    assert project_profile is not None
    assert project_profile["status"] == "SUPPORTED"

@pytest.mark.asyncio
async def test_revocation_safety(artifact_service):
    payload = {
        "source": "GITHUB",
        "url": "https://github.com/scholar-user/to-be-revoked",
        "title": "Temporary Repo"
    }
    person_ctx = {"name": "Scholar User", "github_username": "scholar-user"}
    artifact = await artifact_service.ingest_artifact("person_alex", payload, person_ctx)
    assert artifact.verification_status in ["VERIFIED", "PARTIALLY_VERIFIED"]
    
    success = await artifact_service.revoke_or_delete_artifact("person_alex", artifact.artifact_id)
    assert success is True
    
    updated = await artifact_service.store.get_canonical_artifact("person_alex", artifact.artifact_id)
    assert updated["verification_status"] == "REVOKED"
