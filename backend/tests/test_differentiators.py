"""
Tests for the five PathMind differentiators (main product).

1. Longitudinal memory as product: /journey-timeline returns a chronological,
   evidence-tagged timeline (not one-shot chat context).
2. India resource graph: covered by test_intelligence_pack.py (KB retrieval,
   verified URLs, estimate-labeled salaries) — no new code here.
3. Accountability loop: /check-in returns overdue + week plan-vs-actual +
   a non-judgmental intervention for the most overdue item.
4. Verified, not vibes: skill claims are detected and the counselor proposes
   evidence instead of accepting them at face value.
5. Goal-first, not tech-first: the counselor takes non-tech aspirations
   literally and does not funnel toward coding.

No network, no Supabase, no LLM key required (deterministic fallbacks).
"""
import asyncio
from datetime import datetime, timedelta, timezone

import pytest

from backend.services.counseling import (
    CounselingAgent,
    detect_skill_claims,
    verification_nudge_text,
)
from backend.core.assessment_schemas import CounselingProfile


def _profile(**kw):
    base = dict(person_id="tester-1", candidate_directions=[])
    base.update(kw)
    return CounselingProfile(**base)


def _bare_agent():
    """CounselingAgent without __init__ (which needs Supabase env).

    Tests the real counsel_chat code paths: model=None exercises the
    deterministic fallback; a stub model exercises the LLM prompt wiring.
    """
    agent = CounselingAgent.__new__(CounselingAgent)
    agent.model = None
    return agent


class _PromptCapturingModel:
    def __init__(self):
        self.last_prompt = None

    class _Resp:
        text = "canned counselor reply"

    def generate_content(self, prompt):
        self.last_prompt = prompt
        return self._Resp()


class TestSkillClaimDetection:
    def test_detects_know_phrasing(self):
        claims = detect_skill_claims("I know Python and machine learning")
        assert any("python" in c for c in claims)

    def test_detects_experience_phrasing(self):
        claims = detect_skill_claims("I'm experienced in data analysis")
        assert len(claims) >= 1

    def test_detects_built_phrasing(self):
        claims = detect_skill_claims("I built a portfolio website last year")
        assert len(claims) >= 1

    def test_no_false_positive_on_aspiration(self):
        # "I want to open a tea shop" is a goal, not a skill claim.
        assert detect_skill_claims("I want to open a tea shop") == []

    def test_no_false_positive_on_question(self):
        assert detect_skill_claims("What should I learn next?") == []


class TestVerificationNudge:
    def test_none_when_no_claims(self):
        assert verification_nudge_text([]) is None

    def test_nudge_marks_unverified(self):
        nudge = verification_nudge_text(["python"])
        assert nudge is not None
        assert "UNVERIFIED" in nudge
        assert "evidence" in nudge.lower()

    def test_nudge_forbids_flattery(self):
        nudge = verification_nudge_text(["python"]).lower()
        assert "do not" in nudge and "flatter" in nudge


class TestCounselorVerifiedNotVibes:
    def test_fallback_proposes_verification_not_flattery(self):
        agent = _bare_agent()
        nudge = verification_nudge_text(detect_skill_claims("I know Python"))
        reply = agent.counsel_chat(
            person_id="tester-1",
            user_message="I know Python, what career fits me?",
            profile=_profile(),
            verification_nudge=nudge,
        )
        text = reply.content.lower()
        assert "verify" in text
        assert "face value" in text
        # Must not flatter the unverified claim.
        assert "you're great at python" not in text
        assert "your python skills" not in text

    def test_llm_prompt_carries_verification_nudge(self):
        agent = _bare_agent()
        agent.model = _PromptCapturingModel()
        nudge = verification_nudge_text(detect_skill_claims("I know Python"))
        agent.counsel_chat(
            person_id="tester-1",
            user_message="I know Python, what career fits me?",
            profile=_profile(),
            verification_nudge=nudge,
        )
        prompt = agent.model.last_prompt
        assert prompt is not None
        assert "UNVERIFIED SKILL CLAIM" in prompt


class TestGoalFirstNotTechFirst:
    def test_llm_prompt_has_goal_first_guardrail(self):
        agent = _bare_agent()
        agent.model = _PromptCapturingModel()
        agent.counsel_chat(
            person_id="tester-1",
            user_message="I want to open a tea shop, guide me",
            profile=_profile(candidate_directions=["Tea shop owner"]),
        )
        prompt = agent.model.last_prompt
        assert prompt is not None
        assert "GOAL-FIRST" in prompt
        assert "tea shop" in prompt.lower()

    def test_nontech_aspiration_not_funneled_to_coding(self):
        agent = _bare_agent()
        reply = agent.counsel_chat(
            person_id="tester-1",
            user_message="I want to open a tea shop, guide me",
            profile=_profile(candidate_directions=["Tea shop owner"]),
        )
        text = reply.content.lower()
        assert "tea shop owner" in text
        for tech_word in ("software engineer", "coding", "learn to code",
                          "ai engineer", "programming"):
            assert tech_word not in text, f"tech funneling leaked: {tech_word}"


class _FakeCommitmentService:
    def __init__(self, commitments):
        self._commitments = commitments

    async def list_commitments(self, person_id, status=None):
        out = list(self._commitments)
        if status:
            out = [c for c in out if c.get("status") == status]
        return out


class TestAccountabilityCheckIn:
    def test_check_in_reports_overdue_and_plan_vs_actual(self, monkeypatch):
        import backend.api.accountability_routes as routes

        now = datetime.now(timezone.utc)
        overdue_due = (now - timedelta(days=3)).isoformat()
        done_due = (now - timedelta(days=2)).isoformat()
        future_due = (now + timedelta(days=2)).isoformat()
        commitments = [
            {"commitment_id": "c1", "title": "Finish DSA module",
             "due_at": overdue_due, "status": "planned"},
            {"commitment_id": "c2", "title": "Revise notes",
             "due_at": done_due, "status": "completed",
             "completed_at": done_due},
            {"commitment_id": "c3", "title": "Mock test",
             "due_at": future_due, "status": "planned"},
        ]
        monkeypatch.setattr(
            routes, "get_service",
            lambda: _FakeCommitmentService(commitments),
        )
        result = asyncio.run(routes.accountability_check_in("tester-1"))
        assert len(result["overdue"]) == 1
        assert result["overdue"][0]["title"] == "Finish DSA module"
        week = result["week_plan_vs_actual"]
        assert week["planned"] == 2
        assert week["completed"] == 1
        assert week["completion_rate"] == 0.5
        iv = result["intervention"]
        assert iv is not None
        msg = iv["non_judgmental_message"].lower()
        assert "reschedule" in msg  # concrete option, not shame
        assert len(iv["suggested_options"]) >= 3

    def test_check_in_no_overdue_no_intervention(self, monkeypatch):
        import backend.api.accountability_routes as routes

        monkeypatch.setattr(
            routes, "get_service", lambda: _FakeCommitmentService([]))
        result = asyncio.run(routes.accountability_check_in("tester-1"))
        assert result["overdue"] == []
        assert result["intervention"] is None
        assert result["week_plan_vs_actual"]["completion_rate"] is None


class _FakeMemoryService:
    def __init__(self, memories):
        self._memories = memories

    async def get_long_term(self, person_id, limit=50):
        return self._memories[:limit]


class TestJourneyTimeline:
    def test_timeline_is_chronological_and_evidence_tagged(self, monkeypatch):
        import backend.api.memory_tier_routes as routes
        import backend.services.commitment_service as cs_mod

        memories = [
            {"created_at": "2026-10-10T10:00:00+00:00",
             "memory_type": "EPISODIC", "nature": "DECISION",
             "title": "Chose data analyst path", "content": "picked DA",
             "evidence_verification_status": "SELF_REPORTED"},
            {"created_at": "2026-10-12T10:00:00+00:00",
             "memory_type": "SEMANTIC", "nature": "SKILL_KNOWLEDGE",
             "title": "Python basics", "content": "loops",
             "evidence_verification_status": "VERIFIED"},
        ]
        monkeypatch.setattr(
            routes, "get_service", lambda: _FakeMemoryService(memories))
        monkeypatch.setattr(
            cs_mod, "CommitmentService",
            lambda: _FakeCommitmentService([
                {"title": "Week 1 plan", "status": "completed",
                 "completed_at": "2026-10-11T10:00:00+00:00",
                 "updated_at": "2026-10-11T10:00:00+00:00"},
            ]),
        )
        result = asyncio.run(routes.journey_timeline("tester-1"))
        tl = result["timeline"]
        assert result["event_count"] == 3
        ats = [e["at"] for e in tl]
        assert ats == sorted(ats), "timeline must be chronological"
        kinds = {e["kind"] for e in tl}
        assert "COMMITMENT_COMPLETED" in kinds
        skill = next(e for e in tl if e["title"] == "Python basics")
        assert skill["evidence"] == "VERIFIED"

    def test_timeline_empty_is_not_an_error(self, monkeypatch):
        import backend.api.memory_tier_routes as routes
        import backend.services.commitment_service as cs_mod

        monkeypatch.setattr(
            routes, "get_service", lambda: _FakeMemoryService([]))
        monkeypatch.setattr(
            cs_mod, "CommitmentService",
            lambda: _FakeCommitmentService([]),
        )
        result = asyncio.run(routes.journey_timeline("tester-1"))
        assert result["timeline"] == []
        assert result["event_count"] == 0
