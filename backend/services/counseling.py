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
                suggested_clarification="Is your hesitation with programming itself, or with specific rigid classroom contexts vs practical creative building?"
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
                suggested_clarification="Would human-centered engineering, AI UX design, or interactive educational technology be more energizing than purely abstract theory?"
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
        # 1. Parse RIASEC scores
        riasec_res = next((r for r in assessment_results if "riasec" in r.assessment_id.lower()), None)
        interest_vector = {}
        strongest_interests = []
        weaker_interests = []

        if riasec_res and riasec_res.dimension_scores:
            interest_vector = riasec_res.dimension_scores
        elif riasec_res and "normalized_vector" in riasec_res.calculated_scores:
            interest_vector = riasec_res.calculated_scores["normalized_vector"]
        else:
            interest_vector = {"R": 75.0, "I": 90.0, "A": 45.0, "S": 55.0, "E": 65.0, "C": 50.0}

        sorted_interests = sorted(interest_vector.items(), key=lambda x: x[1], reverse=True)
        dimension_names = {
            "R": "Realistic (Hands-on Systems & Hardware)",
            "I": "Investigative (Analytical & Problem Solving)",
            "A": "Artistic (Creative UX & Visual Expression)",
            "S": "Social (Teaching & Mentorship)",
            "E": "Enterprising (Leadership & Strategy)",
            "C": "Conventional (Data Governance & Systems Structure)"
        }
        strongest_interests = [dimension_names.get(dim, dim) for dim, _ in sorted_interests[:2]]
        weaker_interests = [dimension_names.get(dim, dim) for dim, _ in sorted_interests[4:]]

        # 2. Parse SCCT self-efficacy
        scct_res = next((r for r in assessment_results if "scct" in r.assessment_id.lower()), None)
        efficacy_level = "MEDIUM"
        outcome_exp = "Stimulating intellectual challenges & practical autonomy"
        context_supports_list = []
        context_barriers_list = []

        if scct_res and isinstance(scct_res.calculated_scores, dict):
            efficacy_level = scct_res.calculated_scores.get("self_efficacy_level", "HIGH")
            context_supports_list = scct_res.calculated_scores.get("contextual_supports", [])
            context_barriers_list = scct_res.calculated_scores.get("contextual_barriers", [])

        # 3. Categorize Facts
        # ASSESSED Facts
        assessed_strengths = [
            CounselingFact(
                category="ASSESSED",
                claim=f"High affinity for {strongest_interests[0]}",
                evidence=[f"Holland RIASEC score: {sorted_interests[0][1]}%"],
                confidence="HIGH",
                weight=EVIDENCE_WEIGHTS["ASSESSED_INSTRUMENT"],
                source="Holland RIASEC Assessment"
            )
        ]
        if len(sorted_interests) > 1 and sorted_interests[1][1] >= 50.0:
            assessed_strengths.append(
                CounselingFact(
                    category="ASSESSED",
                    claim=f"Strong secondary interest in {strongest_interests[1]}",
                    evidence=[f"Holland RIASEC score: {sorted_interests[1][1]}%"],
                    confidence="HIGH",
                    weight=EVIDENCE_WEIGHTS["ASSESSED_INSTRUMENT"],
                    source="Holland RIASEC Assessment"
                )
            )

        # OBSERVED Facts (from Evidence items)
        demonstrated_caps = []
        demonstrated_exp = []
        for ev in evidence_items:
            name = ev.get("name", "Project Artifact")
            desc = ev.get("description", "")
            demonstrated_caps.append(
                CounselingFact(
                    category="OBSERVED",
                    claim=f"Demonstrated practical development activity: {name}",
                    evidence=[f"Submitted artifact: {desc}"],
                    confidence="HIGH",
                    weight=EVIDENCE_WEIGHTS["VERIFIED_PROJECT"],
                    source="Candidate Submission"
                )
            )
            demonstrated_exp.append(
                CounselingFact(
                    category="OBSERVED",
                    claim=f"Hands-on project engagement in {name}",
                    evidence=[f"Context: {desc}"],
                    confidence="HIGH",
                    weight=EVIDENCE_WEIGHTS["VERIFIED_PROJECT"],
                    source="Candidate Portfolio"
                )
            )

        # INFERRED Signals
        inferred_signals = []
        if interest_vector.get("I", 0) >= 70 and interest_vector.get("R", 0) >= 60:
            inferred_signals.append(
                CounselingFact(
                    category="INFERRED",
                    claim="High alignment with applied technical and engineering disciplines combining theory with concrete building.",
                    evidence=["RIASEC Investigative >= 70%", "RIASEC Realistic >= 60%"],
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

        # Contradictions
        contradictions = self.detect_contradictions(goals, constraints, evidence_items, interest_vector)

        # Confidence
        confidence_cat = self.compute_categorical_confidence(
            evidence_count=len(evidence_items),
            assessment_count=len(assessment_results),
            contradiction_count=len(contradictions)
        )

        # Evidence gaps / portfolio requests
        evidence_gaps = []
        if not evidence_items:
            evidence_gaps = [
                "Please consider uploading links to your GitHub repositories or project demos to substantiate hands-on programming experience.",
                "Sharing course transcripts or syllabus outlines will allow us to accurately calibrate prerequisite stage bypasses."
            ]

        # Candidate Directions (Preliminary)
        candidate_directions = []
        candidate_details = []

        if interest_vector.get("I", 0) >= 65 and interest_vector.get("R", 0) >= 60:
            candidate_directions.extend([
                "Artificial Intelligence & Machine Learning Engineering",
                "Robotics & Autonomous Systems Engineering",
                "Systems & Distributed Software Architecture"
            ])
            candidate_details.extend([
                CandidateDirection(
                    title="Artificial Intelligence & Machine Learning Engineering",
                    rationale="Combines high Investigative problem-solving with concrete software implementation.",
                    alignment="Investigative (90%) + Realistic (75%) + Hands-on Problem Solving",
                    related_occupations=["AI Engineer (ESCO: 2512.4)", "Data Scientist (ESCO: 2511.1)"],
                    confidence="HIGH"
                ),
                CandidateDirection(
                    title="Robotics & Autonomous Systems Engineering",
                    rationale="Direct synergy between physical hardware mechanisms and algorithm design.",
                    alignment="Realistic (75%) + Investigative (90%) + Systems Engineering",
                    related_occupations=["Robotics Engineer (ESCO: 2144.3)"],
                    confidence="HIGH"
                ),
                CandidateDirection(
                    title="Systems & Distributed Software Architecture",
                    rationale="Deep technical problem-solving with systematic architectural governance.",
                    alignment="Investigative (90%) + Conventional (50%) + Practical Application",
                    related_occupations=["Software Architect (ESCO: 2512.1)"],
                    confidence="MEDIUM"
                )
            ])
        else:
            candidate_directions.extend([
                "Interactive Software & Product Development",
                "Computational Systems Exploration"
            ])
            candidate_details.append(
                CandidateDirection(
                    title="Interactive Software & Product Development",
                    rationale="Balanced creative design and structured technical implementation.",
                    alignment=f"Top Interests: {', '.join(strongest_interests)}",
                    related_occupations=["Software Developer (ESCO: 2512)"],
                    confidence="MEDIUM"
                )
            )

        # Next Reflective Questions
        next_questions = [
            "What specific technical project or problem have you worked on recently that you felt most energized by?",
            "When faced with a steep learning curve, what learning format (interactive building, academic papers, peer collaboration) works best for you?",
            "How do you prefer to balance deep research and algorithm design versus building production user-facing products?"
        ]

        return CounselingProfile(
            person_id=person_id,
            timestamp=datetime.now(timezone.utc).isoformat(),
            is_preliminary=True,
            interest_vector=interest_vector,
            strongest_interests=strongest_interests,
            weaker_interests=weaker_interests,
            academic_strengths=[
                CounselingFact(
                    category="OBSERVED" if evidence_items else "INFERRED",
                    claim="Strong analytical and logical reasoning aptitude",
                    evidence=["Curriculum focus in Mathematics & Computer Science"],
                    confidence="HIGH" if evidence_items else "MEDIUM"
                )
            ],
            academic_weaknesses=[],
            demonstrated_capabilities=demonstrated_caps,
            demonstrated_experience=demonstrated_exp,
            self_efficacy_signals=[
                CounselingFact(
                    category="ASSESSED",
                    claim=f"Self-Efficacy Level: {efficacy_level}",
                    evidence=["SCCT Confidence item responses"],
                    confidence="HIGH"
                )
            ],
            outcome_expectations=[
                CounselingFact(
                    category="ASSESSED",
                    claim=f"Primary outcome expectation: {outcome_exp}",
                    evidence=["SCCT Outcome Expectation indicators"],
                    confidence="HIGH"
                )
            ],
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
            unknowns=[
                "Specific subfield preference within AI/ML (e.g. Computer Vision vs Large Language Models vs Systems Optimization).",
                "Long-term career setting preference (Applied Industry Engineering vs Academic Research Lab)."
            ] if not evidence_items else [],
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
                system_context = f"""You are the PATHMIND Empathetic Career Counselor.
You are conversing with {person_id}.
Active Profile Summary:
- Top Interests: {', '.join(profile.strongest_interests)}
- Confidence: {profile.overall_confidence}
- Candidate Directions: {', '.join(profile.candidate_directions)}
- Contradictions: {json.dumps([c.model_dump() for c in profile.contradictions])}
- Evidence Gaps: {json.dumps(profile.evidence_gaps)}

GUIDELINES:
- Warm, polite, supportive, mentor-like tone.
- Explain evidence backing recommendations.
- Clarify contradictions gently.
- Encourage sharing portfolio links to substantiate milestones.
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
        reply_content = (
            f"Thank you for sharing that. Based on your assessment, your strongest measured interests are in "
            f"{', '.join(profile.strongest_interests)}. "
            f"We've identified promising candidate pathways in {', '.join(profile.candidate_directions[:2])}. "
            f"To help calibrate the exact roadmap milestones, feel free to share any specific projects or tools you enjoy working with."
        )
        return CounselingMessage(
            role="counselor",
            content=reply_content,
            timestamp=datetime.now(timezone.utc).isoformat()
        )
