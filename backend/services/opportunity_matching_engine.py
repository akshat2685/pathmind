from typing import List, Dict, Any, Optional
from datetime import datetime, timezone

from backend.core.opportunity_schemas import (
    CanonicalOpportunity,
    OpportunityMatchResult,
    ApplicationPreparationPlan,
    InterviewPrepPackage
)
from backend.core.execution_schemas import CreateActionRequest
from backend.providers.opportunity_provider import (
    BaseOpportunityProvider,
    VerifiedOpenOpportunityProvider,
    deduplicate_opportunities
)
from backend.services.opportunity_reasoning_agent import OpportunityReasoningAgent
from backend.services.career_readiness_engine import CareerReadinessEngine
from backend.services.execution_engine import ExecutionEngine
from backend.services.store import FirestoreStore

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
        career_engine: Optional[CareerReadinessEngine] = None,
        execution_engine: Optional[ExecutionEngine] = None,
        store: Optional[FirestoreStore] = None
    ):
        self.store = store or FirestoreStore()
        self.provider = provider or VerifiedOpenOpportunityProvider()
        self.agent = agent or OpportunityReasoningAgent()
        self.career_engine = career_engine or CareerReadinessEngine()
        self.execution_engine = execution_engine or ExecutionEngine(store=self.store)

    async def get_all_opportunities(
        self,
        role_filter: Optional[str] = None,
        geography: Optional[str] = None
    ) -> List[CanonicalOpportunity]:
        opps = await self.provider.fetch_opportunities(role_filter=role_filter, geography=geography)
        return deduplicate_opportunities(opps)

    async def get_opportunity_by_id(self, opportunity_id: str) -> Optional[CanonicalOpportunity]:
        opps = await self.get_all_opportunities()
        return next((o for o in opps if o.opportunity_id == opportunity_id), None)

    async def match_opportunities_for_person(
        self,
        person_id: str,
        role_filter: Optional[str] = None,
        geography: Optional[str] = None
    ) -> List[OpportunityMatchResult]:
        # 1. Retrieve real person profile & career goal
        profile = await self.career_engine.get_or_create_canonical_profile(person_id)
        goal = await self.career_engine.get_or_create_career_goal(person_id)
        target_role = goal.target_role or "Applied Machine Learning Systems Engineer"

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

        # 3. Retrieve all valid opportunities
        raw_opps = await self.get_all_opportunities(role_filter=role_filter, geography=geography)
        results: List[OpportunityMatchResult] = []

        for opp in raw_opps:
            matched_reqs: List[str] = []
            gap_reqs: List[str] = []
            unknown_fields: List[str] = []

            # Evaluate skill requirements
            for req in opp.requirements:
                req_clean = req.lower().strip()
                # Check verified evidence first, then observed code, then self-reported
                if any(req_clean in vs or vs in req_clean for vs in verified_skills_set):
                    matched_reqs.append(f"{req} (Verified by Evidence)")
                elif any(req_clean in os or os in req_clean for os in observed_skills_set):
                    matched_reqs.append(f"{req} (Observed in Code)")
                elif any(req_clean in sr or sr in req_clean for sr in self_reported_skills):
                    matched_reqs.append(f"{req} (Self-reported)")
                else:
                    gap_reqs.append(req)

            # Evaluate Education & Work Authorization without penalizing UNKNOWN as failure
            if opp.education_requirements:
                if not profile.education:
                    unknown_fields.append("Education background not specified in profile.")
                else:
                    edu_degree = profile.education[0].degree.lower()
                    if "bachelor" in edu_degree or "b.tech" in edu_degree or "m.tech" in edu_degree or "b.s." in edu_degree:
                        matched_reqs.append(f"Education: {profile.education[0].degree}")
                    else:
                        matched_reqs.append(f"Education: {profile.education[0].degree}")

            if "india" in opp.location.lower() and profile.current_country.lower() != "india" and opp.remote_status != "REMOTE":
                if not profile.work_authorization:
                    unknown_fields.append("Work authorization for India not confirmed.")
                else:
                    unknown_fields.append(f"Work authorization: {profile.work_authorization}")

            # 4. Determine Fit State vs Readiness State
            total_reqs = max(len(opp.requirements), 1)
            coverage = len(matched_reqs) / total_reqs

            # Goal alignment
            is_goal_aligned = (
                target_role.lower() in opp.title.lower() or
                any(s.lower() in target_role.lower() for s in opp.skills) or
                opp.type in ["OPEN_SOURCE", "RESEARCH", "FELLOWSHIP"]
            )

            if coverage >= 0.75 and is_goal_aligned:
                fit_state = "STRONG_MATCH"
                readiness_state = "READY_NOW" if len(gap_reqs) == 0 else "NEAR_READY"
            elif coverage >= 0.40 and is_goal_aligned:
                fit_state = "GOOD_MATCH"
                readiness_state = "NEAR_READY" if len(gap_reqs) <= 1 else "STRETCH"
            elif is_goal_aligned and len(gap_reqs) > 0:
                fit_state = "PARTIAL_MATCH"
                readiness_state = "STRETCH"
            elif coverage >= 0.50:
                fit_state = "GOOD_MATCH"
                readiness_state = "NEAR_READY"
            else:
                fit_state = "LOW_MATCH"
                readiness_state = "NOT_RECOMMENDED"

            # 5. Evaluate Decision Support
            decision_eval = await self.agent.evaluate_decision_support(
                opportunity=opp,
                matched_skills=matched_reqs,
                missing_skills=gap_reqs,
                readiness_state=readiness_state,
                target_role=target_role
            )

            # 6. Formulate Why & Next Step
            why = (
                f"Directly targets '{opp.title}' at {opp.organization}. "
                f"Demonstrates practical application for your confirmed target outcome '{target_role}'."
            )

            if readiness_state == "READY_NOW":
                next_step = f"Submit application via official portal ({opp.application_url}) with verified repository proof."
            elif readiness_state in ["NEAR_READY", "STRETCH"]:
                next_step = f"Complete targeted code milestone for '{gap_reqs[0] if gap_reqs else 'next capability'}' before submitting."
            else:
                next_step = "Focus on active foundational stage milestones before targeting this specialized role."

            results.append(
                OpportunityMatchResult(
                    opportunity=opp,
                    fit_state=fit_state,
                    readiness_state=readiness_state,
                    matched_requirements=matched_reqs,
                    gaps=gap_reqs,
                    unknowns=unknown_fields,
                    why_it_matters=why,
                    next_step=next_step,
                    decision_recommendation=decision_eval.get("decision_recommendation", "RECOMMEND_PREPARING_FIRST"),
                    tradeoffs=decision_eval.get("tradeoffs", [])
                )
            )

        # Sort: STRONG_MATCH first, then GOOD_MATCH, then PARTIAL_MATCH
        rank_order = {"STRONG_MATCH": 0, "GOOD_MATCH": 1, "PARTIAL_MATCH": 2, "LOW_MATCH": 3}
        results.sort(key=lambda r: rank_order.get(r.fit_state, 4))
        return results

    async def generate_preparation_plan(
        self,
        person_id: str,
        opportunity_id: str,
        spawn_to_execution_engine: bool = True
    ) -> ApplicationPreparationPlan:
        opp = await self.get_opportunity_by_id(opportunity_id)
        if not opp:
            raise ValueError(f"Opportunity {opportunity_id} not found.")

        goal = await self.career_engine.get_or_create_career_goal(person_id)
        target_role = goal.target_role or "Applied AI Specialist"

        # Formulate preparation actions
        actions_data: List[Dict[str, Any]] = []

        # Action 1: Gap remediation
        missing_focus = opp.requirements[0] if opp.requirements else "System Implementation"
        act1 = {
            "title": f"Implement & Verify Code Evidence: {missing_focus}",
            "description": f"Build hands-on unit-tested module satisfying '{missing_focus}' for {opp.title} application.",
            "action_type": "EVIDENCE",
            "priority": "NOW",
            "verification_requirement": "EVIDENCE_SUBMISSION"
        }
        actions_data.append(act1)

        # Action 2: Tailor Resume
        act2 = {
            "title": f"Tailor Resume for {opp.title} at {opp.organization}",
            "description": "Align keyword terminology and attach verified project repository links.",
            "action_type": "CAREER_RESEARCH",
            "priority": "NEXT",
            "verification_requirement": "SIMPLE_CONFIRMATION"
        }
        actions_data.append(act2)

        # Action 3: Official Application Submission
        act3 = {
            "title": f"Submit Official Application to {opp.organization}",
            "description": f"Submit candidate profile via official portal: {opp.application_url}",
            "action_type": "APPLICATION",
            "priority": "LATER",
            "verification_requirement": "CAREER_APPLICATION"
        }
        actions_data.append(act3)

        # Optionally register actions in Execution Engine
        if spawn_to_execution_engine:
            for ad in actions_data:
                await self.execution_engine.create_user_action(
                    person_id=person_id,
                    req=CreateActionRequest(
                        title=ad["title"],
                        description=ad["description"],
                        action_type=ad["action_type"],
                        priority=ad["priority"],
                        verification_requirement=ad["verification_requirement"],
                        goal_id=goal.goal_id
                    )
                )

        return ApplicationPreparationPlan(
            opportunity_id=opp.opportunity_id,
            person_id=person_id,
            target_role=target_role,
            required_actions=actions_data,
            estimated_effort_days=7,
            deadline_feasibility="FEASIBLE"
        )

    async def generate_interview_prep(
        self,
        person_id: str,
        opportunity_id: str
    ) -> InterviewPrepPackage:
        opp = await self.get_opportunity_by_id(opportunity_id)
        if not opp:
            raise ValueError(f"Opportunity {opportunity_id} not found.")

        profile = await self.career_engine.get_or_create_canonical_profile(person_id)
        projects_data = [p.model_dump() for p in profile.projects]

        return await self.agent.generate_interview_prep(
            opportunity=opp,
            target_role=profile.current_role,
            student_projects=projects_data
        )
