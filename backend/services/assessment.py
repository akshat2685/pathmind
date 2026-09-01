from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
from backend.core.assessment_schemas import (
    AssessmentDefinition,
    AssessmentItem,
    AssessmentResult,
    AssessmentResponse,
    AssessmentDraft
)

# --- 1. RIASEC Instrument Definition (Standard 12-Item Adaptation) ---
RIASEC_ITEMS = [
    # Realistic (R)
    AssessmentItem(
        id="r1",
        construct="Realistic",
        text="I like to build, repair, or maintain physical hardware, mechanisms, or concrete systems.",
        scale=[
            {"value": 1, "label": "1 — Strongly Dislike"},
            {"value": 2, "label": "2 — Dislike"},
            {"value": 3, "label": "3 — Neutral"},
            {"value": 4, "label": "4 — Like"},
            {"value": 5, "label": "5 — Strongly Like"}
        ]
    ),
    AssessmentItem(
        id="r2",
        construct="Realistic",
        text="I enjoy working outdoors, with tools, robotics, or hands-on engineering equipment.",
        scale=[
            {"value": 1, "label": "1 — Strongly Dislike"},
            {"value": 2, "label": "2 — Dislike"},
            {"value": 3, "label": "3 — Neutral"},
            {"value": 4, "label": "4 — Like"},
            {"value": 5, "label": "5 — Strongly Like"}
        ]
    ),
    # Investigative (I)
    AssessmentItem(
        id="i1",
        construct="Investigative",
        text="I like to analyze complex data, formulate scientific hypotheses, and solve challenging algorithmic problems.",
        scale=[
            {"value": 1, "label": "1 — Strongly Dislike"},
            {"value": 2, "label": "2 — Dislike"},
            {"value": 3, "label": "3 — Neutral"},
            {"value": 4, "label": "4 — Like"},
            {"value": 5, "label": "5 — Strongly Like"}
        ]
    ),
    AssessmentItem(
        id="i2",
        construct="Investigative",
        text="I enjoy conducting in-depth research, reading technical literature, and discovering how systems work beneath the surface.",
        scale=[
            {"value": 1, "label": "1 — Strongly Dislike"},
            {"value": 2, "label": "2 — Dislike"},
            {"value": 3, "label": "3 — Neutral"},
            {"value": 4, "label": "4 — Like"},
            {"value": 5, "label": "5 — Strongly Like"}
        ]
    ),
    # Artistic (A)
    AssessmentItem(
        id="a1",
        construct="Artistic",
        text="I enjoy designing intuitive visual interfaces, novel user experiences, and creative digital media.",
        scale=[
            {"value": 1, "label": "1 — Strongly Dislike"},
            {"value": 2, "label": "2 — Dislike"},
            {"value": 3, "label": "3 — Neutral"},
            {"value": 4, "label": "4 — Like"},
            {"value": 5, "label": "5 — Strongly Like"}
        ]
    ),
    AssessmentItem(
        id="a2",
        construct="Artistic",
        text="I like expressing open-ended creativity, writing expressive prose, or creating artistic concepts without rigid rules.",
        scale=[
            {"value": 1, "label": "1 — Strongly Dislike"},
            {"value": 2, "label": "2 — Dislike"},
            {"value": 3, "label": "3 — Neutral"},
            {"value": 4, "label": "4 — Like"},
            {"value": 5, "label": "5 — Strongly Like"}
        ]
    ),
    # Social (S)
    AssessmentItem(
        id="s1",
        construct="Social",
        text="I enjoy mentoring peers, teaching complex topics clearly, and helping others achieve their goals.",
        scale=[
            {"value": 1, "label": "1 — Strongly Dislike"},
            {"value": 2, "label": "2 — Dislike"},
            {"value": 3, "label": "3 — Neutral"},
            {"value": 4, "label": "4 — Like"},
            {"value": 5, "label": "5 — Strongly Like"}
        ]
    ),
    AssessmentItem(
        id="s2",
        construct="Social",
        text="I prefer collaborative group environments where interpersonal communication and team empathy are essential.",
        scale=[
            {"value": 1, "label": "1 — Strongly Dislike"},
            {"value": 2, "label": "2 — Dislike"},
            {"value": 3, "label": "3 — Neutral"},
            {"value": 4, "label": "4 — Like"},
            {"value": 5, "label": "5 — Strongly Like"}
        ]
    ),
    # Enterprising (E)
    AssessmentItem(
        id="e1",
        construct="Enterprising",
        text="I like leading initiatives, pitching product visions, and persuading stakeholders to adopt new ideas.",
        scale=[
            {"value": 1, "label": "1 — Strongly Dislike"},
            {"value": 2, "label": "2 — Dislike"},
            {"value": 3, "label": "3 — Neutral"},
            {"value": 4, "label": "4 — Like"},
            {"value": 5, "label": "5 — Strongly Like"}
        ]
    ),
    AssessmentItem(
        id="e2",
        construct="Enterprising",
        text="I enjoy taking calculated entrepreneurial risks, organizing teams, and driving measurable project outcomes.",
        scale=[
            {"value": 1, "label": "1 — Strongly Dislike"},
            {"value": 2, "label": "2 — Dislike"},
            {"value": 3, "label": "3 — Neutral"},
            {"value": 4, "label": "4 — Like"},
            {"value": 5, "label": "5 — Strongly Like"}
        ]
    ),
    # Conventional (C)
    AssessmentItem(
        id="c1",
        construct="Conventional",
        text="I prefer structured protocols, organized data schemas, and meticulous attention to detail and accuracy.",
        scale=[
            {"value": 1, "label": "1 — Strongly Dislike"},
            {"value": 2, "label": "2 — Dislike"},
            {"value": 3, "label": "3 — Neutral"},
            {"value": 4, "label": "4 — Like"},
            {"value": 5, "label": "5 — Strongly Like"}
        ]
    ),
    AssessmentItem(
        id="c2",
        construct="Conventional",
        text="I like establishing orderly filing, systematic documentation, and standardized quality assurance standards.",
        scale=[
            {"value": 1, "label": "1 — Strongly Dislike"},
            {"value": 2, "label": "2 — Dislike"},
            {"value": 3, "label": "3 — Neutral"},
            {"value": 4, "label": "4 — Like"},
            {"value": 5, "label": "5 — Strongly Like"}
        ]
    )
]

RIASEC_DEFINITION = AssessmentDefinition(
    id="riasec_v1",
    name="Holland Codes (RIASEC) Career Interest Inventory",
    version="1.0.0",
    construct="Career & Vocational Interests",
    source="Adapted from Holland Vocational Hexagon & O*NET Interest Profiler principles",
    license="Public Domain Adaptation",
    limitations="This is an educational vocational interest inventory for career counseling. It is not a clinical psychological test.",
    items=RIASEC_ITEMS,
    scoring_method="Aggregated Likert score per dimension (R, I, A, S, E, C) normalized on 0-100 scale.",
    interpretation_rules="Higher scores indicate stronger intrinsic interest in that vocational archetype. Top 2-3 dimensions form the Holland Profile."
)

# --- 2. SCCT Career Development Instrument Definition ---
SCCT_ITEMS = [
    AssessmentItem(
        id="se1",
        construct="Self-Efficacy",
        text="How confident are you that you can learn difficult technical or academic concepts if you practice consistently?",
        scale=[
            {"value": 1, "label": "1 — Very Low Confidence"},
            {"value": 2, "label": "2 — Low Confidence"},
            {"value": 3, "label": "3 — Moderate Confidence"},
            {"value": 4, "label": "4 — High Confidence"},
            {"value": 5, "label": "5 — Very High Confidence"}
        ]
    ),
    AssessmentItem(
        id="se2",
        construct="Self-Efficacy",
        text="How confident are you that you can complete a complex, multi-week project independently from start to finish?",
        scale=[
            {"value": 1, "label": "1 — Very Low Confidence"},
            {"value": 2, "label": "2 — Low Confidence"},
            {"value": 3, "label": "3 — Moderate Confidence"},
            {"value": 4, "label": "4 — High Confidence"},
            {"value": 5, "label": "5 — Very High Confidence"}
        ]
    ),
    AssessmentItem(
        id="oe1",
        construct="Outcome Expectations",
        text="How strongly do you expect your ideal career to provide intellectually stimulating challenges and growth?",
        scale=[
            {"value": 1, "label": "1 — Minimal Expectation"},
            {"value": 2, "label": "2 — Low Expectation"},
            {"value": 3, "label": "3 — Moderate Expectation"},
            {"value": 4, "label": "4 — High Expectation"},
            {"value": 5, "label": "5 — Extremely High Expectation"}
        ]
    ),
    AssessmentItem(
        id="oe2",
        construct="Outcome Expectations",
        text="How strongly do you expect your ideal career to provide creative autonomy, practical utility, and financial security?",
        scale=[
            {"value": 1, "label": "1 — Minimal Expectation"},
            {"value": 2, "label": "2 — Low Expectation"},
            {"value": 3, "label": "3 — Moderate Expectation"},
            {"value": 4, "label": "4 — High Expectation"},
            {"value": 5, "label": "5 — Extremely High Expectation"}
        ]
    ),
    AssessmentItem(
        id="cs1",
        construct="Contextual Supports",
        text="What external supports are available in your learning journey? (e.g. Mentors, school labs, online courses, peer study groups)",
        response_type="open"
    ),
    AssessmentItem(
        id="cb1",
        construct="Contextual Barriers",
        text="What potential constraints or barriers could make your desired trajectory challenging? (e.g. Time limits, financial constraints, prerequisite gaps)",
        response_type="open"
    )
]

SCCT_DEFINITION = AssessmentDefinition(
    id="scct_v1",
    name="Social Cognitive Career Theory (SCCT) Development Indicators",
    version="1.0.0",
    construct="Self-Efficacy, Outcome Expectations, and Contextual Factors",
    source="Inspired by Lent, Brown, and Hackett Social Cognitive Career Theory framework",
    license="Educational Framework Adaptation",
    limitations="Measures self-reported confidence and perceived environmental supports/barriers. Non-clinical.",
    items=SCCT_ITEMS,
    scoring_method="Mean self-efficacy score, mean outcome expectation score, and structured extraction of barriers/supports.",
    interpretation_rules="Used by the ADK Counseling Agent to calibrate roadmap difficulty, scaffolding needs, and milestone pacing."
)

# --- 3. Learning & Reasoning Profile (Observable Task Framework) ---
LEARNING_ITEMS = [
    AssessmentItem(
        id="lt_recall",
        construct="Recall",
        text="Task A (Recall): In computer systems, what is the fundamental difference between a Stack and a Queue data structure?",
        response_type="open",
        expected_capability="Retrieval of core technical definitions (LIFO vs FIFO)."
    ),
    AssessmentItem(
        id="lt_explain",
        construct="Explanation",
        text="Task B (Explanation): In your own words, explain why indexing a database table can dramatically speed up search queries, and what trade-off it introduces.",
        response_type="open",
        expected_capability="Explaining mechanisms, trade-offs (faster reads vs slower writes / storage overhead)."
    ),
    AssessmentItem(
        id="lt_apply",
        construct="Application",
        text="Task C (Application): You need to process a 10GB log file on a machine with only 2GB of RAM. How would you design your code to count unique error messages without running out of memory?",
        response_type="open",
        expected_capability="Applying streaming, chunked reading, hashing, or external sorting principles."
    ),
    AssessmentItem(
        id="lt_error",
        construct="Error Detection",
        text="Task D (Error Detection): A developer wrote: `for (let i = 0; i <= array.length; i++) { console.log(array[i]); }`. What bug exists here and why does it occur?",
        response_type="open",
        expected_capability="Identifying off-by-one boundary index error (`<=` instead of `<`)."
    ),
    AssessmentItem(
        id="lt_reason",
        construct="Reasoning",
        text="Task E (Reasoning): When architecting a new software application, why might a team choose a simple monolithic design initially instead of starting immediately with microservices?",
        response_type="open",
        expected_capability="Analyzing architectural trade-offs, operational complexity, network latency, and deployment overhead."
    )
]

LEARNING_DEFINITION = AssessmentDefinition(
    id="learning_v1",
    name="Observable Learning & Reasoning Tasks",
    version="1.0.0",
    construct="Observable Problem-Solving & Technical Explanation Signals",
    source="PATHMIND Observable Competency Tasks",
    license="Internal Open Task Specification",
    limitations="This is an observable micro-task framework designed to gauge baseline explanation and application styles. It is NOT an IQ test and does NOT measure general intelligence.",
    items=LEARNING_ITEMS,
    scoring_method="Qualitative task evaluation by ADK Counseling Agent examining recall vs explanation vs application depth.",
    interpretation_rules="Identifies relative strengths in conceptual articulation vs practical scenario reasoning to tailor pedagogical approaches."
)


class AssessmentEngine:
    def __init__(self):
        self.assessments: Dict[str, AssessmentDefinition] = {
            RIASEC_DEFINITION.id: RIASEC_DEFINITION,
            SCCT_DEFINITION.id: SCCT_DEFINITION,
            LEARNING_DEFINITION.id: LEARNING_DEFINITION
        }

    def get_assessment(self, assessment_id: str) -> Optional[AssessmentDefinition]:
        return self.assessments.get(assessment_id)

    def get_all_assessments(self) -> List[AssessmentDefinition]:
        return list(self.assessments.values())

    def score_riasec(self, responses: List[AssessmentResponse]) -> Dict[str, Any]:
        """
        Calculates raw sum and normalized 0-100 scores across R, I, A, S, E, C.
        """
        raw_scores = {"R": 0, "I": 0, "A": 0, "S": 0, "E": 0, "C": 0}
        counts = {"R": 0, "I": 0, "A": 0, "S": 0, "E": 0, "C": 0}

        # Item-to-dimension map
        item_dimension_map = {
            "r1": "R", "r2": "R",
            "i1": "I", "i2": "I",
            "a1": "A", "a2": "A",
            "s1": "S", "s2": "S",
            "e1": "E", "e2": "E",
            "c1": "C", "c2": "C"
        }

        for resp in responses:
            dim = item_dimension_map.get(resp.item_id.lower())
            if dim:
                try:
                    val = float(resp.response_value)
                    raw_scores[dim] += val
                    counts[dim] += 1
                except (ValueError, TypeError):
                    continue

        normalized_scores = {}
        for dim, total in raw_scores.items():
            count = counts[dim]
            if count > 0:
                # Average on 1-5 scale mapped to 0-100
                avg = total / count
                normalized = round(((avg - 1.0) / 4.0) * 100.0, 1)
                normalized_scores[dim] = max(0.0, min(100.0, normalized))
            else:
                normalized_scores[dim] = 0.0

        # Sort dimensions by score to find dominant Holland types
        sorted_dims = sorted(normalized_scores.items(), key=lambda x: x[1], reverse=True)
        top_interests = [dim for dim, score in sorted_dims if score >= 50.0]
        if not top_interests and sorted_dims:
            top_interests = [sorted_dims[0][0]]

        return {
            "raw_totals": raw_scores,
            "normalized_vector": normalized_scores,
            "strongest_dimensions": top_interests[:3],
            "weaker_dimensions": [d for d, _ in sorted_dims[3:]]
        }

    def score_scct(self, responses: List[AssessmentResponse]) -> Dict[str, Any]:
        """
        Computes average self-efficacy and outcome expectations and collects contextual factors.
        """
        efficacy_vals = []
        outcome_vals = []
        supports = []
        barriers = []

        for resp in responses:
            item_id = resp.item_id.lower()
            val = resp.response_value
            if item_id in ["se1", "se2"]:
                try:
                    efficacy_vals.append(float(val))
                except (ValueError, TypeError):
                    pass
            elif item_id in ["oe1", "oe2"]:
                try:
                    outcome_vals.append(float(val))
                except (ValueError, TypeError):
                    pass
            elif item_id == "cs1":
                if val:
                    supports.append(str(val))
            elif item_id == "cb1":
                if val:
                    barriers.append(str(val))

        avg_efficacy = round(sum(efficacy_vals) / len(efficacy_vals), 2) if efficacy_vals else 3.0
        avg_outcome = round(sum(outcome_vals) / len(outcome_vals), 2) if outcome_vals else 3.0

        return {
            "self_efficacy_average": avg_efficacy,
            "outcome_expectation_average": avg_outcome,
            "self_efficacy_level": "HIGH" if avg_efficacy >= 4.0 else ("MEDIUM" if avg_efficacy >= 2.5 else "LOW"),
            "contextual_supports": supports,
            "contextual_barriers": barriers
        }

    def process_submission(
        self,
        person_id: str,
        assessment_id: str,
        responses: List[AssessmentResponse]
    ) -> AssessmentResult:
        definition = self.get_assessment(assessment_id)
        if not definition:
            raise ValueError(f"Assessment '{assessment_id}' not found")

        if not responses:
            raise ValueError("Cannot submit an empty assessment with no responses.")

        calculated_scores: Dict[str, Any] = {}
        dimension_scores: Optional[Dict[str, float]] = None

        if assessment_id == "riasec_v1":
            scoring_res = self.score_riasec(responses)
            calculated_scores = scoring_res
            dimension_scores = scoring_res.get("normalized_vector")
        elif assessment_id == "scct_v1":
            calculated_scores = self.score_scct(responses)
        elif assessment_id == "learning_v1":
            calculated_scores = {
                "tasks_submitted": len(responses),
                "task_types": ["Recall", "Explanation", "Application", "Error Detection", "Reasoning"],
                "status": "ready_for_agent_evaluation"
            }
        else:
            calculated_scores = {"status": "unrecognized_scoring"}

        return AssessmentResult(
            person_id=person_id,
            assessment_id=assessment_id,
            version=definition.version,
            timestamp=datetime.now(timezone.utc).isoformat(),
            raw_responses=responses,
            calculated_scores=calculated_scores,
            dimension_scores=dimension_scores
        )
