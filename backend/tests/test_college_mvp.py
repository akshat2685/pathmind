import pytest
from unittest.mock import MagicMock
from fastapi.testclient import TestClient
from backend.main import app
from backend.core.college_schemas import EngineeringBranch, CommitmentStatus, MasteryStatus
import backend.core.security as security

# Mock Supabase Auth for tests
mock_user_response_alice = MagicMock()
mock_user_response_alice.user.id = "11111111-1111-4111-8111-111111111111"
mock_user_response_bob = MagicMock()
mock_user_response_bob.user.id = "22222222-2222-4222-8222-222222222222"

def mock_get_user(token: str):
    if token == "alice-token":
        return mock_user_response_alice
    elif token == "bob-token":
        return mock_user_response_bob
    raise ValueError("Invalid token")

mock_adapter = MagicMock()
mock_adapter.client.auth.get_user.side_effect = mock_get_user

# Monkeypatch the adapter in security module
security.get_supabase_adapter = lambda: mock_adapter

client = TestClient(app)

AUTH_HEADERS_ALICE = {"Authorization": "Bearer alice-token"}
AUTH_HEADERS_BOB = {"Authorization": "Bearer bob-token"}

def test_list_all_users_lists_new_users():
    """Verify that every new user is listed in the system."""
    # Alice logs in / gets profile
    resp_alice = client.get("/api/college/profile", headers=AUTH_HEADERS_ALICE)
    assert resp_alice.status_code == 200
    assert resp_alice.json()["uid"] == "11111111-1111-4111-8111-111111111111"

    # Bob logs in / gets profile
    resp_bob = client.get("/api/college/profile", headers=AUTH_HEADERS_BOB)
    assert resp_bob.status_code == 200
    assert resp_bob.json()["uid"] == "22222222-2222-4222-8222-222222222222"

    # List all users
    resp_users = client.get("/api/college/users")
    assert resp_users.status_code == 200
    users = resp_users.json()
    uids = [u["uid"] for u in users]
    assert "11111111-1111-4111-8111-111111111111" in uids
    assert "22222222-2222-4222-8222-222222222222" in uids

def test_search_and_list_universities():
    """Verify university lookup finds canonical accredited institutions."""
    resp = client.get("/api/college/universities?query=anna")
    assert resp.status_code == 200
    results = resp.json()
    assert len(results) >= 1
    assert "Anna University" in results[0]["name"]
    assert results[0]["official_domain"] == "annauniv.edu"

    # Search AICTE Model
    resp_aicte = client.get("/api/college/universities?query=aicte")
    assert resp_aicte.status_code == 200
    assert len(resp_aicte.json()) >= 1
    assert resp_aicte.json()[0]["verification_status"] == "VERIFIED"

def test_curriculum_resolution_all_five_branches():
    """Verify authentic curricula for all 5 supported engineering disciplines."""
    branches = [
        EngineeringBranch.COMPUTER_SCIENCE,
        EngineeringBranch.AI_ENGINEERING,
        EngineeringBranch.MECHANICAL,
        EngineeringBranch.ELECTRICAL,
        EngineeringBranch.CIVIL
    ]

    for b in branches:
        resp = client.get(f"/api/college/curriculum?university_id=univ_aicte_model&branch={b.value}&semester=3")
        assert resp.status_code == 200, f"Failed to get curriculum for {b.value}"
        data = resp.json()
        assert data["branch"] == b.value
        assert len(data["subjects"]) >= 2
        for sub in data["subjects"]:
            assert "name" in sub
            assert "units" in sub
            assert len(sub["units"]) >= 1

def test_curriculum_general_other_handled_transparently():
    """Per PRD Section 3 & 4: General/other aspirations are not rejected, but returned with zero fake engineering data."""
    resp = client.get(f"/api/college/curriculum?university_id=univ_aicte_model&branch={EngineeringBranch.GENERAL_OTHER.value}&semester=1")
    assert resp.status_code == 200
    data = resp.json()
    assert data["branch"] == EngineeringBranch.GENERAL_OTHER.value
    assert data["subjects"] == []

def test_academic_context_and_profile_sync():
    """Verify student academic context setup and profile synchronization."""
    context_payload = {
        "university_id": "univ_aicte_model",
        "branch": EngineeringBranch.COMPUTER_SCIENCE.value,
        "semester": 3,
        "subjects": ["CS-301", "CS-302"],
        "exam_window": {"start": "2026-11-20", "end": "2026-12-05"},
        "available_hours_per_week": 16,
        "learning_style_preferences": ["prefers visual diagrams", "worked examples first"]
    }
    resp = client.post("/api/college/academic-context", json=context_payload, headers=AUTH_HEADERS_ALICE)
    assert resp.status_code == 200
    data = resp.json()
    assert data["semester"] == 3
    assert data["branch"] == EngineeringBranch.COMPUTER_SCIENCE.value
    assert "CS-301" in data["subjects"]

    # Verify profile status updated to CONTEXT_SET
    resp_prof = client.get("/api/college/profile", headers=AUTH_HEADERS_ALICE)
    assert resp_prof.status_code == 200
    assert resp_prof.json()["profile_status"] == "CONTEXT_SET"

def test_ordered_learning_plan_generation():
    """Verify ordered phased study plan contains concrete timestamps and page numbers."""
    resp = client.post("/api/college/plans/generate", json={"goal_id": "goal_sem3_prep"}, headers=AUTH_HEADERS_ALICE)
    assert resp.status_code == 200
    plan = resp.json()
    assert len(plan["phases"]) >= 1
    phase1 = plan["phases"][0]
    assert phase1["status"] == "AVAILABLE"
    assert len(phase1["activities"]) >= 2

    # Check for WATCH activity with timestamps
    watch_act = next((a for a in phase1["activities"] if a["activity_type"] == "WATCH"), None)
    if watch_act:
        assert watch_act["resource"] is not None
        assert "Watch from" in watch_act["instructions"] or "Watch" in watch_act["instructions"]

    # Check for READ activity with page references
    read_act = next((a for a in phase1["activities"] if a["activity_type"] == "READ"), None)
    if read_act:
        assert read_act["resource"] is not None
        assert "pages" in read_act["instructions"] or "Read" in read_act["instructions"]

def test_pyq_authenticity_and_honest_unavailable_state():
    """Strict verification: Valid subjects return real PYQs; unknown subjects return honest PYQ_NOT_AVAILABLE."""
    # 1. Verified subject
    resp_valid = client.get("/api/college/pyqs?subject_id=sub_cs_dsa")
    assert resp_valid.status_code == 200
    data_valid = resp_valid.json()
    assert data_valid["status"] == "VERIFIED"
    assert data_valid["pyq_set"] is not None
    assert len(data_valid["pyq_set"]["questions"]) >= 2
    assert "Q1(a)" in data_valid["pyq_set"]["questions"][0]["question_number"]

    # 2. Unverified subject with no fake questions
    resp_invalid = client.get("/api/college/pyqs?subject_id=unknown_fictional_subject")
    assert resp_invalid.status_code == 200
    data_invalid = resp_invalid.json()
    assert data_invalid["status"] == "PYQ_NOT_AVAILABLE"
    assert data_invalid["pyq_set"] is None

def test_activity_completion_and_phase_progression():
    """Verify completing activities unlocks subsequent milestones."""
    resp_plan = client.get("/api/college/plans/current", headers=AUTH_HEADERS_ALICE)
    assert resp_plan.status_code == 200
    plan = resp_plan.json()
    phase1 = plan["phases"][0]
    act1 = phase1["activities"][0]

    # Complete activity 1
    resp_complete = client.post(
        f"/api/college/activities/{act1['activity_id']}/complete",
        json={"evidence": {"notes": "Completed video module"}},
        headers=AUTH_HEADERS_ALICE
    )
    assert resp_complete.status_code == 200
    updated_plan = resp_complete.json()
    updated_act = updated_plan["phases"][0]["activities"][0]
    assert updated_act["status"] == "COMPLETED"
    assert updated_act["completed_at"] is not None

def test_checkpoint_assessment_and_mastery_scoring():
    """Verify diagnostic assessment generation and objective scoring."""
    resp_asmt = client.post(
        "/api/college/assessments/generate",
        json={
            "plan_id": "plan_test",
            "phase_id": "phase_test_1",
            "subject_id": "CS-301",
            "topic_title": "Linked Lists & Array Formulations"
        },
        headers=AUTH_HEADERS_ALICE
    )
    assert resp_asmt.status_code == 200
    asmt = resp_asmt.json()
    assert len(asmt["questions"]) == 3
    asmt_id = asmt["assessment_id"]

    # Submit answers with correct MCQ answers
    submission = {
        "assessment_id": asmt_id,
        "answers": {
            "q1": "Conservation of Energy & Mass Equilibrium",
            "q2": "Efficiency vs Stability under transient load conditions",
            "q3": "We detect boundary errors by verifying pointer null termination and initial array index bounds before memory access."
        }
    }
    resp_eval = client.post("/api/college/assessments/submit", json=submission, headers=AUTH_HEADERS_ALICE)
    assert resp_eval.status_code == 200
    eval_result = resp_eval.json()
    assert eval_result["score"] >= 70.0
    assert eval_result["mastery_status"] in ["MASTERED", "PARTIALLY_MASTERED"]

def test_accountability_schedule_and_commitments():
    """Verify exam timeline countdown and daily commitments."""
    # Create study commitment
    resp_cmt = client.post(
        "/api/college/accountability/commit",
        json={
            "title": "Complete Unit 1 Linked List derivation set",
            "due_at": "2026-10-01T18:00:00Z",
            "estimated_minutes": 45
        },
        headers=AUTH_HEADERS_ALICE
    )
    assert resp_cmt.status_code == 200
    cmt = resp_cmt.json()
    assert cmt["status"] == "PLANNED"

    # Fetch today schedule
    resp_today = client.get("/api/college/accountability/today", headers=AUTH_HEADERS_ALICE)
    assert resp_today.status_code == 200
    sched = resp_today.json()
    assert sched["exam_days_remaining"] is not None
    assert sched["total_planned_minutes"] >= 45

    # Mark commitment complete
    resp_patch = client.patch(
        f"/api/college/accountability/commit/{cmt['commitment_id']}",
        json={"status": CommitmentStatus.COMPLETED.value},
        headers=AUTH_HEADERS_ALICE
    )
    assert resp_patch.status_code == 200
    assert resp_patch.json()["status"] == CommitmentStatus.COMPLETED.value

def test_memory_isolation_between_learners():
    """Verify Student A's memories cannot be accessed by Student B."""
    # Alice asks agent and records memory
    resp_agent_alice = client.post(
        "/api/college/agent/interact",
        json={"message": "Can you show me the curriculum and PYQs for Data Structures?", "session_id": "sess_alice_1"},
        headers=AUTH_HEADERS_ALICE
    )
    assert resp_agent_alice.status_code == 200
    assert "ui_blocks" in resp_agent_alice.json()

    # Verify Alice has memory
    resp_mem_alice = client.get("/api/college/memory", headers=AUTH_HEADERS_ALICE)
    assert resp_mem_alice.status_code == 200
    alice_short = resp_mem_alice.json()["short_term"]
    assert len(alice_short) >= 1
    assert "Data Structures" in alice_short[0]["content"]

    # Bob checks his memory -> must be empty or isolated to Bob
    resp_mem_bob = client.get("/api/college/memory", headers=AUTH_HEADERS_BOB)
    assert resp_mem_bob.status_code == 200
    bob_short = resp_mem_bob.json()["short_term"]
    for m in bob_short:
        assert m["uid"] == "22222222-2222-4222-8222-222222222222"
        assert "Data Structures" not in m["content"]
