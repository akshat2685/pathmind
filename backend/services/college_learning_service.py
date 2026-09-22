"""
College Learning Plan & Phase Progression Service for PATHMIND College Engineering MVP.
Generates personalized, ordered activity sequences with concrete video timestamps,
reading pages, practice problems, authentic PYQs, and checkpoint assessments.
"""

from typing import List, Dict, Any, Optional
import uuid
from backend.core.college_schemas import (
    CollegeLearningPlan,
    CollegePlanPhase,
    CollegeActivity,
    ActivityType,
    EngineeringBranch,
    AcademicContext,
    CollegeGoal,
    ResourceRecord,
    PYQQuestionRecord
)
from backend.providers.curriculum_registry import (
    get_curriculum,
    get_resources_for_subject,
    get_pyqs_for_subject
)
from backend.services.store import FirestoreStore

class CollegeLearningService:
    def __init__(self, store: Optional[FirestoreStore] = None):
        self.store = store or FirestoreStore()

    async def generate_learning_plan(
        self,
        uid: str,
        goal_id: str,
        target_subject_code_or_id: Optional[str] = None
    ) -> CollegeLearningPlan:
        """
        Synthesizes an ordered, multi-phase learning plan for the student's current academic context.
        """
        raw_ctx = await self.store.get_college_academic_context(uid)
        if not raw_ctx:
            raise ValueError("ACADEMIC_CONTEXT_REQUIRED: Please complete academic onboarding first.")
        
        ctx = AcademicContext(**raw_ctx)
        curr = await get_curriculum(ctx.university_id, ctx.branch, ctx.semester)

        plan_id = f"plan_{uid}_{ctx.semester}_{uuid.uuid4().hex[:6]}"
        subject_scope = [target_subject_code_or_id] if target_subject_code_or_id else ctx.subjects

        # Find target subjects in curriculum
        matched_subjects = []
        if curr and curr.subjects:
            for s in curr.subjects:
                if not subject_scope or s.subject_id in subject_scope or s.code in subject_scope or s.name in subject_scope:
                    matched_subjects.append(s)
            if not matched_subjects:
                matched_subjects = curr.subjects[:2]
        
        phases: List[CollegePlanPhase] = []
        phase_order = 1
        
        from backend.core.config import settings
        import json
        
        gemini_available = bool(settings.GEMINI_API_KEY)
        model = None
        if gemini_available:
            try:
                import google.generativeai as genai
                genai.configure(api_key=settings.GEMINI_API_KEY)
                model = genai.GenerativeModel('gemini-2.5-flash')
            except Exception as e:
                print(f"Warning: Failed to initialize Gemini: {e}")

        for sub in matched_subjects:
            resources = await get_resources_for_subject(sub.subject_id)
            pyq_set = await get_pyqs_for_subject(ctx.university_id, sub.subject_id)
            pyq_questions = pyq_set.questions if pyq_set else []

            for unit in sub.units[:2]:  # Focus on primary active units
                phase_id = f"phase_{plan_id}_u{unit.unit}"
                activities: List[CollegeActivity] = []
                
                if model:
                    try:
                        res_summary = [{"id": r.resource_id, "type": r.resource_type, "title": r.title} for r in resources]
                        pyq_summary = [{"id": q.question_id, "text": q.question_text} for q in pyq_questions]
                        
                        prompt = f"""
You are the PATHMIND Study Planner. Create a personalized study sequence for a college student.
Subject: {sub.name}, Unit: {unit.title} (Topics: {', '.join(unit.topics)})
Available hours/week: {ctx.available_hours_per_week}

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
                        if text.startswith("```json"): text = text[7:]
                        if text.startswith("```"): text = text[3:]
                        if text.endswith("```"): text = text[:-3]
                        gen_activities = json.loads(text.strip())
                        
                        act_order = 1
                        for ga in gen_activities:
                            res = next((r for r in resources if r.resource_id == ga.get("resource_id")), None)
                            pyq = next((q for q in pyq_questions if q.question_id == ga.get("pyq_id")), None)
                            
                            act_type = ga.get("type", "PRACTICE")
                            if act_type not in [e.value for e in ActivityType]:
                                act_type = "PRACTICE"

                            activities.append(CollegeActivity(
                                activity_id=f"act_{phase_id}_{act_order}",
                                plan_id=plan_id,
                                phase_id=phase_id,
                                activity_type=ActivityType(act_type),
                                title=ga.get("title", f"{act_type} Activity"),
                                resource=res,
                                pyq_question=pyq,
                                order=act_order,
                                instructions=ga.get("instructions", "Follow the study plan."),
                                estimated_minutes=ga.get("minutes", 30),
                                status="AVAILABLE" if phase_order == 1 else "LOCKED"
                            ))
                            act_order += 1
                            
                    except Exception as e:
                        print(f"Gemini generation failed: {e}")
                        activities = [] # Fallback to static
                
                if not activities:
                    act_order = 1
                    # Activity 1: WATCH (Lecture section with exact timestamps)
                    video_res = next((r for r in resources if r.resource_type == "VIDEO"), None)
                    if video_res:
                        ts_info = video_res.video_timestamps[0] if video_res.video_timestamps else None
                        ts_text = f" Watch from {ts_info.start_seconds // 60}:00 to {ts_info.end_seconds // 60}:00 for '{ts_info.purpose}'." if ts_info else " Watch the core foundational module."
                        activities.append(CollegeActivity(
                            activity_id=f"act_{phase_id}_{act_order}",
                            plan_id=plan_id,
                            phase_id=phase_id,
                            activity_type=ActivityType.WATCH,
                            title=f"Watch Lecture: {unit.title}",
                            resource=video_res,
                            order=act_order,
                            instructions=f"Engage with {video_res.title} from {video_res.provider}.{ts_text}",
                            estimated_minutes=video_res.estimated_minutes,
                            status="AVAILABLE" if phase_order == 1 else "LOCKED"
                        ))
                        act_order += 1

                    # Activity 2: READ (Verified notes/textbook with page range)
                    doc_res = next((r for r in resources if r.resource_type in ["NOTES", "DOCUMENT"]), None)
                    if doc_res:
                        sec_info = doc_res.document_sections[0] if doc_res.document_sections else None
                        pg_text = f" Study pages {sec_info.start_page}–{sec_info.end_page} covering '{sec_info.section_title}'." if sec_info else " Read the essential concept summary."
                        activities.append(CollegeActivity(
                            activity_id=f"act_{phase_id}_{act_order}",
                            plan_id=plan_id,
                            phase_id=phase_id,
                            activity_type=ActivityType.READ,
                            title=f"Read Verified Notes: {unit.title}",
                            resource=doc_res,
                            order=act_order,
                            instructions=f"Review official notes from {doc_res.provider}.{pg_text}",
                            estimated_minutes=doc_res.estimated_minutes,
                            status="AVAILABLE" if phase_order == 1 else "LOCKED"
                        ))
                        act_order += 1

                    # Activity 3: PRACTICE (Concept formulation & problem solving)
                    activities.append(CollegeActivity(
                        activity_id=f"act_{phase_id}_{act_order}",
                        plan_id=plan_id,
                        phase_id=phase_id,
                        activity_type=ActivityType.PRACTICE,
                        title=f"Solve Practice Problems: {unit.topics[0] if unit.topics else unit.title}",
                        order=act_order,
                        instructions=f"Derive and solve foundational numericals and concept problems for {', '.join(unit.topics[:3])}.",
                        estimated_minutes=30,
                        status="AVAILABLE" if phase_order == 1 else "LOCKED"
                    ))
                    act_order += 1

                    # Activity 4: SOLVE_PYQ (Authentic past exam question if verified)
                    if pyq_questions:
                        target_pyq = pyq_questions[0]
                        activities.append(CollegeActivity(
                            activity_id=f"act_{phase_id}_{act_order}",
                            plan_id=plan_id,
                            phase_id=phase_id,
                            activity_type=ActivityType.SOLVE_PYQ,
                            title=f"Attempt University PYQ: {target_pyq.question_number}",
                            pyq_question=target_pyq,
                            order=act_order,
                            instructions=f"Solve authentic university past question ({target_pyq.marks} marks): {target_pyq.question_text}",
                            estimated_minutes=25,
                            status="AVAILABLE" if phase_order == 1 else "LOCKED"
                        ))
                        act_order += 1

                # Phase Definition
                phases.append(CollegePlanPhase(
                    phase_id=phase_id,
                    order=phase_order,
                    title=f"{sub.code}: {unit.title}",
                    objective=f"Master fundamental theories and exam problems for {sub.name} (Unit {unit.unit}).",
                    status="AVAILABLE" if phase_order == 1 else "LOCKED",
                    activities=activities,
                    assessment_id=f"asmt_{phase_id}"
                ))
                phase_order += 1

        plan = CollegeLearningPlan(
            plan_id=plan_id,
            uid=uid,
            goal_id=goal_id,
            subject_scope=subject_scope,
            phases=phases
        )

        await self.store.save_college_learning_plan(uid, plan.model_dump(mode="json"))
        return plan

    async def get_current_plan(self, uid: str) -> Optional[CollegeLearningPlan]:
        raw = await self.store.get_college_learning_plan(uid)
        if raw:
            return CollegeLearningPlan(**raw)
        return None

    async def complete_activity(
        self,
        uid: str,
        activity_id: str,
        completion_evidence: Optional[Dict[str, Any]] = None
    ) -> CollegeLearningPlan:
        """Marks activity complete and evaluates whether next activity or assessment unlocks."""
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
                    act.completion_evidence = completion_evidence or {"type": "STUDY_CONFIRMATION"}
                    found = True
                    break
            if found:
                # Check if all activities in this phase are complete
                if all(a.status == "COMPLETED" for a in phase.activities):
                    phase.status = "COMPLETED"
                    # Unlock next phase
                    next_idx = phase.order
                    if next_idx < len(plan.phases):
                        plan.phases[next_idx].status = "AVAILABLE"
                        for next_act in plan.phases[next_idx].activities:
                            next_act.status = "AVAILABLE"
                break

        if not found:
            raise ValueError("ACTIVITY_NOT_FOUND")

        await self.store.save_college_learning_plan(uid, plan.model_dump(mode="json"))
        return plan
