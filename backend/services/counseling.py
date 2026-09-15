import os
import json
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
from backend.services.knowledge import KnowledgeService

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
                self.model = genai.GenerativeModel('gemini-2.5-flash')
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

    def counsel_chat(
        self,
        person_id: str,
        user_message: str,
        profile: CounselingProfile,
        history: List[CounselingMessage] = None
    ) -> CounselingMessage:
        """
        Interactive counseling dialogue that explains findings, answers questions,
        and provides guidance without mutating source assessment records.
        """
        history = history or []
        
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

GUIDELINES:
- Warm, polite, supportive, mentor-like tone.
- Explain evidence backing recommendations.
- Clarify contradictions gently.
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
        if profile.strongest_interests:
            parts.append(f"Based on your assessment, your strongest measured interests are in {', '.join(profile.strongest_interests)}.")
        else:
            parts.append("Your psychometric interest profile is currently unassessed.")

        if profile.candidate_directions:
            parts.append(f"We've identified promising candidate pathways in {', '.join(profile.candidate_directions[:2])}.")
        else:
            parts.append("Once you declare a target outcome or complete a diagnostic assessment, we can map out tailored candidate pathways.")

        parts.append("Feel free to share your primary goal or any specific projects, background, and constraints to help calibrate your plan.")
        reply_content = " ".join(parts)
        return CounselingMessage(
            role="counselor",
            content=reply_content,
            timestamp=datetime.now(timezone.utc).isoformat()
        )
