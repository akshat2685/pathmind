"""
Dynamic retrieval for the college diagnostic (hybrid RAG, MVP-grade).

The diagnostic must NOT depend on a manually curated universal knowledge
base. Instead, at request time we retrieve what PathMind already holds from
verified sources — the learner's official curriculum (subjects, units,
topics), verified past-year questions (PYQs) and verified learning
resources — plus the learner's own state (goal, prior topic mastery).

Everything retrieved here is labeled: `grounded=True` only for items that
come from verified PathMind records. Gemini-generated content is never
labeled grounded. Retrieval failures degrade to partial/empty context —
they never raise, so a retrieval failure can never become an HTTP 500.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from backend.core.college_logging import log_event
from backend.core.college_schemas import EngineeringBranch
from backend.providers.curriculum_registry import (
    get_curriculum,
    get_pyqs_for_subject,
    get_resources_for_subject,
)


@dataclass
class RetrievedItem:
    kind: str            # curriculum | pyq | resource | mastery | goal
    title: str
    detail: str
    source_label: str    # human-readable provenance, shown in logs/prompt
    grounded: bool       # True only for verified-source records


@dataclass
class DiagnosticRetrieval:
    """Everything the diagnostic author (Gemini or fallback) may use."""
    branch: str = "GENERAL_OTHER"
    university_id: Optional[str] = None
    semester: Optional[int] = None
    aspirations: str = ""
    # [{subject_id, code, name, units: [{unit, title, topics}]}]
    curriculum_subjects: List[Dict[str, Any]] = field(default_factory=list)
    # [{subject_id, question_id, question_number, question_text, marks, topics}]
    pyq_questions: List[Dict[str, Any]] = field(default_factory=list)
    # subject_id -> [{resource_id, title, resource_type, provider}]
    resources_by_subject: Dict[str, List[Dict[str, Any]]] = field(
        default_factory=dict)
    # [{subject_id, topic, mastery_score, outcome}] — prior evidence, may be []
    known_masteries: List[Dict[str, Any]] = field(default_factory=list)
    # Subject ids saved on the learner's academic context (may exceed the
    # verified-curriculum coverage when a university is only partly seeded).
    context_subject_ids: List[str] = field(default_factory=list)
    items: List[RetrievedItem] = field(default_factory=list)

    @property
    def grounded(self) -> bool:
        return any(i.grounded for i in self.items)

    @property
    def subject_ids(self) -> List[str]:
        return [s["subject_id"] for s in self.curriculum_subjects]

    def prompt_context(self, max_pyq: int = 6, max_topics_per_unit: int = 6) -> str:
        """Compact, clearly-labeled context block for the Gemini prompt."""
        lines: List[str] = []
        if self.curriculum_subjects:
            lines.append("VERIFIED CURRICULUM (official syllabus records):")
            for sub in self.curriculum_subjects:
                lines.append(
                    f"- Subject {sub['subject_id']} ({sub.get('code', '')} "
                    f"{sub.get('name', '')}):")
                for unit in sub.get("units", []):
                    topics = ", ".join(
                        (unit.get("topics") or [])[:max_topics_per_unit])
                    lines.append(
                        f"  Unit {unit.get('unit')}: {unit.get('title', '')}"
                        + (f" — topics: {topics}" if topics else ""))
        if self.pyq_questions:
            lines.append(
                "VERIFIED PAST-YEAR EXAM QUESTIONS (real university PYQs):")
            for q in self.pyq_questions[:max_pyq]:
                topic = (q.get("topics") or ["general"])[0]
                lines.append(
                    f"- [{q['subject_id']}] {q.get('question_number', '')} "
                    f"({q.get('marks', '?')} marks, topic: {topic}): "
                    f"{q.get('question_text', '')}")
        for sid, resources in self.resources_by_subject.items():
            for r in resources[:3]:
                lines.append(
                    f"VERIFIED RESOURCE [{sid}]: {r.get('title', '')} "
                    f"({r.get('resource_type', '')}, {r.get('provider', '')})")
        if self.known_masteries:
            lines.append("PRIOR LEARNER EVIDENCE (per-topic mastery):")
            for m in self.known_masteries[:12]:
                lines.append(
                    f"- {m.get('subject_id')}/{m.get('topic')}: "
                    f"{m.get('outcome')} (score {m.get('mastery_score')})")
        return "\n".join(lines)


def _resolve_branch(profile: Optional[dict]) -> EngineeringBranch:
    supported = (profile or {}).get("supported_path")
    try:
        return EngineeringBranch(supported) if supported else (
            EngineeringBranch.GENERAL_OTHER)
    except ValueError:
        return EngineeringBranch.GENERAL_OTHER


async def retrieve_diagnostic_context(store, uid: str) -> DiagnosticRetrieval:
    """
    Assemble the learner's diagnostic context from existing PathMind state.

    Never raises: each source is fetched independently and any failure just
    narrows the context (logged), so the diagnostic can still fall back to
    whatever grounded material exists.
    """
    retrieval = DiagnosticRetrieval()

    raw_profile = await store.get_college_user_profile(uid)
    profile = raw_profile if isinstance(raw_profile, dict) else None
    branch = _resolve_branch(profile)
    retrieval.branch = branch.value

    raw_ctx = None
    try:
        raw_ctx = await store.get_college_academic_context(uid)
    except Exception as exc:  # store contract already swallows; belt & braces
        log_event("college.diagnostic.retrieval_context_failed",
                  user_id=uid, outcome="error", error_code=type(exc).__name__)
    ctx = raw_ctx if isinstance(raw_ctx, dict) else {}
    retrieval.university_id = ctx.get("university_id")
    retrieval.semester = ctx.get("semester")

    # Learner goal / aspiration (already collected at onboarding Step 1).
    try:
        raw_goal = await store.get_college_goal(uid)
        if raw_goal:
            goal = (raw_goal if isinstance(raw_goal, dict)
                    else raw_goal.model_dump())
            retrieval.aspirations = (
                goal.get("raw_goal") or goal.get("normalized_goal") or "")
            if retrieval.aspirations:
                retrieval.items.append(RetrievedItem(
                    kind="goal", title="Learner aspiration",
                    detail=retrieval.aspirations,
                    source_label="learner profile", grounded=False))
    except Exception as exc:
        log_event("college.diagnostic.retrieval_goal_failed", user_id=uid,
                  outcome="error", error_code=type(exc).__name__)

    # Prior evidence: never re-ask what the learner already demonstrated.
    try:
        retrieval.known_masteries = await store.get_topic_masteries(uid) or []
        for m in retrieval.known_masteries[:12]:
            retrieval.items.append(RetrievedItem(
                kind="mastery", title=f"Mastery: {m.get('topic')}",
                detail=f"{m.get('outcome')} (score {m.get('mastery_score')})",
                source_label="prior assessment evidence", grounded=False))
    except Exception as exc:
        log_event("college.diagnostic.retrieval_mastery_failed", user_id=uid,
                  outcome="error", error_code=type(exc).__name__)

    # Verified curriculum for the learner's university/program/semester.
    context_subject_ids: List[str] = []
    if ctx.get("context_id"):
        try:
            context_subject_ids = await store.get_context_subject_ids(
                ctx["context_id"]) or []
        except Exception as exc:
            log_event("college.diagnostic.retrieval_subjects_failed",
                      user_id=uid, outcome="error",
                      error_code=type(exc).__name__)
    retrieval.context_subject_ids = context_subject_ids

    curriculum = None
    if retrieval.university_id and retrieval.semester:
        try:
            curriculum = await get_curriculum(
                retrieval.university_id, branch, int(retrieval.semester))
        except Exception as exc:
            log_event("college.diagnostic.retrieval_curriculum_failed",
                      user_id=uid, outcome="error",
                      error_code=type(exc).__name__)

    if (curriculum is None or not curriculum.subjects) \
            and retrieval.university_id and retrieval.semester:
        # One retry: get_curriculum swallows transient registry read
        # failures into None, and an empty curriculum starves the grounded
        # fallback (fewer than 3 questions -> DIAGNOSTIC_UNAVAILABLE even
        # though verified material exists — the intermittent dead-end
        # learners hit on the diagnostic step). One extra read rescues
        # the transient case; a genuinely unseeded semester still ends
        # honestly unavailable.
        try:
            curriculum = await get_curriculum(
                retrieval.university_id, branch, int(retrieval.semester))
        except Exception as exc:
            log_event(
                "college.diagnostic.retrieval_curriculum_retry_failed",
                user_id=uid, outcome="error",
                error_code=type(exc).__name__)

    if curriculum and curriculum.subjects:
        wanted = set(context_subject_ids)
        for sub in curriculum.subjects:
            if wanted and sub.subject_id not in wanted:
                continue
            entry = {
                "subject_id": sub.subject_id,
                "code": sub.code,
                "name": sub.name,
                "units": [
                    {"unit": u.unit, "title": u.title,
                     "topics": list(u.topics or [])}
                    for u in (sub.units or [])
                ],
            }
            retrieval.curriculum_subjects.append(entry)
            retrieval.items.append(RetrievedItem(
                kind="curriculum",
                title=f"{sub.code} {sub.name}",
                detail=(f"{len(entry['units'])} units from the verified "
                        f"semester {retrieval.semester} curriculum"),
                source_label=(
                    f"verified curriculum: {retrieval.university_id} "
                    f"semester {retrieval.semester}"),
                grounded=True))

    # Verified PYQs + resources per subject (real exam material first).
    for subject_id in retrieval.subject_ids:
        try:
            pyq_set = await get_pyqs_for_subject(
                retrieval.university_id, subject_id)
            if pyq_set and pyq_set.questions:
                for q in pyq_set.questions[:4]:
                    retrieval.pyq_questions.append({
                        "subject_id": subject_id,
                        "question_id": q.question_id,
                        "question_number": q.question_number,
                        "question_text": q.question_text,
                        "marks": q.marks,
                        "topics": list(q.topic_ids or []),
                        "unit": q.unit,
                    })
                    retrieval.items.append(RetrievedItem(
                        kind="pyq",
                        title=f"PYQ {q.question_number} ({subject_id})",
                        detail=q.question_text,
                        source_label=(
                            f"verified PYQ set {pyq_set.pyq_set_id}"),
                        grounded=True))
        except Exception as exc:
            log_event("college.diagnostic.retrieval_pyq_failed", user_id=uid,
                      outcome="error", error_code=type(exc).__name__)
        try:
            resources = await get_resources_for_subject(subject_id)
            if resources:
                retrieval.resources_by_subject[subject_id] = [
                    {"resource_id": r.resource_id, "title": r.title,
                     "resource_type": r.resource_type,
                     "provider": r.provider}
                    for r in resources[:3]
                ]
                for r in resources[:3]:
                    retrieval.items.append(RetrievedItem(
                        kind="resource", title=r.title,
                        detail=f"{r.resource_type} via {r.provider}",
                        source_label=f"verified resource {r.resource_id}",
                        grounded=True))
        except Exception as exc:
            log_event("college.diagnostic.retrieval_resource_failed",
                      user_id=uid, outcome="error",
                      error_code=type(exc).__name__)

    log_event("college.diagnostic.retrieval_completed", user_id=uid,
              grounded=retrieval.grounded,
              curriculum_subjects=len(retrieval.curriculum_subjects),
              pyq_count=len(retrieval.pyq_questions),
              mastery_count=len(retrieval.known_masteries), outcome="ok")
    return retrieval
