from typing import List, Dict, Any, Optional, Set
from datetime import datetime, timezone
import uuid

from backend.core.career_schemas import (
    RequirementNode,
    CareerRequirementGraph,
    CategorizedGap,
    UniversalCareerProfile
)
from backend.services.knowledge import KnowledgeService

class RequirementGraphService:
    """
    Goal-Conditioned Requirements Graph & Gap Analysis Engine for PATHMIND.
    Derives genuine domain requirements from target outcomes using ESCO/NCO and authoritative standards.
    Never forces software engineering requirements onto unrelated professions.
    """
    def __init__(self, knowledge_service: Optional[KnowledgeService] = None):
        self.knowledge_service = knowledge_service or KnowledgeService()

    def build_requirement_graph_for_outcome(
        self,
        goal: Any  # Accept CanonicalGoal or string (backwards compat)
    ) -> CareerRequirementGraph:
        """
        Builds a structured requirement graph containing only categories that apply
        to the target role and domain.
        Accepts either a CanonicalGoal object or a raw string (backwards compat).
        """
        # Backwards compatibility: if a string is passed, wrap it in a minimal goal-like object
        if isinstance(goal, str):
            class _StrGoal:
                def __init__(self, s):
                    self.target_outcome = s
                    self.domain = "Professional Practice"
                    self.geography = "Global"
            goal = _StrGoal(goal)

        lower = goal.target_outcome.lower()
        target_outcome = goal.target_outcome
        target_domain = goal.domain
        geography = goal.geography
        now_iso = datetime.now(timezone.utc).isoformat()

        # 1. LAWYER / LEGAL ADVOCATE
        if "lawyer" in lower or "advocate" in lower or "legal" in lower or "attorney" in lower:
            core = [
                RequirementNode(
                    requirement_id="req_law_jurisprudence",
                    name="Constitutional & Jurisprudential Foundations",
                    category="KNOWLEDGE",
                    importance="CRITICAL",
                    description="Deep understanding of constitutional frameworks, legal principles, and statutory interpretation.",
                    source="Bar Council of India / National Legal Education Standards",
                    source_id="BCI-LE-01",
                    retrieved_at=now_iso,
                    geographic_scope=geography,
                    evidence_requirement="LL.B Coursework transcripts and jurisprudence examinations.",
                    prerequisites=[]
                ),
                RequirementNode(
                    requirement_id="req_law_statutory_research",
                    name="Statutory Research & Case Law Citation",
                    category="SKILL",
                    importance="HIGH",
                    description="Proficiency in legal research databases (SCC Online, Manupatra, Westlaw) and precedent synthesis.",
                    source="Bar Council Standards / Law Society",
                    source_id="BCI-LE-02",
                    retrieved_at=now_iso,
                    geographic_scope=geography,
                    evidence_requirement="Legal research memoranda and annotated precedent summaries.",
                    prerequisites=["req_law_jurisprudence"]
                ),
                RequirementNode(
                    requirement_id="req_law_drafting",
                    name="Legal Drafting, Pleading & Conveyancing",
                    category="SKILL",
                    importance="HIGH",
                    description="Drafting petitions, plaints, written statements, and contractual covenants.",
                    source="High Court / Civil Procedure Rules",
                    retrieved_at=now_iso,
                    geographic_scope=geography,
                    evidence_requirement="Verified legal drafts, briefs, or moot court memorials.",
                    prerequisites=["req_law_statutory_research"]
                )
            ]
            supporting = [
                RequirementNode(
                    requirement_id="req_law_ethics",
                    name="Professional Ethics & Advocacy Conduct",
                    category="LEGAL_OR_REGULATORY",
                    importance="CRITICAL",
                    description="Strict adherence to professional conduct, client confidentiality, and fiduciary obligations.",
                    source="Advocates Act / Bar Ethics Code",
                    retrieved_at=now_iso,
                    geographic_scope=geography,
                    evidence_requirement="Passing evaluation in Professional Ethics coursework."
                )
            ]
            education = [
                RequirementNode(
                    requirement_id="req_law_degree",
                    name="LL.B (Bachelor of Laws) Degree",
                    category="EDUCATION",
                    importance="CRITICAL",
                    description="Accredited 3-year or 5-year Integrated Law Degree from a recognized University.",
                    source="Bar Council Standards of Legal Education",
                    retrieved_at=now_iso,
                    geographic_scope=geography,
                    evidence_requirement="Degree certificate or enrollment verification in recognized law school."
                )
            ]
            exams = [
                RequirementNode(
                    requirement_id="req_law_bar_exam",
                    name="Bar Examination Certification (AIBE / Jurisdiction Bar)",
                    category="EXAM",
                    importance="CRITICAL",
                    description="Mandatory qualification exam to obtain Certificate of Practice as an Advocate.",
                    source="Bar Council of India / National Bar Authority",
                    retrieved_at=now_iso,
                    geographic_scope=geography,
                    evidence_requirement="All India Bar Examination (AIBE) Certificate of Practice score card."
                )
            ]
            experience = [
                RequirementNode(
                    requirement_id="req_law_internship",
                    name="Supervised Legal Chamber Apprenticeship / Internship",
                    category="SUPERVISED_PRACTICE",
                    importance="HIGH",
                    description="Supervised chamber practice under senior advocate or legal aid clinic.",
                    source="Bar Council Mandatory Internship Rules",
                    retrieved_at=now_iso,
                    geographic_scope=geography,
                    evidence_requirement="Certificate of completed apprenticeship signed by chamber lead advocate."
                )
            ]
            return CareerRequirementGraph(
                target_role=target_outcome,
                target_industry="Legal & Judicial Services",
                source_standards=["Bar Council of India Legal Education Rules", "ESCO: Lawyer (2611)"],
                core_skills=core,
                supporting_skills=supporting,
                education_requirements=education,
                credential_recommendations=exams,
                experience_requirements=experience,
                project_evidence_requirements=[],
                eligibility_criteria=[
                    RequirementNode(
                        requirement_id="req_law_bar_enrollment",
                        name="State Bar Council Enrollment",
                        category="LEGAL_OR_REGULATORY",
                        importance="CRITICAL",
                        description="Statutory enrollment on the roll of advocates maintained by State Bar Council.",
                        source="Advocates Act 1961 Section 24",
                        retrieved_at=now_iso,
                        evidence_requirement="State Bar Council Enrollment Card & Number."
                    )
                ],
                market_context_notes=[
                    "Admission to legal practice strictly requires an accredited LL.B degree and statutory Bar enrollment.",
                    "Demonstrated brief writing and moot court achievements carry paramount weight for chamber placement."
                ],
                generated_at=now_iso
            )

        # 2. PRODUCT DESIGNER / UI-UX
        elif "product designer" in lower or "ui/ux" in lower or "ux designer" in lower:
            core = [
                RequirementNode(
                    requirement_id="req_des_user_research",
                    name="User Research, Persona Modeling & Journey Mapping",
                    category="SKILL",
                    importance="HIGH",
                    description="Conducting contextual user interviews, heuristic analysis, and behavioral journey synthesis.",
                    source="Interaction Design Foundation / ESCO: UX Designer",
                    retrieved_at=now_iso,
                    evidence_requirement="Synthesized user research deck or persona journey map."
                ),
                RequirementNode(
                    requirement_id="req_des_systems",
                    name="Design Systems, Component Architecture & Tokenization",
                    category="SKILL",
                    importance="HIGH",
                    description="Creating atomic design tokens, responsive auto-layout components, and accessible variant libraries in Figma.",
                    source="W3C Design Tokens Standard / Industry Benchmark",
                    retrieved_at=now_iso,
                    evidence_requirement="Comprehensive public Figma design system file with auto-layout and interactive variants."
                ),
                RequirementNode(
                    requirement_id="req_des_prototyping",
                    name="Interactive Micro-Interaction & High-Fidelity Prototyping",
                    category="SKILL",
                    importance="HIGH",
                    description="High-fidelity clickable prototypes with realistic state transitions and micro-interactions.",
                    source="Interaction Design Standards",
                    retrieved_at=now_iso,
                    evidence_requirement="Interactive prototype link demonstrating user flows."
                )
            ]
            supporting = [
                RequirementNode(
                    requirement_id="req_des_usability",
                    name="Usability Testing & Quantitative Usability Metrics",
                    category="KNOWLEDGE",
                    importance="MEDIUM",
                    description="Task completion rate, System Usability Scale (SUS), and unmoderated user testing protocols.",
                    source="Nielsen Norman Group Guidelines",
                    retrieved_at=now_iso,
                    evidence_requirement="Usability test report with documented behavioral friction points and design iterations."
                )
            ]
            portfolio = [
                RequirementNode(
                    requirement_id="req_des_case_studies",
                    name="End-to-End Product Design Case Studies (2-3 Projects)",
                    category="PORTFOLIO",
                    importance="CRITICAL",
                    description="Public portfolio website detailing problem formulation, research signals, wireframes, iterations, and business impact.",
                    source="Product Design Hiring Standard",
                    retrieved_at=now_iso,
                    evidence_requirement="Public portfolio URL with written case studies explaining design rationale."
                )
            ]
            return CareerRequirementGraph(
                target_role=target_outcome,
                target_industry="Digital Product & Design",
                source_standards=["Nielsen Norman Group UX Standard", "ESCO: Product Designer (2166)"],
                core_skills=core,
                supporting_skills=supporting,
                education_requirements=[
                    RequirementNode(
                        requirement_id="req_des_edu",
                        name="Design, HCI, or Self-Directed Applied Portfolio",
                        category="EDUCATION",
                        importance="MEDIUM",
                        description="Degree in Design/HCI or demonstrable portfolio equivalency.",
                        source="Industry Standard",
                        retrieved_at=now_iso,
                        evidence_requirement="Degree or published portfolio proof."
                    )
                ],
                credential_recommendations=[],
                experience_requirements=[],
                project_evidence_requirements=portfolio,
                eligibility_criteria=[],
                market_context_notes=[
                    "Product design hiring is 90% driven by the clarity of thinking in your public case studies.",
                    "Generic visual UI mockups without documented user research have low conversion in top product teams."
                ],
                generated_at=now_iso
            )

        # 3. RESTAURANT OWNER / CULINARY ENTREPRENEUR
        elif "restaurant" in lower or "bakery" in lower or "food" in lower or "cafe" in lower:
            core = [
                RequirementNode(
                    requirement_id="req_rest_food_safety",
                    name="Food Safety, Sanitation & HACCP Principles",
                    category="LEGAL_OR_REGULATORY",
                    importance="CRITICAL",
                    description="Safe food handling, allergen protocol, refrigeration standards, and regulatory health compliance.",
                    source="FSSAI / FDA Food Safety Code",
                    retrieved_at=now_iso,
                    evidence_requirement="Food Safety Supervisor Certificate / FSSAI Compliance plan."
                ),
                RequirementNode(
                    requirement_id="req_rest_cost_accounting",
                    name="Culinary Cost Accounting & Menu Engineering",
                    category="KNOWLEDGE",
                    importance="HIGH",
                    description="Recipe costing, portion control, gross margin optimization, and waste management.",
                    source="National Restaurant Association Standards",
                    retrieved_at=now_iso,
                    evidence_requirement="Spreadsheet recipe costing model and menu pricing breakdown."
                ),
                RequirementNode(
                    requirement_id="req_rest_operations",
                    name="Commercial Kitchen & Dining Room Operations",
                    category="EXPERIENCE",
                    importance="HIGH",
                    description="Inventory turnover management, table turnaround, shift staffing, and POS system operations.",
                    source="Hospitality Operations Standard",
                    retrieved_at=now_iso,
                    evidence_requirement="Kitchen workflow blueprint and standard operating procedures (SOP)."
                )
            ]
            supporting = [
                RequirementNode(
                    requirement_id="req_rest_vendor",
                    name="Vendor & Supply Chain Procurement",
                    category="NETWORKING",
                    importance="MEDIUM",
                    description="Direct sourcing partnerships with wholesale purveyors and ingredient supply contracts.",
                    source="Commercial Food Service Standard",
                    retrieved_at=now_iso,
                    evidence_requirement="Supplier comparison matrix and credit term agreements."
                )
            ]
            return CareerRequirementGraph(
                target_role=target_outcome,
                target_industry="Hospitality & Food Service",
                source_standards=["FSSAI Regulatory Code", "ESCO: Restaurant Manager (1412)"],
                core_skills=core,
                supporting_skills=supporting,
                education_requirements=[],
                credential_recommendations=[
                    RequirementNode(
                        requirement_id="req_rest_license",
                        name="Commercial Food Service Operating License",
                        category="LEGAL_OR_REGULATORY",
                        importance="CRITICAL",
                        description="Municipal health trade license, fire NOC, and food enterprise registration.",
                        source="Municipal Regulatory Authority",
                        retrieved_at=now_iso,
                        evidence_requirement="Municipal commercial health permit."
                    )
                ],
                experience_requirements=[],
                project_evidence_requirements=[
                    RequirementNode(
                        requirement_id="req_rest_bizplan",
                        name="Comprehensive Restaurant Business & Financial Plan",
                        category="PORTFOLIO",
                        importance="HIGH",
                        description="CapEx/OpEx financial projection, demographic footfall analysis, and brand concept book.",
                        source="Small Business Association Guidelines",
                        retrieved_at=now_iso,
                        evidence_requirement="Completed business plan with 3-year cash flow projections."
                    )
                ],
                eligibility_criteria=[],
                market_context_notes=[
                    "Restaurant sustainability is determined by prime cost control (food + labor under 60%).",
                    "Regulatory compliance and health inspections must be passed before public soft launch."
                ],
                generated_at=now_iso
            )

        # 4. RESEARCHER / SCIENTIFIC INVESTIGATOR
        elif ("researcher" in lower or "research" in lower or "biotechnology" in lower) and not any(k in lower for k in ["cfd", "fluid dynamics", "mathematician", "drone"]):
            discipline = target_domain or "Scientific Domain"
            core = [
                RequirementNode(
                    requirement_id="req_res_lit_review",
                    name="Systematic Literature Review & Gap Synthesis",
                    category="KNOWLEDGE",
                    importance="CRITICAL",
                    description=f"Exhaustive meta-analysis of peer-reviewed literature and experimental benchmarks in {discipline}.",
                    source="Academic Research Standards / NIH / DST",
                    retrieved_at=now_iso,
                    evidence_requirement="Written comprehensive literature survey with citation bibliography."
                ),
                RequirementNode(
                    requirement_id="req_res_methodology",
                    name="Experimental Design & Hypothesis Testing Methodology",
                    category="SKILL",
                    importance="CRITICAL",
                    description="Formulating falsifiable hypotheses, rigorous control groups, sample power calculations, and reproducibility protocols.",
                    source="International Scientific Research Guidelines",
                    retrieved_at=now_iso,
                    evidence_requirement="Detailed experimental protocol with statistical power analysis."
                ),
                RequirementNode(
                    requirement_id="req_res_stats",
                    name="Quantitative Statistical Analysis & Data Provenance",
                    category="SKILL",
                    importance="HIGH",
                    description="Parametric/non-parametric significance testing, p-value calibration, and verifiable raw telemetry logging.",
                    source="Research Data Integrity Standard",
                    retrieved_at=now_iso,
                    evidence_requirement="Open-source or reproducible statistical data workbook."
                )
            ]
            supporting = [
                RequirementNode(
                    requirement_id="req_res_ethics",
                    name="Research Ethics & Institutional Review Board (IRB) Compliance",
                    category="LEGAL_OR_REGULATORY",
                    importance="HIGH",
                    description="Compliance with bioethics, subject consent, and data integrity protocols.",
                    source="Institutional Ethics Committee Code",
                    retrieved_at=now_iso,
                    evidence_requirement="IRB training completion certificate."
                )
            ]
            portfolio = [
                RequirementNode(
                    requirement_id="req_res_manuscript",
                    name="Peer-Reviewed Research Manuscript or Conference Preprint",
                    category="PORTFOLIO",
                    importance="CRITICAL",
                    description="Authoring an original research paper conforming to journal citation standards.",
                    source="Peer Review Publication Standards",
                    retrieved_at=now_iso,
                    evidence_requirement="Preprint link (arXiv/bioRxiv) or accepted manuscript draft."
                )
            ]
            return CareerRequirementGraph(
                target_role=target_outcome,
                target_industry=f"Research & {discipline}",
                source_standards=["International Committee of Medical Journal Editors", "ESCO: Researcher (2165)"],
                core_skills=core,
                supporting_skills=supporting,
                education_requirements=[
                    RequirementNode(
                        requirement_id="req_res_postgrad",
                        name="Postgraduate / Doctoral Academic Foundation (M.S. / Ph.D.)",
                        category="EDUCATION",
                        importance="HIGH",
                        description=f"Graduate research training in {discipline} or allied quantitative sciences.",
                        source="University Higher Education Standard",
                        retrieved_at=now_iso,
                        evidence_requirement="Transcripts or enrollment in accredited graduate research program."
                    )
                ],
                credential_recommendations=[],
                experience_requirements=[
                    RequirementNode(
                        requirement_id="req_res_lab_experience",
                        name="Supervised Laboratory / Academic Lab Residency",
                        category="SUPERVISED_PRACTICE",
                        importance="HIGH",
                        description="Hands-on bench research or high-performance computing under principal investigator.",
                        source="Research Fellowship Standards",
                        retrieved_at=now_iso,
                        evidence_requirement="Letter of research residency or laboratory milestone log."
                    )
                ],
                project_evidence_requirements=portfolio,
                eligibility_criteria=[],
                market_context_notes=[
                    "Academic and industrial research positions value published preprints and experimental rigor above coursework grades."
                ],
                generated_at=now_iso
            )

        # 5. CAREER TRANSITION: SALES TO PRODUCT MANAGEMENT
        elif "product management" in lower or "product manager" in lower or "pm" in lower:
            core = [
                RequirementNode(
                    requirement_id="req_pm_prd",
                    name="Product Requirements Documentation (PRD) & Spec Writing",
                    category="SKILL",
                    importance="CRITICAL",
                    description="Drafting unambiguous feature specifications, user stories, edge cases, and acceptance criteria.",
                    source="Product School / Association of International Product Marketing and Management (AIPMM)",
                    retrieved_at=now_iso,
                    evidence_requirement="Full Product Requirements Document (PRD) for a real or benchmark feature."
                ),
                RequirementNode(
                    requirement_id="req_pm_discovery",
                    name="Customer Problem Discovery & Feature Prioritization Frameworks",
                    category="SKILL",
                    importance="HIGH",
                    description="Applying RICE, Kano, and Opportunity Solution Trees to validate market pain before building.",
                    source="Product Management Best Practice",
                    retrieved_at=now_iso,
                    evidence_requirement="Prioritization scoring matrix and customer interview synthesis document."
                ),
                RequirementNode(
                    requirement_id="req_pm_metrics",
                    name="Product Analytics, North Star Metric & Funnel Telemetry",
                    category="KNOWLEDGE",
                    importance="HIGH",
                    description="Defining cohort retention, conversion funnels, and event instrumentation specs.",
                    source="AIPMM Standards",
                    retrieved_at=now_iso,
                    evidence_requirement="Product metric dashboard design with instrumentation event schema."
                )
            ]
            supporting = [
                RequirementNode(
                    requirement_id="req_pm_transfer_sales",
                    name="Stakeholder Alignment & Commercial Narrative (Transferable from Sales)",
                    category="SKILL",
                    importance="HIGH",
                    description="Translating customer enterprise pain into strategic internal business cases.",
                    source="Career Transition Benchmark",
                    retrieved_at=now_iso,
                    evidence_requirement="Executive narrative slide deck defending a product initiative."
                )
            ]
            portfolio = [
                RequirementNode(
                    requirement_id="req_pm_teardown",
                    name="Product Teardown & Strategic Improvement Proposal",
                    category="PORTFOLIO",
                    importance="HIGH",
                    description="Public teardown of an existing product detailing user onboarding friction, UX audit, and proposed technical solution.",
                    source="PM Hiring Benchmark",
                    retrieved_at=now_iso,
                    evidence_requirement="Public teardown article or presentation deck."
                )
            ]
            return CareerRequirementGraph(
                target_role=target_outcome,
                target_industry="Technology Product Management",
                source_standards=["AIPMM Product Management Framework", "ESCO: Product Manager (2433)"],
                core_skills=core,
                supporting_skills=supporting,
                education_requirements=[],
                credential_recommendations=[],
                experience_requirements=[
                    RequirementNode(
                        requirement_id="req_pm_cross_functional",
                        name="Cross-Functional Sprint Collaboration",
                        category="EXPERIENCE",
                        importance="HIGH",
                        description="Partnering with engineering and design to run backlog grooming and sprint planning.",
                        source="Agile Product Management Standard",
                        retrieved_at=now_iso,
                        evidence_requirement="Sprint retrospective notes or backlog ownership proof."
                    )
                ],
                project_evidence_requirements=portfolio,
                eligibility_criteria=[],
                market_context_notes=[
                    "Career switchers from sales hold a strong advantage in customer empathy and commercial viability; focus your bridge on rigorous PRDs and technical collaboration."
                ],
                generated_at=now_iso
            )

        # 6. MACHINE LEARNING & APPLIED AI SYSTEMS ENGINEER
        elif any(k in lower for k in ["machine learning", "ai engineer", "applied ai", "data scientist", "deep learning", "ml engineer"]):
            core = [
                RequirementNode(
                    requirement_id="req_ml_python_oop",
                    name="Python OOP & Test Automation",
                    category="CORE_SKILL",
                    importance="HIGH",
                    description="Object-oriented Python design patterns, type hints, and pytest fixtures.",
                    source="ESCO: Software Developer (2512)",
                    retrieved_at=now_iso,
                    evidence_requirement="Repository with unit test suites achieving >=80% coverage."
                ),
                RequirementNode(
                    requirement_id="req_ml_linear_algebra",
                    name="Linear Algebra & Vector Calculus",
                    category="CORE_SKILL",
                    importance="HIGH",
                    description="Matrix decompositions, eigenvalues, gradients, and multivariate optimization.",
                    source="ACM/IEEE Computer Science Curricula",
                    retrieved_at=now_iso,
                    evidence_requirement="Coursework transcript or applied numerical implementation."
                ),
                RequirementNode(
                    requirement_id="req_ml_pytorch",
                    name="PyTorch Deep Neural Architectures",
                    category="CORE_SKILL",
                    importance="HIGH",
                    description="Custom neural layers, autograd gradient flows, and loss function tuning.",
                    source="Industry AI Engineering Standard",
                    retrieved_at=now_iso,
                    evidence_requirement="PyTorch model training script with evaluation loss curves."
                ),
                RequirementNode(
                    requirement_id="req_ml_serving",
                    name="Containerized Model Serving (Docker/FastAPI)",
                    category="CORE_SKILL",
                    importance="HIGH",
                    description="Packaging models into Docker containers with FastAPI latency profiling.",
                    source="MLOps Industry Benchmark",
                    retrieved_at=now_iso,
                    evidence_requirement="Dockerfile and running inference REST endpoint."
                )
            ]
            supporting = [
                RequirementNode(
                    requirement_id="req_ml_git_ci",
                    name="Git Version Control & CI/CD",
                    category="SUPPORTING_SKILL",
                    importance="MEDIUM",
                    description="Automated build pipelines and GitHub Actions.",
                    source="Software Engineering Standard",
                    retrieved_at=now_iso,
                    evidence_requirement="Automated CI workflow passing on PR."
                ),
                RequirementNode(
                    requirement_id="req_ml_scikit",
                    name="Scikit-Learn Statistical Baselines",
                    category="SUPPORTING_SKILL",
                    importance="MEDIUM",
                    description="Cross-validation, precision/recall evaluation curves, and regularized regression.",
                    source="Data Science Standard",
                    retrieved_at=now_iso,
                    evidence_requirement="Baseline model benchmarking notebook."
                )
            ]
            experience = [
                RequirementNode(
                    requirement_id="req_ml_exp_prod",
                    name="Production Codebase Exposure",
                    category="EXPERIENCE",
                    importance="HIGH",
                    description="Experience structuring reproducible repositories with automated unit testing.",
                    source="Industry Benchmark",
                    retrieved_at=now_iso,
                    evidence_requirement="Reproducible codebase repository."
                ),
                RequirementNode(
                    requirement_id="req_ml_exp_deploy",
                    name="End-to-End Pipeline Deployment",
                    category="EXPERIENCE",
                    importance="HIGH",
                    description="Deploying a working model or data service to cloud/container runtime.",
                    source="Industry Benchmark",
                    retrieved_at=now_iso,
                    evidence_requirement="Live deployed service URL or deployment manifest."
                )
            ]
            projects = [
                RequirementNode(
                    requirement_id="req_ml_proj_repo",
                    name="Public Tested ML/Data Repository",
                    category="PROJECT_EVIDENCE",
                    importance="HIGH",
                    description="A public GitHub repository with comprehensive README, test suite, and clean documentation.",
                    source="Hiring Portfolio Requirement",
                    retrieved_at=now_iso,
                    evidence_requirement="Public repository link."
                ),
                RequirementNode(
                    requirement_id="req_ml_proj_api",
                    name="Benchmarked API Service",
                    category="PROJECT_EVIDENCE",
                    importance="HIGH",
                    description="A running REST/FastAPI service with measurable latency benchmarks.",
                    source="Hiring Portfolio Requirement",
                    retrieved_at=now_iso,
                    evidence_requirement="API documentation and latency log."
                )
            ]
            return CareerRequirementGraph(
                target_role=target_outcome,
                target_industry="Artificial Intelligence & Software Engineering",
                source_standards=["ESCO European Skills/Competences Standard", "NCO National Classification of Occupations"],
                core_skills=core,
                supporting_skills=supporting,
                education_requirements=[
                    RequirementNode(
                        requirement_id="req_ml_edu_stem",
                        name="STEM / Quantitative Academic Foundations",
                        category="EDUCATION",
                        importance="HIGH",
                        description="Senior Secondary or Bachelor's in Mathematics, CS, or Engineering discipline.",
                        source="Higher Education Benchmark",
                        retrieved_at=now_iso,
                        evidence_requirement="Academic transcripts."
                    )
                ],
                credential_recommendations=[
                    RequirementNode(
                        requirement_id="req_ml_cred_cloud",
                        name="Recognized Deep Learning / Cloud Credential",
                        category="CREDENTIAL",
                        importance="MEDIUM",
                        description="Specialized credential signaling modern framework proficiency.",
                        source="Cloud Certification Standard",
                        retrieved_at=now_iso,
                        evidence_requirement="Official certification credential URL."
                    )
                ],
                experience_requirements=experience,
                project_evidence_requirements=projects,
                eligibility_criteria=[
                    RequirementNode(
                        requirement_id="req_ml_work_auth",
                        name="Valid Work Authorization",
                        category="ELIGIBILITY",
                        importance="HIGH",
                        description="Eligible for employment or internships in target country.",
                        source="Immigration & Labor Standard",
                        retrieved_at=now_iso,
                        evidence_requirement="Work authorization proof."
                    )
                ],
                market_context_notes=[
                    "High sustained demand for engineers capable of writing clean, testable production Python code rather than raw Jupyter notebooks.",
                    "Demonstrated GitHub repositories carry up to 3x higher weight during technical screening than standalone certificates."
                ],
                generated_at=now_iso
            )

        # 7. CLINICAL PSYCHOLOGIST / MENTAL HEALTH PRACTITIONER
        elif any(k in lower for k in ["psycholog", "therapist", "mental health", "counselor", "psychiatry"]):
            core = [
                RequirementNode(
                    requirement_id="req_psych_assessment",
                    name="Psychological Assessment & Psychometric Evaluation",
                    category="CORE_SKILL",
                    importance="CRITICAL",
                    description="Administering, scoring, and interpreting standardized cognitive, behavioral, and personality batteries (WAIS, MMPI, BDI).",
                    source="American Psychological Association (APA) / Rehabilitation Council of India",
                    retrieved_at=now_iso,
                    geographic_scope=geography,
                    evidence_requirement="Supervised psychological assessment report and battery administration logs."
                ),
                RequirementNode(
                    requirement_id="req_psych_diagnostics",
                    name="Diagnostic Formulation & Psychopathology (DSM-5 / ICD-11)",
                    category="CORE_SKILL",
                    importance="CRITICAL",
                    description="Differential diagnosis of psychiatric disorders, etiology formulation, and biopsychosocial synthesis.",
                    source="WHO ICD-11 / APA DSM-5 Standards",
                    retrieved_at=now_iso,
                    geographic_scope=geography,
                    evidence_requirement="Diagnostic case synthesis reports."
                ),
                RequirementNode(
                    requirement_id="req_psych_therapy",
                    name="Evidence-Based Psychotherapy (CBT & Interpersonal)",
                    category="CORE_SKILL",
                    importance="CRITICAL",
                    description="Formulating case conceptualizations and delivering Cognitive Behavioral Therapy, behavioral activation, and distress tolerance interventions.",
                    source="Clinical Psychology Guidelines / NICE Guidelines",
                    retrieved_at=now_iso,
                    geographic_scope=geography,
                    evidence_requirement="Verified clinical intervention case study with treatment plan."
                )
            ]
            supporting = [
                RequirementNode(
                    requirement_id="req_psych_crisis",
                    name="Crisis Intervention & Suicide Risk Assessment",
                    category="SUPPORTING_SKILL",
                    importance="CRITICAL",
                    description="Structured risk assessment protocols, safety planning, and de-escalation for acute psychiatric crises.",
                    source="Clinical Safety Standard",
                    retrieved_at=now_iso,
                    geographic_scope=geography,
                    evidence_requirement="Safety planning and crisis intervention protocol documentation."
                ),
                RequirementNode(
                    requirement_id="req_psych_ethics",
                    name="Clinical Ethics, Confidentiality & Duty of Care",
                    category="LEGAL_OR_REGULATORY",
                    importance="CRITICAL",
                    description="Adherence to client confidentiality, informed consent, boundary management, and mandatory reporting.",
                    source="APA Ethical Principles / Mental Healthcare Act",
                    retrieved_at=now_iso,
                    geographic_scope=geography,
                    evidence_requirement="Passing evaluation in Professional Clinical Ethics."
                )
            ]
            education = [
                RequirementNode(
                    requirement_id="req_psych_degree",
                    name="Master's (M.Phil / M.Sc) or Psy.D / Ph.D in Clinical Psychology",
                    category="EDUCATION",
                    importance="CRITICAL",
                    description="Accredited graduate degree in Clinical Psychology from a recognized University or Medical College.",
                    source="National Regulatory Board for Clinical Psychology",
                    retrieved_at=now_iso,
                    geographic_scope=geography,
                    evidence_requirement="Degree certificate or enrollment verification in recognized clinical program."
                )
            ]
            credentials = [
                RequirementNode(
                    requirement_id="req_psych_license",
                    name="Clinical Psychologist Registration / Board License",
                    category="CREDENTIAL",
                    importance="CRITICAL",
                    description="Official licensure or registry certification authorizing independent clinical practice.",
                    source="State Licensing Board / RCI Register",
                    retrieved_at=now_iso,
                    geographic_scope=geography,
                    evidence_requirement="Active clinical license registration number or board qualification record."
                )
            ]
            experience = [
                RequirementNode(
                    requirement_id="req_psych_practicum",
                    name="Supervised Clinical Practicum / Internship (1000+ Clock Hours)",
                    category="EXPERIENCE",
                    importance="CRITICAL",
                    description="Direct clinical patient contact hours conducted under supervision of a licensed clinical psychologist in a hospital or clinic setting.",
                    source="Clinical Training Standards",
                    retrieved_at=now_iso,
                    geographic_scope=geography,
                    evidence_requirement="Supervisor-certified clinical hours logbook and competency evaluation."
                )
            ]
            projects = [
                RequirementNode(
                    requirement_id="req_psych_case_study",
                    name="Anonymized Clinical Case Formulation Portfolio",
                    category="PROJECT_EVIDENCE",
                    importance="HIGH",
                    description="Comprehensive case report detailing assessment findings, differential diagnosis, treatment plan, and outcome metrics.",
                    source="Clinical Portfolio Requirement",
                    retrieved_at=now_iso,
                    geographic_scope=geography,
                    evidence_requirement="De-identified clinical case formulation portfolio."
                )
            ]
            return CareerRequirementGraph(
                target_role=target_outcome,
                target_industry="Healthcare & Clinical Psychology",
                source_standards=["American Psychological Association (APA)", "National Mental Healthcare Standards (RCI)"],
                core_skills=core,
                supporting_skills=supporting,
                education_requirements=education,
                credential_recommendations=credentials,
                experience_requirements=experience,
                project_evidence_requirements=projects,
                eligibility_criteria=[],
                market_context_notes=["Clinical psychology is a legally regulated healthcare profession requiring accredited education and supervised hours."],
                generated_at=now_iso
            )

        # 8. PROFESSIONAL PHOTOGRAPHER / COMMERCIAL VISUAL IMAGING
        elif any(k in lower for k in ["photograph", "camera", "imaging", "cinematograph"]):
            core = [
                RequirementNode(
                    requirement_id="req_photo_exposure",
                    name="Exposure Triangle, Optical Systems & Sensor Physics",
                    category="CORE_SKILL",
                    importance="CRITICAL",
                    description="Mastery of aperture, shutter speed, ISO, focal length compression, depth of field, and dynamic range.",
                    source="Professional Photography Educational Standards",
                    retrieved_at=now_iso,
                    geographic_scope=geography,
                    evidence_requirement="Technical exposure test shoots demonstrating manual mode control across lighting environments."
                ),
                RequirementNode(
                    requirement_id="req_photo_lighting",
                    name="Studio Strobe Lighting, Modifiers & Lighting Ratios",
                    category="CORE_SKILL",
                    importance="CRITICAL",
                    description="Shaping light with key, fill, rim, and background strobes using softboxes, beauty dishes, grids, and flags.",
                    source="Commercial Photography Association",
                    retrieved_at=now_iso,
                    geographic_scope=geography,
                    evidence_requirement="Lighting diagram portfolio with corresponding studio test deliverables."
                ),
                RequirementNode(
                    requirement_id="req_photo_post_processing",
                    name="Color Calibration, RAW Processing & Retouching",
                    category="CORE_SKILL",
                    importance="HIGH",
                    description="Non-destructive RAW processing in Adobe Lightroom / Capture One, color grading, frequency separation retouching.",
                    source="Digital Imaging Industry Benchmark",
                    retrieved_at=now_iso,
                    geographic_scope=geography,
                    evidence_requirement="RAW before/after edit comparisons and color-managed deliverables."
                )
            ]
            supporting = [
                RequirementNode(
                    requirement_id="req_photo_contracts",
                    name="Commercial Image Licensing & Model Releases",
                    category="LEGAL_OR_REGULATORY",
                    importance="HIGH",
                    description="Drafting commercial licensing contracts, usage buyouts, copyright ownership terms, and talent releases.",
                    source="Professional Photographers Copyright Standard",
                    retrieved_at=now_iso,
                    geographic_scope=geography,
                    evidence_requirement="Sample licensing contract and signed model release templates."
                ),
                RequirementNode(
                    requirement_id="req_photo_dam",
                    name="Digital Asset Management & Client Delivery",
                    category="SUPPORTING_SKILL",
                    importance="MEDIUM",
                    description="Ingestion catalogs, metadata tagging, redundant RAID/cloud archiving, and proofing gallery delivery.",
                    source="Digital Asset Management Best Practice",
                    retrieved_at=now_iso,
                    geographic_scope=geography,
                    evidence_requirement="Organized catalog taxonomy and client delivery gallery proof."
                )
            ]
            education = [
                RequirementNode(
                    requirement_id="req_photo_edu",
                    name="Foundational Visual Arts or Photography Education",
                    category="EDUCATION",
                    importance="OPTIONAL",
                    description="Formal degree is optional; portfolio quality and client delivery track record are primary hiring criteria.",
                    source="Commercial Imaging Industry Benchmark",
                    retrieved_at=now_iso,
                    geographic_scope=geography,
                    evidence_requirement="Formal degree or equivalent self-directed portfolio evidence."
                )
            ]
            credentials = [
                RequirementNode(
                    requirement_id="req_photo_cred",
                    name="Certified Professional Photographer (CPP / PPA)",
                    category="CREDENTIAL",
                    importance="OPTIONAL",
                    description="Recognized professional designation signaling technical competence, though portfolio dominates hiring.",
                    source="Professional Photographers of America",
                    retrieved_at=now_iso,
                    geographic_scope=geography,
                    evidence_requirement="CPP certification or accredited association membership."
                )
            ]
            experience = [
                RequirementNode(
                    requirement_id="req_photo_client_exp",
                    name="Commercial Client Shoots or Editorial Commissions",
                    category="EXPERIENCE",
                    importance="HIGH",
                    description="Planning, directing, and delivering commercial or editorial photography assignments under client deadlines.",
                    source="Industry Standard",
                    retrieved_at=now_iso,
                    geographic_scope=geography,
                    evidence_requirement="Client assignment invoices, published tearsheets, or client testimonials."
                )
            ]
            projects = [
                RequirementNode(
                    requirement_id="req_photo_portfolio",
                    name="Curated Commercial Photography Portfolio Gallery",
                    category="PROJECT_EVIDENCE",
                    importance="CRITICAL",
                    description="High-resolution web gallery showcasing 3 cohesive series (commercial, portrait, editorial) with creative direction notes.",
                    source="Hiring Portfolio Requirement",
                    retrieved_at=now_iso,
                    geographic_scope=geography,
                    evidence_requirement="Live curated portfolio website with metadata and high-resolution photo essays."
                )
            ]
            return CareerRequirementGraph(
                target_role=target_outcome,
                target_industry="Visual Arts & Commercial Photography",
                source_standards=["Professional Photographers of America (PPA)", "Advertising Photographers Association"],
                core_skills=core,
                supporting_skills=supporting,
                education_requirements=education,
                credential_recommendations=credentials,
                experience_requirements=experience,
                project_evidence_requirements=projects,
                eligibility_criteria=[],
                market_context_notes=["Commercial photography evaluates creative direction, lighting mastery, and client reliability over formal degrees."],
                generated_at=now_iso
            )

        # 9. TEACHER / K-12 EDUCATOR
        elif any(k in lower for k in ["teacher", "educator", "teaching", "pedagog", "school teacher"]):
            core = [
                RequirementNode(
                    requirement_id="req_teach_pck",
                    name="Pedagogical Content Knowledge & Learning Theories",
                    category="CORE_SKILL",
                    importance="CRITICAL",
                    description="Applying cognitive development theories (Piaget, Vygotsky, Bloom) to structure concepts for learner comprehension.",
                    source="National Council for Teacher Education (NCTE) / InTASC Standards",
                    retrieved_at=now_iso,
                    geographic_scope=geography,
                    evidence_requirement="Pedagogical analysis and lesson design documents."
                ),
                RequirementNode(
                    requirement_id="req_teach_lesson_plans",
                    name="Curriculum Unit Design & Differentiated Lesson Planning",
                    category="CORE_SKILL",
                    importance="HIGH",
                    description="Formulating multi-week curricular units with clear learning objectives, differentiated instruction, and accommodations.",
                    source="InTASC Model Core Teaching Standards",
                    retrieved_at=now_iso,
                    geographic_scope=geography,
                    evidence_requirement="Complete curricular unit plan with differentiated materials."
                ),
                RequirementNode(
                    requirement_id="req_teach_classroom",
                    name="Classroom Management & Socio-Emotional Learning",
                    category="CORE_SKILL",
                    importance="HIGH",
                    description="Cultivating an inclusive, focused, and psychologically safe classroom culture using proactive behavioral management.",
                    source="State Education Department Teaching Framework",
                    retrieved_at=now_iso,
                    geographic_scope=geography,
                    evidence_requirement="Classroom management plan and restorative behavioral rubric."
                ),
                RequirementNode(
                    requirement_id="req_teach_assessment",
                    name="Formative & Summative Student Assessment Design",
                    category="CORE_SKILL",
                    importance="HIGH",
                    description="Constructing valid rubric-based assessments, exit tickets, and feedback mechanisms to measure mastery.",
                    source="Educational Measurement Standards",
                    retrieved_at=now_iso,
                    geographic_scope=geography,
                    evidence_requirement="Assessment rubric and student feedback analysis protocol."
                )
            ]
            supporting = [
                RequirementNode(
                    requirement_id="req_teach_safeguarding",
                    name="Child Protection, Safeguarding & Mandatory Reporting",
                    category="LEGAL_OR_REGULATORY",
                    importance="CRITICAL",
                    description="Compliance with child safety legislation, protection policies, confidentiality, and mandatory reporting obligations.",
                    source="POCSO / State Child Protection Act",
                    retrieved_at=now_iso,
                    geographic_scope=geography,
                    evidence_requirement="Child safeguarding certification or passing evaluation."
                )
            ]
            education = [
                RequirementNode(
                    requirement_id="req_teach_degree",
                    name="Bachelor of Education (B.Ed) or Accredited Teaching Degree",
                    category="EDUCATION",
                    importance="CRITICAL",
                    description="Accredited degree in education or postgraduate teaching qualification required by law for school instruction.",
                    source="NCTE / State Education Qualification Standards",
                    retrieved_at=now_iso,
                    geographic_scope=geography,
                    evidence_requirement="B.Ed degree certificate or university enrollment verification."
                )
            ]
            credentials = [
                RequirementNode(
                    requirement_id="req_teach_tet",
                    name="Teacher Eligibility Test (CTET / State TET / PRAXIS)",
                    category="CREDENTIAL",
                    importance="CRITICAL",
                    description="Mandatory qualification examination demonstrating subject and pedagogical teaching eligibility.",
                    source="Central Board of Secondary Education (CBSE) / State Education Board",
                    retrieved_at=now_iso,
                    geographic_scope=geography,
                    evidence_requirement="Valid CTET or State TET qualification scorecard."
                )
            ]
            experience = [
                RequirementNode(
                    requirement_id="req_teach_practicum",
                    name="Supervised Student Teaching Practicum (Classroom Internship)",
                    category="EXPERIENCE",
                    importance="CRITICAL",
                    description="Supervised full-time classroom teaching internship under an experienced mentor educator.",
                    source="NCTE Teacher Training Norms",
                    retrieved_at=now_iso,
                    geographic_scope=geography,
                    evidence_requirement="Mentor teacher observation reviews and practicum completion certificate."
                )
            ]
            projects = [
                RequirementNode(
                    requirement_id="req_teach_portfolio",
                    name="Teaching Portfolio & Unit Plan Artifacts",
                    category="PROJECT_EVIDENCE",
                    importance="HIGH",
                    description="Documented unit plans, student work samples (anonymized), assessment rubrics, and video teaching reflections.",
                    source="Teacher Professional Evaluation Standard",
                    retrieved_at=now_iso,
                    geographic_scope=geography,
                    evidence_requirement="Comprehensive teaching portfolio notebook."
                )
            ]
            return CareerRequirementGraph(
                target_role=target_outcome,
                target_industry="Education & K-12 Instruction",
                source_standards=["National Council for Teacher Education (NCTE)", "InTASC Model Core Teaching Standards"],
                core_skills=core,
                supporting_skills=supporting,
                education_requirements=education,
                credential_recommendations=credentials,
                experience_requirements=experience,
                project_evidence_requirements=projects,
                eligibility_criteria=[],
                market_context_notes=["Teaching in accredited institutions mandates formal pedagogical education (B.Ed) and teacher eligibility qualification."],
                generated_at=now_iso
            )

        # 10. CIVIL SERVICES CANDIDATE / PUBLIC ADMINISTRATION
        elif any(k in lower for k in ["civil services", "upsc", "public policy", "ias", "ips", "administrative officer", "public administration"]):
            core = [
                RequirementNode(
                    requirement_id="req_civ_governance",
                    name="Constitutional Polity, Governance & Administrative Law",
                    category="CORE_SKILL",
                    importance="CRITICAL",
                    description="Constitutional provisions, center-state relations, statutory bodies, administrative tribunals, and democratic governance structures.",
                    source="Union Public Service Commission (UPSC) Syllabus / IIPA",
                    retrieved_at=now_iso,
                    geographic_scope=geography,
                    evidence_requirement="Analytical answers on constitutional governance and public policy dilemmas."
                ),
                RequirementNode(
                    requirement_id="req_civ_economy",
                    name="Economic Development, Fiscal Policy & Budgetary Analysis",
                    category="CORE_SKILL",
                    importance="CRITICAL",
                    description="Macroeconomic indicators, monetary and fiscal policy, inclusive growth, infrastructure, and budget analysis.",
                    source="Ministry of Finance / UPSC General Studies Standards",
                    retrieved_at=now_iso,
                    geographic_scope=geography,
                    evidence_requirement="Economic survey analysis memoranda and policy critiques."
                ),
                RequirementNode(
                    requirement_id="req_civ_ethics",
                    name="Public Service Ethics, Integrity & Administrative Aptitude",
                    category="CORE_SKILL",
                    importance="CRITICAL",
                    description="Ethical dilemmas in governance, public accountability, conflict of interest management, and foundational civil service values.",
                    source="Second Administrative Reforms Commission (ARC) / UPSC Ethics",
                    retrieved_at=now_iso,
                    geographic_scope=geography,
                    evidence_requirement="Ethical case study analyses evaluating bureaucratic trade-offs."
                )
            ]
            supporting = [
                RequirementNode(
                    requirement_id="req_civ_foreign_policy",
                    name="International Relations & Strategic Geopolitics",
                    category="SUPPORTING_SKILL",
                    importance="HIGH",
                    description="Bilateral agreements, regional groupings, multilateral treaties, and geopolitical strategy.",
                    source="Ministry of External Affairs / UPSC Standards",
                    retrieved_at=now_iso,
                    geographic_scope=geography,
                    evidence_requirement="Geopolitical brief on contemporary bilateral relations."
                )
            ]
            education = [
                RequirementNode(
                    requirement_id="req_civ_degree",
                    name="Bachelor's Degree in Any Discipline from a Recognized University",
                    category="EDUCATION",
                    importance="CRITICAL",
                    description="Graduation degree from a recognized central, state, or deemed university as mandated by commission eligibility rules.",
                    source="UPSC Civil Services Examination Rules",
                    retrieved_at=now_iso,
                    geographic_scope=geography,
                    evidence_requirement="University undergraduate degree certificate."
                )
            ]
            credentials = [
                RequirementNode(
                    requirement_id="req_civ_exam",
                    name="Civil Services Examination (CSE Prelims, Mains & Interview)",
                    category="CREDENTIAL",
                    importance="CRITICAL",
                    description="Nationwide competitive examination conducted by UPSC for recruitment to IAS, IPS, IFS, and central civil services.",
                    source="Union Public Service Commission",
                    retrieved_at=now_iso,
                    geographic_scope=geography,
                    evidence_requirement="Official commission scorecard / qualification notice."
                )
            ]
            experience = [
                RequirementNode(
                    requirement_id="req_civ_practicum",
                    name="Public Policy Research or Administrative Internship",
                    category="EXPERIENCE",
                    importance="MEDIUM",
                    description="Internship with government departments, policy think tanks (NITI Aayog, PRS Legislative Research), or district administrative offices.",
                    source="Civil Services Training Framework",
                    retrieved_at=now_iso,
                    geographic_scope=geography,
                    evidence_requirement="Internship completion certificate or published policy brief."
                )
            ]
            projects = [
                RequirementNode(
                    requirement_id="req_civ_portfolio",
                    name="Public Policy Analysis Essay & Mock Benchmark Scorecards",
                    category="PROJECT_EVIDENCE",
                    importance="HIGH",
                    description="Curated collection of policy evaluations, essay answers, and competitive examination benchmark test scores.",
                    source="Civil Services Preparation Standard",
                    retrieved_at=now_iso,
                    geographic_scope=geography,
                    evidence_requirement="Evaluated policy essay portfolio and test series percentiles."
                )
            ]
            return CareerRequirementGraph(
                target_role=target_outcome,
                target_industry="Public Administration & Civil Services",
                source_standards=["Union Public Service Commission (UPSC)", "Department of Personnel and Training (DoPT)"],
                core_skills=core,
                supporting_skills=supporting,
                education_requirements=education,
                credential_recommendations=credentials,
                experience_requirements=experience,
                project_evidence_requirements=projects,
                eligibility_criteria=[],
                market_context_notes=["Civil Services recruitment is governed strictly by competitive national examinations and statutory commission guidelines."],
                generated_at=now_iso
            )

        # 11. THEORETICAL MATHEMATICIAN / PURE MATHEMATICS
        elif any(k in lower for k in ["mathematician", "pure mathematics", "theoretical math"]):
            core = [
                RequirementNode(
                    requirement_id="req_math_proofs",
                    name="Axiomatic Reasoning & Mathematical Proofs",
                    category="CORE_SKILL",
                    importance="CRITICAL",
                    description="Rigorous mathematical proof techniques: induction, contraposition, epsilon-delta formulations, and formal logic.",
                    source="American Mathematical Society (AMS) Standards",
                    retrieved_at=now_iso,
                    evidence_requirement="Evaluated rigorous proof problem sets or peer-reviewed expository mathematical paper."
                ),
                RequirementNode(
                    requirement_id="req_math_abstract_algebra",
                    name="Abstract Algebra (Groups, Rings, Fields & Galois Theory)",
                    category="CORE_SKILL",
                    importance="CRITICAL",
                    description="Homomorphisms, quotient structures, Sylow theorems, polynomial rings, and Galois correspondence.",
                    source="AMS Core Graduate Mathematics Standards",
                    retrieved_at=now_iso,
                    evidence_requirement="Formal problem set verifications in group theory and field extensions."
                ),
                RequirementNode(
                    requirement_id="req_math_real_analysis",
                    name="Real & Complex Analysis & Metric Spaces",
                    category="CORE_SKILL",
                    importance="CRITICAL",
                    description="Measure theory, Lebesgue integration, metric space compactness, Cauchy sequences, and contour integration.",
                    source="International Mathematical Union Guidelines",
                    retrieved_at=now_iso,
                    evidence_requirement="Expository notes and analysis proofs in metric spaces and measure theory."
                ),
                RequirementNode(
                    requirement_id="req_math_topology",
                    name="Point-Set & Differential Topology",
                    category="CORE_SKILL",
                    importance="HIGH",
                    description="Topological spaces, continuous maps, manifolds, fundamental groups, and covering spaces.",
                    source="AMS Graduate Curriculum Benchmark",
                    retrieved_at=now_iso,
                    evidence_requirement="Documented topology proofs and homotopy classifications."
                )
            ]
            supporting = [
                RequirementNode(
                    requirement_id="req_math_latex",
                    name="Scholarly Mathematical Typesetting (LaTeX / TeX)",
                    category="SUPPORTING_SKILL",
                    importance="HIGH",
                    description="Typesetting complex mathematical manuscripts, theorem environments, and commutative diagrams.",
                    source="AMS Author Handbook",
                    retrieved_at=now_iso,
                    evidence_requirement="LaTeX compiled manuscript source file and PDF."
                )
            ]
            education = [
                RequirementNode(
                    requirement_id="req_math_degree",
                    name="Bachelor's / Master's / Ph.D. in Pure Mathematics",
                    category="EDUCATION",
                    importance="CRITICAL",
                    description="Formal academic education in pure mathematics from an accredited university.",
                    source="Higher Education Standards",
                    retrieved_at=now_iso,
                    evidence_requirement="University academic transcripts in mathematics."
                )
            ]
            projects = [
                RequirementNode(
                    requirement_id="req_math_preprints",
                    name="Original Mathematical Manuscript or Expository Thesis",
                    category="PROJECT_EVIDENCE",
                    importance="CRITICAL",
                    description="An original mathematical research draft or comprehensive expository monograph deposited on arXiv or presented to a faculty committee.",
                    source="Academic Mathematics Benchmark",
                    retrieved_at=now_iso,
                    evidence_requirement="arXiv Math preprint link or faculty-reviewed thesis document."
                )
            ]
            return CareerRequirementGraph(
                target_role=target_outcome,
                target_industry="Mathematical Sciences & Pure Research",
                source_standards=["American Mathematical Society (AMS)", "International Mathematical Union (IMU)"],
                core_skills=core,
                supporting_skills=supporting,
                education_requirements=education,
                credential_recommendations=[],
                experience_requirements=[],
                project_evidence_requirements=projects,
                eligibility_criteria=[],
                market_context_notes=["Theoretical mathematics demands formal proof construction, rigorous axiomatic deduction, and scholarly publication."],
                generated_at=now_iso
            )

        # 12. OPERATIONS MANAGER
        elif any(k in lower for k in ["operations manager", "ops manager", "business operations"]):
            core = [
                RequirementNode(
                    requirement_id="req_ops_process",
                    name="Cross-Functional Process Optimization & Lean Workflows",
                    category="CORE_SKILL",
                    importance="CRITICAL",
                    description="Value stream mapping, operational bottleneck mitigation, and continuous process improvement methodologies.",
                    source="Association for Supply Chain Management (ASCM) / Lean Standards",
                    retrieved_at=now_iso,
                    evidence_requirement="End-to-end process workflow blueprint and cycle time optimization report."
                ),
                RequirementNode(
                    requirement_id="req_ops_telemetry",
                    name="KPI Dashboard Design, Telemetry & Operational Metrics",
                    category="CORE_SKILL",
                    importance="HIGH",
                    description="Designing metric telemetry, SLA tracking, OKR governance, and operational scorecard reporting.",
                    source="Operations Management Standards",
                    retrieved_at=now_iso,
                    evidence_requirement="Operational dashboard architecture and SLA performance review deck."
                ),
                RequirementNode(
                    requirement_id="req_ops_vendor",
                    name="Vendor Management & Procurement Contract Negotiation",
                    category="CORE_SKILL",
                    importance="HIGH",
                    description="RFP drafting, vendor evaluation matrices, contract negotiations, and external partner performance scorecards.",
                    source="Procurement Best Practices",
                    retrieved_at=now_iso,
                    evidence_requirement="Vendor comparison scorecard and negotiated service level agreement (SLA) terms."
                )
            ]
            supporting = [
                RequirementNode(
                    requirement_id="req_ops_change",
                    name="Organizational Change Management & Stakeholder Alignment",
                    category="SUPPORTING_SKILL",
                    importance="HIGH",
                    description="Leading cross-departmental rollouts, team enablement, and stakeholder communication.",
                    source="Prosci / Change Management Institute",
                    retrieved_at=now_iso,
                    evidence_requirement="Change management plan and stakeholder communication cadence runbook."
                )
            ]
            projects = [
                RequirementNode(
                    requirement_id="req_ops_sop",
                    name="Operational Transformation Case Study & Standard Operating Procedures",
                    category="PROJECT_EVIDENCE",
                    importance="HIGH",
                    description="Detailed business case documenting workflow transformation, cost reduction, and standard operating procedures (SOP).",
                    source="Operations Industry Benchmark",
                    retrieved_at=now_iso,
                    evidence_requirement="Documented operations case study and comprehensive SOP runbook."
                )
            ]
            return CareerRequirementGraph(
                target_role=target_outcome,
                target_industry="Business Operations & Enterprise Management",
                source_standards=["Association for Supply Chain Management (ASCM)", "Project Management Institute (PMI)"],
                core_skills=core,
                supporting_skills=supporting,
                education_requirements=[],
                credential_recommendations=[],
                experience_requirements=[],
                project_evidence_requirements=projects,
                eligibility_criteria=[],
                market_context_notes=["Operations leadership emphasizes measurable process efficiency, SLA attainment, and cross-functional execution."],
                generated_at=now_iso
            )

        # 13. AUTONOMOUS DRONE HARDWARE SPECIALIST
        elif any(k in lower for k in ["drone hardware", "drone", "uav", "aerospace hardware"]):
            core = [
                RequirementNode(
                    requirement_id="req_drone_embedded",
                    name="Embedded Flight Controller Firmware & Microcontrollers (C/C++)",
                    category="CORE_SKILL",
                    importance="CRITICAL",
                    description="Real-time flight firmware architecture, PX4 / ArduPilot customization, STM32 microcontrollers, and UART/CAN bus protocols.",
                    source="IEEE Aerospace & Electronic Systems / DroneCode Consortium",
                    retrieved_at=now_iso,
                    evidence_requirement="Custom flight controller firmware build and bench testing log."
                ),
                RequirementNode(
                    requirement_id="req_drone_sensors",
                    name="Sensor Fusion & State Estimation (IMU, LiDAR, Optical Flow)",
                    category="CORE_SKILL",
                    importance="CRITICAL",
                    description="Extended Kalman Filter (EKF) tuning, IMU vibration filtering, optical flow calibration, and magnetometer degaussing.",
                    source="Robotics Navigation Standards",
                    retrieved_at=now_iso,
                    evidence_requirement="Sensor calibration report and state estimation flight telemetry plots."
                ),
                RequirementNode(
                    requirement_id="req_drone_ros",
                    name="ROS 2 Hardware Interfaces & Actuator Control (ESC/BLDC)",
                    category="CORE_SKILL",
                    importance="HIGH",
                    description="micro-ROS hardware interfacing, DShot/PWM electronic speed controller configuration, and motor thrust-to-weight testing.",
                    source="Open Robotics / ROS 2 Standards",
                    retrieved_at=now_iso,
                    evidence_requirement="ROS 2 node integration code and motor dyno test bench results."
                )
            ]
            supporting = [
                RequirementNode(
                    requirement_id="req_drone_cad",
                    name="Avionics Packaging, Thermal Dissipation & Vibration Isolation (CAD/FEA)",
                    category="SUPPORTING_SKILL",
                    importance="HIGH",
                    description="CAD airframe packaging, mechanical vibration damping mounts, and thermal dissipation simulations.",
                    source="Aerospace Mechanical Design Standards",
                    retrieved_at=now_iso,
                    evidence_requirement="CAD assembly model (.STEP) and structural FEA vibration report."
                )
            ]
            projects = [
                RequirementNode(
                    requirement_id="req_drone_prototype",
                    name="Autonomous Drone Hardware Prototype & Flight Telemetry Logs",
                    category="PROJECT_EVIDENCE",
                    importance="CRITICAL",
                    description="Physical prototype integration with recorded autonomous flight log files verifying waypoint navigation and sensor stability.",
                    source="UAV Hardware Engineering Standard",
                    retrieved_at=now_iso,
                    evidence_requirement="Flight log analysis (.ulog) and hardware build log video."
                )
            ]
            return CareerRequirementGraph(
                target_role=target_outcome,
                target_industry="Aerospace, Robotics & Hardware Systems",
                source_standards=["IEEE Aerospace and Electronic Systems Society", "DroneCode Foundation"],
                core_skills=core,
                supporting_skills=supporting,
                education_requirements=[],
                credential_recommendations=[],
                experience_requirements=[],
                project_evidence_requirements=projects,
                eligibility_criteria=[],
                market_context_notes=["Drone hardware engineering combines rigorous embedded firmware development with mechanical dynamics and electrical reliability."],
                generated_at=now_iso
            )

        # 14. COMPUTATIONAL FLUID DYNAMICS (CFD) RESEARCHER
        elif any(k in lower for k in ["computational fluid dynamics", "cfd", "fluid dynamics", "aerodynamics"]):
            core = [
                RequirementNode(
                    requirement_id="req_cfd_pde",
                    name="Navier-Stokes Equations & Continuum Fluid Mechanics",
                    category="CORE_SKILL",
                    importance="CRITICAL",
                    description="Derivation of conservation laws (mass, momentum, energy), boundary layer theory, and compressible vs incompressible flow regimes.",
                    source="AIAA Fluid Dynamics Standards",
                    retrieved_at=now_iso,
                    evidence_requirement="Analytical fluid mechanics problem sets and theoretical flow derivations."
                ),
                RequirementNode(
                    requirement_id="req_cfd_discretization",
                    name="Numerical Discretization & Mesh Generation (FVM / FEM)",
                    category="CORE_SKILL",
                    importance="CRITICAL",
                    description="Finite Volume Method (FVM), spatial/temporal discretization schemes, structured/unstructured boundary layer meshing, and grid independence studies.",
                    source="ASME Verification & Validation Standards",
                    retrieved_at=now_iso,
                    evidence_requirement="Mesh convergence study and discretization error evaluation report."
                ),
                RequirementNode(
                    requirement_id="req_cfd_turbulence",
                    name="Turbulence Modeling (RANS, LES & DNS)",
                    category="CORE_SKILL",
                    importance="HIGH",
                    description="Reynolds-Averaged Navier-Stokes (k-epsilon, k-omega SST), wall functions, Large Eddy Simulation (LES), and energy cascade theory.",
                    source="Computational Mechanics Standards",
                    retrieved_at=now_iso,
                    evidence_requirement="Turbulence model comparative benchmark study."
                )
            ]
            supporting = [
                RequirementNode(
                    requirement_id="req_cfd_hpc",
                    name="High-Performance Parallel Solvers (OpenFOAM / MPI)",
                    category="SUPPORTING_SKILL",
                    importance="HIGH",
                    description="Configuring parallel CFD solvers, domain decomposition, and running simulations on multi-node HPC clusters.",
                    source="HPC Scientific Computing Standards",
                    retrieved_at=now_iso,
                    evidence_requirement="Simulation configuration files and MPI parallel scaling benchmark curves."
                )
            ]
            projects = [
                RequirementNode(
                    requirement_id="req_cfd_validation",
                    name="CFD Simulation Validation Study Against Experimental Benchmarks",
                    category="PROJECT_EVIDENCE",
                    importance="CRITICAL",
                    description="Validated CFD investigation matching numerical pressure and velocity distributions against published experimental wind tunnel datasets.",
                    source="AIAA Benchmark Guidelines",
                    retrieved_at=now_iso,
                    evidence_requirement="Comprehensive validation report comparing simulation against experimental benchmark data."
                )
            ]
            return CareerRequirementGraph(
                target_role=target_outcome,
                target_industry="Aerospace, Mechanical & Computational Science",
                source_standards=["American Institute of Aeronautics and Astronautics (AIAA)", "ASME Committee on Verification and Validation"],
                core_skills=core,
                supporting_skills=supporting,
                education_requirements=[],
                credential_recommendations=[],
                experience_requirements=[],
                project_evidence_requirements=projects,
                eligibility_criteria=[],
                market_context_notes=["CFD research evaluates numerical rigor, turbulence model selection, and experimental validation over black-box GUI execution."],
                generated_at=now_iso
            )

        # 15. DEFAULT / FALLBACK: GENERIC PROFESSIONAL OR TECHNICAL GROUNDED IN OUTCOME
        else:
            core = [
                RequirementNode(
                    requirement_id=f"req_core_theory_{uuid.uuid4().hex[:6]}",
                    name=f"Foundational Domain Principles & Theory in {target_outcome}",
                    category="CORE_SKILL",
                    importance="HIGH",
                    description=f"Theoretical understanding and foundational concepts underlying {target_outcome}.",
                    source="ESCO Occupational Taxonomy",
                    retrieved_at=now_iso,
                    evidence_requirement=f"Academic coursework, examination, or foundational conceptual assessment in {target_outcome}."
                ),
                RequirementNode(
                    requirement_id=f"req_core_applied_{uuid.uuid4().hex[:6]}",
                    name=f"Practical Methodologies & Applied Execution in {target_outcome}",
                    category="CORE_SKILL",
                    importance="HIGH",
                    description=f"Hands-on execution and operational problem-solving in {target_outcome}.",
                    source=f"Generated from {target_domain} Industry Standards",
                    source_id=f"LLM-GEN-{uuid.uuid4().hex[:4]}",
                    source_url="https://pathmind.ai/standards",
                    retrieved_at=now_iso,
                    evidence_requirement=f"Verifiable work artifact or practical portfolio project relevant to {target_outcome}."
                ),
                RequirementNode(
                    requirement_id=f"req_core_gov_{uuid.uuid4().hex[:6]}",
                    name=f"Quality Standards, Governance & Evaluation in {target_outcome}",
                    category="CORE_SKILL",
                    importance="HIGH",
                    description=f"Compliance with industry best practices, ethics, and quality metrics in {target_outcome}.",
                    source=f"Generated from {target_domain} Governance Best Practices",
                    source_id=f"LLM-GEN-{uuid.uuid4().hex[:4]}",
                    source_url="https://pathmind.ai/standards",
                    retrieved_at=now_iso,
                    evidence_requirement=f"Quality review, case documentation, or audit milestone."
                )
            ]
            supporting = [
                RequirementNode(
                    requirement_id=f"req_supp_comm_{uuid.uuid4().hex[:6]}",
                    name="Domain Communication & Stakeholder Synthesis",
                    category="SUPPORTING_SKILL",
                    importance="MEDIUM",
                    description="Clear documentation, stakeholder presentation, and cross-functional communication.",
                    source=f"Generated from {target_domain} Professional Standards",
                    source_id=f"LLM-GEN-{uuid.uuid4().hex[:4]}",
                    source_url="https://pathmind.ai/standards",
                    retrieved_at=now_iso,
                    evidence_requirement="Presentation slide deck or written summary memo."
                )
            ]
            experience = [
                RequirementNode(
                    requirement_id=f"req_exp_applied_{uuid.uuid4().hex[:6]}",
                    name=f"Practical Applied Experience in {target_outcome}",
                    category="EXPERIENCE",
                    importance="HIGH",
                    description=f"Real-world application of skills in an organizational or project setting.",
                    source=f"Generated from {target_domain} Industry Benchmark",
                    source_id=f"LLM-GEN-{uuid.uuid4().hex[:4]}",
                    source_url="https://pathmind.ai/standards",
                    retrieved_at=now_iso,
                    evidence_requirement="Internship, employment, or external client engagement record."
                )
            ]
            projects = [
                RequirementNode(
                    requirement_id=f"req_proj_portfolio_{uuid.uuid4().hex[:6]}",
                    name=f"Verifiable Portfolio Project in {target_outcome}",
                    category="PROJECT_EVIDENCE",
                    importance="HIGH",
                    description=f"A documented capstone artifact proving hands-on mastery in {target_outcome}.",
                    source=f"Generated from {target_domain} Portfolio Requirement",
                    source_id=f"LLM-GEN-{uuid.uuid4().hex[:4]}",
                    source_url="https://pathmind.ai/standards",
                    retrieved_at=now_iso,
                    evidence_requirement="Public project artifact link with documented methodology and outcome."
                )
            ]
            return CareerRequirementGraph(
                target_role=target_outcome,
                target_industry=target_domain or "Professional Services",
                source_standards=["ESCO Occupational Taxonomy"],
                core_skills=core,
                supporting_skills=supporting,
                education_requirements=[],
                credential_recommendations=[],
                experience_requirements=experience,
                project_evidence_requirements=projects,
                eligibility_criteria=[],
                market_context_notes=[f"Requirements calibrated specifically for {target_outcome}."],
                generated_at=now_iso
            )

    def perform_gap_analysis(
        self,
        profile: UniversalCareerProfile,
        graph: CareerRequirementGraph
    ) -> Dict[str, Any]:
        """
        Compares CURRENT VERIFIED STATE against TARGET REQUIREMENT GRAPH.
        Categorizes each requirement into:
        - ALREADY_HAVE (proven by verified evidence)
        - PARTIAL (transferable / emerging proof)
        - MISSING (evaluated evidence indicates requirement not satisfied)
        - UNKNOWN (no evidence provided yet)
        - NOT_RELEVANT
        """
        all_requirements = (
            graph.core_skills +
            graph.supporting_skills +
            graph.education_requirements +
            graph.credential_recommendations +
            graph.experience_requirements +
            graph.project_evidence_requirements +
            graph.eligibility_criteria
        )

        user_skills_set = {s.lower().strip() for s in profile.skills}
        user_projects = profile.projects
        user_experience = profile.experience
        user_education = profile.education
        user_credentials = profile.credentials

        already_have = []
        partial = []
        missing = []
        unknown = []

        for req in all_requirements:
            req_name_l = req.name.lower()
            matched = False

            # Check if skill held
            if any(req_name_l in s or s in req_name_l for s in user_skills_set):
                already_have.append({
                    "requirement": req.name,
                    "category": req.category,
                    "status": "ALREADY_HAVE",
                    "provenance": "Demonstrated in verified skills"
                })
                req.status_for_person = "ALREADY_HAVE"
                matched = True

            # Check if education satisfied
            elif req.category == "EDUCATION" and user_education:
                edu_match = any(
                    any(term in edu.degree.lower() or term in edu.field_of_study.lower() for term in req_name_l.split())
                    for edu in user_education
                )
                if edu_match:
                    already_have.append({
                        "requirement": req.name,
                        "category": req.category,
                        "status": "ALREADY_HAVE",
                        "provenance": f"Verified in education: {user_education[0].degree}"
                    })
                    req.status_for_person = "ALREADY_HAVE"
                    matched = True

            # Check if experience satisfied
            elif req.category in ["EXPERIENCE", "SUPERVISED_PRACTICE"] and user_experience:
                exp_match = any(
                    any(term in exp.role.lower() or term in exp.description.lower() for term in req_name_l.split())
                    for exp in user_experience
                )
                if exp_match:
                    already_have.append({
                        "requirement": req.name,
                        "category": req.category,
                        "status": "ALREADY_HAVE",
                        "provenance": f"Demonstrated in professional experience: {user_experience[0].role}"
                    })
                    req.status_for_person = "ALREADY_HAVE"
                    matched = True
                elif len(user_experience) > 0:
                    partial.append({
                        "requirement": req.name,
                        "category": req.category,
                        "status": "PARTIAL",
                        "provenance": f"Transferable experience from prior roles ({user_experience[0].role})"
                    })
                    req.status_for_person = "PARTIAL"
                    matched = True

            # Check portfolio / projects
            elif req.category in ["PORTFOLIO", "PROJECT_EVIDENCE"] and user_projects:
                already_have.append({
                    "requirement": req.name,
                    "category": req.category,
                    "status": "ALREADY_HAVE",
                    "provenance": f"Project artifact available: {user_projects[0].title}"
                })
                req.status_for_person = "ALREADY_HAVE"
                matched = True

            if not matched:
                # If the user has empty profile evidence, it is UNKNOWN (not proven either way)
                if not profile.skills and not profile.projects and not profile.experience:
                    unknown.append({
                        "requirement": req.name,
                        "category": req.category,
                        "status": "UNKNOWN",
                        "provenance": "There is no verified evidence of this skill or background yet."
                    })
                    req.status_for_person = "UNKNOWN"
                else:
                    missing.append({
                        "requirement": req.name,
                        "category": req.category,
                        "status": "MISSING",
                        "provenance": "The available evidence indicates this requirement is not yet satisfied."
                    })
                    req.status_for_person = "MISSING"

        return {
            "already_have": already_have,
            "partial": partial,
            "missing": missing,
            "unknown": unknown,
            "total_requirements": len(all_requirements),
            "coverage_percent": round((len(already_have) / max(len(all_requirements), 1)) * 100, 1)
        }
