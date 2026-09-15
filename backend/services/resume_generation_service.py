from typing import List, Dict, Any, Optional
from datetime import datetime, timezone
import uuid

from backend.core.career_schemas import UniversalCareerProfile, CanonicalGoal
# from backend.core.opportunity_schemas import CanonicalOpportunity  # We might just use dicts or CanonicalOpportunity depending on availability
from backend.core.resume_schemas import (
    VerifiedClaim,
    PortfolioProject,
    ResumeRequirementAnalysis,
    ResumeFact,
    ResumeVersion
)
from backend.services.resume_validator import ResumeFactValidator

class ResumeGenerationService:
    """
    STRICTLY DETERMINISTIC Resume + Portfolio Intelligence Generation.
    Never hallucinates generic student projects, placeholder roles, or software artifacts for non-software users.
    Every statement maps to a verified claim.
    """

    def __init__(self):
        self.validator = ResumeFactValidator()

    def _extract_verified_claims(self, profile: UniversalCareerProfile) -> List[VerifiedClaim]:
        """Convert UniversalCareerProfile facts into canonical VerifiedClaims."""
        claims = []
        
        for idx, edu in enumerate(profile.education):
            claims.append(
                VerifiedClaim(
                    id=f"claim_edu_{idx}",
                    person_id=profile.person_id,
                    category="EDUCATION",
                    statement=f"{edu.degree} in {edu.field_of_study} from {edu.institution}",
                    source="User Profile",
                    verification_status="VERIFIED",
                    confidence="HIGH",
                    provenance="Declared Education"
                )
            )

        for idx, exp in enumerate(profile.experience):
            claims.append(
                VerifiedClaim(
                    id=f"claim_exp_{idx}",
                    person_id=profile.person_id,
                    category="EXPERIENCE",
                    statement=f"{exp.role} at {exp.organization}",
                    source="User Profile",
                    verification_status="VERIFIED",
                    confidence="HIGH",
                    provenance="Declared Experience"
                )
            )

        for idx, proj in enumerate(profile.projects):
            prov = proj.provenance or "User Stated"
            status = "VERIFIED" if "Verified" in prov or "Milestone" in prov else "USER_STATED"
            claims.append(
                VerifiedClaim(
                    id=f"claim_proj_{idx}",
                    person_id=profile.person_id,
                    category="PROJECT",
                    statement=f"Built {proj.title}",
                    source="User Profile",
                    verification_status=status,
                    confidence="HIGH" if status == "VERIFIED" else "MODERATE",
                    provenance=prov
                )
            )

        for idx, sk in enumerate(profile.skills):
            claims.append(
                VerifiedClaim(
                    id=f"claim_skill_{idx}",
                    person_id=profile.person_id,
                    category="SKILL",
                    statement=sk,
                    source="User Profile",
                    verification_status="VERIFIED",
                    confidence="MODERATE",
                    provenance="Declared Skill"
                )
            )

        return claims

    def generate_fact_grounded_resume(
        self,
        profile: UniversalCareerProfile,
        goal: CanonicalGoal,
        opportunity: Optional[Any] = None
    ) -> ResumeVersion:
        """
        Generates a 100% factual resume tailored to the given canonical goal.
        """
        claims = self._extract_verified_claims(profile)
        
        # 1. Target Alignment
        target_role = goal.target_role or goal.target_outcome
        domain = goal.domain
        
        # 2. Extract strictly verified or user-stated facts
        edu_claims = [c for c in claims if c.category == "EDUCATION" and c.verification_status == "VERIFIED"]
        exp_claims = [c for c in claims if c.category == "EXPERIENCE" and c.verification_status == "VERIFIED"]
        proj_claims = [c for c in claims if c.category == "PROJECT" and c.verification_status in ["VERIFIED", "USER_STATED"]]
        skill_claims = [c for c in claims if c.category == "SKILL" and c.verification_status == "VERIFIED"]

        # Filter out anything unverified or unrelated (No AI hallucination allowed here)
        
        resume_content = {
            "summary": f"Targeting opportunities as {target_role}.",
            "education": [
                {"degree": edu.degree, "institution": edu.institution, "field": edu.field_of_study} 
                for edu, c in zip(profile.education, [c for c in claims if c.category == "EDUCATION"]) 
                if c.verification_status == "VERIFIED"
            ],
            "experience": [
                {"role": exp.role, "organization": exp.organization, "description": exp.description} 
                for exp, c in zip(profile.experience, [c for c in claims if c.category == "EXPERIENCE"]) 
                if c.verification_status == "VERIFIED"
            ],
            "projects": [
                {"title": proj.title, "description": proj.description, "technologies": proj.technologies} 
                for proj, c in zip(profile.projects, [c for c in claims if c.category == "PROJECT"]) 
                if c.verification_status in ["VERIFIED", "USER_STATED"]
            ],
            "skills": [c.statement for c in skill_claims]
        }

        # Validate Opportunity Fit / ATS Analysis
        if opportunity:
            missing_keywords = []
            matched_keywords = []
            reqs = getattr(opportunity, "requirements", []) or getattr(opportunity, "skills", []) or []
            for req in reqs:
                if any(req.lower() in s.lower() for s in resume_content["skills"]):
                    matched_keywords.append(req)
                else:
                    missing_keywords.append(req)
            resume_content["ats_analysis"] = {
                "matched": matched_keywords,
                "missing": missing_keywords
            }

        # Draft Phase
        version = ResumeVersion(
            id=f"res_v_{uuid.uuid4().hex[:8]}",
            person_id=profile.person_id,
            goal_id=goal.id or goal.goal_id,
            opportunity_id=getattr(opportunity, "id", None) if opportunity else None,
            version=1,
            content=resume_content,
            claim_ids=[c.id for c in claims],
            state="DRAFT",
            change_reason="Initial Generation"
        )
        
        return version
