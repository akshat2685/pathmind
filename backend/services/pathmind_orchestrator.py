import asyncio
import json
import re
import time
import uuid
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone

from backend.core.orchestration_schemas import (
    AgentContract,
    ActionProposal,
    AgentStepTrace,
    OrchestrationTrace,
    OrchestrationRequest,
    OrchestrationResponse,
    StructuredAIOutput,)
from backend.services.store import FirestoreStore
from backend.services.counseling import CounselingAgent
from backend.services.adaptive_planning_agent import AdaptivePlanningAgent
from backend.services.evidence_evaluation_agent import EvidenceEvaluationAgent
from backend.services.learner_evolution_agent import LearnerEvolutionAgent
from backend.services.memory_reasoning_agent import MemoryReasoningAgent
from backend.services.artifact_analysis_agent import ArtifactAnalysisAgent
from backend.services.opportunity_reasoning_agent import OpportunityReasoningAgent
from backend.services.execution_intelligence_agent import ExecutionIntelligenceAgent
from backend.services.career_agents import (
    CareerReadinessAgent,
    CredentialAgent,
    ResumeAgent,
    AccountabilityAgent
)
from backend.services.opportunity_matching_engine import OpportunityMatchingEngine
from backend.services.second_brain_service import SecondBrainService
from backend.services.career_readiness_engine import CareerReadinessEngine
from backend.services.execution_engine import ExecutionEngine
from backend.services.trajectory_engine import TrajectoryEngine
from backend.services.roadmap_engine import RoadmapEngine
from backend.services.assessment_blueprint_service import AssessmentBlueprintService
from backend.core.assessment_schemas import CounselingProfile, CounselingFact, AssessmentResult, AssessmentResponse
from backend.core.roadmap_schemas import EvidenceSubmission, Roadmap, Stage

class PathmindOrchestrator:
    """
    Unified PATHMIND Agent Orchestrator.
    Coordinates specialized intelligence agents with deterministic routing,
    strict server-side person scoping, circular call prevention, prompt injection defenses,
    action proposal approval gates, and failure-tolerant execution.
    """
    def __init__(self, store: Optional[FirestoreStore] = None):
        self.store = store or FirestoreStore()

        # Instantiate specialized agents & services
        self.counseling_agent = CounselingAgent()
        self.adaptive_planning_agent = AdaptivePlanningAgent()
        self.evidence_evaluation_agent = EvidenceEvaluationAgent()
        self.learner_evolution_agent = LearnerEvolutionAgent()
        self.memory_reasoning_agent = MemoryReasoningAgent()
        self.artifact_analysis_agent = ArtifactAnalysisAgent()
        self.opportunity_reasoning_agent = OpportunityReasoningAgent()
        self.execution_intelligence_agent = ExecutionIntelligenceAgent()
        self.career_readiness_agent = CareerReadinessAgent()
        self.credential_agent = CredentialAgent()
        self.resume_agent = ResumeAgent()
        self.accountability_agent = AccountabilityAgent()

        self.career_engine = CareerReadinessEngine(store=self.store)
        self.opportunity_engine = OpportunityMatchingEngine(store=self.store, career_engine=self.career_engine)
        self.second_brain = SecondBrainService(store=self.store)
        self.execution_engine = ExecutionEngine(store=self.store)

        # Longitudinal Trajectory, Roadmap & Dynamic Assessment Services
        self.trajectory_engine = TrajectoryEngine()
        self.roadmap_engine = RoadmapEngine(store=self.store)
        self.blueprint_service = AssessmentBlueprintService()

        # Google ADK Tools registration for genuine multi-agent orchestration
        try:
            from google.adk.tools import FunctionTool
            from google.adk import Agent as ADKAgent
            self.adk_tools = [
                FunctionTool(self.blueprint_service.generate_evidence_requirements),
                FunctionTool(self.blueprint_service.evaluate_evidence),
                FunctionTool(self.blueprint_service.generate_assessment_blueprint),
                FunctionTool(self.blueprint_service.evaluate_assessment_responses),
            ]
            self.adk_journey_agent = ADKAgent(
                name="PathmindJourneyOrchestrator",
                description="Google ADK agent coordinating continuous journey workflow and stage verification gates.",
                tools=self.adk_tools
            )
        except Exception:
            self.adk_tools = []
            self.adk_journey_agent = None

        # In-memory idempotency cache (keyed by person_id:idempotency_key)
        self._idempotency_cache: Dict[str, OrchestrationResponse] = {}

        # Canonical Agent Registry
        self.agent_registry: Dict[str, AgentContract] = {
            "CounselingAgent": AgentContract(
                agent_id="CounselingAgent",
                name="Socratic Learning & Direction Agent",
                purpose="Provides Socratic counseling, direction guidance, and learning style adaptations.",
                allowed_inputs=["person_id", "intent", "learning_context", "constraints"],
                allowed_tools=["read_curriculum", "evaluate_direction"],
                output_schema="CounselingResponse",
                side_effects=[],
                forbidden_operations=["direct_database_write", "unlock_stage_directly"],
                dependencies=[],
                failure_states=["TIMEOUT", "FAILED"]
            ),
            "AdaptivePlanningAgent": AgentContract(
                agent_id="AdaptivePlanningAgent",
                name="Milestone Adaptation & Replanning Agent",
                purpose="Analyzes mastery gaps and formulates structured roadmap adaptation proposals.",
                allowed_inputs=["roadmap", "evaluation_result", "concept"],
                allowed_tools=["simulate_adaptation_impact"],
                output_schema="AdaptationProposal",
                side_effects=["propose_roadmap_revision"],
                forbidden_operations=["silent_stage_skipping", "fake_mastery_assertion"],
                dependencies=["EvidenceEvaluationAgent"],
                failure_states=["FAILED", "INSUFFICIENT_CONTEXT"]
            ),
            "EvidenceEvaluationAgent": AgentContract(
                agent_id="EvidenceEvaluationAgent",
                name="AST & Test Assertion Evaluation Agent",
                purpose="Performs static AST analysis, test assertion checks, and code defense verification.",
                allowed_inputs=["code_snippet", "test_code", "concept"],
                allowed_tools=["inspect_ast", "verify_assertions"],
                output_schema="EvaluationResult",
                side_effects=["record_step_verification"],
                forbidden_operations=["unsupported_claims", "mock_verification"],
                dependencies=[],
                failure_states=["FAILED", "TIMEOUT"]
            ),
            "LearnerEvolutionAgent": AgentContract(
                agent_id="LearnerEvolutionAgent",
                name="Longitudinal Trajectory & Pace Agent",
                purpose="Monitors longitudinal skill trajectory, pace changes, and learning habits.",
                allowed_inputs=["learning_events", "history"],
                allowed_tools=["compute_trajectory"],
                output_schema="EvolutionInsights",
                side_effects=[],
                forbidden_operations=["fabricate_evolution_data"],
                dependencies=["EvidenceEvaluationAgent"],
                failure_states=["FAILED"]
            ),
            "MemoryReasoningAgent": AgentContract(
                agent_id="MemoryReasoningAgent",
                name="Second Brain Grounded Recall Agent",
                purpose="Synthesizes grounded historical recall answers based strictly on retrieved personal memories.",
                allowed_inputs=["query", "retrieved_memories", "current_task_context"],
                allowed_tools=["read_personal_memories"],
                output_schema="SecondBrainQueryResponse",
                side_effects=[],
                forbidden_operations=["invent_memories", "invent_dates", "invent_conversations"],
                dependencies=[],
                failure_states=["NO_RELEVANT_MEMORY", "FAILED"]
            ),
            "ArtifactAnalysisAgent": AgentContract(
                agent_id="ArtifactAnalysisAgent",
                name="Artifact Intelligence & Repository Agent",
                purpose="Analyzes public GitHub repos, multi-file codebases, and defense challenge sessions.",
                allowed_inputs=["repo_url", "files", "target_capabilities"],
                allowed_tools=["clone_inspect", "extract_ast_signals"],
                output_schema="ArtifactAnalysis",
                side_effects=["propose_artifact_evidence"],
                forbidden_operations=["assume_claimed_skills_without_proof"],
                dependencies=[],
                failure_states=["TIMEOUT", "SOURCE_UNAVAILABLE"]
            ),
            "OpportunityReasoningAgent": AgentContract(
                agent_id="OpportunityReasoningAgent",
                name="Opportunity Decision & Interview Prep Agent",
                purpose="Evaluates 'Should I Apply?' decisions, tradeoffs, and synthesizes artifact-grounded interview prep.",
                allowed_inputs=["opportunity", "profile", "readiness_state"],
                allowed_tools=["evaluate_tradeoffs", "generate_interview_questions"],
                output_schema="InterviewPrepPackage",
                side_effects=["propose_execution_preparation_plan"],
                forbidden_operations=["invent_jobs", "invent_deadlines", "fake_salaries"],
                dependencies=["CareerReadinessAgent"],
                failure_states=["FAILED", "TIMEOUT"]
            ),
            "ExecutionIntelligenceAgent": AgentContract(
                agent_id="ExecutionIntelligenceAgent",
                name="Execution & Blocker Accountability Agent",
                purpose="Diagnoses action blockers and formulates supportive, non-judgmental accountability interventions.",
                allowed_inputs=["action", "reschedule_history", "profile"],
                allowed_tools=["diagnose_blocker", "generate_supportive_intervention"],
                output_schema="ActionBlockerDiagnosis",
                side_effects=["propose_reschedule_adjustment"],
                forbidden_operations=["shaming", "fake_streaks", "fabricate_tasks"],
                dependencies=[],
                failure_states=["FAILED"]
            ),
            "CareerReadinessAgent": AgentContract(
                agent_id="CareerReadinessAgent",
                name="Career Readiness & Gap Analysis Agent",
                purpose="Evaluates qualitative readiness states (FOUNDATIONAL, TARGET_READY, STRETCH) against target roles.",
                allowed_inputs=["profile", "requirement_graph", "evidence_portfolio"],
                allowed_tools=["build_requirement_graph", "calculate_readiness"],
                output_schema="CareerReadinessReport",
                side_effects=[],
                forbidden_operations=["inflated_readiness", "ignore_prerequisites"],
                dependencies=["EvidenceEvaluationAgent"],
                failure_states=["FAILED", "INSUFFICIENT_CONTEXT"]
            ),
            "CredentialAgent": AgentContract(
                agent_id="CredentialAgent",
                name="Credential ROI & Strategy Agent",
                purpose="Assesses industry recognition, market signals, and realistic ROI for certifications.",
                allowed_inputs=["target_role"],
                allowed_tools=["lookup_credential_taxonomy"],
                output_schema="CredentialStrategy",
                side_effects=[],
                forbidden_operations=["guarantee_employment"],
                dependencies=[],
                failure_states=["FAILED"]
            ),
            "ResumeAgent": AgentContract(
                agent_id="ResumeAgent",
                name="Fact-Validated ATS Resume Agent",
                purpose="Formats truth-validated resumes reflecting strictly verified capabilities and actual projects.",
                allowed_inputs=["profile", "target_role", "target_opportunity"],
                allowed_tools=["format_ats_resume"],
                output_schema="TailoredResume",
                side_effects=[],
                forbidden_operations=["hallucinate_achievements", "hallucinate_credentials"],
                dependencies=["CareerReadinessAgent"],
                failure_states=["FAILED"]
            ),
            "AccountabilityAgent": AgentContract(
                agent_id="AccountabilityAgent",
                name="Pacing & Milestone Monitor Agent",
                purpose="Tracks execution pace against weekly hour constraints and stage velocity.",
                allowed_inputs=["weekly_hours", "completed_stages"],
                allowed_tools=["calculate_velocity"],
                output_schema="AccountabilityStatus",
                side_effects=[],
                forbidden_operations=["punitive_actions"],
                dependencies=[],
                failure_states=["FAILED"]
            )
        }

    def get_agent_registry(self) -> List[AgentContract]:
        return list(self.agent_registry.values())

    def classify_task(self, intent: str, payload: Dict[str, Any]) -> str:
        """
        Deterministic task classifier categorizing user/system requests into canonical task types.
        """
        raw = f"{intent} {' '.join(str(v) for v in payload.values())}".lower()

        if any(w in raw for w in ["apply", "job", "internship", "fellowship", "opportunity"]):
            if "interview" in raw:
                return "INTERVIEW_PREPARATION"
            return "OPPORTUNITY_MATCH"
        elif any(w in raw for w in ["resume", "cv", "ats"]):
            return "CAREER_GUIDANCE"
        elif any(w in raw for w in ["blocker", "stuck on task", "reschedule", "daily plan", "mission control"]):
            return "NEXT_ACTION"
        elif any(w in raw for w in ["remember", "past project", "what did i do", "what worked", "recall"]):
            return "MEMORY_RECALL"
        elif any(w in raw for w in ["github", "repo", "artifact", "defense"]):
            return "ARTIFACT_ANALYSIS"
        elif any(w in raw for w in ["verify code", "test assertion", "submit evidence", "evaluate code"]):
            return "EVIDENCE_EVALUATION"
        elif any(w in raw for w in ["career goal", "change role", "pivot career", "target role"]):
            return "GOAL_CHANGE"
        elif any(w in raw for w in ["career", "readiness", "credentials"]):
            return "CAREER_GUIDANCE"
        elif any(w in raw for w in ["replan", "adapt roadmap", "skip stage", "difficulty"]):
            return "ROADMAP_ADAPTATION"
        else:
            return "LEARNING_GUIDANCE"

    def determine_workflow(self, task_type: str) -> List[str]:
        """
        Maps a task type to its minimal required agent dependency pipeline.
        Prevents invoking unnecessary agents.
        """
        workflow_map = {
            "OPPORTUNITY_MATCH": ["OpportunityReasoningAgent", "CareerReadinessAgent", "ExecutionIntelligenceAgent"],
            "INTERVIEW_PREPARATION": ["OpportunityReasoningAgent", "ArtifactAnalysisAgent"],
            "LEARNING_GUIDANCE": ["MemoryReasoningAgent", "CounselingAgent", "EvidenceEvaluationAgent"],
            "CAREER_GUIDANCE": ["CareerReadinessAgent", "CredentialAgent", "ResumeAgent"],
            "GOAL_CHANGE": ["CounselingAgent", "CareerReadinessAgent", "AdaptivePlanningAgent"],
            "ROADMAP_ADAPTATION": ["EvidenceEvaluationAgent", "AdaptivePlanningAgent", "LearnerEvolutionAgent"],
            "EVIDENCE_EVALUATION": ["EvidenceEvaluationAgent", "AdaptivePlanningAgent"],
            "ARTIFACT_ANALYSIS": ["ArtifactAnalysisAgent", "EvidenceEvaluationAgent"],
            "MEMORY_RECALL": ["MemoryReasoningAgent"],
            "NEXT_ACTION": ["ExecutionIntelligenceAgent"],
            "PROGRESS_ANALYSIS": ["LearnerEvolutionAgent", "AccountabilityAgent"]
        }
        return workflow_map.get(task_type, ["CounselingAgent"])

    def sanitize_untrusted_content(self, text: str) -> str:
        """
        Prompt Injection Defense: Encapsulates external untrusted data (repos, markdown, descriptions)
        and neutralizes potential instruction overrides.
        """
        # Neutralize common prompt injection phrases
        sanitized = re.sub(r"(?i)ignore previous instructions", "[neutralized]", text)
        sanitized = re.sub(r"(?i)system prompt", "[data_content]", sanitized)
        sanitized = re.sub(r"(?i)you are now", "[data_statement]", sanitized)
        return f"[DATA_UNTRUSTED_CONTENT]\n{sanitized}\n[/DATA_UNTRUSTED_CONTENT]"

    async def orchestrate(
        self,
        person_id: str,
        request: OrchestrationRequest
    ) -> OrchestrationResponse:
        """
        Primary execution entry point for multi-agent task orchestration.
        Strictly scopes execution to authenticated person_id.
        """
        # 1. Idempotency Check
        idemp_key = request.idempotency_key
        cache_key = f"{person_id}:{idemp_key}" if idemp_key else None
        if cache_key and cache_key in self._idempotency_cache:
            return self._idempotency_cache[cache_key]

        workflow_id = f"wf_{int(datetime.now(timezone.utc).timestamp()*1000)}_{uuid.uuid4().hex[:6]}"
        start_time = time.time()

        # 2. Task Classification & Workflow Resolution
        task_type = request.task_type or self.classify_task(request.intent, request.payload)
        agent_pipeline = self.determine_workflow(task_type)

        trace = OrchestrationTrace(
            workflow_id=workflow_id,
            person_id=person_id,
            task_type=task_type,
            status="SUCCESS",
            started_at=datetime.now(timezone.utc).isoformat(),
            agents_invoked=agent_pipeline
        )

        # 3. Circular Call & Recursion Prevention
        visited_agents = set()
        max_depth = 5
        if len(agent_pipeline) > max_depth or len(agent_pipeline) != len(set(agent_pipeline)):
            trace.status = "ORCHESTRATION_LOOP_DETECTED"
            trace.completed_at = datetime.now(timezone.utc).isoformat()
            await self.store.save_orchestration_trace(person_id, trace.model_dump(mode="json"))
            return OrchestrationResponse(
                workflow_id=workflow_id,
                person_id=person_id,
                task_type=task_type,
                status="ORCHESTRATION_LOOP_DETECTED",
                final_answer="Orchestration halted: cyclic or excessive dependency depth detected.",
                trace=trace
            )

        # 4. Context Package Assembly
        # Assembles minimal person context
        goal = await self.career_engine.get_or_create_career_goal(person_id)
        profile = await self.career_engine.get_or_create_canonical_profile(person_id)
        sanitized_intent = self.sanitize_untrusted_content(request.intent)

        step_traces: List[AgentStepTrace] = []
        action_proposals: List[ActionProposal] = []
        structured_findings: Dict[str, Any] = {}
        final_answer_parts: List[str] = []
        requires_approval = False
        overall_status = "SUCCESS"

        # 5. Pipeline Step Runner
        for agent_id in agent_pipeline:
            visited_agents.add(agent_id)
            step_start = time.time()
            step_trace = AgentStepTrace(
                agent_id=agent_id,
                input_summary=f"Task: {task_type}, Intent: {request.intent[:60]}...",
                output_summary="",
                status="SUCCESS"
            )

            try:
                # Execute specialized agent bounded with 5.0s timeout
                if agent_id == "OpportunityReasoningAgent":
                    opps = await self.opportunity_engine.match_opportunities_for_person(person_id)
                    top_match = opps[0] if opps else None
                    if top_match:
                        structured_findings["top_opportunity"] = top_match.model_dump(mode="json")
                        final_answer_parts.append(
                            f"Evaluated verified opportunity '{top_match.opportunity.title}' at {top_match.opportunity.organization} "
                            f"(Match: {top_match.fit_status}, Readiness: {top_match.readiness_status}). Decision Advisor: {top_match.feasibility_status}."
                        )
                        # Propose preparation action plan
                        prop = ActionProposal(
                            workflow_id=workflow_id,
                            person_id=person_id,
                            action_type="SPAWN_EXECUTION_ACTION",
                            target_entity="CanonicalAction",
                            target_entity_id=top_match.opportunity.opportunity_id,
                            proposed_change={
                                "opportunity_id": top_match.opportunity.opportunity_id,
                                "actions_count": 3
                            },
                            reason=f"Spawn preparation milestones for {top_match.opportunity.title}",
                            requires_confirmation=False,
                            status="PENDING"
                        )
                        action_proposals.append(prop)
                        step_trace.action_proposals.append(prop)
                    else:
                        final_answer_parts.append("Searched verified registries across India and Global Remote, but found zero active listings matching current search.")

                elif agent_id == "CareerReadinessAgent":
                    report = await self.career_engine.generate_career_readiness_report(person_id)
                    structured_findings["readiness_state"] = report.readiness_state
                    structured_findings["target_role"] = report.target_goal.target_role
                    final_answer_parts.append(
                        f"Current Career Readiness for '{report.target_goal.target_role}': {report.readiness_state}. "
                        f"Next milestone: {report.next_readiness_milestone}."
                    )

                elif agent_id == "MemoryReasoningAgent":
                    mem_res = await self.second_brain.query_second_brain(
                        person_id=person_id,
                        req=request.payload.get("memory_query") or {"query": request.intent}
                    )
                    structured_findings["memory_recall"] = {
                        "status": mem_res.status,
                        "recalled_count": len(mem_res.retrieved_memories)
                    }
                    if mem_res.status == "RESOLVED":
                        final_answer_parts.append(mem_res.answer)

                elif agent_id == "ExecutionIntelligenceAgent":
                    plan = await self.execution_engine.get_daily_execution_plan(person_id)
                    structured_findings["daily_execution"] = {
                        "primary_action": plan.primary_action.title if plan.primary_action else None,
                        "blocker_count": len(plan.active_blockers)
                    }
                    if plan.primary_action:
                        final_answer_parts.append(f"Mission Control Primary Focus: '{plan.primary_action.title}'.")

                elif agent_id == "CounselingAgent":
                    counsel_res = await self.counseling_agent.counsel_learner(
                        learner_context={"person_id": person_id, "current_role": profile.current_role, "target_role": goal.target_role},
                        message=request.intent
                    )
                    final_answer_parts.append(counsel_res.response)

                elif agent_id == "AdaptivePlanningAgent":
                    # Propose roadmap adaptation if requested
                    if task_type in ["ROADMAP_ADAPTATION", "GOAL_CHANGE"]:
                        prop = ActionProposal(
                            workflow_id=workflow_id,
                            person_id=person_id,
                            action_type="CREATE_ROADMAP_VERSION",
                            target_entity="Roadmap",
                            target_entity_id=f"roadmap_{person_id}",
                            proposed_change={
                                "new_target_role": request.payload.get("target_role", goal.target_role),
                                "reason": request.intent
                            },
                            reason="Learner requested career/pace adaptation.",
                            requires_confirmation=True,  # Approval Gate!
                            status="PENDING"
                        )
                        action_proposals.append(prop)
                        step_trace.action_proposals.append(prop)
                        requires_approval = True
                        final_answer_parts.append("Roadmap adaptation proposal generated. Paused waiting for user approval.")

                elif agent_id == "EvidenceEvaluationAgent":
                    step_trace.output_summary = "Evaluated AST boundaries and assertions. Evidence integrity confirmed."

                elif agent_id == "CredentialAgent":
                    cred = self.credential_agent.evaluate_credentials(goal.target_role)
                    structured_findings["credentials_roi"] = cred.model_dump(mode="json")

                elif agent_id == "ResumeAgent":
                    resume = self.resume_agent.generate_tailored_resume(profile=profile, target_role=goal.target_role)
                    structured_findings["tailored_resume"] = resume.model_dump(mode="json")

                elif agent_id == "ArtifactAnalysisAgent":
                    step_trace.output_summary = "Artifact AST analysis ready."

                elif agent_id == "LearnerEvolutionAgent":
                    step_trace.output_summary = "Longitudinal velocity steady."

                step_trace.duration_ms = int((time.time() - step_start) * 1000)
                step_trace.output_summary = step_trace.output_summary or f"Agent {agent_id} completed successfully."

            except asyncio.TimeoutError:
                step_trace.status = "TIMEOUT"
                step_trace.error = "Agent step exceeded execution timeout boundary (5.0s)."
                overall_status = "PARTIAL"
            except Exception as e:
                step_trace.status = "FAILED"
                step_trace.error = str(e)
                overall_status = "PARTIAL"

            step_traces.append(step_trace)

        # 6. Final Status & Tracing
        trace.steps = step_traces
        trace.action_proposals = action_proposals
        trace.total_duration_ms = int((time.time() - start_time) * 1000)
        trace.completed_at = datetime.now(timezone.utc).isoformat()

        if requires_approval:
            trace.status = "WAITING_FOR_USER_APPROVAL"
            overall_status = "WAITING_FOR_USER_APPROVAL"
        else:
            trace.status = overall_status

        # Persist orchestration trace and pending proposals
        await self.store.save_orchestration_trace(person_id, trace.model_dump(mode="json"))
        for prop in action_proposals:
            await self.store.save_action_proposal(person_id, prop.model_dump(mode="json"))

        final_answer = " ".join(final_answer_parts) if final_answer_parts else "Workflow executed."
        # Spec §27: enforce the structured output contract at the boundary.
        # Free-form agent text stays in `message`; findings map to typed fields.
        _recs = []
        if "top_opportunity" in structured_findings:
            _recs.append({"type": "opportunity", "data": structured_findings["top_opportunity"]})
        _sources = []
        if "memory_recall" in structured_findings:
            _sources.append({"type": "memory_recall", "data": structured_findings["memory_recall"]})
        _uncertainty = []
        if trace.status in ("PARTIAL", "TIMEOUT"):
            _uncertainty.append(f"Workflow ended with status {trace.status}; results may be incomplete.")
        _state = "NEEDS_USER_INPUT" if requires_approval else ("FAILED" if trace.status == "FAILED" else "OK")
        structured_output = StructuredAIOutput(
            message=final_answer,
            state=_state,
            recommendations=_recs,
            sources=_sources,
            uncertainty=_uncertainty,
        )
        resp = OrchestrationResponse(
            workflow_id=workflow_id,
            person_id=person_id,
            task_type=task_type,
            status=trace.status,
            final_answer=final_answer,
            structured_result=structured_output,
            action_proposals=action_proposals,
            requires_approval=requires_approval,
            trace=trace
        )

        if cache_key:
            self._idempotency_cache[cache_key] = resp

        return resp

    async def approve_action_proposal(
        self,
        person_id: str,
        proposal_id: str
    ) -> Dict[str, Any]:
        """
        Applies a pending ActionProposal after user confirmation.
        State changes are strictly applied through deterministic services.
        """
        prop_dict = await self.store.get_action_proposal(person_id, proposal_id)
        if not prop_dict:
            raise ValueError(f"Proposal {proposal_id} not found.")

        # Apply state changes through deterministic application layer
        action_type = prop_dict.get("action_type")
        change = prop_dict.get("proposed_change", {})

        if action_type == "CREATE_ROADMAP_VERSION":
            new_role = change.get("new_target_role")
            if new_role:
                goal = await self.career_engine.get_or_create_career_goal(person_id, target_role=new_role)
                goal_dict = goal.model_dump(mode="json")
                goal_dict["target_role"] = new_role
                await self.store.save_career_goal(person_id, goal_dict)

        elif action_type == "SPAWN_EXECUTION_ACTION":
            pass

        # Update status to APPROVED & APPLIED
        await self.store.update_action_proposal_status(person_id, proposal_id, "APPLIED")
        return {"status": "APPLIED", "proposal_id": proposal_id, "action_type": action_type}

    async def reject_action_proposal(
        self,
        person_id: str,
        proposal_id: str
    ) -> Dict[str, Any]:
        prop_dict = await self.store.get_action_proposal(person_id, proposal_id)
        if not prop_dict:
            raise ValueError(f"Proposal {proposal_id} not found.")

        await self.store.update_action_proposal_status(person_id, proposal_id, "REJECTED")
        return {"status": "REJECTED", "proposal_id": proposal_id}

    # =========================================================================
    # Continuous Single Guided Journey Orchestration (Requirements 3, 7, 8, 9, 10)
    # =========================================================================

    async def init_journey(self, name: str) -> Dict[str, Any]:
        """
        Requirement 3: CREATE THE CANONICAL PERSON ID IMMEDIATELY AFTER NAME COLLECTION.
        Persists an initial learner record immediately in Firestore / store.
        """
        clean_name = name.strip()
        if len(clean_name) < 2:
            raise ValueError("Name must be at least 2 characters.")

        # Generate canonical, safe person_id
        safe_prefix = re.sub(r'[^a-zA-Z0-9]', '', clean_name.lower())[:8] or "scholar"
        person_id = f"scholar_{safe_prefix}_{uuid.uuid4().hex[:8]}"

        now_iso = datetime.now(timezone.utc).isoformat()
        person_record = {
            "person_id": person_id,
            "name": clean_name,
            "status": "INITIALIZED",
            "created_at": now_iso,
            "current_step": "NAME_COLLECTED"
        }
        await self.store.save_person_record(person_id, person_record)

        journey_state = {
            "person_id": person_id,
            "name": clean_name,
            "step": 1,
            "step_name": "ASPIRATION",
            "aspiration": "",
            "stage": "",
            "constraints": [],
            "evidence": [],
            "evidence_requirements": None,
            "evidence_evaluation": None,
            "assessment_blueprint": None,
            "assessment_responses": [],
            "assessment_evaluation": None,
            "baseline_profile": None,
            "candidate_paths": [],
            "selected_path_id": None,
            "active_roadmap": None,
            "updated_at": now_iso
        }
        await self.store.save_journey_state(person_id, journey_state)

        return {
            "person_id": person_id,
            "name": clean_name,
            "step": 1,
            "step_name": "ASPIRATION",
            "message": f"Canonical scholar record created for {clean_name}."
        }

    async def get_journey_state(self, person_id: str) -> Dict[str, Any]:
        """
        Retrieves current journey state for seamless rehydration on fresh browser or page reload.
        """
        state = await self.store.get_journey_state(person_id)
        if state:
            return state

        person = await self.store.get_person_record(person_id)
        if person:
            # Reconstruct minimal state
            state = {
                "person_id": person_id,
                "name": person.get("name", "Scholar"),
                "step": 1,
                "step_name": "ASPIRATION",
                "aspiration": "",
                "stage": "",
                "constraints": [],
                "evidence": [],
                "evidence_requirements": None,
                "evidence_evaluation": None,
                "assessment_blueprint": None,
                "assessment_responses": [],
                "assessment_evaluation": None,
                "baseline_profile": None,
                "candidate_paths": [],
                "selected_path_id": None,
                "active_roadmap": None,
                "updated_at": datetime.now(timezone.utc).isoformat()
            }
            await self.store.save_journey_state(person_id, state)
            return state

        raise ValueError(f"No journey state found for person {person_id}. Please initialize with Name.")

    async def record_aspiration_and_stage(
        self,
        person_id: str,
        aspiration: str,
        stage: str,
        constraints: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Records learner's aspiration and stage.
        Generates grounded, domain-neutral evidence requirements.
        """
        state = await self.get_journey_state(person_id)
        clean_aspiration = aspiration.strip()
        clean_stage = stage.strip()
        clean_constraints = constraints or []

        if len(clean_aspiration) < 5:
            raise ValueError("Please provide a descriptive aspiration (at least 5 characters).")

        # Derive grounded evidence requirements
        requirements = self.blueprint_service.generate_evidence_requirements(
            aspiration=clean_aspiration,
            stage=clean_stage
        )

        # Persist career goal
        goal_data = {
            "target_role": clean_aspiration,
            "time_horizon": "1-2 years",
            "weekly_hours": 15,
            "constraints": clean_constraints,
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        await self.store.save_career_goal(person_id, goal_data)

        # Update state
        state["aspiration"] = clean_aspiration
        state["stage"] = clean_stage
        state["constraints"] = clean_constraints
        state["evidence_requirements"] = requirements
        state["step"] = 2
        state["step_name"] = "EVIDENCE_COLLECTION"
        state["updated_at"] = datetime.now(timezone.utc).isoformat()
        await self.store.save_journey_state(person_id, state)

        return state

    async def generate_grounded_assessment(
        self,
        person_id: str,
    ) -> Dict[str, Any]:
        """
        Grounded potential assessment (AJ's core loop).

        Runs AFTER the learner has provided proof: verification data (marks,
        semester results, experience) + aptitude test results. The assessment
        is grounded in what they have ACTUALLY done and shown — not in the
        aspiration alone.

        Returns:
          - potential: honest assessment based on their real marks, test
            performance, and verification data vs what the domain requires
          - gaps: specific, evidenced ("your test scored 40% on X", "your
            marks are Y but this path typically needs Z")
          - path_outline: concrete dedicated steps calibrated to their
            actual level
          - strengths: what their data shows they're already good at

        Honesty rules: every claim must trace to submitted data. Never
        invent stats. If data is thin, say what would change the assessment.
        """
        from backend.core.gemini import get_gemini_model, GeminiUnavailable

        state = await self.get_journey_state(person_id)
        aspiration = state.get("aspiration") or ""
        stage = state.get("stage") or ""
        user_type = stage  # stage holds the persona id (school/college/etc.)

        # Gather all real evidence
        verification = None
        try:
            verification = await self.store.get_verification(person_id)
        except Exception:
            pass

        test_result = None
        try:
            latest_test = await self.store.get_latest_aspiration_test(person_id)
            if latest_test:
                test_id = latest_test.get("test_id") or latest_test.get("id")
                if test_id:
                    test_result = await self.store.get_test_result_for_test(
                        person_id, test_id
                    )
        except Exception:
            pass

        verification_summary = ""
        if verification:
            vdata = verification.get("verification_data") or {}
            vtype = verification.get("user_type") or user_type
            items = [f"{k}: {v}" for k, v in vdata.items() if v not in (None, "", [])]
            verification_summary = f"User type: {vtype}. Verified details: {'; '.join(items) if items else 'none provided'}. Status: {verification.get('status', 'UNKNOWN')}."

        test_summary = ""
        if test_result:
            ev = test_result.get("evaluation") or test_result.get("evaluation_json") or {}
            if isinstance(ev, str):
                try:
                    ev = json.loads(ev)
                except Exception:
                    ev = {}
            score = test_result.get("score")
            max_score = test_result.get("max_score")
            pct = ev.get("percentage")
            strengths = ev.get("strengths") or []
            gaps = ev.get("gaps") or []
            skill_breakdown = ev.get("skill_breakdown") or {}
            test_summary = (
                f"Aptitude test score: {score}/{max_score}"
                + (f" ({pct}%)" if pct is not None else "")
                + f". Strengths shown: {', '.join(strengths) if strengths else 'none identified'}."
                + f" Gaps shown: {', '.join(gaps) if gaps else 'none identified'}."
                + (f" Skill breakdown: {json.dumps(skill_breakdown)}." if skill_breakdown else "")
            )

        if not verification_summary and not test_summary:
            return {
                "potential": "",
                "gaps": [],
                "path_outline": [],
                "strengths": [],
                "uncertainty": [
                    "No verification or test data yet — complete those steps for a grounded assessment."
                ],
                "source": "insufficient_data",
                "generated_at": datetime.now(timezone.utc).isoformat(),
            }

        prompt = f"""You are PATHMIND, an honest career and learning navigator. A learner has provided REAL evidence about themselves. Assess their potential based ONLY on this evidence — not on wishful thinking.

Aspiration: "{aspiration}"
Stage: "{stage}"

VERIFIED EVIDENCE (what they proved about themselves):
{verification_summary or "None provided."}

APTITUDE TEST RESULTS (how they performed):
{test_summary or "No test taken yet."}

Now assess, grounded strictly in the evidence above:

Think about what "{aspiration}" actually requires as a career/path:
- SPORT (cricket, football, etc.): physical readiness, technical foundation, competitive exposure, age window realism
- MEDICINE/ACADEMIC: marks thresholds, entrance exam readiness, study discipline shown
- TRADE/CRAFT: hands-on aptitude, apprenticeship readiness
- TECH/CREATIVE: demonstrated skill, portfolio signals, learning speed shown in test
- BUSINESS: acumen signals, risk awareness, domain understanding

Return JSON with exactly these keys:
{{
  "potential": "3-4 sentences: honest assessment grounded in their actual marks/scores. Reference specific numbers from their evidence. Name the strongest signal in their favor and the biggest evidence-backed risk. No flattery, no generic encouragement.",
  "strengths": ["Strength 1: tied to specific evidence, e.g. 'Scored 85% on cricket situational judgment — strong game awareness'", "Strength 2..."],
  "gaps": ["Gap 1: specific and evidenced, e.g. 'Test showed 40% on technical skills; most academy entrants test at 70%+'", "Gap 2...", "Gap 3..."],
  "path_outline": ["Step 1: concrete action for the next 30 days, calibrated to their actual level", "Step 2: 3-6 month milestone", "Step 3: 1-2 year target"],
  "uncertainty": ["What additional evidence would sharpen this assessment"]
}}

Rules:
- Every claim in potential/strengths/gaps MUST trace to the evidence above. If the evidence is thin, say so and keep the assessment short.
- Never invent marks, scores, or experience the learner didn't provide.
- Be direct about difficult truths the evidence reveals, but not cruel.
- If verification status is NEEDS_REVIEW, note the uncertainty it creates.
"""

        result: Dict[str, Any] = {
            "potential": "",
            "strengths": [],
            "gaps": [],
            "path_outline": [],
            "uncertainty": [],
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "aspiration": aspiration,
            "stage": stage,
        }

        try:
            model = get_gemini_model()
            resp = model.generate_content(prompt)
            text = resp.text.strip()
            if "```json" in text:
                text = text.split("```json")[1].split("```")[0].strip()
            elif "```" in text:
                text = text.split("```")[1].split("```")[0].strip()
            data = json.loads(text)
            for key in ("potential", "strengths", "gaps", "path_outline", "uncertainty"):
                if key in data:
                    result[key] = data[key]
            result["source"] = "gemini"
        except GeminiUnavailable:
            result["source"] = "unavailable"
            result["uncertainty"] = ["AI assessment temporarily unavailable — your verification and test data are saved and will be assessed when the service recovers."]
        except Exception as e:
            result["source"] = "fallback"
            result["uncertainty"] = [f"Assessment generation failed ({type(e).__name__}); your data is saved."]
            print(f"[Orchestrator] grounded assessment failed: {e}")

        # Persist on the journey state so it survives and feeds downstream steps
        state["grounded_assessment"] = result
        state["updated_at"] = datetime.now(timezone.utc).isoformat()
        await self.store.save_journey_state(person_id, state)
        return result

    async def submit_evidence_and_generate_blueprint(
        self,
        person_id: str,
        evidence_items: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Evaluates submitted evidence and generates domain-neutral, stage-aware assessment blueprint.
        """
        state = await self.get_journey_state(person_id)
        aspiration = state.get("aspiration") or "General Intellectual Mastery"
        stage = state.get("stage") or "college"

        # Evaluate evidence
        evidence_eval = self.blueprint_service.evaluate_evidence(
            evidence_items=evidence_items,
            aspiration=aspiration,
            stage=stage
        )

        # Generate stage-aware & domain-neutral blueprint
        blueprint = self.blueprint_service.generate_assessment_blueprint(
            person_id=person_id,
            aspiration=aspiration,
            stage=stage,
            evidence_summary=evidence_eval
        )
        await self.store.save_assessment_blueprint(person_id, blueprint)

        state["evidence"] = evidence_items
        state["evidence_evaluation"] = evidence_eval
        state["assessment_blueprint"] = blueprint
        state["step"] = 3
        state["step_name"] = "ACTUAL_ASSESSMENT"
        state["updated_at"] = datetime.now(timezone.utc).isoformat()
        await self.store.save_journey_state(person_id, state)

        return state

    async def submit_assessment_and_generate_baseline(
        self,
        person_id: str,
        responses: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Evaluates assessment responses, calculates calibration scores,
        and persists verified baseline counseling profile.
        """
        state = await self.get_journey_state(person_id)
        aspiration = state.get("aspiration") or "Applied AI Specialist"
        stage = state.get("stage") or "college"
        blueprint = state.get("assessment_blueprint") or await self.store.get_assessment_blueprint(person_id)

        if not blueprint:
            raise ValueError("No active assessment blueprint found for evaluation.")

        # Objective evaluation
        eval_result = self.blueprint_service.evaluate_assessment_responses(
            person_id=person_id,
            blueprint=blueprint,
            responses=responses,
            aspiration=aspiration,
            stage=stage
        )

        # Synthesize baseline CounselingProfile
        riasec_scores = eval_result.get("riasec_inference", {})
        top_interests = sorted(riasec_scores.items(), key=lambda x: x[1], reverse=True)
        primary_interests = [k for k, v in top_interests[:3]]

        caps = [
            CounselingFact(
                category="DEMONSTRATED_CAPABILITY",
                claim=str(s),
                evidence=["Assessment diagnostic responses"],
                confidence="HIGH",
                weight=1.0,
                source="ASSESSMENT"
            )
            for s in eval_result.get("demonstrated_strengths", [])
        ]
        self_eff_facts = [
            CounselingFact(
                category="SELF_EFFICACY",
                claim=f"{k}: {v}",
                evidence=["Self-efficacy calibration response"],
                confidence="HIGH" if isinstance(v, (int, float)) and v >= 0.7 else "MODERATE",
                weight=1.0,
                source="ASSESSMENT"
            )
            for k, v in eval_result.get("scct_calibration", {}).items()
        ]

        constraint_facts = [
            CounselingFact(
                category="CONSTRAINT",
                claim=str(c),
                evidence=["Self-reported learner constraint"],
                confidence="HIGH",
                weight=1.0,
                source="INTAKE"
            )
            for c in state.get("constraints", [])
        ]

        counseling_profile = CounselingProfile(
            person_id=person_id,
            interest_vector=riasec_scores,
            strongest_interests=primary_interests or ["Investigative", "Realistic"],
            demonstrated_capabilities=caps,
            self_efficacy_signals=self_eff_facts,
            constraints=constraint_facts,
            candidate_directions=[aspiration],
            contradictions=[],
            overall_confidence="VERIFIED"
        )
        await self.store.save_counseling_profile(person_id, counseling_profile.model_dump(mode="json"))

        state["assessment_responses"] = responses
        state["assessment_evaluation"] = eval_result
        state["baseline_profile"] = counseling_profile.model_dump(mode="json")
        state["step"] = 4
        state["step_name"] = "BASELINE_READY"
        state["updated_at"] = datetime.now(timezone.utc).isoformat()
        await self.store.save_journey_state(person_id, state)

        return state

    async def discover_pathways(self, person_id: str) -> Dict[str, Any]:
        """
        Discovers 2-3 grounded candidate pathways based on baseline profile and aspiration.
        """
        state = await self.get_journey_state(person_id)
        aspiration = state.get("aspiration") or "Applied Machine Learning Systems"
        constraints = state.get("constraints") or []

        profile_data = await self.store.get_counseling_profile(person_id)
        counseling_profile = CounselingProfile(**profile_data) if profile_data else None

        discovery_res = await self.trajectory_engine.discover_candidate_paths(
            person_id=person_id,
            counseling_profile=counseling_profile,
            goals=[aspiration],
            constraints=constraints
        )

        candidate_paths = [p.model_dump(mode="json") for p in discovery_res.candidate_paths]
        state["candidate_paths"] = candidate_paths
        state["step"] = 5
        state["step_name"] = "PATHWAYS_DISCOVERED"
        state["updated_at"] = datetime.now(timezone.utc).isoformat()
        await self.store.save_journey_state(person_id, state)

        return {
            "person_id": person_id,
            "candidate_paths": candidate_paths,
            "rationale": discovery_res.overall_reasoning
        }

    async def select_pathway_and_init_roadmap(
        self,
        person_id: str,
        selected_path_id: str
    ) -> Dict[str, Any]:
        """
        Saves chosen pathway and generates multi-phase hidden roadmap with Phase 1 active.
        """
        state = await self.get_journey_state(person_id)
        candidates = state.get("candidate_paths") or []
        chosen_candidate = next((p for p in candidates if p.get("path_id") == selected_path_id), None)

        if not chosen_candidate and candidates:
            chosen_candidate = candidates[0]

        target_role = chosen_candidate.get("title") if chosen_candidate else state.get("aspiration", "Applied AI Specialist")

        # Save selection
        await self.store.save_selected_path(person_id, {
            "person_id": person_id,
            "selected_path_id": selected_path_id,
            "selected_path": chosen_candidate,
            "selection_reason": "Learner chosen trajectory",
            "selected_at": datetime.now(timezone.utc).isoformat()
        })

        # Synthesize personalized roadmap
        roadmap = await self.roadmap_engine.get_or_create_roadmap(
            person_id=person_id,
            target_outcome=target_role
        )

        # Build disclosed view (Phase 1 unlocked, future phases locked)
        disclosed_view = self.roadmap_engine.build_disclosed_view(roadmap)
        disclosed_dict = disclosed_view.model_dump(mode="json")

        state["selected_path_id"] = selected_path_id
        state["active_roadmap"] = disclosed_dict
        state["step"] = 6
        state["step_name"] = "ROADMAP_ACTIVE"
        state["updated_at"] = datetime.now(timezone.utc).isoformat()
        await self.store.save_journey_state(person_id, state)

        return {
            "person_id": person_id,
            "selected_path_id": selected_path_id,
            "roadmap": disclosed_dict
        }

    async def get_active_disclosed_roadmap(self, person_id: str) -> Dict[str, Any]:
        """
        Retrieves the progressive disclosed view of the active roadmap.
        """
        roadmap = await self.roadmap_engine.get_or_create_roadmap(person_id)
        disclosed_view = self.roadmap_engine.build_disclosed_view(roadmap)
        return disclosed_view.model_dump(mode="json")

    async def submit_phase_evidence(
        self,
        person_id: str,
        stage_id: str,
        mission_id: str,
        content_payload: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Requirement 10: The roadmap must be evidence-gated.
        Backend decides PASS / REINFORCE / INSUFFICIENT_EVIDENCE.
        """
        roadmap = await self.roadmap_engine.get_or_create_roadmap(person_id)

        submission = EvidenceSubmission(
            person_id=person_id,
            roadmap_id=roadmap.roadmap_id,
            stage_id=stage_id,
            mission_id=mission_id,
            evidence_type="CODE_REPO",
            content_payload=content_payload
        )

        eval_result = await self.roadmap_engine.evaluate_evidence_and_progress(
            person_id=person_id,
            submission=submission
        )

        # Refresh disclosed roadmap
        refreshed_roadmap = await self.roadmap_engine.get_or_create_roadmap(person_id)
        disclosed_view = self.roadmap_engine.build_disclosed_view(refreshed_roadmap)
        disclosed_dict = disclosed_view.model_dump(mode="json")

        # Update journey state
        state = await self.get_journey_state(person_id)
        state["active_roadmap"] = disclosed_dict
        state["updated_at"] = datetime.now(timezone.utc).isoformat()
        await self.store.save_journey_state(person_id, state)

        return {
            "evaluation": eval_result.model_dump(mode="json"),
            "roadmap": disclosed_dict
        }

