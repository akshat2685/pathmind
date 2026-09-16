import pytest
from fastapi.testclient import TestClient
from backend.main import app
from backend.services.store import FirestoreStore

client = TestClient(app)

@pytest.fixture
def clean_store():
    return FirestoreStore()

def test_complete_guided_journey_state_machine(clean_store):
    """
    Validates the end-to-end continuous journey state machine:
    1. NAME -> Canonical person ID created & persisted immediately
    2. ASPIRATION & STAGE -> Grounded evidence requirements returned
    3. EVIDENCE -> Evaluates evidence and generates domain-neutral assessment blueprint
    4. ACTUAL ASSESSMENT -> Evaluates responses and produces verified baseline profile
    5. PATHWAY DISCOVERY -> 2-3 transparent candidate paths
    6. USER CHOICE & HIDDEN ROADMAP -> Generates multi-phase roadmap with Phase 1 active
    7. EVIDENCE-GATED PROGRESSION -> Backend evaluates milestone evidence (PASS/REINFORCE)
    """
    # 1. NAME -> PERSON CREATED IMMEDIATELY (Requirement 3)
    learner_name = "Ananya Roy"
    init_res = client.post("/api/orchestrate/journey/init", json={"name": learner_name})
    assert init_res.status_code == 200
    init_data = init_res.json()
    assert "person_id" in init_data
    person_id = init_data["person_id"]
    assert person_id.startswith("scholar_ananya")
    assert init_data["step"] == 1
    assert init_data["step_name"] == "ASPIRATION"

    headers = {"X-Person-ID": person_id}

    # Verify state endpoint retrieves the created person (Rehydration test)
    state_res = client.get("/api/orchestrate/journey/state", headers=headers)
    assert state_res.status_code == 200
    state_data = state_res.json()
    assert state_data["person_id"] == person_id
    assert state_data["name"] == learner_name
    assert state_data["step"] == 1

    # 2. ASPIRATION & LEARNER STAGE -> EVIDENCE REQUIREMENTS
    aspiration = "Bioinformatics and Genomic Data Science Specialist"
    stage = "college"
    constraints = ["12 hours weekly", "focus on python & clinical genetics"]
    asp_res = client.post(
        "/api/orchestrate/journey/aspiration",
        json={"aspiration": aspiration, "stage": stage, "constraints": constraints},
        headers=headers
    )
    assert asp_res.status_code == 200
    asp_data = asp_res.json()
    assert asp_data["step"] == 2
    assert asp_data["aspiration"] == aspiration
    assert asp_data["stage"] == stage
    assert "evidence_requirements" in asp_data
    reqs = asp_data["evidence_requirements"]
    assert len(reqs.get("recommended_evidence", [])) >= 2

    # 3. EVIDENCE SUBMISSION -> EVALUATION & ASSESSMENT BLUEPRINT
    evidence_payload = {
        "evidence": [
            {
                "source": "github_repo",
                "type": "link",
                "name": "variant-calling-pipeline",
                "description": "BWA-MEM and GATK pipeline implementation for exome sequencing",
                "url": "https://github.com/example/variant-caller",
                "confidence": "HIGH",
                "timestamp": "2026-09-16T12:00:00Z"
            },
            {
                "source": "case_study",
                "type": "project_description",
                "name": "CRISPR Off-Target Analysis",
                "description": "Deep learning approach to predict CRISPR-Cas9 cleavage propensity across human genome",
                "confidence": "HIGH",
                "timestamp": "2026-09-16T12:00:00Z"
            }
        ]
    }
    ev_res = client.post("/api/orchestrate/journey/evidence", json=evidence_payload, headers=headers)
    assert ev_res.status_code == 200
    ev_data = ev_res.json()
    assert ev_data["step"] == 3
    assert "assessment_blueprint" in ev_data
    blueprint = ev_data["assessment_blueprint"]
    assert len(blueprint["items"]) >= 3
    assert any("foundation" in item["item_id"] for item in blueprint["items"])

    # 4. ACTUAL ASSESSMENT SUBMISSION -> BASELINE PROFILE
    assessment_responses = {
        "responses": [
            {
                "item_id": "q1_foundation",
                "response_value": "Sequence alignment utilizes dynamic programming matrices (Smith-Waterman for local alignment) to score matches, mismatches, and affine gap penalties."
            },
            {
                "item_id": "q2_scenario",
                "response_value": "First run FastQC quality control on raw FASTQ files, then align reads with BWA-MEM against GRCh38, sort BAM with Samtools, and mark PCR duplicates."
            },
            {
                "item_id": "q3_tradeoff",
                "response_value": "The trade-off between sensitivity and false discovery in variant calling: lowering quality thresholds detects rare somatic mutations but risks calling sequencing artifacts."
            },
            {
                "item_id": "q4_efficacy",
                "response_value": 4
            }
        ]
    }
    assess_res = client.post("/api/orchestrate/journey/assessment", json=assessment_responses, headers=headers)
    if assess_res.status_code != 200:
        print("ASSESS_ERROR:", assess_res.text)
    assert assess_res.status_code == 200
    assess_data = assess_res.json()
    assert assess_data["step"] == 4
    assert "baseline_profile" in assess_data
    baseline = assess_data["baseline_profile"]
    assert baseline["person_id"] == person_id
    assert "interest_vector" in baseline

    # 5. PATHWAY DISCOVERY -> 2-3 GROUNDED CANDIDATE PATHS
    paths_res = client.post("/api/orchestrate/journey/discover-paths", headers=headers)
    assert paths_res.status_code == 200
    paths_data = paths_res.json()
    candidate_paths = paths_data["candidate_paths"]
    assert 1 <= len(candidate_paths) <= 3
    chosen_path = candidate_paths[0]

    # 6. USER CHOICE & HIDDEN ROADMAP (ACTIVE PHASE 1)
    select_res = client.post(
        "/api/orchestrate/journey/select-path",
        json={"selected_path_id": chosen_path["path_id"]},
        headers=headers
    )
    assert select_res.status_code == 200
    select_data = select_res.json()
    roadmap = select_data["roadmap"]
    assert roadmap["total_stages"] >= 3
    assert roadmap["active_stage"] is not None
    assert roadmap["active_stage"]["locked"] is False

    # Verify future stages are locked
    locked_stages = [s for s in roadmap["stages"] if s["locked"] is True]
    assert len(locked_stages) >= 1

    # 7. EVIDENCE-GATED PROGRESSION
    active_stage = roadmap["active_stage"]
    mission_id = active_stage["missions"][0]["mission_id"] if active_stage.get("missions") else "mission_01_modular_parser"
    
    code_submission = {
        "stage_id": active_stage["stage_id"],
        "mission_id": mission_id,
        "content_payload": {
            "code": "def parse_fasta(seq_stream: list) -> list:\n    return [{'id': s['id'], 'seq': s['seq'].upper()} for s in seq_stream]\ndef test_parse_fasta():\n    sample = [{'id': 'seq1', 'seq': 'atcg'}]\n    assert parse_fasta(sample) == [{'id': 'seq1', 'seq': 'ATCG'}]"
        }
    }
    phase_ev_res = client.post("/api/orchestrate/journey/submit-phase-evidence", json=code_submission, headers=headers)
    assert phase_ev_res.status_code == 200
    phase_ev_data = phase_ev_res.json()
    assert "evaluation" in phase_ev_data
    assert phase_ev_data["evaluation"]["status"] in ["PASS", "REINFORCE"]
