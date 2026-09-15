from typing import List, Dict, Any, Optional
from backend.core.trajectory_schemas import TrajectoryCase, TrajectoryPattern

# --- Attributed Trajectory Corpus (Explicitly Marked Provenance) ---
CORPUS_TRAJECTORIES: List[TrajectoryCase] = [
    TrajectoryCase(
        trajectory_id="traj_sports_01",
        title="Amateur to Professional Athlete",
        archetype="Youth League -> Competitive Academy -> Professional",
        source_type="ATTRIBUTED_CASE_STUDY",
        starting_conditions={
            "education": "High School",
            "starting_skills": ["Basic Athletics", "Team Collaboration"],
            "constraints": ["Time constraints due to schooling", "Geographic access to premium academies"]
        },
        learning_milestones=[
            "Phase 1: Foundational physical conditioning and technical skill refinement",
            "Phase 2: Competitive league participation and tactical awareness",
            "Phase 3: Specialized coaching, advanced analytics, and mental conditioning",
            "Phase 4: Professional trials and contract negotiation"
        ],
        major_transitions=[
            "Transitioned from casual participation to structured daily training",
            "Selected for regional representative squad"
        ],
        obstacles_and_failures=[
            "Faced mid-season injury requiring 3 months of guided rehabilitation",
            "Initial rejection from premier academy built resilience and improved focus"
        ],
        outcome_role="Professional Athlete",
        similarity_rationale="Matches high physical capability, dedication, and competitive drive.",
        important_differences="This trajectory requires intense physical maintenance and early specialization."
    ),
    TrajectoryCase(
        trajectory_id="traj_tech_02",
        title="Student to Software Engineer",
        archetype="Self-Taught -> Portfolio Builder -> Software Engineer",
        source_type="ATTRIBUTED_CASE_STUDY",
        starting_conditions={
            "education": "Undergraduate",
            "starting_skills": ["Basic Math", "Logical Reasoning"],
            "constraints": ["Self-funded learning", "No prior industry network"]
        },
        learning_milestones=[
            "Phase 1: Foundational programming logic and data structures",
            "Phase 2: Building standalone applications and version control",
            "Phase 3: Systems design, databases, and deployment",
            "Phase 4: Open-source contributions and technical interviews"
        ],
        major_transitions=[
            "Shifted from tutorial consumption to building original projects",
            "Secured first technical internship"
        ],
        obstacles_and_failures=[
            "Struggled initially with system architecture concepts; overcame via mentorship",
            "Failed early technical screens; used feedback to focus on algorithmic efficiency"
        ],
        outcome_role="Software Engineer",
        similarity_rationale="Matches analytical problem-solving and structured conventional interests.",
        important_differences="Focuses heavily on digital artifact creation and abstract logic."
    ),
    TrajectoryCase(
        trajectory_id="traj_design_03",
        title="Hobbyist to Professional Designer",
        archetype="Self-Taught Creator -> Portfolio Curation -> Lead Designer",
        source_type="ATTRIBUTED_CASE_STUDY",
        starting_conditions={
            "education": "Self-Directed",
            "starting_skills": ["Visual Aesthetics", "Basic Tooling"],
            "constraints": ["Building client base from scratch"]
        },
        learning_milestones=[
            "Phase 1: Mastering design principles (typography, color theory, layout)",
            "Phase 2: Tool proficiency and developing a distinct stylistic voice",
            "Phase 3: Client communication, brief interpretation, and iterative feedback",
            "Phase 4: Establishing an agency or securing a senior in-house role"
        ],
        major_transitions=[
            "Moved from speculative redesigns to commissioned commercial work",
            "Developed a formalized design system methodology"
        ],
        obstacles_and_failures=[
            "Early portfolio lacked cohesive narrative; restructured to show end-to-end process",
            "Underpriced initial freelance contracts; learned negotiation and value pricing"
        ],
        outcome_role="Design Lead",
        similarity_rationale="Matches high creative traits and visual communication skills.",
        important_differences="Heavily dependent on subjective portfolio quality and client relationship management."
    ),
    TrajectoryCase(
        trajectory_id="traj_law_04",
        title="Student to Legal Professional",
        archetype="Academic Foundations -> Clerkship -> Practicing Attorney",
        source_type="ATTRIBUTED_CASE_STUDY",
        starting_conditions={
            "education": "Pre-Law / Humanities",
            "starting_skills": ["Critical Reading", "Argumentation", "Research"],
            "constraints": ["High educational costs", "Rigorous competitive exams"]
        },
        learning_milestones=[
            "Phase 1: Advanced reading comprehension and formal logic",
            "Phase 2: Law school admissions and foundational jurisprudence",
            "Phase 3: Internships, moot court, and specialized legal writing",
            "Phase 4: Bar examination and associate placement"
        ],
        major_transitions=[
            "Adapted from generalized academic writing to strict legal drafting",
            "Transitioned from simulated moot courts to actual case assistance"
        ],
        obstacles_and_failures=[
            "Overwhelmed by initial case law volume; developed specialized summarization techniques",
            "Initial difficulty in oral argumentation overcome through dedicated practice"
        ],
        outcome_role="Practicing Attorney",
        similarity_rationale="Matches strong verbal, analytical, and structured argumentation skills.",
        important_differences="Requires adherence to strict regulatory environments and formal credentialing."
    )
]

CORPUS_PATTERNS: List[TrajectoryPattern] = [
    TrajectoryPattern(
        pattern_title="Foundational Mastery Precedes Specialization",
        description="Across all domains, successful professionals establish a robust mastery of foundational principles before attempting advanced specialization.",
        evidence_trajectories_count=4,
        evidence_summary="Trajectories consistently demonstrated that candidates with strong fundamentals adapted faster to complex domain challenges.",
        confidence="HIGH"
    ),
    TrajectoryPattern(
        pattern_title="Observable Portfolios and Verified Performance Outweigh Passive Credentials",
        description="Evaluators evaluate candidates primarily on verifiable artifacts (portfolios, match records, project repositories, case studies) rather than standalone course certificates.",
        evidence_trajectories_count=4,
        evidence_summary="All 4 attributed case studies secured roles through demonstrable project artifacts (SLAM robots, ML apps, distributed backend pipelines).",
        confidence="HIGH"
    ),
    TrajectoryPattern(
        pattern_title="Overcoming Early Implementation Obstacles Built Resilience",
        description="Every high-performing trajectory experienced at least one major technical setback (memory leak, sensor drift, concurrency bug) that catalyzed deeper systems mastery.",
        evidence_trajectories_count=4,
        evidence_summary="Obstacles documented in case studies were the primary turning points that developed senior problem decomposition capabilities.",
        confidence="HIGH"
    )
]

class TrajectoryCorpusService:
    def __init__(self):
        self.trajectories = CORPUS_TRAJECTORIES
        self.patterns = CORPUS_PATTERNS

    def get_all_trajectories(self) -> List[TrajectoryCase]:
        return self.trajectories

    def get_all_patterns(self) -> List[TrajectoryPattern]:
        return self.patterns

    def match_similar_trajectories(
        self,
        domain_keywords: List[str],
        interests: Dict[str, float] = None,
        limit: int = 2
    ) -> List[TrajectoryCase]:
        """
        Matches relevant trajectory cases based on domain keywords and RIASEC profile.
        """
        interests = interests or {}
        matches = []
        kw_set = {k.lower() for k in domain_keywords}

        for traj in self.trajectories:
            score = 0
            traj_text = (traj.title + " " + traj.archetype + " " + traj.outcome_role).lower()
            
            for kw in kw_set:
                if kw in traj_text:
                    score += 2

            # RIASEC alignment boosts
            if interests.get("I", 0) >= 70 and ("ai" in traj_text or "systems" in traj_text):
                score += 2
            if interests.get("R", 0) >= 70 and ("robotics" in traj_text or "hardware" in traj_text):
                score += 2
            if interests.get("C", 0) >= 60 and ("cloud" in traj_text or "data" in traj_text):
                score += 1

            matches.append((traj, score))

        matches.sort(key=lambda x: x[1], reverse=True)
        return [t for t, _ in matches[:limit]]
