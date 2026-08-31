from datetime import datetime
from typing import List, Dict, Any
from backend.core.assessment_schemas import AssessmentDefinition, AssessmentItem, AssessmentResult, AssessmentResponse

# --- 1. RIASEC Definition ---
RIASEC_ITEMS = [
    AssessmentItem(id="r1", construct="Realistic", text="I like to build, repair, or maintain things.", scale=[{"value": 1, "label": "Strongly Dislike"}, {"value": 5, "label": "Strongly Like"}]),
    AssessmentItem(id="i1", construct="Investigative", text="I like to analyze data and solve complex problems.", scale=[{"value": 1, "label": "Strongly Dislike"}, {"value": 5, "label": "Strongly Like"}]),
    AssessmentItem(id="a1", construct="Artistic", text="I enjoy expressing myself through art, music, or writing.", scale=[{"value": 1, "label": "Strongly Dislike"}, {"value": 5, "label": "Strongly Like"}]),
    AssessmentItem(id="s1", construct="Social", text="I enjoy helping, teaching, or counseling others.", scale=[{"value": 1, "label": "Strongly Dislike"}, {"value": 5, "label": "Strongly Like"}]),
    AssessmentItem(id="e1", construct="Enterprising", text="I like leading projects and persuading others.", scale=[{"value": 1, "label": "Strongly Dislike"}, {"value": 5, "label": "Strongly Like"}]),
    AssessmentItem(id="c1", construct="Conventional", text="I prefer organized, structured, and detail-oriented work.", scale=[{"value": 1, "label": "Strongly Dislike"}, {"value": 5, "label": "Strongly Like"}])
]

RIASEC_DEFINITION = AssessmentDefinition(
    id="riasec_v1",
    name="Holland Codes (RIASEC) Mini Assessment",
    version="1.0",
    construct="Career Interests",
    source="Adapted from O*NET Interest Profiler principles",
    license="Public Domain Adaptation",
    limitations="This is a mini-assessment for MVP purposes. It is not a statistically validated clinical instrument.",
    items=RIASEC_ITEMS,
    scoring_method="Sum of values per construct (R, I, A, S, E, C)",
    interpretation_rules="Higher scores indicate stronger interest in that dimension."
)

# --- 2. SCCT Definition ---
SCCT_ITEMS = [
    AssessmentItem(id="se1", construct="Self-Efficacy", text="How confident are you that you can learn a difficult subject if you practice consistently?", scale=[{"value": 1, "label": "Not Confident"}, {"value": 5, "label": "Very Confident"}]),
    AssessmentItem(id="oe1", construct="Outcome Expectations", text="How strongly do you expect your target career to provide the lifestyle you want?", scale=[{"value": 1, "label": "Not Strongly"}, {"value": 5, "label": "Very Strongly"}]),
    AssessmentItem(id="pb1", construct="Perceived Barriers", text="What constraints may make this path difficult? (Time, Money, Location, None)", response_type="open")
]

SCCT_DEFINITION = AssessmentDefinition(
    id="scct_v1",
    name="Social Cognitive Career Theory Indicators",
    version="1.0",
    construct="Career Beliefs and Constraints",
    source="Inspired by SCCT academic framework",
    license="Internal",
    limitations="Self-reported non-clinical diagnostic.",
    items=SCCT_ITEMS,
    scoring_method="Raw capture for LLM synthesis. No numerical aggregation.",
    interpretation_rules="Analyzed by ADK Agent."
)

# --- 3. Learning Profile Tasks ---
LEARNING_ITEMS = [
    AssessmentItem(id="lt1", construct="Recall", text="What is the definition of a variable in programming?", response_type="open"),
    AssessmentItem(id="lt2", construct="Application", text="If you wanted to store a user's age, how would you write that in code?", response_type="open")
]

LEARNING_DEFINITION = AssessmentDefinition(
    id="learning_v1",
    name="Learning & Reasoning Tasks",
    version="1.0",
    construct="Observable Cognitive Signals",
    source="PATHMIND internal tasks",
    license="Internal",
    limitations="Extremely small sample size. Should not be generalized as intelligence.",
    items=LEARNING_ITEMS,
    scoring_method="Agent evaluation of task responses.",
    interpretation_rules="Evaluates recall vs application vs transfer."
)

class AssessmentEngine:
    def __init__(self):
        self.assessments = {
            RIASEC_DEFINITION.id: RIASEC_DEFINITION,
            SCCT_DEFINITION.id: SCCT_DEFINITION,
            LEARNING_DEFINITION.id: LEARNING_DEFINITION
        }

    def get_assessment(self, assessment_id: str) -> AssessmentDefinition:
        return self.assessments.get(assessment_id)

    def get_all_assessments(self) -> List[AssessmentDefinition]:
        return list(self.assessments.values())

    def score_riasec(self, responses: List[AssessmentResponse]) -> Dict[str, int]:
        scores = {"R": 0, "I": 0, "A": 0, "S": 0, "E": 0, "C": 0}
        for resp in responses:
            if resp.item_id == "r1": scores["R"] += int(resp.response_value)
            if resp.item_id == "i1": scores["I"] += int(resp.response_value)
            if resp.item_id == "a1": scores["A"] += int(resp.response_value)
            if resp.item_id == "s1": scores["S"] += int(resp.response_value)
            if resp.item_id == "e1": scores["E"] += int(resp.response_value)
            if resp.item_id == "c1": scores["C"] += int(resp.response_value)
        return scores

    def process_submission(self, person_id: str, assessment_id: str, responses: List[AssessmentResponse]) -> AssessmentResult:
        definition = self.get_assessment(assessment_id)
        if not definition:
            raise ValueError(f"Assessment {assessment_id} not found")

        calculated_scores = {}
        if assessment_id == "riasec_v1":
            calculated_scores = self.score_riasec(responses)
        else:
            # For SCCT and Learning, we just pass raw responses to the ADK agent for interpretation
            calculated_scores = {"status": "pending_agent_review"}

        return AssessmentResult(
            person_id=person_id,
            assessment_id=assessment_id,
            version=definition.version,
            timestamp=datetime.utcnow().isoformat(),
            raw_responses=responses,
            calculated_scores=calculated_scores
        )
