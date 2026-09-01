import json
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
from pydantic import BaseModel
from fastapi import APIRouter, Depends, HTTPException, Header
from backend.core.assessment_schemas import (
    CounselingProfile,
    AssessmentResult,
    AssessmentResponse,
    CounselingChatRequest,
    CounselingMessage,
    CounselingMemoryItem
)
from backend.services.store import FirestoreStore
from backend.services.counseling import CounselingAgent

router = APIRouter(prefix="/api/counseling", tags=["Counseling"])
store = FirestoreStore()
agent = CounselingAgent()

class SynthesizeRequest(BaseModel):
    person_id: Optional[str] = "demo-user"
    goals: Optional[List[str]] = []
    constraints: Optional[List[str]] = []
    evidence: Optional[List[Dict[str, Any]]] = []
    assessment_results: Optional[List[Dict[str, Any]]] = []

def get_person_id(x_person_id: Optional[str] = Header(None)) -> str:
    if not x_person_id:
        return "demo-user"
    return x_person_id

@router.get("/profile", response_model=Optional[CounselingProfile])
async def get_counseling_profile(person_id: str = Depends(get_person_id)):
    profile_data = await store.get_counseling_profile(person_id)
    if not profile_data:
        # Generate default preliminary profile from stored results
        results = await store.get_assessment_results(person_id)
        if results:
            parsed_results = [AssessmentResult(**r) for r in results]
            profile = agent.synthesize_profile(person_id, parsed_results)
            await store.save_counseling_profile(person_id, profile.model_dump(mode="json"))
            return profile
        return None
    return CounselingProfile(**profile_data)

@router.post("/synthesize", response_model=CounselingProfile)
async def synthesize_profile(
    body: Optional[SynthesizeRequest] = None,
    person_id: str = Depends(get_person_id)
):
    try:
        active_person_id = (body.person_id if body and body.person_id else None) or person_id
        goals = body.goals if body and body.goals else []
        constraints = body.constraints if body and body.constraints else []
        evidence = body.evidence if body and body.evidence else []

        # Parse inline assessment results if provided
        if body and body.assessment_results and len(body.assessment_results) > 0:
            parsed_results = []
            for r in body.assessment_results:
                raw_resp = []
                raw_dict_or_list = r.get("raw_responses", {})
                if isinstance(raw_dict_or_list, dict):
                    for k, v in raw_dict_or_list.items():
                        raw_resp.append(AssessmentResponse(item_id=str(k), response_value=v))
                elif isinstance(raw_dict_or_list, list):
                    for item in raw_dict_or_list:
                        if isinstance(item, dict):
                            raw_resp.append(AssessmentResponse(**item))
                
                parsed_results.append(
                    AssessmentResult(
                        person_id=active_person_id,
                        assessment_id=r.get("assessment_id", "riasec_v1"),
                        version=r.get("version", "1.0.0"),
                        timestamp=r.get("timestamp", datetime.now(timezone.utc).isoformat()),
                        raw_responses=raw_resp,
                        calculated_scores=r.get("computed_scores", r.get("calculated_scores", {})),
                        dimension_scores=r.get("dimension_scores")
                    )
                )
        else:
            # Fallback to store
            stored_results = await store.get_assessment_results(active_person_id)
            if not stored_results:
                # Default baseline assessment
                stored_results = [{
                    "person_id": active_person_id,
                    "assessment_id": "riasec_v1",
                    "version": "1.0.0",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "raw_responses": [
                        {"item_id": "r1", "response_value": 4},
                        {"item_id": "r2", "response_value": 4},
                        {"item_id": "i1", "response_value": 5},
                        {"item_id": "i2", "response_value": 5},
                        {"item_id": "a1", "response_value": 2},
                        {"item_id": "s1", "response_value": 3},
                        {"item_id": "e1", "response_value": 4},
                        {"item_id": "c1", "response_value": 3}
                    ],
                    "calculated_scores": {
                        "normalized_vector": {"R": 75.0, "I": 100.0, "A": 25.0, "S": 50.0, "E": 75.0, "C": 50.0}
                    },
                    "dimension_scores": {"R": 75.0, "I": 100.0, "A": 25.0, "S": 50.0, "E": 75.0, "C": 50.0}
                }]
            parsed_results = [AssessmentResult(**r) for r in stored_results]

        profile = agent.synthesize_profile(
            person_id=active_person_id,
            assessment_results=parsed_results,
            goals=goals,
            constraints=constraints,
            evidence_items=evidence
        )

        # Persist synthesized profile
        await store.save_counseling_profile(active_person_id, profile.model_dump(mode="json"))

        return profile
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to synthesize profile: {str(e)}")

@router.post("/chat", response_model=CounselingMessage)
async def counseling_chat(
    req: CounselingChatRequest,
    person_id: str = Depends(get_person_id)
):
    try:
        active_person_id = req.person_id or person_id
        profile_data = await store.get_counseling_profile(active_person_id)
        
        if profile_data:
            profile = CounselingProfile(**profile_data)
        else:
            # Synthesize fallback profile
            profile = agent.synthesize_deterministic_profile(
                person_id=active_person_id,
                assessment_results=[],
                goals=[],
                constraints=[],
                evidence_items=[]
            )

        reply = agent.counsel_chat(
            person_id=active_person_id,
            user_message=req.message,
            profile=profile,
            history=req.history or []
        )

        # Store episodic interaction memory fact
        memory_item = CounselingMemoryItem(
            fact_id=f"mem-{int(datetime.now(timezone.utc).timestamp())}",
            person_id=active_person_id,
            category="INFERRED",
            claim=f"Discussed counseling query: '{req.message[:80]}'",
            evidence=["Interactive counseling session"],
            confidence="MEDIUM"
        )
        await store.save_counseling_memory(active_person_id, memory_item.model_dump(mode="json"))

        return reply
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Counseling chat failed: {str(e)}")

@router.get("/demo", response_model=CounselingProfile)
async def get_demo_scenario():
    """
    Deterministic Demo Scenario:
    Person: Demo Person (Class 12)
    Strengths: Mathematics, Computer Science
    Activities: Robotics, Hackathons
    Projects: 2 technology projects
    Goal: Explore AI/ML and engineering
    """
    demo_person_id = "demo-scholar-class12"
    
    demo_evidence = [
        {
            "name": "Autonomous Line-Following & Maze Robot",
            "type": "project",
            "description": "Hardware build with Arduino/C++ utilizing ultrasonic & infrared sensor arrays.",
            "source": "Robotics Club Lead"
        },
        {
            "name": "Hackathon AI Data Classifier",
            "type": "project",
            "description": "Python scikit-learn machine learning web app built during 36-hour national hackathon.",
            "source": "National Student Hackathon 2025"
        }
    ]

    demo_riasec_result = AssessmentResult(
        person_id=demo_person_id,
        assessment_id="riasec_v1",
        version="1.0.0",
        timestamp=datetime.now(timezone.utc).isoformat(),
        raw_responses=[
            AssessmentResponse(item_id="r1", response_value=5),
            AssessmentResponse(item_id="r2", response_value=4),
            AssessmentResponse(item_id="i1", response_value=5),
            AssessmentResponse(item_id="i2", response_value=5),
            AssessmentResponse(item_id="a1", response_value=3),
            AssessmentResponse(item_id="a2", response_value=2),
            AssessmentResponse(item_id="s1", response_value=3),
            AssessmentResponse(item_id="s2", response_value=3),
            AssessmentResponse(item_id="e1", response_value=4),
            AssessmentResponse(item_id="e2", response_value=4),
            AssessmentResponse(item_id="c1", response_value=3),
            AssessmentResponse(item_id="c2", response_value=3)
        ],
        calculated_scores={
            "normalized_vector": {
                "R": 87.5,
                "I": 100.0,
                "A": 37.5,
                "S": 50.0,
                "E": 75.0,
                "C": 50.0
            }
        },
        dimension_scores={
            "R": 87.5,
            "I": 100.0,
            "A": 37.5,
            "S": 50.0,
            "E": 75.0,
            "C": 50.0
        }
    )

    demo_scct_result = AssessmentResult(
        person_id=demo_person_id,
        assessment_id="scct_v1",
        version="1.0.0",
        timestamp=datetime.now(timezone.utc).isoformat(),
        raw_responses=[
            AssessmentResponse(item_id="se1", response_value=5),
            AssessmentResponse(item_id="se2", response_value=4),
            AssessmentResponse(item_id="oe1", response_value=5),
            AssessmentResponse(item_id="oe2", response_value=5),
            AssessmentResponse(item_id="cs1", response_value="School STEM Lab, Robotics Mentor, Online open-source communities"),
            AssessmentResponse(item_id="cb1", response_value="Balancing Class 12 board exam prep with deep-dive technical project time")
        ],
        calculated_scores={
            "self_efficacy_average": 4.5,
            "outcome_expectation_average": 5.0,
            "self_efficacy_level": "HIGH",
            "contextual_supports": ["School STEM Lab", "Robotics Mentor"],
            "contextual_barriers": ["Balancing Class 12 board exams"]
        }
    )

    demo_learning_result = AssessmentResult(
        person_id=demo_person_id,
        assessment_id="learning_v1",
        version="1.0.0",
        timestamp=datetime.now(timezone.utc).isoformat(),
        raw_responses=[
            AssessmentResponse(item_id="lt_recall", response_value="Stack is LIFO; Queue is FIFO."),
            AssessmentResponse(item_id="lt_explain", response_value="B-Tree indexes reduce search complexity from O(N) to O(log N) at the cost of disk space and write overhead."),
            AssessmentResponse(item_id="lt_apply", response_value="Stream log files in chunks using memory-mapped files or generators with a rolling hash set."),
            AssessmentResponse(item_id="lt_error", response_value="Loop condition `<= length` causes ArrayIndexOutOfBoundsException on 0-indexed arrays."),
            AssessmentResponse(item_id="lt_reason", response_value="Monolith simplifies initial developer velocity and deployment until bounded contexts emerge.")
        ],
        calculated_scores={
            "tasks_submitted": 5,
            "status": "ready_for_agent_evaluation"
        }
    )

    profile = agent.synthesize_profile(
        person_id=demo_person_id,
        assessment_results=[demo_riasec_result, demo_scct_result, demo_learning_result],
        goals=["Explore AI/ML and Robotics Systems Engineering"],
        constraints=["Class 12 Student (Balancing board exams)"],
        evidence_items=demo_evidence
    )

    await store.save_counseling_profile(demo_person_id, profile.model_dump(mode="json"))
    return profile
