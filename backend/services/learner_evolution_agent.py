from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
from backend.core.longitudinal_schemas import (
    TemporalQueryResponse,
    ProgressInsight,
    LongitudinalLearnerState
)
from backend.services.progress_analysis_service import ProgressAnalysisService
from backend.services.context_graph_service import ContextGraphService
from backend.services.store import FirestoreStore

class LearnerEvolutionAgent:
    """
    Google ADK & Reasoning Agent for PATHMIND Longitudinal Development.
    Answers natural-language temporal queries grounded in real persisted history,
    and manages insight dispute lifecycles without hallucinating missing records.
    """
    def __init__(
        self,
        store: Optional[FirestoreStore] = None,
        progress_service: Optional[ProgressAnalysisService] = None,
        context_service: Optional[ContextGraphService] = None
    ):
        self.store = store or FirestoreStore()
        self.context_service = context_service or ContextGraphService(store=self.store)
        self.progress_service = progress_service or ProgressAnalysisService(store=self.store, context_service=self.context_service)

    async def answer_temporal_query(self, person_id: str, query_text: str) -> TemporalQueryResponse:
        state = await self.progress_service.assemble_longitudinal_state(person_id)
        lowered = query_text.lower()
        now_iso = datetime.now(timezone.utc).isoformat()

        # 1. Query: First demonstrated skill / capability
        for cap in state.capability_history:
            if cap.skill_name.lower() in lowered:
                if cap.first_demonstrated_at:
                    return TemporalQueryResponse(
                        query_text=query_text,
                        answer=f"You first demonstrated verified proof for '{cap.skill_name}' on {cap.first_demonstrated_at} with {cap.evidence_count} verified code artifacts.",
                        status="ANSWERED",
                        supporting_event_ids=cap.evidence_ids
                    )
                else:
                    return TemporalQueryResponse(
                        query_text=query_text,
                        answer=f"Capability '{cap.skill_name}' is introduced in your active stage, but no verified proof artifacts have been submitted yet.",
                        status="INSUFFICIENT_EVIDENCE",
                        supporting_event_ids=[]
                    )

        # 2. Query: Learning strategy effectiveness
        if "strategy" in lowered or "method" in lowered or "worked best" in lowered:
            supported_strats = [s for s in state.strategy_profiles if s.effectiveness_status == "SUPPORTED"]
            if supported_strats:
                top_s = supported_strats[0]
                return TemporalQueryResponse(
                    query_text=query_text,
                    answer=f"Across your evaluation history, {top_s.strategy_dimension.replace('_', ' ')} has demonstrated the highest success rate with {top_s.successful_evaluations} verified pass results.",
                    status="ANSWERED",
                    supporting_event_ids=top_s.supporting_event_ids
                )
            else:
                return TemporalQueryResponse(
                    query_text=query_text,
                    answer="Your learning strategy profile is currently emerging. Completing 2+ stage project evaluations will calibrate your verified strategy profile.",
                    status="INSUFFICIENT_HISTORY",
                    supporting_event_ids=[]
                )

        # 3. Query: Turning points / goal changes
        if "turning point" in lowered or "goal" in lowered or "changed" in lowered:
            if state.turning_points:
                tp = state.turning_points[0]
                return TemporalQueryResponse(
                    query_text=query_text,
                    answer=f"Major turning point recorded: '{tp.title}' on {tp.timestamp[:10]}. {tp.what_happened} Result: {tp.what_changed_afterward}",
                    status="ANSWERED",
                    supporting_event_ids=[tp.turning_point_id]
                )

        # 4. Fallback when query is outside recorded history
        return TemporalQueryResponse(
            query_text=query_text,
            answer="Insufficient historical events recorded in your longitudinal timeline to answer this specific query with verified grounding.",
            status="INSUFFICIENT_HISTORY",
            supporting_event_ids=[]
        )

    async def dispute_insight(
        self,
        person_id: str,
        insight_id: str,
        dispute_reason: str
    ) -> bool:
        success = await self.store.update_progress_insight_status(
            person_id=person_id,
            insight_id=insight_id,
            status="DISPUTED",
            dispute_reason=dispute_reason
        )
        if success:
            # Log memory signal for Personal Agent Loop
            await self.context_service.memory_engine.extract_and_store_memory_from_event(
                person_id=person_id,
                event_payload={
                    "topic": "Progress Insight Dispute",
                    "observation": f"Learner disputed progress insight {insight_id}.",
                    "intervention": dispute_reason,
                    "event_type": "INSIGHT_DISPUTED"
                }
            )
        return success
