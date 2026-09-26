"""
Deterministic rules for the PATHMIND main product.

Every function in this module is PURE:
  - narrow, typed signatures
  - no I/O, no database, no network, no clock reads
  - ZERO LLM/Gemini calls

Ported from the college-mvp's college_rules.py pattern (the domain-neutral
parts). Deterministic logic must never be tangled with LLM calls.

Confidence convention ("never false precision"): confidences are coarse bands
expressed as fixed constants, not computed decimals.
"""

from datetime import date, timedelta
from enum import Enum
from typing import Dict, List, Optional, Tuple


class MasteryOutcome(str, Enum):
    MASTERED = "MASTERED"
    PARTIALLY_MASTERED = "PARTIALLY_MASTERED"
    REINFORCEMENT_REQUIRED = "REINFORCEMENT_REQUIRED"
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"


# --- Mastery thresholds (fraction of marks) ---------------------------------

#: Fraction required for MASTERED.
MASTERY_THRESHOLD = 0.75
#: Fraction required for PARTIALLY_MASTERED (below this: REINFORCEMENT_REQUIRED).
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


def determine_mastery(percentage: float) -> str:
    """
    Map an assessment percentage to a mastery outcome. Pure threshold rule.
    """
    if percentage >= MASTERY_THRESHOLD * 100.0:
        return MasteryOutcome.MASTERED.value
    if percentage >= PARTIAL_THRESHOLD * 100.0:
        return MasteryOutcome.PARTIALLY_MASTERED.value
    return MasteryOutcome.REINFORCEMENT_REQUIRED.value


def topic_outcome_from_ratio(mastery_ratio: Optional[float]) -> str:
    """
    Map a per-topic mastery ratio (0.0-1.0) to an outcome.
    None (no gradable evidence) -> INSUFFICIENT_EVIDENCE, never a guess.
    """
    if mastery_ratio is None:
        return MasteryOutcome.INSUFFICIENT_EVIDENCE.value
    if mastery_ratio >= MASTERY_THRESHOLD:
        return MasteryOutcome.MASTERED.value
    if mastery_ratio >= PARTIAL_THRESHOLD:
        return MasteryOutcome.PARTIALLY_MASTERED.value
    return MasteryOutcome.REINFORCEMENT_REQUIRED.value


def evaluate_unlock_rule(
    unlock_rule: Dict, topic_scores: Dict[str, float]
) -> Tuple[bool, str]:
    """
    Pure evaluation of a stage unlock rule against per-topic mastery scores.

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


def promote_memory(
    current_status: str,
    observation_count: int,
    importance: str,
    evidence_verified: bool,
) -> str:
    """
    Pure memory promotion rule (spec §13): OBSERVED -> CANDIDATE -> DURABLE.

    - OBSERVED -> CANDIDATE: seen 2+ times, or marked HIGH/CRITICAL importance.
    - CANDIDATE -> DURABLE: seen 3+ times, or backed by verified evidence.
    - DURABLE is terminal (supersession is handled separately).
    - Never promotes on a single casual observation (no fake durability).
    """
    if current_status == "DURABLE":
        return "DURABLE"
    if current_status == "CANDIDATE":
        if observation_count >= 3 or evidence_verified:
            return "DURABLE"
        return "CANDIDATE"
    # OBSERVED (or unknown -> treat as OBSERVED)
    if observation_count >= 2 or importance in ("HIGH", "CRITICAL"):
        return "CANDIDATE"
    return "OBSERVED"
