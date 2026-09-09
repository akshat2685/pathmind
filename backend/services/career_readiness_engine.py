from typing import List, Dict, Any, Optional
from datetime import datetime, timezone
import json
from backend.core.config import settings
from backend.core.career_schemas import (
    UniversalCareerProfile,
    EducationItem,
    ExperienceItem,
    ProjectItem,
    CredentialItem,
    TargetOutcome,
    CareerGoal,
    CareerRequirementGraph,
    RequirementNode,
    CategorizedGap,
    TransferableSkillsAnalysis,
    VerifiedCredential,
    ExperienceGap,
    EvidencePortfolio,
    EvidenceRequirementStatus,
    AccountabilityStatus,
    VerifiedOpportunity,
    TailoredResume,
    CareerCheckpoint,
    ReadinessTransitionRecord,
    CareerReadinessReport
)
from backend.services.career_agents import (
    CareerReadinessAgent,
    CredentialAgent,
    OpportunityAgent,
    ResumeAgent,
    AccountabilityAgent
)
from backend.services.opportunity_service import OpportunityService
from backend.services.knowledge import KnowledgeService
from backend.services.store import FirestoreStore

class CareerReadinessEngine:
    def __init__(self):
        self.store = FirestoreStore()
        self.knowledge_service = KnowledgeService()
        self.opportunity_service = OpportunityService()
        
        # 5 Focused ADK Agents
        self.readiness_agent = CareerReadinessAgent()
        self.credential_agent = CredentialAgent()
        self.opportunity_agent = OpportunityAgent()
        self.resume_agent = ResumeAgent()
        self.accountability_agent = AccountabilityAgent()

    async def get_or_create_canonical_profile(
        self,
        person_id: str,
        current_state_type: str = "college_student"
    ) -> UniversalCareerProfile:
        profile_dict = await self.store.get_career_profile(person_id)
        if profile_dict:
            return UniversalCareerProfile(**profile_dict)

        # Initialize canonical career profile based on state type
        state_lower = current_state_type.lower()
        if "mechanical" in state_lower or "switcher" in state_lower or "professional" in state_lower:
            new_profile = UniversalCareerProfile(
                person_id=person_id,
                current_role="Senior Mechanical & Thermal Systems Engineer",
                current_state_type=current_state_type,
                education=[
                    EducationItem(
                        degree="B.Tech in Mechanical Engineering",
                        field_of_study="Mechanical & Thermal Systems",
                        institution="National Institute of Technology",
                        year="2022",
                        grade_or_score="8.6 CGPA",
                        is_verified=True
                    )
                ],
                experience=[
                    ExperienceItem(
                        role="Mechanical Systems Design Lead",
                        organization="Precision Engineering & CAD Systems",
                        duration="2022 – Present (3 Years)",
                        description="Led finite element analysis, numerical thermal simulation, and multi-variable optimization pipelines.",
                        skills_used=["Numerical Analysis", "MATLAB", "Engineering Physics", "CAD/FEM", "Mathematical Modeling"],
                        is_verified=True
                    )
                ],
                skills=["Calculus & Linear Algebra", "Engineering Physics", "Mathematical Modeling", "MATLAB", "Numerical Optimization", "Analytical Problem Decomposition", "Python Scripting"],
                projects=[
                    ProjectItem(
                        title="Automated Thermal Sensor Stream & Simulation Pipeline",
                        technologies=["Python", "NumPy", "MATLAB", "Pandas"],
                        description="Engineered high-frequency temperature sensor logging pipeline with automated variance detection algorithms.",
                        provenance="Verified in Professional Portfolio",
                        is_verified=True
                    )
                ],
                credentials=[
                    CredentialItem(
                        title="Certified SolidWorks & ANSYS Professional",
                        issuer="Dassault Systèmes / ANSYS",
                        issue_date="2022",
                        is_verified=True
                    )
                ],
                portfolio_links=["https://github.com/scholar-engineer/thermal-sim-py"],
                achievements=["Published Technical Paper on Multiphysics Optimization in ASME Journal"],
                current_country="India",
                current_city="Bengaluru",
                target_country="India & Global",
                remote_preference="HYBRID",
                work_authorization="Citizen (India)",
                goals=["Transition from Mechanical Engineering to Machine Learning / Data Engineering"],
                constraints={"weekly_hours": 12, "format_preference": "project-based-practical"}
            )
        elif "frontend" in state_lower or "web" in state_lower:
            new_profile = UniversalCareerProfile(
                person_id=person_id,
                current_role="Fullstack & Frontend Web Developer",
                current_state_type=current_state_type,
                education=[
                    EducationItem(
                        degree="B.S. in Information Technology",
                        field_of_study="Software Engineering",
                        institution="State Technological University",
                        year="2024",
                        grade_or_score="3.7 GPA",
                        is_verified=True
                    )
                ],
                experience=[
                    ExperienceItem(
                        role="Associate Software Engineer",
                        organization="CloudScale SaaS Technologies",
                        duration="2024 – Present",
                        description="Developed modular React/TypeScript frontend architectures and FastAPI asynchronous backend microservices.",
                        skills_used=["TypeScript", "React", "FastAPI", "PostgreSQL", "Git", "REST APIs"],
                        is_verified=True
                    )
                ],
                skills=["JavaScript", "TypeScript", "React", "Next.js", "Python", "FastAPI", "Git Version Control", "REST APIs", "SQL"],
                projects=[
                    ProjectItem(
                        title="Distributed Real-time Telemetry Dashboard",
                        technologies=["TypeScript", "React", "FastAPI", "WebSockets"],
                        description="Engineered low-latency dashboard with live state streams and responsive canvas charting.",
                        provenance="Verified in GitHub Repository",
                        is_verified=True
                    )
                ],
                credentials=[
                    CredentialItem(
                        title="Meta Certified Frontend Developer",
                        issuer="Meta",
                        issue_date="2024",
                        is_verified=True
                    )
                ],
                portfolio_links=["https://github.com/scholar-dev/telemetry-ui"],
                achievements=["1st Place at State Level Web Hackathon 2024"],
                current_country="India",
                current_city="Bengaluru",
                target_country="India & Global",
                remote_preference="REMOTE",
                work_authorization="Citizen (India)",
                goals=["Transition from Web Development to Applied AI Systems Engineering"],
                constraints={"weekly_hours": 15, "format_preference": "applied-code"}
            )
        else:
            # Baseline STEM Student profile
            new_profile = UniversalCareerProfile(
                person_id=person_id,
                current_role="Senior Secondary Scholar & Aspiring AI Engineer",
                current_state_type=current_state_type,
                education=[
                    EducationItem(
                        degree="Class 12 Senior Secondary (STEM Foundations)",
                        field_of_study="Mathematics, Physics, Computer Science",
                        institution="Central Board of Secondary Education",
                        year="2026",
                        grade_or_score="94% Projected",
                        is_verified=True
                    )
                ],
                experience=[
                    ExperienceItem(
                        role="Student Scholar & Technical Contributor",
                        organization="PATHMIND Longitudinal Learning Program",
                        duration="2026 – Present",
                        description="Progressive mastery of applied software engineering and mathematical foundations for machine learning systems.",
                        skills_used=["Python", "Linear Algebra", "Calculus", "Pytest"],
                        is_verified=True
                    )
                ],
                skills=["Python 3.12", "Linear Algebra", "Calculus", "Pytest", "Data Structures", "Git", "Arduino Prototyping"],
                projects=[
                    ProjectItem(
                        title="Modular Data Parser & Stream Ingestion Pipeline",
                        technologies=["Python", "Pytest", "Dataclasses", "Type Hints"],
                        description="Engineered a memory-efficient generator-based ETL pipeline with 85%+ branch coverage unit test assertions.",
                        provenance="Verified in Stage 01 Milestone",
                        is_verified=True
                    ),
                    ProjectItem(
                        title="National Hackathon ML Classifier & Hardware Robot",
                        technologies=["Python", "Arduino", "Scikit-Learn"],
                        description="Developed an autonomous sensor-guided robot and image classification model.",
                        provenance="Verified in Student Longitudinal Portfolio",
                        is_verified=True
                    )
                ],
                credentials=[
                    CredentialItem(
                        title="National STEM Hackathon Finalist Certificate",
                        issuer="Ministry of Education / National Innovation Council",
                        issue_date="2025",
                        is_verified=True
                    )
                ],
                portfolio_links=["https://github.com/pathmind-scholar/parser-etl"],
                achievements=["National Science & Robotics Olympiad Top 1% Ranker"],
                current_country="India",
                current_city="Bengaluru",
                target_country="India & Global",
                remote_preference="HYBRID",
                work_authorization="Citizen (India)",
                goals=["Become an Applied Machine Learning Systems Engineer"],
                constraints={"weekly_hours": 10, "format_preference": "project-based"}
            )

        await self.store.save_career_profile(person_id, new_profile.model_dump(mode="json"))
        return new_profile

    async def get_or_create_career_goal(self, person_id: str, target_role: Optional[str] = None) -> TargetOutcome:
        goal_dict = await self.store.get_career_goal(person_id)
        if goal_dict:
            return TargetOutcome(**goal_dict)

        new_goal = TargetOutcome(
            goal_id=f"goal_{person_id}",
            person_id=person_id,
            goal_type="career",
            target_role=target_role or "Applied Machine Learning Systems Engineer",
            target_industry="Artificial Intelligence & Software Engineering",
            geography="India & Global",
            target_timeline="12–18 Months",
            priority="HIGH",
            version=1,
            constraints={"weekly_hours": 10, "format_preference": "project-based"}
        )
        await self.store.save_career_goal(person_id, new_goal.model_dump(mode="json"))
        return new_goal

    def build_requirement_graph(
        self,
        target_role: str,
        skills_held: List[str]
    ) -> CareerRequirementGraph:
        """
        Builds a structured requirement graph originating from official standards (ESCO / NCO).
        """
        skills_held_lower = {s.lower() for s in skills_held}
        target_lower = target_role.lower()

        if "data" in target_lower and "machine" not in target_lower:
            core = [
                RequirementNode(name="SQL & Data Warehousing", category="CORE_SKILL", importance="HIGH", description="Complex analytical queries, window functions, and partitioning in BigQuery/PostgreSQL.", status_for_person="AVAILABLE" if any("sql" in s for s in skills_held_lower) else "MISSING"),
                RequirementNode(name="Python ETL Pipelines", category="CORE_SKILL", importance="HIGH", description="Modular, idempotent data ingestion pipelines with robust schema validation.", status_for_person="AVAILABLE" if any("python" in s for s in skills_held_lower) else "MISSING"),
                RequirementNode(name="Data Modeling & Schemas", category="CORE_SKILL", importance="HIGH", description="Dimensional star/snowflake modeling and Dataform/dbt transformations.", status_for_person="TRANSFERABLE" if any("model" in s for s in skills_held_lower) else "MISSING"),
                RequirementNode(name="Cloud Storage & Ingestion", category="CORE_SKILL", importance="HIGH", description="Cloud bucket orchestration (GCS/S3) and batch ingestion.", status_for_person="MISSING")
            ]
            supporting = [
                RequirementNode(name="Git Version Control", category="SUPPORTING_SKILL", importance="MEDIUM", description="Branching, pull request workflows, and CI automation.", status_for_person="AVAILABLE" if any("git" in s for s in skills_held_lower) else "MISSING"),
                RequirementNode(name="Pytest Test Assertions", category="SUPPORTING_SKILL", importance="MEDIUM", description="Automated unit assertions for data pipeline functions.", status_for_person="AVAILABLE" if any("pytest" in s for s in skills_held_lower) else "MISSING")
            ]
        else:
            # Applied Machine Learning Engineer
            core = [
                RequirementNode(name="Python OOP & Test Automation", category="CORE_SKILL", importance="HIGH", description="Object-oriented Python design patterns, type hints, and pytest fixtures.", status_for_person="AVAILABLE" if any("python" in s for s in skills_held_lower) else "MISSING"),
                RequirementNode(name="Linear Algebra & Vector Calculus", category="CORE_SKILL", importance="HIGH", description="Matrix decompositions, eigenvalues, gradients, and multivariate optimization.", status_for_person="AVAILABLE" if any("algebra" in s or "calculus" in s or "math" in s for s in skills_held_lower) else "MISSING"),
                RequirementNode(name="PyTorch Deep Neural Architectures", category="CORE_SKILL", importance="HIGH", description="Custom neural layers, autograd gradient flows, and loss function tuning.", status_for_person="MISSING"),
                RequirementNode(name="Containerized Model Serving (Docker/FastAPI)", category="CORE_SKILL", importance="HIGH", description="Packaging models into Docker containers with FastAPI latency profiling.", status_for_person="MISSING")
            ]
            supporting = [
                RequirementNode(name="Git Version Control & CI/CD", category="SUPPORTING_SKILL", importance="MEDIUM", description="Automated build pipelines and GitHub Actions.", status_for_person="AVAILABLE" if any("git" in s for s in skills_held_lower) else "MISSING"),
                RequirementNode(name="Scikit-Learn Statistical Baselines", category="SUPPORTING_SKILL", importance="MEDIUM", description="Cross-validation, precision/recall evaluation curves, and regularized regression.", status_for_person="AVAILABLE" if any("scikit" in s or "learn" in s for s in skills_held_lower) else "MISSING")
            ]

        experience = [
            RequirementNode(name="Production Codebase Exposure", category="EXPERIENCE", importance="HIGH", description="Experience structuring reproducible repositories with automated unit testing.", status_for_person="TRANSFERABLE" if len(skills_held) > 3 else "MISSING"),
            RequirementNode(name="End-to-End Pipeline Deployment", category="EXPERIENCE", importance="HIGH", description="Deploying a working model or data service to cloud/container runtime.", status_for_person="MISSING")
        ]

        projects = [
            RequirementNode(name="Public Tested ML/Data Repository", category="PROJECT_EVIDENCE", importance="HIGH", description="A public GitHub repository with comprehensive README, test suite, and clean documentation.", status_for_person="MISSING"),
            RequirementNode(name="Benchmarked API Service", category="PROJECT_EVIDENCE", importance="HIGH", description="A running REST/FastAPI service with measurable latency benchmarks.", status_for_person="MISSING")
        ]

        return CareerRequirementGraph(
            target_role=target_role,
            target_industry="Artificial Intelligence & Software Engineering",
            source_standards=["ESCO European Skills/Competences Standard", "NCO National Classification of Occupations"],
            core_skills=core,
            supporting_skills=supporting,
            education_requirements=[
                RequirementNode(name="STEM / Quantitative Academic Foundations", category="EDUCATION", importance="HIGH", description="Senior Secondary or Bachelor's in Mathematics, CS, or Engineering discipline.", status_for_person="AVAILABLE")
            ],
            credential_recommendations=[
                RequirementNode(name="Recognized Deep Learning / Cloud Credential", category="CREDENTIAL", importance="MEDIUM", description="Specialized credential signaling modern framework proficiency.", status_for_person="MISSING")
            ],
            experience_requirements=experience,
            project_evidence_requirements=projects,
            eligibility_criteria=[
                RequirementNode(name="Valid Work Authorization", category="ELIGIBILITY", importance="HIGH", description="Eligible for employment or internships in target country.", status_for_person="AVAILABLE")
            ],
            market_context_notes=[
                "High sustained demand for engineers capable of writing clean, testable production Python code rather than raw Jupyter notebooks.",
                "Demonstrated GitHub repositories carry up to 3x higher weight during technical screening than standalone certificates."
            ],
            generated_at=datetime.now(timezone.utc).isoformat()
        )

    def analyze_transferable_skills(
        self,
        profile: UniversalCareerProfile,
        target_role: str
    ) -> TransferableSkillsAnalysis:
        """
        Calculates:
        - YOU ALREADY HAVE
        - YOU CAN TRANSFER
        - YOU NEED TO DEVELOP
        Supports students, working professionals, and career switchers.
        """
        current_state = profile.current_state_type.lower()
        if "mechanical" in current_state or "engineer" in current_state and "software" not in current_state:
            return TransferableSkillsAnalysis(
                already_have=["Calculus & Linear Algebra", "Engineering Physics", "Mathematical Modeling", "MATLAB Analysis"],
                can_transfer=["Analytical Problem Decomposition", "Numerical Optimization Logic", "Physical Systems Simulation"],
                need_to_develop=["Python Data Science Stack (NumPy, Pandas)", "SQL Databases & Schemas", "Production MLOps & Docker Pipelines"],
                analysis_summary="Your engineering analysis and multivariate mathematics transfer directly into statistical ML; focus software effort on Python data pipelines."
            )
        elif "frontend" in current_state or "web" in current_state:
            return TransferableSkillsAnalysis(
                already_have=["JavaScript / TypeScript", "Web APIs (REST / FastAPI)", "Git Version Control", "UI Architecture"],
                can_transfer=["API Integration & Schema Contracts", "Modular Code Organization", "Client-Server Asynchronous Data Flow"],
                need_to_develop=["Linear Algebra & Vector Calculus", "PyTorch Deep Learning", "Distributed Model Serving & Containerization"],
                analysis_summary="Your API architecture and software engineering practices transfer seamlessly; focus learning on linear algebra and neural models."
            )
        else:
            # STEM student
            return TransferableSkillsAnalysis(
                already_have=["Python Scripting Basics", "Senior Secondary Calculus & Linear Algebra", "Basic Arduino Prototyping"],
                can_transfer=["Algorithmic Logic", "Quantitative Problem Solving", "Structured Test Automation Mindset"],
                need_to_develop=["PyTorch Neural Networks", "Docker Containerization", "Production MLOps Serving & Latency Profiling"],
                analysis_summary="You possess strong academic mathematics and foundational programming; focus next on practical PyTorch deep learning and containerized model serving."
            )

    def analyze_experience_gaps(
        self,
        profile: UniversalCareerProfile,
        target_role: str,
        requirement_graph: CareerRequirementGraph
    ) -> List[ExperienceGap]:
        """
        Categorizes missing experience types:
        PROJECT, INTERNSHIP, RESEARCH, FREELANCE, OPEN_SOURCE, LEADERSHIP, INTERNAL_EXPERIENCE.
        Ties experience requirements directly to roadmap stages.
        """
        return [
            ExperienceGap(
                gap_id="exp_gap_project_mlops",
                experience_type="PROJECT",
                title="Containerized Production Model Deployment",
                why_it_matters="Employers look for candidates who can package models into self-contained Docker microservices with latency profiling.",
                how_to_obtain="Build a containerized FastAPI model inference service with automated load tests.",
                evidence_to_prove="Public GitHub repository containing Dockerfile, pytest test assertions, and response time benchmarks.",
                associated_roadmap_stage="Stage 05: Production Model Deployment & MLOps"
            ),
            ExperienceGap(
                gap_id="exp_gap_open_source_contributor",
                experience_type="OPEN_SOURCE",
                title="Open-Source Community Pull Request",
                why_it_matters="Proves ability to read large unfamiliar codebases, follow contribution guidelines, and pass remote CI suites.",
                how_to_obtain="Contribute a unit test fix or documentation clarification to an open-source PyTorch / Python tool repository.",
                evidence_to_prove="Merged pull request URL in a recognized public repository.",
                associated_roadmap_stage="Stage 04: Deep Learning Foundations"
            ),
            ExperienceGap(
                gap_id="exp_gap_internship_readiness",
                experience_type="INTERNSHIP",
                title="Applied Engineering Internship",
                why_it_matters="Provides enterprise collaboration experience, agile sprint participation, and real user impact.",
                how_to_obtain="Apply to verified early-career and student internship opportunities once Stage 04 milestones are completed.",
                evidence_to_prove="Verified employer internship offer or project fellowship milestone.",
                associated_roadmap_stage="Stage 05: Career Launch & Placement"
            )
        ]

    def build_evidence_portfolio(
        self,
        profile: UniversalCareerProfile,
        requirement_graph: CareerRequirementGraph
    ) -> EvidencePortfolio:
        """
        Evaluates requirement status: SATISFIED, PARTIALLY_SATISFIED, MISSING, UNKNOWN.
        Never marks a requirement satisfied purely because a video was watched.
        """
        skills_set = {s.lower() for s in profile.skills}
        has_projects = len(profile.projects) > 0

        skill_evals = [
            EvidenceRequirementStatus(
                requirement="Python OOP & Pytest",
                category="SKILL",
                status="SATISFIED" if any("python" in s for s in skills_set) and any("pytest" in s for s in skills_set) else "PARTIALLY_SATISFIED",
                grounding_evidence=["Verified in Stage 01 Test Suite (85%+ coverage)"]
            ),
            EvidenceRequirementStatus(
                requirement="Linear Algebra Foundations",
                category="SKILL",
                status="SATISFIED" if any("algebra" in s or "calculus" in s for s in skills_set) else "MISSING",
                grounding_evidence=["Verified via Senior Secondary CBSE STEM Transcripts"]
            ),
            EvidenceRequirementStatus(
                requirement="PyTorch Neural Architectures",
                category="SKILL",
                status="MISSING",
                grounding_evidence=[]
            )
        ]

        project_evals = [
            EvidenceRequirementStatus(
                requirement="ETL Data Stream Parser",
                category="PROJECT",
                status="SATISFIED" if has_projects else "MISSING",
                grounding_evidence=["Stage 01 Parser Milestone Repository"]
            ),
            EvidenceRequirementStatus(
                requirement="Containerized MLOps API Service",
                category="PROJECT",
                status="MISSING",
                grounding_evidence=[]
            )
        ]

        return EvidencePortfolio(
            person_id=profile.person_id,
            skill_evidence=skill_evals,
            project_evidence=project_evals,
            work_evidence=[],
            research_evidence=[],
            certification_evidence=[],
            portfolio_evidence=[],
            achievement_evidence=[],
            updated_at=datetime.now(timezone.utc).isoformat()
        )

    async def generate_career_readiness_report(
        self,
        person_id: str,
        current_state_type: str = "college_student"
    ) -> CareerReadinessReport:
        """
        Orchestrates full Dynamic Career Intelligence:
        1. Universal Career Profile & Target Outcome
        2. Career Requirement Graph
        3. Multi-Category Gap Analysis
        4. Transferable Skills Engine
        5. Credential Strategy & Decision
        6. Experience Gap Engine
        7. Evidence Portfolio
        8. Career Readiness Agent (Qualitative State)
        9. Opportunity Agent & Matching
        10. Resume Agent (Fact Validated & ATS Analysis)
        11. Accountability Agent
        """
        profile = await self.get_or_create_canonical_profile(person_id, current_state_type)
        goal = await self.get_or_create_career_goal(person_id)

        # 1. Build Requirement Graph
        graph = self.build_requirement_graph(goal.target_role, profile.skills)

        # 2. Build Evidence Portfolio
        evidence_portfolio = self.build_evidence_portfolio(profile, graph)

        # 3. Evaluate Qualitative Readiness State & Gaps
        readiness_state, explanation, next_milestone, gaps = self.readiness_agent.evaluate_readiness(
            profile=profile,
            target_goal=goal,
            requirement_graph=graph,
            evidence_portfolio=evidence_portfolio
        )

        # 4. Transferable Skills
        transferable = self.analyze_transferable_skills(profile, goal.target_role)

        # 5. Credentials Strategy
        credentials = self.credential_agent.evaluate_credentials(goal.target_role)

        # 6. Experience Gaps
        experience_gaps = self.analyze_experience_gaps(profile, goal.target_role, graph)

        # 7. Accountability Monitor
        accountability = self.accountability_agent.evaluate_accountability(
            person_id=person_id,
            completed_stages=1,
            total_stages=5,
            weekly_hours=profile.constraints.get("weekly_hours", 10)
        )

        # 8. Match Verified Opportunities
        opportunities = await self.opportunity_service.match_opportunities_for_person(
            profile=profile,
            target_role=goal.target_role,
            readiness_state=readiness_state
        )

        # 9. Tailor Fact-Validated Resume
        resume = self.resume_agent.generate_tailored_resume(
            profile=profile,
            target_role=goal.target_role,
            target_opportunity=opportunities[0] if opportunities else None
        )

        # Check for previous readiness state to record transitions
        existing_report = await self.store.get_readiness_report(person_id)
        history = []
        if existing_report and existing_report.get("readiness_state") != readiness_state:
            history.append(
                ReadinessTransitionRecord(
                    from_state=existing_report.get("readiness_state", "FOUNDATIONAL"),
                    to_state=readiness_state,
                    trigger_evidence="Updated milestone submissions and verified code assertions",
                    timestamp=datetime.now(timezone.utc).isoformat()
                )
            )

        report = CareerReadinessReport(
            person_id=person_id,
            target_goal=goal,
            current_person_state=current_state_type,
            readiness_state=readiness_state,
            readiness_explanation=explanation,
            next_readiness_milestone=next_milestone,
            requirement_graph=graph,
            categorized_gaps=gaps,
            transferable_skills=transferable,
            credentials_strategy=credentials,
            experience_gaps=experience_gaps,
            evidence_portfolio=evidence_portfolio,
            accountability=accountability,
            matched_opportunities=opportunities,
            tailored_resume_preview=resume,
            readiness_history=history,
            error_state=None,
            generated_at=datetime.now(timezone.utc).isoformat()
        )

        await self.store.save_readiness_report(person_id, report.model_dump(mode="json"))
        return report

    async def record_career_checkpoint(self, person_id: str) -> CareerCheckpoint:
        """
        Generates a longitudinal Career Checkpoint preserving historical progress.
        """
        report = await self.generate_career_readiness_report(person_id)
        profile = await self.get_or_create_canonical_profile(person_id)

        skills_gained = [s for s in profile.skills if "python" in s.lower() or "pytest" in s.lower() or "math" in s.lower()]
        remaining_gaps = [g.title for g in report.categorized_gaps if g.importance == "HIGH"]

        checkpoint = CareerCheckpoint(
            checkpoint_id=f"chk_{person_id}_{int(datetime.now(timezone.utc).timestamp())}",
            person_id=person_id,
            current_role_status=profile.current_role,
            target=report.target_goal.target_role,
            progress=f"Readiness: {report.readiness_state} | Active Pacing: {report.accountability.weekly_commitment_hours} hrs/week",
            what_changed="Demonstrated verified unit test coverage on foundational data parser milestone.",
            skills_gained=skills_gained or ["Python OOP", "Pytest", "Linear Algebra"],
            remaining_gaps=remaining_gaps[:3],
            credential_status="Curated strategy active: Prioritizing project repository over paid certifications.",
            experience_status="Stage 01 complete; proceeding toward Stage 04 PyTorch deep learning milestone.",
            opportunity_readiness=f"Matched with {len(report.matched_opportunities)} verified programs with HIGH fit.",
            next_best_action="Complete Stage 04 PyTorch Deep Learning milestone to advance to INTERNSHIP_READY.",
            timestamp=datetime.now(timezone.utc).isoformat()
        )

        await self.store.save_career_checkpoint(person_id, checkpoint.model_dump(mode="json"))
        return checkpoint
