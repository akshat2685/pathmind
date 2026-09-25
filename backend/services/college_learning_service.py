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
import re
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
from backend.providers.curriculum_registry import (
    get_curriculum,
    get_resources_for_subject,
    get_pyqs_for_subject,
)
from backend.services.store import FirestoreStore

#: Fraction of the phase assessment score required to unlock the next phase.
UNLOCK_REQUIRED_SCORE = 75.0


class CollegeLearningService:
    def __init__(self, store: Optional[FirestoreStore] = None):
        self.store = store or FirestoreStore()

    # ------------------------------------------------------------------
    # Plan generation
    # ------------------------------------------------------------------

    async def generate_learning_plan(
        self,
        uid: str,
        goal_id: str,
        target_subject_code_or_id: Optional[str] = None,
        scope: PlanScope = PlanScope.SEMESTER,
    ) -> CollegeLearningPlan:
        """
        Synthesizes an ordered, multi-phase learning plan across the whole
        requested scope. Every subject unit becomes a phase (full syllabus).
        """
        with timed_stage("college.plan.generated", user_id=uid, scope=scope.value):
            raw_ctx = await self.store.get_college_academic_context(uid)
            if not raw_ctx:
                raise ValueError(
                    "ACADEMIC_CONTEXT_REQUIRED: Please complete academic onboarding first.")
            ctx = AcademicContext(**raw_ctx)

            branch = await self._resolve_branch(uid)
            scoped_subjects = await self._resolve_scoped_subjects(
                uid, ctx, branch, scope, target_subject_code_or_id)

            await self._ensure_goal(uid, goal_id, scope)

            plan_id = f"plan_{uid}_{scope.value.lower()}_{uuid.uuid4().hex[:6]}"
            model = self._get_gemini_model()

            phases: List[CollegePlanPhase] = []
            plan_subjects: List[LearningPlanSubject] = []
            seen_subjects = set()
            phase_order = 1

            # Collect phase specs first (order preserved), then build
            # activities concurrently. Serial per-phase Gemini calls are what
            # blew the ~60s serverless cap on whole-program generation; a
            # bounded semaphore keeps free-tier rate limits in check while
            # cutting wall-clock time ~8x. For large plans (whole-program is
            # 87 phases for RTU CSE) even 8x concurrency cannot fit the ~60s
            # serverless window, so generation is tiered: small plans get LLM
            # activities for every phase, large plans get them for the head
            # phases only and the deterministic static sequence for the tail.
            # Tail phases are fully usable (real resources + PYQs) and can be
            # upgraded to AI-personalized activities on demand.
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

            # Tiered generation. Small plans (semester / subject-part) get
            # LLM activities for every phase. Large plans (whole-program is
            # 87 phases) get the deterministic static sequence for ALL phases
            # at generation time: a single phase LLM call costs ~30s+ on the
            # free tier, so even a 3-phase LLM head cannot fit the ~60s
            # serverless window reliably. Tail/head phases are fully usable
            # (real resources + PYQs) and any single phase can be upgraded to
            # AI-personalized activities on demand via enrich_phase_activities.
            _LLM_FULL_CAP = 16  # at/below: LLM activities for every phase
            _tiered = len(phase_specs) > _LLM_FULL_CAP

            def _wants_llm(order: int) -> bool:
                return not _tiered

            _concurrency = asyncio.Semaphore(8)

            async def _build_one(
                spec: Tuple[int, Any, Any, int],
            ) -> Tuple[List[CollegeActivity], bool]:
                semester, sub, unit, order = spec
                async with _concurrency:
                    # model=None forces the deterministic static sequence
                    # (no LLM call) for tail phases of large plans.
                    return await self._build_phase_activities(
                        uid, plan_id, ctx.university_id, semester, sub, unit,
                        order, ctx.available_hours_per_week,
                        model if _wants_llm(order) else None)

            built_per_phase = await asyncio.gather(
                *(_build_one(spec) for spec in phase_specs))

            for (semester, sub, unit, order), (activities, used_llm) in zip(
                    phase_specs, built_per_phase):
                phase_id = f"phase_{plan_id}_{sub.subject_id}_s{semester}_u{unit.unit}"
                phases.append(CollegePlanPhase(
                    phase_id=phase_id,
                    user_id=uid,
                    plan_id=plan_id,
                    order=order,
                    title=f"{sub.code}: {unit.title}",
                    objective=(f"Master fundamental theories and exam problems "
                               f"for {sub.name} (Semester {semester}, Unit {unit.unit})."),
                    ai_enriched=used_llm,
                    status="AVAILABLE" if order == 1 else "LOCKED",
                    # Schema §16 unlock rule: demonstrated mastery required.
                    unlock_rule={
                        "type": "ASSESSMENT_MASTERY",
                        "required_assessment_score": UNLOCK_REQUIRED_SCORE,
                        "required_topics": list(unit.topics),
                    },
                    activities=activities,
                    assessment_id=f"asmt_{phase_id}",
                ))

            plan = CollegeLearningPlan(
                plan_id=plan_id,
                user_id=uid,
                goal_id=goal_id,
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
            await self.store.save_college_learning_plan(
                uid, plan.model_dump(mode="json"))
            await self.store.activate_college_learning_plan(uid, plan_id)
            plan.status = "ACTIVE"
            log_event("college.plan.saved", user_id=uid, plan_id=plan_id,
                      phase_count=len(phases),
                      subject_count=len(plan_subjects), outcome="ok")
            return plan

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
        expected_prefix = f"phase_{plan_id}_"
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

        model = self._get_gemini_model()
        if model is None:
            raise ValueError(
                "AI_UNAVAILABLE: the AI service is not configured right now.")

        order = int(target.get("order") or 1)
        activities, used_llm = await self._build_phase_activities(
            uid, plan_id, ctx.university_id, semester, sub, unit,
            order, ctx.available_hours_per_week, model)
        if not used_llm:
            raise ValueError(
                "AI_UNAVAILABLE: the AI service did not return activities; "
                "your current activities are unchanged. Try again in a bit.")

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
            scoped: List[Tuple[int, Any]] = []
            for semester in range(1, 9):
                curr = await get_curriculum(ctx.university_id, branch, semester)
                if curr and curr.subjects:
                    scoped.extend((semester, s) for s in curr.subjects)
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
        if target_subject_code_or_id:
            matched = [s for s in curr.subjects
                       if s.subject_id == target_subject_code_or_id
                       or s.code == target_subject_code_or_id
                       or s.name == target_subject_code_or_id]
            if not matched:
                raise ValueError(
                    f"SUBJECT_NOT_FOUND: '{target_subject_code_or_id}' is not in "
                    f"the verified curriculum.")
        elif subject_ids:
            matched = [s for s in curr.subjects
                       if s.subject_id in subject_ids or s.code in subject_ids]
            if not matched:
                matched = list(curr.subjects)
        else:
            matched = list(curr.subjects)
        return [(ctx.semester, s) for s in matched]

    async def _ensure_goal(self, uid: str, goal_id: str, scope: PlanScope) -> None:
        """
        learning_plans has an FK to college_goals: make sure the referenced
        goal exists. Creates the goal the learner actually asked for — never
        a fabricated one.
        """
        raw_goal = await self.store.get_college_goal(uid)
        if raw_goal and raw_goal.get("goal_id") == goal_id:
            return
        goal = CollegeGoal(
            goal_id=goal_id,
            user_id=uid,
            goal_type="SEMESTER_EXAM",
            scope=scope,
            raw_goal=f"{scope.value.replace('_', ' ').title()} preparation",
            normalized_goal=f"{scope.value.replace('_', ' ').title()} preparation",
            status="ACTIVE",
        )
        await self.store.save_college_goal(uid, goal.model_dump(mode="json"))

    @staticmethod
    def _get_gemini_model():
        # Centralized in backend.core.gemini (settings.GEMINI_MODEL) so a
        # model retirement is an env change, not a code deploy.
        from backend.core.gemini import get_gemini_model as _shared
        return _shared()

    # ------------------------------------------------------------------
    # Activities
    # ------------------------------------------------------------------

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
    ) -> Tuple[List[CollegeActivity], bool]:
        """Returns (activities, used_llm). used_llm is False when the model
        was unavailable or returned nothing and the deterministic static
        sequence was used instead."""
        phase_id = f"phase_{plan_id}_{sub.subject_id}_s{semester}_u{unit.unit}"
        status = "AVAILABLE" if phase_order == 1 else "LOCKED"
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
    "title": "short engaging title",
    "instructions": "personalized instructions",
    "minutes": 30
}}
Ensure you order them logically (e.g. WATCH then READ then PRACTICE then SOLVE_PYQ).
"""
            response = model.generate_content(prompt)
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
                    estimated_minutes=ga.get("minutes", 30),
                    status=status,
                ))
            return activities
        except Exception as exc:
            log_event("college.plan.activity_generation_failed",
                      outcome="error", error_code=type(exc).__name__)
            return []

    def _static_activities(self, uid, plan_id, phase_id, status, sub, unit,
                           resources, pyq_questions) -> List[CollegeActivity]:
        activities: List[CollegeActivity] = []
        act_order = 1

        video_res = next((r for r in resources if r.resource_type == "VIDEO"), None)
        if video_res:
            ts_info = video_res.video_timestamps[0] if video_res.video_timestamps else None
            ts_text = (f" Watch from {ts_info.start_seconds // 60}:00 to "
                       f"{ts_info.end_seconds // 60}:00 for '{ts_info.purpose}'.") if ts_info else " Watch the core foundational module."
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
                instructions=f"Engage with {video_res.title} from {video_res.provider}.{ts_text}",
                estimated_minutes=video_res.estimated_minutes,
                status=status,
            ))
            act_order += 1

        doc_res = next((r for r in resources
                        if r.resource_type in ["NOTES", "DOCUMENT"]), None)
        if doc_res:
            sec_info = doc_res.document_sections[0] if doc_res.document_sections else None
            pg_text = (f" Study pages {sec_info.start_page}–{sec_info.end_page} "
                       f"covering '{sec_info.section_title}'.") if sec_info else " Read the essential concept summary."
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
                instructions=f"Review official notes from {doc_res.provider}.{pg_text}",
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
            instructions=f"Derive and solve foundational numericals and concept problems for {', '.join(unit.topics[:3])}.",
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
                instructions=f"Solve authentic university past question ({target_pyq.marks} marks): {target_pyq.question_text}",
                estimated_minutes=25,
                status=status,
            ))
        return activities

    # ------------------------------------------------------------------
    # Progression
    # ------------------------------------------------------------------

    async def get_current_plan(self, uid: str) -> Optional[CollegeLearningPlan]:
        raw = await self.store.get_college_learning_plan(uid)
        if raw:
            return CollegeLearningPlan(**raw)
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
            for phase in plan.phases:
                for act in phase.activities:
                    if act.activity_id == activity_id:
                        act.status = "COMPLETED"
                        act.completed_at = now
                        act.completion_evidence = (
                            completion_evidence or {"type": "STUDY_CONFIRMATION"})
                        found = True
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
