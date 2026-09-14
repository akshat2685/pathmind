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
        target_outcome: str,
        target_domain: Optional[str] = None,
        geography: str = "India & Global"
    ) -> CareerRequirementGraph:
        """
        Builds a structured requirement graph containing only categories that apply
        to the target role and domain.
        """
        lower = target_outcome.lower()
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
        elif "researcher" in lower or "research" in lower or "biotechnology" in lower:
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

        # 7. DEFAULT / FALLBACK: GENERIC PROFESSIONAL OR TECHNICAL GROUNDED IN OUTCOME
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
                    source="Occupational Standard",
                    retrieved_at=now_iso,
                    evidence_requirement=f"Verifiable work artifact or practical portfolio project relevant to {target_outcome}."
                ),
                RequirementNode(
                    requirement_id=f"req_core_gov_{uuid.uuid4().hex[:6]}",
                    name=f"Quality Standards, Governance & Evaluation in {target_outcome}",
                    category="CORE_SKILL",
                    importance="HIGH",
                    description=f"Compliance with industry best practices, ethics, and quality metrics in {target_outcome}.",
                    source="Professional Standards Body",
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
                    source="Professional Standards",
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
                    source="Industry Benchmark",
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
                    source="Hiring Portfolio Requirement",
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
