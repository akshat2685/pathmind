"""
College round-6 regression tests:

- Diagnosis is hybrid RAG of record (covered in
  test_college_dynamic_diagnostic.py); here: engagement ranking.
- Real YouTube engagement statistics (views/likes/comments) rank
  research candidates and attached resources — never fabricated.
- Plan generation runs one bounded, fail-open research pass for the
  first phase whose subject has no cached resources, so a fresh path
  starts with real links instead of empty slots.
"""
import asyncio

import pytest
from fastapi.testclient import TestClient

import backend.main as main_mod
import backend.services.college_resource_pipeline as pipeline_mod
from backend.services.college_resource_pipeline import _engagement_score
from college_testkit import install_fake_adapter

client = TestClient(main_mod.app)

ALICE = {"Authorization": "Bearer alice-token", "Content-Type": "application/json"}
BOB = {"Authorization": "Bearer bob-token", "Content-Type": "application/json"}
ALICE_UID = "11111111-1111-4111-8111-111111111111"


@pytest.fixture(scope="module", autouse=True)
def fake_backend():
    adapter, restore = install_fake_adapter()
    yield adapter
    restore()


def _setup(headers, name, branch, subject_ids, hours=10):
    r = client.post("/api/college/profile",
                    json={"name": name,
                          "email": f"{name.lower()}@example.com"},
                    headers=headers)
    assert r.status_code == 200, r.text
    r = client.post("/api/college/academic-context", json={
        "university_id": "univ_aicte_model", "branch": branch,
        "semester": 3, "subjects": subject_ids,
        "available_hours_per_week": hours,
    }, headers=headers)
    assert r.status_code == 200, r.text


# ---------------------------------------------------------------------------
# Engagement score: real statistics only, absence is never a fake zero-quality
# ---------------------------------------------------------------------------

def test_engagement_score_uses_real_statistics():
    assert _engagement_score({}) == 0.0
    assert _engagement_score(None) == 0.0
    assert _engagement_score("junk") == 0.0
    assert _engagement_score({"view_count": 0, "like_count": 10}) == 0.0
    viral = {"view_count": 2_000_000, "like_count": 60_000,
             "comment_count": 3_000}
    solid = {"view_count": 50_000, "like_count": 2_000, "comment_count": 100}
    obscure = {"view_count": 300, "like_count": 5, "comment_count": 0}
    assert (_engagement_score(viral) > _engagement_score(solid)
            > _engagement_score(obscure) > 0)
    # Raw API statistics arrive as strings sometimes; coerce, never crash.
    assert _engagement_score({"view_count": "1000", "like_count": "40"}) > 0


# ---------------------------------------------------------------------------
# Research verifies the strongest candidates first (tier, then engagement)
# ---------------------------------------------------------------------------

def test_research_verifies_best_candidates_first(monkeypatch):
    pipe = pipeline_mod.CollegeResourcePipeline()

    # The sandbox HTTP proxy env breaks httpx client construction; the
    # verifier is faked anyway, so the client itself is irrelevant here.
    class DummyClient:
        def __init__(self, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *exc):
            return False

    monkeypatch.setattr(pipeline_mod.httpx, "AsyncClient", DummyClient)

    async def fake_web(self, query, deadline):
        return [{
            "url": "https://nptel.ac.in/courses/xyz", "title": "NPTEL doc",
            "provider": "nptel.ac.in", "quality_signals": {},
        }]

    async def fake_youtube(self, query, deadline):
        return [
            {"url": "https://www.youtube.com/watch?v=viral",
             "title": "Viral generic", "provider": "YouTube",
             "quality_signals": {"channel_title": "RandomChannel",
                                 "view_count": 2_000_000,
                                 "like_count": 60_000,
                                 "comment_count": 3_000}},
            {"url": "https://www.youtube.com/watch?v=nptel",
             "title": "NPTEL lecture", "provider": "YouTube",
             "quality_signals": {"channel_title": "NPTEL",
                                 "view_count": 5_000, "like_count": 300,
                                 "comment_count": 20}},
            {"url": "https://www.youtube.com/watch?v=obscure",
             "title": "Obscure upload", "provider": "YouTube",
             "quality_signals": {"channel_title": "TinyChannel",
                                 "view_count": 300, "like_count": 5,
                                 "comment_count": 0}},
        ]

    order = []

    async def fake_verify(self, http, cand, subject_id, topic):
        order.append(cand["title"])
        return {"resource_id": f"res_{len(order)}", "title": cand["title"]}

    monkeypatch.setattr(pipeline_mod.CollegeResourcePipeline,
                        "_search_web", fake_web)
    monkeypatch.setattr(pipeline_mod.CollegeResourcePipeline,
                        "_search_youtube", fake_youtube)
    monkeypatch.setattr(pipeline_mod.CollegeResourcePipeline,
                        "_verify_and_persist", fake_verify)

    result = asyncio.run(pipe.research_topic(
        subject_id="CS-301", topic="Linked Lists",
        time_budget_seconds=30))
    assert result["resources_added"] == 4
    # Institutional tier outranks raw views: the NPTEL page (.ac.in,
    # tier A) and the official-channel video (promoted to B) verify
    # before the viral generic upload (tier D); engagement breaks ties
    # within a tier (Viral before Obscure).
    assert order == ["NPTEL doc", "NPTEL lecture",
                     "Viral generic", "Obscure upload"]


# ---------------------------------------------------------------------------
# Generation-time research for the first resource-less phase
# ---------------------------------------------------------------------------

def _research_recorder(calls):
    async def fake_research(self, subject_id, topic, **kwargs):
        calls.append({"subject_id": subject_id, "topic": topic,
                      "kwargs": kwargs})
        return {"status": "VERIFIED", "resources_added": 2, "resources": []}
    return fake_research


def test_generation_researches_first_phase_when_cache_empty(monkeypatch):
    _setup(BOB, "Bob", "MECHANICAL_ENGINEER", ["ME-301", "ME-302"])
    calls = []
    monkeypatch.setattr(pipeline_mod.CollegeResourcePipeline,
                        "research_topic", _research_recorder(calls))
    r = client.post("/api/college/plans/generate",
                    json={"scope": "SEMESTER"}, headers=BOB)
    assert r.status_code == 200, r.text
    assert r.json()["phases"]
    # Exactly one bounded pass, for the first phase's subject and topic.
    assert len(calls) == 1
    assert calls[0]["subject_id"] == "ME-301"
    assert calls[0]["topic"] == "Laws of Thermodynamics"
    assert calls[0]["kwargs"].get("time_budget_seconds", 99) <= 15.0


def test_generation_skips_research_when_first_phase_cached(monkeypatch):
    _setup(ALICE, "Alice", "COMPUTER_SCIENCE_ENGINEER",
           ["CS-301", "CS-302"])
    calls = []
    monkeypatch.setattr(pipeline_mod.CollegeResourcePipeline,
                        "research_topic", _research_recorder(calls))
    r = client.post("/api/college/plans/generate",
                    json={"scope": "SEMESTER"}, headers=ALICE)
    assert r.status_code == 200, r.text
    # CS-301 already has a cached VIDEO + NOTES: no research quota spent.
    assert calls == []


def test_generation_research_failure_never_breaks_plan(monkeypatch):
    _setup(BOB, "Bob", "MECHANICAL_ENGINEER", ["ME-301", "ME-302"], hours=8)
    async def exploding_research(self, subject_id, topic, **kwargs):
        raise RuntimeError("network exploded")
    monkeypatch.setattr(pipeline_mod.CollegeResourcePipeline,
                        "research_topic", exploding_research)
    r = client.post("/api/college/plans/generate",
                    json={"scope": "SEMESTER"}, headers=BOB)
    assert r.status_code == 200, r.text
    assert r.json()["phases"]


# ---------------------------------------------------------------------------
# Attachment prefers the highest-engagement resource on a topic-match tie
# ---------------------------------------------------------------------------

def _video(rid, score):
    from backend.core.college_schemas import ResourceRecord
    return ResourceRecord(
        resource_id=rid, title="Linked Lists Lecture",
        resource_type="VIDEO", provider="YouTube",
        url=f"https://youtube.com/watch?v={rid}", source_id="src_t",
        source_tier="D", topic_ids=["Linked Lists"],
        quality_signals={"view_count": 1000, "engagement_score": score})


def test_decorate_prefers_highest_engagement_video(monkeypatch):
    import backend.services.college_learning_service as learning_mod
    from backend.core.college_schemas import (
        ActivityType, CollegeActivity, CollegeLearningPlan, CollegePlanPhase,
    )
    from backend.services.college_learning_service import CollegeLearningService

    low = _video("res_low_eng", 2.0)
    high = _video("res_high_eng", 85.0)

    async def fake_resources(subject_id):
        return [low, high] if subject_id == "CS-301" else []

    monkeypatch.setattr(learning_mod, "get_resources_for_subject",
                        fake_resources)

    def _phase(suffix, activities):
        return CollegePlanPhase(
            phase_id=f"phase_plan_engtest_CS-301_s3_{suffix}",
            user_id=ALICE_UID, plan_id="plan_engtest", order=1,
            title="CS-301: Linked Lists", objective="Learn linked lists.",
            status="AVAILABLE", activities=activities)

    empty = _phase("u1", [])
    pending_watch = _phase("u2", [CollegeActivity(
        activity_id="act_eng_u2", user_id=ALICE_UID, plan_id="plan_engtest",
        phase_id="phase_plan_engtest_CS-301_s3_u2",
        activity_type=ActivityType.WATCH, title="Watch Lecture: Linked Lists",
        order=1, instructions="Watch the lecture.")])
    plan = CollegeLearningPlan(
        plan_id="plan_engtest", user_id=ALICE_UID, goal_id="goal_engtest",
        phases=[empty, pending_watch])

    decorated = asyncio.run(CollegeLearningService()._decorate_plan(plan))
    # Both the synthesized slot and the pending WATCH slot resolve to the
    # high-engagement video, not whichever row came first.
    for phase in decorated.phases:
        watch = next(a for a in phase.activities
                     if a.activity_type == ActivityType.WATCH)
        assert watch.resource is not None
        assert watch.resource.resource_id == "res_high_eng"
