"""
College Assessment & Checkpoint Evaluation Service for PATHMIND College Engineering MVP.

Generates checkpoint assessments (tied to a learning-plan phase) and diagnostic
assessments (onboarding baseline, not tied to any phase).

Grading honesty rules (TRD §16):
  - MCQ: deterministic exact-match scoring (see college_rules.score_mcq_answer).
  - Short answer with a reference answer: deterministic exact match.
  - Short answer with a rubric: graded by the LLM with structured reasoning
    (grade_short_answer_with_llm) — never by answer length.
  - Short answer with neither: flagged requires_review; never auto-graded.
  - evaluation_confidence is a coarse band (never false precision).
  - Every result updates the per-topic mastery store, which the phase
    unlock_rule gates on.
"""

from dataclasses import dataclass
from typing import List, Dict, Any, Optional
import asyncio
import json
import uuid
from datetime import datetime, timezone

from backend.core.college_schemas import (
    AssessmentKind,
    CollegeAssessment,
    CollegeAssessmentQuestion,
    CollegeAssessmentSubmission,
    CollegeAssessmentResult,
    LearningSignal,
    MasteryStatus,
    TopicMasteryRecord,
)
from backend.core.college_rules import (
    CONFIDENCE_DETERMINISTIC,
    CONFIDENCE_HIGH,
    CONFIDENCE_MEDIUM,
    CONFIDENCE_LOW,
    determine_mastery,
    grade_short_answer_exact_match,
    score_mcq_answer,
    topic_outcome_from_ratio,
)
from backend.core.college_logging import log_event, timed_stage
from backend.services.store import FirestoreStore


@dataclass
class ShortAnswerGrade:
    """Structured LLM judgement for one short answer. Coarse by design."""
    score: float            # 0..marks, rounded to 1 decimal
    confidence: str         # "high" | "medium" | "low"
    reasoning: str          # 1-2 sentences: what earned / lost marks


def _get_gemini_model():
    """
    Returns a configured Gemini model, or None when unavailable.
    Delegates to the shared accessor so the model id stays centralized
    (settings.GEMINI_MODEL). No LLM call ever happens inside college_rules.
    """
    from backend.core.gemini import get_gemini_model as _shared
    return _shared()


async def grade_short_answer_with_llm(
    *,
    question_text: str,
    rubric: Optional[str],
    reference_answer: Optional[str],
    student_answer: str,
    marks: float,
    model,
) -> ShortAnswerGrade:
    """
    Grade one short answer with the LLM using structured reasoning.

    This is the ONLY place short-answer judgement happens; deterministic code
    never calls it implicitly. Raises on failure so callers fall back honestly
    (requires_review) instead of inventing a score.
    """
    prompt = f"""You are grading a college engineering short-answer response.
Grade ONLY what the rubric supports. Do not inflate scores and do not reward
length, formatting, or confidence of tone.

Question: {question_text}
Rubric: {rubric or "N/A"}
Reference answer (if any): {reference_answer or "N/A"}
Student answer: {student_answer if student_answer.strip() else "(blank)"}
Maximum marks: {marks}

Return ONLY a JSON object, no other text:
{{"score": <number from 0 to {marks}>, "confidence": "high|medium|low", "reasoning": "<1-2 sentences: which rubric points were met or missed>"}}"""
    response = await asyncio.to_thread(model.generate_content, prompt)
    text = response.text.strip()
    if text.startswith("```"):
        text = text.strip("`")
        if text.lower().startswith("json"):
            text = text[4:]
    data = json.loads(text.strip())
    score = max(0.0, min(float(marks), float(data.get("score", 0.0))))
    confidence = str(data.get("confidence", "low")).lower()
    if confidence not in ("high", "medium", "low"):
        confidence = "low"
    reasoning = str(data.get("reasoning", "")).strip()[:500]
    # Coarse score on purpose: never false precision.
    return ShortAnswerGrade(score=round(score, 1), confidence=confidence,
                            reasoning=reasoning)


_CONFIDENCE_TO_FLOAT = {
    "high": CONFIDENCE_HIGH,
    "medium": CONFIDENCE_MEDIUM,
    "low": CONFIDENCE_LOW,
}


class CollegeAssessmentService:
    def __init__(self, store: Optional[FirestoreStore] = None):
        self.store = store or FirestoreStore()

    @staticmethod
    def _generate_content_or_unavailable(model, prompt: str, feature: str):
        """
        Calls model.generate_content, converting ANY provider failure
        (retired model id, bad key, quota, network) into an honest
        ValueError the route maps to 503 — never a bare 500.
        """
        try:
            return model.generate_content(prompt)
        except Exception as exc:
            log_event(f"college.assessment.{feature.lower()}_llm_failed",
                      outcome="error", error_code=type(exc).__name__)
            raise ValueError(
                f"{feature}_UNAVAILABLE: the AI service could not be reached "
                f"({type(exc).__name__}); try again later instead of "
                f"receiving invented questions")

    # ------------------------------------------------------------------
    # Generation
    # ------------------------------------------------------------------

    async def generate_phase_assessment(
        self,
        uid: str,
        plan_id: str,
        phase_id: str,
        subject_id: str,
        topic_title: str,
        topics: Optional[List[str]] = None,
    ) -> CollegeAssessment:
        """
        Creates a checkpoint assessment for one learning-plan phase.
        Questions are tagged round-robin over `topics` so results feed the
        per-topic mastery store at topic granularity.
        """
        with timed_stage("college.assessment.checkpoint_generated", user_id=uid,
                         phase_id=phase_id):
            assessment_id = f"asmt_{phase_id}_{uuid.uuid4().hex[:4]}"
            topic_tags = topics or [topic_title]

            model = _get_gemini_model()
            questions = self._generate_questions_with_llm(
                model, subject_id, topic_title, topic_tags
            )
            if not questions:
                questions = self._static_fallback_questions(topic_title, topic_tags)

            assessment = CollegeAssessment(
                assessment_id=assessment_id,
                user_id=uid,
                plan_id=plan_id,
                phase_id=phase_id,
                subject_id=subject_id,
                assessment_kind=AssessmentKind.CHECKPOINT,
                title=f"Checkpoint Assessment: {topic_title}",
                questions=questions,
                status="AVAILABLE",
            )
            await self.store.save_college_assessment(
                uid, assessment.model_dump(mode="json"))
            log_event("college.assessment.checkpoint_saved", user_id=uid,
                      assessment_id=assessment_id,
                      question_count=len(questions), outcome="ok")
            return assessment

    async def generate_diagnostic_assessment(self, uid: str) -> CollegeAssessment:
        """
        Onboarding diagnostic: generated from the learner's aspirations, branch
        and subjects. NOT tied to any learning-plan phase (plan_id/phase_id
        stay None — never a fake linkage). Requires an LLM; without one we
        report honest unavailability instead of inventing questions.
        """
        with timed_stage("college.assessment.diagnostic_generated", user_id=uid):
            raw_profile = await self.store.get_college_user_profile(uid)
            if not raw_profile:
                raise ValueError(
                    "PROFILE_NOT_FOUND: complete onboarding before diagnostics")
            profile = (raw_profile if isinstance(raw_profile, dict)
                       else raw_profile.model_dump())

            raw_ctx = await self.store.get_college_academic_context(uid)
            subject_ids: List[str] = []
            if raw_ctx:
                subject_ids = await self.store.get_context_subject_ids(
                    raw_ctx.get("context_id"))

            raw_goal = await self.store.get_college_goal(uid)
            aspirations = ""
            if raw_goal:
                aspirations = (raw_goal.get("raw_goal")
                               or raw_goal.get("normalized_goal") or "")

            branch = profile.get("supported_path") or "GENERAL_OTHER"

            model = _get_gemini_model()
            if model is None:
                raise ValueError(
                    "DIAGNOSTIC_UNAVAILABLE: an AI question author "
                    "is required to build an honest diagnostic; refusing to "
                    "invent generic questions")

            prompt = f"""You are the PATHMIND Diagnostic Author. Write a short
baseline diagnostic for a college engineering learner.

Branch: {branch}
Subjects: {', '.join(subject_ids) if subject_ids else 'general engineering foundations'}
Learner aspirations: {aspirations or 'not stated'}

Return ONLY a JSON array of exactly 5 questions: 3 MCQ and 2 SHORT_ANSWER,
spread across the subjects above. Each item:
{{"id": "dq1", "text": "...", "type": "MCQ|SHORT_ANSWER",
  "options": ["A","B","C","D"], "answer": "B",
  "rubric": "for SHORT_ANSWER: what earns marks", "marks": 5,
  "topic": "short topic label", "subject_id": "<one of the subjects above>"}}
MCQs must include "options" and "answer". SHORT_ANSWER must include "rubric".
Never invent subject ids; use only the subjects listed."""
            response = self._generate_content_or_unavailable(
                model, prompt, "DIAGNOSTIC")
            text = response.text.strip()
            if text.startswith("```"):
                text = text.strip("`")
                if text.lower().startswith("json"):
                    text = text[4:]
            try:
                gen_qs = json.loads(text.strip())
            except Exception as exc:
                raise ValueError(
                    "DIAGNOSTIC_UNAVAILABLE: could not parse "
                    f"authored questions ({type(exc).__name__})")

            questions = []
            for i, gq in enumerate(gen_qs, start=1):
                questions.append(CollegeAssessmentQuestion(
                    question_id=gq.get("id", f"dq{i}"),
                    question_text=gq.get("text", "Question"),
                    question_type=gq.get("type", "MCQ"),
                    options=gq.get("options", []),
                    correct_answer=gq.get("answer"),
                    rubric=gq.get("rubric"),
                    topic=gq.get("topic") or (subject_ids[(i - 1) % len(subject_ids)]
                                              if subject_ids else "general"),
                    marks=gq.get("marks", 5),
                ))

            assessment = CollegeAssessment(
                assessment_id=f"diag_{uuid.uuid4().hex[:6]}",
                user_id=uid,
                plan_id=None,
                phase_id=None,
                subject_id=subject_ids[0] if subject_ids else None,
                assessment_kind=AssessmentKind.DIAGNOSTIC,
                title=f"Diagnostic Assessment: {branch.replace('_', ' ').title()}",
                questions=questions,
                status="AVAILABLE",
            )
            await self.store.save_college_assessment(
                uid, assessment.model_dump(mode="json"))
            log_event("college.assessment.diagnostic_saved", user_id=uid,
                      assessment_id=assessment.assessment_id,
                      question_count=len(questions),
                      subject_count=len(subject_ids), outcome="ok")
            return assessment

    def _generate_questions_with_llm(
        self, model, subject_id: str, topic_title: str, topic_tags: List[str]
    ) -> List[CollegeAssessmentQuestion]:
        if model is None:
            return []
        try:
            prompt = f"""
You are the PATHMIND Assessment Generator.
Create a short diagnostic checkpoint assessment for a college engineering student.
Subject ID: {subject_id}
Topic/Phase Title: {topic_title}

Return ONLY a valid JSON array of exactly 3 questions in this format:
[{{
    "id": "q1",
    "text": "The actual question text...",
    "type": "MCQ",
    "options": ["Option A", "Option B", "Option C", "Option D"],
    "answer": "Option B",
    "marks": 5
}},
{{
    "id": "q3",
    "text": "A short answer explanation question...",
    "type": "SHORT_ANSWER",
    "rubric": "Rubric for grading",
    "marks": 10
}}]
Make the first two MCQs and the last one SHORT_ANSWER.
"""
            response = model.generate_content(prompt)
            text = response.text.strip()
            if text.startswith("```json"):
                text = text[7:]
            if text.startswith("```"):
                text = text[3:]
            if text.endswith("```"):
                text = text[:-3]
            gen_qs = json.loads(text.strip())
            questions = []
            for i, gq in enumerate(gen_qs, start=1):
                questions.append(CollegeAssessmentQuestion(
                    question_id=gq.get("id", f"q{i}"),
                    question_text=gq.get("text", "Question"),
                    question_type=gq.get("type", "MCQ"),
                    options=gq.get("options", []),
                    correct_answer=gq.get("answer"),
                    rubric=gq.get("rubric"),
                    topic=topic_tags[(i - 1) % len(topic_tags)],
                    marks=gq.get("marks", 5),
                ))
            return questions
        except Exception as exc:
            log_event("college.assessment.generation_failed", outcome="error",
                      error_code=type(exc).__name__)
            return []

    @staticmethod
    def _static_fallback_questions(
        topic_title: str, topic_tags: List[str]
    ) -> List[CollegeAssessmentQuestion]:
        tag = lambda i: topic_tags[i % len(topic_tags)]
        return [
            CollegeAssessmentQuestion(
                question_id="q1",
                question_text=f"Which core theorem or principle forms the theoretical basis of {topic_title}?",
                question_type="MCQ",
                options=[
                    "Conservation of Energy & Mass Equilibrium",
                    "Second-Order Differential Continuity",
                    "Direct Algebraic Proportionality",
                    "Unconstrained Dynamic Convergence",
                ],
                correct_answer="Conservation of Energy & Mass Equilibrium",
                topic=tag(0),
                marks=5,
            ),
            CollegeAssessmentQuestion(
                question_id="q2",
                question_text=f"When analyzing {topic_title}, what primary trade-off must be managed under real-world constraints?",
                question_type="MCQ",
                options=[
                    "Efficiency vs Stability under transient load conditions",
                    "Memory address alignment vs static clock cycles",
                    "Nominal resistance vs dielectric breakdown",
                    "Tensile capacity vs plastic shear failure",
                ],
                correct_answer="Efficiency vs Stability under transient load conditions",
                topic=tag(1),
                marks=5,
            ),
            CollegeAssessmentQuestion(
                question_id="q3",
                question_text=f"Explain how you would detect and correct a boundary error or numerical divergence when applying {topic_title}.",
                question_type="SHORT_ANSWER",
                rubric="Evaluates understanding of initial boundary conditions, tolerance limits, and validation steps.",
                topic=tag(2),
                marks=10,
            ),
        ]

    # ------------------------------------------------------------------
    # Evaluation
    # ------------------------------------------------------------------

    async def evaluate_submission(
        self,
        uid: str,
        submission: CollegeAssessmentSubmission,
    ) -> CollegeAssessmentResult:
        """
        Grades a submission, updates the per-topic mastery store, records a
        learning signal on reinforcement need, and evaluates phase unlocks on
        demonstrated mastery (never on mere activity completion).
        """
        with timed_stage("college.assessment.evaluated", user_id=uid,
                         assessment_id=submission.assessment_id):
            raw_asmt = await self.store.get_college_assessment(
                uid, submission.assessment_id)
            if not raw_asmt:
                raise ValueError("ASSESSMENT_NOT_FOUND")

            assessment = CollegeAssessment(**raw_asmt)
            total_marks = sum(float(q.marks or 0) for q in assessment.questions)
            earned_marks = 0.0
            topic_results: List[Dict[str, Any]] = []
            confidences: List[float] = []

            for q in assessment.questions:
                student_ans = (submission.answers.get(q.question_id) or "").strip()
                marks = float(q.marks or 0)

                if q.question_type == "MCQ":
                    item_score = score_mcq_answer(
                        student_ans, q.correct_answer, marks)
                    confidence: Optional[float] = CONFIDENCE_DETERMINISTIC
                    requires_review = False
                    reasoning = "Deterministic exact-match scoring."
                else:
                    (item_score, confidence, requires_review,
                     reasoning) = await self._grade_short_answer(q, student_ans)

                earned_marks += item_score
                if confidence is not None:
                    confidences.append(confidence)
                topic_results.append({
                    "question_id": q.question_id,
                    "topic": q.topic,
                    "earned_marks": round(item_score, 1),
                    "total_marks": marks,
                    "status": ("STRONG" if item_score >= marks * 0.7
                               else "NEEDS_WORK"),
                    "requires_review": requires_review,
                    "confidence": confidence,
                    "reasoning": reasoning,
                })

            percentage = (earned_marks / total_marks * 100) if total_marks > 0 else 0.0
            normalized = round(percentage / 100.0, 2)
            mastery = determine_mastery(percentage)

            if mastery == MasteryStatus.MASTERED.value:
                feedback = (f"Outstanding grasp of {assessment.title}. "
                            f"Ready to advance to subsequent syllabus phases.")
            elif mastery == MasteryStatus.PARTIALLY_MASTERED.value:
                feedback = ("Acceptable foundational comprehension, but additional "
                            "problem-solving practice is advised on specific topics.")
            else:
                feedback = ("Key conceptual gaps observed. Targeted review of the "
                            "lecture and notes is recommended prior to advancing.")

            # Coarse aggregate confidence: weakest link, never false precision.
            evaluation_confidence = (round(min(confidences), 2)
                                     if confidences else None)

            result = CollegeAssessmentResult(
                result_id=f"res_{submission.assessment_id}_{uuid.uuid4().hex[:4]}",
                assessment_id=submission.assessment_id,
                user_id=uid,
                score=round(percentage, 1),
                normalized_score=normalized,
                mastery_status=mastery,
                feedback=feedback,
                topic_results=topic_results,
                evaluation_confidence=evaluation_confidence,
                created_at=datetime.now(timezone.utc).isoformat(),
            )
            await self.store.save_college_assessment_result(
                uid, result.model_dump(mode="json"))
            log_event("college.assessment.result_saved", user_id=uid,
                      result_id=result.result_id, mastery_status=mastery,
                      score=round(percentage, 1),
                      evaluation_confidence=evaluation_confidence,
                      outcome="ok")

            # Feed the per-topic mastery store (drives unlocks + baseline).
            await self._update_topic_mastery_from_result(
                uid, assessment, topic_results, result.result_id)

            # Ingest learning signal + mastery if reinforcement is needed.
            if mastery == MasteryStatus.REINFORCEMENT_REQUIRED.value:
                signal = LearningSignal(
                    signal_id=f"sig_{uuid.uuid4().hex[:6]}",
                    user_id=uid,
                    signal_type="CONCEPT_GAP_DETECTED",
                    subject_id=assessment.subject_id,
                    topic_id=assessment.title,
                    description=(f"Struggled on checkpoint assessment for "
                                 f"{assessment.title} (Score: {percentage}%)."),
                    recommended_intervention=("Schedule spaced revision and targeted "
                                              "worked examples before proceeding to PYQs."),
                )
                await self.store.save_learning_signal(
                    uid, signal.model_dump(mode="json"))
                await self._apply_signal_to_mastery(uid, signal)

            # Mastery-gated phase unlock (checkpoints only; diagnostics are
            # not tied to phases).
            if (assessment.assessment_kind == AssessmentKind.CHECKPOINT
                    and assessment.phase_id):
                from backend.services.college_learning_service import (
                    CollegeLearningService,
                )
                learning_service = CollegeLearningService(self.store)
                await learning_service.maybe_unlock_next_phase(uid, assessment)

            return result

    async def _grade_short_answer(
        self, question: CollegeAssessmentQuestion, student_answer: str
    ):
        """
        Returns (score, confidence|None, requires_review, reasoning).

        Never grades on answer length. Uses the LLM with structured reasoning
        when a rubric exists; otherwise falls back honestly to exact match or
        requires_review.
        """
        marks = float(question.marks or 0)
        if question.correct_answer:
            score, requires_review = grade_short_answer_exact_match(
                student_answer, question.correct_answer, marks)
            if not requires_review:
                return (score, CONFIDENCE_DETERMINISTIC, False,
                        "Exact match against the reference answer.")
            # Not an exact match: a thoughtful free-text answer must never be
            # auto-scored as zero. Grade it against the reference answer with
            # the LLM; if that fails, flag for human review instead of a 0.
            model = _get_gemini_model()
            if model is not None:
                try:
                    grade = await grade_short_answer_with_llm(
                        question_text=question.question_text,
                        rubric=question.rubric,
                        reference_answer=question.correct_answer,
                        student_answer=student_answer,
                        marks=marks,
                        model=model,
                    )
                    return (grade.score,
                            _CONFIDENCE_TO_FLOAT[grade.confidence],
                            False, grade.reasoning)
                except Exception as exc:
                    log_event("college.assessment.llm_grading_failed",
                              outcome="error", error_code=type(exc).__name__)
            return (0.0, None, True,
                    "Free-text answer did not match the reference answer and "
                    "AI grading was unavailable; flagged for human review "
                    "instead of auto-scoring zero.")

        if question.rubric:
            model = _get_gemini_model()
            if model is not None:
                try:
                    grade = await grade_short_answer_with_llm(
                        question_text=question.question_text,
                        rubric=question.rubric,
                        reference_answer=None,
                        student_answer=student_answer,
                        marks=marks,
                        model=model,
                    )
                    return (grade.score,
                            _CONFIDENCE_TO_FLOAT[grade.confidence],
                            False, grade.reasoning)
                except Exception as exc:
                    log_event("college.assessment.llm_grading_failed",
                              outcome="error", error_code=type(exc).__name__)

        return (0.0, None, True,
                "No reference answer or rubric and no grading model available; "
                "flagged for human review instead of auto-grading.")

    async def _update_topic_mastery_from_result(
        self,
        uid: str,
        assessment: CollegeAssessment,
        topic_results: List[Dict[str, Any]],
        result_id: str,
    ) -> None:
        """Upsert per-topic mastery from graded evidence. Never invents."""
        existing = await self.store.get_topic_masteries(uid)
        for tr in topic_results:
            topic = tr.get("topic") or "general"
            total = float(tr.get("total_marks") or 0)
            if tr.get("requires_review") or total <= 0:
                ratio: Optional[float] = None
            else:
                ratio = max(0.0, min(1.0, float(tr.get("earned_marks") or 0) / total))
            outcome = topic_outcome_from_ratio(ratio)

            if ratio is None:
                # No gradable evidence: record the gap only if we knew nothing.
                if any(r.get("topic") == topic
                       and r.get("subject_id") == assessment.subject_id
                       for r in existing):
                    continue
                record = TopicMasteryRecord(
                    user_id=uid,
                    subject_id=assessment.subject_id,
                    topic=topic,
                    mastery_score=0.0,
                    outcome=outcome,  # INSUFFICIENT_EVIDENCE
                    evidence_ref=result_id,
                )
            else:
                record = TopicMasteryRecord(
                    user_id=uid,
                    subject_id=assessment.subject_id,
                    topic=topic,
                    mastery_score=round(ratio, 3),
                    outcome=outcome,
                    evidence_ref=result_id,
                )
            await self.store.upsert_topic_mastery(uid, record.model_dump(mode="json"))
        log_event("college.mastery.updated_from_assessment", user_id=uid,
                  result_id=result_id, topic_count=len(topic_results),
                  outcome="ok")

    async def _apply_signal_to_mastery(
        self, uid: str, signal: LearningSignal
    ) -> None:
        """A CONCEPT_GAP signal marks the topic REINFORCEMENT_REQUIRED."""
        topic = signal.topic_id or "general"
        existing = await self.store.get_topic_masteries(uid)
        prior = next(
            (r for r in existing
             if r.get("topic") == topic and r.get("subject_id") == signal.subject_id),
            None,
        )
        record = TopicMasteryRecord(
            user_id=uid,
            subject_id=signal.subject_id,
            topic=topic,
            mastery_score=float(prior.get("mastery_score", 0.0)) if prior else 0.0,
            outcome=MasteryStatus.REINFORCEMENT_REQUIRED.value,
            evidence_ref=signal.signal_id,
        )
        await self.store.upsert_topic_mastery(uid, record.model_dump(mode="json"))
        log_event("college.mastery.updated_from_signal", user_id=uid,
                  signal_id=signal.signal_id, topic=topic, outcome="ok")
