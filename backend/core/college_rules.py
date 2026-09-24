"""
Deterministic rules for the PathMind College MVP (TRD §5/§6).

Every function in this module is PURE:
  - narrow, typed signatures
  - no I/O, no database, no network, no clock reads
  - ZERO LLM/Gemini calls

These are the exact units Phase 1b will wrap as ADK FunctionTools. Deterministic
logic must never be tangled with LLM calls; LLM-backed grading lives in
`college_assessment_service.grade_short_answer_with_llm` and calls into these
helpers only for the deterministic parts.

Confidence convention ("never false precision", TRD §16): confidences are coarse
bands expressed as fixed constants, not computed decimals.
"""

from datetime import date, timedelta
from typing import Dict, List, Optional, Tuple

from backend.core.college_schemas import MasteryStatus

# --- Mastery thresholds (fraction of marks) ---------------------------------

#: Fraction of marks required for MASTERED.
MASTERY_THRESHOLD = 0.75
#: Fraction of marks required for PARTIALLY_MASTERED (below this: REINFORCEMENT_REQUIRED).
PARTIAL_THRESHOLD = 0.50

#: Coarse confidence bands. Fixed constants on purpose: we never claim a
#: computed precision like 0.87 for a judgement call.
CONFIDENCE_DETERMINISTIC = 1.0
CONFIDENCE_HIGH = 0.9
CONFIDENCE_MEDIUM = 0.6
CONFIDENCE_LOW = 0.3


def calculate_streak_days(active_dates: List[date], today: date) -> int:
    """
    Count consecutive calendar days with at least one completion, ending today.

    A streak is alive when the most recent activity was today or yesterday;
    it then counts back over unbroken consecutive days. Zero activity returns
    zero — there is no minimum-1 floor (no fake state).

    Pure: callers pass the dates; this function never reads the clock or DB.
    """
    unique = sorted({d for d in active_dates if d <= today}, reverse=True)
    if not unique:
        return 0
    if (today - unique[0]).days > 1:
        return 0
    streak = 0
    expected = unique[0]
    for day in unique:
        if day == expected:
            streak += 1
            expected -= timedelta(days=1)
        elif day < expected:
            break
    return streak


def score_mcq_answer(
    student_answer: str, correct_answer: Optional[str], marks: float
) -> float:
    """
    Deterministic MCQ scoring: exact (case-insensitive, trimmed) match earns
    full marks, anything else earns zero. No partial credit, no LLM.
    """
    if not correct_answer:
        return 0.0
    if (student_answer or "").strip().lower() == correct_answer.strip().lower():
        return float(marks)
    return 0.0


def grade_short_answer_exact_match(
    student_answer: str, correct_answer: Optional[str], marks: float
) -> Tuple[float, bool]:
    """
    Deterministic short-answer rule used when no LLM grading is available.

    Returns (score, requires_review). An exact match against a reference answer
    earns full marks; anything without a reference answer is flagged for human
    review instead of being graded on length or keyword overlap — both would be
    fake precision.
    """
    if correct_answer and (student_answer or "").strip().lower() == correct_answer.strip().lower():
        return float(marks), False
    if not correct_answer:
        return 0.0, True
    return 0.0, False


def determine_mastery(percentage: float) -> str:
    """
    Map an assessment percentage to a mastery outcome. Pure threshold rule.
    Returns the MasteryStatus value (never INSUFFICIENT_EVIDENCE: that outcome
    is produced per-topic when there is no gradable evidence at all).
    """
    if percentage >= MASTERY_THRESHOLD * 100.0:
        return MasteryStatus.MASTERED.value
    if percentage >= PARTIAL_THRESHOLD * 100.0:
        return MasteryStatus.PARTIALLY_MASTERED.value
    return MasteryStatus.REINFORCEMENT_REQUIRED.value


def topic_outcome_from_ratio(mastery_ratio: Optional[float]) -> str:
    """
    Map a per-topic mastery ratio (0.0–1.0) to an outcome enum value.
    None (no gradable evidence) -> INSUFFICIENT_EVIDENCE, never a guess.
    """
    if mastery_ratio is None:
        return MasteryStatus.INSUFFICIENT_EVIDENCE.value
    if mastery_ratio >= MASTERY_THRESHOLD:
        return MasteryStatus.MASTERED.value
    if mastery_ratio >= PARTIAL_THRESHOLD:
        return MasteryStatus.PARTIALLY_MASTERED.value
    return MasteryStatus.REINFORCEMENT_REQUIRED.value


def exam_countdown_days(target: date, today: date) -> int:
    """Deterministic days-until-exam. Never negative; pure date math."""
    return max(0, (target - today).days)


def evaluate_unlock_rule(
    unlock_rule: Dict, topic_scores: Dict[str, float]
) -> Tuple[bool, str]:
    """
    Pure evaluation of a phase unlock_rule against per-topic mastery scores.

    unlock_rule shape (schema §16):
        {"type": "ASSESSMENT_MASTERY",
         "required_assessment_score": 75.0,   # percent; per-topic threshold
         "required_topics": ["Topic A", ...]}

    topic_scores maps topic -> mastery ratio 0.0–1.0. The special key
    "__overall__" may carry the latest assessment percentage/100 when a rule
    lists no required topics.

    Returns (unlocked, reason_code). Never unlocks on missing evidence.
    """
    if not unlock_rule or unlock_rule.get("type") != "ASSESSMENT_MASTERY":
        return False, "UNSUPPORTED_RULE"
    try:
        threshold = float(unlock_rule.get("required_assessment_score", 75.0)) / 100.0
    except (TypeError, ValueError):
        return False, "INVALID_THRESHOLD"

    required_topics: List[str] = unlock_rule.get("required_topics") or []
    if not required_topics:
        overall = topic_scores.get("__overall__")
        if overall is None:
            return False, "NO_ASSESSMENT_EVIDENCE"
        if overall >= threshold:
            return True, "OVERALL_SCORE_MET"
        return False, "OVERALL_SCORE_BELOW_THRESHOLD"

    missing = [t for t in required_topics if t not in topic_scores]
    if missing:
        return False, "MISSING_TOPIC_EVIDENCE"
    failing = [t for t in required_topics if topic_scores[t] < threshold]
    if failing:
        return False, "TOPIC_MASTERY_BELOW_THRESHOLD"
    return True, "ALL_REQUIRED_TOPICS_MASTERED"


def build_learner_baseline(masteries: List[Dict]) -> Dict:
    """
    Derive the learner baseline (strengths / weaknesses / gaps) from per-topic
    mastery records. Single source of truth: the mastery store. Pure.

    Each mastery dict: {"subject_id":..., "topic":..., "mastery_score":...,
    "outcome":...}.
    """
    strengths: List[Dict] = []
    weaknesses: List[Dict] = []
    gaps: List[Dict] = []
    for record in masteries:
        entry = {
            "subject_id": record.get("subject_id"),
            "topic": record.get("topic"),
            "mastery_score": record.get("mastery_score"),
            "outcome": record.get("outcome"),
        }
        outcome = record.get("outcome")
        if outcome == MasteryStatus.MASTERED.value:
            strengths.append(entry)
        elif outcome in (
            MasteryStatus.PARTIALLY_MASTERED.value,
            MasteryStatus.REINFORCEMENT_REQUIRED.value,
        ):
            weaknesses.append(entry)
        else:
            gaps.append(entry)
    return {
        "strengths": strengths,
        "weaknesses": weaknesses,
        "gaps": gaps,
        "topic_count": len(masteries),
    }
