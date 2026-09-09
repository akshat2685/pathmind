import pytest
from datetime import datetime, timezone
from fastapi.testclient import TestClient

from backend.main import app
from backend.services.store import FirestoreStore

client = TestClient(app)

@pytest.fixture
def clean_store():
    store = FirestoreStore()
    return store

def test_canonical_product_journey_e2e(clean_store):
    """
    Validates the complete 14-step Canonical Product Journey:
    1. Authenticate & System Readiness
    2. Personal Context Graph Inspection
    3. Psychometric & Practical Assessment Synthesis
    4. Empirical Career Trajectory Discovery
    5. Path Selection & Progressive Roadmap Generation
    6. Backend Stage Lock Enforcement
    7. Active Stage Evidence Submission
    8. Real Evidence Evaluation
    9. Mastery Profile & Dashboard State Verification
    10. Adaptive Replanning Impact Analysis & Proposal Approval
    11. Real Opportunity Matching (Fit vs Readiness Separation)
    12. Daily Execution Mission Tracking & Action Completion
    13. Second Brain Memory Ingestion & Query Recall
    14. Longitudinal Model State Assembly
    """
    person_id = "evaluator-engineer-2026"
    headers = {"X-Person-ID": person_id}

    # 1. AUTHENTICATE & SYSTEM READINESS
    health_res = client.get("/health/ready")
    assert health_res.status_code == 200
    assert health_res.json()["status"] == "ready"

    # 2. PERSONAL CONTEXT GRAPH INSPECTION
    context_res = client.get("/api/context/graph", headers=headers)
    assert context_res.status_code == 200
    graph = context_res.json()
    assert graph["person_id"] == person_id
    assert "capability_context" in graph
    assert "goal_context" in graph

    # 3. REAL ASSESSMENT & COUNSELING SYNTHESIS
    synthesis_payload = {
        "person_id": person_id,
        "goals": ["Become an AI & Machine Learning Systems Specialist"],
        "constraints": ["15 hours/week available"],
        "assessment_results": [
            {
                "assessment_id": "battery_holland_riasec",
                "raw_responses": {
                    "r1": 5, "r2": 4,  # High Realistic
                    "i1": 5, "i2": 5,  # High Investigative
                    "a1": 2, "a2": 2,  # Low Artistic
                    "s1": 3, "s2": 3,  # Moderate Social
                    "e1": 4, "e2": 3,  # Enterprising
                    "c1": 4, "c2": 4   # Conventional
                }
            },
            {
                "assessment_id": "practical_observable_tasks",
                "raw_responses": [
                    {"item_id": "task_python_oop", "response_value": "Implemented generator batching with type annotations"},
                    {"item_id": "task_architecture", "response_value": "Selected microservices for loose coupling"}
                ]
            }
        ]
    }
    synth_res = client.post("/api/counseling/synthesize", json=synthesis_payload, headers=headers)
    assert synth_res.status_code == 200
    counseling_profile = synth_res.json()
    assert counseling_profile["person_id"] == person_id
    assert len(counseling_profile["candidate_directions"]) >= 1

    # 4. CAREER DIRECTION & TRAJECTORY DISCOVERY
    discover_res = client.post(
        "/api/trajectories/discover",
        json={"goals": ["Become an Applied AI Engineer"], "constraints": ["15 hours/week available"]},
        headers=headers
    )
    assert discover_res.status_code == 200
    disc_data = discover_res.json()
    candidate_paths = disc_data["candidate_paths"]
    assert len(candidate_paths) >= 1
    selected_candidate = candidate_paths[0]

    # 5. SELECT PATH & GENERATE PROGRESSIVE ROADMAP
    select_payload = {
        "person_id": person_id,
        "selected_path_id": selected_candidate["path_id"],
        "selected_path": selected_candidate,
        "all_candidate_paths": candidate_paths,
        "selection_reason": "Strong alignment with investigative mathematics and systems programming"
    }
    select_res = client.post(
        "/api/trajectories/select",
        json=select_payload,
        headers=headers
    )
    assert select_res.status_code == 200
    assert select_res.json()["selected_path_id"] == selected_candidate["path_id"]

    roadmap_res = client.post(
        "/api/roadmap/generate",
        params={"path_id": "path_applied_ai_ml_systems"},
        headers=headers
    )
    assert roadmap_res.status_code == 200
    roadmap = roadmap_res.json()
    assert roadmap["total_stages"] >= 3
    assert roadmap["active_stage"] is not None
    active_stage = roadmap["active_stage"]
    assert active_stage["locked"] is False

    # 6. BACKEND LOCK ENFORCEMENT
    # Find a locked stage in the disclosed view
    locked_stages = [s for s in roadmap["stages"] if s["locked"] is True]
    assert len(locked_stages) >= 1
    locked_stage = locked_stages[0]

    # Directly requesting locked stage must be rejected by backend lock enforcement
    locked_stage_res = client.get(f"/api/roadmap/stage/{locked_stage['stage_id']}", headers=headers)
    assert locked_stage_res.status_code == 403
    assert "UNLOCK_REJECTED" in locked_stage_res.json()["detail"]

    # 7 & 8. REAL EVIDENCE SUBMISSION & EVALUATION ON ACTIVE STAGE
    active_mission = active_stage["missions"][0] if active_stage.get("missions") else None
    mission_id = active_mission["mission_id"] if active_mission else "mission_01_modular_parser"
    
    sub_payload = {
        "person_id": person_id,
        "roadmap_id": "rdm_applied_ai_ml_systems",
        "stage_id": active_stage["stage_id"],
        "mission_id": mission_id,
        "evidence_type": "CODE_REPO",
        "content_payload": {
            "code": "class BatchDataLoader:\n    def __init__(self, data: list):\n        self.data = data\n    def __iter__(self):\n        for item in self.data:\n            yield item\ndef test_batch_dataloader():\n    loader = BatchDataLoader([1, 2, 3])\n    assert list(loader) == [1, 2, 3]"
        }
    }
    eval_res = client.post("/api/roadmap/evidence/submit", json=sub_payload, headers=headers)
    assert eval_res.status_code == 200
    eval_result = eval_res.json()
    assert eval_result["status"] == "PASS"
    assert len(eval_result["demonstrated"]) >= 1

    # 9. MASTERY RECORD & DASHBOARD STATE VERIFICATION
    dashboard_res = client.get("/api/evidence/dashboard", headers=headers)
    assert dashboard_res.status_code == 200
    dashboard_state = dashboard_res.json()
    assert dashboard_state["person_id"] == person_id
    assert "skills_mastered" in dashboard_state
    assert "capabilities_working_on" in dashboard_state

    # 10. ADAPTIVE REPLANNING IMPACT ANALYSIS
    adapt_res = client.post(
        "/api/adaptation/constraint-change",
        json={"weekly_hours": 8, "preferred_format": "project-based"},
        headers=headers
    )
    assert adapt_res.status_code == 200
    adaptation = adapt_res.json()
    assert adaptation["person_id"] == person_id
    assert "impact_analysis" in adaptation
    assert adaptation["status"] in ["PENDING_APPROVAL", "APPROVED", "AUTO_APPLIED"]

    # Apply proposal deterministically with user consent
    decide_res = client.post(
        "/api/adaptation/decide",
        json={
            "adaptation_id": adaptation["adaptation_id"],
            "person_id": person_id,
            "action": "APPROVE",
            "user_feedback": "Approved 8h pacing adjustment"
        },
        headers=headers
    )
    assert decide_res.status_code == 200
    assert decide_res.json()["status"] == "APPROVED"

    # 11. REAL OPPORTUNITY MATCHING (FIT VS READINESS SEPARATION)
    opp_res = client.get("/api/opportunities/matched", headers=headers)
    assert opp_res.status_code == 200
    matched_opps = opp_res.json()
    assert isinstance(matched_opps, list)
    if len(matched_opps) > 0:
        top_opp = matched_opps[0]
        assert "fit_state" in top_opp
        assert "readiness_state" in top_opp
        assert "matched_requirements" in top_opp
        assert "gaps" in top_opp
        assert "unknowns" in top_opp

    # 12. EXECUTION ENGINE DAILY PLAN & ACTION COMPLETION
    daily_res = client.get("/api/execution/daily", headers=headers)
    assert daily_res.status_code == 200
    daily_plan = daily_res.json()
    assert daily_plan["person_id"] == person_id
    assert "primary_action" in daily_plan
    primary_action = daily_plan["primary_action"]

    if primary_action:
        action_id = primary_action["action_id"]
        complete_res = client.post(
            f"/api/execution/actions/{action_id}/complete",
            json={
                "outcome_state": "COMPLETED",
                "notes": "Verified passing unit test suite with 100% assertions satisfied"
            },
            headers=headers
        )
        assert complete_res.status_code == 200
        assert complete_res.json()["status"] == "COMPLETED"

    # 13. SECOND BRAIN RECALL & QUERY
    ingest_payload = {
        "topic": "Python Systems Programming",
        "nature": "MILESTONE",
        "memory_type": "CAPABILITY_BREAKTHROUGH",
        "title": "Demonstrated Generator Batching",
        "content": "Demonstrated type-annotated generator batching data loader with passing unit tests.",
        "context_tags": ["python", "generators", "batching"]
    }
    ingest_res = client.post("/api/memory/events", json=ingest_payload, headers=headers)
    assert ingest_res.status_code == 200

    brain_query_res = client.post(
        "/api/memory/query",
        json={"query": "How did I demonstrate generator batching?", "current_task_context": "data loading"},
        headers=headers
    )
    assert brain_query_res.status_code == 200
    brain_data = brain_query_res.json()
    assert brain_data["person_id"] == person_id
    assert brain_data["status"] in ["RESOLVED", "NO_RELEVANT_MEMORY"]
    assert "answer" in brain_data

    # 14. LONGITUDINAL LEARNER MODEL STATE ASSEMBLY
    longitudinal_res = client.get("/api/longitudinal/state", headers=headers)
    assert longitudinal_res.status_code == 200
    longitudinal_state = longitudinal_res.json()
    assert longitudinal_state["person_id"] == person_id
    assert "current_state_summary" in longitudinal_state
    assert "capability_history" in longitudinal_state
