from typing import List, Dict, Any, Optional, Any
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
from backend.services.opportunity_matching_engine import OpportunityMatchingEngine
from backend.services.knowledge import KnowledgeService
from backend.services.requirement_graph_service import RequirementGraphService
from backend.services.pm_store import get_pm_store

class CareerReadinessEngine:
    def __init__(self, store: Optional[Any] = None):
        self.store = store or get_pm_store()
        self.knowledge_service = KnowledgeService()
        self.opportunity_matching_engine = OpportunityMatchingEngine(store=self.store, career_engine=self)
        self.requirement_graph_service = RequirementGraphService(self.knowledge_service)
        
        # 5 Focused ADK Agents
        self.readiness_agent = CareerReadinessAgent()
        self.credential_agent = CredentialAgent()
        self.opportunity_agent = OpportunityAgent()
        self.resume_agent = ResumeAgent()
        self.accountability_agent = AccountabilityAgent()

    async def get_or_create_canonical_profile(
        self,
        person_id: str,
        current_state_type: str = "unassessed"
    ) -> UniversalCareerProfile:
        profile_dict = await self.store.get_career_profile(person_id)
        if profile_dict:
            return UniversalCareerProfile(**profile_dict)

        # Clean Unassessed Blank Profile: NO FAKE PEOPLE OR FABRICATED DATA
        new_profile = UniversalCareerProfile(
            person_id=person_id,
            current_role="Unknown",
            current_state_type=current_state_type or "unassessed",
            education=[],
            experience=[],
            skills=[],
            projects=[],
            credentials=[],
            portfolio_links=[],
            achievements=[],
            current_country="Global",
            current_city="Unknown",
            target_country="Global",
            remote_preference="UNKNOWN",
            work_authorization="UNCONFIRMED",
            goals=[],
            constraints={}
        )

        await self.store.save_career_profile(person_id, new_profile.model_dump(mode="json"))
        return new_profile

    async def get_or_create_career_goal(self, person_id: str, target_role: Optional[str] = None) -> TargetOutcome:
        goal_dict = await self.store.get_career_goal(person_id)
        if goal_dict:
            return TargetOutcome(**goal_dict)

        # Generate via interpretation service if missing
        from backend.services.goal_interpretation_service import GoalInterpretationService
        interpreter = GoalInterpretationService(self.store)
        
        raw_statement = target_role if target_role else "Explore potential domains"
        return await interpreter.interpret_goal(person_id, raw_statement)

    def build_requirement_graph(
        self,
        goal: TargetOutcome,
        skills_held: List[str]
    ) -> CareerRequirementGraph:
        """
        Builds a structured requirement graph originating from official standards (ESCO / NCO / BCI / etc.)
        via RequirementGraphService.
        """
        graph = self.requirement_graph_service.build_requirement_graph_for_outcome(goal)
        skills_held_lower = {s.lower().strip() for s in skills_held}

        # Calibrate status_for_person based on skills held
        for node in graph.core_skills:
            node_name_lower = node.name.lower()
            if any(node_name_lower in s or s in node_name_lower for s in skills_held_lower):
                node.status_for_person = "AVAILABLE"
            else:
                node.status_for_person = "MISSING"

        for node in graph.supporting_skills:
            node_name_lower = node.name.lower()
            if any(node_name_lower in s or s in node_name_lower for s in skills_held_lower):
                node.status_for_person = "AVAILABLE"
            else:
                node.status_for_person = "MISSING"

        return graph

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
        Supports students, working professionals, and career switchers across multiple domains.
        """
        current_state = profile.current_state_type.lower()
        target_lower = target_role.lower()

        if "mechanical" in current_state or ("engineer" in current_state and "software" not in current_state):
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
        elif any(k in target_lower for k in ["product manager", "product management", "associate product manager"]) or ("product" in target_lower and "designer" not in target_lower):
            base_skills = profile.skills or ["Customer Discovery & Empathy", "Stakeholder Communication"]
            return TransferableSkillsAnalysis(
                already_have=base_skills,
                can_transfer=["Cross-Functional Collaboration", "Problem Decomposition", "Strategic Communication"],
                need_to_develop=["Product Requirements Documentation (PRD)", "Product Discovery & User Research", "Opportunity-Solution Tree Roadmapping", "Product Analytics & Metrics"],
                analysis_summary="Your existing background transfers directly into product discovery and cross-functional coordination; focus learning on PRDs, user discovery, and roadmapping."
            )
        elif any(k in target_lower for k in ["academic / scientific researcher", "scientific researcher", "academic researcher", "research scientist"]) or (target_lower.strip() == "researcher"):
            base_skills = profile.skills or ["Quantitative Analysis", "Critical Reading"]
            return TransferableSkillsAnalysis(
                already_have=base_skills,
                can_transfer=["Analytical Rigor", "Data Modeling", "Systematic Inquiry"],
                need_to_develop=["Literature Review & Systematic Synthesis", "Formal Research Methodology", "Hypothesis Testing & Statistical Inference", "Peer-Reviewed Manuscript Preparation"],
                analysis_summary="Focus on formal research methodology, systematic literature benchmarking, and peer-reviewed preprint publication."
            )
        elif "design" in target_lower or "ux" in target_lower:
            return TransferableSkillsAnalysis(
                already_have=profile.skills or ["Visual Communication", "Empathy"],
                can_transfer=["User Journey Thinking", "Aesthetic Evaluation"],
                need_to_develop=["Figma Design Systems & Variables", "Usability Testing Protocols", "Interaction Prototyping"],
                analysis_summary="Focus on building end-to-end UX case studies and mastery of Figma design tokens."
            )
        elif "law" in target_lower or "legal" in target_lower:
            return TransferableSkillsAnalysis(
                already_have=profile.skills or ["Critical Analysis", "Written Communication"],
                can_transfer=["Logical Argumentation", "Textual Interpretation"],
                need_to_develop=["Statutory Interpretation Doctrine", "Case Law Precedent Analysis", "Legal Research Databases"],
                analysis_summary="Focus on formal jurisprudential doctrine, statutory drafting, and bar examination subjects."
            )
        elif "restaurant" in target_lower or "culinary" in target_lower or "food" in target_lower:
            return TransferableSkillsAnalysis(
                already_have=profile.skills or ["Customer Service", "Resource Management"],
                can_transfer=["Operational Coordination", "Supplier Negotiation"],
                need_to_develop=["Food Safety Regulations & HACCP", "Menu Engineering & Prime Costing", "Commercial Kitchen Architecture"],
                analysis_summary="Focus on hospitality unit economics, health code compliance, and commercial kitchen operations."
            )
        elif any(k in target_lower for k in ["psycholog", "mental health", "therap", "counsel"]):
            return TransferableSkillsAnalysis(
                already_have=profile.skills or ["Active Listening", "Empathetic Communication"],
                can_transfer=["Behavioral Observation", "Qualitative Case Synthesis", "Diagnostic Interviewing"],
                need_to_develop=["Psychopathology & DSM-5 Diagnostic Criteria", "Cognitive Behavioral Therapy (CBT) Protocols", "Supervised Clinical Hours & Ethics"],
                analysis_summary="Focus on formal clinical diagnostic training, therapeutic intervention modalities, and supervised practicum hours."
            )
        elif any(k in target_lower for k in ["photo", "photographer"]):
            return TransferableSkillsAnalysis(
                already_have=profile.skills or ["Visual Aesthetic Sense", "Composition"],
                can_transfer=["Creative Framing", "Visual Storytelling", "Client Communication"],
                need_to_develop=["Studio Strobe Lighting Techniques", "Commercial RAW Post-Processing", "High-Volume Client Delivery Galleries"],
                analysis_summary="Focus on studio lighting mastery, commercial portfolio curation, and color-calibrated RAW processing."
            )
        elif any(k in target_lower for k in ["teach", "educat", "pedagog", "school"]):
            return TransferableSkillsAnalysis(
                already_have=profile.skills or ["Subject Matter Knowledge", "Oral Presentation"],
                can_transfer=["Concept Decomposition", "Student Mentorship", "Curriculum Structuring"],
                need_to_develop=["Constructivist Pedagogy & Unit Design", "Differentiated Instruction Strategies", "Classroom Management & State TET / B.Ed"],
                analysis_summary="Focus on pedagogical framework design, differentiated lesson planning, and supervised student teaching practicum."
            )
        elif any(k in target_lower for k in ["upsc", "civil services", "public policy", "ias", "ips"]):
            return TransferableSkillsAnalysis(
                already_have=profile.skills or ["Analytical Reading", "Critical Comprehension"],
                can_transfer=["Multi-Perspective Policy Evaluation", "Socio-Economic Reasoning", "Structured Essay Synthesis"],
                need_to_develop=["General Studies Mains Answer Structuring", "Optional Subject Comprehensive Mastery", "Ethics & Administrative Case Study Protocols"],
                analysis_summary="Focus on structured answer writing frameworks, current affairs synthesis, and exhaustive optional subject preparation."
            )
        elif any(k in target_lower for k in ["biotech", "molecular", "genetics", "bioinformatics", "biology"]):
            return TransferableSkillsAnalysis(
                already_have=profile.skills or ["Laboratory Safety", "Scientific Method"],
                can_transfer=["Hypothesis Formulation", "Quantitative Data Analysis", "Experimental Protocol Design"],
                need_to_develop=["Molecular Assay Protocols & PCR", "Bioinformatics Sequence Alignment", "Peer-Reviewed Scientific Manuscript Preparation"],
                analysis_summary="Focus on hands-on wet-lab assays, computational sequence modeling, and academic preprint contributions."
            )
        elif any(k in target_lower for k in ["mathematician", "pure mathematics", "theoretical math"]):
            return TransferableSkillsAnalysis(
                already_have=profile.skills or ["Abstract Reasoning", "Quantitative Rigor"],
                can_transfer=["Axiomatic Deduction", "Analytical Proof Mindset", "Logical Formalism"],
                need_to_develop=["Abstract Algebra (Groups, Rings, Fields)", "Real Analysis & Measure Theory", "Point-Set & Differential Topology", "LaTeX Manuscript Exposition"],
                analysis_summary="Focus on formal proof construction in higher algebra, measure-theoretic real analysis, and axiomatic topology."
            )
        elif any(k in target_lower for k in ["operations manager", "ops manager", "business operations"]):
            return TransferableSkillsAnalysis(
                already_have=profile.skills or ["Organizational Coordination", "Stakeholder Communication"],
                can_transfer=["Workflow Optimization", "Executive Communication", "Cross-Departmental Logistics"],
                need_to_develop=["Value Stream Mapping & Lean Workflows", "KPI Dashboard Design & Telemetry", "Vendor Procurement & SLA Negotiations"],
                analysis_summary="Focus on quantitative workflow diagnostics, real-time KPI telemetry, and high-stakes vendor contract negotiations."
            )
        elif any(k in target_lower for k in ["drone hardware", "drone", "uav", "aerospace hardware"]):
            return TransferableSkillsAnalysis(
                already_have=profile.skills or ["CAD Modeling", "Statics & Dynamics"],
                can_transfer=["Mechanical System Architecture", "Kinematic Analysis", "Structural FEA"],
                need_to_develop=["Embedded Flight Controller Firmware (PX4/C++)", "Sensor Fusion (IMU/LiDAR/Optical Flow)", "ROS 2 Hardware Interfaces & ESC Protocols"],
                analysis_summary="Focus on embedded real-time flight firmware, multi-sensor Kalman filtering, and actuator bus communications."
            )
        elif any(k in target_lower for k in ["computational fluid dynamics", "cfd", "fluid dynamics", "aerodynamics"]):
            return TransferableSkillsAnalysis(
                already_have=profile.skills or ["Multivariable Calculus", "Fluid Mechanics"],
                can_transfer=["Continuum Mechanics", "Differential Equations", "Thermodynamic Principles"],
                need_to_develop=["Numerical Discretization & FVM Meshing", "Turbulence Modeling (RANS/LES)", "HPC Parallel OpenFOAM / MPI Solvers"],
                analysis_summary="Focus on finite volume discretization schemes, turbulence model selection, and parallel HPC cluster execution."
            )
        else:
            # General student / candidate profile
            return TransferableSkillsAnalysis(
                already_have=profile.skills or ["Foundational Reasoning", "Academic Problem Solving"],
                can_transfer=["Algorithmic Logic", "Quantitative Problem Solving", "Structured Test Mindset"],
                need_to_develop=[f"Core Competencies in {target_role}", "Applied Project Portfolio", "Industry Verification"],
                analysis_summary=f"You possess strong foundational capabilities; focus next on practical artifacts and domain competencies for {target_role}."
            )

    # Alias for semantic compatibility
    evaluate_transferable_skills = analyze_transferable_skills

    def analyze_experience_gaps(
        self,
        profile: UniversalCareerProfile,
        target_role: str,
        requirement_graph: CareerRequirementGraph
    ) -> List[ExperienceGap]:
        """
        Categorizes missing experience types:
        PROJECT, INTERNSHIP, RESEARCH, FREELANCE, OPEN_SOURCE, LEADERSHIP, INTERNAL_EXPERIENCE.
        Ties experience requirements directly to target role milestones.
        """
        target_lower = target_role.lower()

        if "design" in target_lower or "ux" in target_lower:
            return [
                ExperienceGap(
                    gap_id="exp_gap_design_case_study",
                    experience_type="PROJECT",
                    title="End-to-End Product Design Case Study",
                    why_it_matters="Design teams evaluate your problem framing, discovery synthesis, and wireframe iterations.",
                    how_to_obtain="Complete a comprehensive Figma case study documenting user problem, research, and component tokens.",
                    evidence_to_prove="Public Figma link or portfolio case study article.",
                    associated_roadmap_stage="Design Systems & Usability Stage"
                ),
                ExperienceGap(
                    gap_id="exp_gap_design_usability",
                    experience_type="RESEARCH",
                    title="User Usability Testing Report",
                    why_it_matters="Proves ability to gather and act on qualitative user feedback.",
                    how_to_obtain="Conduct moderated usability sessions on a prototype and document friction points.",
                    evidence_to_prove="Documented usability test report with task completion metrics.",
                    associated_roadmap_stage="Usability Testing Stage"
                )
            ]
        elif "law" in target_lower or "legal" in target_lower:
            return [
                ExperienceGap(
                    gap_id="exp_gap_legal_brief",
                    experience_type="PROJECT",
                    title="Moot Court Brief & Legal Research Memorandum",
                    why_it_matters="Legal employers evaluate statutory research rigor and structured advocacy.",
                    how_to_obtain="Draft a comprehensive legal memorandum applying case law precedents to a complex dispute.",
                    evidence_to_prove="Verified legal research paper or moot court submission brief.",
                    associated_roadmap_stage="Statutory Interpretation & Legal Writing"
                ),
                ExperienceGap(
                    gap_id="exp_gap_chamber_internship",
                    experience_type="INTERNSHIP",
                    title="Senior Advocate Chamber or Law Firm Internship",
                    why_it_matters="Provides direct courtroom observation, procedural filing exposure, and client consultation experience.",
                    how_to_obtain="Complete an internship with a practicing advocate or law firm.",
                    evidence_to_prove="Verified internship completion certificate or chamber recommendation.",
                    associated_roadmap_stage="Practical Courtroom & Chamber Experience"
                )
            ]
        elif "restaurant" in target_lower or "culinary" in target_lower:
            return [
                ExperienceGap(
                    gap_id="exp_gap_prime_cost",
                    experience_type="PROJECT",
                    title="Menu Prime Costing & Financial Feasibility Model",
                    why_it_matters="Hospitality ventures succeed on strict COGS and labor cost controls.",
                    how_to_obtain="Build a financial spreadsheet modeling dish ingredient costs, target margins, and breakeven covers.",
                    evidence_to_prove="Completed financial model and supplier price comparisons.",
                    associated_roadmap_stage="Unit Economics & Kitchen Planning"
                ),
                ExperienceGap(
                    gap_id="exp_gap_kitchen_stage",
                    experience_type="INTERNSHIP",
                    title="Commercial Kitchen & Service Practicum",
                    why_it_matters="Understanding service rush, station prep, and sanitation is essential for ownership.",
                    how_to_obtain="Complete hands-on service stages in a commercial food establishment.",
                    evidence_to_prove="Verified commercial kitchen stage record or manager letter.",
                    associated_roadmap_stage="Commercial Service & Health Compliance"
                )
            ]
        elif any(k in target_lower for k in ["psycholog", "mental health", "therap", "counsel"]):
            return [
                ExperienceGap(
                    gap_id="exp_gap_clinical_practicum",
                    experience_type="INTERNSHIP",
                    title="Supervised Clinical Psychology Practicum",
                    why_it_matters="Licensing boards require documented client contact hours under a licensed clinical supervisor.",
                    how_to_obtain="Complete structured clinical placement conducting intake interviews and supervised psychotherapy.",
                    evidence_to_prove="Signed supervisor practicum logbook and institutional internship certificate.",
                    associated_roadmap_stage="Stage 03: Supervised Clinical Practicum"
                ),
                ExperienceGap(
                    gap_id="exp_gap_psych_eval_report",
                    experience_type="PROJECT",
                    title="Comprehensive Psychological Assessment & Case Formulation",
                    why_it_matters="Clinics evaluate diagnostic reasoning, psychometric test interpretation, and treatment planning.",
                    how_to_obtain="Conduct diagnostic evaluation battery (WAIS, MMPI) and synthesize full clinical case formulation.",
                    evidence_to_prove="De-identified comprehensive psychological assessment report.",
                    associated_roadmap_stage="Stage 02: Psychological Assessment & Diagnostic Formulation"
                )
            ]
        elif any(k in target_lower for k in ["photo", "photographer"]):
            return [
                ExperienceGap(
                    gap_id="exp_gap_photo_portfolio",
                    experience_type="PROJECT",
                    title="Commercial Editorial Portfolio & Lighting Case Study",
                    why_it_matters="Art directors and clients select photographers entirely based on published lighting mastery and cohesive visual style.",
                    how_to_obtain="Produce a 15-image editorial collection documenting lighting diagrams, modifier choices, and RAW post-processing.",
                    evidence_to_prove="Curated online gallery link and behind-the-scenes lighting breakdown documentation.",
                    associated_roadmap_stage="Stage 02: Advanced Studio & Location Lighting Mastery"
                ),
                ExperienceGap(
                    gap_id="exp_gap_photo_client_delivery",
                    experience_type="FREELANCE",
                    title="Commercial Client Commission & Delivery Workflow",
                    why_it_matters="Proves ability to manage client brief, rate card, model release, and deadline delivery.",
                    how_to_obtain="Execute a commissioned or commercial test shoot with full contract, call sheet, and deliverables.",
                    evidence_to_prove="Delivered client gallery, signed model releases, and commercial invoice.",
                    associated_roadmap_stage="Stage 03: Professional Portfolio, Client Business & Delivery"
                )
            ]
        elif any(k in target_lower for k in ["teach", "educat", "pedagog", "school"]):
            return [
                ExperienceGap(
                    gap_id="exp_gap_teach_practicum",
                    experience_type="INTERNSHIP",
                    title="Supervised Classroom Teaching Practicum",
                    why_it_matters="School administrations require verified classroom teaching hours with pedagogical mentor evaluations.",
                    how_to_obtain="Complete a multi-week classroom teaching placement delivering structured lessons and student grading.",
                    evidence_to_prove="Supervising teacher evaluation report and classroom observation logs.",
                    associated_roadmap_stage="Stage 03: Classroom Practicum & Student Teaching"
                ),
                ExperienceGap(
                    gap_id="exp_gap_teach_lesson_plans",
                    experience_type="PROJECT",
                    title="Curriculum Unit Design & Differentiated Assessment Rubrics",
                    why_it_matters="Demonstrates ability to design standards-aligned lesson plans with differentiated learning accommodations.",
                    how_to_obtain="Design a comprehensive 4-week instructional unit with diagnostic rubrics and student activities.",
                    evidence_to_prove="Published lesson plan portfolio and differentiated assessment guide.",
                    associated_roadmap_stage="Stage 02: Curriculum Design & Instructional Strategies"
                )
            ]
        elif any(k in target_lower for k in ["upsc", "civil services", "public policy", "ias", "ips"]):
            return [
                ExperienceGap(
                    gap_id="exp_gap_upsc_mains_writing",
                    experience_type="PROJECT",
                    title="General Studies Mains Evaluated Answer Writing Series",
                    why_it_matters="UPSC selection depends overwhelmingly on written Mains marks; structured answer presentation is vital.",
                    how_to_obtain="Complete comprehensive timed answer writing tests across GS Papers I–IV with faculty review.",
                    evidence_to_prove="Evaluated test copies with mentor marks, feedback, and model answer comparisons.",
                    associated_roadmap_stage="Stage 02: Mains Comprehensive Answer Writing & Optional Mastery"
                ),
                ExperienceGap(
                    gap_id="exp_gap_upsc_mock_interview",
                    experience_type="RESEARCH",
                    title="Personality Test & Board Mock Interview Series",
                    why_it_matters="Evaluates administrative poise, nuanced policy articulation, and ethical decision-making.",
                    how_to_obtain="Participate in mock interview boards with retired senior civil servants.",
                    evidence_to_prove="Detailed mock interview board evaluation transcript and score rubric.",
                    associated_roadmap_stage="Stage 03: Personality Test & Interview Preparation"
                )
            ]
        elif any(k in target_lower for k in ["biotech", "molecular", "genetics", "bioinformatics", "biology"]):
            return [
                ExperienceGap(
                    gap_id="exp_gap_lab_protocol",
                    experience_type="PROJECT",
                    title="Standardized Molecular Assay Protocol & Wet-Lab Notebook",
                    why_it_matters="Research labs evaluate experimental reproducibility, pipetting precision, and rigorous protocol tracking.",
                    how_to_obtain="Perform and document recombinant DNA, PCR, or cell culture assays with negative controls.",
                    evidence_to_prove="Validated laboratory notebook or research poster presentation.",
                    associated_roadmap_stage="Laboratory Assays & Molecular Methods"
                ),
                ExperienceGap(
                    gap_id="exp_gap_research_thesis",
                    experience_type="RESEARCH",
                    title="Scientific Research Preprint or Co-Authored Manuscript",
                    why_it_matters="Primary signal for scientific investigation is peer-reviewed methodology and statistical validation.",
                    how_to_obtain="Synthesize experimental findings into a formal research paper or conference submission.",
                    evidence_to_prove="Preprint URL (e.g. bioRxiv) or co-authored academic publication.",
                    associated_roadmap_stage="Scientific Writing & Publication"
                )
            ]
        elif any(k in target_lower for k in ["mathematician", "pure mathematics", "theoretical math"]):
            return [
                ExperienceGap(
                    gap_id="exp_gap_math_monograph",
                    experience_type="RESEARCH",
                    title="Expository Mathematical Monograph or arXiv Preprint",
                    why_it_matters="Academic mathematical admissions and research fellowships evaluate original proof formulation and scholarly exposition.",
                    how_to_obtain="Author a LaTeX monograph deconstructing a seminal theorem or presenting an original mathematical result.",
                    evidence_to_prove="arXiv Math preprint URL or faculty-evaluated thesis defense document.",
                    associated_roadmap_stage="Formal Mathematical Proofs & Expository Monograph"
                ),
                ExperienceGap(
                    gap_id="exp_gap_math_proof_portfolio",
                    experience_type="PROJECT",
                    title="Advanced Proof Verification Portfolio",
                    why_it_matters="Demonstrates rigorous epsilon-delta argumentation and axiomatic mastery in abstract algebra and topology.",
                    how_to_obtain="Compile an evaluated proof portfolio across group theory, measure theory, and differential topology.",
                    evidence_to_prove="Evaluated LaTeX proof portfolio document with complete lemmas.",
                    associated_roadmap_stage="Abstract Algebra: Groups, Rings & Galois Theory"
                )
            ]
        elif any(k in target_lower for k in ["operations manager", "ops manager", "business operations"]):
            return [
                ExperienceGap(
                    gap_id="exp_gap_ops_transformation",
                    experience_type="PROJECT",
                    title="Cross-Functional Value Stream Transformation Study",
                    why_it_matters="Proves ability to audit real-world bottlenecks, reduce operational cycle times, and establish measurable SLAs.",
                    how_to_obtain="Perform an end-to-end process mapping audit of an enterprise workflow and author a Lean Six Sigma runbook.",
                    evidence_to_prove="Comprehensive process optimization blueprint and executive KPI review deck.",
                    associated_roadmap_stage="Cross-Functional Process Optimization & Lean Workflows"
                ),
                ExperienceGap(
                    gap_id="exp_gap_ops_procurement",
                    experience_type="INTERNAL_EXPERIENCE",
                    title="Vendor Procurement RFP & Contract Negotiation",
                    why_it_matters="Evaluates commercial judgment, vendor scorecarding, and supplier risk governance.",
                    how_to_obtain="Lead or shadow a competitive vendor bidding process from RFP drafting to contract finalization.",
                    evidence_to_prove="Vendor evaluation scorecard and negotiated SLA contract agreement.",
                    associated_roadmap_stage="Vendor Management & Procurement Contract Negotiations"
                )
            ]
        elif any(k in target_lower for k in ["drone hardware", "drone", "uav", "aerospace hardware"]):
            return [
                ExperienceGap(
                    gap_id="exp_gap_drone_prototype",
                    experience_type="PROJECT",
                    title="Autonomous Drone Hardware Flight Prototype",
                    why_it_matters="Hardware teams evaluate physical avionics packaging, vibration damping, and successful autonomous flight test logs.",
                    how_to_obtain="Integrate flight controller, ESCs, motors, and sensors onto an airframe and execute autonomous waypoint flights.",
                    evidence_to_prove="Recorded flight log analysis file (.ulog) and hardware build log video.",
                    associated_roadmap_stage="Autonomous Flight Telemetry & Airframe Integration"
                ),
                ExperienceGap(
                    gap_id="exp_gap_drone_firmware",
                    experience_type="OPEN_SOURCE",
                    title="PX4 / ArduPilot Flight Firmware Driver Module",
                    why_it_matters="Proves ability to write embedded C++ drivers for real-time aerospace operating systems.",
                    how_to_obtain="Write and benchmark a custom sensor driver or actuator module in PX4 / micro-ROS.",
                    evidence_to_prove="Public repository or pull request with passing bench test telemetry.",
                    associated_roadmap_stage="Embedded Flight Controller Firmware & Microcontrollers"
                )
            ]
        elif any(k in target_lower for k in ["computational fluid dynamics", "cfd", "fluid dynamics", "aerodynamics"]):
            return [
                ExperienceGap(
                    gap_id="exp_gap_cfd_validation",
                    experience_type="RESEARCH",
                    title="CFD Experimental Validation & Mesh Convergence Study",
                    why_it_matters="Simulation engineering requires proving that numerical solutions match physical wind tunnel data without grid dependence.",
                    how_to_obtain="Conduct a grid convergence index study and validate RANS/LES pressure profiles against experimental benchmark data.",
                    evidence_to_prove="Complete CFD validation report matching numerical data with experimental wind tunnel records.",
                    associated_roadmap_stage="HPC Parallel Solvers & Experimental Validation Study"
                ),
                ExperienceGap(
                    gap_id="exp_gap_cfd_hpc",
                    experience_type="PROJECT",
                    title="High-Performance OpenFOAM Parallel Scaling Study",
                    why_it_matters="Demonstrates capability to configure multi-core MPI domain decomposition on high-performance computing clusters.",
                    how_to_obtain="Set up and run an OpenFOAM parallel simulation comparing speedup curves across compute nodes.",
                    evidence_to_prove="Simulation case directory, MPI run script, and scalability plot.",
                    associated_roadmap_stage="Numerical Discretization & Mesh Generation"
                )
            ]
        elif any(k in target_lower for k in ["ai", "machine learning", "deep learning", "software", "data"]):
            # Technical / Engineering
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
        else:
            # Generic domain fallback - DO NOT default to Docker or PyTorch
            return [
                ExperienceGap(
                    gap_id="exp_gap_domain_capstone",
                    experience_type="PROJECT",
                    title=f"Comprehensive {target_role} Capstone Portfolio Artifact",
                    why_it_matters="Employers and clients evaluate concrete work output and demonstrated problem-solving rigor.",
                    how_to_obtain=f"Complete a structured, end-to-end practical project or case study demonstrating core skills in {target_role}.",
                    evidence_to_prove="Verified project artifact, portfolio link, or formal documentation report.",
                    associated_roadmap_stage=f"{target_role} Capstone Stage"
                ),
                ExperienceGap(
                    gap_id="exp_gap_supervised_practicum",
                    experience_type="INTERNSHIP",
                    title=f"Supervised Practicum / Apprenticeship in {target_role}",
                    why_it_matters="Real-world supervised exposure provides institutional credibility and procedural mastery.",
                    how_to_obtain=f"Secure an entry-level apprenticeship, internship, or supervised field practicum in {target_role}.",
                    evidence_to_prove="Letter of completion, employer evaluation, or verified recommendation.",
                    associated_roadmap_stage=f"{target_role} Field Practicum Stage"
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

        skill_evals = []
        for node in requirement_graph.core_skills:
            is_held = any(node.name.lower() in s or s in node.name.lower() for s in skills_set)
            skill_evals.append(
                EvidenceRequirementStatus(
                    requirement=node.name,
                    category="SKILL",
                    status="SATISFIED" if is_held else "MISSING",
                    grounding_evidence=[f"Verified in skills: {node.name}"] if is_held else []
                )
            )

        project_evals = []
        for node in requirement_graph.project_evidence_requirements:
            project_evals.append(
                EvidenceRequirementStatus(
                    requirement=node.name,
                    category="PROJECT",
                    status="SATISFIED" if has_projects else "MISSING",
                    grounding_evidence=[p.title for p in profile.projects] if has_projects else []
                )
            )

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
        graph = self.build_requirement_graph(goal, profile.skills)

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
        opportunities = await self.opportunity_matching_engine.match_opportunities_for_person(
            person_id=person_id,
            role_filter=goal.target_role
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

        skills_gained = profile.skills[:3] if profile.skills else ["Foundational Competency", "Core Domain Knowledge"]
        remaining_gaps = [g.title for g in report.categorized_gaps if g.importance == "HIGH"]

        checkpoint = CareerCheckpoint(
            checkpoint_id=f"chk_{person_id}_{int(datetime.now(timezone.utc).timestamp())}",
            person_id=person_id,
            current_role_status=profile.current_role,
            target=report.target_goal.target_role,
            progress=f"Readiness: {report.readiness_state} | Active Pacing: {report.accountability.weekly_commitment_hours} hrs/week",
            what_changed="Completed foundational stage milestone with verified evidence.",
            skills_gained=skills_gained,
            remaining_gaps=remaining_gaps[:3],
            credential_status="Curated strategy active: Prioritizing verified portfolio evidence over commercial certificates.",
            experience_status=f"Stage foundations verified; progressing toward {report.next_readiness_milestone}.",
            opportunity_readiness=f"Matched with {len(report.matched_opportunities)} verified programs with HIGH fit.",
            next_best_action=f"Complete active milestone in {report.target_goal.target_role} to advance readiness.",
            timestamp=datetime.now(timezone.utc).isoformat()
        )

        await self.store.save_career_checkpoint(person_id, checkpoint.model_dump(mode="json"))
        return checkpoint
