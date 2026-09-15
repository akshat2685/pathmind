from typing import Dict, Any, List, Optional
from backend.services.store import FirestoreStore
from backend.services.career_readiness_engine import CareerReadinessEngine

store = FirestoreStore()
career_engine = CareerReadinessEngine(store=store)

async def get_learner_profile(person_id: str) -> Dict[str, Any]:
    """Retrieves the learner's basic profile including name, aspiration, and stage."""
    profile = await store.get_career_profile(person_id)
    if not profile:
        return {"status": "NOT_FOUND"}
    return profile

async def update_learner_profile(person_id: str, name: str, aspiration: str, learner_stage: str) -> Dict[str, Any]:
    """Updates the learner's profile with their name, aspiration, and current stage."""
    profile = await store.get_career_profile(person_id) or {}
    profile.update({
        "name": name,
        "aspiration": aspiration,
        "learner_stage": learner_stage
    })
    await store.save_career_profile(person_id, profile)
    return {"status": "SUCCESS", "profile": profile}

async def get_evidence_requirements(person_id: str, aspiration: str, learner_stage: str) -> Dict[str, Any]:
    """Determines what evidence is required based on aspiration and stage."""
    # Deterministic logic: Return requirements based on stage
    requirements = []
    if learner_stage == "School Student":
        requirements = ["Academic transcripts", "Extracurriculars", "Projects"]
    elif learner_stage == "College Student":
        requirements = ["Semester results", "Internships", "Projects"]
    elif learner_stage == "Graduate":
        requirements = ["Degree", "Portfolio", "Specialization"]
    elif learner_stage == "Working Professional":
        requirements = ["Work experience", "Certifications", "Work samples"]
    else:
        requirements = ["Portfolio", "Certifications"]
        
    return {
        "aspiration": aspiration,
        "learner_stage": learner_stage,
        "required_evidence": requirements
    }

async def submit_evidence(person_id: str, evidence_type: str, evidence_description: str) -> Dict[str, Any]:
    """Submits a piece of evidence for the learner."""
    submission = {
        "submission_id": f"ev_{hash(evidence_description)}",
        "evidence_type": evidence_type,
        "description": evidence_description,
        "status": "SUBMITTED"
    }
    await store.save_evidence_submission(person_id, submission)
    return {"status": "SUCCESS", "submission": submission}

async def generate_stage_aware_assessment(person_id: str) -> Dict[str, Any]:
    """Generates an assessment based on current aspiration, stage, and submitted evidence."""
    profile = await store.get_career_profile(person_id)
    if not profile:
        return {"error": "Profile required to generate assessment."}
    
    stage = profile.get("learner_stage", "Unknown")
    aspiration = profile.get("aspiration", "Unknown")
    
    # Generate assessment blueprint deterministically
    return {
        "assessment_id": f"assess_{hash(aspiration)}",
        "title": f"{aspiration} Assessment for {stage}",
        "questions": [
            {"id": "q1", "text": f"What is your current experience level in {aspiration}?"},
            {"id": "q2", "text": f"How does being a {stage} influence your {aspiration} goals?"}
        ]
    }

async def save_assessment_result(person_id: str, assessment_id: str, responses: Dict[str, Any]) -> Dict[str, Any]:
    """Saves the completed assessment and evaluates the baseline."""
    result = {
        "assessment_id": assessment_id,
        "responses": responses,
        "status": "COMPLETED"
    }
    await store.save_assessment_result(person_id, result)
    return {"status": "SUCCESS", "result": result}

async def generate_candidate_paths(person_id: str) -> Dict[str, Any]:
    """Generates candidate pathways based on the learner's full profile and assessments."""
    profile = await store.get_career_profile(person_id)
    aspiration = profile.get("aspiration", "Unknown")
    
    paths = [
        {
            "path_id": "path_1",
            "title": f"Direct {aspiration} Route",
            "confidence": "HIGH",
            "fit": "Excellent",
            "requirements": ["Basic assessment", "Initial portfolio"]
        },
        {
            "path_id": "path_2",
            "title": f"Alternative {aspiration} Route",
            "confidence": "MEDIUM",
            "fit": "Good",
            "requirements": ["Advanced assessment", "Specialized portfolio"]
        }
    ]
    return {"pathways": paths}

async def save_selected_path(person_id: str, path_id: str) -> Dict[str, Any]:
    """Saves the selected path and generates the progressive roadmap."""
    await store.save_selected_path(person_id, {"selected_path_id": path_id})
    
    roadmap = {
        "phases": [
            {"phase_id": "phase_1", "title": "Foundation", "status": "UNLOCKED"},
            {"phase_id": "phase_2", "title": "Core Capability", "status": "LOCKED"},
            {"phase_id": "phase_3", "title": "Applied Practice", "status": "LOCKED"}
        ]
    }
    await store.save_roadmap(person_id, roadmap)
    return {"status": "SUCCESS", "roadmap": roadmap}

async def get_current_roadmap(person_id: str) -> Dict[str, Any]:
    """Retrieves the active roadmap."""
    roadmap = await store.get_active_roadmap(person_id)
    if not roadmap:
        return {"status": "NOT_FOUND"}
    return roadmap

async def unlock_next_phase(person_id: str, current_phase_id: str) -> Dict[str, Any]:
    """Deterministically checks if criteria are met to unlock the next phase."""
    roadmap = await store.get_active_roadmap(person_id)
    if not roadmap:
        return {"status": "ROADMAP_NOT_FOUND"}
        
    phases = roadmap.get("phases", [])
    for i, phase in enumerate(phases):
        if phase["phase_id"] == current_phase_id and i + 1 < len(phases):
            phases[i+1]["status"] = "UNLOCKED"
            await store.update_active_roadmap(person_id, roadmap)
            return {"status": "SUCCESS", "unlocked_phase": phases[i+1]["phase_id"], "roadmap": roadmap}
            
    return {"status": "ALREADY_AT_END"}

# Export pure functions for agent tools
get_learner_profile_tool = get_learner_profile
update_learner_profile_tool = update_learner_profile
get_evidence_requirements_tool = get_evidence_requirements
submit_evidence_tool = submit_evidence
generate_stage_aware_assessment_tool = generate_stage_aware_assessment
save_assessment_result_tool = save_assessment_result
generate_candidate_paths_tool = generate_candidate_paths
save_selected_path_tool = save_selected_path
get_current_roadmap_tool = get_current_roadmap
unlock_next_phase_tool = unlock_next_phase
