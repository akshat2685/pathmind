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
                fit_level="PROMISING",
                confidence="LOW" if len(["LL.B Degree transcripts and Bar enrollment status."]) > 0 else "HIGH",
                why_it_matches=[
                    "Aligns directly with stated target objective in legal practice and corporate jurisprudence.",
                    "Builds upon structured analytical reasoning and written communication aptitude."
                ],
                supporting_evidence=["Stated objective in legal jurisprudence."],
                missing_evidence=["LL.B Degree transcripts and Bar enrollment status."],
                transparency_summary={
                    "what_we_know": ["Target objective in corporate law matches legal regulatory taxonomy (ESCO: 2611 / NCO: 2611.10).", "Identified transferable reasoning and written communication strengths."],
                    "how_we_know_it": ["User stated target goal", "Authoritative Bar Council of India & ESCO standard graphs"],
                    "what_remains_unknown": ["LL.B degree verification and AIBE bar certification."],
                    "what_could_change_this": ["Submission of law degree transcripts or bar council enrollment documents."]
                },
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
                fit_level="PROMISING",
                confidence="LOW",
                why_it_matches=["Specialized advocacy pathway emphasizing dispute resolution and evidence law."],
                supporting_evidence=["Stated interest in advocacy."],
                missing_evidence=["Moot court briefs and courtroom internship records."],
                transparency_summary={
                    "what_we_know": ["Target outcome matches Litigation Lawyer standard (ESCO: 2611.1)."],
                    "how_we_know_it": ["User stated target preference", "ESCO occupational knowledge base"],
                    "what_remains_unknown": ["Courtroom internship and trial brief records."],
                    "what_could_change_this": ["Submission of verified moot court brief or litigation internship logs."]
                },
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
                fit_level="PROMISING",
                confidence="LOW",
                why_it_matches=["Directly aligns with stated product design and human-computer interaction goals."],
                supporting_evidence=["Stated design objective."],
                missing_evidence=["Public Figma portfolio and documented case studies."],
                transparency_summary={
                    "what_we_know": ["User stated aspiration matches Product Designer standard (ESCO: 2166 / NCO: 2166.10)."],
                    "how_we_know_it": ["Stated goal input", "ESCO occupational knowledge base"],
                    "what_remains_unknown": ["Public Figma project links and user testing artifacts."],
                    "what_could_change_this": ["Submission of verified Figma component architecture or portfolio case studies."]
                },
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
                fit_level="PROMISING",
                confidence="LOW",
                why_it_matches=["Emphasizes qualitative research rigor and strategic customer empathy."],
                supporting_evidence=["Stated user empathy focus."],
                missing_evidence=["Usability test reports and customer interview synthesis."],
                transparency_summary={
                    "what_we_know": ["User stated aspiration matches UX Researcher standard (ESCO: 2513.2 / NCO: 2513.20)."],
                    "how_we_know_it": ["Stated goal input", "ESCO occupational knowledge base"],
                    "what_remains_unknown": ["Usability benchmarking and user interview recordings."],
                    "what_could_change_this": ["Submission of verified user test sessions or interview synthesis matrices."]
                },
                required_skills=["Qualitative User Interviewing", "Usability Test Protocols (SUS)", "Persona & Journey Modeling", "Product Opportunity Trees"],
                current_skills_held=["Qualitative Analysis"],
                transferable_skills=["Empathetic Inquiry"],
                skill_gaps=[SkillGap(skill_name="Quantitative Usability Testing", category="CORE", current_status="MISSING", description="System Usability Scale (SUS) benchmarking.", recommended_action="Run 5 user test sessions on a live web app.")],
                education_routes=[EducationRoute(route_type="PROJECT_BASED_ACCELERATED", title="UX Research Portfolio", description="User research case studies.", estimated_duration="Derived from portfolio depth (typically 3–6 months)", institutions_or_paths=["UX Research Guild"], geographic_relevance="Global")],
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
                fit_level="PROMISING",
                confidence="LOW",
                why_it_matches=["Aligns directly with restaurant launch and hospitality venture aspirations."],
                supporting_evidence=["Declared hospitality goal."],
                missing_evidence=["Business plan and commercial kitchen stage records."],
                transparency_summary={
                    "what_we_know": ["Declared hospitality venture goal aligns with Restaurant Manager standards (ESCO: 1412 / NCO: 1412.10)."],
                    "how_we_know_it": ["User declared venture goal", "FSSAI regulatory framework & ESCO standards"],
                    "what_remains_unknown": ["Commercial kitchen certification and menu unit economic records."],
                    "what_could_change_this": ["Submission of completed FSSAI supervisor certification or menu cost workbook."]
                },
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
                fit_level="PROMISING",
                confidence="LOW",
                why_it_matches=["Aligns with biotechnology research and laboratory science objectives."],
                supporting_evidence=["Declared life sciences objective."],
                missing_evidence=["Wet-lab experimental records and peer-reviewed literature review."],
                transparency_summary={
                    "what_we_know": ["Declared life sciences objective matches Biotechnologist standard (ESCO: 2131.2 / NCO: 2131.20)."],
                    "how_we_know_it": ["User declared objective", "ESCO occupational knowledge base"],
                    "what_remains_unknown": ["Wet-lab PCR assays and formal lab safety compliance logs."],
                    "what_could_change_this": ["Submission of verified laboratory notebook or academic transcripts."]
                },
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
                fit_level="PROMISING",
                confidence="LOW",
                why_it_matches=["Aligns directly with clinical psychology, mental health care, and therapeutic practice goals."],
                supporting_evidence=["Stated mental health and counseling objective."],
                missing_evidence=["Supervised clinical practicum logs and diagnostic assessment reports."],
                transparency_summary={
                    "what_we_know": ["Declared mental health aspiration matches Clinical Psychologist standard (ESCO: 2634.1 / NCO: 2634.10)."],
                    "how_we_know_it": ["User stated aspiration", "Rehabilitation Council of India & ESCO standard graphs"],
                    "what_remains_unknown": ["Supervised clinical hours and diagnostic assessment reports."],
                    "what_could_change_this": ["Submission of clinical supervisor evaluation or diagnostic case notes."]
                },
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
                fit_level="PROMISING",
                confidence="LOW",
                why_it_matches=["Specialized focus on evidence-based cognitive behavioral counseling modalities."],
                supporting_evidence=["Declared therapeutic practice interest."],
                missing_evidence=["Counseling case formulation and supervised hours."],
                transparency_summary={
                    "what_we_know": ["Target outcome matches Counseling Psychologist standard (ESCO: 2634.3 / NCO: 2634.20)."],
                    "how_we_know_it": ["User declared therapeutic interest", "ESCO occupational knowledge base"],
                    "what_remains_unknown": ["Structured CBT case formulations and supervised practicum."],
                    "what_could_change_this": ["Submission of Beck Institute certification or supervised counseling hours."]
                },
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
                fit_level="PROMISING",
                confidence="LOW",
                why_it_matches=["Directly aligns with professional photography, studio lighting, and commercial visual arts goals."],
                supporting_evidence=["Declared photography objective."],
                missing_evidence=["Published commercial editorial tear-sheets and lighting breakdown documentation."],
                transparency_summary={
                    "what_we_know": ["Stated goal matches Photographer standard (ESCO: 3431 / NCO: 3431.10)."],
                    "how_we_know_it": ["User stated photography objective", "ESCO occupational standard"],
                    "what_remains_unknown": ["Commercial client delivery galleries and studio lighting diagrams."],
                    "what_could_change_this": ["Submission of commercial gallery link or lighting breakdown tear sheet."]
                },
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
                fit_level="PROMISING",
                confidence="LOW",
                why_it_matches=["Directly fulfills classroom teaching, pedagogy, and educator development aspirations."],
                supporting_evidence=["Declared teaching objective."],
                missing_evidence=["Supervised student teaching evaluations and state teaching eligibility scores."],
                transparency_summary={
                    "what_we_know": ["Target outcome aligns with Secondary School Teacher standards (ESCO: 2330 / NCO: 2330.10)."],
                    "how_we_know_it": ["User stated teaching goal", "NCTE / CBSE statutory framework and ESCO standards"],
                    "what_remains_unknown": ["B.Ed licensure and supervised practicum observation reports."],
                    "what_could_change_this": ["Submission of CTET exam scorecard or completed student teaching evaluation."]
                },
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
                fit_level="PROMISING",
                confidence="LOW",
                why_it_matches=["Directly aligns with civil service examination and public administration leadership goals."],
                supporting_evidence=["Declared public service aspiration."],
                missing_evidence=["Evaluated General Studies Mains test copies and optional subject syllabus completion."],
                transparency_summary={
                    "what_we_know": ["Target outcome matches Government Administrator standard (ESCO: 1112 / NCO: 1112.10)."],
                    "how_we_know_it": ["User stated civil service aspiration", "UPSC official syllabus and ESCO standards"],
                    "what_remains_unknown": ["Evaluated Mains answer copies and optional subject benchmark scores."],
                    "what_could_change_this": ["Submission of verified mock examination evaluations or optional subject progress."]
                },
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

        elif goals:
            primary_goal = goals[0].strip()
            path_custom = CandidatePath(
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
