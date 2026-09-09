from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
from backend.core.trust_schemas import (
    StructuredRecommendation,
    RecommendationExplanation,
    TraceableClaim,
    UserRecommendationFeedback
)
from backend.services.trust_provenance_service import TrustProvenanceService
from backend.services.context_graph_service import ContextGraphService
from backend.services.store import FirestoreStore

class RecommendationExplanationService:
    """
    Recommendation Reasoning & Explainability Service for PATHMIND.
    Answers "Why This?" and "Why Not the Other Option?" grounded strictly in
    verified person evidence, occupational standards, and structured trade-offs.
    """
    def __init__(
        self,
        store: Optional[FirestoreStore] = None,
        trust_service: Optional[TrustProvenanceService] = None,
        context_service: Optional[ContextGraphService] = None
    ):
        self.store = store or FirestoreStore()
        self.trust_service = trust_service or TrustProvenanceService(store=self.store)
        self.context_service = context_service or ContextGraphService(store=self.store)

    async def generate_structured_recommendation(
        self,
        person_id: str,
        rec_type: str,
        title: str,
        summary: str,
        why_now: str,
        recommended_choice: str,
        alternative_choices: List[str],
        options: List[Dict[str, Any]],
        tradeoffs: List[str],
        uncertainties: List[str],
        facts: List[str],
        inferences: List[str]
    ) -> StructuredRecommendation:
        graph = await self.context_service.assemble_context_graph(person_id)
        target_role = graph.goal_context.get("primary_target_role", "Applied AI Engineer")

        # Ground claims
        claims: List[TraceableClaim] = []
        for f in facts:
            clm = await self.trust_service.verify_claim_provenance(
                person_id=person_id,
                claim_text=f,
                claim_category="FACT",
                source_type="ESCO"
            )
            claims.append(clm)

        for inf in inferences:
            clm = await self.trust_service.verify_claim_provenance(
                person_id=person_id,
                claim_text=inf,
                claim_category="INFERENCE",
                source_type="INTERNAL_DETERMINISTIC"
            )
            claims.append(clm)

        rec = StructuredRecommendation(
            person_id=person_id,
            type=rec_type,
            title=title,
            summary=summary,
            target_role=target_role,
            why_now=why_now,
            grounding_claims=claims,
            options=options,
            tradeoffs=tradeoffs,
            uncertainties=uncertainties,
            recommended_choice=recommended_choice,
            alternative_choices=alternative_choices,
            status="ACTIVE"
        )

        await self.store.save_structured_recommendation(person_id, rec.model_dump())
        return rec

    async def explain_recommendation(
        self,
        person_id: str,
        recommendation_id: str
    ) -> RecommendationExplanation:
        rec_raw = await self.store.get_structured_recommendation_by_id(person_id, recommendation_id)
        if not rec_raw:
            # Fallback for dynamic next action queries
            graph = await self.context_service.assemble_context_graph(person_id)
            target_role = graph.goal_context.get("primary_target_role", "Applied AI Engineer")
            rec = await self.generate_structured_recommendation(
                person_id=person_id,
                rec_type="NEXT_ACTION",
                title=f"Progress to {graph.learning_context.get('current_stage_title')}",
                summary="Build hands-on verified project repository.",
                why_now=f"Active focus in Stage 0{graph.learning_context.get('current_stage_number')}.",
                recommended_choice="Hands-on Project Repository with Unit Tests",
                alternative_choices=["Theoretical Video Course", "Pay for Certification First"],
                options=[
                    {"name": "Project Repository", "pace": "Self-paced", "proof": "Verifiable Git Repo"},
                    {"name": "Theoretical Course", "pace": "Fast", "proof": "Completion Certificate"}
                ],
                tradeoffs=[
                    "Project repositories provide verifiable code evidence required by hiring teams, whereas certificates demonstrate exposure only."
                ],
                uncertainties=[
                    "Proficiency in asynchronous concurrency has not yet been benchmarked."
                ],
                facts=[
                    f"{target_role} standard requires demonstrated unit testing and clean software design."
                ],
                inferences=[
                    "Project-based evidence will yield a higher career match score than theoretical quizzes."
                ]
            )
            rec_raw = rec.model_dump()

        rec = StructuredRecommendation(**rec_raw)

        # Synthesize Explanation
        facts_list = [c.claim_text for c in rec.grounding_claims if c.claim_category == "FACT"]
        inf_list = [c.claim_text for c in rec.grounding_claims if c.claim_category == "INFERENCE"]
        evidence_list = [
            f"Verified {s}" for s in rec_raw.get("grounding_claims", [])
            if isinstance(s, dict) and s.get("claim_category") == "OBSERVATION"
        ]

        why_this = (
            f"You are pursuing {rec.target_role}. {rec.why_now} "
            f"Choosing '{rec.recommended_choice}' directly satisfies required occupational standards without redundant effort."
        )

        why_not = (
            f"Alternative options ({', '.join(rec.alternative_choices)}) were evaluated. "
            f"However: {rec.tradeoffs[0] if rec.tradeoffs else 'The recommended choice offers higher evidence quality for your target role.'}"
        )

        explanation = RecommendationExplanation(
            recommendation_id=rec.recommendation_id,
            person_id=person_id,
            why_this=why_this,
            why_not_alternative=why_not,
            facts_summary=facts_list,
            evidence_summary=evidence_list,
            inference_summary=inf_list,
            unknowns_summary=rec.uncertainties
        )

        await self.store.save_recommendation_explanation(person_id, rec.recommendation_id, explanation.model_dump())
        return explanation

    async def record_user_decision(
        self,
        person_id: str,
        recommendation_id: str,
        user_choice: str,
        notes: Optional[str] = None
    ) -> bool:
        rec_raw = await self.store.get_structured_recommendation_by_id(person_id, recommendation_id)
        if rec_raw:
            new_status = "ACCEPTED" if user_choice == rec_raw.get("recommended_choice") else "SUPERSEDED"
            await self.store.update_recommendation_status(person_id, recommendation_id, new_status)

        # Save to canonical DecisionRecord
        from backend.services.decision_intelligence_service import DecisionIntelligenceService
        decision_service = DecisionIntelligenceService(store=self.store, context_service=self.context_service)
        await decision_service.record_user_decision(
            person_id=person_id,
            decision_type="RECOMMENDATION_SELECTION",
            title=f"Choice on Recommendation: {rec_raw.get('title', 'Path Selection') if rec_raw else 'Path'}",
            user_choice=user_choice,
            alternatives=rec_raw.get("alternative_choices", []) if rec_raw else []
        )
        return True

    async def record_feedback(
        self,
        person_id: str,
        recommendation_id: str,
        feedback_type: str,
        notes: Optional[str] = None
    ) -> UserRecommendationFeedback:
        fb = UserRecommendationFeedback(
            recommendation_id=recommendation_id,
            person_id=person_id,
            feedback_type=feedback_type,
            notes=notes
        )
        await self.store.save_recommendation_feedback(person_id, fb.model_dump())

        # Feed to Personal Agent Learning Loop
        await self.context_service.memory_engine.extract_and_store_memory_from_event(
            person_id=person_id,
            event_payload={
                "topic": "Recommendation Feedback",
                "observation": f"Learner feedback on {recommendation_id}: {feedback_type}.",
                "intervention": notes or "Calibration updated.",
                "event_type": "RECOMMENDATION_FEEDBACK"
            }
        )
        return fb
