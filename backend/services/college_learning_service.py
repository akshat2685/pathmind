"""
College Learning Plan & Phase Progression Service for PATHMIND College Engineering MVP.

Generates ordered, scope-aware learning plans (WHOLE_PROGRAM / SEMESTER /
SUBJECT_PART) covering the full syllabus — never a capped subset.

Phase progression is mastery-gated (schema §16): completing activities marks a
phase COMPLETED, but the next phase unlocks ONLY when the phase's unlock_rule
(required assessment score per topic) is satisfied by evidence in the
per-topic mastery store. `complete_activity` never unlocks on its own.
"""

from typing import List, Dict, Any, Optional, Tuple
import asyncio
import json
import re
import time
import uuid

from backend.core.college_schemas import (
    CollegeLearningPlan,
    CollegePlanPhase,
    CollegeActivity,
    CollegeGoal,
    ActivityType,
    EngineeringBranch,
    AcademicContext,
    CollegeAssessment,
    LearningPlanSubject,
    PlanScope,
    ResourceRecord,
    PYQQuestionRecord,
)
from backend.core.college_rules import evaluate_unlock_rule
from backend.core.college_logging import log_event, timed_stage
from backend.core.gemini import generate_fast
from backend.providers.curriculum_registry import (
    get_curriculum,
    get_resources_for_subject,
    get_pyqs_for_subject,
)
from backend.services.store import FirestoreStore

#: Fraction of the phase assessment score required to unlock the next phase.
UNLOCK_REQUIRED_SCORE = 75.0

_PHASE_ID_RE = re.compile(r"^phase_(.*)_s(\d+)_u(\d+)$")


def _subject_id_from_phase_id(phase_id: str, plan_id: str) -> Optional[str]:
    """phase_id format: phase_{plan_id}_{subject_id}_s{semester}_u{unit}."""
    m = _PHASE_ID_RE.match(phase_id or "")
    if not m:
        return None
    prefix = m.group(1)
    expected = f"{plan_id}_"
    if not prefix.startswith(expected):
        return None
    return prefix[len(expected):] or None


#: Words that carry no topical signal when matching a resource to a phase.
_MATCH_STOPWORDS = {
    "course", "unit", "lecture", "video", "notes", "introduction",
    "overview", "fundamentals", "basic", "basics", "with", "from",
    "this", "that", "into", "your",
}


def _resource_match_score(resource: ResourceRecord, phase_title: str) -> int:
    """Token overlap between a cached resource and a phase title.

    Resources researched for a unit carry the unit/topic in topic_ids, so a
    topic-matched resource beats a generic subject-level one for that phase.
    """
    def _tokens(text: str) -> set:
        return {
            t for t in re.split(r"[^a-z0-9]+", (text or "").lower())
            if len(t) >= 4 and t not in _MATCH_STOPWORDS
        }

    title_tokens = _tokens(phase_title)
    if not title_tokens:
        return 0
    score = 0
    for topic in (resource.topic_ids or []):
        score += 2 * len(title_tokens & _tokens(topic))
    score += len(title_tokens & _tokens(resource.title))
    return score


def _resource_engagement(resource: ResourceRecord) -> float:
    """Real engagement score persisted by the research pipeline.

    0.0 when the resource carries no statistics (hand-seeded rows and
    everything cached before engagement ranking) — a 0 tie falls back
    to the deterministic resource_id order, so historical behavior is
    preserved exactly until real statistics exist.
    """
    signals = getattr(resource, "quality_signals", None) or {}
    if not isinstance(signals, dict):
        return 0.0
    try:
        return float(signals.get("engagement_score") or 0.0)
    except (TypeError, ValueError):
        return 0.0


def _resource_quality(resource: ResourceRecord) -> float:
    """The quality signal that ranks a resource of this kind (AJ's rule).

    Videos: real engagement (views/likes/comments — the most-watched,
    best-liked lecture on the topic wins). Documents, notes, and free
    online courses found via Tavily: the search engine's SEO/AEO
    relevance score persisted under quality_signals["search_score"]
    (0..1), with engagement as a fallback for rows that carry no score.
    Trust is enforced separately by verification + reachability — it
    does not outrank quality at pick time.
    """
    if (resource.resource_type or "") == "VIDEO":
        return _resource_engagement(resource)
    signals = getattr(resource, "quality_signals", None) or {}
    if isinstance(signals, dict):
        for key in ("search_score", "tavily_score"):
            value = signals.get(key)
            if value is not None:
                try:
                    return float(value)
                except (TypeError, ValueError):
                    continue
    return _resource_engagement(resource)


def _resource_pick_key(resource: ResourceRecord, match_title: str):
    """Attachment order: an on-topic resource always beats an off-topic
    one (gate), then kind-native quality decides, then match depth,
    then the deterministic resource_id."""
    match = _resource_match_score(resource, match_title)
    return (1 if match > 0 else 0, _resource_quality(resource),
            match, resource.resource_id)


#: One-shot ADK generation seam (college_adk_runtime.run_agent_generation).
#: Bound LAZILY into this module's namespace on first use: a top-level
#: import of the runtime would cycle (college_adk_tools imports this
#: service, and the runtime imports the tools). Tests patch this module
#: attribute to stub the seam AND record that the ADK path was really
#: invoked — a green suite that never exercised the seam does not count
#: as proof the agent authored anything.
run_agent_generation = None


def _agent_generation():
    """Resolve the ADK one-shot generation callable (lazy, patchable)."""
    global run_agent_generation
    if run_agent_generation is None:
        from backend.services.college_adk_runtime import (
            run_agent_generation as _impl)
        run_agent_generation = _impl
    return run_agent_generation


def _learn_steps_for(activity_type: str, resource: Optional[ResourceRecord],
                     topics: Optional[List[str]] = None) -> List[str]:
    """Deterministic 'how to learn this' method steps for one activity.

    The plan must teach the method, not just name the material: watch with
    active recall, read with closed-book summaries, practice before checking
    solutions, PYQs under timed exam conditions with an error log.
    """
    topic_hint = (topics[0] if topics else "this topic")
    if activity_type == "WATCH":
        if resource is not None:
            return [
                f"Open the video: \"{resource.title}\" ({resource.provider}).",
                "Watch in small parts. Pause after every new definition "
                "or diagram, and write it down in your own simple words.",
                "When the video ends, close it and write the 3 most "
                "important points from memory. Do not look back yet.",
                "Now check what you missed. Those are your weak points — "
                "the next steps in this phase will fix exactly those.",
            ]
        return [
            f"Find one good video on {topic_hint} — your class recording, "
            "an NPTEL lecture, or a channel you already trust.",
            "Watch in small parts. Pause after every new definition or "
            "diagram, and write it down in your own simple words.",
            "When it ends, close it and write the 3 most important points "
            "from memory. Note what you missed — the next steps fix that.",
        ]
    if activity_type == "READ":
        if resource is not None:
            return [
                f"Open the material: \"{resource.title}\" "
                f"({resource.provider}).",
                "First look at all the headings and diagrams. This gives "
                "you a map of what is coming.",
                "Read one section at a time. After each section, close "
                "the material and write a short summary (3–5 lines) from "
                "memory.",
                "Underline every word you cannot explain in one simple "
                "sentence. Clear those before you take the checkpoint.",
            ]
        return [
            f"Use your textbook or class notes for {topic_hint}.",
            "First look at all the headings, then read one section at a "
            "time. After each section, write a short summary (3–5 lines) "
            "from memory, without looking.",
            "Mark every word you cannot explain in one simple sentence. "
            "Clear those before you move on.",
        ]
    if activity_type == "SOLVE_PYQ":
        return [
            "Set a timer and solve like a real exam — no notes, no "
            "phone, no pausing.",
            "When the time is over, check your answers with the marking "
            "scheme or your notes. Give yourself honest marks.",
            "For every mark you lost, write one line about what went "
            "wrong: did not know the concept, wrong formula, silly "
            "mistake, or ran out of time.",
            "Tomorrow, solve the questions you got wrong again — from a "
            "blank page, without seeing the answers first.",
        ]
    # PRACTICE (and any other type): attempt-first problem solving.
    return [
        "Try every problem yourself first, book closed. Struggling for a "
        "few minutes before you see the answer is how you actually learn.",
        "If you get stuck or go wrong, write down exactly where your "
        "thinking went wrong — not just the correct answer.",
        "Then solve the same problem again from a blank page. Reading an "
        "answer is not the same as solving it yourself.",
        "At the end, say the main idea of "
        f"{topic_hint} in 2–3 simple sentences, without looking at your "
        "notes.",
    ]


class CollegeLearningService:
    def __init__(self, store: Optional[FirestoreStore] = None):
        self.store = store or FirestoreStore()

    # ------------------------------------------------------------------
    # Plan generation
    # ------------------------------------------------------------------

    async def generate_learning_plan(
        self,
        uid: str,
        goal_id: Optional[str] = None,
        target_subject_code_or_id: Optional[str] = None,
        scope: PlanScope = PlanScope.SEMESTER,
    ) -> CollegeLearningPlan:
        """
        Synthesizes an ordered, multi-phase learning plan across the whole
        requested scope. Every subject unit becomes a phase (full syllabus).
        """
        with timed_stage("college.plan.generated", user_id=uid, scope=scope.value):
            gen_started = time.monotonic()
            raw_ctx = await self.store.get_college_academic_context(uid)
            if not raw_ctx:
                raise ValueError(
                    "ACADEMIC_CONTEXT_REQUIRED: Please complete academic onboarding first.")
            ctx = AcademicContext(**raw_ctx)

            branch = await self._resolve_branch(uid)
            scoped_subjects = await self._resolve_scoped_subjects(
                uid, ctx, branch, scope, target_subject_code_or_id)

            effective_goal_id = await self._ensure_goal(uid, goal_id, scope)

            plan_id = f"plan_{uid}_{scope.value.lower()}_{uuid.uuid4().hex[:6]}"

            phases: List[CollegePlanPhase] = []
            plan_subjects: List[LearningPlanSubject] = []
            seen_subjects = set()
            phase_order = 1

            # Collect phase specs first (order preserved), then build
            # activities concurrently. Phase/activity assembly is
            # STATIC-FIRST: no LLM call happens while phases are being
            # assembled, for any scope — a single Gemini call costs
            # ~30s+ (and the AI endpoint is intermittently unreachable
            # from the serverless runtime), so per-phase LLM enrichment
            # put every plan one slow call away from the ~60s serverless
            # cap. Every phase ships with the deterministic sequence
            # (real verified resources + PYQs). Round 7 adds ONE bounded
            # ADK plan-agent pass AFTER assembly (_personalize_plan)
            # that rewrites objectives + technique guidance from the
            # learner's diagnostic evidence and aspiration — fail-open:
            # any failure ships the static plan untouched, labeled
            # authored_by="static_fallback". Any single phase can also
            # be upgraded on demand via enrich_phase_activities
            # ("Personalize with AI").
            phase_specs: List[Tuple[int, Any, Any, int]] = []
            for semester, sub in scoped_subjects:
                if sub.subject_id not in seen_subjects:
                    seen_subjects.add(sub.subject_id)
                    plan_subjects.append(LearningPlanSubject(
                        plan_id=plan_id,
                        subject_id=sub.subject_id,
                    ))
                # Full syllabus: every unit becomes a phase (no [:2] cap).
                for unit in sub.units:
                    phase_specs.append((semester, sub, unit, phase_order))
                    phase_order += 1

            if not phase_specs:
                raise ValueError(
                    "CURRICULUM_NOT_FOUND: no verified curriculum units cover "
                    "the requested scope.")

            _concurrency = asyncio.Semaphore(8)

            # One batch fetch for all subjects (3 queries in a thread)
            # instead of 2 blocking reads per phase (~174 for whole-program).
            subject_ids = list({sub.subject_id
                                for _, sub, _, _ in phase_specs})
            prefetched = await self._prefetch_subject_inputs(
                ctx.university_id, subject_ids)

            async def _build_one(
                spec: Tuple[int, Any, Any, int],
            ) -> Tuple[List[CollegeActivity], bool]:
                semester, sub, unit, order = spec
                async with _concurrency:
                    # model=None: deterministic static sequence, no LLM
                    # call at generation time (see static-first note above).
                    return await self._build_phase_activities(
                        uid, plan_id, ctx.university_id, semester, sub, unit,
                        order, ctx.available_hours_per_week,
                        None,
                        prefetched=prefetched)

            built_per_phase = await asyncio.gather(
                *(_build_one(spec) for spec in phase_specs))

            # Diagnostic evidence -> planner. Read the learner's per-topic
            # mastery store once and let it shape each phase: Weak topics
            # get guided intensive learning, Partial topics targeted
            # explanation + practice, Mastered topics only light revision
            # with spaced retrieval, and topics with no evidence stay
            # Unknown (planned normally; the checkpoint gathers evidence).
            # This reuses the existing planner — no second plan system.
            mastery_by_topic: Dict[str, str] = {}
            try:
                for mrow in (await self.store.get_topic_masteries(uid)
                             or []):
                    if mrow.get("topic"):
                        mastery_by_topic[mrow["topic"]] = mrow.get(
                            "outcome") or ""
            except Exception as exc:
                log_event("college.plan.mastery_read_failed", user_id=uid,
                          outcome="error", error_code=type(exc).__name__)

            def _phase_guidance(unit) -> Tuple[str, str, List[Dict[str, str]]]:
                evidence = [
                    {"topic": t, "outcome": mastery_by_topic[t]}
                    for t in (unit.topics or []) if t in mastery_by_topic
                ]
                outcomes = [e["outcome"] for e in evidence]
                if not outcomes:
                    return "unknown", "", evidence
                if "REINFORCEMENT_REQUIRED" in outcomes:
                    return "weak", "Start here — learn the basics step by step: ", evidence
                if "PARTIALLY_MASTERED" in outcomes:
                    return ("partial",
                            "Focus on your weak topics first: ", evidence)
                if all(o == "MASTERED" for o in outcomes):
                    return ("mastered",
                            "Quick revision — you already know this well: ",
                            evidence)
                return "partial", "Focus on your weak topics first: ", evidence

            for (semester, sub, unit, order), (activities, used_llm) in zip(
                    phase_specs, built_per_phase):
                phase_id = f"phase_{plan_id}_{sub.subject_id}_s{semester}_u{unit.unit}"
                band, objective_prefix, guidance_evidence = _phase_guidance(unit)
                phases.append(CollegePlanPhase(
                    phase_id=phase_id,
                    user_id=uid,
                    plan_id=plan_id,
                    order=order,
                    title=f"{sub.code}: {unit.title}",
                    objective=(objective_prefix +
                               f"Learn {unit.title} ({sub.name}, Semester "
                               f"{semester}, Unit {unit.unit}). By the end "
                               f"you should be able to explain the main "
                               f"ideas in your own simple words and solve "
                               f"exam questions from this unit."),
                    ai_enriched=used_llm,
                    status="AVAILABLE" if order == 1 else "LOCKED",
                    # Schema §16 unlock rule: demonstrated mastery required.
                    # diagnostic_guidance records how diagnostic evidence
                    # shaped this phase (read by the UI/reporting only;
                    # unlock evaluation ignores unknown keys).
                    unlock_rule={
                        "type": "ASSESSMENT_MASTERY",
                        "required_assessment_score": UNLOCK_REQUIRED_SCORE,
                        "required_topics": list(unit.topics),
                        "diagnostic_guidance": {
                            "band": band,
                            "topics": guidance_evidence,
                        },
                    },
                    activities=activities,
                    assessment_id=f"asmt_{phase_id}",
                ))

            plan = CollegeLearningPlan(
                plan_id=plan_id,
                user_id=uid,
                goal_id=effective_goal_id,
                plan_type=("PROGRAM_PREPARATION" if scope == PlanScope.WHOLE_PROGRAM
                           else "TOPIC_MASTERY" if scope == PlanScope.SUBJECT_PART
                           else "SEMESTER_PREPARATION"),
                scope=scope,
                phases=phases,
                subjects=plan_subjects,
                # Persist as DRAFT first: if the function is killed mid-save
                # (serverless timeout), the previous ACTIVE plan stays the
                # newest readable one. Flip to ACTIVE only after the full
                # hierarchy is persisted.
                status="DRAFT",
            )
            # Round 7: one bounded ADK plan-agent personalization pass
            # BEFORE persist — objectives/techniques rewritten from the
            # diagnostic evidence + aspiration. Fail-open by design:
            # _personalize_plan never raises, and plan.authored_by
            # records which path actually happened.
            await self._personalize_plan(uid, plan, ctx, scope,
                                         gen_started)
            await self.store.save_college_learning_plan(
                uid, plan.model_dump(mode="json"))
            await self.store.activate_college_learning_plan(uid, plan_id)
            plan.status = "ACTIVE"
            log_event("college.plan.saved", user_id=uid, plan_id=plan_id,
                      phase_count=len(phases),
                      subject_count=len(plan_subjects), outcome="ok")
            # Round 6: path creation uses the resource pipeline. Warm
            # the verified cache for the first phase when its subject
            # has no cached video/notes yet, so the learner opens the
            # plan to real resources instead of an empty first phase.
            # Bounded and fail-open — the plan is already ACTIVE and is
            # returned untouched if research finds or costs anything
            # unexpected (see _research_first_phase_resources).
            await self._research_first_phase_resources(
                uid, plan, prefetched, gen_started)
            return plan

    async def _personalize_plan(
        self, uid: str, plan: CollegeLearningPlan, ctx: AcademicContext,
        scope: PlanScope, gen_started: float,
    ) -> None:
        """One bounded ADK plan-agent pass over the assembled static plan.

        The agent sees a compact brief (aspiration, scope, and per phase:
        id/title/subject/topics/diagnostic band) and may rewrite each
        phase's objective, focus topics, and learn technique. It may not
        invent resources — verified material attaches deterministically
        from the cache — and unknown phase_ids are ignored. Runs only
        while the generation budget allows (skipped past 25s so the
        response stays inside the serverless window). NEVER raises: any
        failure leaves the static plan untouched. plan.authored_by is
        set on every path and logged as college.plan.authored — mode
        says "adk" ONLY when the seam actually returned text that
        changed >=1 phase.
        """
        try:
            if time.monotonic() - gen_started >= 25.0:
                plan.authored_by = "static_fallback"
                log_event("college.plan.authored", user_id=uid,
                          plan_id=plan.plan_id, mode="static_fallback",
                          outcome="skipped",
                          error_code="GENERATION_BUDGET")
                return
            aspiration = ""
            if ctx is not None:
                exam_window = getattr(ctx, "exam_window", None) or {}
                if isinstance(exam_window, dict):
                    aspiration = str(
                        exam_window.get("aspiration") or "")[:300]
            brief_phases = []
            for phase in plan.phases:
                rule = phase.unlock_rule or {}
                guidance = rule.get("diagnostic_guidance") or {}
                brief_phases.append({
                    "phase_id": phase.phase_id,
                    "title": phase.title,
                    "subject_id": _subject_id_from_phase_id(
                        phase.phase_id, plan.plan_id),
                    "topics": list(rule.get("required_topics") or [])[:8],
                    "band": guidance.get("band", "unknown"),
                })
            payload = {"aspiration": aspiration, "scope": scope.value,
                       "phases": brief_phases}
            prompt = (
                "You are personalizing a study plan for one learner. "
                "Below is a JSON brief: the learner's aspiration, the "
                "plan scope, and each phase with its diagnostic band "
                "(weak = evidence of gaps, partial = some evidence, "
                "mastered = already strong, unknown = no evidence yet).\n"
                "Rules:\n"
                "- Weak phases come first in your wording: start from "
                "the basics, step by step. Mastered phases get quick "
                "revision wording (spaced recall), never full re-teaching.\n"
                "- Match the work to the aspiration when it is stated.\n"
                "- focus_topics: the topics in that phase to hit first "
                "(weakest first). technique: one concrete how-to-learn "
                "method for this phase (e.g. active recall with worked "
                "examples, timed PYQ drills, teach-back summaries).\n"
                "- Keep each objective to at most 2 short sentences in "
                "plain simple language a student understands.\n"
                "- NEVER invent resources, URLs, book titles, or "
                "channels — verified material is attached separately by "
                "the system.\n"
                "- Include every phase_id from the brief, unchanged.\n"
                "Return ONLY JSON of this shape: {\"phases\": "
                "[{\"phase_id\": \"...\", \"objective\": \"...\", "
                "\"focus_topics\": [\"...\"], \"technique\": \"...\"}]}\n\n"
                f"BRIEF:\n{json.dumps(payload)}"
            )
            # Tighter seam bound than the runtime default: this call
            # starts only inside the 25s generation budget and the
            # request still owes a persist afterwards — 25s here keeps
            # the worst case inside the serverless window.
            raw = await _agent_generation()("plan", prompt, timeout=25.0)
            applied = self._apply_plan_personalization(plan, raw)
            if applied:
                plan.authored_by = "adk:plan_agent"
                log_event("college.plan.authored", user_id=uid,
                          plan_id=plan.plan_id, mode="adk",
                          phases_personalized=applied, outcome="ok")
            else:
                plan.authored_by = "static_fallback"
                log_event("college.plan.authored", user_id=uid,
                          plan_id=plan.plan_id, mode="static_fallback",
                          outcome="degraded",
                          error_code="NO_APPLICABLE_PHASES")
        except Exception as exc:
            plan.authored_by = "static_fallback"
            log_event("college.plan.authored", user_id=uid,
                      plan_id=plan.plan_id, mode="static_fallback",
                      outcome="error", error_code=type(exc).__name__)

    @staticmethod
    def _apply_plan_personalization(plan: CollegeLearningPlan,
                                    raw: Optional[str]) -> int:
        """Apply the plan agent's JSON to the plan, defensively.

        Returns how many phases actually changed. Unknown phase_ids are
        ignored; every string is capped; the technique and focus topics
        ride inside unlock_rule.diagnostic_guidance (existing schema —
        no migration). Malformed input changes nothing.
        """
        text = (raw or "").strip()
        if text.startswith("```"):
            text = text.strip("`")
            if text.lower().startswith("json"):
                text = text[4:]
        try:
            data = json.loads(text.strip())
        except Exception:
            return 0
        if not isinstance(data, dict):
            return 0
        items = data.get("phases")
        if not isinstance(items, list):
            return 0
        by_id = {p.phase_id: p for p in plan.phases}
        applied = 0
        for item in items:
            if not isinstance(item, dict):
                continue
            phase = by_id.get(str(item.get("phase_id") or ""))
            if phase is None:
                continue
            changed = False
            objective = str(item.get("objective") or "").strip()
            if objective:
                phase.objective = objective[:800]
                changed = True
            rule = dict(phase.unlock_rule or {})
            guidance = dict(rule.get("diagnostic_guidance") or {})
            technique = str(item.get("technique") or "").strip()
            if technique:
                guidance["technique"] = technique[:300]
                changed = True
            focus = item.get("focus_topics")
            if isinstance(focus, list):
                topics = [str(t).strip()[:120] for t in focus
                          if str(t).strip()][:8]
                if topics:
                    guidance["focus_topics"] = topics
                    changed = True
            if changed:
                if guidance:
                    rule["diagnostic_guidance"] = guidance
                    phase.unlock_rule = rule
                applied += 1
        return applied

    async def _research_first_phase_resources(
        self, uid: str, plan: CollegeLearningPlan,
        prefetched, gen_started: float,
    ) -> None:
        """One bounded live-research pass for the plan's first phase.

        Runs only when the first phase's subject lacks a cached VIDEO or
        a cached NOTES/DOCUMENT. The VERIFIED cache is shared across
        learners, so each topic is researched once globally, not once
        per student; later phases keep filling through the dashboard's
        on-demand research cascade. Never raises: the plan is already
        saved ACTIVE, and research is an enhancement, not a dependency.
        """
        try:
            if not plan.phases:
                return
            elapsed = time.monotonic() - gen_started
            # Stay comfortably inside the ~60s serverless cap: skip
            # research when generation itself already ran long, and
            # never grant research more than 15s.
            if elapsed > 30.0:
                log_event("college.plan.research_skipped", user_id=uid,
                          plan_id=plan.plan_id, outcome="skipped",
                          error_code="GENERATION_BUDGET")
                return
            first = plan.phases[0]
            subject_id = _subject_id_from_phase_id(
                first.phase_id, plan.plan_id)
            if not subject_id:
                return
            cached = (prefetched[0].get(subject_id) or []) if prefetched else []
            has_video = any(r.resource_type == "VIDEO" for r in cached)
            has_doc = any(r.resource_type in ("NOTES", "DOCUMENT")
                          for r in cached)
            if has_video and has_doc:
                return
            topic = (first.title.split(": ", 1)[1]
                     if ": " in first.title else first.title)
            budget = min(15.0, 40.0 - elapsed)
            from backend.services.college_resource_pipeline import (
                CollegeResourcePipeline,
            )
            result = await CollegeResourcePipeline().research_topic(
                subject_id=subject_id, topic=topic,
                time_budget_seconds=budget)
            log_event("college.plan.first_phase_researched", user_id=uid,
                      plan_id=plan.plan_id, subject_id=subject_id,
                      topic=topic,
                      added=(result or {}).get("resources_added", 0),
                      outcome="ok")
        except Exception as exc:  # fail-open: the plan already shipped
            log_event("college.plan.research_failed", user_id=uid,
                      plan_id=plan.plan_id, outcome="error",
                      error_code=type(exc).__name__)

    async def enrich_phase_activities(
        self, uid: str, plan_id: str, phase_id: str,
    ) -> CollegePlanPhase:
        """
        (Re)generates one phase's activities with the LLM, persists them and
        marks the phase ai_enriched. This is how tail phases of large
        (whole-program) plans get AI-personalized activities on demand, one
        phase per serverless-friendly call. Raises ValueError with an honest
        code when it cannot proceed; never silently keeps stale activities.
        """
        raw_plan = await self.store.get_college_learning_plan(uid)
        if not raw_plan or raw_plan.get("plan_id") != plan_id:
            raise ValueError("PLAN_NOT_FOUND")
        phases = raw_plan.get("phases") or []
        target = next(
            (ph for ph in phases if ph.get("phase_id") == phase_id), None)
        if not target:
            raise ValueError("PHASE_NOT_FOUND")

        # phase_id format: phase_{plan_id}_{subject_id}_s{semester}_u{unit}
        m = re.match(r"^phase_(.*)_s(\d+)_u(\d+)$", phase_id)
        if not m:
            raise ValueError("PHASE_ID_UNPARSEABLE")
        prefix, semester_s, unit_s = m.groups()
        expected_prefix = f"{plan_id}_"  # regex already consumed the leading "phase_"
        if not prefix.startswith(expected_prefix):
            raise ValueError("PHASE_PLAN_MISMATCH")
        subject_id = prefix[len(expected_prefix):]
        semester_hint, unit_no = int(semester_s), int(unit_s)

        raw_ctx = await self.store.get_college_academic_context(uid)
        if not raw_ctx:
            raise ValueError("ACADEMIC_CONTEXT_REQUIRED")
        ctx = (raw_ctx if isinstance(raw_ctx, AcademicContext)
               else AcademicContext(**raw_ctx))
        branch = await self._resolve_branch(uid)

        # Prefer the semester stored on the phase row: one curriculum fetch.
        # Fall back to scanning semesters only if that misses.
        try:
            semester = int(target.get("semester") or semester_hint)
        except (TypeError, ValueError):
            semester = semester_hint
        sub = None
        for sem_try in [semester] + [s for s in range(1, 9)
                                     if s != semester]:
            curr = await get_curriculum(ctx.university_id, branch, sem_try)
            if curr and curr.subjects:
                hit = next((s for s in curr.subjects
                            if s.subject_id == subject_id), None)
                if hit:
                    sub = hit
                    semester = sem_try
                    break
        if sub is None:
            raise ValueError("SUBJECT_NOT_FOUND")
        unit = next((u for u in sub.units if u.unit == unit_no), None)
        if unit is None:
            raise ValueError("UNIT_NOT_FOUND")

        # Resources first: if this subject has no cached verified VIDEO,
        # run the live research pipeline (YouTube Data API + DuckDuckGo/
        # Tavily web search, reachability-verified, cached as VERIFIED) so
        # the rebuilt activities link to real material. Research failure
        # never blocks personalization — building falls back to whatever
        # is already cached, and the dashboard's attach-on-read pass links
        # later research into existing plans.
        try:
            cached_resources = await get_resources_for_subject(sub.subject_id)
        except Exception:
            cached_resources = []
        if not any(r.resource_type == "VIDEO" for r in cached_resources):
            try:
                from backend.services.college_resource_pipeline import (
                    CollegeResourcePipeline,
                )
                await CollegeResourcePipeline().research_topic(
                    subject_id=sub.subject_id,
                    topic=unit.title,
                    subject_name=sub.name,
                    time_budget_seconds=20,
                )
            except Exception as exc:
                log_event("college.plan.phase_resource_research_failed",
                          user_id=uid, phase_id=phase_id, outcome="error",
                          error_code=type(exc).__name__)

        model = self._get_gemini_model()
        if model is None:
            raise ValueError(
                "AI_UNAVAILABLE: the AI service is not configured right now.")

        order = int(target.get("order") or 1)
        activities, used_llm = await self._build_phase_activities(
            uid, plan_id, ctx.university_id, semester, sub, unit,
            order, ctx.available_hours_per_week, model)
        if not used_llm:
            detail = getattr(self, "_last_activity_gen_error", "") or ""
            raise ValueError(
                "AI_UNAVAILABLE: the AI service did not return activities; "
                "your current activities are unchanged. Try again in a bit."
                + (f" Last error: {detail}" if detail else ""))

        phase = CollegePlanPhase(**target)
        phase.activities = activities
        phase.ai_enriched = True
        await self.store.save_college_phase(uid, phase.model_dump(mode="json"))
        log_event("college.plan.phase_enriched", user_id=uid, plan_id=plan_id,
                  phase_id=phase_id, activity_count=len(activities),
                  outcome="ok")
        return phase

    async def _resolve_branch(self, uid: str) -> EngineeringBranch:
        raw_profile = await self.store.get_college_user_profile(uid)
        supported_path = None
        if isinstance(raw_profile, dict):
            supported_path = raw_profile.get("supported_path")
        elif raw_profile is not None:
            supported_path = getattr(raw_profile, "supported_path", None)
        try:
            return EngineeringBranch(supported_path) if supported_path else EngineeringBranch.GENERAL_OTHER
        except ValueError:
            return EngineeringBranch.GENERAL_OTHER

    async def _resolve_scoped_subjects(
        self,
        uid: str,
        ctx: AcademicContext,
        branch: EngineeringBranch,
        scope: PlanScope,
        target_subject_code_or_id: Optional[str],
    ) -> List[Tuple[int, Any]]:
        """
        Returns [(semester, SubjectRecord)] across the whole requested scope.
        Never invents subjects; raises honest errors when nothing verified
        covers the scope.
        """
        if scope == PlanScope.SUBJECT_PART:
            if not target_subject_code_or_id:
                raise ValueError(
                    "SUBJECT_REQUIRED: SUBJECT_PART scope needs a target subject.")
            curr = await get_curriculum(ctx.university_id, branch, ctx.semester)
            if not curr or not curr.subjects:
                raise ValueError("CURRICULUM_NOT_FOUND: no verified curriculum "
                                 "for this branch/semester.")
            matched = [s for s in curr.subjects
                       if s.subject_id == target_subject_code_or_id
                       or s.code == target_subject_code_or_id
                       or s.name == target_subject_code_or_id]
            if not matched:
                raise ValueError(
                    f"SUBJECT_NOT_FOUND: '{target_subject_code_or_id}' is not in "
                    f"the verified curriculum.")
            return [(ctx.semester, s) for s in matched]

        if scope == PlanScope.WHOLE_PROGRAM:
            # Sequential awaits. The previous threaded fetch raced under
            # serverless CPU limits and silently dropped whole semesters
            # (a live 8-semester RTU CSE program produced a plan covering
            # only semesters 3, 4, 5, 7 — get_curriculum swallows fetch
            # failures into None, so a raced-out semester vanished without
            # a trace). Eight sequential registry reads cost a few seconds
            # and cannot drop a semester silently: a semester with no
            # verified curriculum is logged by name.
            scoped: List[Tuple[int, Any]] = []
            for semester in range(1, 9):
                curr = await get_curriculum(
                    ctx.university_id, branch, semester)
                if curr and curr.subjects:
                    scoped.extend((semester, s) for s in curr.subjects)
                else:
                    log_event(
                        "college.plan.whole_program_semester_missing",
                        user_id=uid, semester=semester, outcome="degraded")
            if not scoped:
                raise ValueError("CURRICULUM_NOT_FOUND: no verified curricula "
                                 "found for this program.")
            return scoped

        # SEMESTER (default): the learner's chosen context subjects, or the
        # whole semester when none were chosen.
        curr = await get_curriculum(ctx.university_id, branch, ctx.semester)
        if not curr or not curr.subjects:
            raise ValueError("CURRICULUM_NOT_FOUND: no verified curriculum "
                             "for this branch/semester.")
        subject_ids = await self.store.get_context_subject_ids(ctx.context_id)
        # target_subject_code_or_id is only meaningful for SUBJECT_PART.
        # A SEMESTER plan covers the learner's chosen context subjects (or
        # the whole semester when none were chosen); never silently narrow
        # it to the first selected subject.
        if subject_ids:
            matched = [s for s in curr.subjects
                       if s.subject_id in subject_ids or s.code in subject_ids]
            if not matched:
                matched = list(curr.subjects)
        else:
            matched = list(curr.subjects)
        return [(ctx.semester, s) for s in matched]

    @staticmethod
    def _canonical_goal_id(uid: str, goal_id: Optional[str], scope: PlanScope) -> str:
        """
        Builds the authoritative per-user goal ID for a plan request.

        Clients have historically sent shared static IDs such as
        "goal_semester" for every learner. college_goals.goal_id was globally
        unique in the first schema, so a second learner asking for the same
        static ID collided with the first learner's goal row. The backend is
        the authority here: preserve an already user-namespaced ID, otherwise
        namespace the requested slug under the learner's uid.
        """
        prefix = f"goal_{uid}_"
        raw = (goal_id or "").strip()
        if raw.startswith(prefix):
            return raw
        slug = re.sub(r"[^a-z0-9_-]+", "_", raw.lower()).strip("_")
        while slug.startswith("goal_"):
            slug = slug[len("goal_"):]
        if not slug:
            slug = scope.value.lower()
        return f"{prefix}{slug}"[:160]

    async def _ensure_goal(
        self, uid: str, goal_id: Optional[str], scope: PlanScope
    ) -> str:
        """
        learning_plans has an FK to college_goals: make sure the referenced
        goal exists for THIS learner. Creates the goal the learner actually
        asked for — never a fabricated one, and never another learner's row.
        Returns the effective goal_id the plan must reference.
        """
        raw_goal = await self.store.get_college_goal(uid)
        existing_goal_id = (
            raw_goal.get("goal_id") if isinstance(raw_goal, dict)
            else getattr(raw_goal, "goal_id", None)
        )
        if goal_id and existing_goal_id == goal_id:
            return goal_id

        canonical_goal_id = self._canonical_goal_id(uid, goal_id, scope)
        if existing_goal_id == canonical_goal_id:
            return canonical_goal_id

        goal = CollegeGoal(
            goal_id=canonical_goal_id,
            user_id=uid,
            goal_type="SEMESTER_EXAM",
            scope=scope,
            raw_goal=f"{scope.value.replace('_', ' ').title()} preparation",
            normalized_goal=f"{scope.value.replace('_', ' ').title()} preparation",
            status="ACTIVE",
        )
        await self.store.save_college_goal(uid, goal.model_dump(mode="json"))
        return canonical_goal_id

    @staticmethod
    def _get_gemini_model():
        # Centralized in backend.core.gemini (settings.GEMINI_MODEL) so a
        # model retirement is an env change, not a code deploy.
        from backend.core.gemini import get_gemini_model as _shared
        return _shared()

    # ------------------------------------------------------------------
    # Activities
    # ------------------------------------------------------------------

    async def _prefetch_subject_inputs(
        self, university_id: Optional[str], subject_ids: List[str],
    ) -> Tuple[Dict[str, List[ResourceRecord]],
               Dict[str, List[PYQQuestionRecord]]]:
        """
        Batch-fetch resources + PYQ questions for many subjects in 3 queries.
        The supabase-py client is synchronous: letting each of the 87
        whole-program phases do its own 2 reads blocks the event loop ~60s+
        and blows the serverless window. The blocking batch runs in a thread
        so the loop stays free. Returns (resources_by_subject,
        pyq_questions_by_subject). Mirrors the semantics of
        get_resources_for_subject / get_pyqs_for_subject.
        """
        def _fetch():
            from backend.providers.curriculum_registry import (
                get_supabase_adapter)
            resources_by: Dict[str, List[ResourceRecord]] = {}
            pyqs_by: Dict[str, List[PYQQuestionRecord]] = {}
            adapter = get_supabase_adapter()
            if not adapter.client or not subject_ids:
                return resources_by, pyqs_by
            try:
                res = (adapter.client.table("learning_resources")
                       .select("*").in_("subject_id", subject_ids).execute())
                for row in (res.data or []):
                    try:
                        rec = ResourceRecord(**row)
                    except Exception:
                        continue
                    # subject_id lives on the DB row, not the pydantic model.
                    resources_by.setdefault(
                        row.get("subject_id"), []).append(rec)
            except Exception:
                pass
            try:
                q = (adapter.client.table("pyq_sets").select("*")
                     .in_("subject_id", subject_ids))
                if university_id:
                    q = q.eq("university_id", university_id)
                sets = q.execute()
                # latest exam_year set per subject
                best: Dict[str, dict] = {}
                for row in (sets.data or []):
                    sid = row.get("subject_id")
                    if (sid not in best or (row.get("exam_year") or 0) >
                            (best[sid].get("exam_year") or 0)):
                        best[sid] = row
                set_ids = [r.get("pyq_set_id") for r in best.values()
                           if r.get("pyq_set_id")]
                questions_by_set: Dict[str, List[PYQQuestionRecord]] = {}
                if set_ids:
                    qr = (adapter.client.table("pyq_questions").select("*")
                          .in_("pyq_set_id", set_ids).execute())
                    for qrow in (qr.data or []):
                        try:
                            qrec = PYQQuestionRecord(**qrow)
                        except Exception:
                            continue
                        questions_by_set.setdefault(
                            qrow.get("pyq_set_id"), []).append(qrec)
                for sid, srow in best.items():
                    pyqs_by[sid] = questions_by_set.get(
                        srow.get("pyq_set_id"), [])
            except Exception:
                pass
            return resources_by, pyqs_by

        return await asyncio.to_thread(_fetch)

    async def _build_phase_activities(
        self,
        uid: str,
        plan_id: str,
        university_id: str,
        semester: int,
        sub,
        unit,
        phase_order: int,
        available_hours_per_week: Optional[int],
        model,
        prefetched: Optional[Tuple[Dict[str, List[ResourceRecord]],
                                   Dict[str, List[PYQQuestionRecord]]]] = None,
    ) -> Tuple[List[CollegeActivity], bool]:
        """Returns (activities, used_llm). used_llm is False when the model
        was unavailable or returned nothing and the deterministic static
        sequence was used instead."""
        phase_id = f"phase_{plan_id}_{sub.subject_id}_s{semester}_u{unit.unit}"
        status = "AVAILABLE" if phase_order == 1 else "LOCKED"
        if prefetched is not None:
            # Batch-prefetched by the caller: no per-phase DB reads.
            resources = prefetched[0].get(sub.subject_id, [])
            pyq_questions = prefetched[1].get(sub.subject_id, [])
        else:
            resources = await get_resources_for_subject(sub.subject_id)
            pyq_set = await get_pyqs_for_subject(university_id, sub.subject_id)
            pyq_questions = pyq_set.questions if pyq_set else []

        activities: List[CollegeActivity] = []
        used_llm = False
        if model:
            # generate_content is a blocking sync call: run it in a thread so
            # the concurrent phase builds actually overlap instead of stalling
            # the event loop.
            activities = await asyncio.to_thread(
                self._genai_activities,
                uid, plan_id, phase_id, status, model, sub, unit,
                available_hours_per_week, resources, pyq_questions)
            used_llm = bool(activities)
        if not activities:
            activities = self._static_activities(
                uid, plan_id, phase_id, status, sub, unit,
                resources, pyq_questions)
        return activities, used_llm

    def _genai_activities(self, uid, plan_id, phase_id, status, model,
                          sub, unit, available_hours_per_week,
                          resources, pyq_questions) -> List[CollegeActivity]:
        import json
        try:
            res_summary = [{"id": r.resource_id, "type": r.resource_type,
                            "title": r.title} for r in resources]
            pyq_summary = [{"id": q.question_id, "text": q.question_text}
                           for q in pyq_questions]
            prompt = f"""
You are the PATHMIND Study Planner. Create a personalized study sequence for a college student.
Subject: {sub.name}, Unit: {unit.title} (Topics: {', '.join(unit.topics)})
Available hours/week: {available_hours_per_week}

Available Resources: {json.dumps(res_summary)}
Available PYQs (Past Questions): {json.dumps(pyq_summary)}

Return ONLY a valid JSON array of activities in the best learning order. Each activity should be:
{{
    "type": "WATCH|READ|PRACTICE|SOLVE_PYQ",
    "resource_id": "id from above if applicable",
    "pyq_id": "id from above if applicable",
    "title": "short title in simple, plain words",
    "instructions": "1-2 short sentences in simple, direct English: exactly what the student should do first, how long it should take, and what they will be able to do after. No jargon, no buzzwords, no complicated words.",
    "steps": ["one short, simple step", "one action per step"],
    "minutes": 30
}}
Write for a first-year student reading this on a phone: short sentences, everyday words, one clear action per step. If a sentence needs a technical term, explain that term in the same sentence.
"steps" = 2-4 concrete instructions for HOW to learn this, not what it is:
for WATCH, active viewing (pause and write each definition in your own words,
then recall the key ideas with the video closed); for READ, skim-then-read
with a closed-book summary after each section; for PRACTICE, attempt
closed-book BEFORE checking any solution, then redo from a blank page;
for SOLVE_PYQ, a timed exam-condition attempt, honest self-scoring, and an
error log (concept / formula / calculation / time).
Ensure you order them logically (e.g. WATCH then READ then PRACTICE then SOLVE_PYQ).
"""
            response = generate_fast(model, prompt, 1536)
            text = response.text.strip()
            if text.startswith("```json"):
                text = text[7:]
            if text.startswith("```"):
                text = text[3:]
            if text.endswith("```"):
                text = text[:-3]
            gen_activities = json.loads(text.strip())

            activities = []
            for act_order, ga in enumerate(gen_activities, start=1):
                res = next((r for r in resources
                            if r.resource_id == ga.get("resource_id")), None)
                pyq = next((q for q in pyq_questions
                            if q.question_id == ga.get("pyq_id")), None)
                act_type = ga.get("type", "PRACTICE")
                if act_type not in [e.value for e in ActivityType]:
                    act_type = "PRACTICE"
                raw_steps = ga.get("steps")
                steps = [
                    str(s).strip()[:240] for s in raw_steps
                    if isinstance(s, str) and str(s).strip()
                ][:6] if isinstance(raw_steps, list) else []
                if len(steps) < 2:
                    steps = _learn_steps_for(act_type, res, list(unit.topics))
                activities.append(CollegeActivity(
                    activity_id=f"act_{phase_id}_{act_order}",
                    user_id=uid,
                    plan_id=plan_id,
                    phase_id=phase_id,
                    activity_type=ActivityType(act_type),
                    title=ga.get("title", f"{act_type} Activity"),
                    resource=res,
                    resource_id=res.resource_id if res else None,
                    pyq_question=pyq,
                    pyq_question_id=pyq.question_id if pyq else None,
                    order=act_order,
                    instructions=ga.get("instructions", "Follow the study plan."),
                    learn_steps=steps,
                    estimated_minutes=ga.get("minutes", 30),
                    status=status,
                ))
            return activities
        except Exception as exc:
            log_event("college.plan.activity_generation_failed",
                      outcome="error", error_code=type(exc).__name__)
            # Bounded detail for the enrich endpoint's honest 503: the
            # exception TYPE alone cannot distinguish a retired model
            # from a quota cap from unparseable output.
            self._last_activity_gen_error = (
                f"{type(exc).__name__}: {str(exc)[:160]}")
            return []

    def _static_activities(self, uid, plan_id, phase_id, status, sub, unit,
                           resources, pyq_questions) -> List[CollegeActivity]:
        activities: List[CollegeActivity] = []
        act_order = 1

        videos = [r for r in resources if r.resource_type == "VIDEO"]
        # On-topic first, then the most-watched/best-liked lecture
        # (round 7 quality-first ranking); ties keep cache order (max is
        # stable), so stat-less caches behave exactly as before.
        match_title = f"{sub.code}: {unit.title}"
        video_res = (max(videos,
                         key=lambda r: _resource_pick_key(r, match_title))
                     if videos else None)
        if video_res:
            ts_info = video_res.video_timestamps[0] if video_res.video_timestamps else None
            ts_text = (f" Start at {ts_info.start_seconds // 60}:00 and watch till "
                       f"{ts_info.end_seconds // 60}:00 — this part covers '{ts_info.purpose}'.") if ts_info else " Watch it fully once."
            activities.append(CollegeActivity(
                activity_id=f"act_{phase_id}_{act_order}",
                user_id=uid,
                plan_id=plan_id,
                phase_id=phase_id,
                activity_type=ActivityType.WATCH,
                title=f"Watch Lecture: {unit.title}",
                resource=video_res,
                resource_id=video_res.resource_id,
                order=act_order,
                instructions=f"Watch \"{video_res.title}\" ({video_res.provider}).{ts_text}",
                learn_steps=_learn_steps_for("WATCH", video_res, list(unit.topics)),
                estimated_minutes=video_res.estimated_minutes,
                status=status,
            ))
            act_order += 1

        docs = [r for r in resources
                if r.resource_type in ["NOTES", "DOCUMENT"]]
        doc_res = (max(docs,
                       key=lambda r: _resource_pick_key(r, match_title))
                   if docs else None)
        if doc_res:
            sec_info = doc_res.document_sections[0] if doc_res.document_sections else None
            pg_text = (f" Read pages {sec_info.start_page}–{sec_info.end_page} "
                       f"(this section is about '{sec_info.section_title}').") if sec_info else " Read the full notes once."
            activities.append(CollegeActivity(
                activity_id=f"act_{phase_id}_{act_order}",
                user_id=uid,
                plan_id=plan_id,
                phase_id=phase_id,
                activity_type=ActivityType.READ,
                title=f"Read Verified Notes: {unit.title}",
                resource=doc_res,
                resource_id=doc_res.resource_id,
                order=act_order,
                instructions=f"Read the notes from {doc_res.provider}.{pg_text}",
                learn_steps=_learn_steps_for("READ", doc_res, list(unit.topics)),
                estimated_minutes=doc_res.estimated_minutes,
                status=status,
            ))
            act_order += 1

        activities.append(CollegeActivity(
            activity_id=f"act_{phase_id}_{act_order}",
            user_id=uid,
            plan_id=plan_id,
            phase_id=phase_id,
            activity_type=ActivityType.PRACTICE,
            title=f"Solve Practice Problems: {unit.topics[0] if unit.topics else unit.title}",
            order=act_order,
            instructions=f"Solve practice problems on: {', '.join(unit.topics[:3])}. Try each problem yourself first — check the answer only after you have written your own.",
            learn_steps=_learn_steps_for("PRACTICE", None, list(unit.topics)),
            estimated_minutes=30,
            status=status,
        ))
        act_order += 1

        if pyq_questions:
            target_pyq = pyq_questions[0]
            activities.append(CollegeActivity(
                activity_id=f"act_{phase_id}_{act_order}",
                user_id=uid,
                plan_id=plan_id,
                phase_id=phase_id,
                activity_type=ActivityType.SOLVE_PYQ,
                title=f"Attempt University PYQ: {target_pyq.question_number}",
                pyq_question=target_pyq,
                pyq_question_id=target_pyq.question_id,
                order=act_order,
                instructions=f"Solve this real university question ({target_pyq.marks} marks). Set a timer, use no notes, then check your answer honestly. Question: {target_pyq.question_text}",
                learn_steps=_learn_steps_for("SOLVE_PYQ", None, list(unit.topics)),
                estimated_minutes=25,
                status=status,
            ))
        return activities

    # ------------------------------------------------------------------
    # Progression
    # ------------------------------------------------------------------

    async def _decorate_plan(
        self, plan: CollegeLearningPlan,
    ) -> CollegeLearningPlan:
        """Attach verified resources + learn steps to a loaded plan.

        Activities persist only `resource_id` (the resource object is a
        transient API field), so a plan read back from the store arrives
        link-less unless rehydrated here. This pass:
          1. re-attaches the exact resource each activity references,
          2. attaches the best cached VERIFIED resource to WATCH/READ
             activities that have none (topic-matched to the phase first) —
             this is how resources researched on demand (dashboard
             auto-enrich / Personalize) reach already-generated plans,
          3. fills `learn_steps` (the how-to-learn method) where missing.
        Guarded: a decoration failure must never break a plan read.
        """
        try:
            subjects: List[str] = []
            for phase in plan.phases:
                sid = _subject_id_from_phase_id(phase.phase_id, plan.plan_id)
                if sid and sid not in subjects:
                    subjects.append(sid)
            resources_by_subject: Dict[str, List[ResourceRecord]] = {}

            # Fetch every phase subject's cached resources in parallel:
            # this pass runs on every plan read, and N sequential
            # round-trips (one per subject) made the dashboard feel
            # stuck right after onboarding.
            async def _load_subject_resources(sid: str):
                try:
                    return sid, await get_resources_for_subject(sid)
                except Exception:
                    return sid, []

            resources_by_subject = dict(await asyncio.gather(
                *(_load_subject_resources(sid) for sid in subjects)))
            by_id = {
                r.resource_id: r
                for records in resources_by_subject.values()
                for r in records
            }
            # Referenced ids outside the phase subjects' caches (stale or
            # cross-subject links): one batch fetch, best-effort.
            missing_ids = list(dict.fromkeys(
                act.resource_id
                for phase in plan.phases for act in phase.activities
                if act.resource_id and act.resource_id not in by_id))
            if missing_ids:
                try:
                    from backend.providers.curriculum_registry import (
                        get_supabase_adapter,
                    )
                    adapter = get_supabase_adapter()
                    if adapter and adapter.client:
                        res = (
                            adapter.client.table("learning_resources")
                            .select("*")
                            .in_("resource_id", missing_ids)
                            .execute()
                        )
                        for row in (res.data or []):
                            try:
                                rec = ResourceRecord(**row)
                                by_id[rec.resource_id] = rec
                            except Exception:
                                continue
                except Exception:
                    pass

            for phase in plan.phases:
                sid = _subject_id_from_phase_id(phase.phase_id, plan.plan_id)
                cached = resources_by_subject.get(sid or "", [])
                for act in phase.activities:
                    if act.resource is None and act.resource_id:
                        act.resource = by_id.get(act.resource_id)
                    if act.resource is None and sid:
                        act_type = act.activity_type.value
                        if act_type == "WATCH":
                            candidates = [
                                r for r in cached
                                if r.resource_type == "VIDEO"]
                        elif act_type == "READ":
                            docs = [
                                r for r in cached
                                if r.resource_type in ("NOTES", "DOCUMENT")]
                            candidates = docs or [
                                r for r in cached
                                if r.resource_type != "VIDEO"]
                        elif act_type == "PRACTICE":
                            # Practice problems are where a learner uses
                            # worked material: give PRACTICE the same best
                            # cached material so the card shows a real link
                            # instead of "no material linked yet" while
                            # verified notes/videos sit unused in the cache.
                            candidates = [
                                r for r in cached
                                if r.resource_type in ("NOTES", "DOCUMENT")]
                            candidates = candidates or list(cached)
                        else:
                            candidates = []
                        if candidates:
                            best = max(
                                candidates,
                                key=lambda r: _resource_pick_key(
                                    r, phase.title),
                            )
                            act.resource = best
                            # Persisted on the next phase save, so the link
                            # sticks instead of being re-derived every read.
                            act.resource_id = best.resource_id
                    if not act.learn_steps:
                        act.learn_steps = _learn_steps_for(
                            act.activity_type.value, act.resource)

                # Heal resourceless builds: a phase generated while the
                # resource cache was empty may have no WATCH/READ slots at
                # all (the deterministic builder only creates them when
                # material exists). Now that verified material is cached,
                # synthesize the slots generation would have produced.
                # Deterministic ids — a later phase save persists them as
                # ordinary activities.
                # Locked phases get the slots too: a learner browsing the
                # path ahead should see a learning link for every topic, not
                # only for the phase they are on. Completion stays gated
                # server-side (checkpoint mastery), so a visible link never
                # unlocks anything by itself.
                if sid and cached and phase.status in ("AVAILABLE",
                                                       "IN_PROGRESS",
                                                       "LOCKED"):
                    present = {a.activity_type.value
                               for a in phase.activities}
                    unit_title = (phase.title.split(": ", 1)[1]
                                  if ": " in phase.title else phase.title)
                    synthesized: List[CollegeActivity] = []
                    videos = [r for r in cached
                              if r.resource_type == "VIDEO"]
                    docs = [r for r in cached
                            if r.resource_type in ("NOTES", "DOCUMENT")]
                    if videos and "WATCH" not in present:
                        best = max(
                            videos,
                            key=lambda r: _resource_pick_key(
                                r, phase.title))
                        synthesized.append(CollegeActivity(
                            activity_id=f"act_{phase.phase_id}_auto_watch",
                            user_id=plan.user_id,
                            plan_id=plan.plan_id,
                            phase_id=phase.phase_id,
                            activity_type=ActivityType.WATCH,
                            title=f"Watch Lecture: {unit_title}",
                            resource=best,
                            resource_id=best.resource_id,
                            order=1,
                            instructions=(
                                f"Watch \"{best.title}\" "
                                f"({best.provider}). Follow the steps "
                                f"below while you watch."),
                            learn_steps=_learn_steps_for("WATCH", best, []),
                            estimated_minutes=best.estimated_minutes,
                            status="AVAILABLE",
                        ))
                    if docs and "READ" not in present:
                        best = max(
                            docs,
                            key=lambda r: _resource_pick_key(
                                r, phase.title))
                        synthesized.append(CollegeActivity(
                            activity_id=f"act_{phase.phase_id}_auto_read",
                            user_id=plan.user_id,
                            plan_id=plan.plan_id,
                            phase_id=phase.phase_id,
                            activity_type=ActivityType.READ,
                            title=f"Read Verified Notes: {unit_title}",
                            resource=best,
                            resource_id=best.resource_id,
                            order=2,
                            instructions=(
                                f"Read \"{best.title}\" "
                                f"({best.provider}). Follow the steps "
                                f"below while you read."),
                            learn_steps=_learn_steps_for("READ", best, []),
                            estimated_minutes=best.estimated_minutes,
                            status="AVAILABLE",
                        ))
                    if synthesized:
                        phase.activities = (
                            synthesized + list(phase.activities))

                # Every phase assigns previous-year practice for its own
                # level: one SOLVE_PYQ step that sends the learner to the
                # PYQ Vault scoped to this subject and unit. Synthesized
                # even when no questions are seeded — the vault runs its
                # live official-domain search when the learner opens it,
                # and reports honestly when nothing is verified yet.
                if sid and phase.status != "COMPLETED":
                    present_types = {a.activity_type.value
                                     for a in phase.activities}
                    if "SOLVE_PYQ" not in present_types:
                        unit_title = (phase.title.split(": ", 1)[1]
                                      if ": " in phase.title
                                      else phase.title)
                        phase.activities = list(phase.activities) + [
                            CollegeActivity(
                                activity_id=(
                                    f"act_{phase.phase_id}_auto_pyq"),
                                user_id=plan.user_id,
                                plan_id=plan.plan_id,
                                phase_id=phase.phase_id,
                                activity_type=ActivityType.SOLVE_PYQ,
                                title=(f"Solve Previous-Year Questions: "
                                       f"{unit_title}"),
                                resource_id=None,
                                pyq_question_id=None,
                                order=max((a.order
                                           for a in phase.activities),
                                          default=0) + 1,
                                instructions=(
                                    "Open the PYQ Vault for this subject "
                                    "and pick the most recent "
                                    "previous-year paper. Sit in exam "
                                    "conditions — no notes, timer on — "
                                    f"and solve the {unit_title} "
                                    "questions first. Then check every "
                                    "mistake and write down why you got "
                                    "it wrong. If no verified paper is "
                                    "available yet, do the practice "
                                    "problems above instead."),
                                estimated_minutes=45,
                                status="AVAILABLE",
                                learn_steps=_learn_steps_for(
                                    "SOLVE_PYQ", None, [unit_title]),
                            )]
        except Exception as exc:
            log_event("college.plan.decorate_failed", user_id=plan.user_id,
                      outcome="error", error_code=type(exc).__name__)
        return plan

    async def get_current_plan(self, uid: str) -> Optional[CollegeLearningPlan]:
        raw = await self.store.get_college_learning_plan(uid)
        if raw:
            plan = (raw if isinstance(raw, CollegeLearningPlan)
                    else CollegeLearningPlan(**raw))
            return await self._decorate_plan(plan)
        return None

    async def complete_activity(
        self,
        uid: str,
        activity_id: str,
        completion_evidence: Optional[Dict[str, Any]] = None,
    ) -> CollegeLearningPlan:
        """
        Marks an activity complete. When every activity in a phase is done the
        phase becomes COMPLETED — but the next phase is NOT unlocked here.
        Unlocking requires demonstrated mastery via the phase assessment
        (see maybe_unlock_next_phase).
        """
        with timed_stage("college.plan.activity_completed", user_id=uid,
                         activity_id=activity_id):
            plan = await self.get_current_plan(uid)
            if not plan:
                raise ValueError("PLAN_NOT_FOUND")

            from datetime import datetime, timezone
            now = datetime.now(timezone.utc).isoformat()

            found = False
            touched_phase = None
            for phase in plan.phases:
                for act in phase.activities:
                    if act.activity_id == activity_id:
                        act.status = "COMPLETED"
                        act.completed_at = now
                        act.completion_evidence = (
                            completion_evidence or {"type": "STUDY_CONFIRMATION"})
                        found = True
                        touched_phase = phase
                        break
                if found:
                    if all(a.status == "COMPLETED" for a in phase.activities):
                        phase.status = "COMPLETED"
                        log_event("college.plan.phase_completed_awaiting_mastery",
                                  user_id=uid, phase_id=phase.phase_id,
                                  outcome="ok")
                    break

            if not found:
                raise ValueError("ACTIVITY_NOT_FOUND")

            # Persist ONLY the touched phase. Re-saving the whole plan
            # hierarchy (plan + subjects + every phase + every activity) on
            # each "Mark Done" click was the dashboard lag: the phase-scoped
            # save upserts one phase row and replaces just its activities.
            # The plan row itself does not change on activity completion.
            save_phase = getattr(self.store, "save_college_phase", None)
            if save_phase is not None and touched_phase is not None:
                await save_phase(
                    uid, touched_phase.model_dump(mode="json"))
            else:
                await self.store.save_college_learning_plan(
                    uid, plan.model_dump(mode="json"))
            return plan

    async def maybe_unlock_next_phase(
        self, uid: str, assessment: CollegeAssessment
    ) -> bool:
        """
        Evaluate the phase's unlock_rule against the per-topic mastery store.
        Unlocks the next phase only on demonstrated mastery — never on mere
        activity completion. Returns True when a phase was unlocked.
        """
        with timed_stage("college.plan.unlock_evaluated", user_id=uid,
                         assessment_id=assessment.assessment_id):
            plan = await self.get_current_plan(uid)
            if not plan:
                return False
            idx = next((i for i, p in enumerate(plan.phases)
                        if p.phase_id == assessment.phase_id), None)
            if idx is None:
                log_event("college.plan.unlock_evaluated", user_id=uid,
                          outcome="skipped", reason="PHASE_NOT_FOUND")
                return False
            phase = plan.phases[idx]

            masteries = await self.store.get_topic_masteries(uid)
            topic_scores = {
                m["topic"]: float(m.get("mastery_score") or 0.0)
                for m in masteries
                if assessment.subject_id is None
                or m.get("subject_id") == assessment.subject_id
            }
            unlocked, reason = evaluate_unlock_rule(phase.unlock_rule, topic_scores)
            log_event("college.plan.unlock_evaluated", user_id=uid,
                      phase_id=phase.phase_id, unlocked=unlocked, reason=reason,
                      outcome="ok")
            if not unlocked:
                return False
            if idx + 1 < len(plan.phases):
                nxt = plan.phases[idx + 1]
                nxt.status = "AVAILABLE"
                for act in nxt.activities:
                    if act.status == "LOCKED":
                        act.status = "AVAILABLE"
                await self.store.save_college_learning_plan(
                    uid, plan.model_dump(mode="json"))
                log_event("college.plan.phase_unlocked", user_id=uid,
                          phase_id=nxt.phase_id, reason=reason, outcome="ok")
                return True
            return False
