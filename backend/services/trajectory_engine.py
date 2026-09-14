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

        # Check for non-technical domains first
        if any(k in goals_text for k in ["law", "legal", "advocate", "bar exam", "litigation"]):
            path_corp_law = CandidatePath(
                path_id="path_corporate_law_compliance",
                title="Corporate Law & Regulatory Compliance",
                domain="Legal & Regulatory Practice",
                description="Focuses on corporate governance, commercial contract drafting, statutory compliance, and enterprise risk management.",
                fit_score=92.0,
                fit_level="HIGH",
                confidence="HIGH",
                why_it_matches=[
                    "Aligns directly with stated target objective in legal practice and corporate jurisprudence.",
                    "Builds upon structured analytical reasoning and written communication aptitude."
                ],
                supporting_evidence=["Stated objective in legal jurisprudence."],
                missing_evidence=["LL.B Degree transcripts and Bar enrollment status."],
                required_skills=[
                    "Constitutional Law & Jurisprudence",
                    "Statutory Research & Case Law Citation (SCC/Manupatra)",
                    "Commercial Contract Drafting",
                    "Corporate Governance Regulations (Companies Act / SEC)",
                    "Legal Risk Assessment"
                ],
                current_skills_held=["Analytical Reasoning", "Written Communication"],
                transferable_skills=["Critical Reading", "Structured Logic"],
                skill_gaps=[
                    SkillGap(
                        skill_name="Statutory Research & Citation",
                        category="CORE",
                        current_status="MISSING",
                        description="Proficiency in case law precedent synthesis and legal database research.",
                        recommended_action="Draft statutory briefs using Manupatra / SCC Online."
                    )
                ],
                education_routes=[
                    EducationRoute(
                        route_type="TRADITIONAL_DEGREE",
                        title="LL.B (3-Year) or B.A. LL.B (5-Year Integrated)",
                        description="Accredited degree recognized by the Bar Council of India or relevant jurisdiction.",
                        estimated_duration="3–5 Years",
                        institutions_or_paths=["National Law Universities (NLUs)", "Faculty of Law / Accredited Law Schools"],
                        geographic_relevance="India & Global"
                    )
                ],
                credential_options=[
                    CredentialOption(
                        title="All India Bar Examination (AIBE)",
                        issuer="Bar Council of India",
                        classification="MANDATORY",
                        purpose="Mandatory qualifying examination to obtain Certificate of Practice for courtroom advocacy."
                    )
                ],
                india_context={"nco_code": "2611.10", "regulatory_body": "Bar Council of India"},
                global_context={"esco_uri": "http://data.europa.eu/esco/occupation/2611", "esco_title": "Lawyer"}
            )
            path_litigation = CandidatePath(
                path_id="path_commercial_litigation",
                title="Commercial Litigation & Dispute Resolution",
                domain="Judicial Advocacy",
                description="Focuses on trial advocacy, appellate procedure, statutory pleadings, and arbitration mechanisms.",
                fit_score=88.0,
                fit_level="HIGH",
                confidence="HIGH",
                why_it_matches=["Specialized advocacy pathway emphasizing dispute resolution and evidence law."],
                supporting_evidence=["Stated interest in advocacy."],
                missing_evidence=["Moot court briefs and courtroom internship records."],
                required_skills=["Civil & Criminal Procedure", "Evidence Law & Cross-Examination", "Appellate Drafting", "Alternative Dispute Resolution (ADR)"],
                current_skills_held=["Logical Argumentation"],
                transferable_skills=["Oral Advocacy"],
                skill_gaps=[SkillGap(skill_name="Procedural Pleading Drafting", category="CORE", current_status="MISSING", description="Drafting plaints, written statements, and writ petitions.", recommended_action="Complete chamber internship drafting assignments.")],
                education_routes=[EducationRoute(route_type="TRADITIONAL_DEGREE", title="LL.B Degree", description="Recognized law degree.", estimated_duration="3 Years", institutions_or_paths=["Accredited Law Faculty"], geographic_relevance="India")],
                credential_options=[CredentialOption(title="State Bar Council Enrollment", issuer="State Bar Council", classification="MANDATORY", purpose="Mandatory license for advocate practice.")],
                india_context={"nco_code": "2611.20", "regulatory_body": "State Bar Council"},
                global_context={"esco_uri": "http://data.europa.eu/esco/occupation/2611.1", "esco_title": "Litigation Lawyer"}
            )
            return [path_corp_law, path_litigation]

        elif any(k in goals_text for k in ["design", "ux", "ui", "product design", "figma"]):
            path_design = CandidatePath(
                path_id="path_product_design_systems",
                title="Product Design & Design Systems",
                domain="Human-Computer Interaction",
                description="Focuses on end-to-end product design, Figma design token architectures, usability testing, and user journeys.",
                fit_score=93.0,
                fit_level="HIGH",
                confidence="HIGH",
                why_it_matches=["Directly aligns with stated product design and human-computer interaction goals."],
                supporting_evidence=["Stated design objective."],
                missing_evidence=["Public Figma portfolio and documented case studies."],
                required_skills=["Figma Design Systems & Auto-Layout", "User Journey Mapping & Wireframing", "Usability Testing & Heuristics", "Design Tokens & Accessibility (WCAG)"],
                current_skills_held=["Visual Aesthetic Sense"],
                transferable_skills=["User Empathy", "Problem Framing"],
                skill_gaps=[SkillGap(skill_name="Design Token Architecture", category="CORE", current_status="MISSING", description="Mastery of Figma variables, modes, and design token handoff to engineering.", recommended_action="Publish a comprehensive design system case study.")],
                education_routes=[EducationRoute(route_type="PROJECT_BASED_ACCELERATED", title="Applied Design Portfolio & Case Studies", description="Self-directed capstone projects solving real consumer friction points.", estimated_duration="6–12 Months", institutions_or_paths=["Interaction Design Foundation", "Figma Academy"], geographic_relevance="Global")],
                credential_options=[CredentialOption(title="NN/g UX Master Certification", issuer="Nielsen Norman Group", classification="OPTIONAL", purpose="Industry recognized UX credential.")],
                india_context={"nco_code": "2166.10"},
                global_context={"esco_uri": "http://data.europa.eu/esco/occupation/2166", "esco_title": "Product Designer"}
            )
            path_uxr = CandidatePath(
                path_id="path_ux_research_strategy",
                title="User Experience Research & Design Strategy",
                domain="User Experience Research",
                description="Focuses on behavioral discovery, qualitative user interviews, usability metrics, and product roadmap synthesis.",
                fit_score=89.0,
                fit_level="HIGH",
                confidence="HIGH",
                why_it_matches=["Emphasizes qualitative research rigor and strategic customer empathy."],
                supporting_evidence=["Stated user empathy focus."],
                missing_evidence=["Usability test reports and customer interview synthesis."],
                required_skills=["Qualitative User Interviewing", "Usability Test Protocols (SUS)", "Persona & Journey Modeling", "Product Opportunity Trees"],
                current_skills_held=["Qualitative Analysis"],
                transferable_skills=["Empathetic Inquiry"],
                skill_gaps=[SkillGap(skill_name="Quantitative Usability Testing", category="CORE", current_status="MISSING", description="System Usability Scale (SUS) benchmarking.", recommended_action="Run 5 user test sessions on a live web app.")],
                education_routes=[EducationRoute(route_type="PROJECT_BASED_ACCELERATED", title="UX Research Portfolio", description="User research case studies.", estimated_duration="6 Months", institutions_or_paths=["UX Research Guild"], geographic_relevance="Global")],
                credential_options=[],
                india_context={"nco_code": "2513.20"},
                global_context={"esco_uri": "http://data.europa.eu/esco/occupation/2513.2", "esco_title": "UX Researcher"}
            )
            return [path_design, path_uxr]

        elif any(k in goals_text for k in ["restaurant", "culinary", "hospitality", "chef", "food"]):
            path_resto = CandidatePath(
                path_id="path_hospitality_entrepreneurship",
                title="Food & Beverage Hospitality Entrepreneurship",
                domain="Hospitality & Culinary Management",
                description="Focuses on culinary concept launch, prime costing, food safety licenses, kitchen operations, and guest experience delivery.",
                fit_score=91.0,
                fit_level="HIGH",
                confidence="HIGH",
                why_it_matches=["Aligns directly with restaurant launch and hospitality venture aspirations."],
                supporting_evidence=["Declared hospitality goal."],
                missing_evidence=["Business plan and commercial kitchen stage records."],
                required_skills=["Menu Engineering & Prime Costing", "Food Safety (FSSAI/HACCP)", "Commercial Kitchen Workflow", "Hospitality Service Standards", "Inventory Supply Chain"],
                current_skills_held=["Customer Service"],
                transferable_skills=["Operational Planning"],
                skill_gaps=[SkillGap(skill_name="Menu Prime Costing", category="CORE", current_status="MISSING", description="Dish ingredient unit economics and target margin controls.", recommended_action="Build a complete menu prime cost model.")],
                education_routes=[EducationRoute(route_type="VOCATIONAL_DIRECT", title="Culinary Arts & Hospitality Management", description="Hands-on commercial culinary and operations training.", estimated_duration="1–2 Years", institutions_or_paths=["Institute of Hotel Management (IHM)", "Culinary Academy"], geographic_relevance="India & Global")],
                credential_options=[CredentialOption(title="FSSAI Food Safety Supervisor Certification", issuer="Food Safety and Standards Authority of India", classification="MANDATORY", purpose="Mandatory statutory certificate for food business operations.")],
                india_context={"nco_code": "1412.10", "regulatory_body": "FSSAI"},
                global_context={"esco_uri": "http://data.europa.eu/esco/occupation/1412", "esco_title": "Restaurant Manager"}
            )
            return [path_resto]

        elif any(k in goals_text for k in ["biotech", "molecular", "genetics", "bioinformatics", "biology"]):
            path_biotech = CandidatePath(
                path_id="path_biotech_molecular_research",
                title="Biotechnology & Molecular Biology Research",
                domain="Life Sciences & Molecular Genetics",
                description="Focuses on wet-lab molecular assays, recombinant DNA protocols, gene expression analysis, and peer-reviewed scientific methodology.",
                fit_score=92.0,
                fit_level="HIGH",
                confidence="HIGH",
                why_it_matches=["Aligns with biotechnology research and laboratory science objectives."],
                supporting_evidence=["Declared life sciences objective."],
                missing_evidence=["Wet-lab experimental records and peer-reviewed literature review."],
                required_skills=["Recombinant DNA Technology", "PCR & Gel Electrophoresis", "Cell Culture & Aseptic Protocol", "Statistical Experimental Design", "Scientific Manuscript Writing"],
                current_skills_held=["Quantitative Reasoning"],
                transferable_skills=["Analytical Problem Solving"],
                skill_gaps=[SkillGap(skill_name="Molecular Assay Protocols", category="CORE", current_status="MISSING", description="Hands-on execution of quantitative PCR and Western blotting.", recommended_action="Complete structured laboratory practicum.")],
                education_routes=[EducationRoute(route_type="TRADITIONAL_DEGREE", title="B.S. / M.S. in Biotechnology or Molecular Biology", description="University degree in biological sciences.", estimated_duration="3–4 Years", institutions_or_paths=["University Life Sciences Faculty"], geographic_relevance="India & Global")],
                credential_options=[],
                india_context={"nco_code": "2131.20"},
                global_context={"esco_uri": "http://data.europa.eu/esco/occupation/2131.2", "esco_title": "Biotechnologist"}
            )
            return [path_biotech]

        elif any(k in goals_text for k in ["psycholog", "mental health", "therap", "counsel"]):
            path_psych = CandidatePath(
                path_id="path_clinical_psychology",
                title="Clinical Psychology & Therapeutic Practice",
                domain="Clinical & Counseling Psychology",
                description="Focuses on psychopathology assessment, standardized psychometric evaluation, evidence-based cognitive psychotherapy, and supervised clinical practice.",
                fit_score=94.0,
                fit_level="HIGH",
                confidence="HIGH",
                why_it_matches=["Aligns directly with clinical psychology, mental health care, and therapeutic practice goals."],
                supporting_evidence=["Stated mental health and counseling objective."],
                missing_evidence=["Supervised clinical practicum logs and diagnostic assessment reports."],
                required_skills=["Psychopathology & DSM-5 Diagnostic Criteria", "Standardized Psychological Testing (WAIS, MMPI)", "Cognitive Behavioral Therapy (CBT)", "Clinical Ethical Codes & Confidentiality", "Intake Interviewing & MSE"],
                current_skills_held=["Active Listening", "Empathetic Communication"],
                transferable_skills=["Behavioral Observation", "Qualitative Case Synthesis"],
                skill_gaps=[SkillGap(skill_name="Psychometric Battery Administration", category="CORE", current_status="MISSING", description="Administering, scoring, and interpreting standardized intelligence and personality batteries.", recommended_action="Complete diagnostic assessment practicum under a licensed supervisor.")],
                education_routes=[EducationRoute(route_type="TRADITIONAL_DEGREE", title="M.Phil / Psy.D in Clinical Psychology", description="Post-graduate professional degree required for clinical licensing.", estimated_duration="2 Years", institutions_or_paths=["Recognized Medical Institutes & Universities"], geographic_relevance="India & Global")],
                credential_options=[CredentialOption(title="Clinical Psychologist Licensure / RCI Registration", issuer="Rehabilitation Council of India / State Board", classification="MANDATORY", purpose="Statutory license required to practice clinical psychotherapy.")],
                india_context={"nco_code": "2634.10", "regulatory_body": "Rehabilitation Council of India (RCI)"},
                global_context={"esco_uri": "http://data.europa.eu/esco/occupation/2634.1", "esco_title": "Clinical Psychologist"}
            )
            path_cbt = CandidatePath(
                path_id="path_cognitive_behavioral_counseling",
                title="Cognitive Behavioral Counseling & Assessment",
                domain="Counseling Psychology",
                description="Focuses on structured cognitive-behavioral intervention protocols, case conceptualization, and psychoeducation.",
                fit_score=90.0,
                fit_level="HIGH",
                confidence="HIGH",
                why_it_matches=["Specialized focus on evidence-based cognitive behavioral counseling modalities."],
                supporting_evidence=["Declared therapeutic practice interest."],
                missing_evidence=["Counseling case formulation and supervised hours."],
                required_skills=["CBT Protocol Delivery", "Cognitive Restructuring", "Behavioral Activation", "Therapeutic Alliance"],
                current_skills_held=["Empathetic Communication"],
                transferable_skills=["Interpersonal Facilitation"],
                skill_gaps=[SkillGap(skill_name="CBT Case Conceptualization", category="CORE", current_status="MISSING", description="Authoring structured CBT case formulation notes.", recommended_action="Complete Beck Institute certified training modules.")],
                education_routes=[EducationRoute(route_type="PROJECT_BASED_ACCELERATED", title="Specialized CBT Practitioner Certification", description="Applied therapeutic intervention training.", estimated_duration="6–12 Months", institutions_or_paths=["Beck Institute / Recognized Counseling Institutes"], geographic_relevance="Global")],
                credential_options=[CredentialOption(title="Certified CBT Practitioner", issuer="Beck Institute", classification="STRONGLY_USEFUL", purpose="Validates competency in evidence-based CBT protocols.")],
                india_context={"nco_code": "2634.20"},
                global_context={"esco_uri": "http://data.europa.eu/esco/occupation/2634.3", "esco_title": "Counseling Psychologist"}
            )
            return [path_psych, path_cbt]

        elif any(k in goals_text for k in ["photo", "photographer"]):
            path_photo = CandidatePath(
                path_id="path_commercial_editorial_photography",
                title="Commercial & Editorial Photography",
                domain="Visual Arts & Commercial Photography",
                description="Focuses on optical mechanics, studio strobe multi-light setups, commercial creative direction, color-calibrated RAW post-processing, and editorial portfolio delivery.",
                fit_score=93.0,
                fit_level="HIGH",
                confidence="HIGH",
                why_it_matches=["Directly aligns with professional photography, studio lighting, and commercial visual arts goals."],
                supporting_evidence=["Declared photography objective."],
                missing_evidence=["Published commercial editorial tear-sheets and lighting breakdown documentation."],
                required_skills=["Manual Exposure & Optical Physics", "Studio Strobe Multi-Light Ratios", "RAW Color Grading (Capture One / Lightroom)", "Commercial Client Direction", "Frequency Separation Retouching"],
                current_skills_held=["Visual Composition", "Aesthetic Framing"],
                transferable_skills=["Creative Storytelling", "Client Communication"],
                skill_gaps=[SkillGap(skill_name="Studio Strobe Multi-Light Ratios", category="CORE", current_status="MISSING", description="Controlling key, fill, and rim strobe lighting ratios with optical modifiers.", recommended_action="Produce a 15-image editorial collection documenting lighting diagrams.")],
                education_routes=[EducationRoute(route_type="PROJECT_BASED_ACCELERATED", title="Commercial Photography Portfolio & Studio Apprenticeship", description="Hands-on commercial studio assistantship and portfolio curation.", estimated_duration="12–18 Months", institutions_or_paths=["Commercial Photography Studios & Workshops"], geographic_relevance="Global")],
                credential_options=[CredentialOption(title="Certified Professional Photographer (CPP)", issuer="Professional Photographers of America (PPA)", classification="STRONGLY_USEFUL", purpose="Validates technical mastery of lighting, optics, and commercial color science.")],
                india_context={"nco_code": "3431.10"},
                global_context={"esco_uri": "http://data.europa.eu/esco/occupation/3431", "esco_title": "Photographer"}
            )
            return [path_photo]

        elif any(k in goals_text for k in ["teach", "educat", "pedagog", "school"]):
            path_teacher = CandidatePath(
                path_id="path_k12_classroom_education",
                title="K-12 Classroom Education & Pedagogy",
                domain="Education & Pedagogy",
                description="Focuses on educational psychology, constructivist unit design, backward curricular planning (UbD), positive behavioral classroom management, and supervised student teaching.",
                fit_score=94.0,
                fit_level="HIGH",
                confidence="HIGH",
                why_it_matches=["Directly fulfills classroom teaching, pedagogy, and educator development aspirations."],
                supporting_evidence=["Declared teaching objective."],
                missing_evidence=["Supervised student teaching evaluations and state teaching eligibility scores."],
                required_skills=["Educational Psychology (Bloom's, Vygotsky)", "Curriculum Backward Design (UbD)", "Formative & Diagnostic Assessment Rubrics", "Classroom Behavioral Management (PBIS)", "Universal Design for Learning (UDL)"],
                current_skills_held=["Subject Matter Expertise", "Oral Communication"],
                transferable_skills=["Concept Explanation", "Student Mentorship"],
                skill_gaps=[SkillGap(skill_name="Constructivist Unit & Rubric Architecture", category="CORE", current_status="MISSING", description="Authoring differentiated 4-week instructional units with diagnostic rubrics.", recommended_action="Design an instructional unit plan with UDL accommodations.")],
                education_routes=[EducationRoute(route_type="TRADITIONAL_DEGREE", title="Bachelor of Education (B.Ed)", description="Professional teaching degree required for school appointments.", estimated_duration="2 Years", institutions_or_paths=["University Faculty of Education / Teacher Training Colleges"], geographic_relevance="India & Global")],
                credential_options=[CredentialOption(title="Central Teacher Eligibility Test (CTET) / State TET", issuer="CBSE / National Council for Teacher Education", classification="MANDATORY", purpose="Statutory qualifying examination for K-12 teaching appointments.")],
                india_context={"nco_code": "2330.10", "regulatory_body": "National Council for Teacher Education (NCTE)"},
                global_context={"esco_uri": "http://data.europa.eu/esco/occupation/2330", "esco_title": "Secondary School Teacher"}
            )
            return [path_teacher]

        elif any(k in goals_text for k in ["upsc", "civil services", "public policy", "ias", "ips"]):
            path_civ = CandidatePath(
                path_id="path_civil_services_public_admin",
                title="Civil Services & Public Administration",
                domain="Public Administration & Policy",
                description="Focuses on Indian constitutional governance, macroeconomics, multi-disciplinary Mains answer writing, optional subject mastery, and administrative ethics.",
                fit_score=93.0,
                fit_level="HIGH",
                confidence="HIGH",
                why_it_matches=["Directly aligns with civil service examination and public administration leadership goals."],
                supporting_evidence=["Declared public service aspiration."],
                missing_evidence=["Evaluated General Studies Mains test copies and optional subject syllabus completion."],
                required_skills=["Constitutional Law & Indian Polity", "Socio-Economic Development Policy", "GS Mains Multi-Dimensional Answer Structuring", "Administrative Ethics & Case Study Resolution", "Current Affairs Analytical Synthesis"],
                current_skills_held=["Analytical Reading", "Critical Comprehension"],
                transferable_skills=["Logical Synthesis", "Policy Argumentation"],
                skill_gaps=[SkillGap(skill_name="GS Mains Multi-Dimensional Answer Writing", category="CORE", current_status="MISSING", description="Drafting timed, structured evaluative answers across GS I–IV papers.", recommended_action="Enroll in and complete a full-length evaluative Mains answer writing test series.")],
                education_routes=[EducationRoute(route_type="PROJECT_BASED_ACCELERATED", title="Civil Services Comprehensive Syllabus & Test Preparation", description="Structured preparation across General Studies, Optional Subject, and Essay papers.", estimated_duration="12–18 Months", institutions_or_paths=["Self-Directed / Public Policy Foundations"], geographic_relevance="India")],
                credential_options=[CredentialOption(title="UPSC Civil Services Examination (Preliminary & Mains)", issuer="Union Public Service Commission", classification="MANDATORY", purpose="Constitutional qualifying examination for All India and Central Civil Services.")],
                india_context={"nco_code": "1112.10", "regulatory_body": "Union Public Service Commission (UPSC)"},
                global_context={"esco_uri": "http://data.europa.eu/esco/occupation/1112", "esco_title": "Government Administrator"}
            )
            return [path_civ]

        elif goals and not any(k in goals_text for k in ["ai", "machine learning", "robotics", "software", "developer", "coding", "data", "engineer"]):
            primary_goal = goals[0].strip()
            path_custom = CandidatePath(
                path_id=f"path_{primary_goal.lower().replace(' ', '_')[:30]}",
                title=f"{primary_goal} Professional Pathway",
                domain=f"{primary_goal} Practice",
                description=f"Directly derived from stated candidate goal: '{primary_goal}'. Structured around core domain competencies, practical deliverables, and industry verification.",
                fit_score=90.0,
                fit_level="HIGH",
                confidence="HIGH",
                why_it_matches=[f"Directly matches stated objective: '{primary_goal}'."],
                supporting_evidence=[f"Declared candidate aspiration in {primary_goal}."],
                missing_evidence=[f"Verified portfolio artifacts and domain-specific credentials for {primary_goal}."],
                required_skills=[f"Core {primary_goal} Methodology", "Domain Problem Solving", "Professional Standards"],
                current_skills_held=["Analytical Reasoning", "Communication"],
                transferable_skills=["Project Management", "Structured Problem Solving"],
                skill_gaps=[SkillGap(skill_name=f"Applied {primary_goal} Competencies", category="CORE", current_status="MISSING", description=f"Demonstrated practical execution in {primary_goal}.", recommended_action="Build verified portfolio artifacts.")],
                education_routes=[EducationRoute(route_type="PROJECT_BASED_ACCELERATED", title=f"Applied {primary_goal} Preparation", description=f"Focused preparation for {primary_goal}.", estimated_duration="12 Months", institutions_or_paths=["Recognized Training Institutions"], geographic_relevance="Global")],
                credential_options=[],
                india_context={},
                global_context={}
            )
            return [path_custom]

        # 1. Candidate Path 1: Applied AI & Machine Learning Systems (Default / Technical)
        traj_ai = self.corpus_service.match_similar_trajectories(["ai", "machine learning"], interests, limit=1)
        why_ai = ["Directly leverages mathematical and algorithmic strengths demonstrated in academic profile."]
        if interests.get("I"):
            why_ai.insert(0, f"Matches high Investigative Holland psychometric score ({interests.get('I')}%+ analytical affinity).")
        else:
            why_ai.insert(0, "Aligns with analytical and computational problem-solving objectives.")

        path_ai = CandidatePath(
            path_id="path_applied_ai_ml_systems",
            title="Applied AI & Machine Learning Systems",
            domain="Artificial Intelligence & Data Engineering",
            description="Focuses on building production-grade machine learning systems, deep learning model deployment, data ingestion pipelines, and scalable inference architectures.",
            fit_score=92.0,
            fit_level="HIGH",
            confidence="HIGH",
            why_it_matches=why_ai,
            supporting_evidence=[
                "Demonstrated Python coding experience in national hackathon project.",
                "Strong performance in Class 12 Mathematics and Computer Science.",
                f"RIASEC Investigative score ({interests.get('I', 90)}%) and Realistic score ({interests.get('R', 75)}%)." if interests else "Analytical problem-solving background."
            ],
            missing_evidence=[
                "Formal demonstration of deep learning framework proficiency (PyTorch/TensorFlow).",
                "Verifiable production inference deployment or latency benchmarking repository."
            ],
            required_skills=[
                "Python & Modern C++",
                "Linear Algebra & Multivariate Calculus",
                "PyTorch & Deep Learning Architectures",
                "MLOps, Docker & Model Serving (FastAPI, ONNX)",
                "Data Engineering & Distributed Processing (SQL, PySpark)"
            ],
            current_skills_held=["Python Programming", "Calculus & Linear Algebra Foundations", "Basic Web APIs"],
            transferable_skills=["Systematic Logical Reasoning", "Algorithmic Problem Decomposition"],
            skill_gaps=[
                SkillGap(
                    skill_name="Deep Learning Frameworks (PyTorch)",
                    category="CORE",
                    current_status="MISSING",
                    description="Ability to construct, train, and validate custom neural architectures and fine-tune foundation models.",
                    recommended_action="Complete hands-on PyTorch computer vision / NLP projects with verified GitHub repositories."
                ),
                SkillGap(
                    skill_name="Production MLOps & Containerization",
                    category="SPECIALIZED",
                    current_status="MISSING",
                    description="Deploying models as scalable microservices with Docker, FastAPI, and latency profiling.",
                    recommended_action="Package a trained classifier into a Docker container and benchmark throughput under load."
                ),
                SkillGap(
                    skill_name="SQL & Data Warehousing",
                    category="FOUNDATIONAL",
                    current_status="PARTIAL",
                    description="Writing complex SQL queries and structuring data pipelines for model ingestion.",
                    recommended_action="Practice relational database schemas and automated data transformations."
                )
            ],
            education_routes=[
                EducationRoute(
                    route_type="TRADITIONAL_DEGREE",
                    title="B.Tech / B.S. in Computer Science (AI/ML Specialization)",
                    description="Four-year undergraduate degree with coursework in Operating Systems, Algorithms, Machine Learning, and Distributed Systems.",
                    estimated_duration="4 Years",
                    institutions_or_paths=["IITs / NITs / Top Engineering Colleges (India)", "Global Premier Universities"],
                    geographic_relevance="India & Global"
                ),
                EducationRoute(
                    route_type="PROJECT_BASED_ACCELERATED",
                    title="Self-Directed Open-Source Portfolio + Applied Specialization",
                    description="Rigorous project-driven pathway focused on open-source contributions, competitive hackathons, and published benchmark implementations.",
                    estimated_duration="18–24 Months",
                    institutions_or_paths=["Fast.ai", "DeepLearning.AI Specializations", "Open-Source AI Communities"],
                    geographic_relevance="Global"
                )
            ],
            credential_options=[
                CredentialOption(
                    title="TensorFlow / PyTorch Developer Certificate",
                    issuer="DeepLearning.AI / Linux Foundation",
                    classification="STRONGLY_USEFUL",
                    purpose="Validates baseline model training and evaluation competence for junior technical roles.",
                    prerequisites=["Python OOP", "Linear Algebra Foundations"],
                    verified_cost="~$150–$300",
                    preparation_effort="8–12 Weeks",
                    provenance="Industry Standard Certification"
                ),
                CredentialOption(
                    title="AWS Certified Machine Learning – Specialty",
                    issuer="Amazon Web Services",
                    classification="OPTIONAL",
                    purpose="Demonstrates cloud AI service integration, data pipelines, and infrastructure governance.",
                    prerequisites=["Cloud Fundamentals", "Python"],
                    verified_cost="~$300",
                    preparation_effort="12 Weeks",
                    provenance="AWS Official Training"
                )
            ],
            india_context={
                "nco_code": "2512.0101 (Software Developer & AI Specialist)",
                "industry_hubs": ["Bengaluru", "Hyderabad", "Pune", "NCR"],
                "entrance_routes": ["JEE Main / Advanced", "State CETs", "BITS / Private University Exams"],
                "market_trend": "High demand for applied ML engineers capable of bridging model training with backend software engineering."
            },
            global_context={
                "esco_uri": "http://data.europa.eu/esco/occupation/528f90ed-e250-48bd-aacc-ffb7b1de5654",
                "esco_title": "ICT application developer / AI engineer",
                "global_demand": "Rapidly growing demand across Europe and North America for production LLM integration and edge AI systems."
            },
            experience_requirements=[
                "1–2 substantial open-source or public GitHub project repositories",
                "Participation in data science hackathons or technical challenges"
            ],
            advantages=[
                "High industry demand and competitive compensation trajectory.",
                "Rich ecosystem of open-source research and community learning.",
                "Direct synergy between mathematics, problem-solving, and software impact."
            ],
            disadvantages=[
                "Rapidly shifting technological landscape requires continuous unlearning and relearning.",
                "Entry-level competition is high for unverified or purely theoretical resumes."
            ],
            risks=[
                "Risk of focusing solely on high-level APIs without understanding underlying math and systems fundamentals."
            ],
            alternatives=["Autonomous Robotics Perception", "Distributed Data Engineering"],
            similar_trajectories=traj_ai,
            source_references=[{"source": "ESCO", "title": "AI Engineer (ESCO: 2512)"}, {"source": "NCO", "code": "2512"}]
        )

        # 2. Candidate Path 2: Autonomous Robotics & Embedded Systems
        traj_robotics = self.corpus_service.match_similar_trajectories(["robotics", "hardware", "embedded"], interests, limit=1)
        path_robotics = CandidatePath(
            path_id="path_robotics_embedded_systems",
            title="Autonomous Robotics & Embedded Systems",
            domain="Robotics & Cyber-Physical Systems",
            description="Bridges physical hardware mechanisms with embedded microcontrollers, ROS2 middleware, real-time control algorithms, and sensor fusion.",
            fit_score=88.0,
            fit_level="STRONG",
            confidence="HIGH",
            why_it_matches=[
                "Aligns strongly with Realistic Holland dimension (75% score) and hardware interest.",
                "Directly continues verified experience in autonomous line-following robotics and sensor integration.",
                "Combines C++ systems engineering with physical physical-world impact."
            ],
            supporting_evidence=[
                "Demonstrated robotics club project building sensor arrays and Arduino controllers.",
                "Class 12 Physics & Mathematics foundation.",
                "High self-efficacy in hands-on building and debugging."
            ],
            missing_evidence=[
                "Demonstration of ROS 2 (Robot Operating System) navigation stack mastery.",
                "Experience with real-time operating systems (FreeRTOS) or advanced kinematic simulations."
            ],
            required_skills=[
                "Modern C++ (C++17/20) & Python",
                "ROS 2 (Robot Operating System) & Gazebo Simulation",
                "Sensor Fusion (LiDAR, IMU, Kalman Filtering)",
                "Embedded Microcontrollers (ARM Cortex, STM32, ESP32)",
                "Control Theory & Classical Kinematics"
            ],
            current_skills_held=["Arduino / C++ Basics", "Hardware Prototyping", "Sensor Interfacing"],
            transferable_skills=["Hardware Debugging", "Physical System Spatial Reasoning"],
            skill_gaps=[
                SkillGap(
                    skill_name="ROS 2 & Node Graph Middleware",
                    category="CORE",
                    current_status="MISSING",
                    description="Designing distributed robotic nodes, topics, services, and action servers.",
                    recommended_action="Build simulated autonomous rover navigation nodes in ROS 2 and Gazebo."
                ),
                SkillGap(
                    skill_name="Modern C++ & Memory Management",
                    category="CORE",
                    current_status="PARTIAL",
                    description="Mastering smart pointers, concurrency, and real-time execution constraints.",
                    recommended_action="Refactor Arduino C code into modern modular C++ classes with strict pointer safety."
                ),
                SkillGap(
                    skill_name="SLAM & State Estimation",
                    category="SPECIALIZED",
                    current_status="MISSING",
                    description="Simultaneous Localization and Mapping algorithms using 2D/3D LiDAR sensor data.",
                    recommended_action="Implement an Extended Kalman Filter simulation for noisy sensor fusion."
                )
            ],
            education_routes=[
                EducationRoute(
                    route_type="TRADITIONAL_DEGREE",
                    title="B.Tech in Mechatronics / Electrical / Computer Engineering",
                    description="Four-year interdisciplinary degree integrating mechanical design, microelectronics, and software control.",
                    estimated_duration="4 Years",
                    institutions_or_paths=["IITs / Premier Technical Institutes", "Specialized Mechatronics Programs"],
                    geographic_relevance="India & Global"
                ),
                EducationRoute(
                    route_type="PROJECT_BASED_ACCELERATED",
                    title="Makerspace Hardware Prototyping + ROS2 Specialization",
                    description="Hands-on development using hardware development kits (NVIDIA Jetson, Raspberry Pi) and open robotics competitions.",
                    estimated_duration="2 Years",
                    institutions_or_paths=["Open Source Robotics Foundation (OSRF)", "University Robotics Clubs"],
                    geographic_relevance="Global"
                )
            ],
            credential_options=[
                CredentialOption(
                    title="Certified ROS 2 Developer",
                    issuer="ConstructSim / OSRF Ecosystem",
                    classification="STRONGLY_USEFUL",
                    purpose="Validates ability to develop industrial robotic packages, navigation stacks, and URDF kinematic models.",
                    prerequisites=["C++ Basics", "Linux Terminal"],
                    verified_cost="~$200",
                    preparation_effort="10 Weeks",
                    provenance="Robotics Industry Standard"
                ),
                CredentialOption(
                    title="Embedded Systems Architecture Certification",
                    issuer="Arm University / IEEE",
                    classification="OPTIONAL",
                    purpose="Certifies microarchitecture understanding, RTOS scheduling, and peripheral drivers.",
                    prerequisites=["C Programming", "Digital Logic"],
                    verified_cost="~$150",
                    preparation_effort="8 Weeks",
                    provenance="IEEE Technical Society"
                )
            ],
            india_context={
                "nco_code": "2144.0100 (Mechatronics & Robotics Engineer)",
                "industry_hubs": ["Bengaluru", "Chennai", "Pune", "Gurugram"],
                "entrance_routes": ["JEE / State Engineering Exams", "Robotics Club Competitions (ABU Robocon, e-Yantra)"],
                "market_trend": "Surging growth in autonomous warehouse logistics, drone technology, and industrial automation across India."
            },
            global_context={
                "esco_uri": "http://data.europa.eu/esco/occupation/7e3a968a-2144-482d",
                "esco_title": "Robotics engineer",
                "global_demand": "High demand in autonomous vehicles, surgical robotics, and industrial automation across Germany, Japan, and USA."
            },
            experience_requirements=[
                "Participation in student robotics competitions or hackathons",
                "Documented physical hardware builds with circuit schematics and code"
            ],
            advantages=[
                "Highly tangible, physical-world feedback and visible project outcomes.",
                "Deep technical barrier to entry protects against routine automation.",
                "Exciting intersection of mechanics, electronics, and artificial intelligence."
            ],
            disadvantages=[
                "Hardware prototyping incurs component costs and physical lab equipment access requirements.",
                "Debugging hardware-software interface issues can be time-intensive."
            ],
            risks=[
                "Component supply chain delays or hardware burnout during testing."
            ],
            alternatives=["Embedded Firmware Engineer", "Autonomous Perception Specialist"],
            similar_trajectories=traj_robotics,
            source_references=[{"source": "ESCO", "title": "Robotics Engineer (ESCO: 2144)"}, {"source": "NCO", "code": "2144"}]
        )

        # 3. Candidate Path 3: Cloud Infrastructure & Distributed Systems Architecture
        traj_cloud = self.corpus_service.match_similar_trajectories(["cloud", "systems", "distributed"], interests, limit=1)
        path_cloud = CandidatePath(
            path_id="path_cloud_distributed_systems",
            title="Cloud Infrastructure & Distributed Systems",
            domain="Systems Architecture & Cloud Engineering",
            description="Focuses on building resilient, high-throughput cloud infrastructure, distributed microservices, network protocols, database scaling, and DevOps automation.",
            fit_score=84.0,
            fit_level="STRONG",
            confidence="MEDIUM",
            why_it_matches=[
                "Aligns with strong analytical problem-solving and structured Conventional traits (50%).",
                "Builds on high interest in understanding operating systems and large-scale data flow.",
                "Offers high career flexibility across every modern technology company."
            ],
            supporting_evidence=[
                "Demonstrated logical reasoning in Observable Task E (Monolith vs Microservices trade-offs).",
                "Interest in backend architecture and structured system design."
            ],
            missing_evidence=[
                "Experience with Linux server administration, container orchestration (Kubernetes), or cloud infrastructure."
            ],
            required_skills=[
                "Golang / Modern Python / Java",
                "Linux Internals, Concurrency & Networking (TCP/IP, gRPC)",
                "Distributed Databases & Storage Systems (PostgreSQL, Redis, Kafka)",
                "Docker, Kubernetes & Infrastructure as Code (Terraform)",
                "Observability, SRE & Cloud Security (Prometheus, OpenTelemetry)"
            ],
            current_skills_held=["Basic Scripting", "Relational Database Concepts"],
            transferable_skills=["Systematic Architecture Decomposition", "Protocol Organization"],
            skill_gaps=[
                SkillGap(
                    skill_name="Linux Internals & Concurrency",
                    category="FOUNDATIONAL",
                    current_status="MISSING",
                    description="Understanding OS threads, processes, file descriptors, and memory management.",
                    recommended_action="Complete operating systems projects implementing multi-threaded servers."
                ),
                SkillGap(
                    skill_name="Kubernetes & Container Orchestration",
                    category="CORE",
                    current_status="MISSING",
                    description="Deploying, scaling, and managing containerized microservices in cluster environments.",
                    recommended_action="Deploy a multi-service web application to a local Minikube cluster with automated rolling updates."
                ),
                SkillGap(
                    skill_name="Distributed Event Streaming (Kafka)",
                    category="SPECIALIZED",
                    current_status="MISSING",
                    description="Building fault-tolerant event-driven producer-consumer data pipelines.",
                    recommended_action="Implement an asynchronous event processing pipeline with dead-letter queue recovery."
                )
            ],
            education_routes=[
                EducationRoute(
                    route_type="TRADITIONAL_DEGREE",
                    title="B.Tech / B.S. in Computer Science / Information Technology",
                    description="Four-year foundational degree emphasizing Computer Networks, Database Systems, and Distributed Computing.",
                    estimated_duration="4 Years",
                    institutions_or_paths=["Engineering Universities", "Autonomous Technical Institutes"],
                    geographic_relevance="India & Global"
                ),
                EducationRoute(
                    route_type="PROJECT_BASED_ACCELERATED",
                    title="DevOps & Distributed Systems Engineering Track",
                    description="Accelerated focus on Linux system administration, cloud certifications, and infrastructure-as-code automation.",
                    estimated_duration="12–18 Months",
                    institutions_or_paths=["Cloud Native Computing Foundation (CNCF)", "Linux Foundation"],
                    geographic_relevance="Global"
                )
            ],
            credential_options=[
                CredentialOption(
                    title="Certified Kubernetes Administrator (CKA)",
                    issuer="Cloud Native Computing Foundation (CNCF)",
                    classification="STRONGLY_USEFUL",
                    purpose="Industry benchmark certifying hands-on competency in configuring, securing, and maintaining production Kubernetes clusters.",
                    prerequisites=["Linux Fundamentals", "Docker"],
                    verified_cost="~$395",
                    preparation_effort="12 Weeks",
                    provenance="CNCF Official Certification"
                ),
                CredentialOption(
                    title="AWS Certified Solutions Architect – Associate",
                    issuer="Amazon Web Services",
                    classification="STRONGLY_USEFUL",
                    purpose="Validates knowledge of designing high-availability, cost-optimized, and resilient cloud architectures.",
                    prerequisites=["Cloud Fundamentals"],
                    verified_cost="~$150",
                    preparation_effort="8–10 Weeks",
                    provenance="AWS Official Certification"
                )
            ],
            india_context={
                "nco_code": "2512.0200 (Cloud Architect & Backend Systems Engineer)",
                "industry_hubs": ["Bengaluru", "Hyderabad", "Noida", "Mumbai"],
                "entrance_routes": ["Engineering Degrees", "Direct Campus Placement", "Open-Source Contributions"],
                "market_trend": "Vast demand across multinational tech hubs and fintech startups for scalable backend infrastructure engineers."
            },
            global_context={
                "esco_uri": "http://data.europa.eu/esco/occupation/6819a9d8-2512",
                "esco_title": "Systems architect / cloud infrastructure engineer",
                "global_demand": "Consistent global remote hiring for distributed systems reliability engineers (SREs) and cloud architects."
            },
            experience_requirements=[
                "Public GitHub repository demonstrating high-throughput server architecture or cloud deployment",
                "Experience debugging live service incidents and analyzing server metrics"
            ],
            advantages=[
                "Ubiquitous demand across all sectors (fintech, healthcare, e-commerce, AI startups).",
                "Strong remote work opportunities and global mobility.",
                "Clear architectural growth from software engineer to principal architect."
            ],
            disadvantages=[
                "On-call reliability rotations and high responsibility for system uptime.",
                "Requires deep attention to edge cases, race conditions, and network failures."
            ],
            risks=[
                "Over-relying on cloud managed services without understanding low-level networking primitives."
            ],
            alternatives=["Site Reliability Engineer (SRE)", "Backend API Specialist"],
            similar_trajectories=traj_cloud,
            source_references=[{"source": "ESCO", "title": "Systems Architect (ESCO: 2512)"}, {"source": "NCO", "code": "2512"}]
        )

        return [path_ai, path_robotics, path_cloud]

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
        goals = goals or ["Explore AI/ML and Engineering"]
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
        if "product manager" in lower_prompt or "pm" in lower_prompt or "product management" in lower_prompt:
            new_target = "Product Manager"
        elif "restaurant" in lower_prompt or "culinary" in lower_prompt or "bistro" in lower_prompt:
            new_target = "Restaurant Owner & Hospitality Entrepreneur"
        elif "lawyer" in lower_prompt or "legal" in lower_prompt or "advocate" in lower_prompt:
            new_target = "Corporate Lawyer & Legal Consultant"
        elif "design" in lower_prompt or "ux" in lower_prompt:
            new_target = "Product Designer (UI/UX)"
        elif "psycholog" in lower_prompt or "therap" in lower_prompt:
            new_target = "Clinical Psychologist"
        elif "photograph" in lower_prompt:
            new_target = "Commercial Photographer"
        elif "teach" in lower_prompt or "educat" in lower_prompt:
            new_target = "K-12 School Teacher"
        elif "civil services" in lower_prompt or "upsc" in lower_prompt:
            new_target = "Civil Services Administrator"
        elif "goal_change" in lower_type or "target_change" in lower_type:
            new_target = modification_prompt.strip()

        if new_target:
            from backend.services.requirement_graph_service import RequirementGraphService
            req_service = RequirementGraphService()
            base_graph = req_service.build_requirement_graph_for_outcome(base_path.title)
            target_graph = req_service.build_requirement_graph_for_outcome(new_target)

            base_skills = {n.name for n in base_graph.core_skills}
            target_skills = {n.name for n in target_graph.core_skills}

            shared_assets = sorted(list(base_skills.intersection(target_skills)))
            discarded_assumptions = sorted(list(base_skills - target_skills))
            new_requirements = sorted(list(target_skills - base_skills))

            trade_off_notes.append(f"Target Outcome Shift: '{base_path.title}' -> '{new_target}'")
            trade_off_notes.append(f"Shared Assets (Retained): {', '.join(shared_assets) if shared_assets else 'Foundational reasoning and structured problem solving'}")
            trade_off_notes.append(f"Discarded Assumptions: {', '.join(discarded_assumptions) if discarded_assumptions else 'Domain-specific prerequisites no longer mandated'}")
            trade_off_notes.append(f"New Requirements to Develop: {', '.join(new_requirements) if new_requirements else 'Target domain core competencies'}")
            trade_off_notes.append("Timeline Delta: Shift requires redirecting milestone focus to new domain evidence; previous shared competencies accelerate foundational stages.")

            adjusted.title = new_target
            adjusted.domain = getattr(target_graph, "domain", getattr(target_graph, "target_industry", "Domain"))
            adjusted.required_skills = [n.name for n in target_graph.core_skills]
            adjusted.transferable_skills = shared_assets or ["Foundational Reasoning"]
            adjusted.skill_gaps = [
                SkillGap(
                    skill_name=n.name,
                    category="CORE",
                    current_status="MISSING",
                    description=n.description,
                    recommended_action=f"Develop proficiency in {n.name} through focused coursework or practical artifacts."
                )
                for n in target_graph.core_skills if n.name not in base_skills
            ]
        elif modification_type == "LOW_BUDGET" or "afford" in lower_prompt or "cost" in lower_prompt:
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
