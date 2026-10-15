"""
Tests for the authenticity batch (production-grade PathMind).

Covers: skill verification lifecycle + anti-resume, calibrated uncertainty,
computed trajectory, decision journal, adaptive projection, stage-gate
visibility, pivot detection, proactive accountability / failure memory in
the counselor, constraint-honest prompt, personal readiness context, and
the live-jobs fetcher. Hermetic: no network, no Supabase, no LLM key.
"""
import asyncio
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import pytest

from backend.services.skill_profile_service import SkillProfileService
from backend.services.trajectory_service import TrajectoryService
from backend.services.counseling import detect_pivot_talk, pivot_nudge_text
from backend.tests.test_differentiators import (
    _bare_agent as _bare,
    _profile,
    _PromptCapturingModel,
)
from backend.core.assessment_schemas import CounselingFact


class _FakeMem:
    """In-memory stand-in for LongitudinalMemoryService."""

    def __init__(self):
        self.long_term = []
        self.signals = []

    async def record_long_term(self, person_id, content, title,
                               memory_type="EPISODIC", importance="MEDIUM",
                               related_domain=None, metadata=None):
        m = {
            "memory_id": f"m{len(self.long_term)}",
            "title": title, "content": content, "memory_type": memory_type,
            "importance": importance, "related_domain": related_domain,
            "metadata": metadata or {},
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        self.long_term.append(m)
        return m

    async def get_long_term(self, person_id, limit=50):
        return sorted(self.long_term, key=lambda m: m["created_at"],
                      reverse=True)[:limit]

    async def record_signal(self, person_id, signal_type, content,
                            related_domain=None, metadata=None):
        self.signals.append({"signal_type": signal_type, "content": content})
        return {}


class _FakeCommitments:
    def __init__(self, commitments):
        self._c = commitments

    async def list_commitments(self, person_id, status=None):
        out = list(self._c)
        if status:
            out = [c for c in out if c.get("status") == status]
        return out


class _FakeTraj(TrajectoryService):
    def __init__(self, mem, com):
        super().__init__(memory=mem, commitments=com)


def _com(days_ago, status, title="Work"):
    return {
        "commitment_id": f"c-{title}-{days_ago}-{status}",
        "title": title,
        "due_at": (datetime.now(timezone.utc) - timedelta(days=days_ago)).isoformat(),
        "status": status,
    }


class TestSkillLifecycle:
    def test_claim_is_self_reported_not_verified(self):
        svc = SkillProfileService(_FakeMem())
        r = asyncio.run(svc.claim_skill("p1", "Python"))
        assert r["status"] == "SELF_REPORTED"
        prof = asyncio.run(svc.skill_profile("p1"))
        assert prof["counts"] == {"proven": 0, "claimed": 1, "gaps": 0}
        assert prof["proven"] == []

    def test_verify_with_real_code_flips_to_verified(self):
        mem = _FakeMem()
        svc = SkillProfileService(mem)
        asyncio.run(svc.claim_skill("p1", "Python"))
        r = asyncio.run(svc.verify_skill(
            "p1", "Python",
            {"code": "def f(x: int) -> int:\n    assert x > 0\n    return x * 2  # tested",
             "repo_url": "", "explanation": ""}))
        assert r["status"] == "VERIFIED"
        assert mem.signals and mem.signals[0]["signal_type"] == "MILESTONE"
        prof = asyncio.run(svc.skill_profile("p1"))
        assert prof["counts"]["proven"] == 1
        assert prof["counts"]["claimed"] == 0
        assert prof["proven"][0]["skill"] == "python"

    def test_verify_with_junk_stays_unverified(self):
        svc = SkillProfileService(_FakeMem())
        asyncio.run(svc.claim_skill("p1", "Python"))
        r = asyncio.run(svc.verify_skill("p1", "Python", {"code": "x"}))
        assert r["status"] == "UNVERIFIED"
        prof = asyncio.run(svc.skill_profile("p1"))
        assert prof["counts"]["proven"] == 0
        assert prof["counts"]["claimed"] == 1

    def test_latest_wins_across_attempts(self):
        svc = SkillProfileService(_FakeMem())
        asyncio.run(svc.claim_skill("p1", "Go"))
        asyncio.run(svc.verify_skill("p1", "Go", {"code": "x"}))
        assert asyncio.run(svc.skill_profile("p1"))["counts"]["proven"] == 0
        asyncio.run(svc.verify_skill(
            "p1", "Go",
            {"code": "def g() -> None:\n    assert True\n    import pytest",
             "repo_url": "", "explanation": ""}))
        prof = asyncio.run(svc.skill_profile("p1"))
        assert prof["counts"]["proven"] == 1


class TestCalibratedUncertainty:
    def test_no_hits_returns_explicit_marker(self):
        from backend.services.intelligence_service import build_evidence_block
        block = build_evidence_block("xqztlp flibber wobble " * 4)
        assert block is not None
        assert block.startswith("NO_VERIFIED_RESULTS")

    def test_fallback_says_it_plainly(self):
        agent = _bare()
        reply = agent.counsel_chat(
            person_id="p1", user_message="xqztlp?",
            profile=_profile(),
            evidence_block="NO_VERIFIED_RESULTS: nothing relevant here.",
        )
        assert "don't have verified data" in reply.content.lower()
        assert "Verified entries relevant" not in reply.content

    def test_guideline_in_llm_prompt(self):
        agent = _bare()
        agent.model = _PromptCapturingModel()
        agent.counsel_chat(person_id="p1", user_message="hi", profile=_profile())
        assert "CALIBRATED UNCERTAINTY" in agent.model.last_prompt


class TestTrajectory:
    def _traj(self):
        mem = _FakeMem()
        com = _FakeCommitments([
            _com(3, "completed", "A"), _com(5, "completed", "B"),
            _com(10, "planned", "C"), _com(40, "planned", "Old"),
        ])
        return _FakeTraj(mem, com), mem

    def test_pace_28d(self):
        traj, _ = self._traj()
        pace = asyncio.run(traj.pace("p1"))
        assert pace["due"] == 3 and pace["completed"] == 2
        assert pace["completion_rate"] == round(2 / 3, 2)
        assert pace["completions_per_week"] == round(2 / 4, 2)

    def test_lapsed_is_failure_memory(self):
        traj, _ = self._traj()
        lapsed = asyncio.run(traj.lapsed("p1"))
        assert len(lapsed) == 1 and lapsed[0]["title"] == "Old"
        assert lapsed[0]["days_overdue"] >= 40

    def test_pivots_chronological_with_reasons(self):
        traj, mem = self._traj()
        for title in ("First", "Second"):
            asyncio.run(mem.record_long_term(
                "p1", f"reason-{title}", title, metadata={"nature": "DECISION"}))
        pivots = asyncio.run(traj.pivots("p1"))
        assert [p["title"] for p in pivots] == ["First", "Second"]
        assert all("reason-" in p["reason"] for p in pivots)

    def test_skill_velocity_honest_when_sparse(self):
        traj, mem = self._traj()
        v = asyncio.run(traj.skill_velocity("p1"))
        assert v["verified_count"] == 0 and v["verified_per_30d"] in (0.0, None)

    def test_trajectory_route(self, monkeypatch):
        import backend.api.memory_tier_routes as routes
        import backend.services.trajectory_service as mod

        mem = _FakeMem()
        com = _FakeCommitments([_com(3, "completed", "A")])
        monkeypatch.setattr(mod, "TrajectoryService",
                            lambda: _FakeTraj(mem, com))
        result = asyncio.run(routes.trajectory("p1"))
        assert result["pace_28d"]["completed"] == 1
        assert result["person_id"] == "p1"


class TestDecisionJournal:
    def test_post_and_get(self, monkeypatch):
        import backend.api.memory_tier_routes as routes
        import backend.services.trajectory_service as mod

        mem = _FakeMem()
        monkeypatch.setattr(routes, "get_service", lambda: mem)
        monkeypatch.setattr(mod, "TrajectoryService",
                            lambda: _FakeTraj(mem, _FakeCommitments([])))
        req = SimpleNamespace(title="Leave web dev for data",
                              reason="Market + interest",
                              alternatives_rejected=["Stay"])
        created = asyncio.run(routes.record_decision(req, "p1"))
        assert created["title"].startswith("Leave web")
        listed = asyncio.run(routes.list_decisions("p1"))
        assert len(listed["decisions"]) == 1
        assert listed["decisions"][0]["alternatives_rejected"] == ["Stay"]


class TestProjection:
    def test_projects_from_measured_pace(self, monkeypatch):
        import backend.api.accountability_routes as routes
        import backend.services.trajectory_service as mod

        mem = _FakeMem()
        com = _FakeCommitments(
            [_com(3, "completed", "A"), _com(10, "completed", "B")] +
            [_com(-d, "planned", f"Open{d}") for d in (1, 2, 3, 4)]
        )
        monkeypatch.setattr(mod, "TrajectoryService",
                            lambda: _FakeTraj(mem, com))
        result = asyncio.run(routes.adaptive_projection("p1"))
        assert result["open_commitments"] == 4
        assert result["projected_weeks_remaining"] == round(4 / 0.5, 1)
        assert "measured pace" in result["note"]

    def test_no_pace_no_projection(self, monkeypatch):
        import backend.api.accountability_routes as routes
        import backend.services.trajectory_service as mod

        monkeypatch.setattr(
            mod, "TrajectoryService",
            lambda: _FakeTraj(_FakeMem(), _FakeCommitments([])))
        result = asyncio.run(routes.adaptive_projection("p1"))
        assert result["projected_weeks_remaining"] is None
        assert "No measured pace" in result["note"]


class TestPivotDetection:
    def test_detects_pivot_talk(self):
        assert detect_pivot_talk("I want to switch to design")
        assert detect_pivot_talk("thinking of quitting my course")

    def test_ignores_normal_chat(self):
        assert not detect_pivot_talk("What should I learn next?")
        assert not detect_pivot_talk("I want to open a tea shop")

    def test_fallback_nudges_journaling(self):
        agent = _bare()
        reply = agent.counsel_chat(
            person_id="p1", user_message="I want to switch careers",
            profile=_profile(), pivot_nudge=pivot_nudge_text())
        assert "changing direction" in reply.content.lower()


class TestCoachInitiates:
    def test_fallback_surfaces_overdue(self):
        agent = _bare()
        reply = agent.counsel_chat(
            person_id="p1", user_message="hey", profile=_profile(),
            accountability_prompt="PROACTIVE ACCOUNTABILITY: 2 overdue")
        assert "overdue" in reply.content.lower()

    def test_fallback_references_failure_memory(self):
        agent = _bare()
        reply = agent.counsel_chat(
            person_id="p1", user_message="hey", profile=_profile(),
            failure_prompt="WHAT DIDN'T WORK: 'X' lapsed")
        assert "lapsed" in reply.content.lower()


class TestConstraintHonest:
    def test_constraints_rendered_in_prompt(self):
        agent = _bare()
        agent.model = _PromptCapturingModel()
        profile = _profile(constraints=[
            CounselingFact(category="OBSERVED", claim="Only 2 hours/day available"),
        ])
        agent.counsel_chat(person_id="p1", user_message="plan my week",
                           profile=profile)
        prompt = agent.model.last_prompt
        assert "Only 2 hours/day available" in prompt
        assert "CONSTRAINT-HONEST" in prompt


class TestStageGates:
    def test_gates_explain_locks(self, monkeypatch):
        import sys
        from unittest.mock import MagicMock

        # roadmap_routes builds engine/store at import time (needs Supabase);
        # stub those before first import in this environment.
        monkeypatch.setattr("backend.services.pm_store.get_pm_store",
                            lambda: MagicMock())
        monkeypatch.setattr("backend.services.roadmap_engine.RoadmapEngine",
                            lambda *a, **k: MagicMock())
        monkeypatch.setattr(
            "backend.services.personal_agent_engine.PersonalAgentEngine",
            lambda *a, **k: MagicMock())
        sys.modules.pop("backend.api.roadmap_routes", None)
        import backend.api.roadmap_routes as routes

        stages = [
            SimpleNamespace(stage_id="s1", title="Foundations", locked=False),
            SimpleNamespace(stage_id="s2", title="Build", locked=True),
            SimpleNamespace(stage_id="s3", title="Launch", locked=True),
        ]
        roadmap = SimpleNamespace(current_stage_id="s1")

        async def fake_get_or_create(person_id):
            return roadmap

        monkeypatch.setattr(
            routes, "engine",
            SimpleNamespace(
                get_or_create_roadmap=fake_get_or_create,
                get_all_stages_flat=lambda r: stages,
            ),
        )
        result = asyncio.run(routes.stage_gates("p1"))
        by_id = {s["stage_id"]: s for s in result["stages"]}
        assert by_id["s1"]["locked"] is False
        assert by_id["s1"]["is_current"] is True
        assert "Foundations" in by_id["s2"]["unlock_requirement"]
        assert by_id["s3"]["unlock_requirement"] is not None


class TestPersonalReadiness:
    def test_momentum_appends_without_changing_stage(self):
        from backend.services.intelligence_service import (
            get_intelligence_service, READINESS_STAGES)
        svc = get_intelligence_service()
        base = svc.predict_readiness("I am thinking about a career change")
        personal = svc.predict_readiness(
            "I am thinking about a career change",
            personal_context={"completions_per_week": 1.5, "lapsed": 2})
        assert base and personal
        assert personal["stage"] == base["stage"]
        assert personal["stage"] in READINESS_STAGES
        assert "measured pace" in personal["note"]
        assert "2 commitments lapsed" in personal["note"]


class TestLiveJobs:
    def test_results_are_source_labeled(self):
        from backend.api.intelligence_routes import fetch_live_jobs

        def fake_get(url, params=None, timeout=None):
            class R:
                def json(self):
                    return {"data": [
                        {"title": "Data Analyst", "company_name": "Acme",
                         "location": "Remote", "remote": True,
                         "url": "https://x.example/j/1",
                         "created_at": "2026-10-01"}]}
            return R()

        results = fetch_live_jobs("data analyst", _get=fake_get)
        assert len(results) == 1
        assert results[0]["source"] == "arbeitnow.com"
        assert results[0]["fetched_at"]

    def test_upstream_failure_returns_empty(self):
        from backend.api.intelligence_routes import fetch_live_jobs

        def boom(url, params=None, timeout=None):
            raise ConnectionError("down")

        assert fetch_live_jobs("x", _get=boom) == []
