"""
Aspiration test service for the PATHMIND main product.

Onboarding flow step: sign in -> name -> aspiration -> status card ->
verification -> TEST -> personalized path.

generate_test() asks Gemini for a domain-aware, level-appropriate test
(8-12 questions: ~60% MCQ, ~25% short answer, ~15% self-assessment).
evaluate_test() scores MCQs deterministically and short answers with a
rubric-guided Gemini call.

Honesty contract:
- Correct answers are stored in pm_aspiration_tests.data but NEVER leave
  the backend. generate_test() strips them before responding.
- If Gemini is unavailable at generation time, no test is fabricated:
  GeminiUnavailable propagates and the route answers 503.
- Short answers that cannot be scored (Gemini down) are marked
  NEEDS_REVIEW with score=None — never invented.
- Self-assessment questions are informational (points=0, excluded from
  max_score); their 1-5 ratings feed the skill profile, not the score.
"""

import asyncio
import json
import logging
import time
import uuid
from typing import Any, Dict, List, Optional

from backend.core.gemini import GeminiUnavailable, generate_text_resilient

logger = logging.getLogger(__name__)

VALID_TYPES = ("mcq", "short", "self_assess")

# ---------------------------------------------------------------------------
# Domain guidance injected into the generation prompt
# ---------------------------------------------------------------------------
_DOMAIN_GUIDANCE = """
Domain-specific guidance (apply the one matching the aspiration; otherwise use the generic fallback):
- CRICKET / SPORT: mix cricket knowledge (rules, technique, game awareness), situational judgment
  (match scenarios: "2 overs left, 18 needed, 3 wickets in hand — what is the right approach?"), and
  physical self-assessment ("Rate your sprint stamina 1-5", "Rate your throwing strength 1-5").
  Never ask the learner to perform unverifiable physical feats in a written test — self-assessment only.
- CODING / SOFTWARE: conceptual MCQs (data structures, complexity, language fundamentals),
  code-tracing MCQs (short snippets, "what does this print?"), one short design/explanation answer.
- MEDICINE / HEALTHCARE: science aptitude (biology/chemistry reasoning at the learner's stage),
  situational judgment (ethics, patient scenarios), study-habit self-assessment.
- BUSINESS / ENTREPRENEURSHIP: business acumen scenarios (pricing, unit economics, customer
  reasoning), numeracy MCQs, one short "pitch your idea" style answer.
- GENERIC FALLBACK: domain-basics MCQs, learning-aptitude questions, motivation and
  self-assessment. Keep questions concrete, never generic filler.
"""

_TEST_PROMPT_TEMPLATE = """You are PATHMIND's assessment designer. Create a diagnostic entrance test for a learner.

Learner profile:
- Aspiration: {aspiration}
- Stage: {stage}
- User type: {user_type}
- Verification summary: {verification_summary}

{_DOMAIN_GUIDANCE}

Requirements:
- 8-12 questions total. Target mix: ~60% MCQ, ~25% short answer, ~15% self-assessment.
- Difficulty MUST match the learner's stage and user type (a school student gets fundamentals;
  a working professional gets applied/professional depth). Use the verification summary to calibrate.
- Every question needs a skill_tag: a short kebab-case label of the skill it probes
  (e.g. "batting-technique", "dsa-basics", "unit-economics").
- MCQ: exactly 4 options, correct_option as a 0-based index into options. points: 2-5.
- Short answer: include a "rubric" string describing what a full-marks answer contains. points: 5-10.
- Self-assessment: question asks the learner to rate themselves 1-5 on something real
  (stamina, confidence, prior exposure). points MUST be 0 (these do not affect the score).
- Also suggest time_suggestion_minutes (10-30).

Return ONLY a JSON object, no markdown fences, no commentary:
{{
  "questions": [
    {{"id": "q1", "type": "mcq", "question": "...", "options": ["...", "...", "...", "..."],
      "correct_option": 0, "points": 4, "skill_tag": "..."}},
    {{"id": "q2", "type": "short", "question": "...", "rubric": "...", "points": 8, "skill_tag": "..."}},
    {{"id": "q3", "type": "self_assess", "question": "Rate your ... from 1 (weak) to 5 (strong).",
      "points": 0, "skill_tag": "..."}}
  ],
  "time_suggestion_minutes": 20
}}
"""

_SHORT_SCORE_PROMPT_TEMPLATE = """You are PATHMIND's strict but fair examiner. Score these short answers against their rubrics.

Aspiration context: {aspiration}

For each item, award 0 to max_points (integers only; partial credit allowed). Be honest: a vague or
wrong answer gets low marks. An empty answer gets 0.

Return ONLY a JSON array, no markdown fences, no commentary:
[
  {{"question_id": "q2", "score": 6, "feedback": "one sentence on what was good/missing"}},
  ...
]

Items:
{items_json}
"""


def _sanitize_questions(questions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Questions safe for the frontend: correct answers stripped."""
    out = []
    for q in questions:
        q2 = {k: v for k, v in q.items() if k not in ("correct_option", "correct_answer")}
        out.append(q2)
    return out


def _validate_and_normalize(raw: Dict[str, Any]) -> Dict[str, Any]:
    """Validate the LLM's test JSON; raise ValueError on unusable output."""
    questions = raw.get("questions")
    if not isinstance(questions, list) or not (8 <= len(questions) <= 12):
        raise ValueError(
            f"LLM returned {len(questions) if isinstance(questions, list) else 'non-list'} "
            "questions; need 8-12."
        )
    normalized: List[Dict[str, Any]] = []
    for i, q in enumerate(questions):
        if not isinstance(q, dict) or not q.get("question"):
            raise ValueError(f"question {i} is malformed")
        qtype = q.get("type")
        if qtype not in VALID_TYPES:
            raise ValueError(f"question {i} has invalid type {qtype!r}")
        nq: Dict[str, Any] = {
            "id": str(q.get("id") or f"q{i + 1}"),
            "type": qtype,
            "question": str(q["question"]),
            "points": int(q.get("points") or 0),
            "skill_tag": str(q.get("skill_tag") or "general"),
        }
        if qtype == "mcq":
            options = q.get("options")
            if not isinstance(options, list) or len(options) != 4:
                raise ValueError(f"mcq {nq['id']} needs exactly 4 options")
            correct = q.get("correct_option", q.get("correct_answer"))
            # Accept 0-based int, 1-based int, or "A"/"B"/"C"/"D" letter
            if isinstance(correct, str) and correct.strip().upper() in ("A", "B", "C", "D"):
                correct = "ABCD".index(correct.strip().upper())
            try:
                correct = int(correct)
            except (TypeError, ValueError):
                raise ValueError(f"mcq {nq['id']} has invalid correct_option")
            if correct == 0 and str(q.get("correct_option", "")).strip() in ("", "0"):
                # ambiguous — but 0 is a legal answer; accept as-is
                pass
            if not 0 <= correct <= 3:
                # tolerate 1-based indexing from the model
                if 1 <= correct <= 4:
                    correct = correct - 1
                else:
                    raise ValueError(f"mcq {nq['id']} correct_option out of range")
            nq["options"] = [str(o) for o in options]
            nq["correct_option"] = correct
            if nq["points"] <= 0:
                nq["points"] = 4
        elif qtype == "short":
            nq["rubric"] = str(q.get("rubric") or "Award marks for correctness, depth, and use of domain concepts.")
            if nq["points"] <= 0:
                nq["points"] = 8
        else:  # self_assess
            nq["points"] = 0  # never scored; informational only
        normalized.append(nq)

    # Enforce unique ids
    seen = set()
    for nq in normalized:
        if nq["id"] in seen:
            nq["id"] = f"{nq['id']}_{uuid.uuid4().hex[:4]}"
        seen.add(nq["id"])

    time_min = raw.get("time_suggestion_minutes")
    try:
        time_min = max(5, min(60, int(time_min)))
    except (TypeError, ValueError):
        time_min = 20

    total_points = sum(q["points"] for q in normalized if q["type"] in ("mcq", "short"))
    return {
        "questions": normalized,
        "time_suggestion_minutes": time_min,
        "total_points": total_points,
    }


def _verification_summary(verification_data: Optional[Dict[str, Any]]) -> str:
    if not verification_data:
        return "none provided"
    parts = []
    for k, v in verification_data.items():
        s = str(v)
        if len(s) > 120:
            s = s[:120] + "..."
        parts.append(f"{k}: {s}")
    return "; ".join(parts) or "none provided"


class AspirationTestService:
    def __init__(self, store: Optional[Any] = None):
        # Store is duck-typed (PmStore in production, fake in tests).
        # PmStore is imported lazily so this module loads without the
        # supabase package installed.
        self._store = store

    @property
    def store(self) -> Any:
        if self._store is None:
            from backend.services.pm_store import get_pm_store
            self._store = get_pm_store()
        return self._store

    # ------------------------------------------------------------------
    async def generate_test(
        self,
        person_id: str,
        aspiration: str,
        stage: str,
        user_type: str,
        verification_data: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Generate a domain-aware entrance test. Returns the test with correct
        answers STRIPPED. Raises GeminiUnavailable when the model cannot serve
        (caller must NOT fabricate a test).
        """
        aspiration = (aspiration or "").strip()
        if len(aspiration) < 5:
            raise ValueError("Aspiration is required to generate a test.")
        stage = (stage or "").strip() or "unspecified"
        user_type = (user_type or "").strip() or "unspecified"

        prompt = _TEST_PROMPT_TEMPLATE.format(
            aspiration=aspiration,
            stage=stage,
            user_type=user_type,
            verification_summary=_verification_summary(verification_data),
            _DOMAIN_GUIDANCE=_DOMAIN_GUIDANCE,
        )
        started = time.time()
        # generate_text_resilient is blocking; run off the event loop.
        text = await asyncio.to_thread(
            generate_text_resilient, prompt, feature="aspiration_test"
        )
        logger.info(
            "aspiration_test.generated person=%s ms=%d",
            person_id[:8], int((time.time() - started) * 1000),
        )

        cleaned = text.strip()
        if cleaned.startswith("```"):
            # tolerate fenced output even though the prompt forbids it
            parts = cleaned.split("```")
            cleaned = parts[1] if len(parts) > 1 else cleaned
            if cleaned.lstrip().startswith("json"):
                cleaned = cleaned.lstrip()[4:]
        try:
            raw = json.loads(cleaned.strip())
        except json.JSONDecodeError as e:
            raise ValueError(f"Test generator returned invalid JSON: {e}") from e

        norm = _validate_and_normalize(raw)
        test_id = f"t_{uuid.uuid4().hex[:12]}"

        full_record = {
            "test_id": test_id,
            "aspiration": aspiration,
            "stage": stage,
            "user_type": user_type,
            "verification_summary": _verification_summary(verification_data),
            "questions": norm["questions"],  # WITH correct_option — backend only
            "total_points": norm["total_points"],
            "time_suggestion_minutes": norm["time_suggestion_minutes"],
            "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        }
        await self.store.save_aspiration_test(person_id, full_record)

        return {
            "test_id": test_id,
            "aspiration": aspiration,
            "stage": stage,
            "user_type": user_type,
            "questions": _sanitize_questions(norm["questions"]),
            "total_points": norm["total_points"],
            "time_suggestion_minutes": norm["time_suggestion_minutes"],
        }

    # ------------------------------------------------------------------
    async def evaluate_test(
        self,
        person_id: str,
        test_id: str,
        answers: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """
        Score a submitted test. MCQs are deterministic; short answers go
        through a rubric-guided Gemini call (NEEDS_REVIEW when unavailable).
        """
        test = await self.store.get_aspiration_test(person_id, test_id)
        if not test:
            raise KeyError(f"test {test_id} not found for this user")

        questions: List[Dict[str, Any]] = test.get("questions", [])
        by_id = {q["id"]: q for q in questions}
        answer_map = {
            str(a.get("question_id")): a.get("answer") for a in (answers or [])
            if isinstance(a, dict) and a.get("question_id")
        }

        per_question: List[Dict[str, Any]] = []
        skill_stats: Dict[str, Dict[str, Any]] = {}
        short_items: List[Dict[str, Any]] = []

        def _skill(tag: str) -> Dict[str, Any]:
            return skill_stats.setdefault(
                tag, {"earned": 0, "max": 0, "scored_max": 0, "self_ratings": []}
            )

        for q in questions:
            qid = q["id"]
            tag = q.get("skill_tag") or "general"
            raw_answer = answer_map.get(qid)
            entry: Dict[str, Any] = {
                "question_id": qid,
                "type": q["type"],
                "skill_tag": tag,
                "points": q["points"],
            }

            if q["type"] == "mcq":
                st = _skill(tag)
                st["max"] += q["points"]
                st["scored_max"] += q["points"]  # MCQs are always scored
                chosen = self._normalize_mcq_answer(raw_answer, q["options"])
                entry["answered"] = chosen is not None
                if chosen is not None and chosen == q["correct_option"]:
                    entry["score"] = q["points"]
                    entry["correct"] = True
                    st["earned"] += q["points"]
                else:
                    entry["score"] = 0
                    entry["correct"] = False
            elif q["type"] == "short":
                st = _skill(tag)
                st["max"] += q["points"]
                text_answer = str(raw_answer or "").strip()
                entry["answered"] = bool(text_answer)
                entry["score"] = None  # filled by the Gemini pass below
                entry["status"] = "PENDING"
                short_items.append({
                    "question_id": qid,
                    "question": q["question"],
                    "rubric": q.get("rubric", ""),
                    "max_points": q["points"],
                    "answer": text_answer[:2000],
                })
            else:  # self_assess
                rating = self._normalize_rating(raw_answer)
                _skill(tag)["self_ratings"].append(rating) if rating else None
                entry["answered"] = rating is not None
                entry["rating"] = rating
                entry["score"] = 0  # informational; excluded from totals
            per_question.append(entry)

        # Score short answers via one rubric-guided Gemini call.
        short_results: Dict[str, Dict[str, Any]] = {}
        short_unavailable = False
        if short_items:
            try:
                short_results = await self._score_short_answers(
                    aspiration=test.get("aspiration", ""), items=short_items
                )
            except GeminiUnavailable as e:
                short_unavailable = True
                logger.warning("aspiration_test.short_scoring_unavailable: %s", e)

        for entry in per_question:
            if entry["type"] != "short":
                continue
            qid = entry["question_id"]
            res = short_results.get(qid)
            if res is None:
                entry["score"] = None
                entry["status"] = "NEEDS_REVIEW"
                entry["feedback"] = (
                    "Could not be auto-scored right now; a mentor review is pending."
                )
            else:
                entry["score"] = res["score"]
                entry["status"] = "SCORED"
                entry["feedback"] = res.get("feedback", "")
                sk = _skill(entry["skill_tag"])
                sk["earned"] += res["score"]
                sk["scored_max"] += entry["points"]  # only scored shorts count

        max_score = sum(
            q["points"] for q in questions if q["type"] in ("mcq", "short")
        )
        scored_max = sum(
            e["points"] for e in per_question
            if e["type"] in ("mcq", "short") and e.get("status", "SCORED") == "SCORED"
        )
        score = sum(e["score"] or 0 for e in per_question if isinstance(e.get("score"), int))
        percentage = round(100.0 * score / scored_max, 1) if scored_max else 0.0

        skill_breakdown = {}
        for tag, st in skill_stats.items():
            avg_rating = (
                round(sum(st["self_ratings"]) / len(st["self_ratings"]), 1)
                if st["self_ratings"] else None
            )
            # Skills whose questions are all pending review get no percentage
            # (honest) rather than a misleading 0%.
            pct = (
                round(100.0 * st["earned"] / st["scored_max"], 1)
                if st["scored_max"] else None
            )
            skill_breakdown[tag] = {
                "earned": st["earned"],
                "max": st["max"],
                "percentage": pct,
                "avg_self_rating": avg_rating,
            }

        strengths = sorted(
            t for t, s in skill_breakdown.items()
            if s["percentage"] is not None and s["percentage"] >= 70
        )
        gaps = sorted(
            t for t, s in skill_breakdown.items()
            if s["percentage"] is not None and s["percentage"] <= 40
        )
        recommended_focus = self._recommended_focus(gaps, strengths, short_unavailable)

        evaluation = {
            "result_id": f"r_{uuid.uuid4().hex[:12]}",
            "test_id": test_id,
            "aspiration": test.get("aspiration", ""),
            "score": score,
            "max_score": max_score,
            "scored_max": scored_max,
            "percentage": percentage,
            "skill_breakdown": skill_breakdown,
            "strengths": strengths,
            "gaps": gaps,
            "recommended_focus": recommended_focus,
            "short_answers_pending_review": short_unavailable,
            "per_question": [
                {k: v for k, v in e.items()} for e in per_question
            ],
            "evaluated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        }
        await self.store.save_test_result(person_id, {
            **evaluation,
            "answers": [
                {"question_id": str(a.get("question_id")), "answer": a.get("answer")}
                for a in (answers or []) if isinstance(a, dict)
            ],
        })
        return evaluation

    # ------------------------------------------------------------------
    @staticmethod
    def _normalize_mcq_answer(answer: Any, options: List[str]) -> Optional[int]:
        """Accept an option index (int) or option text; return 0-based index or None."""
        if answer is None or answer == "":
            return None
        if isinstance(answer, bool):
            return None
        if isinstance(answer, int):
            return answer if 0 <= answer < len(options) else None
        s = str(answer).strip()
        if s.upper() in ("A", "B", "C", "D"):
            return "ABCD".index(s.upper())
        try:
            n = int(s)
            if 0 <= n < len(options):
                return n
        except ValueError:
            pass
        # match option text (case-insensitive)
        for i, opt in enumerate(options):
            if str(opt).strip().lower() == s.lower():
                return i
        return None

    @staticmethod
    def _normalize_rating(answer: Any) -> Optional[int]:
        try:
            n = int(str(answer).strip())
        except (TypeError, ValueError):
            return None
        return n if 1 <= n <= 5 else None

    async def _score_short_answers(
        self, aspiration: str, items: List[Dict[str, Any]]
    ) -> Dict[str, Dict[str, Any]]:
        prompt = _SHORT_SCORE_PROMPT_TEMPLATE.format(
            aspiration=aspiration, items_json=json.dumps(items, ensure_ascii=False)
        )
        text = await asyncio.to_thread(
            generate_text_resilient, prompt, feature="aspiration_test_scoring"
        )
        cleaned = text.strip()
        if cleaned.startswith("```"):
            parts = cleaned.split("```")
            cleaned = parts[1] if len(parts) > 1 else cleaned
            if cleaned.lstrip().startswith("json"):
                cleaned = cleaned.lstrip()[4:]
        try:
            arr = json.loads(cleaned.strip())
        except json.JSONDecodeError as e:
            raise GeminiUnavailable(f"scorer returned invalid JSON: {e}") from e
        out: Dict[str, Dict[str, Any]] = {}
        # clamp scores to each question's max
        max_by_id = {it["question_id"]: it["max_points"] for it in items}
        if isinstance(arr, list):
            for r in arr:
                if not isinstance(r, dict) or not r.get("question_id"):
                    continue
                qid = str(r["question_id"])
                cap = max_by_id.get(qid)
                if cap is None:
                    continue
                try:
                    s = int(r.get("score", 0))
                except (TypeError, ValueError):
                    s = 0
                out[qid] = {
                    "score": max(0, min(cap, s)),
                    "feedback": str(r.get("feedback", ""))[:500],
                }
        return out

    @staticmethod
    def _recommended_focus(
        gaps: List[str], strengths: List[str], short_pending: bool
    ) -> List[str]:
        focus: List[str] = []
        for g in gaps[:4]:
            focus.append(
                f"Build foundations in '{g}' — start with guided basics before advancing."
            )
        if strengths:
            focus.append(
                f"Leverage your strength in {', '.join(strengths[:3])} while shoring up weaker areas."
            )
        if short_pending:
            focus.append(
                "Some written answers are pending review — your final profile will refine once scored."
            )
        if not focus:
            focus.append(
                "Solid baseline. Push into intermediate material and deliberate practice next."
            )
        return focus


_test_service_instance: Optional[AspirationTestService] = None


def get_test_service() -> AspirationTestService:
    """Process-wide AspirationTestService singleton (PmStore resolved lazily)."""
    global _test_service_instance
    if _test_service_instance is None:
        _test_service_instance = AspirationTestService()
    return _test_service_instance
