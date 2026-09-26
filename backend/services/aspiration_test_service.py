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


def _validate_and_normalize(
    raw: Dict[str, Any], min_questions: int = 8
) -> Dict[str, Any]:
    """Validate the LLM's test JSON; raise ValueError on unusable output."""
    questions = raw.get("questions")
    if not isinstance(questions, list) or not (min_questions <= len(questions) <= 12):
        raise ValueError(
            f"LLM returned {len(questions) if isinstance(questions, list) else 'non-list'} "
            f"questions; need {min_questions}-12."
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

        # Tiered bank-first flow:
        #   1. normalize aspiration -> domain (deterministic alias match)
        #   2. pull VERIFIED > EXPERT_REVIEWED > AI_DRAFT from the bank
        #   3. Gemini tops up any shortfall (stored as AI_DRAFT, never "verified")
        #   4. the test's tier = lowest tier among its questions (honest ceiling)
        domain = await self.store.get_domain_for_aspiration(aspiration)
        bank_rows = await self.store.get_bank_questions(domain, limit=12)
        bank_questions = [self._bank_row_to_question(r) for r in bank_rows]

        needed = max(0, 12 - len(bank_questions))
        ai_questions: List[Dict[str, Any]] = []
        if needed > 0:
            ai_questions = await self._generate_ai_questions(
                aspiration, stage, user_type, verification_data, needed
            )
            # Persist AI drafts so the audit map can reference them.
            for q in ai_questions:
                try:
                    qid = await self.store.save_bank_question({
                        "domain": domain,
                        "aspiration_aliases": [aspiration.lower()[:80]],
                        "question_type": q["type"],
                        "question_text": q["question"],
                        "options": q.get("options"),
                        "correct_option": str(q.get("correct_option"))
                        if q.get("correct_option") is not None else None,
                        "rubric": q.get("rubric"),
                        "skill_tag": q.get("skill_tag"),
                        "difficulty": q.get("difficulty", 3),
                        "points": q.get("points", 1),
                        "source_type": "AI_GENERATED",
                        "source_name": "PathMind AI draft",
                        "source_detail": "Generated for this test; awaiting review",
                        "verification_status": "AI_DRAFT",
                        "created_by": "test-generator",
                    })
                    q["_bank_id"] = qid
                    q["_tier"] = "AI_DRAFT"
                except Exception:
                    logger.warning("aspiration_test.bank_insert_failed person=%s", person_id[:8])

        for r, q in zip(bank_rows, bank_questions):
            q["_bank_id"] = r.get("question_id")
            q["_tier"] = r.get("verification_status") or "AI_DRAFT"

        questions = (bank_questions + ai_questions)[:12]
        if len(questions) < 8:
            raise GeminiUnavailable(
                "Could not assemble a usable test: bank yielded "
                f"{len(bank_questions)} and the generator produced "
                f"{len(ai_questions)}. Try again shortly."
            )

        test_id = f"t_{uuid.uuid4().hex[:12]}"
        test_tier = self._test_tier(questions)
        provenance = self._test_provenance_label(questions, domain)

        full_record = {
            "test_id": test_id,
            "aspiration": aspiration,
            "stage": stage,
            "user_type": user_type,
            "domain": domain,
            "test_tier": test_tier,
            "provenance": provenance,
            "verification_summary": _verification_summary(verification_data),
            "questions": questions,  # WITH correct_option — backend only
            "total_points": sum(q.get("points", 1) for q in questions),
            "time_suggestion_minutes": max(10, len(questions) * 2),
            "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        }
        await self.store.save_aspiration_test(person_id, full_record)

        # Audit trail + usage rotation for bank questions.
        try:
            await self.store.record_test_questions(
                test_id, [(q["_bank_id"], q["_tier"]) for q in questions if q.get("_bank_id")]
            )
            await self.store.bump_question_usage(
                [q["_bank_id"] for q in questions if q.get("_bank_id")]
            )
        except Exception:
            logger.warning("aspiration_test.audit_failed person=%s", person_id[:8])

        sanitized = _sanitize_questions(questions)
        for s, q in zip(sanitized, questions):
            s["tier"] = q.get("_tier", "AI_DRAFT")
            if q.get("_tier") in ("VERIFIED", "EXPERT_REVIEWED"):
                s["source_name"] = q.get("source_name")

        return {
            "test_id": test_id,
            "aspiration": aspiration,
            "stage": stage,
            "user_type": user_type,
            "domain": domain,
            "test_tier": test_tier,
            "provenance": provenance,
            "questions": sanitized,
            "total_points": full_record["total_points"],
            "time_suggestion_minutes": full_record["time_suggestion_minutes"],
        }

    # ------------------------------------------------------------------
    # Bank-first helpers
    # ------------------------------------------------------------------
    @staticmethod
    def _bank_row_to_question(row: Dict[str, Any]) -> Dict[str, Any]:
        # Same schema as _validate_and_normalize output: id/type/question.
        q: Dict[str, Any] = {
            "id": f"bank_{row.get('question_id')}",
            "type": row.get("question_type") or "mcq",
            "question": row.get("question_text") or "",
            "skill_tag": row.get("skill_tag") or "general",
            "difficulty": row.get("difficulty") or 3,
            "points": row.get("points") or 1,
            "source_name": row.get("source_name"),
            "source_detail": row.get("source_detail"),
        }
        if row.get("options"):
            q["options"] = row["options"]
        if row.get("correct_option") is not None and row.get("correct_option") != "":
            # Bank stores TEXT; the scorer compares ints — coerce (letters tolerated).
            raw_correct = str(row["correct_option"]).strip().upper()
            if raw_correct in ("A", "B", "C", "D"):
                q["correct_option"] = "ABCD".index(raw_correct)
            else:
                try:
                    q["correct_option"] = int(raw_correct)
                except (TypeError, ValueError):
                    q["correct_option"] = row["correct_option"]
        if row.get("rubric"):
            q["rubric"] = row["rubric"]
        return q

    @staticmethod
    def _test_tier(questions: List[Dict[str, Any]]) -> str:
        """Honest ceiling: the test is only as verified as its weakest question."""
        order = {"VERIFIED": 0, "EXPERT_REVIEWED": 1, "AI_DRAFT": 2}
        worst = max(order.get(q.get("_tier", "AI_DRAFT"), 2) for q in questions)
        return {0: "VERIFIED", 1: "EXPERT_REVIEWED", 2: "AI_DRAFT"}[worst]

    @staticmethod
    def _test_provenance_label(
        questions: List[Dict[str, Any]], domain: str
    ) -> Dict[str, Any]:
        tiers = [q.get("_tier", "AI_DRAFT") for q in questions]
        n_verified = sum(1 for t in tiers if t == "VERIFIED")
        n_reviewed = sum(1 for t in tiers if t == "EXPERT_REVIEWED")
        sources = sorted({
            q.get("source_name")
            for q in questions
            if q.get("_tier") == "VERIFIED" and q.get("source_name")
        })
        total = len(questions)
        if n_verified == total:
            label = (
                f"Verified test — all {total} questions from "
                f"{', '.join(sources) if sources else 'official sources'}."
            )
        elif n_verified > 0 or n_reviewed > 0:
            label = (
                f"{n_verified + n_reviewed} of {total} questions from verified or "
                f"expert-reviewed sources"
                f"{' (' + ', '.join(sources) + ')' if sources else ''}; "
                "the rest are AI-generated practice questions."
            )
        else:
            label = (
                "Practice test — AI-generated questions, not from any official "
                "source. Warm-up only, not a verdict."
                + (
                    " No verified questions exist for this field yet."
                    if domain not in ("general",) else ""
                )
            )
        return {
            "test_tier": AspirationTestService._test_tier(questions),
            "total": total,
            "verified_count": n_verified,
            "expert_reviewed_count": n_reviewed,
            "sources": sources,
            "label": label,
        }

    async def _generate_ai_questions(
        self,
        aspiration: str,
        stage: str,
        user_type: str,
        verification_data: Optional[Dict[str, Any]],
        count: int,
    ) -> List[Dict[str, Any]]:
        """Generate `count` AI-draft questions via Gemini (honest 503 when down)."""
        prompt = _TEST_PROMPT_TEMPLATE.format(
            aspiration=aspiration,
            stage=stage,
            user_type=user_type,
            verification_summary=_verification_summary(verification_data),
            _DOMAIN_GUIDANCE=_DOMAIN_GUIDANCE,
        ) + (
            f"\nGenerate exactly {count} questions (not 8-12). "
            "These are AI-generated practice questions — keep them diagnostic, "
            "never claim official provenance."
        )
        started = time.time()
        text = await asyncio.to_thread(
            generate_text_resilient, prompt, feature="aspiration_test"
        )
        logger.info(
            "aspiration_test.ai_topup person=%s n=%d ms=%d",
            aspiration[:16], count, int((time.time() - started) * 1000),
        )
        cleaned = text.strip()
        if cleaned.startswith("```"):
            parts = cleaned.split("```")
            cleaned = parts[1] if len(parts) > 1 else cleaned
            if cleaned.lstrip().startswith("json"):
                cleaned = cleaned.lstrip()[4:]
        try:
            raw = json.loads(cleaned.strip())
        except json.JSONDecodeError as e:
            raise ValueError(f"Test generator returned invalid JSON: {e}") from e
        norm = _validate_and_normalize(raw, min_questions=1)
        return norm["questions"][:count]

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
