"""
Unit tests for backend/core/college_rules.py.

These are pure, deterministic functions (TRD §5/§6: tool-ready): no LLM,
no network, no database. They must stay importable and side-effect free.
"""
from datetime import date

from backend.core.college_rules import (
    calculate_streak_days,
    score_mcq_answer,
    grade_short_answer_exact_match,
    topic_outcome_from_ratio,
    determine_mastery,
    exam_countdown_days,
    evaluate_unlock_rule,
    build_learner_baseline,
)
from backend.core.college_schemas import MasteryStatus


def test_streak_zero_activity_is_zero():
    assert calculate_streak_days([], date(2026, 9, 24)) == 0


def test_streak_consecutive_days():
    days = [date(2026, 9, 24), date(2026, 9, 23), date(2026, 9, 22)]
    assert calculate_streak_days(days, date(2026, 9, 24)) == 3


def test_streak_ends_yesterday_counts():
    days = [date(2026, 9, 23), date(2026, 9, 22)]
    assert calculate_streak_days(days, date(2026, 9, 24)) == 2


def test_streak_gap_breaks():
    days = [date(2026, 9, 24), date(2026, 9, 22)]
    assert calculate_streak_days(days, date(2026, 9, 24)) == 1


def test_streak_ignores_future_and_duplicates():
    days = [date(2026, 9, 25), date(2026, 9, 24), date(2026, 9, 24)]
    assert calculate_streak_days(days, date(2026, 9, 24)) == 1


def test_mcq_scoring_case_insensitive():
    assert score_mcq_answer("  Conservation of Energy ", "conservation of energy", 20) == 20.0
    assert score_mcq_answer("wrong", "right", 20) == 0.0
    assert score_mcq_answer("", "right", 20) == 0.0
    assert score_mcq_answer("anything", None, 20) == 0.0


def test_short_answer_exact_match_only():
    score, review = grade_short_answer_exact_match("Pointer Null", "pointer null", 60)
    assert score == 60.0 and review is False
    # No fuzzy/length grading: a wrong answer with a reference scores zero;
    # anything without a reference goes to human review.
    score, review = grade_short_answer_exact_match("a very long wrong answer " * 10, "x", 60)
    assert score == 0.0 and review is False
    score, review = grade_short_answer_exact_match("anything", None, 60)
    assert score == 0.0 and review is True


def test_topic_outcome_thresholds():
    assert topic_outcome_from_ratio(None) == MasteryStatus.INSUFFICIENT_EVIDENCE.value
    assert topic_outcome_from_ratio(0.9) == MasteryStatus.MASTERED.value
    assert topic_outcome_from_ratio(0.6) == MasteryStatus.PARTIALLY_MASTERED.value
    assert topic_outcome_from_ratio(0.2) == MasteryStatus.REINFORCEMENT_REQUIRED.value


def test_determine_mastery_thresholds():
    assert determine_mastery(90.0) == MasteryStatus.MASTERED.value
    assert determine_mastery(60.0) == MasteryStatus.PARTIALLY_MASTERED.value
    assert determine_mastery(20.0) == MasteryStatus.REINFORCEMENT_REQUIRED.value


def test_exam_countdown():
    assert exam_countdown_days(date(2026, 11, 20), date(2026, 9, 24)) == 57
    assert exam_countdown_days(date(2026, 9, 24), date(2026, 9, 24)) == 0
    assert exam_countdown_days(date(2026, 9, 1), date(2026, 9, 24)) == 0


def test_unlock_rule_gates_on_evidence():
    rule = {"type": "ASSESSMENT_MASTERY", "required_assessment_score": 75.0,
            "required_topics": ["Linked Lists", "Arrays"]}
    unlocked, reason = evaluate_unlock_rule(rule, {"Linked Lists": 0.9, "Arrays": 0.8})
    assert unlocked and reason == "ALL_REQUIRED_TOPICS_MASTERED"

    unlocked, reason = evaluate_unlock_rule(rule, {"Linked Lists": 0.9, "Arrays": 0.5})
    assert not unlocked and reason == "TOPIC_MASTERY_BELOW_THRESHOLD"

    # Missing evidence never unlocks
    unlocked, reason = evaluate_unlock_rule(rule, {"Linked Lists": 0.9})
    assert not unlocked and reason == "MISSING_TOPIC_EVIDENCE"

    # No rule at all: honest closed gate
    unlocked, reason = evaluate_unlock_rule(None, {"Linked Lists": 1.0})
    assert not unlocked and reason == "UNSUPPORTED_RULE"


def test_baseline_from_mastery_records():
    records = [
        {"subject_id": "CS-301", "topic": "Linked Lists",
         "mastery_score": 0.9, "outcome": "MASTERED"},
        {"subject_id": "CS-301", "topic": "Graphs",
         "mastery_score": 0.2, "outcome": "REINFORCEMENT_REQUIRED"},
        {"subject_id": "CS-302", "topic": "Paging",
         "mastery_score": 0.0, "outcome": "INSUFFICIENT_EVIDENCE"},
    ]
    baseline = build_learner_baseline(records)
    assert [e["topic"] for e in baseline["strengths"]] == ["Linked Lists"]
    assert [e["topic"] for e in baseline["weaknesses"]] == ["Graphs"]
    assert [e["topic"] for e in baseline["gaps"]] == ["Paging"]
    assert baseline["topic_count"] == 3
