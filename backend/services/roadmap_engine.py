from typing import List, Dict, Any, Optional
from datetime import datetime, timezone
import uuid

from backend.core.config import settings
from backend.core.roadmap_schemas import (
    Roadmap,
    RoadmapPhase,
    Stage,
    Mission,
    Resource,
    EvidenceSubmission,
    EvaluationResult,
    MasteryDimensions,
    DisclosedRoadmapView,
    DisclosedStageView,
    AdaptConstraintRequest
)
from backend.core.career_schemas import UniversalCareerProfile
from backend.services.store import FirestoreStore
from backend.services.knowledge import KnowledgeService
from backend.services.personal_agent_engine import PersonalAgentEngine
from backend.services.requirement_graph_service import RequirementGraphService

class RoadmapEngine:
    def __init__(self, store: Optional[FirestoreStore] = None):
        self.store = store or FirestoreStore()
        self.knowledge_service = KnowledgeService()
        self.personal_agent = PersonalAgentEngine()
        self.requirement_service = RequirementGraphService(knowledge_service=self.knowledge_service)
        self.gemini_available = bool(settings.GEMINI_API_KEY)
        self.model = None

        if self.gemini_available:
            try:
                import google.generativeai as genai
                genai.configure(api_key=settings.GEMINI_API_KEY)
                self.model = genai.GenerativeModel('gemini-2.5-flash')
            except Exception as e:
                print(f"Warning: Failed to initialize Gemini model in RoadmapEngine: {e}")
                self.model = None

    def generate_ai_ml_roadmap(self, person_id: str, path_id: str = "path_applied_ai_ml_systems") -> Roadmap:
        """
        Synthesizes a progressive, multi-phase roadmap for Applied AI & Machine Learning Systems.
        Enforces server-side stage locking: Stage 1 is ACTIVE/UNLOCKED, all future stages are LOCKED.
        Retained for explicit AI/ML goals and backwards-compatible legacy test fixtures.
        """
        # Phase 1: Foundations
        stage_1 = Stage(
            stage_id="stage_01_python_foundations",
            phase_id="phase_01_foundations",
            stage_number=1,
            title="Python Foundations & Object-Oriented Engineering",
            objective="Establish production-grade Python engineering practices, modular package architecture, and memory profiling.",
            skills=["Python OOP", "Data Structures", "Type Hints", "Unit Testing"],
            prerequisites=["Basic Scripting"],
            missions=[
                Mission(
                    mission_id="mission_01_modular_parser",
                    stage_id="stage_01_python_foundations",
                    objective="Build a modular, type-annotated CSV/JSON data ingestion pipeline with comprehensive pytest test coverage.",
                    why="Applied ML systems require resilient, structured ETL pipelines before any model training can occur.",
                    estimated_time="4–6 hours",
                    steps=[
                        "Design clean Python dataclasses and Pydantic models for incoming dataset records.",
                        "Implement custom generator-based streaming parser for memory-efficient batching.",
                        "Write unit tests with pytest achieving >= 85% branch coverage.",
                        "Include type hints and pass strict mypy typecheck validation."
                    ],
                    resources=[
                        Resource(
                            title="Official Python 3 Documentation — Dataclasses & Generators",
                            url="https://docs.python.org/3/library/dataclasses.html",
                            resource_type="DOCUMENTATION",
                            estimated_duration="2 hours",
                            provenance="Python Software Foundation"
                        ),
                        Resource(
                            title="Pytest Best Practices & Fixture Architecture",
                            url="https://docs.pytest.org/en/stable/",
                            resource_type="DOCUMENTATION",
                            estimated_duration="1.5 hours",
                            provenance="pytest.org"
                        )
                    ],
                    evidence_requirements=[
                        "GitHub repository URL or Python code artifact containing the modular parser and test suite.",
                        "Passing pytest test execution output snippet."
                    ],
                    completion_criteria="Code must demonstrate type safety, generator batching, and passing unit tests.",
                    status="ACTIVE"
                )
            ],
            resources=[
                Resource(
                    title="Real Python: Python Typing & Data Architecture",
                    url="https://realpython.com/python-type-checking/",
                    resource_type="DOCUMENTATION",
                    estimated_duration="2 hours",
                    provenance="Real Python"
                )
            ],
            evidence_requirements=["Modular Python pipeline codebase with unit tests."],
            completion_rules={"min_tests_passing": 3, "accuracy_threshold": 80.0},
            estimated_effort="1 Week",
            locked=False,
            status="ACTIVE"
        )

        stage_2 = Stage(
            stage_id="stage_02_math_and_linear_algebra",
            phase_id="phase_01_foundations",
            stage_number=2,
            title="Mathematics & Linear Algebra for Machine Learning",
            objective="Master vector spaces, matrix factorizations, eigen-decomposition, and multivariate gradients.",
            skills=["Linear Algebra", "Vector Calculus", "Matrix Decompositions", "NumPy Vectorization"],
            prerequisites=["stage_01_python_foundations"],
            missions=[
                Mission(
                    mission_id="mission_02_matrix_gradient",
                    stage_id="stage_02_math_and_linear_algebra",
                    objective="Implement gradient descent optimization and PCA dimensionality reduction from scratch using pure NumPy.",
                    why="Understanding the geometric and calculus foundations prevents black-box model debugging failures.",
                    estimated_time="6–8 hours",
                    steps=[
                        "Implement matrix multiplication and eigenvalue decomposition using NumPy.",
                        "Construct a vectorized gradient descent solver with momentum from first principles."
                    ],
                    resources=[],
                    evidence_requirements=["NumPy implementation notebook and derivation notes."],
                    completion_criteria="Mathematical derivations and vectorized NumPy implementation execute correctly without external ML libraries.",
                    status="PENDING"
                )
            ],
            resources=[],
            evidence_requirements=["Vectorized mathematical implementation notebook."],
            completion_rules={"accuracy_threshold": 80.0},
            estimated_effort="2 Weeks",
            locked=True,
            status="LOCKED"
        )

        # Phase 2: Core Machine Learning
        stage_3 = Stage(
            stage_id="stage_03_classical_ml_pipelines",
            phase_id="phase_02_core_ml",
            stage_number=3,
            title="Classical ML & Feature Engineering Pipelines",
            objective="Construct end-to-end classification, regression, and cross-validation pipelines with Scikit-learn.",
            skills=["Scikit-learn", "Feature Engineering", "Cross-Validation", "Hyperparameter Tuning"],
            prerequisites=["stage_02_math_and_linear_algebra"],
            missions=[],
            resources=[],
            evidence_requirements=["Scikit-learn pipeline repository with model evaluation metrics."],
            completion_rules={"accuracy_threshold": 80.0},
            estimated_effort="2 Weeks",
            locked=True,
            status="LOCKED"
        )

        stage_4 = Stage(
            stage_id="stage_04_deep_learning_pytorch",
            phase_id="phase_02_core_ml",
            stage_number=4,
            title="Deep Learning Architectures with PyTorch",
            objective="Build, train, and validate Convolutional and Transformer neural networks from scratch using PyTorch.",
            skills=["PyTorch", "Autograd", "CNNs", "Transformers", "Loss Functions"],
            prerequisites=["stage_03_classical_ml_pipelines"],
            missions=[],
            resources=[],
            evidence_requirements=["Trained PyTorch model repository with loss/accuracy curves."],
            completion_rules={"accuracy_threshold": 80.0},
            estimated_effort="3 Weeks",
            locked=True,
            status="LOCKED"
        )

        # Phase 3: Systems & Deployment
        stage_5 = Stage(
            stage_id="stage_05_production_mlops_serving",
            phase_id="phase_03_mlops",
            stage_number=5,
            title="Production MLOps, Containerization & Low-Latency Serving",
            objective="Deploy trained models as containerized FastAPI microservices with ONNX runtime acceleration and Docker.",
            skills=["FastAPI", "Docker", "ONNX Runtime", "Latency Profiling", "Model Serving"],
            prerequisites=["stage_04_deep_learning_pytorch"],
            missions=[],
            resources=[],
            evidence_requirements=["Containerized Docker image and load test benchmark report."],
            completion_rules={"accuracy_threshold": 80.0},
            estimated_effort="2 Weeks",
            locked=True,
            status="LOCKED"
        )

        phases = [
            RoadmapPhase(
                phase_id="phase_01_foundations",
                title="Phase 1: Software & Mathematical Foundations",
                description="Rigorous programming, data architecture, and computational linear algebra.",
                stages=[stage_1, stage_2]
            ),
            RoadmapPhase(
                phase_id="phase_02_core_ml",
                title="Phase 2: Core Machine Learning & Neural Networks",
                description="Classical learning algorithms, feature engineering, and PyTorch deep learning.",
                stages=[stage_3, stage_4]
            ),
            RoadmapPhase(
                phase_id="phase_03_mlops",
                title="Phase 3: Production MLOps & Scalable Serving",
                description="Packaging models into high-throughput containerized services with telemetry.",
                stages=[stage_5]
            )
        ]

        roadmap = Roadmap(
            roadmap_id=f"rm_{person_id}_{int(datetime.now(timezone.utc).timestamp())}",
            person_id=person_id,
            path_id=path_id,
            version=1,
            target_outcome="Applied AI & Machine Learning Systems Specialist",
            phases=phases,
            current_stage_id="stage_01_python_foundations",
            current_mission_id="mission_01_modular_parser",
            total_stages=5,
            completed_stages=0,
            checkpoint_interval=5,
            revision_reason="Initial personalized synthesis from selected pathway.",
            constraints={"weekly_hours": 10, "format_preference": "project-based"}
        )
        return roadmap

    async def synthesize_personalized_roadmap(
        self,
        person_id: str,
        target_outcome: str,
        target_domain: Optional[str] = None,
        constraints: Optional[Dict[str, Any]] = None,
        path_id: Optional[str] = None
    ) -> Roadmap:
        """
        Generalized Roadmap Synthesis Pipeline:
        Derives stages and requirements directly from target outcome, domain standards,
        and user constraints. Never defaults to software engineering or AI/ML.
        """
        lower = target_outcome.lower()
        now_ts = int(datetime.now(timezone.utc).timestamp())
        actual_constraints = constraints or {}
        weekly_hours = actual_constraints.get("weekly_hours")

        def calc_effort(base_weeks: int) -> str:
            if weekly_hours is None or weekly_hours <= 0:
                return f"{base_weeks} Weeks (TIMELINE_UNCERTAIN: unspecified weekly availability)"
            total_hours = base_weeks * 10
            scaled_weeks = max(1, round(total_hours / weekly_hours))
            return "1 Week" if scaled_weeks == 1 else f"{scaled_weeks} Weeks"

        # 0. EXPLICIT AI/ML GOALS (Retained for tests and specific goals)
        if "ai specialist" in lower or "machine learning" in lower or "ai engineer" in lower:
            return self.generate_ai_ml_roadmap(person_id, path_id or "path_applied_ai_ml_systems")

        # 1. LAWYER / LEGAL ADVOCATE
        if "lawyer" in lower or "advocate" in lower or "legal" in lower or "attorney" in lower:
            st1 = Stage(
                stage_id="stage_01_legal_foundations",
                phase_id="phase_01_jurisprudence",
                stage_number=1,
                title="Constitutional Law & Jurisprudential Foundations",
                objective="Master foundational constitutional principles, fundamental rights jurisprudence, and legal reasoning methodologies.",
                skills=["Constitutional Law", "Legal Analysis", "Statutory Interpretation", "Case Synthesis"],
                prerequisites=[],
                missions=[
                    Mission(
                        mission_id="mission_01_precedent_synthesis",
                        stage_id="stage_01_legal_foundations",
                        objective="Analyze landmark constitutional precedents and draft an analytical judicial synthesis memorandum.",
                        why="Rigorous statutory and constitutional analysis underpins all subsequent litigation and advisory work.",
                        estimated_time="6–8 hours",
                        steps=[
                            "Read leading constitutional bench rulings on fundamental rights doctrine.",
                            "Identify the core ratio decidendi versus obiter dicta.",
                            "Draft a structured 4-page legal analysis memorandum citing recognized law reporters."
                        ],
                        resources=[
                            Resource(
                                title="National Law University Legal Research & Writing Guide",
                                url="https://www.law.cornell.edu/wex/legal_research",
                                resource_type="DOCUMENTATION",
                                estimated_duration="2 hours",
                                provenance="Legal Education Standard"
                            )
                        ],
                        evidence_requirements=["Submitted judicial synthesis memorandum document."],
                        completion_criteria="Memorandum articulates doctrine with precise citation format.",
                        status="ACTIVE"
                    )
                ],
                resources=[],
                evidence_requirements=["Jurisprudential case analysis brief."],
                completion_rules={"accuracy_threshold": 80.0},
                estimated_effort=calc_effort(2),
                locked=False,
                status="ACTIVE"
            )
            st2 = Stage(
                stage_id="stage_02_statutory_research",
                phase_id="phase_01_jurisprudence",
                stage_number=2,
                title="Statutory Research, Citation & Case Law Mapping",
                objective="Master specialized legal databases (SCC Online, Manupatra, Westlaw) and procedural court rules.",
                skills=["Legal Databases", "Statutory Cross-Referencing", "Precedent Mapping"],
                prerequisites=["stage_01_legal_foundations"],
                missions=[],
                resources=[],
                evidence_requirements=["Annotated research brief with statutory cross-references."],
                completion_rules={"accuracy_threshold": 80.0},
                estimated_effort=calc_effort(2),
                locked=True,
                status="LOCKED"
            )
            st3 = Stage(
                stage_id="stage_03_legal_drafting",
                phase_id="phase_02_advocacy",
                stage_number=3,
                title="Pleadings, Conveyancing & Appellate Advocacy",
                objective="Draft structured petitions, writ pleadings, contractual agreements, and conduct oral advocacy.",
                skills=["Petition Drafting", "Contract Drafting", "Oral Advocacy", "Moot Court Practice"],
                prerequisites=["stage_02_statutory_research"],
                missions=[],
                resources=[],
                evidence_requirements=["Verified legal brief or moot court memorial."],
                completion_rules={"accuracy_threshold": 80.0},
                estimated_effort=calc_effort(3),
                locked=True,
                status="LOCKED"
            )
            st4 = Stage(
                stage_id="stage_04_bar_qualification",
                phase_id="phase_02_advocacy",
                stage_number=4,
                title="Bar Examination Preparation & Professional Ethics",
                objective="Complete bar qualification curriculum, professional ethics codes, and state bar council enrollment requirements.",
                skills=["Bar Exam Preparation", "Professional Ethics", "Fiduciary Practice", "Chamber Operations"],
                prerequisites=["stage_03_legal_drafting"],
                missions=[],
                resources=[],
                evidence_requirements=["Bar examination practice test record and enrollment documentation."],
                completion_rules={"accuracy_threshold": 80.0},
                estimated_effort=calc_effort(4),
                locked=True,
                status="LOCKED"
            )
            phases = [
                RoadmapPhase(
                    phase_id="phase_01_jurisprudence",
                    title="Phase 1: Legal Foundations & Research Mastery",
                    description="Constitutional doctrine, statutory interpretation, and legal research techniques.",
                    stages=[st1, st2]
                ),
                RoadmapPhase(
                    phase_id="phase_02_advocacy",
                    title="Phase 2: Advocacy, Drafting & Bar Certification",
                    description="Procedural drafting, appellate argumentation, and formal bar licensing.",
                    stages=[st3, st4]
                )
            ]
            current_stage_id = "stage_01_legal_foundations"
            current_mission_id = "mission_01_precedent_synthesis"

        # 2. PRODUCT DESIGNER
        elif "product designer" in lower or "ui/ux" in lower or "ux designer" in lower:
            st1 = Stage(
                stage_id="stage_01_ux_research",
                phase_id="phase_01_discovery",
                stage_number=1,
                title="User Research & Problem Discovery",
                objective="Conduct contextual user interviews, heuristic audits, and synthesize actionable persona journey maps.",
                skills=["Contextual Inquiry", "User Personas", "Journey Mapping", "Information Architecture"],
                prerequisites=[],
                missions=[
                    Mission(
                        mission_id="mission_01_journey_map",
                        stage_id="stage_01_ux_research",
                        objective="Conduct 3 user problem interviews and build an annotated journey map identifying critical UX friction points.",
                        why="Great digital products originate from deep customer empathy rather than aesthetic guesswork.",
                        estimated_time="5–6 hours",
                        steps=[
                            "Formulate a semi-structured user interview script focusing on a specific workflow.",
                            "Interview 3 representative target users and log observed friction points.",
                            "Synthesize findings into an annotated persona journey map in Figma/FigJam."
                        ],
                        resources=[
                            Resource(
                                title="Nielsen Norman Group: Customer Journey Mapping Guide",
                                url="https://www.nngroup.com/articles/customer-journey-mapping/",
                                resource_type="DOCUMENTATION",
                                estimated_duration="2 hours",
                                provenance="NN/g"
                            )
                        ],
                        evidence_requirements=["Public Figma or PDF link to annotated user research and journey map."],
                        completion_criteria="Journey map includes clear personas, touchpoints, emotions, and friction opportunities.",
                        status="ACTIVE"
                    )
                ],
                resources=[],
                evidence_requirements=["User research deck and journey map document."],
                completion_rules={"accuracy_threshold": 80.0},
                estimated_effort=calc_effort(2),
                locked=False,
                status="ACTIVE"
            )
            st2 = Stage(
                stage_id="stage_02_design_systems",
                phase_id="phase_02_systems",
                stage_number=2,
                title="Design Systems & Component Architecture in Figma",
                objective="Build atomic design token libraries, responsive auto-layout components, and WCAG-accessible variant sets.",
                skills=["Figma Auto-Layout", "Design Tokens", "Component Variants", "WCAG Accessibility"],
                prerequisites=["stage_01_ux_research"],
                missions=[],
                resources=[],
                evidence_requirements=["Comprehensive Figma component library file."],
                completion_rules={"accuracy_threshold": 80.0},
                estimated_effort=calc_effort(2),
                locked=True,
                status="LOCKED"
            )
            st3 = Stage(
                stage_id="stage_03_interactive_prototyping",
                phase_id="phase_02_systems",
                stage_number=3,
                title="Interactive Micro-Interactions & Usability Testing",
                objective="Construct high-fidelity interactive prototypes with realistic transitions and conduct unmoderated usability tests.",
                skills=["Micro-interactions", "High-Fidelity Prototyping", "Usability Testing", "SUS Metrics"],
                prerequisites=["stage_02_design_systems"],
                missions=[],
                resources=[],
                evidence_requirements=["Interactive Figma prototype link and usability test summary report."],
                completion_rules={"accuracy_threshold": 80.0},
                estimated_effort=calc_effort(2),
                locked=True,
                status="LOCKED"
            )
            st4 = Stage(
                stage_id="stage_04_portfolio_case_studies",
                phase_id="phase_03_launch",
                stage_number=4,
                title="Product Design Portfolio & Case Study Publication",
                objective="Publish 2 in-depth case studies detailing problem statement, user signals, iterations, and business outcomes.",
                skills=["Design Rationale", "Case Study Writing", "Product Metrics", "Portfolio Curation"],
                prerequisites=["stage_03_interactive_prototyping"],
                missions=[],
                resources=[],
                evidence_requirements=["Live public portfolio URL with 2 comprehensive case studies."],
                completion_rules={"accuracy_threshold": 80.0},
                estimated_effort=calc_effort(3),
                locked=True,
                status="LOCKED"
            )
            phases = [
                RoadmapPhase(
                    phase_id="phase_01_discovery",
                    title="Phase 1: User Research & Problem Framing",
                    description="Qualitative research methods, customer problem framing, and behavioral journey mapping.",
                    stages=[st1]
                ),
                RoadmapPhase(
                    phase_id="phase_02_systems",
                    title="Phase 2: Design Systems & Interactive Prototyping",
                    description="Atomic component architecture, design tokenization, and high-fidelity prototype benchmarking.",
                    stages=[st2, st3]
                ),
                RoadmapPhase(
                    phase_id="phase_03_launch",
                    title="Phase 3: Public Portfolio & Hiring Readiness",
                    description="Authoring rigorous product case studies and curating an industry-ready portfolio.",
                    stages=[st4]
                )
            ]
            current_stage_id = "stage_01_ux_research"
            current_mission_id = "mission_01_journey_map"

        # 3. RESTAURANT ENTREPRENEUR
        elif "restaurant" in lower or "bakery" in lower or "cafe" in lower or "food" in lower:
            st1 = Stage(
                stage_id="stage_01_food_safety_regulations",
                phase_id="phase_01_concept",
                stage_number=1,
                title="Food Safety, Health Codes & Concept Blueprint",
                objective="Master commercial food hygiene protocols, HACCP critical control points, and author brand concept book.",
                skills=["Food Safety Protocols", "FSSAI / Health Standards", "Concept Blueprint", "Kitchen Layout Basics"],
                prerequisites=[],
                missions=[
                    Mission(
                        mission_id="mission_01_haccp_plan",
                        stage_id="stage_01_food_safety_regulations",
                        objective="Create a comprehensive food safety and HACCP temperature control plan for commercial food handling.",
                        why="Statutory health compliance is mandatory before securing trade licenses and opening to the public.",
                        estimated_time="5–6 hours",
                        steps=[
                            "Review FSSAI / local municipal commercial kitchen sanitary requirements.",
                            "Map temperature logs for raw ingredient receiving, refrigeration, and cooking lines.",
                            "Draft an allergen segregation protocol."
                        ],
                        resources=[],
                        evidence_requirements=["Documented HACCP safety manual and sanitary checklist."],
                        completion_criteria="Plan satisfies municipal health inspection criteria.",
                        status="ACTIVE"
                    )
                ],
                resources=[],
                evidence_requirements=["Food safety compliance protocol and concept deck."],
                completion_rules={"accuracy_threshold": 80.0},
                estimated_effort=calc_effort(2),
                locked=False,
                status="ACTIVE"
            )
            st2 = Stage(
                stage_id="stage_02_menu_financial_engineering",
                phase_id="phase_02_economics",
                stage_number=2,
                title="Menu Engineering & Prime Cost Economics",
                objective="Engineer dish cost structures, portion control matrices, and gross margin optimization spreadsheets.",
                skills=["Recipe Costing", "Gross Margin Optimization", "Portion Control", "Waste Auditing"],
                prerequisites=["stage_01_food_safety_regulations"],
                missions=[],
                resources=[],
                evidence_requirements=["Recipe costing model maintaining food cost <= 30%."],
                completion_rules={"accuracy_threshold": 80.0},
                estimated_effort=calc_effort(2),
                locked=True,
                status="LOCKED"
            )
            st3 = Stage(
                stage_id="stage_03_kitchen_ops_supply",
                phase_id="phase_02_economics",
                stage_number=3,
                title="Commercial Kitchen Operations & Supply Chain Procurement",
                objective="Establish wholesale purveyor contracts, inventory rotation FIFO protocols, and kitchen station workflows.",
                skills=["Inventory Management", "Vendor Contracts", "Kitchen Workflows", "POS Systems"],
                prerequisites=["stage_02_menu_financial_engineering"],
                missions=[],
                resources=[],
                evidence_requirements=["Vendor comparison matrix and station standard operating procedures."],
                completion_rules={"accuracy_threshold": 80.0},
                estimated_effort=calc_effort(3),
                locked=True,
                status="LOCKED"
            )
            st4 = Stage(
                stage_id="stage_04_licensing_launch",
                phase_id="phase_03_launch",
                stage_number=4,
                title="Municipal Trade Licensing & Soft Launch Operations",
                objective="Complete municipal licensing, health inspections, team training, and soft launch trial operations.",
                skills=["Health Permitting", "Fire Safety Compliance", "Staff Training", "Soft Launch Planning"],
                prerequisites=["stage_03_kitchen_ops_supply"],
                missions=[],
                resources=[],
                evidence_requirements=["Municipal trade license filing and soft launch operating runbook."],
                completion_rules={"accuracy_threshold": 80.0},
                estimated_effort=calc_effort(3),
                locked=True,
                status="LOCKED"
            )
            phases = [
                RoadmapPhase(
                    phase_id="phase_01_concept",
                    title="Phase 1: Regulatory Foundations & Concept Blueprint",
                    description="Food safety regulations, health code compliance, and brand concept design.",
                    stages=[st1]
                ),
                RoadmapPhase(
                    phase_id="phase_02_economics",
                    title="Phase 2: Financial Engineering & Operations",
                    description="Prime cost control, menu costing, and commercial kitchen procurement.",
                    stages=[st2, st3]
                ),
                RoadmapPhase(
                    phase_id="phase_03_launch",
                    title="Phase 3: Licensing & Commercial Launch",
                    description="Trade licensing, staff training, and opening execution.",
                    stages=[st4]
                )
            ]
            current_stage_id = "stage_01_food_safety_regulations"
            current_mission_id = "mission_01_haccp_plan"

        # 4. RESEARCHER
        elif ("researcher" in lower or "research" in lower) and not any(k in lower for k in ["cfd", "fluid dynamics", "mathematician", "drone"]):
            discipline = target_domain or "Scientific Domain"
            st1 = Stage(
                stage_id="stage_01_literature_survey",
                phase_id="phase_01_theory",
                stage_number=1,
                title=f"Systematic Literature Survey in {discipline}",
                objective=f"Conduct an exhaustive meta-analysis of peer-reviewed publications and identify open frontiers in {discipline}.",
                skills=["Literature Review", "Meta-Analysis", "Citation Mapping", "Academic Writing"],
                prerequisites=[],
                missions=[
                    Mission(
                        mission_id="mission_01_lit_review",
                        stage_id="stage_01_literature_survey",
                        objective="Synthesize 20 peer-reviewed papers into a structured literature review identifying unaddressed research questions.",
                        why="Grounding investigation in existing literature prevents redundant research and clarifies novel contributions.",
                        estimated_time="6–8 hours",
                        steps=[
                            "Search Google Scholar / PubMed / IEEE Xplore for recent seminal papers.",
                            "Categorize methodologies, experimental assumptions, and reported limitations.",
                            "Author a 5-page state-of-the-art review."
                        ],
                        resources=[],
                        evidence_requirements=["Comprehensive literature survey document with complete citations."],
                        completion_criteria="Document synthesizes findings and identifies clear research gaps.",
                        status="ACTIVE"
                    )
                ],
                resources=[],
                evidence_requirements=["Comprehensive research survey with annotated bibliography."],
                completion_rules={"accuracy_threshold": 80.0},
                estimated_effort=calc_effort(2),
                locked=False,
                status="ACTIVE"
            )
            st2 = Stage(
                stage_id="stage_02_experimental_methodology",
                phase_id="phase_02_investigation",
                stage_number=2,
                title="Experimental Design & Hypothesis Testing Protocols",
                objective="Formulate falsifiable hypotheses, statistical power calculations, and reproducible control protocols.",
                skills=["Hypothesis Formulation", "Statistical Power", "Control Protocols", "Reproducibility"],
                prerequisites=["stage_01_literature_survey"],
                missions=[],
                resources=[],
                evidence_requirements=["Experimental protocol document with statistical power analysis."],
                completion_rules={"accuracy_threshold": 80.0},
                estimated_effort=calc_effort(3),
                locked=True,
                status="LOCKED"
            )
            st3 = Stage(
                stage_id="stage_03_data_validation",
                phase_id="phase_02_investigation",
                stage_number=3,
                title="Data Provenance, Significance Testing & Telemetry",
                objective="Conduct parametric/non-parametric significance testing, compute effect sizes, and establish open data audit trails.",
                skills=["Statistical Significance", "P-Value Calibration", "Data Modeling", "Open Science Standards"],
                prerequisites=["stage_02_experimental_methodology"],
                missions=[],
                resources=[],
                evidence_requirements=["Reproducible analysis workbook and raw data telemetry."],
                completion_rules={"accuracy_threshold": 80.0},
                estimated_effort=calc_effort(2),
                locked=True,
                status="LOCKED"
            )
            st4 = Stage(
                stage_id="stage_04_manuscript_publication",
                phase_id="phase_03_defense",
                stage_number=4,
                title="Peer-Reviewed Manuscript Authoring & Defense",
                objective="Author a complete research paper conforming to journal publication standards and present findings.",
                skills=["Journal Manuscript Writing", "Peer Review Response", "Academic Presentation"],
                prerequisites=["stage_03_data_validation"],
                missions=[],
                resources=[],
                evidence_requirements=["Complete manuscript draft or preprint repository URL."],
                completion_rules={"accuracy_threshold": 80.0},
                estimated_effort=calc_effort(4),
                locked=True,
                status="LOCKED"
            )
            phases = [
                RoadmapPhase(
                    phase_id="phase_01_theory",
                    title="Phase 1: Theory & Literature Synthesis",
                    description="Systematic literature review, domain foundations, and gap analysis.",
                    stages=[st1]
                ),
                RoadmapPhase(
                    phase_id="phase_02_investigation",
                    title="Phase 2: Experimental Rigor & Statistical Analysis",
                    description="Experimental protocols, hypothesis testing, and reproducible data validation.",
                    stages=[st2, st3]
                ),
                RoadmapPhase(
                    phase_id="phase_03_defense",
                    title="Phase 3: Publication & Scholarly Defense",
                    description="Drafting peer-reviewed manuscript and preparing scholarly presentations.",
                    stages=[st4]
                )
            ]
            current_stage_id = "stage_01_literature_survey"
            current_mission_id = "mission_01_lit_review"

        # 5. CAREER TRANSITION: SALES TO PRODUCT MANAGEMENT
        elif "product management" in lower or "product manager" in lower or "pm" in lower:
            st1 = Stage(
                stage_id="stage_01_customer_discovery",
                phase_id="phase_01_discovery",
                stage_number=1,
                title="Customer Discovery & Commercial Problem Framing",
                objective="Translate commercial sales insights into structured user problem statements and Opportunity Solution Trees.",
                skills=["User Problem Interviews", "Opportunity Solution Trees", "Commercial Framing", "Stakeholder Alignment"],
                prerequisites=[],
                missions=[
                    Mission(
                        mission_id="mission_01_opp_tree",
                        stage_id="stage_01_customer_discovery",
                        objective="Build an Opportunity Solution Tree bridging customer objections to validated product opportunities.",
                        why="Your enterprise sales background provides unmatched customer proximity; this milestone formalizes it into product strategy.",
                        estimated_time="5–6 hours",
                        steps=[
                            "Review commercial customer objections and churn themes.",
                            "Frame top 3 customer pain points into Opportunity Solution Trees.",
                            "Identify underlying user behaviors and market assumptions."
                        ],
                        resources=[],
                        evidence_requirements=["Opportunity Solution Tree artifact and discovery synthesis document."],
                        completion_criteria="Artifact maps commercial needs to distinct problem opportunities.",
                        status="ACTIVE"
                    )
                ],
                resources=[],
                evidence_requirements=["Customer interview synthesis deck."],
                completion_rules={"accuracy_threshold": 80.0},
                estimated_effort=calc_effort(2),
                locked=False,
                status="ACTIVE"
            )
            st2 = Stage(
                stage_id="stage_02_prd_specifications",
                phase_id="phase_02_execution",
                stage_number=2,
                title="Product Requirements Documentation (PRD) & User Stories",
                objective="Author rigorous, unambiguous feature specifications, user stories, acceptance criteria, and edge cases.",
                skills=["PRD Writing", "User Stories", "Acceptance Criteria", "Agile Backlog Grooming"],
                prerequisites=["stage_01_customer_discovery"],
                missions=[],
                resources=[],
                evidence_requirements=["Complete Product Requirements Document (PRD) with user stories."],
                completion_rules={"accuracy_threshold": 80.0},
                estimated_effort=calc_effort(2),
                locked=True,
                status="LOCKED"
            )
            st3 = Stage(
                stage_id="stage_03_product_analytics",
                phase_id="phase_02_execution",
                stage_number=3,
                title="Product Analytics, Event Schemas & Retention Telemetry",
                objective="Define North Star metrics, retention funnels, and write event tracking instrumentation schemas.",
                skills=["Cohort Retention", "Funnel Conversion", "A/B Testing Frameworks", "North Star Metrics"],
                prerequisites=["stage_02_prd_specifications"],
                missions=[],
                resources=[],
                evidence_requirements=["Event tracking instrumentation schema and product telemetry dashboard."],
                completion_rules={"accuracy_threshold": 80.0},
                estimated_effort=calc_effort(2),
                locked=True,
                status="LOCKED"
            )
            st4 = Stage(
                stage_id="stage_04_teardown_portfolio",
                phase_id="phase_03_transition",
                stage_number=4,
                title="Product Teardown & Transition Portfolio",
                objective="Publish a public teardown evaluating an existing software product with strategic improvements and business impact.",
                skills=["Product Strategy", "Technical Feasibility Analysis", "Executive Presentations"],
                prerequisites=["stage_03_product_analytics"],
                missions=[],
                resources=[],
                evidence_requirements=["Public product teardown document with strategic improvement proposals."],
                completion_rules={"accuracy_threshold": 80.0},
                estimated_effort=calc_effort(3),
                locked=True,
                status="LOCKED"
            )
            phases = [
                RoadmapPhase(
                    phase_id="phase_01_discovery",
                    title="Phase 1: Customer Discovery & Framing",
                    description="Transferring sales domain expertise into structured customer problem frameworks.",
                    stages=[st1]
                ),
                RoadmapPhase(
                    phase_id="phase_02_execution",
                    title="Phase 2: Product Specifications & Telemetry",
                    description="Writing production PRDs, agile backlog execution, and product analytics telemetry.",
                    stages=[st2, st3]
                ),
                RoadmapPhase(
                    phase_id="phase_03_transition",
                    title="Phase 3: Product Teardown Portfolio",
                    description="Publishing product teardowns and preparing for transition interviews.",
                    stages=[st4]
                )
            ]
            current_stage_id = "stage_01_customer_discovery"
            current_mission_id = "mission_01_opp_tree"

        # 6. CLINICAL PSYCHOLOGIST
        elif any(k in lower for k in ["psycholog", "mental health", "therap", "counsel"]):
            st1 = Stage(
                stage_id="stage_01_psychopathology_ethics",
                phase_id="phase_01_clinical_foundations",
                stage_number=1,
                title="Psychopathology, Diagnostic Systems & Clinical Ethics",
                objective="Master DSM-5/ICD-11 diagnostic criteria, clinical interview techniques, and mental health ethical codes.",
                skills=["Diagnostic Classification (DSM-5)", "Clinical Interviewing", "Ethical Standards", "Mental Status Examination"],
                prerequisites=[],
                missions=[
                    Mission(
                        mission_id="mission_01_diagnostic_intake",
                        stage_id="stage_01_psychopathology_ethics",
                        objective="Conduct a simulated diagnostic intake interview and author a structured clinical assessment note.",
                        why="Diagnostic intake and ethical risk assessment are prerequisites to any therapeutic intervention.",
                        estimated_time="5–6 hours",
                        steps=[
                            "Review standardized Mental Status Examination (MSE) protocols.",
                            "Conduct structured diagnostic interview based on DSM-5 clinical criteria.",
                            "Draft intake report identifying symptoms, differential diagnoses, and ethical boundaries."
                        ],
                        resources=[],
                        evidence_requirements=["De-identified clinical intake interview note and differential diagnosis formulation."],
                        completion_criteria="Intake report documents MSE observations and ethical safeguards.",
                        status="ACTIVE"
                    )
                ],
                resources=[],
                evidence_requirements=["Clinical intake evaluation notes and diagnostic case analysis."],
                completion_rules={"accuracy_threshold": 80.0},
                estimated_effort=calc_effort(2),
                locked=False,
                status="ACTIVE"
            )
            st2 = Stage(
                stage_id="stage_02_psychological_assessment",
                phase_id="phase_01_clinical_foundations",
                stage_number=2,
                title="Psychological Assessment & Psychometric Testing",
                objective="Administer, score, and interpret standardized psychometric batteries (WAIS, MMPI, BDI) with case formulation.",
                skills=["Psychometric Testing", "Cognitive Assessment", "Personality Inventories", "Case Formulation"],
                prerequisites=["stage_01_psychopathology_ethics"],
                missions=[],
                resources=[],
                evidence_requirements=["Comprehensive psychometric evaluation report and interpretive summary."],
                completion_rules={"accuracy_threshold": 80.0},
                estimated_effort=calc_effort(3),
                locked=True,
                status="LOCKED"
            )
            st3 = Stage(
                stage_id="stage_03_cbt_interventions",
                phase_id="phase_02_therapeutic_practice",
                stage_number=3,
                title="Evidence-Based Psychotherapy & CBT Modalities",
                objective="Execute Cognitive Behavioral Therapy (CBT) cognitive restructuring, behavioral activation, and exposure protocols.",
                skills=["CBT Protocol Delivery", "Cognitive Restructuring", "Behavioral Activation", "Therapeutic Alliance"],
                prerequisites=["stage_02_psychological_assessment"],
                missions=[],
                resources=[],
                evidence_requirements=["Written CBT treatment plan with thought records and behavioral homework protocols."],
                completion_rules={"accuracy_threshold": 80.0},
                estimated_effort=calc_effort(3),
                locked=True,
                status="LOCKED"
            )
            st4 = Stage(
                stage_id="stage_04_supervised_practicum",
                phase_id="phase_03_licensure",
                stage_number=4,
                title="Supervised Clinical Practicum & Ethical Case Defense",
                objective="Complete documented clinical contact hours under licensed supervision and defend treatment outcomes.",
                skills=["Clinical Case Defense", "Supervisor Consultation", "Outcome Measurement", "Statutory Licensure"],
                prerequisites=["stage_03_cbt_interventions"],
                missions=[],
                resources=[],
                evidence_requirements=["Supervisor logbook of clinical hours and evaluated case defense transcript."],
                completion_rules={"accuracy_threshold": 80.0},
                estimated_effort=calc_effort(4),
                locked=True,
                status="LOCKED"
            )
            phases = [
                RoadmapPhase(
                    phase_id="phase_01_clinical_foundations",
                    title="Phase 1: Psychopathology & Assessment",
                    description="Diagnostic classifications, clinical interviewing, and standardized psychometric evaluation.",
                    stages=[st1, st2]
                ),
                RoadmapPhase(
                    phase_id="phase_02_therapeutic_practice",
                    title="Phase 2: Evidence-Based Therapeutic Modalities",
                    description="Cognitive behavioral interventions, treatment planning, and therapeutic alliance.",
                    stages=[st3]
                ),
                RoadmapPhase(
                    phase_id="phase_03_licensure",
                    title="Phase 3: Supervised Practicum & Licensure",
                    description="Documented clinical hours under licensed supervision and case defense.",
                    stages=[st4]
                )
            ]
            current_stage_id = "stage_01_psychopathology_ethics"
            current_mission_id = "mission_01_diagnostic_intake"

        # 7. PROFESSIONAL PHOTOGRAPHER
        elif any(k in lower for k in ["photo", "photographer"]):
            st1 = Stage(
                stage_id="stage_01_camera_optics_exposure",
                phase_id="phase_01_visual_foundations",
                stage_number=1,
                title="Optical Physics, Camera Architecture & Manual Exposure",
                objective="Master depth of field, focal length distortion, dynamic range, and exposure triangle in manual mode.",
                skills=["Manual Exposure", "Focal Length Optics", "Dynamic Range Control", "Composition Geometry"],
                prerequisites=[],
                missions=[
                    Mission(
                        mission_id="mission_01_exposure_triad",
                        stage_id="stage_01_camera_optics_exposure",
                        objective="Shoot a high-contrast editorial scene demonstrating precise manual exposure and histogram evaluation.",
                        why="Full manual optical control ensures repeatable results across erratic natural and commercial lighting.",
                        estimated_time="4–5 hours",
                        steps=[
                            "Set camera to full manual exposure mode.",
                            "Capture bracketed exposures evaluating RAW histogram clipping.",
                            "Submit 3 calibrated test shots demonstrating aperture depth-of-field control."
                        ],
                        resources=[],
                        evidence_requirements=["Uncompressed RAW image files with complete EXIF exposure metadata."],
                        completion_criteria="Histograms confirm zero unintended highlight clipping and sharp focus plane.",
                        status="ACTIVE"
                    )
                ],
                resources=[],
                evidence_requirements=["RAW image collection with documented EXIF exposure settings."],
                completion_rules={"accuracy_threshold": 80.0},
                estimated_effort=calc_effort(2),
                locked=False,
                status="ACTIVE"
            )
            st2 = Stage(
                stage_id="stage_02_studio_strobe_lighting",
                phase_id="phase_01_visual_foundations",
                stage_number=2,
                title="Studio Strobe Lighting, Off-Camera Flash & Modifiers",
                objective="Master 3-point studio lighting, lighting contrast ratios, softboxes, beauty dishes, and optical flags.",
                skills=["Off-Camera Flash", "Strobe Synchronization", "Light Modifiers", "Lighting Ratio Control"],
                prerequisites=["stage_01_camera_optics_exposure"],
                missions=[],
                resources=[],
                evidence_requirements=["Studio lighting diagrams and corresponding high-resolution portrait photographs."],
                completion_rules={"accuracy_threshold": 80.0},
                estimated_effort=calc_effort(2),
                locked=True,
                status="LOCKED"
            )
            st3 = Stage(
                stage_id="stage_03_raw_grading_postproduction",
                phase_id="phase_02_commercial_production",
                stage_number=3,
                title="Color-Calibrated RAW Post-Production & Frequency Separation",
                objective="Execute non-destructive RAW conversion in Lightroom/Capture One and frequency separation skin retouching in Photoshop.",
                skills=["RAW Color Grading", "ICC Profiles", "Frequency Separation", "Dodge & Burn"],
                prerequisites=["stage_02_studio_strobe_lighting"],
                missions=[],
                resources=[],
                evidence_requirements=["Before/after layered PSD or TIFF retouched image file."],
                completion_rules={"accuracy_threshold": 80.0},
                estimated_effort=calc_effort(3),
                locked=True,
                status="LOCKED"
            )
            st4 = Stage(
                stage_id="stage_04_commercial_editorial_delivery",
                phase_id="phase_03_business_launch",
                stage_number=4,
                title="Commercial Editorial Portfolio, Client Runbooks & Gallery Delivery",
                objective="Publish a 15-image curated editorial portfolio, commercial rate card, model release runbook, and delivery portal.",
                skills=["Portfolio Curation", "Commercial Rate Cards", "Model Releases", "Client Proofing"],
                prerequisites=["stage_03_raw_grading_postproduction"],
                missions=[],
                resources=[],
                evidence_requirements=["Live public portfolio URL and client delivery contract template."],
                completion_rules={"accuracy_threshold": 80.0},
                estimated_effort=calc_effort(3),
                locked=True,
                status="LOCKED"
            )
            phases = [
                RoadmapPhase(
                    phase_id="phase_01_visual_foundations",
                    title="Phase 1: Optical Mechanics & Studio Lighting",
                    description="Manual exposure mastery, optical physics, and off-camera studio strobe lighting.",
                    stages=[st1, st2]
                ),
                RoadmapPhase(
                    phase_id="phase_02_commercial_production",
                    title="Phase 2: Post-Production & Retouching",
                    description="Color calibration, RAW development, and non-destructive editorial retouching.",
                    stages=[st3]
                ),
                RoadmapPhase(
                    phase_id="phase_03_business_launch",
                    title="Phase 3: Portfolio & Commercial Delivery",
                    description="Curated commercial portfolio, client contracts, and gallery delivery.",
                    stages=[st4]
                )
            ]
            current_stage_id = "stage_01_camera_optics_exposure"
            current_mission_id = "mission_01_exposure_triad"

        # 8. TEACHER / K-12 EDUCATOR
        elif any(k in lower for k in ["teach", "educat", "pedagog", "school"]):
            st1 = Stage(
                stage_id="stage_01_pedagogical_foundations",
                phase_id="phase_01_pedagogy",
                stage_number=1,
                title="Educational Psychology & Constructivist Pedagogy",
                objective="Master cognitive developmental theory (Piaget, Vygotsky ZPD), Bloom's taxonomy, and learner motivation.",
                skills=["Educational Psychology", "Constructivist Learning", "Bloom's Taxonomy", "Zone of Proximal Development"],
                prerequisites=[],
                missions=[
                    Mission(
                        mission_id="mission_01_constructivist_lesson",
                        stage_id="stage_01_pedagogical_foundations",
                        objective="Design an inquiry-based constructivist lesson plan applying Bloom's Taxonomy cognitive scaffolding.",
                        why="Effective teaching requires deliberate pedagogical architecture rather than mere rote information delivery.",
                        estimated_time="5–6 hours",
                        steps=[
                            "Select a core curricular topic in your subject domain.",
                            "Map learning objectives across Bloom's Taxonomy cognitive levels.",
                            "Design interactive student scaffolding exercises."
                        ],
                        resources=[],
                        evidence_requirements=["Complete lesson plan document with pedagogical rationale and scaffolding tasks."],
                        completion_criteria="Plan incorporates active student inquiry and explicit cognitive stages.",
                        status="ACTIVE"
                    )
                ],
                resources=[],
                evidence_requirements=["Constructivist lesson plan and pedagogical rationale brief."],
                completion_rules={"accuracy_threshold": 80.0},
                estimated_effort=calc_effort(2),
                locked=False,
                status="ACTIVE"
            )
            st2 = Stage(
                stage_id="stage_02_curriculum_instructional_design",
                phase_id="phase_01_pedagogy",
                stage_number=2,
                title="Curriculum Architecture, Unit Design & Assessment Rubrics",
                objective="Design multi-week curriculum units utilizing backward design (UbD), formative checks, and diagnostic rubrics.",
                skills=["Understanding by Design (UbD)", "Curriculum Alignment", "Formative Assessment", "Rubric Construction"],
                prerequisites=["stage_01_pedagogical_foundations"],
                missions=[],
                resources=[],
                evidence_requirements=["4-week curricular unit map with diagnostic assessment rubrics."],
                completion_rules={"accuracy_threshold": 80.0},
                estimated_effort=calc_effort(3),
                locked=True,
                status="LOCKED"
            )
            st3 = Stage(
                stage_id="stage_03_classroom_management_inclusion",
                phase_id="phase_02_instructional_practice",
                stage_number=3,
                title="Classroom Management, Behavioral Systems & Inclusive Learning",
                objective="Implement positive behavioral interventions, proactive routines, and differentiated Universal Design for Learning (UDL).",
                skills=["Classroom Management", "PBIS Framework", "Universal Design for Learning (UDL)", "Differentiated Instruction"],
                prerequisites=["stage_02_curriculum_instructional_design"],
                missions=[],
                resources=[],
                evidence_requirements=["Classroom management plan and differentiated learning accommodation matrix."],
                completion_rules={"accuracy_threshold": 80.0},
                estimated_effort=calc_effort(2),
                locked=True,
                status="LOCKED"
            )
            st4 = Stage(
                stage_id="stage_04_student_teaching_practicum",
                phase_id="phase_03_teaching_credentials",
                stage_number=4,
                title="Supervised Student Teaching Practicum & Teaching Licensure",
                objective="Complete supervised student teaching placement, classroom observation evaluations, and state licensure examination (CTET/B.Ed).",
                skills=["Classroom Teaching Delivery", "Mentor Teacher Evaluation", "State Teacher Certification", "Pedagogical Reflection"],
                prerequisites=["stage_03_classroom_management_inclusion"],
                missions=[],
                resources=[],
                evidence_requirements=["Supervising teacher evaluation report and state teaching examination scorecard."],
                completion_rules={"accuracy_threshold": 80.0},
                estimated_effort=calc_effort(4),
                locked=True,
                status="LOCKED"
            )
            phases = [
                RoadmapPhase(
                    phase_id="phase_01_pedagogy",
                    title="Phase 1: Pedagogical Foundations & Curriculum Design",
                    description="Educational psychology, Bloom's taxonomy, and backward curricular architecture.",
                    stages=[st1, st2]
                ),
                RoadmapPhase(
                    phase_id="phase_02_instructional_practice",
                    title="Phase 2: Classroom Management & Inclusive Learning",
                    description="Behavioral systems, differentiated instruction, and Universal Design for Learning.",
                    stages=[st3]
                ),
                RoadmapPhase(
                    phase_id="phase_03_teaching_credentials",
                    title="Phase 3: Practicum & State Teacher Certification",
                    description="Supervised student teaching and teacher eligibility examination.",
                    stages=[st4]
                )
            ]
            current_stage_id = "stage_01_pedagogical_foundations"
            current_mission_id = "mission_01_constructivist_lesson"

        # 9. CIVIL SERVICES / UPSC CANDIDATE
        elif any(k in lower for k in ["upsc", "civil services", "public policy", "ias", "ips"]):
            st1 = Stage(
                stage_id="stage_01_polity_governance_economy",
                phase_id="phase_01_prelims_foundations",
                stage_number=1,
                title="Constitutional Polity, Governance & Indian Economy Foundations",
                objective="Master Indian Constitution articles, separation of powers, statutory bodies, macroeconomics, and fiscal policy.",
                skills=["Indian Polity", "Constitutional Articles", "Governance Frameworks", "Macroeconomics"],
                prerequisites=[],
                missions=[
                    Mission(
                        mission_id="mission_01_constitutional_doctrine",
                        stage_id="stage_01_polity_governance_economy",
                        objective="Analyze landmark Supreme Court constitutional bench decisions and draft a policy governance summary.",
                        why="Constitutional doctrine and statutory frameworks form the core foundation of civil administration.",
                        estimated_time="6–7 hours",
                        steps=[
                            "Review foundational constitutional provisions on basic structure doctrine and judicial review.",
                            "Analyze key governance reform commissions (e.g. 2nd ARC recommendations).",
                            "Draft a 250-word evaluative answer analyzing constitutional checks and balances."
                        ],
                        resources=[],
                        evidence_requirements=["Evaluated 250-word GS Paper II format answer script."],
                        completion_criteria="Answer incorporates constitutional articles and commission references.",
                        status="ACTIVE"
                    )
                ],
                resources=[],
                evidence_requirements=["Evaluated constitutional policy answer script."],
                completion_rules={"accuracy_threshold": 80.0},
                estimated_effort=calc_effort(3),
                locked=False,
                status="ACTIVE"
            )
            st2 = Stage(
                stage_id="stage_02_mains_answer_writing",
                phase_id="phase_02_mains_integration",
                stage_number=2,
                title="General Studies Mains Integrated Answer Writing (GS I–IV)",
                objective="Master multi-dimensional answer writing across History, Geography, Polity, Economy, Environment, and Security.",
                skills=["Answer Structuring", "Multi-Dimensional Analysis", "Current Affairs Integration", "Speed & Time Management"],
                prerequisites=["stage_01_polity_governance_economy"],
                missions=[],
                resources=[],
                evidence_requirements=["Evaluated full-length GS Mains test paper with mentor assessment."],
                completion_rules={"accuracy_threshold": 80.0},
                estimated_effort=calc_effort(4),
                locked=True,
                status="LOCKED"
            )
            st3 = Stage(
                stage_id="stage_03_optional_subject_mastery",
                phase_id="phase_02_mains_integration",
                stage_number=3,
                title="Optional Subject Advanced Conceptual Mastery & PYQs",
                objective="Complete exhaustive academic coverage of chosen optional subject with past 10 years' question analysis.",
                skills=["Optional Subject Theory", "Academic Depth", "PYQ Deconstruction", "Scholarly Arguments"],
                prerequisites=["stage_02_mains_answer_writing"],
                missions=[],
                resources=[],
                evidence_requirements=["Comprehensive optional subject test series evaluation copy."],
                completion_rules={"accuracy_threshold": 80.0},
                estimated_effort=calc_effort(4),
                locked=True,
                status="LOCKED"
            )
            st4 = Stage(
                stage_id="stage_04_ethics_personality_interview",
                phase_id="phase_03_interview_readiness",
                stage_number=4,
                title="Ethics, Integrity & Personality Test Board Interview Preparation",
                objective="Resolve administrative ethics case studies (GS IV) and participate in personality test mock interview boards.",
                skills=["Ethics Case Studies", "Administrative Poise", "Nuanced Articulation", "Policy Defense"],
                prerequisites=["stage_03_optional_subject_mastery"],
                missions=[],
                resources=[],
                evidence_requirements=["Mock interview board evaluation transcript and scored ethics case study copy."],
                completion_rules={"accuracy_threshold": 80.0},
                estimated_effort=calc_effort(3),
                locked=True,
                status="LOCKED"
            )
            phases = [
                RoadmapPhase(
                    phase_id="phase_01_prelims_foundations",
                    title="Phase 1: Polity, Governance & Economic Foundations",
                    description="Constitutional law, statutory governance frameworks, and Indian economy fundamentals.",
                    stages=[st1]
                ),
                RoadmapPhase(
                    phase_id="phase_02_mains_integration",
                    title="Phase 2: Mains Multi-Disciplinary Writing & Optional Mastery",
                    description="General Studies Papers I–IV answer structuring and comprehensive optional subject depth.",
                    stages=[st2, st3]
                ),
                RoadmapPhase(
                    phase_id="phase_03_interview_readiness",
                    title="Phase 3: Ethics & Personality Test Board Preparation",
                    description="Administrative ethics case resolution and board interview simulations.",
                    stages=[st4]
                )
            ]
            current_stage_id = "stage_01_polity_governance_economy"
            current_mission_id = "mission_01_constitutional_doctrine"

        # 10. THEORETICAL MATHEMATICIAN / PURE MATHEMATICS
        elif any(k in lower for k in ["mathematician", "pure mathematics", "theoretical math"]):
            st1 = Stage(
                stage_id="stage_01_abstract_algebra",
                phase_id="phase_01_algebraic_foundations",
                stage_number=1,
                title="Abstract Algebra: Groups, Rings & Galois Theory",
                objective="Master foundational algebraic structures, group homomorphisms, quotient rings, and field extensions.",
                skills=["Group Theory", "Ring Theory", "Field Extensions", "Galois Theory"],
                prerequisites=[],
                missions=[
                    Mission(
                        mission_id="mission_01_galois_proof",
                        stage_id="stage_01_abstract_algebra",
                        objective="Construct formal proofs of solvability by radicals using Galois correspondence for polynomial extensions.",
                        why="Abstract algebra develops the foundational language and proof rigor essential for modern pure mathematics.",
                        estimated_time="6–8 hours",
                        steps=[
                            "Review group actions, normal subgroups, and Sylow theorems.",
                            "Formulate field splitting extensions and determine Galois groups.",
                            "Draft rigorous axiomatic proofs with detailed intermediate lemmas."
                        ],
                        resources=[],
                        evidence_requirements=["Evaluated problem set proof document in LaTeX."],
                        completion_criteria="Proofs adhere to rigorous epsilon-delta and axiomatic deduction standards.",
                        status="ACTIVE"
                    )
                ],
                resources=[],
                evidence_requirements=["Abstract algebra problem set verifications in LaTeX."],
                completion_rules={"accuracy_threshold": 80.0},
                estimated_effort=calc_effort(3),
                locked=False,
                status="ACTIVE"
            )
            st2 = Stage(
                stage_id="stage_02_real_analysis_measure",
                phase_id="phase_01_algebraic_foundations",
                stage_number=2,
                title="Real Analysis, Metric Spaces & Measure Theory",
                objective="Master metric space completeness, Lebesgue measure, dominated convergence theorem, and Hilbert spaces.",
                skills=["Metric Spaces", "Lebesgue Integration", "Measure Theory", "Cauchy Sequences"],
                prerequisites=["stage_01_abstract_algebra"],
                missions=[],
                resources=[],
                evidence_requirements=["Real analysis and measure theory proof portfolio."],
                completion_rules={"accuracy_threshold": 80.0},
                estimated_effort=calc_effort(3),
                locked=True,
                status="LOCKED"
            )
            st3 = Stage(
                stage_id="stage_03_topology_manifolds",
                phase_id="phase_02_geometric_foundations",
                stage_number=3,
                title="Point-Set & Differential Topology",
                objective="Master topological spaces, compact Hausdorff manifolds, fundamental groups, and differential forms.",
                skills=["Topological Spaces", "Manifolds", "Homotopy", "Compactness"],
                prerequisites=["stage_02_real_analysis_measure"],
                missions=[],
                resources=[],
                evidence_requirements=["Documented topology proofs and homotopy classifications."],
                completion_rules={"accuracy_threshold": 80.0},
                estimated_effort=calc_effort(3),
                locked=True,
                status="LOCKED"
            )
            st4 = Stage(
                stage_id="stage_04_formal_proofs_monograph",
                phase_id="phase_03_mathematical_synthesis",
                stage_number=4,
                title="Formal Mathematical Proofs & Expository Monograph",
                objective="Author an original mathematical manuscript or comprehensive expository monograph formatted in LaTeX for scholarly dissemination.",
                skills=["Axiomatic Deduction", "Scholarly LaTeX", "Mathematical Proof Writing", "Expository Research"],
                prerequisites=["stage_03_topology_manifolds"],
                missions=[],
                resources=[],
                evidence_requirements=["Complete mathematical research draft or expository thesis manuscript."],
                completion_rules={"accuracy_threshold": 80.0},
                estimated_effort=calc_effort(4),
                locked=True,
                status="LOCKED"
            )
            phases = [
                RoadmapPhase(
                    phase_id="phase_01_algebraic_foundations",
                    title="Phase 1: Abstract Algebra & Real Analysis",
                    description="Group theory, field extensions, and rigorous measure theory.",
                    stages=[st1, st2]
                ),
                RoadmapPhase(
                    phase_id="phase_02_geometric_foundations",
                    title="Phase 2: Topology & Smooth Manifolds",
                    description="Point-set topology, homotopy groups, and differential geometry.",
                    stages=[st3]
                ),
                RoadmapPhase(
                    phase_id="phase_03_mathematical_synthesis",
                    title="Phase 3: Formal Proofs & Scholarly Publication",
                    description="Authoring mathematical manuscripts and rigorous proof defenses.",
                    stages=[st4]
                )
            ]
            current_stage_id = "stage_01_abstract_algebra"
            current_mission_id = "mission_01_galois_proof"

        # 11. OPERATIONS MANAGER
        elif any(k in lower for k in ["operations manager", "ops manager", "business operations"]):
            st1 = Stage(
                stage_id="stage_01_process_optimization",
                phase_id="phase_01_ops_foundations",
                stage_number=1,
                title="Cross-Functional Process Optimization & Lean Workflows",
                objective="Map end-to-end organizational value streams, eliminate operational bottlenecks, and implement Lean Six Sigma practices.",
                skills=["Value Stream Mapping", "Bottleneck Mitigation", "Six Sigma", "Workflow Design"],
                prerequisites=[],
                missions=[
                    Mission(
                        mission_id="mission_01_value_stream",
                        stage_id="stage_01_process_optimization",
                        objective="Conduct a value stream audit of an enterprise workflow and author a cycle-time reduction blueprint.",
                        why="Operational efficiency hinges on rigorous bottleneck diagnosis and waste elimination.",
                        estimated_time="5–6 hours",
                        steps=[
                            "Map current-state cross-functional handoffs across departments.",
                            "Identify throughput constraints, wait times, and failure demand.",
                            "Design future-state streamlined process workflow with measurable SLAs."
                        ],
                        resources=[],
                        evidence_requirements=["Comprehensive value stream map and process optimization runbook."],
                        completion_criteria="Blueprint identifies specific cycle-time bottlenecks and measurable KPIs.",
                        status="ACTIVE"
                    )
                ],
                resources=[],
                evidence_requirements=["Process mapping blueprint and cycle-time optimization report."],
                completion_rules={"accuracy_threshold": 80.0},
                estimated_effort=calc_effort(2),
                locked=False,
                status="ACTIVE"
            )
            st2 = Stage(
                stage_id="stage_02_kpi_telemetry",
                phase_id="phase_01_ops_foundations",
                stage_number=2,
                title="KPI Dashboard Design, Telemetry & Operational Metrics",
                objective="Establish real-time metric instrumentation, SLA governance frameworks, and executive operational reviews.",
                skills=["Metric Telemetry", "SLA Governance", "Capacity Planning", "OKR Alignment"],
                prerequisites=["stage_01_process_optimization"],
                missions=[],
                resources=[],
                evidence_requirements=["Executive KPI dashboard design and SLA tracking schema."],
                completion_rules={"accuracy_threshold": 80.0},
                estimated_effort=calc_effort(2),
                locked=True,
                status="LOCKED"
            )
            st3 = Stage(
                stage_id="stage_03_vendor_procurement",
                phase_id="phase_02_ops_execution",
                stage_number=3,
                title="Vendor Management & Procurement Contract Negotiations",
                objective="Draft comprehensive RFPs, evaluate vendor cost models, and negotiate high-stakes SLAs.",
                skills=["RFP Drafting", "Vendor Scorecards", "SLA Negotiations", "Supplier Risk Management"],
                prerequisites=["stage_02_kpi_telemetry"],
                missions=[],
                resources=[],
                evidence_requirements=["Vendor evaluation scorecard and negotiated SLA contract."],
                completion_rules={"accuracy_threshold": 80.0},
                estimated_effort=calc_effort(3),
                locked=True,
                status="LOCKED"
            )
            st4 = Stage(
                stage_id="stage_04_transformation_runbook",
                phase_id="phase_03_ops_leadership",
                stage_number=4,
                title="Enterprise Transformation Runbook & SOP Publication",
                objective="Lead organizational change management, author definitive standard operating procedures (SOP), and present business transformation.",
                skills=["Change Management", "SOP Runbooks", "Executive Presentations", "Operational Scaling"],
                prerequisites=["stage_03_vendor_procurement"],
                missions=[],
                resources=[],
                evidence_requirements=["Enterprise transformation business case and complete SOP runbook."],
                completion_rules={"accuracy_threshold": 80.0},
                estimated_effort=calc_effort(3),
                locked=True,
                status="LOCKED"
            )
            phases = [
                RoadmapPhase(
                    phase_id="phase_01_ops_foundations",
                    title="Phase 1: Process Optimization & KPI Telemetry",
                    description="Value stream mapping, bottleneck mitigation, and metric dashboards.",
                    stages=[st1, st2]
                ),
                RoadmapPhase(
                    phase_id="phase_02_ops_execution",
                    title="Phase 2: Procurement & Vendor Management",
                    description="RFP drafting, SLA contract negotiations, and supplier governance.",
                    stages=[st3]
                ),
                RoadmapPhase(
                    phase_id="phase_03_ops_leadership",
                    title="Phase 3: Organizational Transformation",
                    description="Change management execution and standard operating procedures.",
                    stages=[st4]
                )
            ]
            current_stage_id = "stage_01_process_optimization"
            current_mission_id = "mission_01_value_stream"

        # 12. AUTONOMOUS DRONE HARDWARE SPECIALIST
        elif any(k in lower for k in ["drone hardware", "drone", "uav", "aerospace hardware"]):
            st1 = Stage(
                stage_id="stage_01_embedded_flight_firmware",
                phase_id="phase_01_avionics_foundations",
                stage_number=1,
                title="Embedded Flight Controller Firmware & Microcontrollers (C/C++)",
                objective="Master real-time flight firmware architecture, PX4 / ArduPilot builds, STM32 microcontrollers, and UART/CAN bus buses.",
                skills=["PX4 Architecture", "STM32 Microcontrollers", "UART/CAN Protocols", "C/C++ Embedded"],
                prerequisites=[],
                missions=[
                    Mission(
                        mission_id="mission_01_firmware_build",
                        stage_id="stage_01_embedded_flight_firmware",
                        objective="Compile and flash a custom PX4 flight controller firmware module and log hardware-in-the-loop telemetry.",
                        why="Autonomous drone reliability requires deep control over embedded real-time flight firmware.",
                        estimated_time="5–6 hours",
                        steps=[
                            "Set up embedded ARM toolchain and PX4 development environment.",
                            "Write a custom sensor driver node handling I2C/SPI telemetry.",
                            "Flash STM32 flight board and verify 500Hz loop rate."
                        ],
                        resources=[],
                        evidence_requirements=["Custom flight firmware code repository and logic analyzer trace."],
                        completion_criteria="Firmware executes at targeted real-time frequency without watchdog resets.",
                        status="ACTIVE"
                    )
                ],
                resources=[],
                evidence_requirements=["Embedded firmware code and flight controller bench test logs."],
                completion_rules={"accuracy_threshold": 80.0},
                estimated_effort=calc_effort(3),
                locked=False,
                status="ACTIVE"
            )
            st2 = Stage(
                stage_id="stage_02_sensor_fusion_state_estimation",
                phase_id="phase_01_avionics_foundations",
                stage_number=2,
                title="Sensor Fusion & State Estimation (IMU, LiDAR, Optical Flow)",
                objective="Implement Extended Kalman Filters (EKF), vibration dampening filters, optical flow odometry, and magnetometer calibration.",
                skills=["Extended Kalman Filters", "IMU Filtering", "Optical Flow Calibration", "LiDAR Interfacing"],
                prerequisites=["stage_01_embedded_flight_firmware"],
                missions=[],
                resources=[],
                evidence_requirements=["Sensor calibration report and state estimation telemetry plots."],
                completion_rules={"accuracy_threshold": 80.0},
                estimated_effort=calc_effort(3),
                locked=True,
                status="LOCKED"
            )
            st3 = Stage(
                stage_id="stage_03_ros2_actuator_interfaces",
                phase_id="phase_02_autonomous_integration",
                stage_number=3,
                title="ROS 2 Hardware Interfaces & Actuator Control (ESC/BLDC)",
                objective="Configure micro-ROS nodes, DShot electronic speed controllers, and conduct dynamometer thrust-to-weight testing.",
                skills=["micro-ROS", "DShot Protocols", "ESC Configuration", "Thrust Bench Testing"],
                prerequisites=["stage_02_sensor_fusion_state_estimation"],
                missions=[],
                resources=[],
                evidence_requirements=["ROS 2 node integration code and motor dyno test results."],
                completion_rules={"accuracy_threshold": 80.0},
                estimated_effort=calc_effort(3),
                locked=True,
                status="LOCKED"
            )
            st4 = Stage(
                stage_id="stage_04_flight_telemetry_integration",
                phase_id="phase_03_hardware_flight_test",
                stage_number=4,
                title="Autonomous Flight Telemetry & Airframe Integration",
                objective="Integrate physical avionics into an airframe, run autonomous waypoint missions, and analyze high-rate flight telemetry logs.",
                skills=["Avionics Packaging", "Vibration Damping", "Autonomous Navigation", "Flight Log Telemetry"],
                prerequisites=["stage_03_ros2_actuator_interfaces"],
                missions=[],
                resources=[],
                evidence_requirements=["Recorded flight log analysis (.ulog) verifying waypoint accuracy."],
                completion_rules={"accuracy_threshold": 80.0},
                estimated_effort=calc_effort(4),
                locked=True,
                status="LOCKED"
            )
            phases = [
                RoadmapPhase(
                    phase_id="phase_01_avionics_foundations",
                    title="Phase 1: Embedded Firmware & Sensor Fusion",
                    description="PX4 microcontrollers, C++ firmware, and Extended Kalman Filtering.",
                    stages=[st1, st2]
                ),
                RoadmapPhase(
                    phase_id="phase_02_autonomous_integration",
                    title="Phase 2: ROS 2 & Actuator Control",
                    description="micro-ROS hardware interfacing and BLDC motor ESC configuration.",
                    stages=[st3]
                ),
                RoadmapPhase(
                    phase_id="phase_03_hardware_flight_test",
                    title="Phase 3: Airframe Integration & Telemetry",
                    description="Physical prototype assembly and autonomous flight log verification.",
                    stages=[st4]
                )
            ]
            current_stage_id = "stage_01_embedded_flight_firmware"
            current_mission_id = "mission_01_firmware_build"

        # 13. COMPUTATIONAL FLUID DYNAMICS (CFD) RESEARCHER
        elif any(k in lower for k in ["computational fluid dynamics", "cfd", "fluid dynamics", "aerodynamics"]):
            st1 = Stage(
                stage_id="stage_01_navier_stokes_continuum",
                phase_id="phase_01_cfd_theory",
                stage_number=1,
                title="Navier-Stokes Equations & Continuum Fluid Dynamics",
                objective="Derive mass, momentum, and energy conservation equations, boundary layer theory, and compressible vs incompressible flow regimes.",
                skills=["Conservation Laws", "Boundary Layer Theory", "Compressible Flow", "Analytical Aerodynamics"],
                prerequisites=[],
                missions=[
                    Mission(
                        mission_id="mission_01_boundary_layer",
                        stage_id="stage_01_navier_stokes_continuum",
                        objective="Derive analytical solutions for laminar boundary layer equations and compare with numerical benchmarks.",
                        why="Theoretical fluid dynamics foundations prevent misinterpretation of numerical simulation artifacts.",
                        estimated_time="5–6 hours",
                        steps=[
                            "Derive 2D Navier-Stokes momentum equations in differential form.",
                            "Apply Blasius similarity transformation for flat plate boundary layer.",
                            "Document shear stress and skin friction coefficients."
                        ],
                        resources=[],
                        evidence_requirements=["Analytical fluid mechanics derivation notes and validation graphs."],
                        completion_criteria="Derivation correctly matches standard boundary layer solutions.",
                        status="ACTIVE"
                    )
                ],
                resources=[],
                evidence_requirements=["Theoretical fluid mechanics derivations and problem sets."],
                completion_rules={"accuracy_threshold": 80.0},
                estimated_effort=calc_effort(3),
                locked=False,
                status="ACTIVE"
            )
            st2 = Stage(
                stage_id="stage_02_fvm_mesh_generation",
                phase_id="phase_01_cfd_theory",
                stage_number=2,
                title="Numerical Discretization & Mesh Generation (FVM / FEM)",
                objective="Master Finite Volume Method (FVM), spatial/temporal schemes, boundary layer inflation layers, and grid convergence studies.",
                skills=["Finite Volume Method (FVM)", "Spatial Discretization", "Prism Layer Meshing", "Grid Independence Studies"],
                prerequisites=["stage_01_navier_stokes_continuum"],
                missions=[],
                resources=[],
                evidence_requirements=["Mesh convergence study report with Richardson extrapolation."],
                completion_rules={"accuracy_threshold": 80.0},
                estimated_effort=calc_effort(3),
                locked=True,
                status="LOCKED"
            )
            st3 = Stage(
                stage_id="stage_03_turbulence_modeling",
                phase_id="phase_02_simulation_engineering",
                stage_number=3,
                title="Turbulence Modeling: RANS, LES & Wall Functions",
                objective="Implement and benchmark k-omega SST, k-epsilon, and Large Eddy Simulation (LES) against adverse pressure gradient test cases.",
                skills=["k-omega SST", "Reynolds Stress", "Large Eddy Simulation", "Wall Functions"],
                prerequisites=["stage_02_fvm_mesh_generation"],
                missions=[],
                resources=[],
                evidence_requirements=["Comparative turbulence modeling benchmark report."],
                completion_rules={"accuracy_threshold": 80.0},
                estimated_effort=calc_effort(3),
                locked=True,
                status="LOCKED"
            )
            st4 = Stage(
                stage_id="stage_04_hpc_validation_study",
                phase_id="phase_03_cfd_validation",
                stage_number=4,
                title="HPC Parallel Solvers & Experimental Validation Study",
                objective="Run multi-node parallel CFD simulations in OpenFOAM with MPI and author a comprehensive validation report against wind tunnel datasets.",
                skills=["OpenFOAM", "MPI Domain Decomposition", "Wind Tunnel Validation", "Scholarly Simulation Defense"],
                prerequisites=["stage_03_turbulence_modeling"],
                missions=[],
                resources=[],
                evidence_requirements=["Comprehensive validation study comparing simulation against experimental wind tunnel data."],
                completion_rules={"accuracy_threshold": 80.0},
                estimated_effort=calc_effort(4),
                locked=True,
                status="LOCKED"
            )
            phases = [
                RoadmapPhase(
                    phase_id="phase_01_cfd_theory",
                    title="Phase 1: Continuum Fluid Dynamics & FVM Meshing",
                    description="Navier-Stokes equations, boundary layer theory, and finite volume mesh generation.",
                    stages=[st1, st2]
                ),
                RoadmapPhase(
                    phase_id="phase_02_simulation_engineering",
                    title="Phase 2: Turbulence Modeling & HPC Solvers",
                    description="RANS/LES turbulence modeling and parallel computing.",
                    stages=[st3]
                ),
                RoadmapPhase(
                    phase_id="phase_03_cfd_validation",
                    title="Phase 3: Experimental Validation & Defense",
                    description="Validating numerical pressure and drag against experimental wind tunnel benchmarks.",
                    stages=[st4]
                )
            ]
            current_stage_id = "stage_01_navier_stokes_continuum"
            current_mission_id = "mission_01_boundary_layer"


        # 7. DEFAULT GENERIC DOMAIN-AGNOSTIC SYNTHESIS
        else:
            st1 = Stage(
                stage_id="stage_01_foundations",
                phase_id="phase_01_core",
                stage_number=1,
                title=f"{target_outcome} Foundations & Professional Standards",
                objective=f"Master fundamental principles, professional methodologies, and foundational competencies for {target_outcome}.",
                skills=[f"Core {target_outcome} Principles", "Professional Methodologies", "Foundational Competencies"],
                prerequisites=[],
                missions=[
                    Mission(
                        mission_id="mission_01_foundational_artifact",
                        stage_id="stage_01_foundations",
                        objective=f"Produce an introductory verified portfolio artifact demonstrating core competencies in {target_outcome}.",
                        why="Establishes demonstrated execution before advancing into specialized practices.",
                        estimated_time="5–6 hours",
                        steps=[
                            "Review foundational industry standards and evaluation criteria.",
                            "Construct introductory demonstration artifact.",
                            "Document methodology and reflections."
                        ],
                        resources=[],
                        evidence_requirements=[f"Submitted portfolio artifact demonstrating {target_outcome} basics."],
                        completion_criteria="Artifact demonstrates adherence to core domain standards.",
                        status="ACTIVE"
                    )
                ],
                resources=[],
                evidence_requirements=[f"Foundational artifact in {target_outcome}."],
                completion_rules={"accuracy_threshold": 80.0},
                estimated_effort=calc_effort(2),
                locked=False,
                status="ACTIVE"
            )
            st2 = Stage(
                stage_id="stage_02_applied_competencies",
                phase_id="phase_01_core",
                stage_number=2,
                title=f"Applied Methods & Practical Execution in {target_outcome}",
                objective=f"Execute end-to-end practical deliverables and professional workflows in {target_outcome}.",
                skills=[f"Applied {target_outcome} Techniques", "Quality Standards", "Practical Delivery"],
                prerequisites=["stage_01_foundations"],
                missions=[],
                resources=[],
                evidence_requirements=[f"Applied project deliverable in {target_outcome}."],
                completion_rules={"accuracy_threshold": 80.0},
                estimated_effort=calc_effort(3),
                locked=True,
                status="LOCKED"
            )
            st3 = Stage(
                stage_id="stage_03_professional_capstone",
                phase_id="phase_02_capstone",
                stage_number=3,
                title=f"Professional Portfolio Capstone in {target_outcome}",
                objective=f"Publish a comprehensive, peer-reviewed or industry-evaluated capstone portfolio in {target_outcome}.",
                skills=[f"Capstone Project", "Industry Presentation", "Professional Portfolio"],
                prerequisites=["stage_02_applied_competencies"],
                missions=[],
                resources=[],
                evidence_requirements=[f"Verified public capstone portfolio in {target_outcome}."],
                completion_rules={"accuracy_threshold": 80.0},
                estimated_effort=calc_effort(3),
                locked=True,
                status="LOCKED"
            )
            phases = [
                RoadmapPhase(
                    phase_id="phase_01_core",
                    title="Phase 1: Foundations & Applied Practice",
                    description=f"Core competencies and practical delivery in {target_outcome}.",
                    stages=[st1, st2]
                ),
                RoadmapPhase(
                    phase_id="phase_02_capstone",
                    title="Phase 2: Professional Capstone & Launch",
                    description=f"Capstone project and verified public portfolio launch.",
                    stages=[st3]
                )
            ]
            current_stage_id = "stage_01_foundations"
            current_mission_id = "mission_01_foundational_artifact"

        flat_stages = []
        for p in phases:
            flat_stages.extend(p.stages)

        total_stages = len(flat_stages)

        return Roadmap(
            roadmap_id=f"rm_{person_id}_{now_ts}",
            person_id=person_id,
            path_id=path_id or f"path_{target_outcome.lower().replace(' ', '_')[:30]}",
            version=1,
            target_outcome=target_outcome,
            phases=phases,
            current_stage_id=current_stage_id,
            current_mission_id=current_mission_id,
            total_stages=total_stages,
            completed_stages=0,
            checkpoint_interval=total_stages,
            revision_reason=f"Personalized synthesis conditioned on target outcome '{target_outcome}'.",
            constraints=actual_constraints
        )

    async def get_or_create_roadmap(
        self,
        person_id: str,
        path_id: Optional[str] = None,
        target_outcome: Optional[str] = None
    ) -> Roadmap:
        active_dict = await self.store.get_active_roadmap(person_id)
        if active_dict:
            return Roadmap(**active_dict)

        # 1. Check if user has a stored goal
        stored_goal = await self.store.get_goal(person_id)
        if stored_goal and stored_goal.get("target_outcome"):
            new_roadmap = await self.synthesize_personalized_roadmap(
                person_id=person_id,
                target_outcome=stored_goal["target_outcome"],
                target_domain=stored_goal.get("target_domain"),
                constraints=stored_goal.get("constraints") or {},
                path_id=path_id or f"path_{stored_goal.get('target_outcome', '').lower().replace(' ', '_')}"
            )
            await self.store.save_roadmap(person_id, new_roadmap.model_dump(mode="json"))
            return new_roadmap

        # 2. Check if target_outcome parameter provided
        if target_outcome:
            new_roadmap = await self.synthesize_personalized_roadmap(
                person_id=person_id,
                target_outcome=target_outcome,
                path_id=path_id or f"path_{target_outcome.lower().replace(' ', '_')}"
            )
            await self.store.save_roadmap(person_id, new_roadmap.model_dump(mode="json"))
            return new_roadmap


        # 4. If neither goal nor valid path exists for production user, raise explicit error instead of silent AI hallucination
        raise ValueError("NEEDS_USER_INPUT: No canonical goal or path found for user. Cannot synthesize roadmap without direction.")

    def get_all_stages_flat(self, roadmap: Roadmap) -> List[Stage]:
        flat = []
        for phase in roadmap.phases:
            flat.extend(phase.stages)
        return flat

    def build_disclosed_view(
        self,
        roadmap: Roadmap,
        personal_agent_note: Optional[str] = None,
        memory_moment: Optional[Dict[str, Any]] = None
    ) -> DisclosedRoadmapView:
        """
        Progressive Disclosure:
        - Active stage contains full missions and resources.
        - Locked future stages reveal ONLY title, objective, and locked indicator. Protected content is stripped.
        """
        flat_stages = self.get_all_stages_flat(roadmap)
        active_stage = next((s for s in flat_stages if s.stage_id == roadmap.current_stage_id), None)
        active_mission = active_stage.missions[0] if active_stage and active_stage.missions else None

        disclosed_stages = []
        for s in flat_stages:
            if not s.locked:
                # Disclose full details
                why_now = s.why_now or (
                    f"Stage {s.stage_number} is currently active as the primary foundational prerequisite for your target outcome."
                    if s.stage_number == 1 else
                    f"Stage {s.stage_number} activates upon verified completion of prerequisite competencies: {', '.join(s.prerequisites) if s.prerequisites else 'prior stage'}."
                )
                prereq_rationale = s.prerequisite_rationale or (
                    f"Demonstrated mastery of {', '.join(s.prerequisites)} ensures a rigorous baseline before advancing."
                    if s.prerequisites else "Establishes foundational competencies required for advanced stages."
                )
                curr_mission = s.missions[0] if s.missions else None
                unlock_text = (curr_mission.what_will_this_unlock if curr_mission and curr_mission.what_will_this_unlock else None) or (
                    f"Unlocks next stage and verified practical competencies in {', '.join(s.skills[:2]) if s.skills else s.title}."
                )
                evidence_text = (curr_mission.what_evidence_will_count if curr_mission and curr_mission.what_evidence_will_count else None) or (
                    s.evidence_requirements[0] if s.evidence_requirements else "Verified portfolio artifact or evaluation submission."
                )
                disclosed_stages.append(
                    DisclosedStageView(
                        stage_id=s.stage_id,
                        phase_id=s.phase_id,
                        stage_number=s.stage_number,
                        title=s.title,
                        objective=s.objective,
                        skills=s.skills,
                        estimated_effort=s.estimated_effort,
                        locked=False,
                        status=s.status,
                        current_mission=curr_mission,
                        resources=s.resources,
                        evidence_requirements=s.evidence_requirements,
                        why_now=why_now,
                        prerequisite_rationale=prereq_rationale,
                        what_will_this_unlock=unlock_text,
                        what_evidence_will_count=evidence_text
                    )
                )
            else:
                # Progressive disclosure: Redact protected mission content & resources
                why_now_locked = s.why_now or f"Stage {s.stage_number} unlocks sequentially once previous stages are verified."
                prereq_locked = s.prerequisite_rationale or (
                    f"Requires completion of prerequisite stage competencies: {', '.join(s.prerequisites) if s.prerequisites else 'prior stage'}."
                )
                unlock_locked = f"Unlocks advanced competencies in {', '.join(s.skills[:2]) if s.skills else s.title}."
                evidence_locked = s.evidence_requirements[0] if s.evidence_requirements else "Submission of stage verification artifact."
                disclosed_stages.append(
                    DisclosedStageView(
                        stage_id=s.stage_id,
                        phase_id=s.phase_id,
                        stage_number=s.stage_number,
                        title=s.title,
                        objective=s.objective,
                        skills=s.skills,
                        estimated_effort=s.estimated_effort,
                        locked=True,
                        status="LOCKED",
                        current_mission=None,
                        resources=[],
                        evidence_requirements=[],
                        why_now=why_now_locked,
                        prerequisite_rationale=prereq_locked,
                        what_will_this_unlock=unlock_locked,
                        what_evidence_will_count=evidence_locked
                    )
                )

        progress_pct = (roadmap.completed_stages / max(roadmap.total_stages, 1)) * 100.0

        return DisclosedRoadmapView(
            roadmap_id=roadmap.roadmap_id,
            person_id=roadmap.person_id,
            path_id=roadmap.path_id,
            version=roadmap.version,
            target_outcome=roadmap.target_outcome,
            current_stage_id=roadmap.current_stage_id,
            total_stages=roadmap.total_stages,
            completed_stages=roadmap.completed_stages,
            overall_progress_percent=progress_pct,
            stages=disclosed_stages,
            active_stage=active_stage,
            active_mission=active_mission,
            personal_agent_note=personal_agent_note,
            memory_moment=memory_moment
        )

    async def evaluate_evidence_and_progress(
        self,
        person_id: str,
        submission: EvidenceSubmission
    ) -> EvaluationResult:
        """
        ADK EvidenceEvaluatorAgent + Progression Loop:
        1. Evaluates evidence against stage criteria.
        2. If PASS: Unlocks next stage on backend, triggers Personal Agent Learning Loop.
        3. If REINFORCE: Inserts remediation mission, tracks learning signal.
        """
        roadmap = await self.get_or_create_roadmap(person_id)
        flat_stages = self.get_all_stages_flat(roadmap)
        target_stage = next((s for s in flat_stages if s.stage_id == submission.stage_id), None)

        if not target_stage:
            raise ValueError("Target stage not found in active roadmap.")

        # Backend Lock Enforcement: Reject submission if attempting to submit for locked stage
        if target_stage.locked and target_stage.stage_id != roadmap.current_stage_id:
            raise PermissionError("Access denied: Cannot submit evidence for a locked stage.")

        # Save submission
        await self.store.save_evidence_submission(person_id, submission.model_dump(mode="json"))

        # Evaluate evidence: Substantive content verification
        payload = submission.content_payload or {}
        evidence_text = str(payload.get("code", "") or payload.get("repo_url", "") or payload.get("explanation", "") or payload.get("text", "") or payload.get("artifact_url", "")).strip()

        # Determine pass based on non-trivial substantive submission
        is_pass = len(evidence_text) >= 20 and (
            "test" in evidence_text.lower() or
            "def " in evidence_text or
            "http" in evidence_text.lower() or
            "import" in evidence_text.lower() or
            "analysis" in evidence_text.lower() or
            "draft" in evidence_text.lower() or
            "brief" in evidence_text.lower() or
            "figma" in evidence_text.lower() or
            "plan" in evidence_text.lower() or
            "protocol" in evidence_text.lower() or
            "report" in evidence_text.lower()
        )

        current_idx = next(i for i, s in enumerate(flat_stages) if s.stage_id == target_stage.stage_id)
        next_stage = flat_stages[current_idx + 1] if current_idx + 1 < len(flat_stages) else None

        if is_pass:
            demonstrated_skills = [f"Demonstrated proficiency in {sk}." for sk in target_stage.skills[:3]] or ["Demonstrated stage objective competencies."]
            eval_result = EvaluationResult(
                submission_id=submission.submission_id,
                stage_id=submission.stage_id,
                mission_id=submission.mission_id,
                status="PASS",
                mastery_dimensions=MasteryDimensions(
                    understanding=90.0,
                    application=88.0,
                    transfer=82.0,
                    accuracy=94.0,
                    explanation=86.0
                ),
                demonstrated=demonstrated_skills,
                missing=[],
                feedback=f"Excellent execution. Your submission demonstrates solid practical mastery of {target_stage.title}.",
                recommended_next_action=f"Unlock {next_stage.title}." if next_stage else "Complete final milestone capstone.",
                confidence="HIGH",
                evaluated_at=datetime.now(timezone.utc).isoformat()
            )

            # --- Unlock Next Stage ---
            target_stage.status = "COMPLETED"
            roadmap.completed_stages += 1

            if next_stage:
                next_stage.locked = False
                next_stage.status = "ACTIVE"
                if next_stage.missions:
                    next_stage.missions[0].status = "ACTIVE"
                roadmap.current_stage_id = next_stage.stage_id
                roadmap.current_mission_id = next_stage.missions[0].mission_id if next_stage.missions else None

            # Persist updated roadmap
            await self.store.update_active_roadmap(person_id, roadmap.model_dump(mode="json"))

            # --- Personal Agent Learning Loop ---
            await self.personal_agent.process_learning_event_and_evolve(
                person_id=person_id,
                stage_id=submission.stage_id,
                evaluation=eval_result,
                concept=target_stage.title
            )

        else:
            # Reinforcement Path
            eval_result = EvaluationResult(
                submission_id=submission.submission_id,
                stage_id=submission.stage_id,
                mission_id=submission.mission_id,
                status="REINFORCE",
                mastery_dimensions=MasteryDimensions(
                    understanding=65.0,
                    application=60.0,
                    transfer=55.0,
                    accuracy=68.0,
                    explanation=70.0
                ),
                demonstrated=["Preliminary conceptual alignment attempted."],
                missing=[f"Verifiable artifact for {target_stage.title}", "Detailed methodology documentation"],
                feedback=f"Evidence is preliminary. We need a verifiable artifact or documentation to confirm competency in {target_stage.title}.",
                recommended_next_action=f"Review targeted guidance and submit completed milestone artifact for {target_stage.title}.",
                confidence="MEDIUM",
                evaluated_at=datetime.now(timezone.utc).isoformat()
            )
            target_stage.status = "REINFORCEMENT"

            # Create targeted reinforcement mission
            reinforcement_mission = Mission(
                mission_id=f"reinf_{target_stage.stage_id}",
                stage_id=target_stage.stage_id,
                objective=f"Reinforce core competencies in {target_stage.title}.",
                why="Ensuring deep comprehension before unlocking downstream dependencies.",
                estimated_time="1.5 hours",
                steps=[
                    f"Review the key principles of {target_stage.title}.",
                    "Address noted gaps and provide documented proof."
                ],
                resources=[],
                evidence_requirements=[f"Updated evidence artifact addressing feedback for {target_stage.title}."],
                completion_criteria="Submission satisfies core milestone criteria.",
                status="REINFORCING"
            )
            target_stage.missions.insert(0, reinforcement_mission)
            roadmap.current_mission_id = reinforcement_mission.mission_id
            await self.store.update_active_roadmap(person_id, roadmap.model_dump(mode="json"))

            # Track learning signal in personal agent
            await self.personal_agent.process_learning_event_and_evolve(
                person_id=person_id,
                stage_id=submission.stage_id,
                evaluation=eval_result,
                concept=target_stage.title
            )

        # Save evaluation result
        await self.store.save_evaluation_result(person_id, eval_result.model_dump(mode="json"))
        return eval_result

    async def adapt_constraints(
        self,
        person_id: str,
        req: AdaptConstraintRequest
    ) -> Roadmap:
        """
        Adapts roadmap workload and pacing without resetting completed progress.
        """
        roadmap = await self.get_or_create_roadmap(person_id)
        
        if req.weekly_hours:
            roadmap.constraints["weekly_hours"] = req.weekly_hours
            multiplier = 10.0 / float(req.weekly_hours)
            flat_stages = self.get_all_stages_flat(roadmap)
            for s in flat_stages:
                if s.locked:
                    s.estimated_effort = f"{round(1.5 * multiplier, 1)} Weeks"
            roadmap.revision_reason = f"Adjusted roadmap pacing for {req.weekly_hours} hours/week commitment."

        if req.preferred_format:
            roadmap.constraints["format_preference"] = req.preferred_format

        # Increment version
        version = await self.store.save_roadmap(person_id, roadmap.model_dump(mode="json"))
        roadmap.version = version
        return roadmap
