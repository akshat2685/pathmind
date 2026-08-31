import asyncio
from backend.services.assessment import AssessmentEngine
from backend.core.assessment_schemas import AssessmentResponse
from backend.services.counseling import CounselingAgent
from backend.services.store import FirestoreStore
import json

async def run_demo():
    print("Initializing PATHMIND Assessment & Counseling Engine Demo...")
    
    engine = AssessmentEngine()
    store = FirestoreStore()
    agent = CounselingAgent()
    
    person_id = "demo-user-12th-grade"
    print(f"\n--- Running scenario for Person ID: {person_id} ---")
    
    # 1. RIASEC Assessment (High Investigative/Enterprising, Low Artistic)
    print("1. Submitting RIASEC Assessment Responses...")
    riasec_responses = [
        AssessmentResponse(item_id="r1", response_value=4, timestamp="now"),
        AssessmentResponse(item_id="i1", response_value=5, timestamp="now"),
        AssessmentResponse(item_id="a1", response_value=2, timestamp="now"),
        AssessmentResponse(item_id="s1", response_value=3, timestamp="now"),
        AssessmentResponse(item_id="e1", response_value=4, timestamp="now"),
        AssessmentResponse(item_id="c1", response_value=3, timestamp="now")
    ]
    
    riasec_result = engine.process_submission(person_id, "riasec_v1", riasec_responses)
    await store.save_assessment_result(person_id, riasec_result.model_dump(mode="json"))
    print(f"RIASEC Calculated Scores: {riasec_result.calculated_scores}")
    
    # 2. SCCT Assessment
    print("\n2. Submitting SCCT Assessment Responses...")
    scct_responses = [
        AssessmentResponse(item_id="se1", response_value=5, timestamp="now"), # High self-efficacy
        AssessmentResponse(item_id="oe1", response_value=4, timestamp="now"),
        AssessmentResponse(item_id="pb1", response_value="I am worried about the cost of a 4-year degree.", timestamp="now")
    ]
    scct_result = engine.process_submission(person_id, "scct_v1", scct_responses)
    await store.save_assessment_result(person_id, scct_result.model_dump(mode="json"))
    
    # 3. Learning Tasks
    print("\n3. Submitting Learning Task Responses...")
    learning_responses = [
        AssessmentResponse(item_id="lt1", response_value="A variable is a container for data.", timestamp="now"),
        AssessmentResponse(item_id="lt2", response_value="let userAge = 18;", timestamp="now")
    ]
    learning_result = engine.process_submission(person_id, "learning_v1", learning_responses)
    await store.save_assessment_result(person_id, learning_result.model_dump(mode="json"))
    
    # 4. Trigger Counseling Synthesis
    print("\n4. Triggering ADK Counseling Synthesis...")
    
    # The agent detects this contradiction: stated low interest vs behavioral evidence.
    background_context = """
    Reported Preference: "I hate programming."
    Behavioral Evidence: Student has built 4 mobile apps and participated in 2 hackathons.
    Age: 12th Grade
    """
    
    all_results = [riasec_result, scct_result, learning_result]
    profile = agent.synthesize_profile(person_id, all_results, background_context)
    
    print("\n--- SYNTHESIZED COUNSELING PROFILE ---")
    print(json.dumps(profile.model_dump(), indent=2))

if __name__ == "__main__":
    asyncio.run(run_demo())
