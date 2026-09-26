"""
College Agent Orchestrator for PATHMIND College Engineering MVP.
Conforms to TRD Section 4 & 23: RootLearnerAgent orchestrating Academic, Learning,
Assessment, and Accountability capabilities with Gemini reasoning and deterministic fallbacks.
"""

from typing import Dict, Any, List, Optional
import asyncio
import json
import logging
import re
from backend.core.config import settings
from backend.core.college_schemas import (
    EngineeringBranch,
    AcademicContext,
    CollegeActivity,
    TodaySchedule
)
from backend.services.academic_service import AcademicService
from backend.services.college_learning_service import CollegeLearningService
from backend.services.pyq_service import PYQService
from backend.services.college_accountability_service import CollegeAccountabilityService
from backend.services.college_memory_service import CollegeMemoryService
from backend.services.store import FirestoreStore

logger = logging.getLogger(__name__)

class CollegeOrchestrator:
    def __init__(self, store: Optional[FirestoreStore] = None):
        self.store = store or FirestoreStore()
        self.academic_service = AcademicService(self.store)
        self.learning_service = CollegeLearningService(self.store)
        self.pyq_service = PYQService()
        self.accountability_service = CollegeAccountabilityService(self.store)
        self.memory_service = CollegeMemoryService(self.store)

    async def _generate_mentor_reply(
        self,
        uid: str,
        user_message: str,
        ctx,
        pref_texts: List[str],
        countdown,
    ) -> Optional[str]:
        """
        Calls Gemini for the mentor reply with retries and backoff. Raises
        the last exception when all attempts fail so the caller can answer
        honestly instead of fabricating a reply. Returns None only when no
        model is configured (caller then reports unavailability).
        """
        from backend.core.gemini import get_gemini_model as _shared_model

        model = _shared_model()
        if model is None:
            return None

        from backend.services.proactive_memory_service import ProactiveMemoryService
        proactive_mem_service = ProactiveMemoryService(self.memory_service)

        # Fetch proactive memory context
        proactive_ctx = await proactive_mem_service.get_proactive_memory_context(
            uid, user_message)
        mems_context = ""
        for m in proactive_ctx.get("retrieved_memories", []):
            mems_context += f"[{m.get('memory_id')}] {m.get('title')}: {m.get('content')}\n"

        # Fetch today's schedule for deeper context
        today_schedule = await self.accountability_service.get_today_schedule(uid)
        active_tasks = [a.title for a in today_schedule.active_activities]

        prompt = f"""
        You are PATHMIND, an expert engineering-college academic mentor.
        Learner Context:
        - University: {ctx.university_name if ctx else 'Engineering College'}
        - Engineering Branch: {ctx.branch.value if ctx else 'General Engineering'}
        - Semester: {ctx.semester if ctx else 'Undergraduate'}
        - Active Subjects: {', '.join(ctx.subjects) if ctx else 'Core Engineering'}
        - Exam countdown: {countdown} days remaining
        - Known Learning Preferences: {'; '.join(pref_texts) if pref_texts else 'Standard technical explanations with examples'}
        - Active Tasks Today: {', '.join(active_tasks) if active_tasks else 'None currently planned'}

        Retrieved Memory Context:
        {mems_context if mems_context else "No specific past memories matched."}

        Student Query: "{user_message}"

        Respond concisely (2-4 sentences) with grounded, rigorous pedagogical advice matching their university curriculum and today's schedule. Use the retrieved memories to personalize the advice.
        If the question is not about academics, answer it briefly and honestly anyway — never reply with an empty message.

        If the user states a new durable preference, goal, or learning insight, append exactly one of the following JSON blocks to your output:
        ```json
        {{"action": "promote", "title": "Brief title", "content": "Detailed memory"}}
        ```
        OR if an old memory (provide its ID from context) is no longer valid:
        ```json
        {{"action": "supersede", "old_memory_id": "ID", "title": "New Title", "content": "New content"}}
        ```
        """
        from backend.core.gemini import generate_text_resilient, GeminiUnavailable

        try:
            # Resilient gateway (blocking): keep it off the event loop.
            # Absorbs per-minute throttling, fails fast on daily exhaustion,
            # optionally falls back to GEMINI_FALLBACK_MODEL. Raises
            # GeminiUnavailable on terminal failure so the caller answers
            # honestly instead of fabricating a reply.
            text = await asyncio.to_thread(
                generate_text_resilient, prompt, feature="mentor.reply")
        except GeminiUnavailable as exc:
            logger.error("Mentor LLM failed after retries: %s (quota_scope=%s)",
                         type(exc).__name__, exc.quota_scope)
            raise

        # Extract Memory Actions
        json_match = re.search(r'```json\n(.*?)\n```', text, re.DOTALL)
        if json_match:
            try:
                action_data = json.loads(json_match.group(1))
                if action_data.get("action") == "promote":
                    await proactive_mem_service.promote_to_long_term_memory(
                        uid, action_data.get("title", ""),
                        action_data.get("content", ""))
                elif action_data.get("action") == "supersede":
                    await proactive_mem_service.supersede_memory(
                        uid, action_data.get("old_memory_id", ""),
                        action_data.get("title", ""),
                        action_data.get("content", ""))
                text = text.replace(json_match.group(0), "").strip()
            except Exception as e:
                logger.warning(f"Failed to parse memory action: {e}")
        if not text:
            raise RuntimeError(
                "LLM response contained only a memory action block")
        return text

    async def interact(self, uid: str, user_message: str, session_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Processes learner message, retrieves academic context and memories,
        and produces structured UI blocks and recommended actions.
        """
        # 1. Fetch learner context & memories
        raw_ctx = await self.store.get_college_academic_context(uid)
        ctx = AcademicContext(**raw_ctx) if raw_ctx else None
        
        long_mems = await self.memory_service.get_long_term_memories(uid)
        pref_texts = [m.content for m in long_mems if m.memory_type == "LEARNING_PREFERENCE"]

        raw_plan = await self.learning_service.get_current_plan(uid)
        countdown = await self.accountability_service.calculate_exam_countdown(uid)

        # 2. Record short term session memory
        if session_id:
            await self.memory_service.record_short_term_context(
                uid=uid,
                session_id=session_id,
                content=f"Learner asked: {user_message}"
            )

        # 3. Check for specific subject or PYQ intent
        msg_lower = user_message.lower()
        if "pyq" in msg_lower or "previous year" in msg_lower or "past paper" in msg_lower:
            if not ctx:
                return {
                    "message": "I need your academic context (university, branch, semester) before I can look up previous year questions. Please complete onboarding first.",
                    "state": "NEEDS_CONTEXT",
                    "ui_blocks": [
                        {
                            "type": "NEXT_ACTION",
                            "data": {
                                "label": "Complete academic setup",
                                "action": "OPEN_ONBOARDING"
                            }
                        }
                    ],
                    "sources": []
                }
            subject_ids = await self.store.get_context_subject_ids(ctx.context_id)
            if not subject_ids:
                return {
                    "message": "Your academic context has no subjects linked yet, so I can't look up previous year questions.",
                    "state": "NEEDS_CONTEXT",
                    "ui_blocks": [
                        {
                            "type": "NEXT_ACTION",
                            "data": {
                                "label": "Update academic context",
                                "action": "OPEN_ONBOARDING"
                            }
                        }
                    ],
                    "sources": []
                }
            sub_id = subject_ids[0]
            pyq_result = await self.pyq_service.get_pyqs(ctx.university_id, sub_id)

            if pyq_result.get("status") == "PYQ_NOT_AVAILABLE":
                return {
                    "message": pyq_result.get("message") or "Verified previous year questions are currently unavailable for this subject.",
                    "state": "PYQ_REVIEW",
                    "ui_blocks": [
                        {
                            "type": "NEXT_ACTION",
                            "data": {
                                "label": "Continue studying",
                                "action": "OPEN_DASHBOARD"
                            }
                        }
                    ],
                    "sources": []
                }

            pyq_set = pyq_result.get("pyq_set") or {}
            sources = [pyq_set["source_id"]] if isinstance(pyq_set, dict) and pyq_set.get("source_id") else []
            return {
                "message": f"Here are the verified previous year questions for {sub_id}.",
                "state": "PYQ_REVIEW",
                "ui_blocks": [
                    {
                        "type": "PYQ_VIEW",
                        "data": pyq_result
                    },
                    {
                        "type": "NEXT_ACTION",
                        "data": {
                            "label": "Attempt Question 1",
                            "action": "SOLVE_PYQ"
                        }
                    }
                ],
                "sources": sources
            }

        # 4. Generate intelligent guidance with Gemini if configured.
        # Retried with backoff: a transient rate-limit must not silently
        # degrade into a fabricated "roadmap" summary. If the LLM is truly
        # unreachable we say so honestly (state ERROR) instead of inventing
        # a reply the model never wrote.
        ai_response_text = None
        mentor_error = False
        if settings.GEMINI_API_KEY:
            try:
                ai_response_text = await self._generate_mentor_reply(
                    uid, user_message, ctx, pref_texts, countdown)
            except Exception as e:
                logger.error("Mentor LLM failed after retries: %s",
                             str(e), exc_info=True)
                log_event("college.mentor.llm_failed", user_id=uid,
                          outcome="error", error_code=type(e).__name__)
                mentor_error = True

        if mentor_error or not (ai_response_text or "").strip():
            return {
                "message": ("The AI mentor is temporarily unavailable "
                            "(the language service could not be reached). "
                            "Your study plan, assessments and PYQs below are "
                            "unaffected — please try asking again in a moment. "
                            "Nothing was fabricated in place of the answer."),
                "state": "ERROR",
                "ui_blocks": [
                    {
                        "type": "NEXT_ACTION",
                        "data": {
                            "label": "Retry your question",
                            "action": "OPEN_MENTOR"
                        }
                    }
                ],
                "sources": []
            }

        ai_response_text = ai_response_text.strip()

        # Compile active steps
        steps = []
        subject_ids = await self.store.get_context_subject_ids(ctx.context_id) if ctx else []
        if raw_plan and raw_plan.phases:
            for act in raw_plan.phases[0].activities[:3]:
                steps.append({
                    "title": act.title,
                    "activity_type": act.activity_type.value,
                    "status": act.status,
                    "instructions": act.instructions
                })

        return {
            "message": ai_response_text,
            "state": "LEARNING",
            "ui_blocks": [
                {
                    "type": "LEARNING_PLAN",
                    "data": {
                        "subject": subject_ids[0] if subject_ids else "Core Engineering",
                        "steps": steps
                    }
                },
                {
                    "type": "NEXT_ACTION",
                    "data": {
                        "label": "Continue Study Session",
                        "action": "START_ACTIVITY"
                    }
                }
            ],
            # No verified sources back this generic reply — never claim any.
            "sources": []
        }
