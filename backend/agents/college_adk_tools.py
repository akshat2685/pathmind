"""
ADK FunctionTools for the PathMind College MVP (TRD §5).

Every tool is typed, narrow, and scoped: the agent never gets generic DB
access. Tools wrap the Phase-1 deterministic services and stores directly:

  - deterministic logic (auth, scoring, streaks, unlocks, countdowns) lives in
    `backend/core/college_rules.py` and the college_* services — the LLM never
    computes those values, it only invokes these tools and reads results.

The authenticated learner UID is injected per-call via ADK session state
(`tool_context.state["uid"]`), never accepted from the agent as an argument,
so one learner can never query another's data.
"""

from __future__ import annotations

import json
import logging
from typing import Any, Dict, List, Optional

try:
    from google.adk.tools import FunctionTool, ToolContext
    _ADK_TOOLS_OK = True
except ImportError:  # pragma: no cover - envs without a working google.adk
    # Same rule as college_adk_agents: a broken google namespace must degrade,
    # never crash module import. ToolContext is annotation-only (PEP 563, the
    # file has `from __future__ import annotations`), so only FunctionTool
    # needs a runtime guard in as_function_tools().
    FunctionTool = None  # type: ignore[assignment]
    ToolContext = None  # type: ignore[assignment]
    _ADK_TOOLS_OK = False

from backend.core.college_schemas import (
    CollegeAssessmentSubmission,
    CommitmentStatus,
    EngineeringBranch,
    PlanScope,
)
from backend.core.college_logging import log_event
from backend.services.academic_service import AcademicService
from backend.services.college_accountability_service import CollegeAccountabilityService
from backend.services.college_assessment_service import CollegeAssessmentService
from backend.services.college_learning_service import CollegeLearningService
from backend.services.college_memory_service import CollegeMemoryService
from backend.services.college_resource_pipeline import CollegeResourcePipeline
from backend.services.college_store import CollegeStore
from backend.services.pyq_service import PYQService

logger = logging.getLogger(__name__)


def _uid(tool_context: ToolContext) -> Optional[str]:
    state = getattr(tool_context, "state", None) or {}
    return state.get("uid")


def _require_uid(tool_context: ToolContext) -> str:
    uid = _uid(tool_context)
    if not uid:
        raise PermissionError("AUTH_REQUIRED")
    return uid


def _dump(obj: Any) -> Any:
    if hasattr(obj, "model_dump"):
        return obj.model_dump(mode="json")
    if isinstance(obj, list):
        return [_dump(o) for o in obj]
    return obj


class CollegeToolKit:
    """Builds the TRD §5 tool set bound to one store."""

    def __init__(self, store: Optional[CollegeStore] = None):
        self.store = store or CollegeStore()
        self.academic = AcademicService(self.store)
        self.learning = CollegeLearningService(self.store)
        self.assessment = CollegeAssessmentService(self.store)
        self.accountability = CollegeAccountabilityService(self.store)
        self.memory = CollegeMemoryService(self.store)
        self.pyq = PYQService()
        self.resources = CollegeResourcePipeline(self.store)

    # ------------------------------------------------------------------
    # Learner profile / context
    # ------------------------------------------------------------------

    async def get_learner_profile(self, tool_context: ToolContext) -> Dict[str, Any]:
        """Return the authenticated learner's profile (name, branch, semester)."""
        uid = _require_uid(tool_context)
        profile = await self.store.get_college_user_profile(uid)
        if not profile:
            return {"status": "PROFILE_NOT_FOUND"}
        return {"status": "ok", "profile": _dump(profile)}

    async def get_academic_context(self, tool_context: ToolContext) -> Dict[str, Any]:
        """Return the learner's academic context (university, semester, subjects)."""
        uid = _require_uid(tool_context)
        ctx = await self.academic.get_learner_academic_context(uid)
        if not ctx:
            return {"status": "NEEDS_CONTEXT",
                    "message": "No academic context set. Ask the learner to complete onboarding."}
        return {"status": "ok", "context": _dump(ctx)}

    async def get_current_subjects(self, tool_context: ToolContext) -> Dict[str, Any]:
        """List the subject ids linked to the learner's academic context."""
        uid = _require_uid(tool_context)
        raw = await self.store.get_college_academic_context(uid)
        if not raw:
            return {"status": "NEEDS_CONTEXT", "subjects": []}
        ids = await self.store.get_context_subject_ids(raw.get("context_id"))
        return {"status": "ok", "subjects": ids}

    async def get_active_goal(self, tool_context: ToolContext) -> Dict[str, Any]:
        """Return the learner's active study goal, if any."""
        uid = _require_uid(tool_context)
        goal = await self.store.get_college_goal(uid)
        if not goal:
            return {"status": "GOAL_NOT_FOUND", "goal": None}
        return {"status": "ok", "goal": _dump(goal)}

    # ------------------------------------------------------------------
    # University research (TRD §7)
    # ------------------------------------------------------------------

    async def search_university_sources(
        self, tool_context: ToolContext, query: str
    ) -> Dict[str, Any]:
        """Search canonical verified universities by name fragment."""
        _require_uid(tool_context)
        universities = await self.academic.list_universities(query or "")
        if not universities:
            return {"status": "UNIVERSITY_NOT_FOUND", "universities": []}
        return {"status": "ok",
                "universities": [_dump(u) for u in universities]}

    async def get_verified_curriculum(
        self, tool_context: ToolContext, university_id: str,
        branch: str, semester: int,
    ) -> Dict[str, Any]:
        """Return the verified curriculum for university + branch + semester."""
        _require_uid(tool_context)
        try:
            branch_enum = EngineeringBranch[branch.upper()]
        except KeyError:
            return {"status": "INVALID_BRANCH",
                    "message": f"Unknown branch '{branch}'."}
        curr = await self.academic.resolve_curriculum(
            university_id, branch_enum, int(semester))
        if not curr:
            return {"status": "CURRICULUM_NOT_FOUND",
                    "message": "No verified curriculum covers this combination."}
        return {"status": "ok", "curriculum": _dump(curr)}

    # ------------------------------------------------------------------
    # Resources & PYQs
    # ------------------------------------------------------------------

    async def get_verified_resources(
        self, tool_context: ToolContext, subject_id: str,
        topic: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Return cached VERIFIED learning resources for a subject/topic.
        Never fabricates URLs: if nothing verified is cached, returns
        RESOURCE_ENRICHMENT_PENDING — call trigger_resource_research.
        """
        _require_uid(tool_context)
        return await self.resources.get_verified_resources(
            subject_id, topic=topic)

    async def trigger_resource_research(
        self, tool_context: ToolContext, subject_id: str, topic: str,
        time_budget_seconds: int = 30,
    ) -> Dict[str, Any]:
        """
        Run bounded live internet research for one topic (DuckDuckGo primary,
        Tavily backup, YouTube API for videos). Only reachable, verified URLs
        are persisted. Budgeted to keep the endpoint under the 60s Vercel cap.
        """
        uid = _require_uid(tool_context)
        ctx = await self.academic.get_learner_academic_context(uid)
        university_name = None
        if ctx:
            univ = await self.academic.get_university(ctx.university_id)
            university_name = univ.name if univ else None
        result = await self.resources.research_topic(
            subject_id=subject_id, topic=topic,
            university_name=university_name,
            time_budget_seconds=min(int(time_budget_seconds), 45))
        return result

    async def get_verified_pyqs(
        self, tool_context: ToolContext, subject_id: str,
        university_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Return verified previous-year questions for a subject.
        Returns PYQ_NOT_AVAILABLE explicitly when unverifiable — never invents.
        """
        uid = _require_uid(tool_context)
        if not university_id:
            ctx = await self.academic.get_learner_academic_context(uid)
            university_id = ctx.university_id if ctx else None
        return await self.pyq.get_pyqs(university_id, subject_id)

    async def evaluate_source(
        self, tool_context: ToolContext, url: str
    ) -> Dict[str, Any]:
        """
        Evaluate one URL: reachability check + deterministic tier assignment
        (TRD §8–9 signals). Rejected URLs are never promoted to plans.
        """
        _require_uid(tool_context)
        from backend.services.college_resource_pipeline import tier_for_domain
        import urllib.parse
        import httpx
        domain = urllib.parse.urlparse(url).netloc.lower().replace("www.", "")
        if not domain:
            return {"status": "REJECTED", "reason": "MALFORMED_URL"}
        reachable = False
        final_url = url
        try:
            async with httpx.AsyncClient(
                    timeout=12.0, follow_redirects=True,
                    headers={"User-Agent": "PathMind-CollegeMVP/1.0"}) as http:
                resp = await http.head(url)
                reachable = resp.status_code < 400
                if not reachable:
                    resp = await http.get(url)
                    reachable = resp.status_code < 400
                if reachable:
                    final_url = str(resp.url)
        except Exception:
            reachable = False
        if not reachable:
            return {"status": "UNVERIFIABLE", "url": url,
                    "reason": "URL_UNREACHABLE"}
        return {"status": "VERIFIED", "url": final_url,
                "domain": domain, "tier": tier_for_domain(domain)}

    # ------------------------------------------------------------------
    # Plans
    # ------------------------------------------------------------------

    async def create_study_plan(
        self, tool_context: ToolContext, goal_id: str,
        target_subject_code_or_id: Optional[str] = None,
        scope: str = "SEMESTER",
    ) -> Dict[str, Any]:
        """
        Generate an ordered multi-phase learning plan (deterministic phasing;
        activity ordering may use Gemini where configured). Unlock rules are
        mastery-gated and evaluated deterministically at completion time.
        """
        uid = _require_uid(tool_context)
        try:
            scope_enum = PlanScope[scope.upper()]
        except KeyError:
            scope_enum = PlanScope.SEMESTER
        try:
            plan = await self.learning.generate_learning_plan(
                uid=uid, goal_id=goal_id,
                target_subject_code_or_id=target_subject_code_or_id,
                scope=scope_enum)
        except ValueError as ve:
            code = str(ve).split(":")[0]
            return {"status": code, "message": str(ve)}
        log_event("college.adk.plan_created", user_id=uid,
                  plan_id=plan.plan_id, outcome="ok")
        return {"status": "ok", "plan": _dump(plan)}

    async def update_progress(
        self, tool_context: ToolContext, activity_id: str,
        evidence_note: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Mark a learning activity complete. Phase unlocks are evaluated by
        deterministic mastery rules — completion alone never unlocks the next
        phase unless its unlock rule is satisfied.
        """
        uid = _require_uid(tool_context)
        evidence = {"note": evidence_note} if evidence_note else None
        try:
            plan = await self.learning.complete_activity(
                uid=uid, activity_id=activity_id,
                completion_evidence=evidence)
        except ValueError as ve:
            return {"status": "ACTIVITY_NOT_FOUND", "message": str(ve)}
        return {"status": "ok", "plan_id": plan.plan_id}

    # ------------------------------------------------------------------
    # Assessments (TRD §15–16)
    # ------------------------------------------------------------------

    async def get_topic_mastery_state(
        self, tool_context: ToolContext, subject_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Read the learner model: per-(subject, topic) mastery records."""
        uid = _require_uid(tool_context)
        records = await self.store.get_topic_masteries(uid, subject_id)
        return {"status": "ok",
                "masteries": [_dump(r) for r in records]}

    async def create_assessment(
        self, tool_context: ToolContext, subject_id: str,
        topic_title: str, plan_id: Optional[str] = None,
        phase_id: Optional[str] = None, topics: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Create a checkpoint assessment. When `topics` is omitted, topics are
        selected adaptively: weakest mastered topics for the subject come
        first (read from the mastery store — never invented).
        """
        uid = _require_uid(tool_context)
        topic_list = None
        if topics:
            try:
                topic_list = json.loads(topics)
            except Exception:
                topic_list = [t.strip() for t in topics.split(",") if t.strip()]
        if not topic_list:
            # Adaptive selection: weakest topics first.
            records = await self.store.get_topic_masteries(uid, subject_id)
            def _score(r):
                s = r.mastery_score if hasattr(r, "mastery_score") else r.get("mastery_score")
                return s if s is not None else -1.0
            ranked = sorted(records, key=_score)
            topic_list = [
                (r.topic if hasattr(r, "topic") else r.get("topic"))
                for r in ranked[:5]
            ] or [topic_title]
        try:
            assessment = await self.assessment.generate_phase_assessment(
                uid=uid, plan_id=plan_id or "", phase_id=phase_id or "",
                subject_id=subject_id, topic_title=topic_title,
                topics=topic_list)
        except ValueError as ve:
            return {"status": "ASSESSMENT_UNAVAILABLE", "message": str(ve)}
        return {"status": "ok", "assessment": _dump(assessment),
                "adaptive_topics": topic_list}

    async def evaluate_assessment(
        self, tool_context: ToolContext, assessment_id: str,
        answers_json: str,
    ) -> Dict[str, Any]:
        """
        Grade a submitted assessment. Objective answers are scored
        deterministically; open answers use the exact-match rule or LLM
        grading with structured confidence — never length heuristics.
        """
        uid = _require_uid(tool_context)
        try:
            answers = json.loads(answers_json)
            if not isinstance(answers, dict):
                raise ValueError("answers_json must be an object")
        except ValueError as ve:
            return {"status": "INVALID_ANSWERS", "message": str(ve)}
        try:
            submission = CollegeAssessmentSubmission(
                assessment_id=assessment_id, answers=answers)
            result = await self.assessment.evaluate_submission(
                uid=uid, submission=submission)
        except ValueError as ve:
            return {"status": "ASSESSMENT_NOT_FOUND", "message": str(ve)}
        return {"status": "ok", "result": _dump(result)}

    # ------------------------------------------------------------------
    # Memory (TRD §18–19)
    # ------------------------------------------------------------------

    async def retrieve_short_term_memory(
        self, tool_context: ToolContext,
    ) -> Dict[str, Any]:
        """Read this learner's recent short-term session context."""
        uid = _require_uid(tool_context)
        mems = await self.memory.get_short_term_memories(uid)
        return {"status": "ok",
                "memories": [_dump(m) for m in mems[-10:]]}

    async def retrieve_long_term_memory(
        self, tool_context: ToolContext, topic: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Read persistent long-term memories, optionally filtered by topic."""
        uid = _require_uid(tool_context)
        mems = await self.memory.get_long_term_memories(uid)
        items = [_dump(m) for m in mems]
        if topic:
            needle = topic.lower()
            items = [m for m in items
                     if needle in (m.get("content") or "").lower()
                     or needle in (m.get("title") or "").lower()
                     or needle in (m.get("related_topic") or "").lower()]
        return {"status": "ok", "memories": items}

    async def record_memory(
        self, tool_context: ToolContext, content: str, title: str,
        memory_type: str = "EPISODIC", related_subject: Optional[str] = None,
        related_topic: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Persist a durable learner memory (TRD §19 write policy applies: only
        stable, useful, future-relevant observations — not throwaway questions).
        """
        uid = _require_uid(tool_context)
        if not content or not content.strip():
            return {"status": "MEMORY_REJECTED",
                    "message": "Empty content is not a memory."}
        mem = await self.memory.record_long_term_memory(
            uid=uid, content=content.strip(), title=title.strip(),
            memory_type=memory_type, related_subject=related_subject,
            related_topic=related_topic)
        log_event("college.adk.memory_recorded", user_id=uid,
                  memory_id=mem.memory_id, outcome="ok")
        return {"status": "ok", "memory": _dump(mem)}

    async def record_learning_signal(
        self, tool_context: ToolContext, signal_type: str,
        description: str, recommended_intervention: str,
        subject_id: Optional[str] = None, topic_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Record an actionable pedagogical insight for future adaptation."""
        uid = _require_uid(tool_context)
        signal = await self.memory.record_learning_signal(
            uid=uid, signal_type=signal_type, description=description,
            recommended_intervention=recommended_intervention,
            subject_id=subject_id, topic_id=topic_id)
        return {"status": "ok", "signal": _dump(signal)}

    # ------------------------------------------------------------------
    # Accountability (TRD §20–21)
    # ------------------------------------------------------------------

    async def create_accountability_commitment(
        self, tool_context: ToolContext, title: str, due_at: str,
        estimated_minutes: int = 60,
    ) -> Dict[str, Any]:
        """Create a study commitment with strict status tracking."""
        uid = _require_uid(tool_context)
        try:
            commitment = await self.accountability.create_commitment(
                uid=uid, title=title, due_at=due_at,
                estimated_minutes=int(estimated_minutes))
        except Exception as ve:
            return {"status": "COMMITMENT_REJECTED", "message": str(ve)}
        return {"status": "ok", "commitment": _dump(commitment)}

    async def get_accountability_state(
        self, tool_context: ToolContext,
    ) -> Dict[str, Any]:
        """
        Today's accountability state: exam countdown (deterministic date math),
        real streak (zero when no completions — never fabricated), commitments.
        """
        uid = _require_uid(tool_context)
        schedule = await self.accountability.get_today_schedule(uid)
        data = _dump(schedule)
        data["status"] = "ok"
        return data

    # ------------------------------------------------------------------
    # Wiring
    # ------------------------------------------------------------------

    def as_function_tools(self, names: List[str]) -> List[FunctionTool]:
        """Build ADK FunctionTools for the named tool methods."""
        if not _ADK_TOOLS_OK or FunctionTool is None:
            raise RuntimeError("google-adk is not importable in this environment")
        tools: List[FunctionTool] = []
        for name in names:
            method = getattr(self, name, None)
            if method is None:
                raise ValueError(f"Unknown college tool: {name}")
            tools.append(FunctionTool(method))
        return tools

    def all_tool_names(self) -> List[str]:
        return [
            "get_learner_profile", "get_academic_context", "get_current_subjects",
            "get_active_goal", "search_university_sources", "get_verified_curriculum",
            "get_verified_resources", "trigger_resource_research", "get_verified_pyqs",
            "evaluate_source", "create_study_plan", "update_progress",
            "get_topic_mastery_state", "create_assessment", "evaluate_assessment",
            "retrieve_short_term_memory", "retrieve_long_term_memory",
            "record_memory", "record_learning_signal",
            "create_accountability_commitment", "get_accountability_state",
        ]
