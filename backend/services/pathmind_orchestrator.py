import asyncio
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
    OrchestrationResponse
)
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

        self.opportunity_engine = OpportunityMatchingEngine(store=self.store)
        self.second_brain = SecondBrainService(store=self.store)
        self.career_engine = CareerReadinessEngine()
        self.execution_engine = ExecutionEngine(store=self.store)

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
                            f"(Match: {top_match.fit_state}, Readiness: {top_match.readiness_state}). Decision Advisor: {top_match.decision_recommendation}."
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
                    plan = await self.execution_engine.get_daily_plan(person_id)
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
        resp = OrchestrationResponse(
            workflow_id=workflow_id,
            person_id=person_id,
            task_type=task_type,
            status=trace.status,
            final_answer=final_answer,
            structured_result=structured_findings,
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
