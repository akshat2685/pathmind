"""
Tests for the aspiration test step (sign in -> name -> aspiration ->
status card -> verification -> TEST -> personalized path).

Covers the pure functions (validation, sanitization, answer normalization),
the evaluation orchestration with a fake store, and the honesty contracts:
- correct answers never leave the backend (_sanitize_questions),
- no fabricated test when Gemini is down (GeminiUnavailable propagates),
- unscored short answers are NEEDS_REVIEW, never invented scores,
- skills with only pending-review questions get no percentage (not 0%).

No database, no AI, no network: generate_text_resilient is monkeypatched.
"""
import asyncio
import json

import pytest

import backend.services.aspiration_test_service as svc_mod
from backend.core.gemini import GeminiUnavailable
from backend.services.aspiration_test_service import (
    AspirationTestService,
    _sanitize_questions,
    _validate_and_normalize,
)


def _good_llm_payload():
    return {"questions": [
        {"id": "q1", "type": "mcq", "question": "Q1?",
         "options": ["a", "b", "c", "d"], "correct_option": 2,
         "points": 4, "skill_tag": "rules"},
        {"id": "q2", "type": "mcq", "question": "Q2?",
         "options": ["a", "b", "c", "d"], "correct_option": "B",
         "points": 4, "skill_tag": "rules"},
        {"id": "q3", "type": "mcq", "question": "Q3?",
         "options": ["a", "b", "c", "d"], "correct_option": 0,
         "points": 4, "skill_tag": "tactics"},
        {"id": "q4", "type": "mcq", "question": "Q4?",
         "options": ["a", "b", "c", "d"], "correct_option": 3,
         "points": 4, "skill_tag": "tactics"},
        {"id": "q5", "type": "mcq", "question": "Q5?",
         "options": ["a", "b", "c", "d"], "correct_option": 1,
         "points": 4, "skill_tag": "fitness"},
        {"id": "q6", "type": "short", "question": "Q6?",
         "rubric": "r", "points": 8, "skill_tag": "judgment"},
        {"id": "q7", "type": "short", "question": "Q7?",
         "rubric": "r", "points": 8, "skill_tag": "judgment"},
        {"id": "q8", "type": "self_assess", "question": "Rate X 1-5",
         "points": 0, "skill_tag": "stamina"},
    ], "time_suggestion_minutes": 20}


class FakeStore:
    """Duck-typed stand-in for PmStore's aspiration-test methods."""

    def __init__(self, questions):
        self.tests = {"t_1": {
            "test_id": "t_1", "aspiration": "cricketer",
            "questions": questions,
        }}
        self.results = []

    async def save_aspiration_test(self, person_id, test_data):
        self.tests[test_data["test_id"]] = dict(test_data)
        return test_data["test_id"]

    async def get_aspiration_test(self, person_id, test_id):
        t = self.tests.get(test_id)
        return dict(t) if t else None

    async def get_latest_aspiration_test(self, person_id):
        return dict(self.tests["t_1"])

    async def save_test_result(self, person_id, result_data):
        self.results.append(dict(result_data))
        return result_data["result_id"]

    async def get_test_result(self, person_id, result_id):
        for r in self.results:
            if r["result_id"] == result_id:
                return r
        return None

    async def get_test_result_for_test(self, person_id, test_id):
        for r in reversed(self.results):
            if r["test_id"] == test_id:
                return r
        return None

    async def get_domain_for_aspiration(self, text):
        return "general"

    async def get_bank_questions(self, domain, limit=12, tiers=("VERIFIED", "EXPERT_REVIEWED", "AI_DRAFT")):
        # Bank starts empty in tests: forces the honest AI-generation path.
        return []


@pytest.fixture
def questions():
    return _validate_and_normalize(_good_llm_payload())["questions"]


@pytest.fixture
def service(questions):
    return AspirationTestService(store=FakeStore(questions))


def _answers():
    return [
        {"question_id": "q1", "answer": 2},
        {"question_id": "q2", "answer": "B"},
        {"question_id": "q3", "answer": 1},   # wrong
        {"question_id": "q4", "answer": 3},
        {"question_id": "q5", "answer": 0},   # wrong
        {"question_id": "q6", "answer": "some answer"},
        {"question_id": "q7", "answer": ""},
        {"question_id": "q8", "answer": 4},
    ]


# ---------------------------------------------------------------------------
# Validation / sanitization (pure)
# ---------------------------------------------------------------------------
def test_validate_accepts_good_payload_and_coerces_letter():
    norm = _validate_and_normalize(_good_llm_payload())
    assert len(norm["questions"]) == 8
    assert norm["questions"][1]["correct_option"] == 1  # "B" -> 1
    assert norm["total_points"] == 36  # self_assess excluded


def test_validate_rejects_bad_payloads():
    too_few = {"questions": _good_llm_payload()["questions"][:7]}
    with pytest.raises(ValueError):
        _validate_and_normalize(too_few)
    bad_opts = _good_llm_payload()
    bad_opts["questions"][0] = {**bad_opts["questions"][0], "options": ["a", "b"]}
    with pytest.raises(ValueError):
        _validate_and_normalize(bad_opts)
    bad_type = _good_llm_payload()
    bad_type["questions"][0] = {**bad_type["questions"][0], "type": "essay"}
    with pytest.raises(ValueError):
        _validate_and_normalize(bad_type)


def test_sanitize_strips_correct_answers(questions):
    san = _sanitize_questions(questions)
    assert all("correct_option" not in q for q in san)
    assert all("correct_answer" not in q for q in san)
    # everything else survives
    assert san[0]["options"] == ["a", "b", "c", "d"]
    assert san[0]["points"] == 4


def test_mcq_answer_normalization():
    n = AspirationTestService._normalize_mcq_answer
    opts = ["a", "b", "c", "d"]
    assert n(2, opts) == 2
    assert n("C", opts) == 2
    assert n("the third", ["a", "b", "the third", "d"]) == 2
    assert n(9, opts) is None
    assert n("", opts) is None
    assert n(None, opts) is None


# ---------------------------------------------------------------------------
# Evaluation (fake store; Gemini stubbed at the module boundary)
# ---------------------------------------------------------------------------
def test_evaluate_gemini_down_is_honest(service, monkeypatch):
    def boom(prompt, *, feature, **kw):
        raise GeminiUnavailable("down")
    monkeypatch.setattr(svc_mod, "generate_text_resilient", boom)

    ev = asyncio.run(service.evaluate_test("u1", "t_1", _answers()))
    assert ev["score"] == 12          # 3 correct MCQs x 4
    assert ev["max_score"] == 36      # self_assess excluded from scoring
    assert ev["percentage"] == 60.0   # 12 / 20 scored_max
    assert ev["short_answers_pending_review"] is True
    shorts = [p for p in ev["per_question"] if p["type"] == "short"]
    assert all(p["status"] == "NEEDS_REVIEW" and p["score"] is None for p in shorts)
    # pending-review skill gets NO percentage (honest) instead of a fake 0%
    assert ev["skill_breakdown"]["judgment"]["percentage"] is None
    assert "judgment" not in ev["gaps"]
    assert ev["strengths"] == ["rules"]
    assert ev["gaps"] == ["fitness"]
    # self-assessment feeds the profile, not the score
    assert ev["skill_breakdown"]["stamina"]["avg_self_rating"] == 4.0


def test_evaluate_short_scoring_with_clamp(service, monkeypatch):
    def fake_llm(prompt, *, feature, **kw):
        return json.dumps([
            {"question_id": "q6", "score": 999, "feedback": "evil"},
            {"question_id": "q7", "score": -5, "feedback": "evil"},
        ])
    monkeypatch.setattr(svc_mod, "generate_text_resilient", fake_llm)

    ev = asyncio.run(service.evaluate_test("u1", "t_1", _answers()))
    shorts = {p["question_id"]: p["score"]
              for p in ev["per_question"] if p["type"] == "short"}
    assert shorts == {"q6": 8, "q7": 0}  # clamped to [0, max_points]
    assert ev["score"] == 20
    assert ev["short_answers_pending_review"] is False


def test_evaluate_unknown_test_raises_keyerror(service):
    with pytest.raises(KeyError):
        asyncio.run(service.evaluate_test("u1", "nope", []))


def test_generate_no_fabrication_when_gemini_down(service, monkeypatch):
    def boom(prompt, *, feature, **kw):
        raise GeminiUnavailable("down")
    monkeypatch.setattr(svc_mod, "generate_text_resilient", boom)
    with pytest.raises(GeminiUnavailable):
        asyncio.run(service.generate_test("u1", "cricketer", "10th", "school", {}))


def test_generate_rejects_short_aspiration(service):
    with pytest.raises(ValueError):
        asyncio.run(service.generate_test("u1", "abc", "10th", "school", {}))
