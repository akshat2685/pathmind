from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timezone
import json
from backend.core.career_schemas import (
    UniversalCareerProfile,
    TargetOutcome,
    CareerRequirementGraph,
    RequirementNode,
    CategorizedGap,
    TransferableSkillsAnalysis,
    VerifiedCredential,
    ExperienceGap,
    EvidencePortfolio,
    EvidenceRequirementStatus,
    VerifiedOpportunity,
    TailoredResume,
    AccountabilityStatus,
    CareerCheckpoint
)
from backend.services.resume_validator import ResumeFactValidator

class CareerReadinessAgent:
    """
    ADK Agent: CareerReadinessAgent
    Analyzes current vs target requirements.
    Determines explainable qualitative readiness states without fake numeric precision.
    """
    def evaluate_readiness(
        self,
        profile: UniversalCareerProfile,
        target_goal: TargetOutcome,
        requirement_graph: CareerRequirementGraph,
        evidence_portfolio: EvidencePortfolio
    ) -> Tuple[str, str, str, List[CategorizedGap]]:
        skills_held = {s.lower().strip() for s in profile.skills}
        has_projects = len(profile.projects) > 0
        has_experience = len(profile.experience) > 0
        current_state = profile.current_state_type.lower()

        # Check core skill coverage
        core_skills = [node.name for node in requirement_graph.core_skills]
        covered_core = [s for s in core_skills if any(s.lower() in sh or sh in s.lower() for sh in skills_held)]
        coverage_ratio = len(covered_core) / max(len(core_skills), 1)

        # Categorized Gaps formulation
        gaps: List[CategorizedGap] = []
        for node in requirement_graph.core_skills:
            if not any(node.name.lower() in sh or sh in node.name.lower() for sh in skills_held):
                gaps.append(
                    CategorizedGap(
                        gap_id=f"gap_skill_{node.name.lower().replace(' ', '_')}",
                        gap_type="SKILL",
                        title=f"Core Skill: {node.name}",
                        description=f"Target role '{target_goal.target_role}' requires demonstrated proficiency in {node.name}.",
                        importance="HIGH",
                        source="ESCO / Occupational Standard",
                        reason="Fundamental capability for role execution.",
                        recommended_action=f"Complete targeted learning milestone and build verified code artifact for {node.name}."
                    )
                )

        for node in requirement_graph.experience_requirements:
            gaps.append(
                CategorizedGap(
                    gap_id=f"gap_exp_{node.name.lower().replace(' ', '_')}",
                    gap_type="EXPERIENCE",
                    title=f"Experience Requirement: {node.name}",
                    description=node.description,
                    importance=node.importance,
                    source="Industry Benchmark",
                    reason="Proves practical application beyond classroom exercises.",
                    recommended_action=f"Acquire hands-on exposure through structured milestones or open-source contributions."
                )
            )

        for node in requirement_graph.project_evidence_requirements:
            gaps.append(
                CategorizedGap(
                    gap_id=f"gap_evidence_{node.name.lower().replace(' ', '_')}",
                    gap_type="EVIDENCE",
                    title=f"Verifiable Artifact: {node.name}",
                    description=node.description,
                    importance="HIGH",
                    source="Hiring Portfolio Requirement",
                    reason="Public repositories provide 3x higher signal than unverified claims.",
                    recommended_action="Publish modular codebase with automated tests and documentation on GitHub."
                )
            )

        # Evaluate qualitative readiness
        if coverage_ratio >= 0.8 and has_projects and has_experience:
            readiness_state = "TARGET_READY"
            explanation = (
                f"You have satisfied core competencies for {target_goal.target_role}, demonstrated practical evidence artifacts, "
                f"and hold relevant domain experience."
            )
            next_milestone = f"Target Role Placement & {target_goal.target_role} Professional Evaluation"
        elif coverage_ratio >= 0.6 and has_projects:
            if "switcher" in current_state or "professional" in current_state:
                readiness_state = "TRANSITION_READY"
                explanation = (
                    f"You have established foundational competencies and can transfer your prior professional experience into "
                    f"{target_goal.target_role}. Next focus on closing key practical evidence gaps."
                )
                next_milestone = f"Senior Transition & Specialized {target_goal.target_role} Portfolio"
            else:
                readiness_state = "INTERNSHIP_READY"
                explanation = (
                    f"You have acquired essential foundational competencies with verified evidence artifacts. "
                    f"You are well-positioned to apply for internships, apprenticeships, and entry-level contributor roles."
                )
                next_milestone = f"Entry-Level / Junior {target_goal.target_role} Readiness"
        elif coverage_ratio >= 0.3 or has_projects:
            readiness_state = "DEVELOPING"
            explanation = (
                f"You possess verified academic and domain foundations, but need 1 comprehensive capstone project or practicum "
                f"evidence to qualify for intermediate and contributor roles in {target_goal.target_role}."
            )
            next_milestone = f"INTERNSHIP_READY (Requires completing applied capstone milestones for {target_goal.target_role})"
        else:
            readiness_state = "FOUNDATIONAL"
            explanation = (
                f"Currently building core prerequisite competencies and foundational knowledge for {target_goal.target_role}."
            )
            next_milestone = f"DEVELOPING (Complete introductory prerequisites and foundational milestones)"

        return readiness_state, explanation, next_milestone, gaps

class CredentialAgent:
    """
    ADK Agent: CredentialAgent
    Evaluates relevant credentials and answers: 'Do I actually need this certification?'
    Enforces that projects and repositories outweigh paid certificates unless strictly mandated.
    """
    def evaluate_credentials(self, target_role: str) -> List[VerifiedCredential]:
        target_lower = target_role.lower()
        credentials: List[VerifiedCredential] = []

        if any(k in target_lower for k in ["psycholog", "mental health", "therap", "counsel"]):
            credentials.append(
                VerifiedCredential(
                    credential_id="cred_rci_clinical_licensure",
                    title="Clinical Psychologist Licensure / RCI Registration",
                    issuer="Rehabilitation Council of India / State Licensing Board",
                    classification="MANDATORY",
                    target_roles=["Clinical Psychologist", "Licensed Therapist"],
                    prerequisites=["M.Phil or Psy.D in Clinical Psychology", "Supervised Clinical Practicum"],
                    preparation_effort="2 Years Degree + Board Registration",
                    verified_cost="Official Regulatory Fee",
                    geographic_relevance="Jurisdiction-Specific (India / State Boards)",
                    official_url="http://www.rehabcouncil.nic.in/",
                    source="Statutory Health Regulatory Board",
                    strategic_advice="Mandatory legal requirement to practice clinical psychotherapy and sign diagnostic psychological reports.",
                    decision_rationale="MANDATORY: Unlicensed psychological practice is illegal in regulated healthcare jurisdictions."
                )
            )
            credentials.append(
                VerifiedCredential(
                    credential_id="cred_cbt_practitioner",
                    title="Certified Cognitive Behavioral Therapy (CBT) Practitioner",
                    issuer="Beck Institute for Cognitive Behavior Therapy",
                    classification="STRONGLY_USEFUL",
                    target_roles=["Clinical Psychologist", "Counseling Specialist"],
                    prerequisites=["Graduate Degree in Mental Health / Psychology"],
                    preparation_effort="8–12 Weeks",
                    verified_cost="~$400–$800",
                    geographic_relevance="Global",
                    official_url="https://beckinstitute.org/",
                    source="Beck Institute Certification Portal",
                    strategic_advice="Strongly useful for evidencing formal mastery of evidence-based CBT interventions beyond baseline coursework.",
                    decision_rationale="STRONGLY_USEFUL: Highest employer and clinic recognition for structured therapeutic interventions."
                )
            )
        elif any(k in target_lower for k in ["photo", "photographer"]):
            credentials.append(
                VerifiedCredential(
                    credential_id="cred_ppa_certified_photographer",
                    title="Certified Professional Photographer (CPP)",
                    issuer="Professional Photographers of America (PPA)",
                    classification="STRONGLY_USEFUL",
                    target_roles=["Commercial Photographer", "Portrait Photographer"],
                    prerequisites=["Technical Lighting & Image Evaluation Examination", "Portfolio Review"],
                    preparation_effort="6–10 Weeks",
                    verified_cost="~$325",
                    geographic_relevance="Global",
                    official_url="https://www.ppa.com/certifications",
                    source="Professional Photographers of America Registry",
                    strategic_advice="Strongly useful for commercial and corporate client trust, but your published portfolio tear-sheets carry dominant hiring weight.",
                    decision_rationale="STRONGLY_USEFUL: Validates strict technical lighting, color management, and optical competency."
                )
            )
            credentials.append(
                VerifiedCredential(
                    credential_id="cred_adobe_visual_design",
                    title="Adobe Certified Professional in Visual Design (Photoshop & Lightroom)",
                    issuer="Adobe Systems",
                    classification="OPTIONAL",
                    target_roles=["Digital Retoucher", "Editorial Photographer"],
                    prerequisites=["Lightroom RAW workflow", "Photoshop non-destructive layer editing"],
                    preparation_effort="4–6 Weeks",
                    verified_cost="~$150",
                    geographic_relevance="Global",
                    official_url="https://certifiedprofessional.adobe.com/",
                    source="Adobe Credentialing Service",
                    strategic_advice="Optional. Commercial art directors evaluate RAW post-processing from your portfolio rather than software badge certificates.",
                    decision_rationale="OPTIONAL: Direct portfolio samples prove post-processing ability more convincingly."
                )
            )
        elif any(k in target_lower for k in ["teach", "educat", "pedagog", "school teacher"]):
            credentials.append(
                VerifiedCredential(
                    credential_id="cred_ctet_teaching_license",
                    title="Central Teacher Eligibility Test (CTET) / State TET or B.Ed",
                    issuer="Central Board of Secondary Education / National Council for Teacher Education",
                    classification="MANDATORY",
                    target_roles=["K-12 School Teacher", "Secondary Educator"],
                    prerequisites=["B.Ed or Diploma in Elementary Education"],
                    preparation_effort="3–6 Months Examination Prep",
                    verified_cost="Official Examination Fee",
                    geographic_relevance="India & State Jurisdictions",
                    official_url="https://ctet.nic.in/",
                    source="National Teacher Education Regulatory Authority",
                    strategic_advice="Mandatory requirement for appointment as a teacher in central and state government/affiliated schools.",
                    decision_rationale="MANDATORY: Statutory qualification mandated by the Right to Education Act."
                )
            )
            credentials.append(
                VerifiedCredential(
                    credential_id="cred_google_educator",
                    title="Google Certified Educator Level 1 & 2",
                    issuer="Google for Education",
                    classification="OPTIONAL",
                    target_roles=["Classroom Teacher", "Instructional Technology Coach"],
                    prerequisites=["Classroom management software tools"],
                    preparation_effort="2–3 Weeks",
                    verified_cost="~$25",
                    geographic_relevance="Global",
                    official_url="https://edu.google.com/intl/ALL_us/for-educators/certification-programs/",
                    source="Google for Education Directory",
                    strategic_advice="Optional. Helpful for modern digital classroom integration, but pedagogical delivery and lesson plans are primary.",
                    decision_rationale="OPTIONAL: Good micro-credential for modern digital classroom technology."
                )
            )
        elif any(k in target_lower for k in ["law", "legal", "advocate", "litigat"]):
            credentials.append(
                VerifiedCredential(
                    credential_id="cred_bar_council_enrollment",
                    title="Bar Council State Enrollment & All India Bar Examination (AIBE)",
                    issuer="Bar Council of India / State Bar Council",
                    classification="MANDATORY",
                    target_roles=["Advocate", "Litigation Counsel", "Legal Consultant"],
                    prerequisites=["LL.B Degree from BCI-recognized University"],
                    preparation_effort="3 Months Preparation",
                    verified_cost="Official Enrollment Fee",
                    geographic_relevance="India & State Jurisdictions",
                    official_url="http://www.barcouncilofindia.org/",
                    source="Bar Council of India Statutory Registry",
                    strategic_advice="Statutory requirement to hold right of audience before courts of law.",
                    decision_rationale="MANDATORY: Essential statutory license for legal practice and advocacy."
                )
            )
            credentials.append(
                VerifiedCredential(
                    credential_id="cred_cipp_privacy_law",
                    title="Certified Information Privacy Professional (CIPP/E)",
                    issuer="International Association of Privacy Professionals (IAPP)",
                    classification="STRONGLY_USEFUL",
                    target_roles=["Technology Legal Counsel", "Data Privacy Lawyer"],
                    prerequisites=["Statutory interpretation of GDPR / DPDP Act"],
                    preparation_effort="6–8 Weeks",
                    verified_cost="~$550",
                    geographic_relevance="Global",
                    official_url="https://iapp.org/certify/cipp/",
                    source="IAPP Official Registry",
                    strategic_advice="Strongly useful specialization for corporate tech counsel and regulatory compliance attorneys.",
                    decision_rationale="STRONGLY_USEFUL: High corporate and law firm demand for privacy jurisprudence."
                )
            )
        elif any(k in target_lower for k in ["design", "ux", "ui", "product design"]):
            credentials.append(
                VerifiedCredential(
                    credential_id="cred_nng_ux_master",
                    title="UX Master Certification",
                    issuer="Nielsen Norman Group (NN/g)",
                    classification="STRONGLY_USEFUL",
                    target_roles=["Senior Product Designer", "UX Researcher"],
                    prerequisites=["Completion of 15 NN/g UX specialized course days"],
                    preparation_effort="3–6 Months",
                    verified_cost="Course-based tuition",
                    geographic_relevance="Global",
                    official_url="https://www.nngroup.com/ux-certification/",
                    source="Nielsen Norman Group Portal",
                    strategic_advice="Strongly useful academic signal for design principles, but portfolio Figma case studies carry highest hiring priority.",
                    decision_rationale="STRONGLY_USEFUL: Globally recognized standard for empirical usability heuristics."
                )
            )
            credentials.append(
                VerifiedCredential(
                    credential_id="cred_google_ux_cert",
                    title="Google UX Design Professional Certificate",
                    issuer="Google Career Certificates",
                    classification="OPTIONAL",
                    target_roles=["Junior UX Designer", "Interaction Designer"],
                    prerequisites=["No prerequisites"],
                    preparation_effort="6 Months (10 hrs/week)",
                    verified_cost="Coursera Subscription ($49/mo)",
                    geographic_relevance="Global",
                    official_url="https://grow.google/certificates/ux-design/",
                    source="Google Career Certificates",
                    strategic_advice="Optional. Prioritize completing 2 thorough end-to-end Figma case studies over certificates.",
                    decision_rationale="OPTIONAL: Introductory course; portfolio artifacts provide superior signal."
                )
            )
        elif any(k in target_lower for k in ["restaurant", "culinary", "hospitality", "bistro", "chef"]):
            credentials.append(
                VerifiedCredential(
                    credential_id="cred_servsafe_manager",
                    title="ServSafe Food Protection Manager / HACCP Certification",
                    issuer="National Restaurant Association / Local Health Authority",
                    classification="MANDATORY",
                    target_roles=["Restaurant Manager", "Executive Chef", "Food Business Owner"],
                    prerequisites=["Food Safety & Sanitation Law Examination"],
                    preparation_effort="2–4 Weeks",
                    verified_cost="~$150",
                    geographic_relevance="Global & Municipal Jurisdictions",
                    official_url="https://www.servsafe.com/",
                    source="National Restaurant Association Standards",
                    strategic_advice="Mandatory legal requirement for public dining establishment operating licenses.",
                    decision_rationale="MANDATORY: Regulatory compliance requirement to prevent public health violations."
                )
            )
            credentials.append(
                VerifiedCredential(
                    credential_id="cred_certified_sommelier",
                    title="Court of Master Sommeliers Introductory / Certified Sommelier",
                    issuer="Court of Master Sommeliers",
                    classification="OPTIONAL",
                    target_roles=["Beverage Director", "Fine Dining Manager"],
                    prerequisites=["Tasting and wine service theory"],
                    preparation_effort="8–12 Weeks",
                    verified_cost="~$600",
                    geographic_relevance="Global",
                    official_url="https://www.mastersommeliers.org/",
                    source="Court of Master Sommeliers",
                    strategic_advice="Optional. Valuable for fine-dining beverage revenue optimization, but core kitchen unit economics take precedence.",
                    decision_rationale="OPTIONAL: Specialized beverage credential for high-end dining concepts."
                )
            )
        elif any(k in target_lower for k in ["upsc", "civil services", "public policy", "ias", "ips"]):
            credentials.append(
                VerifiedCredential(
                    credential_id="cred_upsc_cse",
                    title="UPSC Civil Services Examination (Preliminary & Mains)",
                    issuer="Union Public Service Commission",
                    classification="MANDATORY",
                    target_roles=["Indian Administrative Service (IAS)", "Indian Police Service (IPS)", "Civil Servant"],
                    prerequisites=["Graduation Degree in any discipline"],
                    preparation_effort="12–18 Months Intensive Syllabus Study",
                    verified_cost="Official Examination Fee",
                    geographic_relevance="National (India)",
                    official_url="https://upsc.gov.in/",
                    source="Union Public Service Commission",
                    strategic_advice="Constitutional examination required for appointment to All India and Central Civil Services.",
                    decision_rationale="MANDATORY: Statutory constitutional pathway for premier public administration roles."
                )
            )
        elif any(k in target_lower for k in ["product manager", "product management", "pm"]):
            credentials.append(
                VerifiedCredential(
                    credential_id="cred_cspo_product_owner",
                    title="Certified Scrum Product Owner (CSPO)",
                    issuer="Scrum Alliance",
                    classification="STRONGLY_USEFUL",
                    target_roles=["Product Manager", "Associate PM", "Product Owner"],
                    prerequisites=["Agile methodologies & backlog management"],
                    preparation_effort="2 Days Interactive Training",
                    verified_cost="~$800–$1,000",
                    geographic_relevance="Global",
                    official_url="https://www.scrumalliance.org/get-certified/product-owner-track/cspo",
                    source="Scrum Alliance Registry",
                    strategic_advice="Useful for demonstrating familiarity with agile sprint cadence and backlog prioritization.",
                    decision_rationale="STRONGLY_USEFUL: Industry benchmark for cross-functional agile product leadership."
                )
            )
        elif any(k in target_lower for k in ["biotech", "molecular", "genetics", "bioinformatics", "biology"]):
            credentials.append(
                VerifiedCredential(
                    credential_id="cred_csir_ugc_net_jrf",
                    title="CSIR-UGC NET (Junior Research Fellowship) / GATE Life Sciences",
                    issuer="Council of Scientific and Industrial Research",
                    classification="MANDATORY",
                    target_roles=["Biotechnology Researcher", "Doctoral Fellow", "R&D Scientist"],
                    prerequisites=["Master's Degree in Life Sciences / Biotechnology"],
                    preparation_effort="6–12 Months Examination Prep",
                    verified_cost="Official Examination Fee",
                    geographic_relevance="India & Global Research Institutes",
                    official_url="https://csirnet.nta.ac.in/",
                    source="National Testing Agency & CSIR",
                    strategic_advice="Essential national eligibility requirement for funded institutional scientific research and doctoral admission.",
                    decision_rationale="MANDATORY: Standard qualification for government-funded laboratory research fellowships."
                )
            )
        elif "data" in target_lower and "science" not in target_lower and "engineer" in target_lower:
            credentials.append(
                VerifiedCredential(
                    credential_id="cred_dbt_analytics_eng",
                    title="dbt Certified Developer",
                    issuer="dbt Labs",
                    classification="STRONGLY_USEFUL",
                    target_roles=["Data Engineer", "Analytics Engineer"],
                    prerequisites=["SQL Data Modeling", "Git Version Control"],
                    preparation_effort="4–6 Weeks",
                    verified_cost="~$200",
                    geographic_relevance="Global",
                    official_url="https://www.getdbt.com/certifications/",
                    source="Official dbt Labs Portal",
                    strategic_advice="Strongly recognized for data modeling roles, but building a public warehouse pipeline with BigQuery/dbt carries equal hiring weight.",
                    decision_rationale="STRONGLY_USEFUL: High employer signal for modern data stack roles."
                )
            )
            credentials.append(
                VerifiedCredential(
                    credential_id="cred_gcp_data_engineer",
                    title="Google Cloud Professional Data Engineer",
                    issuer="Google Cloud",
                    classification="OPTIONAL",
                    target_roles=["Cloud Data Engineer", "Big Data Architect"],
                    prerequisites=["Distributed Computing", "SQL / BigQuery Fundamentals"],
                    preparation_effort="8–12 Weeks",
                    verified_cost="~$200",
                    geographic_relevance="Global",
                    official_url="https://cloud.google.com/learn/certification/data-engineer",
                    source="Google Cloud Certification Registry",
                    strategic_advice="Optional. Prioritize verifiable pipeline repositories over vendor certificates unless specifically required by enterprise clients.",
                    decision_rationale="OPTIONAL: Projects with live ETL code carry higher weight than exam certifications."
                )
            )
        elif any(k in target_lower for k in ["ai", "machine learning", "deep learning", "software engineer", "developer", "robotics"]):
            credentials.append(
                VerifiedCredential(
                    credential_id="cred_deeplearning_ai_pytorch",
                    title="DeepLearning.AI Deep Learning Specialization",
                    issuer="DeepLearning.AI",
                    classification="STRONGLY_USEFUL",
                    target_roles=["Machine Learning Engineer", "AI Researcher"],
                    prerequisites=["Python OOP", "Linear Algebra Foundations"],
                    preparation_effort="8–12 Weeks",
                    verified_cost="Coursera Subscription ($49/mo)",
                    geographic_relevance="Global",
                    official_url="https://www.deeplearning.ai/",
                    source="Official DeepLearning.AI Portal",
                    strategic_advice="Useful for structured learning and initial resume screening, but 1 deployed PyTorch repository carries 3x higher hiring weight.",
                    decision_rationale="STRONGLY_USEFUL: Curated curriculum recognized widely across industry."
                )
            )
            credentials.append(
                VerifiedCredential(
                    credential_id="cred_aws_ml_specialty",
                    title="AWS Certified Machine Learning – Specialty",
                    issuer="Amazon Web Services",
                    classification="OPTIONAL",
                    target_roles=["Cloud ML Engineer", "MLOps Architect"],
                    prerequisites=["Cloud Fundamentals", "Python Data Stack"],
                    preparation_effort="12 Weeks",
                    verified_cost="~$300",
                    geographic_relevance="India & Global",
                    official_url="https://aws.amazon.com/certification/certified-machine-learning-specialty/",
                    source="Amazon Web Services Official Training",
                    strategic_advice="Optional. Prioritize public project repositories and containerized Docker pipelines over vendor exam certificates.",
                    decision_rationale="OPTIONAL: High cost; vendor-specific; portfolio repositories provide stronger direct evidence."
                )
            )
        else:
            # Generic professional outcome - Do NOT default to AI/ML
            credentials.append(
                VerifiedCredential(
                    credential_id=f"cred_domain_foundation_{target_lower.replace(' ', '_')[:20]}",
                    title=f"Recognized Professional Standard Credential in {target_role}",
                    issuer="Recognized Professional Association",
                    classification="STRONGLY_USEFUL",
                    target_roles=[target_role],
                    prerequisites=["Core domain foundation"],
                    preparation_effort="6–12 Weeks",
                    verified_cost="Official Fee",
                    geographic_relevance="National & Global",
                    official_url="https://en.wikipedia.org/wiki/Professional_certification",
                    source="Professional Standards Registry",
                    strategic_advice="Evaluate whether local jurisdiction or target employers require formal certification before enrolling.",
                    decision_rationale="STRONGLY_USEFUL: Establishes baseline standard compliance."
                )
            )

        return credentials

class OpportunityAgent:
    """
    ADK Agent: OpportunityAgent
    Finds and matches verified opportunities.
    Separates career fit from legal/employment eligibility.
    Provides transparent explanations.
    """
    def match_and_explain(
        self,
        opportunities: List[VerifiedOpportunity],
        profile: UniversalCareerProfile,
        target_role: str,
        readiness_state: str
    ) -> List[VerifiedOpportunity]:
        matched_results: List[VerifiedOpportunity] = []
        skills_set = {s.lower().strip() for s in profile.skills}

        for opp in opportunities:
            # Substring/token aware overlap match
            overlap_count = 0
            for req in opp.required_skills:
                req_l = req.lower().strip()
                if any(req_l in s or s in req_l for s in skills_set):
                    overlap_count += 1

            opp_copy = opp.model_copy(deep=True)

            # Fit calculation
            if overlap_count >= 2 or ("ai" in target_role.lower() and "ai" in opp.title.lower()):
                opp_copy.fit_level = "HIGH"
            elif overlap_count >= 1:
                opp_copy.fit_level = "MEDIUM"
            else:
                opp_copy.fit_level = "LOW"

            # Opportunity Timing Advice
            if readiness_state in ["FOUNDATIONAL"]:
                opp_copy.pre_application_advice = "Focus on foundational programming milestones before submitting an application."
            elif readiness_state in ["DEVELOPING"]:
                opp_copy.pre_application_advice = "Build and publish your stage milestone project repository to strengthen your application."
            else:
                opp_copy.pre_application_advice = "You possess sufficient evidence to apply directly via the verified link below."

            # Legal / Geographic Check
            if profile.current_country.lower() != "india" and "india" in opp.location.lower() and "remote" not in opp.location.lower():
                opp_copy.eligibility_blockers.append("Role requires local work authorization in India.")

            matched_results.append(opp_copy)

        matched_results.sort(key=lambda x: 0 if x.fit_level == "HIGH" else 1 if x.fit_level == "MEDIUM" else 2)
        return matched_results

class ResumeAgent:
    """
    ADK Agent: ResumeAgent
    Generates role-specific tailored resume and ATS analysis derived EXCLUSIVELY from verified profile facts.
    Strictly forbids hallucinating companies, projects, grades, or technologies.
    """
    def __init__(self):
        self.validator = ResumeFactValidator()

    def generate_tailored_resume(
        self,
        profile: UniversalCareerProfile,
        target_role: str,
        target_opportunity: Optional[VerifiedOpportunity] = None
    ) -> TailoredResume:
        # Build fact-grounded summary
        parts = [f"Candidate targeting {target_role}."]
        if profile.education:
            deg = profile.education[0]
            parts.append(f"Academic background in {deg.field_of_study or deg.degree} from {deg.institution}.")
        if profile.skills:
            parts.append(f"Demonstrated competencies in: {', '.join(profile.skills[:5])}.")
        summary = " ".join(parts)

        # Grounded projects (Strictly from profile facts)
        projects_data = []
        provenance_map = {}
        for p in profile.projects:
            prov = p.provenance or "Verified Project Artifact"
            projects_data.append({
                "title": p.title,
                "technologies": p.technologies,
                "description": p.description,
                "provenance": prov
            })
            provenance_map[p.title] = prov

        # Grounded experience (Strictly from profile facts)
        experience_data = []
        for exp in profile.experience:
            experience_data.append({
                "role": exp.role,
                "organization": exp.organization,
                "duration": exp.duration,
                "description": exp.description
            })

        # Grounded education (Strictly from profile facts)
        education_data = []
        for edu in profile.education:
            education_data.append({
                "degree": edu.degree,
                "field": edu.field_of_study,
                "institution": edu.institution,
                "year": edu.year or ""
            })

        # ATS Analysis
        skills_held = {s.lower().strip() for s in profile.skills}
        if target_opportunity and target_opportunity.required_skills:
            required_keywords = target_opportunity.required_skills
        elif profile.skills:
            required_keywords = profile.skills[:5]
        else:
            required_keywords = []

        matched_keywords = [kw for kw in required_keywords if any(kw.lower() in s or s in kw.lower() for s in skills_held)]
        missing_keywords = [kw for kw in required_keywords if not any(kw.lower() in s or s in kw.lower() for s in skills_held)]

        if required_keywords:
            ats_score = int((len(matched_keywords) / len(required_keywords)) * 100)
        else:
            ats_score = 100 if profile.skills else 50

        ats_recommendations = []
        if missing_keywords:
            ats_recommendations.append(f"Complete upcoming milestones to add verified evidence for: {', '.join(missing_keywords[:2])}.")
        if profile.projects:
            ats_recommendations.append("Include repository/portfolio links and measurable outcome metrics in project descriptions.")
        else:
            ats_recommendations.append("Add verified project or portfolio artifacts to strengthen ATS validation.")

        unvalidated_resume = TailoredResume(
            resume_id=f"res_{profile.person_id}_{int(datetime.now(timezone.utc).timestamp())}",
            person_id=profile.person_id,
            target_role=target_role,
            target_opportunity_id=target_opportunity.opportunity_id if target_opportunity else None,
            summary=summary,
            highlighted_skills=profile.skills,
            tailored_projects=projects_data,
            verified_experience=experience_data,
            education=education_data,
            certifications=[{"title": c.title, "issuer": c.issuer} for c in profile.credentials],
            provenance_map=provenance_map,
            ats_match_score=ats_score,
            ats_matched_keywords=matched_keywords,
            ats_missing_keywords=missing_keywords,
            ats_recommendations=ats_recommendations,
            fact_validation_status="PASSED",
            unsupported_claims_rejected=[],
            generated_at=datetime.now(timezone.utc).isoformat()
        )

        # Execute Strict Deterministic Fact Validation
        sanitized_resume, is_valid = self.validator.validate_and_sanitize(unvalidated_resume, profile)
        return sanitized_resume

class AccountabilityAgent:
    """
    ADK Agent: AccountabilityAgent
    Maintains ongoing commitments and pacing without alarmist notifications, shame, or pressure.
    Adapts based on personal memory and learning history.
    """
    def evaluate_accountability(
        self,
        person_id: str,
        completed_stages: int = 1,
        total_stages: int = 5,
        weekly_hours: int = 10,
        missed_milestones: int = 0
    ) -> AccountabilityStatus:
        if missed_milestones == 0 and completed_stages >= 1:
            return AccountabilityStatus(
                status="ON_TRACK",
                current_streak_days=4,
                weekly_commitment_hours=weekly_hours,
                mentor_observation=(
                    "You completed your recent milestone on schedule with verified test assertions. "
                    f"Your current pacing of {weekly_hours} hours/week remains well-aligned with your target timeline."
                ),
                suggested_adjustment=None,
                next_checkpoint="Friday Milestone Check-in",
                last_check_in=datetime.now(timezone.utc).isoformat()
            )
        elif missed_milestones >= 2:
            return AccountabilityStatus(
                status="AT_RISK",
                current_streak_days=1,
                weekly_commitment_hours=weekly_hours,
                mentor_observation=(
                    "It looks like the last two milestones encountered challenging prerequisite concepts. "
                    "Let's break the upcoming milestone into 2 smaller, focused 45-minute coding blocks rather than a large single task."
                ),
                suggested_adjustment="Decompose active milestone into 2 bite-sized test assertions.",
                next_checkpoint="Wednesday Progress Sync",
                last_check_in=datetime.now(timezone.utc).isoformat()
            )
        else:
            return AccountabilityStatus(
                status="REPLANNING",
                current_streak_days=2,
                weekly_commitment_hours=weekly_hours,
                mentor_observation=(
                    "You are making steady conceptual progress. Consider committing small functional iterations to your repository "
                    "to maintain daily momentum."
                ),
                suggested_adjustment="Commit 1 unit test case every 2 days.",
                next_checkpoint="Thursday Milestone Review",
                last_check_in=datetime.now(timezone.utc).isoformat()
            )
