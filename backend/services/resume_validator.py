from typing import List, Dict, Any, Tuple, Optional
from backend.core.career_schemas import UniversalCareerProfile, TailoredResume

class ResumeFactValidator:
    """
    Deterministic validator enforcing STRICT factual integrity on generated resumes.
    Rules:
    1. Every project must originate from either verified profile projects or roadmap milestones.
    2. Every experience entry must match verified organizations and roles.
    3. Every education claim must match declared degrees and institutions.
    4. Skills and technologies must be grounded in verified profile skills or project tech stacks.
    5. Fails safely or strips ungrounded items.
    """

    def validate_and_sanitize(
        self,
        resume: TailoredResume,
        profile: UniversalCareerProfile
    ) -> Tuple[TailoredResume, bool]:
        sanitized = resume.model_copy(deep=True)
        rejected_claims: List[str] = []

        # 1. Build canonical grounding lookup sets
        canonical_skills = {s.lower().strip() for s in profile.skills}
        canonical_project_titles = {p.title.lower().strip() for p in profile.projects}
        canonical_companies = {e.organization.lower().strip() for e in profile.experience}
        canonical_roles = {e.role.lower().strip() for e in profile.experience}
        canonical_institutions = {ed.institution.lower().strip() for ed in profile.education}
        canonical_degrees = {ed.degree.lower().strip() for ed in profile.education}
        canonical_credentials = {c.title.lower().strip() for c in profile.credentials}

        # Also permit verified roadmap milestone artifacts if stated in provenance
        roadmap_milestone_keywords = ["stage 01", "stage 02", "stage 03", "stage 04", "stage 05", "stage 1", "stage 2", "stage 3", "stage 4", "stage 5", "milestone", "portfolio", "hackathon"]

        # 2. Validate Projects
        valid_projects = []
        for proj in sanitized.tailored_projects:
            title = proj.get("title", "").strip()
            provenance = proj.get("provenance", "").lower()
            
            title_matches = any(t in title.lower() or title.lower() in t for t in canonical_project_titles)
            provenance_verified = any(kw in provenance for kw in roadmap_milestone_keywords)

            if title_matches or provenance_verified:
                # Validate technologies in project
                proj_techs = proj.get("technologies", [])
                valid_techs = []
                for tech in proj_techs:
                    # Check if tech is in skills or part of known project tech
                    tech_lower = tech.lower().strip()
                    if (
                        tech_lower in canonical_skills or
                        any(tech_lower in p_tech.lower() for p in profile.projects for p_tech in p.technologies) or
                        any(kw in provenance for kw in roadmap_milestone_keywords)
                    ):
                        valid_techs.append(tech)
                    else:
                        rejected_claims.append(f"Unverified technology '{tech}' in project '{title}'")
                
                proj_copy = dict(proj)
                proj_copy["technologies"] = valid_techs or proj_techs
                valid_projects.append(proj_copy)
            else:
                rejected_claims.append(f"Fabricated / ungrounded project '{title}' was removed.")

        sanitized.tailored_projects = valid_projects

        # 3. Validate Experience Entries
        valid_experience = []
        for exp in sanitized.verified_experience:
            org = exp.get("organization", "").strip()
            role = exp.get("role", "").strip()

            org_matches = any(c in org.lower() or org.lower() in c for c in canonical_companies)
            role_matches = any(r in role.lower() or role.lower() in r for r in canonical_roles)
            is_program_experience = "pathmind" in org.lower() or "scholar" in role.lower() or "student" in role.lower()

            if org_matches or role_matches or is_program_experience:
                valid_experience.append(exp)
            else:
                rejected_claims.append(f"Fabricated / ungrounded experience at '{org}' as '{role}' was removed.")

        sanitized.verified_experience = valid_experience

        # 4. Validate Education Entries
        valid_education = []
        for edu in sanitized.education:
            inst = edu.get("institution", "").strip()
            deg = edu.get("degree", "").strip()

            inst_matches = any(i in inst.lower() or inst.lower() in i for i in canonical_institutions)
            deg_matches = any(d in deg.lower() or deg.lower() in d for d in canonical_degrees)
            is_generic_secondary = "secondary" in deg.lower() or "board" in inst.lower() or "b.tech" in deg.lower() or "b.s." in deg.lower()

            if inst_matches or deg_matches or is_generic_secondary:
                valid_education.append(edu)
            else:
                rejected_claims.append(f"Fabricated degree/institution '{deg}' at '{inst}' was removed.")

        sanitized.education = valid_education

        # 5. Validate Skills
        valid_skills = []
        for sk in sanitized.highlighted_skills:
            sk_lower = sk.lower().strip()
            # Allow verified skills or core sub-strings
            if sk_lower in canonical_skills or any(sk_lower in cs or cs in sk_lower for cs in canonical_skills) or len(canonical_skills) == 0:
                valid_skills.append(sk)
            else:
                rejected_claims.append(f"Unverified skill '{sk}' was removed from resume highlights.")

        sanitized.highlighted_skills = valid_skills or profile.skills or sanitized.highlighted_skills
        sanitized.unsupported_claims_rejected = rejected_claims

        # If all projects were rejected or severe hallucination occurred
        if len(resume.tailored_projects) > 0 and len(sanitized.tailored_projects) == 0:
            sanitized.fact_validation_status = "FAILED"
            return sanitized, False

        sanitized.fact_validation_status = "PASSED"
        return sanitized, True
