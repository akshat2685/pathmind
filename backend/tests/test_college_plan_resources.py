"""
Plan resources + learn-steps + lag-fix + fallback-diagnostic + PYQ-code tests.

Regression coverage for the 2026-09-30 live-test findings:
  1. Plan phases showed no resource links anywhere (research pipeline was
     never invoked and read paths never rehydrated `resource`).
  2. Activities carried no "how to learn" method — only one-line titles.
  3. "Mark Done" re-saved the entire plan hierarchy (dashboard lag).
  4. The grounded diagnostic fallback repeated one template built from raw
     syllabus topics, including course-administration lines.
  5. PYQ realtime search never used the subject code (7CS4-01), which is
     how university paper archives are actually indexed.

All external calls are stubbed: Gemini via backend.core.gemini, the resource
pipeline via CollegeResourcePipeline.research_topic, Tavily via
pyq_realtime_service seams.
"""
import asyncio

import pytest
from fastapi.testclient import TestClient

from backend.main import app
from college_testkit import install_fake_adapter
import backend.core.gemini as gemini_mod
import backend.services.college_store as cs_mod
import backend.services.pyq_realtime_service as pyq_mod
from backend.services.college_assessment_service import (
    CollegeAssessmentService,
)
from backend.services.college_diagnostic_retrieval import DiagnosticRetrieval
from backend.services.college_resource_pipeline import CollegeResourcePipeline

client = TestClient(app, raise_server_exceptions=False)
ALICE = {"Authorization": "Bearer " + "alice" + "-token"}
BOB = {"Authorization": "Bearer " + "bob" + "-token"}
ALICE_UID = "11111111-1111-4111-8111-111111111111"


@pytest.fixture(scope="module", autouse=True)
def fake_backend():
    adapter, restore = install_fake_adapter()
    yield adapter
    restore()


def _setup(uid_headers, name, email, branch, subjects):
    r = client.post("/api/college/profile",
                    json={"name": name, "email": email},
                    headers=uid_headers)
    assert r.status_code == 200, r.text
    r = client.post("/api/college/academic-context", json={
        "university_id": "univ_aicte_model",
        "branch": branch,
        "semester": 3, "subjects": subjects,
        "available_hours_per_week": 10,
    }, headers=uid_headers)
    assert r.status_code == 200, r.text


def _generate_plan(headers):
    r = client.post("/api/college/plans/generate",
                    json={"scope": "SEMESTER"}, headers=headers)
    assert r.status_code == 200, r.text
    return r.json()


def _current_plan(headers):
    r = client.get("/api/college/plans/current", headers=headers)
    assert r.status_code == 200, r.text
    return r.json()


# ---------------------------------------------------------------------------
# 1. Resources + learn steps on plan reads
# ---------------------------------------------------------------------------

def test_plan_read_rehydrates_resources_and_learn_steps(monkeypatch):
    monkeypatch.setattr(gemini_mod, "get_gemini_model", lambda: None)
    _setup(ALICE, "Alice", "alice@example.com",
           "COMPUTER_SCIENCE_ENGINEER", ["CS-301", "CS-302"])
    _generate_plan(ALICE)

    plan = _current_plan(ALICE)
    phase1 = plan["phases"][0]
    watch = next(a for a in phase1["activities"]
                 if a["activity_type"] == "WATCH")
    read = next(a for a in phase1["activities"]
                if a["activity_type"] == "READ")
    # The seeded VERIFIED CS-301 resources survive the store round-trip:
    # activities persist only resource_id, so this only passes if the read
    # path rehydrates the resource object.
    assert watch["resource"] is not None
    assert watch["resource"]["url"] == (
        "https://example.edu/video/cs301-linked-lists")
    assert read["resource"] is not None
    assert read["resource"]["url"] == "https://example.edu/notes/cs301"
    # Every activity teaches the method, not just the material.
    for phase in plan["phases"]:
        for act in phase["activities"]:
            assert len(act["learn_steps"]) >= 3, (
                act["activity_id"], act["activity_type"])


def test_attach_on_read_links_newly_researched_resources(fake_backend,
                                                          monkeypatch):
    """A resource researched AFTER plan generation reaches the old plan."""
    monkeypatch.setattr(gemini_mod, "get_gemini_model", lambda: None)
    _setup(BOB, "Bob", "bob@example.com",
           "MECHANICAL_ENGINEER", ["ME-301", "ME-302"])
    _generate_plan(BOB)

    plan = _current_plan(BOB)
    # Generated while the ME-301 cache was empty: no WATCH slot exists.
    assert not any(a["activity_type"] == "WATCH"
                   for a in plan["phases"][0]["activities"])

    # Simulate the research pipeline caching a verified video for ME-301.
    fake_backend.client.table("learning_resources").insert([{
        "resource_id": "res_me301_video1",
        "subject_id": "ME-301",
        "resource_type": "VIDEO",
        "title": "Thermodynamics: Laws Lecture",
        "provider": "Test Provider",
        "url": "https://example.edu/video/me301-thermo",
        "source_id": "src_test_official",
        "source_tier": "B",
        "verification_status": "VERIFIED",
        "estimated_minutes": 40,
        "video_timestamps": [],
        "document_sections": [],
    }]).execute()

    plan2 = _current_plan(BOB)
    watch2 = next(a for a in plan2["phases"][0]["activities"]
                  if a["activity_type"] == "WATCH")
    assert watch2["resource"] is not None
    assert watch2["resource"]["url"] == (
        "https://example.edu/video/me301-thermo")
    assert watch2["resource_id"] == "res_me301_video1"
    assert len(watch2["learn_steps"]) >= 3


# ---------------------------------------------------------------------------
# 2. Lag fix: completing an activity persists only the touched phase
# ---------------------------------------------------------------------------

def test_complete_activity_saves_only_touched_phase(monkeypatch):
    plan = _current_plan(ALICE)
    act = plan["phases"][0]["activities"][0]

    calls = {"phase": 0, "plan": 0}
    orig_phase_save = cs_mod.college_store.save_college_phase

    async def _counting_phase_save(uid, phase_data):
        calls["phase"] += 1
        return await orig_phase_save(uid, phase_data)

    async def _forbidden_plan_save(uid, plan_data):
        calls["plan"] += 1
        raise AssertionError(
            "complete_activity must not re-save the whole plan")

    monkeypatch.setattr(cs_mod.college_store, "save_college_phase",
                        _counting_phase_save)
    monkeypatch.setattr(cs_mod.college_store, "save_college_learning_plan",
                        _forbidden_plan_save)

    r = client.post(f"/api/college/activities/{act['activity_id']}/complete",
                    json={"evidence": {"self_reported_focus": 5}},
                    headers=ALICE)
    assert r.status_code == 200, r.text
    assert calls["phase"] >= 1
    assert calls["plan"] == 0

    updated = next(a for p in r.json()["phases"] for a in p["activities"]
                   if a["activity_id"] == act["activity_id"])
    assert updated["status"] == "COMPLETED"

    # And it actually persisted (phase-scoped save, not just in-memory).
    plan_after = _current_plan(ALICE)
    persisted = next(a for p in plan_after["phases"] for a in p["activities"]
                     if a["activity_id"] == act["activity_id"])
    assert persisted["status"] == "COMPLETED"


# ---------------------------------------------------------------------------
# 3. Phase personalization researches resources when the cache is empty
# ---------------------------------------------------------------------------

def test_enrich_phase_researches_when_subject_cache_empty(monkeypatch):
    monkeypatch.setattr(gemini_mod, "get_gemini_model", lambda: None)
    plan = _current_plan(ALICE)
    cs302_phase = next(p for p in plan["phases"]
                       if "CS-302" in p["phase_id"])
    # CS-302 has no seeded resources -> enrich must hit the pipeline first.
    captured = {}

    async def _stub_research(self, subject_id, topic, university_name=None,
                             subject_name=None, time_budget_seconds=45.0):
        captured["subject_id"] = subject_id
        captured["topic"] = topic
        return {"status": "ENRICHED", "resources_added": 0, "resources": []}

    monkeypatch.setattr(CollegeResourcePipeline, "research_topic",
                        _stub_research)

    r = client.post(
        f"/api/college/plans/{plan['plan_id']}/phases/"
        f"{cs302_phase['phase_id']}/activities/enrich",
        json={}, headers=ALICE)
    # No Gemini in tests -> honest AI_UNAVAILABLE (503), but research ran
    # first: the phase must not personalize resource-less when live
    # research could have filled the cache.
    assert r.status_code == 503, r.text
    assert captured["subject_id"] == "CS-302"


# ---------------------------------------------------------------------------
# 4. Grounded fallback: no course-meta topics, varied, spread across subjects
# ---------------------------------------------------------------------------

def test_fallback_diagnostic_filters_meta_topics_and_varies():
    retrieval = DiagnosticRetrieval(curriculum_subjects=[
        {"subject_id": "rtu_cse_7cs4_01", "code": "7CS4-01",
         "name": "Internet of Things", "units": [
             {"unit": 1, "title": "Course Introduction",
              "topics": ["Objective of the course", "Scope of the course",
                         "IoT Architecture", "Sensor Networks"]},
             {"unit": 2, "title": "Protocols",
              "topics": ["MQTT Protocol", "CoAP Protocol"]},
         ]},
        {"subject_id": "rtu_cse_7cs3_02", "code": "7CS3-02",
         "name": "Database Systems", "units": [
             {"unit": 1, "title": "Relational Model",
              "topics": ["Introduction to Databases", "SQL Fundamentals",
                         "Transactions and ACID"]},
         ]},
    ])

    questions = CollegeAssessmentService._fallback_diagnostic_questions(
        retrieval)

    assert 5 <= len(questions) <= 6
    texts = [q.question_text for q in questions]
    # Course-administration lines are never probe material.
    assert not any("Objective of the course" in t for t in texts)
    assert not any("Scope of the course" in t for t in texts)
    # Real topics from BOTH subjects appear (round-robin, not subject 1
    # exhausted first).
    topics = {q.topic for q in questions}
    assert "IoT Architecture" in topics
    assert "SQL Fundamentals" in topics
    # The framing rotates — not one template repeated.
    openings = {t.split("'")[0].strip() for t in texts}
    assert len(openings) >= 3
    assert len({q.probe for q in questions}) >= 3
    # Honest provenance preserved.
    assert all(q.source == "verified_curriculum" for q in questions)


# ---------------------------------------------------------------------------
# 5. PYQ realtime search includes the subject code
# ---------------------------------------------------------------------------

def test_pyq_realtime_search_uses_subject_code(monkeypatch):
    captured = []

    async def _fake_domains(university_id):
        return ["rtu.ac.in"]

    async def _fake_search(query, include_domains, max_results=10):
        captured.append(query)
        return []

    monkeypatch.setattr(pyq_mod, "_get_official_domains", _fake_domains)
    monkeypatch.setattr(pyq_mod, "_tavily_search_official", _fake_search)

    result = asyncio.run(pyq_mod.realtime_pyq_search(
        university_id="rtu",
        branch="COMPUTER_SCIENCE_ENGINEER",
        semester=7,
        subject_name="Internet of Things",
        subject_code="7CS4-01",
        scope="subject",
    ))

    assert result == []
    assert any("7CS4-01" in q for q in captured)
    assert any("Internet of Things" in q for q in captured)
