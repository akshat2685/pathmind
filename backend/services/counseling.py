import os
import json
import re
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
from backend.core.config import settings
from backend.core.assessment_schemas import (
    CounselingProfile,
    CounselingFact,
    Contradiction,
    CandidateDirection,
    AssessmentResult,
    CounselingMessage
)
from backend.core.memory_schemas import MemoryItem
from backend.services.knowledge import KnowledgeService
from backend.services.intelligence_service import readiness_steering_text

# --- Decision-journal: pivot detection --------------------------------------
# When the learner talks about switching direction, the counselor should
# nudge them to record the decision with its reason — pivots stay
# explainable months later via POST /api/memory/decisions.
_PIVOT_PATTERNS = [
    re.compile(r"\bi\s+(?:want to|am going to|will|should)\s+(?:switch|change|quit|leave|drop|pivot)", re.I),
    re.compile(r"\b(?:thinking of|considering)\s+(?:switching|changing|quitting|leaving|dropping)", re.I),
    re.compile(r"\bnot\s+(?:sure|certain)\b.{0,40}\b(?:anymore|still)\b", re.I),
]


def detect_pivot_talk(text: str) -> bool:
    """True when the message sounds like a direction change worth journaling."""
    return any(p.search(text or "") for p in _PIVOT_PATTERNS)


def pivot_nudge_text() -> str:
    return (
        "POSSIBLE PIVOT: the learner sounds like they may be changing "
        "direction. Don't just roll with it — ask what changed and what "
        "they're choosing instead, and suggest recording the decision with "
        "its reason (POST /api/memory/decisions) so the choice stays "
        "explainable later."
    )


# --- Verified-not-vibes: skill-claim detection --------------------------------
# When the learner claims a skill ("I know Python", "I'm experienced in X"),
# the counselor must not accept it as established fact. These patterns catch
# the common phrasings; the claim text is passed through for the nudge.
_SKILL_CLAIM_PATTERNS = [
    re.compile(r"\bi\s+(?:know|understand|am good at|am skilled in|am experienced in)\s+([a-zA-Z][a-zA-Z0-9+#.\s]{1,40})", re.I),
    re.compile(r"\bi'?m\s+experienced\s+in\s+([a-zA-Z][a-zA-Z0-9+#.\s]{1,40})", re.I),
    re.compile(r"\bi\s+(?:have|got)\s+(?:experience|expertise)\s+(?:in|with)\s+([a-zA-Z][a-zA-Z0-9+#.\s]{1,40})", re.I),
    re.compile(r"\bi\s+(?:built|made|created|completed|finished)\s+(?:a|an|my)?\s*([a-zA-Z][a-zA-Z0-9+#.\s]{1,40}?)(?:\s+project|\s+app|\s+website|$)", re.I),
]


def detect_skill_claims(text: str) -> list:
    """Return claimed skill phrases from free text; [] when none found."""
    claims = []
    for pat in _SKILL_CLAIM_PATTERNS:
        for m in pat.finditer(text or ""):
            claim = m.group(1).strip().rstrip(".,!?")
            if 2 <= len(claim) <= 45 and claim.lower() not in claims:
                claims.append(claim.lower())
    return claims


def verification_nudge_text(claims: list) -> str | None:
    """Prompt block: treat claims as UNVERIFIED, propose evidence, never flatter."""
    if not claims:
        return None
    listed = ", ".join(f'"{c}"' for c in claims)
    return (
        "UNVERIFIED SKILL CLAIM(S): the learner claims knowledge of "
        f"{listed}. This is SELF-REPORTED, not verified. Do NOT treat it as "
        "established fact and do NOT flatter them about it. If the claim "
        "matters to your advice, propose verifying it: ask them to share a "
        "code sample, repo link, or work sample via evidence submission "
        "(POST /api/journey/evidence), which is deterministically verified. "
        "Until then, qualify any skill-dependent advice."
    )


# --- Transparent, Configurable Evidence Weighting Matrix ---
EVIDENCE_WEIGHTS = {
    "VERIFIED_PROJECT": 1.0,      # Direct demonstrated repositories / code artifacts
    "ACADEMIC_EVIDENCE": 0.8,     # Coursework, grades, academic background
    "ASSESSED_INSTRUMENT": 0.7,   # Standardized RIASEC & SCCT measurements
    "OBSERVED_ACTIVITY": 0.6,     # Extracurriculars (Robotics, Hackathons, Clubs)
    "STATED_PREFERENCE": 0.5      # Self-declared aspirations without artifact proof
}

class CounselingAgent:
    def __init__(self):
        self.gemini_available = bool(settings.GEMINI_API_KEY)
        self.knowledge_service = KnowledgeService()
        self.model = None

        if self.gemini_available:
            try:
                import google.generativeai as genai
                genai.configure(api_key=settings.GEMINI_API_KEY)
                self.model = genai.GenerativeModel('gemini-3.5-flash')
            except Exception as e:
                print(f"Warning: Failed to initialize Gemini client: {e}")
                self.model = None

    def detect_contradictions(
        self,
        stated_goals: List[str],
        stated_constraints: List[str],
        evidence_items: List[Dict[str, Any]],
        riasec_scores: Dict[str, float]
    ) -> List[Contradiction]:
        """
        Detects meaningful discrepancies between stated preferences, observable project evidence,
        and psychometric scores without silently discarding either.
        """
        contradictions: List[Contradiction] = []
        goals_text = " ".join(stated_goals).lower()
        
        # 1. Project Evidence vs Stated Disinterest
        has_coding_evidence = any(
            any(k in str(item).lower() for k in ["github", "code", "programming", "software", "hackathon", "robotics", "repo"])
            for item in evidence_items
        )
        
        if ("hate coding" in goals_text or "dislike programming" in goals_text or "no coding" in goals_text) and has_coding_evidence:
            contradictions.append(Contradiction(
                reported_preference="Disinterest or aversion to programming/software.",
                observed_evidence="Multiple programming/robotics projects, repositories, or hackathon activities found in profile evidence.",
                suggested_clarification="There's a difference in the information PATHMIND has: Is your hesitation with programming itself, or with specific rigid classroom contexts vs practical creative building? Clarification will help refine recommendations.",
                discrepancy_description="User declared aversion to coding while profile contains verified software artifacts.",
                resolution_strategy="user_clarification",
                user_action_needed="Clarify whether you prefer avoiding programming entirely or if past frustration was specific to prior coursework."
            ))

        # 2. Abstract High-Theory Goal vs Purely Artistic/Social Psychometric Profile
        highest_riasec = max(riasec_scores.items(), key=lambda x: x[1])[0] if riasec_scores else "I"
        i_score = riasec_scores.get("I", 0.0)
        a_score = riasec_scores.get("A", 0.0)
        s_score = riasec_scores.get("S", 0.0)

        if any(term in goals_text for term in ["theoretical math", "compiler research", "quantum algorithms"]) and i_score < 40 and (a_score > 70 or s_score > 70):
            contradictions.append(Contradiction(
                reported_preference="Targeting abstract theoretical systems research.",
                observed_evidence=f"Psychometric interest profile is significantly stronger in Artistic ({a_score}%) and Social ({s_score}%) than Investigative ({i_score}%).",
                suggested_clarification="There's a difference in the information PATHMIND has: Would human-centered engineering, AI UX design, or interactive educational technology be more energizing than purely abstract theory? Clarification helps align your trajectory.",
                discrepancy_description="Targeting high-theory research while interest assessment scores reflect significantly higher Social/Artistic affinity.",
                resolution_strategy="both_presented",
                user_action_needed="Indicate whether to prioritize theoretical depth or human-centered application."
            ))

        # 3. High Seniority Claim vs Zero Verified Evidence
        if any(term in goals_text for term in ["expert", "lead architect", "senior engineer", "director"]) and len(evidence_items) == 0:
            contradictions.append(Contradiction(
                reported_preference="Self-declared senior/expert mastery level.",
                observed_evidence="Zero verified portfolio artifacts, evaluations, or repositories submitted.",
                suggested_clarification="There's a difference in the information PATHMIND has: To recommend advanced professional tiers with high confidence, PATHMIND requires verified work samples or assessment demonstrations.",
                discrepancy_description="Self-declared seniority lacks verified supporting evidence.",
                resolution_strategy="higher_verifiability_preferred",
                user_action_needed="Submit verified project repositories, certifications, or complete diagnostic evaluations."
            ))

        return contradictions

    def compute_categorical_confidence(
        self,
        evidence_count: int,
        assessment_count: int,
        contradiction_count: int
    ) -> str:
        """
        Determines strictly categorical confidence: HIGH, MEDIUM, LOW, INSUFFICIENT_EVIDENCE.
        No arbitrary fake decimal percentages.
        """
        if assessment_count == 0 and evidence_count == 0:
            return "INSUFFICIENT_EVIDENCE"
        if evidence_count >= 2 and assessment_count >= 2 and contradiction_count == 0:
            return "HIGH"
        if assessment_count >= 1 and evidence_count >= 1:
            return "MEDIUM"
        if assessment_count >= 1:
            return "MEDIUM"
        return "LOW"

    def synthesize_deterministic_profile(
        self,
        person_id: str,
        assessment_results: List[AssessmentResult],
        goals: List[str],
        constraints: List[str],
        evidence_items: List[Dict[str, Any]]
    ) -> CounselingProfile:
        """
        Deterministic, transparent synthesis engine adhering strictly to psychometric constructs,
        evidence classification, contradiction detection, and KnowledgeService taxonomy.
        """
        # 1. Parse RIASEC scores (STRICT: NO SYNTHETIC FALLBACK)
        riasec_res = next((r for r in assessment_results if "riasec" in r.assessment_id.lower()), None)
        interest_vector = {}
        strongest_interests = []
        weaker_interests = []
        is_riasec_assessed = False

        if riasec_res and riasec_res.dimension_scores:
            interest_vector = riasec_res.dimension_scores
            is_riasec_assessed = True
        elif riasec_res and isinstance(riasec_res.calculated_scores, dict) and "normalized_vector" in riasec_res.calculated_scores:
            interest_vector = riasec_res.calculated_scores["normalized_vector"]
            is_riasec_assessed = True

        dimension_names = {
            "R": "Realistic (Hands-on Systems & Practical Building)",
            "I": "Investigative (Analytical Research & Problem Solving)",
            "A": "Artistic (Creative Expression, Visual & UX Design)",
            "S": "Social (Teaching, Counseling & Direct Helping)",
            "E": "Enterprising (Leadership, Entrepreneurship & Strategy)",
            "C": "Conventional (Organization, Data Governance & Structured Process)"
        }

        assessed_strengths = []
        if is_riasec_assessed and interest_vector:
            sorted_interests = sorted(interest_vector.items(), key=lambda x: x[1], reverse=True)
            strongest_interests = [dimension_names.get(dim, dim) for dim, _ in sorted_interests[:2]]
            weaker_interests = [dimension_names.get(dim, dim) for dim, _ in sorted_interests[4:]]
            
            assessed_strengths.append(
                CounselingFact(
                    category="ASSESSED",
                    claim=f"Responses indicate stronger interest in {strongest_interests[0]} (interests reflect preferences, not ability or guaranteed outcome)",
                    evidence=[f"Holland RIASEC measured preference: {sorted_interests[0][1]}%"],
                    confidence="MEDIUM",
                    weight=EVIDENCE_WEIGHTS["ASSESSED_INSTRUMENT"],
                    source="Holland RIASEC Assessment"
                )
            )
            if len(sorted_interests) > 1 and sorted_interests[1][1] >= 50.0:
                assessed_strengths.append(
                    CounselingFact(
                        category="ASSESSED",
                        claim=f"Responses indicate secondary interest in {strongest_interests[1]}",
                        evidence=[f"Holland RIASEC measured preference: {sorted_interests[1][1]}%"],
                        confidence="MEDIUM",
                        weight=EVIDENCE_WEIGHTS["ASSESSED_INSTRUMENT"],
                        source="Holland RIASEC Assessment"
                    )
                )

        # 2. Parse SCCT self-efficacy
        scct_res = next((r for r in assessment_results if "scct" in r.assessment_id.lower()), None)
        efficacy_level = None
        outcome_exp = None
        context_supports_list = []
        context_barriers_list = []

        if scct_res and isinstance(scct_res.calculated_scores, dict):
            efficacy_level = scct_res.calculated_scores.get("self_efficacy_level", "MEDIUM")
            outcome_exp = scct_res.calculated_scores.get("outcome_expectation", "Meaningful professional mastery and practical autonomy")
            context_supports_list = scct_res.calculated_scores.get("contextual_supports", [])
            context_barriers_list = scct_res.calculated_scores.get("contextual_barriers", [])

        # 3. Categorize Facts
        # OBSERVED Facts (from Evidence items)
        demonstrated_caps = []
        demonstrated_exp = []
        academic_strengths = []
        for ev in evidence_items:
            name = ev.get("name") or ev.get("title") or "Project Artifact"
            desc = ev.get("description", "")
            ev_type = ev.get("type", "project")
            demonstrated_caps.append(
                CounselingFact(
                    category="OBSERVED",
                    claim=f"Demonstrated practical capability: {name}",
                    evidence=[f"Artifact ({ev_type}): {desc}" if desc else f"Submitted artifact: {name}"],
                    confidence="HIGH",
                    weight=EVIDENCE_WEIGHTS["VERIFIED_PROJECT"],
                    source="Candidate Submission"
                )
            )
            demonstrated_exp.append(
                CounselingFact(
                    category="OBSERVED",
                    claim=f"Practical engagement in {name}",
                    evidence=[f"Context: {desc}" if desc else f"Artifact: {name}"],
                    confidence="HIGH",
                    weight=EVIDENCE_WEIGHTS["VERIFIED_PROJECT"],
                    source="Candidate Portfolio"
                )
            )
            if "course" in str(name).lower() or "academic" in str(desc).lower() or "transcript" in str(desc).lower():
                academic_strengths.append(
                    CounselingFact(
                        category="OBSERVED",
                        claim=f"Demonstrated academic coursework in {name}",
                        evidence=[f"Coursework record: {desc}"],
                        confidence="HIGH",
                        weight=EVIDENCE_WEIGHTS["ACADEMIC_EVIDENCE"],
                        source="Candidate Academic Record"
                    )
                )

        # INFERRED Signals (Derived strictly from genuine assessed signals or verified evidence)
        inferred_signals = []
        if is_riasec_assessed:
            if interest_vector.get("I", 0) >= 70 and interest_vector.get("R", 0) >= 60:
                inferred_signals.append(
                    CounselingFact(
                        category="INFERRED",
                        claim="High alignment with applied technical disciplines combining theory with concrete building.",
                        evidence=["RIASEC Investigative >= 70%", "RIASEC Realistic >= 60%"],
                        confidence="HIGH",
                        weight=0.9,
                        source="Psychometric Synthesis"
                    )
                )
            if interest_vector.get("A", 0) >= 70:
                inferred_signals.append(
                    CounselingFact(
                        category="INFERRED",
                        claim="Strong affinity for creative, visual, design, and user experience expression.",
                        evidence=[f"RIASEC Artistic: {interest_vector.get('A', 0)}%"],
                        confidence="HIGH",
                        weight=0.9,
                        source="Psychometric Synthesis"
                    )
                )
            if interest_vector.get("S", 0) >= 70:
                inferred_signals.append(
                    CounselingFact(
                        category="INFERRED",
                        claim="Strong alignment with people-oriented vocations, advisory roles, teaching, and mentorship.",
                        evidence=[f"RIASEC Social: {interest_vector.get('S', 0)}%"],
                        confidence="HIGH",
                        weight=0.9,
                        source="Psychometric Synthesis"
                    )
                )
            if interest_vector.get("E", 0) >= 70:
                inferred_signals.append(
                    CounselingFact(
                        category="INFERRED",
                        claim="High aptitude for venture leadership, product management, strategic operations, and initiative driving.",
                        evidence=[f"RIASEC Enterprising: {interest_vector.get('E', 0)}%"],
                        confidence="HIGH",
                        weight=0.9,
                        source="Psychometric Synthesis"
                    )
                )
            if interest_vector.get("C", 0) >= 70:
                inferred_signals.append(
                    CounselingFact(
                        category="INFERRED",
                        claim="Strong orientation toward systems organization, regulatory governance, data integrity, and structured workflows.",
                        evidence=[f"RIASEC Conventional: {interest_vector.get('C', 0)}%"],
                        confidence="HIGH",
                        weight=0.9,
                        source="Psychometric Synthesis"
                    )
                )

        # Learning Signals from observable tasks
        learning_res = next((r for r in assessment_results if "learning" in r.assessment_id.lower()), None)
        learning_signals = []
        if learning_res:
            learning_signals.append(
                CounselingFact(
                    category="OBSERVED",
                    claim="Demonstrated strong concrete problem decomposition and scenario application over abstract rote definitions.",
                    evidence=["Completed Observable Tasks A-E (Recall, Explain, Apply, Error Detection, Reason)"],
                    confidence="MEDIUM",
                    weight=EVIDENCE_WEIGHTS["ASSESSED_INSTRUMENT"],
                    source="Observable Task Framework"
                )
            )

        # Contradictions & Conflict Notices
        contradictions = self.detect_contradictions(goals, constraints, evidence_items, interest_vector)
        conflict_notices = [
            {
                "what_conflicts": [c.reported_preference, c.observed_evidence],
                "discrepancy_description": c.discrepancy_description or c.reported_preference,
                "resolution_strategy": c.resolution_strategy or "user_clarification",
                "user_action_needed": c.user_action_needed or c.suggested_clarification
            }
            for c in contradictions
        ]

        # Confidence
        confidence_cat = self.compute_categorical_confidence(
            evidence_count=len(evidence_items),
            assessment_count=len(assessment_results),
            contradiction_count=len(contradictions)
        )

        # Domain-aware Evidence Gaps / Portfolio Requests
        evidence_gaps = []
        goals_text = " ".join(goals).lower() if goals else ""
        if not evidence_items:
            evidence_gaps = [
                "Please consider sharing portfolio artifacts, project documentation, or case studies relevant to your target direction.",
                "Sharing official transcripts, certifications, or syllabus outlines will allow us to accurately calibrate prerequisite stage bypasses."
            ]

        # Candidate Directions (Goal-Conditioned, Assessment-Grounded, Domain-Agnostic)
        candidate_directions = []
        candidate_details = []

        if goals:
            # Generic stated goal formulation
            primary_goal = goals[0]
            candidate_directions = [f"{primary_goal.strip()} Professional Pathway"]
            candidate_details = [
                CandidateDirection(
                    title=f"{primary_goal.strip()} Professional Pathway",
                    rationale=f"Directly derived from stated candidate goal: '{primary_goal}'.",
                    alignment="Explicit user-declared objective",
                    related_occupations=[],
                    confidence="HIGH"
                )
            ]
        elif is_riasec_assessed:
            # Stated goal absent, but genuine psychometric assessment exists: map from assessed interests
            top_dim = sorted_interests[0][0]
            if top_dim == "A":
                candidate_directions = ["Creative & Visual Design", "Interactive Media & Digital Content"]
                candidate_details = [CandidateDirection(title="Creative & Visual Design", rationale="Strongest measured Artistic interest.", alignment="Artistic Profile", related_occupations=["Graphic Designer (ESCO: 2166)"])]
            elif top_dim == "S":
                candidate_directions = ["Instructional Design & Educational Leadership", "Community & Counseling Advisory"]
                candidate_details = [CandidateDirection(title="Instructional Design & Educational Leadership", rationale="Strongest measured Social interest.", alignment="Social Profile", related_occupations=["Educator (ESCO: 2351)"])]
            elif top_dim == "E":
                candidate_directions = ["Venture Operations & Product Leadership", "Strategic Business Development"]
                candidate_details = [CandidateDirection(title="Venture Operations & Product Leadership", rationale="Strongest measured Enterprising interest.", alignment="Enterprising Profile", related_occupations=["Business Consultant (ESCO: 2421)"])]
            elif top_dim == "C":
                candidate_directions = ["Data Governance & Compliance Management", "Financial Analysis & Systems Operations"]
                candidate_details = [CandidateDirection(title="Data Governance & Compliance Management", rationale="Strongest measured Conventional interest.", alignment="Conventional Profile", related_occupations=["Compliance Officer (ESCO: 2422)"])]
            elif top_dim == "R":
                candidate_directions = ["Applied Systems & Hardware Engineering", "Field Operations & Prototyping"]
                candidate_details = [CandidateDirection(title="Applied Systems & Hardware Engineering", rationale="Strongest measured Realistic interest.", alignment="Realistic Profile", related_occupations=["Mechanical Engineer (ESCO: 2144)"])]
            else:
                candidate_directions = ["Scientific Research & Analytical Investigation", "Computational Problem Solving"]
                candidate_details = [CandidateDirection(title="Scientific Research & Analytical Investigation", rationale="Strongest measured Investigative interest.", alignment="Investigative Profile", related_occupations=["Researcher (ESCO: 2131)"])]
        else:
            # Stated goal absent AND psychometrics unassessed: DO NOT INVENT CAREERS
            candidate_directions = []
            candidate_details = []

        # Goal-conditioned or exploratory Next Reflective Questions
        if goals:
            primary_goal = goals[0]
            next_questions = [
                f"What specific milestone or project in {primary_goal} are you most energized to tackle first?",
                "When mastering new competencies, what learning format (practical hands-on casework, structured literature, or 1-on-1 mentorship) works best for you?",
                "What schedule constraints (such as weekly available hours or strict target completion dates) should we prioritize in your plan?"
            ]
        else:
            next_questions = [
                "What professional domain, industry, or problem space do you feel most drawn toward exploring?",
                "What types of activities (creative design, direct helping, strategic planning, analytical investigation, or practical building) bring you the most flow?",
                "Do you currently have any prior coursework, certifications, or portfolio projects you'd like us to account for?"
            ]

        # Transparent Unknowns
        unknowns = []
        if not goals:
            unknowns.append("Primary career or learning objective has not yet been specified.")
        if not is_riasec_assessed:
            unknowns.append("Holland RIASEC occupational interest profile is unassessed.")
        if not evidence_items:
            unknowns.append("No verified portfolio artifacts or demonstrated prior projects submitted.")
        if not constraints:
            unknowns.append("Weekly time commitment and geographic mobility constraints are unconfirmed.")

        self_eff_facts = []
        if efficacy_level:
            self_eff_facts.append(
                CounselingFact(
                    category="ASSESSED",
                    claim=f"Self-Efficacy Level: {efficacy_level}",
                    evidence=["SCCT Confidence item responses"],
                    confidence="HIGH"
                )
            )

        outcome_facts = []
        if outcome_exp:
            outcome_facts.append(
                CounselingFact(
                    category="ASSESSED",
                    claim=f"Primary outcome expectation: {outcome_exp}",
                    evidence=["SCCT Outcome Expectation indicators"],
                    confidence="HIGH"
                )
            )

        return CounselingProfile(
            person_id=person_id,
            timestamp=datetime.now(timezone.utc).isoformat(),
            is_preliminary=True,
            interest_vector=interest_vector,
            strongest_interests=strongest_interests,
            weaker_interests=weaker_interests,
            academic_strengths=academic_strengths,
            academic_weaknesses=[],
            demonstrated_capabilities=demonstrated_caps,
            demonstrated_experience=demonstrated_exp,
            self_efficacy_signals=self_eff_facts,
            outcome_expectations=outcome_facts,
            contextual_barriers=[
                CounselingFact(
                    category="OBSERVED",
                    claim=b,
                    evidence=["Self-reported constraint"],
                    confidence="HIGH"
                ) for b in context_barriers_list
            ],
            contextual_supports=[
                CounselingFact(
                    category="OBSERVED",
                    claim=s,
                    evidence=["Self-reported support environment"],
                    confidence="HIGH"
                ) for s in context_supports_list
            ],
            learning_signals=learning_signals,
            strengths=assessed_strengths + demonstrated_caps,
            interest_patterns=assessed_strengths,
            capability_signals=demonstrated_caps + inferred_signals,
            constraints=[
                CounselingFact(category="OBSERVED", claim=c, evidence=["Declared in onboarding"], confidence="HIGH")
                for c in constraints
            ],
            contradictions=contradictions,
            conflict_notices=conflict_notices,
            unknowns=unknowns,
            evidence_gaps=evidence_gaps,
            candidate_directions=candidate_directions,
            candidate_direction_details=candidate_details,
            next_questions=next_questions,
            overall_confidence=confidence_cat
        )

    def synthesize_profile(
        self,
        person_id: str,
        assessment_results: List[AssessmentResult],
        goals: List[str] = None,
        constraints: List[str] = None,
        evidence_items: List[Dict[str, Any]] = None
    ) -> CounselingProfile:
        """
        Synthesizes a structured CounselingProfile. If Gemini is available, enhances the synthesis
        via LLM while strictly adhering to the schema and psychometric bounds.
        """
        goals = goals or []
        constraints = constraints or []
        evidence_items = evidence_items or []

        # Always start with rigorous baseline synthesis
        base_profile = self.synthesize_deterministic_profile(
            person_id=person_id,
            assessment_results=assessment_results,
            goals=goals,
            constraints=constraints,
            evidence_items=evidence_items
        )

        if not self.model:
            return base_profile

        try:
            prompt = f"""You are the PATHMIND Career Counselor and Psychometric Mentor.
Synthesize an evidence-informed, polite, supportive, and non-clinical counseling profile.

STRICT PRINCIPLES:
1. Distinguish OBSERVED, ASSESSED, INFERRED, UNKNOWN, and RECOMMENDATION.
2. Ground all claims in the provided assessment results and evidence artifacts.
3. If portfolio/project links are missing, include specific polite requests in `evidence_gaps`.
4. Check for contradictions between stated goals and measured psychometrics.
5. Overall confidence must be one of: HIGH, MEDIUM, LOW, INSUFFICIENT_EVIDENCE.
6. The profile must be marked is_preliminary: true.

Input Data:
- Person ID: {person_id}
- Stated Goals: {json.dumps(goals)}
- Stated Constraints: {json.dumps(constraints)}
- Evidence Artifacts: {json.dumps(evidence_items)}
- Assessment Results: {json.dumps([r.model_dump(mode='json') for r in assessment_results])}
- Base Synthesized Profile: {base_profile.model_dump_json(indent=2)}
"""
            response = self.model.generate_content(
                prompt,
                generation_config={
                    "response_mime_type": "application/json",
                    "temperature": 0.2
                }
            )
            profile_dict = json.loads(response.text)
            profile_dict["person_id"] = person_id
            profile_dict["timestamp"] = datetime.now(timezone.utc).isoformat()
            profile_dict["is_preliminary"] = True
            return CounselingProfile(**profile_dict)
        except Exception as e:
            print(f"Gemini synthesis fallback to deterministic engine: {e}")
            return base_profile

    @staticmethod
    def _format_memory_context(memories: List[MemoryItem]) -> str:
        """
        Formats promoted memories for prompt injection, labeled by promotion
        status so the LLM weights DURABLE patterns strongly and treats
        CANDIDATE patterns as tentative.
        """
        if not memories:
            return "- Long-term Memory: none recorded yet for this learner."
        lines = ["- Relevant Long-term Memories (from the learner's personal vault):"]
        for m in memories[:5]:
            tag = "DURABLE — established pattern, weight strongly" if m.promotion_status == "DURABLE" else "CANDIDATE — tentative, do not assert as fact"
            snippet = (m.summary or m.content or "")[:220]
            lines.append(f"  [{tag}] {m.topic}: {m.title} — {snippet} (seen {m.observation_count}x, source: {m.source_reference})")
        return "\n".join(lines)

    def counsel_chat(
        self,
        person_id: str,
        user_message: str,
        profile: CounselingProfile,
        history: List[CounselingMessage] = None,
        memories: Optional[List[MemoryItem]] = None,
        longitudinal_brief: Optional[str] = None,
        readiness_stage: Optional[str] = None,
        evidence_block: Optional[str] = None,
        trajectory_brief: Optional[str] = None,
        verification_nudge: Optional[str] = None,
        accountability_prompt: Optional[str] = None,
        failure_prompt: Optional[str] = None,
        pivot_nudge: Optional[str] = None
    ) -> CounselingMessage:
        """
        Interactive counseling dialogue that explains findings, answers questions,
        and provides guidance without mutating source assessment records.

        memories: promoted (CANDIDATE/DURABLE) long-term memories injected into
        the prompt. DURABLE memories are repeatedly-observed patterns — weight
        them strongly. CANDIDATE memories are emerging patterns — treat as
        tentative and never present them as established fact.

        longitudinal_brief: college-MVP-style context brief (recent session
        turns + durable learner facts + learning signals) built by
        LongitudinalMemoryService.build_context_brief(). Injected verbatim so
        every turn is grounded in this learner's own short-term and long-term
        memory.

        readiness_stage: intelligence-pack readiness screening (heuristic, NOT
        a diagnosis). Steers tone only — never surfaced as a verdict.

        evidence_block: intelligence-pack grounded evidence (verified resources
        + professions entries with hard grounding rules). Injected into the
        prompt; the deterministic fallback surfaces the entries directly.

        trajectory_brief: one-or-two-line journey trajectory (when the journey
        started, current aspiration, durable patterns count). Lets the
        counselor demonstrate it remembers the whole journey, not just the
        current turn.

        verification_nudge: UNVERIFIED skill-claim guidance from
        verification_nudge_text(). Steers the counselor to propose evidence
        instead of accepting claims at face value.

        accountability_prompt: proactive accountability block — overdue
        commitments the counselor should raise naturally instead of waiting
        to be asked. The coach initiates.

        failure_prompt: failure-memory block — lapsed commitments framed as
        "what didn't work", so planning references the learner's real
        history instead of generic advice.

        pivot_nudge: POSSIBLE PIVOT guidance from pivot_nudge_text().
        Prompts the counselor to journal the decision with its reason.
        """
        history = history or []
        memory_block = self._format_memory_context(memories or [])
        brief_block = f"\n{longitudinal_brief}\n" if longitudinal_brief else ""

        # Intelligence pack: stage steers tone (never a user-facing verdict);
        # evidence block carries hard grounding rules for the LLM.
        readiness_prompt = ""
        if readiness_stage:
            steering = readiness_steering_text(readiness_stage)
            if steering:
                readiness_prompt = f"\n{steering}\n"
        evidence_prompt = f"\n{evidence_block}\n" if evidence_block else ""
        trajectory_prompt = f"\n{trajectory_brief}\n" if trajectory_brief else ""
        verification_prompt = (
            f"\n{verification_nudge}\n" if verification_nudge else ""
        )
        accountability_block = (
            f"\n{accountability_prompt}\n" if accountability_prompt else ""
        )
        failure_block = f"\n{failure_prompt}\n" if failure_prompt else ""
        pivot_block = f"\n{pivot_nudge}\n" if pivot_nudge else ""

        # Constraint-honest planning: hard limits rendered verbatim so the
        # model negotiates with them instead of silently ignoring them.
        constraints_block = ""
        try:
            cons = [f.claim for f in (profile.constraints or []) if getattr(f, "claim", None)]
            if cons:
                constraints_block = (
                    "\nRecorded constraints (HARD LIMITS — never propose a "
                    "plan that violates these; if the math doesn't fit, say "
                    "so and present the tradeoff):\n- " + "\n- ".join(cons[:8]) + "\n"
                )
        except Exception:
            pass

        # Polite mentor dialogue generation
        if self.model:
            try:
                top_interests_str = ", ".join(profile.strongest_interests) if profile.strongest_interests else "UNASSESSED"
                candidate_dirs_str = ", ".join(profile.candidate_directions) if profile.candidate_directions else "NONE_SPECIFIED"
                system_context = f"""You are the PATHMIND Empathetic Career Counselor.
You are conversing with {person_id}.
Active Profile Summary:
- Top Interests: {top_interests_str}
- Confidence: {profile.overall_confidence}
- Candidate Directions: {candidate_dirs_str}
- Contradictions: {json.dumps([c.model_dump() for c in profile.contradictions])}
- Evidence Gaps: {json.dumps(profile.evidence_gaps)}
{memory_block}
{brief_block}{readiness_prompt}{evidence_prompt}{trajectory_prompt}{verification_prompt}{accountability_block}{failure_block}{pivot_block}{constraints_block}GUIDELINES:
- Warm, polite, supportive, mentor-like tone.
- Explain evidence backing recommendations.
- Clarify contradictions gently.
- GOAL-FIRST: take the learner's stated aspiration literally and at face value. Never steer them toward software/tech/AI careers unless they asked for one. A tea shop, a trade, teaching, nursing, design, or creator work deserves the same seriousness as an ML engineer path. Do not funnel every conversation toward coding.
- VERIFIED, NOT VIBES: treat user-claimed skills as UNVERIFIED until evidence exists. Never flatter ("you're great at X") without evidence; when a claim matters to the advice, propose verifying it (share code, a repo, or a work sample) rather than accepting it.
- CALIBRATED UNCERTAINTY: if the evidence block reports NO_VERIFIED_RESULTS, say plainly that you don't have verified data on the topic. Never fill the gap with general knowledge presented as verified fact.
- CONSTRAINT-HONEST: the learner's recorded constraints are hard limits, not suggestions. If a plan can't fit their time, money, or location constraints, say so and present the tradeoff explicitly — never silently propose something that violates them.
- Memories marked DURABLE are established patterns in this learner's history: use them to personalize (e.g. reference known strengths, preferences, recurring struggles).
- Memories marked CANDIDATE are tentative emerging patterns: you may probe them gently ("I've noticed... does that sound right?") but never assert them as fact.
- Encourage sharing portfolio links or domain-specific artifacts to substantiate milestones.
- Keep responses concise, clear, and actionable.
"""
                chat_history_str = "\n".join([f"{m.role}: {m.content}" for m in history[-6:]])
                prompt = f"{system_context}\n\nRecent History:\n{chat_history_str}\n\nUser: {user_message}\nCounselor:"
                
                resp = self.model.generate_content(prompt)
                reply_text = resp.text.strip()
                return CounselingMessage(
                    role="counselor",
                    content=reply_text,
                    timestamp=datetime.now(timezone.utc).isoformat()
                )
            except Exception as e:
                print(f"Chat model error: {e}")

        # Deterministic fallback response
        parts = ["Thank you for sharing that."]
        # Intelligence pack: stage steers tone even without the LLM — motivational
        # when readiness is low, concrete when the learner is ready to move.
        if readiness_stage in ("precontemplation", "contemplation"):
            parts.append(
                "There's no pressure to commit to a plan right now — "
                "let's first explore what matters most to you."
            )
        elif readiness_stage in ("preparation", "action", "maintenance"):
            parts.append(
                "Since you're ready to move, let's get concrete about next steps."
            )
        durable = [m for m in (memories or []) if m.promotion_status == "DURABLE"]
        if durable:
            top = durable[0]
            parts.append(f"From your history, I remember a consistent pattern: {top.title} ({top.topic}). I'll keep that in mind.")
        if profile.strongest_interests:
            parts.append(f"Based on your assessment, your strongest measured interests are in {', '.join(profile.strongest_interests)}.")
        else:
            parts.append("Your psychometric interest profile is currently unassessed.")

        if profile.candidate_directions:
            parts.append(f"We've identified promising candidate pathways in {', '.join(profile.candidate_directions[:2])}.")
        else:
            parts.append("Once you declare a target outcome or complete a diagnostic assessment, we can map out tailored candidate pathways.")

        parts.append("Feel free to share your primary goal or any specific projects, background, and constraints to help calibrate your plan.")

        # Intelligence pack: surface the retrieved verified entries directly
        # (dropping the LLM-facing header and HARD RULES instructions).
        # Calibrated uncertainty: a NO_VERIFIED_RESULTS marker is honesty,
        # not evidence — say so instead of surfacing it as entries.
        if evidence_block:
            if evidence_block.strip().startswith("NO_VERIFIED_RESULTS"):
                parts.append(
                    "I don't have verified data on that specific topic, so "
                    "I won't guess — tell me more about what you're trying "
                    "to do and I'll work with what I can verify."
                )
            else:
                entry_text = evidence_block.split("HARD RULES:")[0].split("\n", 1)[-1].strip()
                if entry_text:
                    parts.append("Verified entries relevant to your question:\n" + entry_text)

        # Longitudinal memory as product: the fallback also demonstrates the
        # journey is remembered, not just the current turn.
        if trajectory_brief:
            parts.append(trajectory_brief)

        # Verified, not vibes: never accept a skill claim at face value, even
        # without the LLM — propose evidence instead of flattery.
        if verification_nudge:
            parts.append(
                "I don't take skill claims at face value — if you'd like that "
                "to count toward your plan, share a code sample, repo link, "
                "or work sample as evidence and I'll verify it properly."
            )

        # The coach initiates: surface overdue work naturally, no lecture.
        if accountability_prompt:
            parts.append(
                "Quick check-in from me: you have overdue commitments on "
                "your plan. Want to talk about what got in the way, or "
                "should we reschedule them into something smaller?"
            )

        # Failure memory: planning that ignores what lapsed is generic advice.
        if failure_prompt:
            parts.append(
                "I've noticed some commitments lapsed unfinished before — "
                "let's keep this next step small enough that it survives a "
                "bad week."
            )

        # Pivot journaling nudge.
        if pivot_nudge:
            parts.append(
                "It sounds like you might be changing direction — what "
                "changed? If we record the decision and your reason, your "
                "future self will thank you."
            )

        reply_content = " ".join(parts)
        return CounselingMessage(
            role="counselor",
            content=reply_content,
            timestamp=datetime.now(timezone.utc).isoformat()
        )
