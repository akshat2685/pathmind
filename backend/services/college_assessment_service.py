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
from typing import List, Dict, Any, Optional, Tuple
import asyncio
import json
import re
import time
import uuid
from datetime import datetime, timezone

from backend.core.college_schemas import (
    coerce_model,
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
from backend.core.gemini import generate_fast
from backend.services.store import FirestoreStore


@dataclass
class ShortAnswerGrade:
    """Structured LLM judgement for one short answer. Coarse by design."""
    score: float            # 0..marks, rounded to 1 decimal
    confidence: str         # "high" | "medium" | "low"
    reasoning: str          # 1-2 sentences: what earned / lost marks


def _get_gemini_model(purpose: str = "direct"):
    """
    Returns a configured model wrapper, or None when unavailable.
    Delegates to the shared accessor (backend.core.llm) so model ids
    stay centralized per task pool (settings.GROQ_MODEL_*). The
    function name is legacy — the provider is Groq. The TypeError
    fallback keeps no-arg test doubles (which patch the shared
    accessor) working unchanged.
    """
    from backend.core.gemini import get_gemini_model as _shared
    try:
        return _shared(purpose)
    except TypeError:
        return _shared()


def _get_light_model():
    """
    Grading-pool model (short answers: small outputs, huge free pool).
    Tolerates no-arg test doubles patched over _get_gemini_model —
    those predate purpose routing.
    """
    try:
        return _get_gemini_model("light")
    except TypeError:
        return _get_gemini_model()


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
    response = await asyncio.to_thread(generate_fast, model, prompt, 512)
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
    def _generate_content_or_unavailable(model, prompt: str, feature: str,
                                         max_output_tokens: int = 2048):
        """
        Calls model.generate_content, converting ANY provider failure
        (retired model id, bad key, quota, network) into an honest
        ValueError the route maps to 503 — never a bare 500.
        """
        try:
            return generate_fast(model, prompt, max_output_tokens)
        except Exception as exc:
            # Log both the exception type AND message (truncated) so
            # operators can distinguish 404 (retired model) from 429
            # (quota) from 400 (bad key) in Vercel logs. Previously only
            # the type was logged, making diagnosis impossible.
            exc_msg = str(exc)[:500] if str(exc) else "(no message)"
            log_event(f"college.assessment.{feature.lower()}_llm_failed",
                      outcome="error", error_code=type(exc).__name__,
                      error_message=exc_msg)
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
            # Provenance (AJ's verifiability rule): checkpoint questions
            # are model-authored when the direct Groq call produced them and
            # static otherwise — stamp it like the diagnostic/plan do
            # (this was null in the DB before round 12).
            authored_by = "groq_direct"
            if not questions:
                questions = self._static_fallback_questions(topic_title, topic_tags)
                authored_by = "static_fallback"

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
                authored_by=authored_by,
            )
            await self.store.save_college_assessment(
                uid, assessment.model_dump(mode="json"))
            log_event("college.assessment.checkpoint_saved", user_id=uid,
                      assessment_id=assessment_id,
                      question_count=len(questions), outcome="ok")
            return assessment

    async def generate_diagnostic_assessment(self, uid: str) -> CollegeAssessment:
        """
        Diagnostic authored by the ADK assessment agent on hybrid-RAG
        evidence (round 7; AJ's corrected spec — Gemini AUTHORS,
        retrieval GROUNDS):

          learner context -> verified-source retrieval (curriculum /
          PYQs / resources / prior mastery) -> the assessment agent's
          one-shot generation drafts ~10 probes and selects 5-6 against
          that evidence (strictly validated; verified_* claims are
          downgraded when retrieval lacks the material) -> verified PYQs
          fill any topic the authored set left uncovered -> assessment.

        Honest fallback chain, each step labeled in `authored_by`:
        ADK generation ("adk:assessment_agent") -> direct Groq call
        ("groq_direct") when the ADK seam fails -> the round-6
        grounded assembly of real verified PYQs + curriculum probes
        ("rag_fallback") when no LLM authored anything. Short answers
        without a rubric grade as INSUFFICIENT_EVIDENCE (Unknown),
        never a fake score. Only a learner with no profile raises;
        only a learner whose final set still has <3 questions gets an
        honest DIAGNOSTIC_UNAVAILABLE — questions are never invented.
        """
        with timed_stage("college.assessment.diagnostic_generated", user_id=uid):
            raw_profile = await self.store.get_college_user_profile(uid)
            if not raw_profile:
                raise ValueError(
                    "PROFILE_NOT_FOUND: complete onboarding before diagnostics")
            profile = (raw_profile if isinstance(raw_profile, dict)
                       else raw_profile.model_dump())

            from backend.services.college_diagnostic_retrieval import (
                retrieve_diagnostic_context,
            )
            retrieval = await retrieve_diagnostic_context(self.store, uid)
            subject_ids = (retrieval.subject_ids
                           or retrieval.context_subject_ids)
            branch = retrieval.branch or profile.get(
                "supported_path") or "GENERAL_OTHER"

            # Round 7 (AJ's corrected spec): the ADK assessment agent
            # is the primary AUTHOR, writing against the hybrid-RAG
            # evidence above; real verified PYQs then fill topics the
            # authored set left uncovered (never displacing authored
            # questions). The round-6 grounded assembly (PYQs + probes)
            # is now the FALLBACK for when no LLM authored anything.
            authored: List[CollegeAssessmentQuestion] = []
            llm_via: Optional[str] = None
            model = _get_gemini_model()
            try:
                authored, llm_via = await self._generate_diagnostic_with_llm(
                    model, profile, retrieval)
            except ValueError as exc:
                # ADK + direct model both failed or produced unusable
                # output: the grounded fallback ships instead of the
                # old hard failure.
                log_event(
                    "college.assessment.diagnostic_llm_fallback",
                    user_id=uid, outcome="degraded",
                    error_code=str(exc)[:120])
                authored, llm_via = [], None

            if len(authored) >= 3:
                # The LLM-authored set is the diagnostic (>=3 valid
                # questions): keep it intact and fill uncovered topics
                # with real verified PYQs up to 6.
                questions = list(authored)
                covered = {str(q.topic or "").strip().lower()
                           for q in questions}
                for q in self._rag_pyq_questions(retrieval):
                    if len(questions) >= 6:
                        break
                    key = str(q.topic or "").strip().lower()
                    if not key or key in covered:
                        continue
                    questions.append(q)
                    covered.add(key)
                authored_by = ("adk:assessment_agent" if llm_via == "adk"
                               else "groq_direct")
            else:
                # No LLM authored anything usable: ship the grounded
                # round-6 assembly, honestly labeled.
                if authored:
                    log_event(
                        "college.assessment.diagnostic_llm_insufficient",
                        user_id=uid, question_count=len(authored),
                        outcome="degraded")
                questions = self._fallback_diagnostic_questions(retrieval)
                authored_by = "rag_fallback"
            questions = questions[:6]

            if len(questions) < 3:
                raise ValueError(
                    "DIAGNOSTIC_UNAVAILABLE: no verified curriculum or PYQ "
                    "material covers this learner yet and the AI question "
                    "author is unavailable; refusing to invent questions")

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
                authored_by=authored_by,
            )
            # Provenance is a payload field (above) AND a log line named
            # after the agent that ran: mode says "adk" ONLY when the
            # ADK generation call actually returned text that authored
            # >=1 question — never for the direct-call or RAG paths.
            log_event(
                "college.diagnostic.authored", user_id=uid,
                assessment_id=assessment.assessment_id,
                mode=("adk" if authored_by == "adk:assessment_agent"
                      else authored_by),
                authored_by=authored_by,
                question_count=len(questions), outcome="ok")
            await self.store.save_college_assessment(
                uid, assessment.model_dump(mode="json"))
            log_event("college.assessment.diagnostic_saved", user_id=uid,
                      assessment_id=assessment.assessment_id,
                      question_count=len(questions),
                      authored_by=authored_by,
                      grounded=retrieval.grounded,
                      sources=[q.source for q in questions],
                      subject_count=len(subject_ids), outcome="ok")
            return assessment

    async def _generate_diagnostic_with_llm(self, model, profile, retrieval):
        """
        The ADK assessment agent authors ~10 candidate probes against
        the retrieved context and selects the 5-6 highest-information
        ones (single call: a second selection round-trip risks the
        serverless window on the free tier).

        Returns (questions, via): via is "adk" when the text came back
        from the ADK generation seam and "groq_direct" when only the
        legacy direct model call produced it — the caller turns that
        into the payload's authored_by, so the label never claims ADK
        when the seam did not actually return text. Output is strictly
        validated; unusable output raises ValueError so the caller
        falls back to grounded material.
        """
        subject_ids = retrieval.subject_ids or retrieval.context_subject_ids
        subjects_line = ", ".join(subject_ids) if subject_ids else (
            "general engineering foundations")
        known = "; ".join(
            f"{m.get('topic')}={m.get('outcome')}"
            for m in retrieval.known_masteries[:8]) or "none yet"
        context_block = retrieval.prompt_context() or (
            "(no verified curriculum/PYQ material retrieved for this "
            "learner; rely on the learner context only and label every "
            "question model_generated)")

        prompt = f"""You are the PATHMIND Diagnostic Author. Build a short
baseline diagnostic for a college engineering learner.

LEARNER CONTEXT (profile data, not verified facts):
Branch: {retrieval.branch}
University: {retrieval.university_id or 'not set'}, Semester: {retrieval.semester or 'not set'}
Subjects in scope: {subjects_line}
Learner aspirations: {retrieval.aspirations or 'not stated'}
Already-known topic evidence (do not re-probe mastered topics): {known}

RETRIEVED SOURCE MATERIAL:
{context_block}

TASK: First draft about 10 candidate diagnostic probes internally, then
SELECT the 5-6 with the highest information gain for THIS learner. Prefer
probes that reveal prerequisite knowledge, conceptual understanding,
application ability, common misconceptions, and transfer — do not force
every category. Avoid duplicates, trivia, and anything far outside the
learner's semester. At least 4 MCQ and at least 1 SHORT_ANSWER.

SOURCE HONESTY (strict): set "source" to "verified_pyq" ONLY when the
question is adapted from a listed verified PYQ; "verified_curriculum"
when its topic comes from the verified curriculum above; otherwise
"model_generated". Never present invented facts as verified.

Return ONLY a JSON array of the selected 5-6 questions. Each item:
{{"id": "dq1", "text": "...", "type": "MCQ|SHORT_ANSWER",
  "options": ["A","B","C","D"], "answer": "B",
  "rubric": "for SHORT_ANSWER: what earns marks", "marks": 5,
  "topic": "short topic label from the curriculum above",
  "probe": "prerequisite|concept|application|misconception|transfer",
  "source": "verified_curriculum|verified_pyq|model_generated"}}
MCQs must include "options" and "answer" (letter or exact option text).
SHORT_ANSWER must include "rubric" and may include "answer" as a short
reference answer. Never invent subject ids."""
        # ADK-first: the assessment agent's one-shot generation is the
        # primary author. Only when the seam FAILS (ADK missing, no key,
        # runner error, timeout, empty reply) do we spend a direct model
        # call on the same prompt — and the returned `via` keeps the
        # provenance honest about which path produced the text.
        text = None
        via = None
        chain_started = time.monotonic()
        try:
            adk_text = await _agent_generation()("assessment", prompt)
            if adk_text and adk_text.strip():
                text, via = adk_text.strip(), "adk"
        except Exception as exc:
            log_event(
                "college.assessment.diagnostic_adk_failed",
                outcome="degraded", error_code=type(exc).__name__)
            text = None
        if text is None:
            if model is None:
                raise ValueError(
                    "DIAGNOSTIC_UNAVAILABLE: assessment agent and direct "
                    "model both unavailable")
            # Budget gate: the direct leg is bounded only by the client
            # timeout (~30s). If the ADK attempt already burned most of
            # the serverless window, skip straight to the grounded
            # fallback instead of dying mid-call against the platform
            # cap (which would cost the learner the whole diagnostic).
            if time.monotonic() - chain_started > 20.0:
                log_event(
                    "college.assessment.diagnostic_direct_skipped",
                    outcome="degraded", error_code="CHAIN_BUDGET")
                raise ValueError(
                    "DIAGNOSTIC_UNAVAILABLE: assessment agent timed "
                    "out and no request budget remains for a direct "
                    "attempt")
            response = self._generate_content_or_unavailable(
                model, prompt, "DIAGNOSTIC", max_output_tokens=4096)
            text = response.text.strip()
            via = "groq_direct"
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
        if not isinstance(gen_qs, list):
            raise ValueError(
                "DIAGNOSTIC_UNAVAILABLE: authored questions were not a list")
        return self._validate_generated_questions(gen_qs, retrieval), via

    @staticmethod
    def _validate_generated_questions(gen_qs, retrieval):
        """Strictly validate model output; drop anything malformed."""
        allowed_sources = {"verified_curriculum", "verified_pyq",
                           "model_generated"}
        allowed_probes = {"prerequisite", "concept", "application",
                          "misconception", "transfer"}
        questions: List[CollegeAssessmentQuestion] = []
        seen_texts = set()
        for i, gq in enumerate(gen_qs, start=1):
            if not isinstance(gq, dict):
                continue
            text = str(gq.get("text") or "").strip()
            if not text or text.lower() in seen_texts:
                continue
            qtype = str(gq.get("type") or "MCQ").upper()
            topic = str(gq.get("topic") or "").strip()
            if not topic:
                continue
            source = str(gq.get("source") or "model_generated")
            if source not in allowed_sources:
                source = "model_generated"
            # Honesty guard: a verified label requires retrieved material.
            if source == "verified_pyq" and not retrieval.pyq_questions:
                source = "model_generated"
            if (source == "verified_curriculum"
                    and not retrieval.curriculum_subjects):
                source = "model_generated"
            probe = str(gq.get("probe") or "concept").lower()
            if probe not in allowed_probes:
                probe = "concept"
            try:
                marks = int(gq.get("marks") or 5)
            except (TypeError, ValueError):
                marks = 5
            marks = max(1, min(10, marks))

            if qtype == "MCQ":
                options = list(dict.fromkeys(
                    str(o).strip() for o in (gq.get("options") or [])
                    if str(o).strip()))
                if len(options) < 3:
                    continue
                answer = str(gq.get("answer") or "").strip()
                if not answer:
                    continue
                # Resolve a letter answer ("B") to the option text now, so
                # the stored correct answer is always one of the options.
                if len(answer) == 1 and answer.upper() in "ABCD":
                    idx = "ABCD".index(answer.upper())
                    if idx >= len(options):
                        continue
                    answer = options[idx]
                elif answer not in options:
                    continue
                # Canonical server-assigned id: a model-supplied "id" can
                # repeat across questions, which collapses the frontend's
                # radio groups into one (answering wipes the others).
                questions.append(CollegeAssessmentQuestion(
                    question_id=f"dq{len(questions) + 1}",
                    question_text=text,
                    question_type="MCQ",
                    options=options,
                    correct_answer=answer,
                    topic=topic,
                    marks=marks,
                    probe=probe,
                    source=source,
                ))
            elif qtype == "SHORT_ANSWER":
                rubric = str(gq.get("rubric") or "").strip()
                if not rubric:
                    continue
                # A model-supplied reference answer powers the deterministic
                # exact-match grader; it stays model-labeled, never verified.
                reference = str(gq.get("answer") or "").strip() or None
                questions.append(CollegeAssessmentQuestion(
                    question_id=f"dq{len(questions) + 1}",
                    question_text=text,
                    question_type="SHORT_ANSWER",
                    correct_answer=reference,
                    rubric=rubric,
                    topic=topic,
                    marks=marks,
                    probe=probe,
                    source=source,
                ))
            else:
                continue
            seen_texts.add(text.lower())
            if len(questions) >= 6:
                break
        return questions

    # Syllabus lines that are course administration, not knowledge —
    # probing them ("Explain the core idea of 'Objective of the course'")
    # produces the repeated, content-free questions learners complained
    # about. A topic that merely announces the course is never probe
    # material for the grounded fallback.
    _META_TOPIC_RE = re.compile(
        r"(objective|scope|outcome|introduction|overview|"
        r"course\s+(content|structure|description)|about\s+the\s+course|"
        r"text\s*books?|reference\s+books?|syllabus)",
        re.IGNORECASE,
    )

    # Rotating probe framings for the grounded fallback: the same template
    # repeated six times reads as one question asked six times.
    _FALLBACK_PROBE_TEMPLATES = (
        ("Explain the core idea of '{topic}' ({subject}) in your own "
         "words, and give one example of where it is used.", "concept"),
        ("Describe a real situation where '{topic}' ({subject}) is "
         "applied. What problem does it solve there, and why does it "
         "work?", "application"),
        ("What is the most common misunderstanding students have about "
         "'{topic}' ({subject})? State the wrong idea, then the correct "
         "one.", "misconception"),
        ("What foundational ideas must be solid before '{topic}' "
         "({subject}) makes sense? Pick one and explain it briefly.",
         "prerequisite"),
    )

    @staticmethod
    def _rag_pyq_questions(retrieval):
        """Real verified PYQs as diagnostic questions (never invented)."""
        questions: List[CollegeAssessmentQuestion] = []
        for q in retrieval.pyq_questions[:4]:
            topic = (q.get("topics") or [None])[0]
            if not topic:
                subject = next(
                    (s for s in retrieval.curriculum_subjects
                     if s["subject_id"] == q["subject_id"]), None)
                topic = (subject or {}).get("name") or q["subject_id"]
            try:
                marks = int(q.get("marks") or 5)
            except (TypeError, ValueError):
                marks = 5
            questions.append(CollegeAssessmentQuestion(
                question_id=f"dq_pyq_{q['question_id']}",
                question_text=q["question_text"],
                question_type="SHORT_ANSWER",
                topic=topic,
                marks=max(1, min(15, marks)),
                probe="application",
                source="verified_pyq",
            ))
        return questions

    @staticmethod
    def _rag_curriculum_probes(retrieval, existing, target_total: int = 6):
        """
        Curriculum topic probes filling the slots `existing` leaves open.

        Round-robin across subjects so one subject's first unit can never
        dominate the diagnostic; rotates the probe framing; skips
        course-admin meta topics, topics already covered by `existing`,
        and topics with demonstrated mastery. No invented answers or
        rubrics — these grade as INSUFFICIENT_EVIDENCE (Unknown) until a
        grader can judge them, never a fake score.
        """
        questions: List[CollegeAssessmentQuestion] = []
        mastered = {
            str(m.get("topic") or "").strip().lower()
            for m in (retrieval.known_masteries or [])
            if str(m.get("outcome") or "").upper().startswith("MASTER")
        }
        used = {str(q.topic or "").strip().lower() for q in existing}
        # Per-subject probe candidates: real knowledge topics only,
        # deduped, never re-probing demonstrated mastery.
        per_subject: List[List[Tuple[str, Any]]] = []
        for sub in retrieval.curriculum_subjects:
            topics: List[Tuple[str, Any]] = []
            seen_local = set()
            for unit in sub.get("units", []):
                for topic in (unit.get("topics") or []):
                    label = str(topic).strip()
                    key = label.lower()
                    if (len(label) < 3 or key in seen_local
                            or key in used or key in mastered
                            or CollegeAssessmentService._META_TOPIC_RE.search(label)):
                        continue
                    seen_local.add(key)
                    topics.append((label, sub))
            per_subject.append(topics)

        templates = CollegeAssessmentService._FALLBACK_PROBE_TEMPLATES
        probe_no = 0
        while len(existing) + len(questions) < target_total:
            progressed = False
            for topics in per_subject:
                if len(existing) + len(questions) >= target_total:
                    break
                if not topics:
                    continue
                label, sub = topics.pop(0)
                text, probe = templates[probe_no % len(templates)]
                probe_no += 1
                questions.append(CollegeAssessmentQuestion(
                    question_id=(
                        f"dq_curr_{sub['subject_id']}_"
                        f"{len(existing) + len(questions)}"),
                    question_text=text.format(
                        topic=label,
                        subject=sub.get("name", sub["subject_id"])),
                    question_type="SHORT_ANSWER",
                    topic=label,
                    marks=5,
                    probe=probe,
                    source="verified_curriculum",
                ))
                progressed = True
            if not progressed:
                break
        return questions

    @staticmethod
    def _fallback_diagnostic_questions(retrieval):
        """The pure-RAG diagnostic: verified PYQs, then curriculum probes."""
        anchored = CollegeAssessmentService._rag_pyq_questions(retrieval)
        probes = CollegeAssessmentService._rag_curriculum_probes(
            retrieval, anchored)
        return (anchored + probes)[:6]

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
            response = generate_fast(model, prompt, 1536)
            text = response.text.strip()
            if text.startswith("```json"):
                text = text[7:]
            if text.startswith("```"):
                text = text[3:]
            if text.endswith("```"):
                text = text[:-3]
            gen_qs = json.loads(text.strip())
            if not isinstance(gen_qs, list):
                return []
            questions: List[CollegeAssessmentQuestion] = []
            seen_texts = set()
            for gq in gen_qs:
                if not isinstance(gq, dict):
                    continue
                qtext = str(gq.get("text") or "").strip()
                if not qtext or qtext.lower() in seen_texts:
                    continue
                qtype = str(gq.get("type") or "").strip().upper()
                try:
                    marks = int(gq.get("marks") or 5)
                except (TypeError, ValueError):
                    marks = 5
                marks = max(1, min(10, marks))
                # Canonical server-assigned ids, always. Trusting the model's
                # own "id" field caused duplicate ids (it repeats "q1"),
                # which collapses the frontend's radio groups into one —
                # answering one question silently erased the others.
                question_id = f"q{len(questions) + 1}"
                topic = topic_tags[len(questions) % len(topic_tags)]
                if qtype == "MCQ":
                    options = list(dict.fromkeys(
                        str(o).strip() for o in (gq.get("options") or [])
                        if str(o).strip()))
                    if len(options) < 2:
                        continue
                    answer = str(gq.get("answer") or "").strip()
                    if not answer:
                        continue
                    # The prompt's format example invites a letter answer
                    # ("Option B" in the schema, "B" in practice). Resolve
                    # letters to the option text NOW so the stored correct
                    # answer is always exactly one of the options.
                    if len(answer) == 1 and answer.upper() in "ABCD":
                        idx = "ABCD".index(answer.upper())
                        if idx >= len(options):
                            continue
                        answer = options[idx]
                    elif answer not in options:
                        # An answer that is not one of the options can never
                        # be scored — drop the question instead of shipping
                        # an unanswerable MCQ.
                        continue
                    questions.append(CollegeAssessmentQuestion(
                        question_id=question_id,
                        question_text=qtext,
                        question_type="MCQ",
                        options=options,
                        correct_answer=answer,
                        topic=topic,
                        marks=marks,
                    ))
                elif qtype == "SHORT_ANSWER":
                    reference = str(gq.get("answer") or "").strip() or None
                    questions.append(CollegeAssessmentQuestion(
                        question_id=question_id,
                        question_text=qtext,
                        question_type="SHORT_ANSWER",
                        correct_answer=reference,
                        rubric=str(gq.get("rubric") or "").strip() or None,
                        topic=topic,
                        marks=marks,
                    ))
                else:
                    continue
                seen_texts.add(qtext.lower())
                if len(questions) >= 3:
                    break
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

            assessment = coerce_model(CollegeAssessment, raw_asmt)
            total_marks = sum(float(q.marks or 0) for q in assessment.questions)
            earned_marks = 0.0
            topic_results: List[Dict[str, Any]] = []
            confidences: List[float] = []

            # Grade every non-MCQ answer concurrently: each LLM grading call
            # is slow, and sequential grading times out on serverless when a
            # diagnostic has more than one free-text question.
            graded: Dict[int, tuple] = {}
            pending: List[tuple] = []
            for i, q in enumerate(assessment.questions):
                student_ans = (submission.answers.get(q.question_id) or "").strip()
                marks = float(q.marks or 0)
                if q.question_type == "MCQ":
                    correct = q.correct_answer
                    # The generator stores the correct answer as a letter
                    # (A/B/C/D) while the frontend submits the selected
                    # option text. Resolve letters to option text on both
                    # sides so real student answers actually score.
                    def _resolve_mcq(ans: str) -> str:
                        a = (ans or "").strip()
                        if len(a) == 1 and a.upper() in "ABCD" and q.options:
                            idx = "ABCD".index(a.upper())
                            if 0 <= idx < len(q.options):
                                return q.options[idx]
                        return a
                    graded[i] = (
                        score_mcq_answer(_resolve_mcq(student_ans),
                                         _resolve_mcq(correct), marks),
                        CONFIDENCE_DETERMINISTIC, False,
                        "Deterministic exact-match scoring.")
                else:
                    pending.append((i, q, student_ans))

            if pending:
                _grade_sem = asyncio.Semaphore(4)

                async def _grade_one(item):
                    i, q, ans = item
                    async with _grade_sem:
                        return i, await self._grade_short_answer(q, ans)

                for i, res in await asyncio.gather(
                        *(_grade_one(it) for it in pending)):
                    graded[i] = res

            for i, q in enumerate(assessment.questions):
                marks = float(q.marks or 0)
                (item_score, confidence, requires_review,
                 reasoning) = graded[i]

                earned_marks += item_score
                if confidence is not None:
                    confidences.append(confidence)
                # Evidence model: never overclaim from one question. A
                # question that still needs review contributes NO conclusion
                # (Unknown); otherwise the per-question ratio maps to a
                # Strong/Partial/Weak evidence label with a plain-language
                # likely issue, so results read as Strengths / Gaps /
                # Weaknesses / Unknowns rather than a bare pass/fail.
                ratio = (item_score / marks) if marks > 0 else 0.0
                evidence_outcome = topic_outcome_from_ratio(
                    None if requires_review else ratio)
                status_label, likely_issue = {
                    "MASTERED": (
                        "Strong", "Demonstrated on this evidence"),
                    "PARTIALLY_MASTERED": (
                        "Partial",
                        "Likely application/practice gap — targeted practice"),
                    "REINFORCEMENT_REQUIRED": (
                        "Weak",
                        "Likely knowledge/concept gap — guided learning first"),
                    "INSUFFICIENT_EVIDENCE": (
                        "Unknown",
                        "Insufficient evidence — no conclusion drawn yet"),
                }[evidence_outcome]
                topic_results.append({
                    "question_id": q.question_id,
                    "topic": q.topic,
                    "earned_marks": round(item_score, 1),
                    "total_marks": marks,
                    "status": ("STRONG" if item_score >= marks * 0.7
                               else "NEEDS_WORK"),
                    "outcome": evidence_outcome,
                    "status_label": status_label,
                    "likely_issue": likely_issue,
                    "evidence_note": reasoning,
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
            model = _get_light_model()
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
            model = _get_light_model()
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
