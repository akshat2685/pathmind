from typing import List, Dict, Any, Optional, TYPE_CHECKING, Any
from datetime import datetime, timezone

if TYPE_CHECKING:
    from backend.services.career_readiness_engine import CareerReadinessEngine

from backend.core.opportunity_schemas import (
    CanonicalOpportunity,
    OpportunityMatch,
    ApplicationPreparationPlan,
    InterviewPrepPackage
)
from backend.core.career_schemas import CanonicalGoal
from backend.providers.opportunity_provider import (
    BaseOpportunityProvider,
    JobOpportunitiesProvider,
    deduplicate_opportunities
)
from backend.services.opportunity_reasoning_agent import OpportunityReasoningAgent
from backend.services.pm_store import get_pm_store

class OpportunityMatchingEngine:
    """
    Deterministic Matching & Opportunity Intelligence Engine for PATHMIND.
    Matches verified opportunities against real person capabilities, separates fit from readiness,
    handles unknown profile fields without unfair penalties, and generates actionable execution plans.
    """
    def __init__(
        self,
        provider: Optional[BaseOpportunityProvider] = None,
        agent: Optional[OpportunityReasoningAgent] = None,
        career_engine: Optional["CareerReadinessEngine"] = None,
        store: Optional[Any] = None
    ):
        self.store = store or get_pm_store()
        self.provider = provider or JobOpportunitiesProvider()
        self.agent = agent or OpportunityReasoningAgent()
        
        if career_engine is None:
            raise ValueError("career_engine dependency must be provided to OpportunityMatchingEngine")
        self.career_engine = career_engine

    async def get_all_opportunities(
        self,
        domain_filter: Optional[str] = None,
        role_filter: Optional[str] = None,
        geography: Optional[str] = None
    ) -> List[CanonicalOpportunity]:
        opps = await self.provider.fetch_opportunities(
            domain_filter=domain_filter,
            role_filter=role_filter, 
            geography=geography
        )
        return deduplicate_opportunities(opps)

    async def get_opportunity_by_id(self, opportunity_id: str) -> Optional[CanonicalOpportunity]:
        opps = await self.get_all_opportunities()
        return next((o for o in opps if o.id == opportunity_id), None)

    async def match_opportunities_for_person(
        self,
        person_id: str,
        role_filter: Optional[str] = None,
        geography: Optional[str] = None
    ) -> List[OpportunityMatch]:
        
        # 1. Retrieve real person profile & career goal
        profile = await self.career_engine.get_or_create_canonical_profile(person_id)
        # Assuming store now has get_canonical_goal method
        goal: CanonicalGoal = await self.career_engine.get_or_create_career_goal(person_id)
        
        target_role = role_filter or goal.target_role or "General Professional Practice"
        target_domain = getattr(goal, "domain", getattr(goal, "target_domain", "Unknown"))

        # 2. Retrieve verified skills from evidence/artifacts
        artifacts = await self.store.get_person_artifacts(person_id)
        verified_skills_set = set()
        observed_skills_set = set()

        for art in artifacts:
            analysis = art.get("analysis") or {}
            for cap in analysis.get("capability_mappings", []):
                name = cap.get("capability_name", "").lower().strip()
                if cap.get("status") == "VERIFIED" or cap.get("is_promoted_to_evidence"):
                    verified_skills_set.add(name)
                elif cap.get("status") == "OBSERVED":
                    observed_skills_set.add(name)

        # Profile self-reported skills
        self_reported_skills = {s.lower().strip() for s in profile.skills}

        # 3. Retrieve verified opportunities from external provider
        raw_opps = await self.get_all_opportunities(
            domain_filter=target_domain,
            role_filter=target_role, 
            geography=geography or profile.current_country
        )

        results: List[OpportunityMatch] = []

        for opp in raw_opps:
            matched_reqs = []
            gap_reqs = []
            unknown_fields = []
            match_reasons = []

            # Determine Fit (Relevance to Goal)
            fit_status = "UNKNOWN"
            if target_role.lower() in opp.title.lower() or target_domain.lower() in opp.title.lower():
                fit_status = "HIGH"
                match_reasons.append("Opportunity aligns directly with target role and domain.")
            else:
                fit_status = "MEDIUM"
                match_reasons.append("Opportunity is broadly related to your field.")

            # Determine Eligibility
            eligibility_status = "UNKNOWN"
            if opp.eligibility != "UNKNOWN":
                # Simplistic check for hackathon: Assume eligible unless explicit age blockers
                eligibility_status = "ELIGIBLE"
            
            # Match specific requirements to assess Readiness
            for req in opp.requirements:
                req_clean = req.lower().strip()
                if any(req_clean in vs or vs in req_clean for vs in verified_skills_set):
                    matched_reqs.append(f"{req} (Verified by Evidence)")
                elif any(req_clean in os or os in req_clean for os in observed_skills_set):
                    matched_reqs.append(f"{req} (Observed in Code)")
                elif any(req_clean in sr or sr in req_clean for sr in self_reported_skills):
                    matched_reqs.append(f"{req} (Self-reported)")
                else:
                    gap_reqs.append(req)

            # Determine Readiness
            readiness_status = "UNKNOWN"
            if len(opp.requirements) > 0:
                coverage = len(matched_reqs) / len(opp.requirements)
                if coverage >= 0.8:
                    readiness_status = "READY"
                elif coverage >= 0.4:
                    readiness_status = "PARTIALLY_READY"
                else:
                    readiness_status = "NOT_READY"

            # Determine Feasibility
            feasibility_status = "UNKNOWN"
            if opp.location != "UNKNOWN":
                if "remote" in opp.remote_status.lower():
                    feasibility_status = "HIGH"
                elif profile.current_country and profile.current_country.lower() in opp.location.lower():
                    feasibility_status = "HIGH"
                else:
                    feasibility_status = "LOW"

            results.append(
                OpportunityMatch(
                    opportunity_id=opp.id,
                    goal_id=goal.id,
                    match_reasons=match_reasons,
                    requirement_matches=matched_reqs,
                    requirement_gaps=gap_reqs,
                    eligibility_status=eligibility_status,
                    fit_status=fit_status,
                    readiness_status=readiness_status,
                    feasibility_status=feasibility_status,
                    opportunity=opp
                )
            )

        return results

    async def get_application_preparation_plan(
        self,
        person_id: str,
        opportunity_id: str
    ) -> ApplicationPreparationPlan:
        opp = await self.get_opportunity_by_id(opportunity_id)
        if not opp:
            raise ValueError("Opportunity not found or no longer available.")
        
        plan = await self.agent.generate_opportunity_preparation_plan(
            person_id=person_id,
            target_role=opp.title,
            opportunity_title=opp.title,
            organization=opp.organization,
            requirements=opp.requirements
        )
        plan["opportunity_id"] = opportunity_id
        return ApplicationPreparationPlan(**plan)

    async def get_interview_prep_package(
        self,
        person_id: str,
        opportunity_id: str
    ) -> InterviewPrepPackage:
        opp = await self.get_opportunity_by_id(opportunity_id)
        if not opp:
            raise ValueError("Opportunity not found or no longer available.")
        
        package = await self.agent.generate_interview_prep_package(
            person_id=person_id,
            target_role=opp.title,
            opportunity_title=opp.title,
            organization=opp.organization,
            requirements=opp.requirements
        )
        package["opportunity_id"] = opportunity_id
        return InterviewPrepPackage(**package)
