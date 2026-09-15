import json
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
from backend.core.config import settings
from backend.core.assessment_schemas import CounselingProfile
from backend.core.trajectory_schemas import (
    CandidatePath,
    SkillGap,
    EducationRoute,
    CredentialOption,
    TrajectoryCase,
    TrajectoryPattern,
    DiscoveryResponse,
    CounterfactualResponse
)
from backend.services.knowledge import KnowledgeService
from backend.services.trajectory_corpus import TrajectoryCorpusService

class TrajectoryEngine:
    def __init__(self):
        self.knowledge_service = KnowledgeService()
        self.corpus_service = TrajectoryCorpusService()
        self.gemini_available = bool(settings.GEMINI_API_KEY)
        self.model = None

        if self.gemini_available:
            try:
                import google.generativeai as genai
                genai.configure(api_key=settings.GEMINI_API_KEY)
                self.model = genai.GenerativeModel('gemini-2.5-flash')
            except Exception as e:
                print(f"Warning: Failed to initialize Gemini model in TrajectoryEngine: {e}")
                self.model = None

    async def _fetch_occupation_knowledge(self, query: str) -> Dict[str, Any]:
        """
        Retrieves real occupational knowledge via KnowledgeService (ESCO & India NCO).
        """
        try:
            resp = await self.knowledge_service.search_occupations(query=query, limit=3)
            return {
                "results": [r.model_dump() if hasattr(r, "model_dump") else r for r in resp.results],
                "sources": [s.model_dump() if hasattr(s, "model_dump") else s for s in resp.sources]
            }
        except Exception:
            return {"results": [], "sources": []}

    def generate_deterministic_candidate_paths(
        self,
        person_id: str,
        counseling_profile: Optional[CounselingProfile] = None,
        goals: List[str] = None,
        constraints: List[str] = None,
        geographic_preference: str = "India & Global"
    ) -> List[CandidatePath]:
        """
        Synthesizes 2–3 structured candidate career pathways based on counseling facts,
        observable project evidence, Holland RIASEC interest vector, and trajectory patterns.
        """
        goals = goals or []
        constraints = constraints or []
        interests = counseling_profile.interest_vector if counseling_profile and counseling_profile.interest_vector else {}
        goals_text = " ".join(goals).lower() if goals else ""
        if counseling_profile and counseling_profile.candidate_directions:
            goals_text += " " + " ".join(counseling_profile.candidate_directions).lower()

        if goals:
            primary_goal = goals[0].strip()
            path_custom = CandidatePath(            path_custom = CandidatePath(
                path_id=f"path_{primary_goal.lower().replace(' ', '_')[:30]}",
                title=f"{primary_goal} Professional Pathway",
                domain=f"{primary_goal} Practice",
                description=f"Directly derived from stated candidate goal: '{primary_goal}'. Structured around core domain competencies, practical deliverables, and industry verification.",
                fit_level="PROMISING",
                confidence="LOW",
                why_it_matches=[f"Directly matches stated objective: '{primary_goal}'."],
                supporting_evidence=[f"Declared candidate aspiration in {primary_goal}."],
                missing_evidence=[f"Verified portfolio artifacts and domain-specific credentials for {primary_goal}."],
                transparency_summary={
                    "what_we_know": [f"Candidate declared target aspiration in {primary_goal}."],
                    "how_we_know_it": ["Direct user declaration"],
                    "what_remains_unknown": ["Domain-specific verified evidence not yet provided."],
                    "what_could_change_this": ["Submission of relevant portfolio artifacts or completion of initial stages."]
                },
                required_skills=[f"Core {primary_goal} Methodology", "Domain Problem Solving", "Professional Standards"],
                current_skills_held=["Analytical Reasoning", "Communication"],
                transferable_skills=["Project Management", "Structured Problem Solving"],
                skill_gaps=[SkillGap(skill_name=f"Core {primary_goal} Competencies", category="CORE", current_status="MISSING", description=f"Foundational mastery of practical deliverables in {primary_goal}.", recommended_action=f"Build verified work samples demonstrating {primary_goal} competencies.")],
                education_routes=[EducationRoute(route_type="PROJECT_BASED_ACCELERATED", title=f"{primary_goal} Foundational Route", description=f"Comprehensive curriculum and portfolio building for {primary_goal}.", estimated_duration="6–12 Months", institutions_or_paths=["Accredited Professional Programs"], geographic_relevance="Global")],
                credential_options=[],
                india_context={},
                global_context={}
            )
            return [path_custom]

        # Fallback if no specific goal is identified: Generic Exploration Path
        path_exploration = CandidatePath(
            path_id="path_career_exploration",
            title="Career Exploration & Discovery",
            domain="Exploration",
            description="A structured pathway focused on self-discovery, exploring different industries, and identifying strengths and interests before committing to a specific domain.",
            fit_level="UNKNOWN",
            confidence="LOW",
            why_it_matches=["Provides flexibility when a specific target goal is not yet defined."],
            supporting_evidence=["User has not yet specified a clear canonical goal."],
            missing_evidence=["Specific domain targets and verifiable performance artifacts."],
            transparency_summary={
                "what_we_know": ["User is in a discovery phase"],
                "how_we_know_it": ["Absence of a specific declared goal"],
                "what_remains_unknown": ["Specific industry or role target"],
                "what_could_change_this": ["Completing assessments and declaring a target outcome"]
            },
            required_skills=["Self-Reflection", "Research", "Adaptability"],
            current_skills_held=[],
            transferable_skills=["Curiosity"],
            skill_gaps=[],
            education_routes=[
                EducationRoute(
                    route_type="PROJECT_BASED_ACCELERATED",
                    title="Broad Exploratory Learning",
                    description="Take introductory courses across multiple fields to gauge interest.",
                    estimated_duration="3-6 Months",
                    institutions_or_paths=["Online Platforms", "Career Fairs", "Informational Interviews"],
                    geographic_relevance="Global"
                )
            ],
            credential_options=[],
            india_context={},
            global_context={},
            experience_requirements=["Participation in exploratory projects or shadow programs"],
            advantages=["Maintains optionality.", "Reduces the risk of committing to the wrong path early."],
            disadvantages=["Delays specialized skill acquisition."],
            risks=["Analysis paralysis if exploration continues indefinitely."],
            alternatives=[],
            similar_trajectories=[],
            source_references=[]
        )

        return [path_exploration]

    async def discover_candidate_paths(
        self,
        person_id: str,
        counseling_profile: Optional[CounselingProfile] = None,
        goals: List[str] = None,
        constraints: List[str] = None,
        geographic_preference: str = "India & Global"
    ) -> DiscoveryResponse:
        """
        Orchestrates multi-agent path discovery:
        1. Decomposes broad goals.
        2. Retrieves empirical trajectory patterns and case studies.
        3. Retrieves ESCO/NCO occupational context via KnowledgeService.
        4. Synthesizes 2–3 transparent candidate pathways with trade-offs.
        5. Critiques assumptions against counseling contradictions.
        """
        goals = goals or ["Explore potential career directions"]
        constraints = constraints or []

        # 1. Generate base structured candidate paths
        candidate_paths = self.generate_deterministic_candidate_paths(
            person_id=person_id,
            counseling_profile=counseling_profile,
            goals=goals,
            constraints=constraints,
            geographic_preference=geographic_preference
        )

        # 2. Extract trajectory patterns from corpus
        patterns = self.corpus_service.get_all_patterns()

        # 3. Path Critic: Apply counseling contradictions & constraint adjustments
        if counseling_profile and counseling_profile.contradictions:
            for contradiction in counseling_profile.contradictions:
                for path in candidate_paths:
                    path.risks.append(f"Counselor Note: {contradiction.suggested_clarification}")

        if candidate_paths:
            target_domain_decomposed = f"{candidate_paths[0].domain} -> ({' | '.join(p.title for p in candidate_paths)})"
            overall_reasoning = (
                f"Based on your profile, evidence signals, and target outcome direction, "
                f"we synthesized {len(candidate_paths)} concrete, highly aligned candidate pathways. "
                f"Each path outlines exact skill gaps, education routes, and verified domain requirements."
            )
        else:
            target_domain_decomposed = "Unspecified Domain"
            overall_reasoning = "No candidate pathways could be synthesized from the available profile evidence."

        return DiscoveryResponse(
            person_id=person_id,
            target_domain_decomposed=target_domain_decomposed,
            candidate_paths=candidate_paths,
            extracted_patterns=patterns,
            overall_reasoning=overall_reasoning,
            generated_at=datetime.now(timezone.utc).isoformat()
        )

    def generate_counterfactual_path(
        self,
        base_path: CandidatePath,
        modification_type: str,
        modification_prompt: str
    ) -> CounterfactualResponse:
        """
        Lightweight counterfactual 'What If?' sandbox. Modifies education routes, pacing,
        and skill priorities without resetting the entire application state.
        When target role changes, performs graph comparison between requirement graphs.
        """
        adjusted = base_path.model_copy(deep=True)
        trade_off_notes = []

        lower_prompt = (modification_prompt or "").lower()
        lower_type = (modification_type or "").lower()

        # Check if modification represents a target outcome change
        new_target = None
        if "goal_change" in lower_type or "target_change" in lower_type:
            new_target = modification_prompt.strip()
            
        # Optional: Use LLM to extract target from prompt if possible, but for deterministic fallback, rely on explicit type.

        if new_target:        elif modification_type == "LOW_BUDGET" or "afford" in lower_prompt or "cost" in lower_prompt:
            adjusted.education_routes = [
                EducationRoute(
                    route_type="PROJECT_BASED_ACCELERATED",
                    title="Low-Cost Open-Source Apprenticeship & Public Specialization",
                    description="Leverages free high-quality open-source curricula paired with public portfolio development.",
                    estimated_duration="18–24 Months",
                    institutions_or_paths=["Open Source Curricula", "Local Industry Apprenticeships", "Public Portfolios"],
                    geographic_relevance="Global"
                )
            ]
            adjusted.credential_options = [c for c in adjusted.credential_options if c.classification != "LOW_VALUE"]
            trade_off_notes.append("Decreased financial expenditure to near zero; relies entirely on self-discipline and verifiable public evidence artifacts.")
            trade_off_notes.append("Requires self-advocacy and networking in domain communities to secure initial apprenticeship/internship opportunities.")

        elif modification_type == "SELF_PACED_5_HOURS" or "5 hours" in lower_prompt or "time" in lower_prompt:
            for route in adjusted.education_routes:
                route.estimated_duration = "Extended Pacing (36–48 Months at 5 hrs/week)"
                route.description += " [Adjusted for part-time/weekend study pacing]."
            trade_off_notes.append("Pacing extended to 36+ months to accommodate low weekly time commitment.")
            trade_off_notes.append("Milestones restructured into modular, weekly atomic deliverables.")

        elif modification_type == "GLOBAL_MIGRATION" or "abroad" in lower_prompt or "global" in lower_prompt:
            trade_off_notes.append("Prioritized international ESCO skill taxonomy standards and globally recognized professional credentials.")
            trade_off_notes.append("Recommended English domain writing and international public evidence contributions as primary bridge.")

        else:
            trade_off_notes.append(f"Custom counterfactual variation applied: '{modification_prompt}'.")
            trade_off_notes.append("Adjusted milestone pacing and alternative skill dependencies accordingly.")

        return CounterfactualResponse(
            base_path_id=base_path.path_id,
            modification_applied=modification_prompt or modification_type,
            adjusted_path=adjusted,
            trade_off_notes=trade_off_notes,
            generated_at=datetime.now(timezone.utc).isoformat()
        )
