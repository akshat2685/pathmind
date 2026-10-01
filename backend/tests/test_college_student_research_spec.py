"""
Student-research spec tests (2026-10-01).

AJ's complaint: the resources the pipeline returned were academic
(NPTEL course pages), not what Indian engineering students actually
use before an exam. The spec from the research:

- Resource queries speak the students' language: "<subject> unit <n>
  one shot" on YouTube; "<code> previous year question paper <UNI>",
  "<subject> important questions", "<subject> notes pdf" on the web.
  No "nptel lecture", no meaningless "site:youtube.com" in API queries.
- Candidates carry a student-intent lane (ONE_SHOT / PYQ /
  IMPORTANT_QUESTIONS / NOTES) and ranking adds a bounded lane bonus
  on top of AJ's quality-first rule (engagement / Tavily score).
- A YouTube watch page found via web search is a VIDEO, not a DOCUMENT.
- The diagnostic prompt carries the exam-pattern spec (PYQ-first,
  easiest-first, paper-like coverage and marks) and the assessment is
  titled "Exam Readiness", not "Diagnostic Assessment".
"""
import json

import pytest
from fastapi.testclient import TestClient

from backend.main import app
from college_testkit import install_fake_adapter
import backend.core.gemini as gemini_mod
import backend.services.college_assessment_service as assessment_mod
from backend.services.college_resource_pipeline import (
    CollegeResourcePipeline,
    _candidate_quality,
    _candidate_rank_key,
    classify_lane,
)

client = TestClient(app, raise_server_exceptions=False)
ALICE = {"Authorization": "Bearer " + "alice" + "-token"}


@pytest.fixture(autouse=True)
def fake_backend():
    adapter, restore = install_fake_adapter()
    yield adapter
    restore()


# ---------------------------------------------------------------------------
# Query spec
# ---------------------------------------------------------------------------

def test_queries_with_code_unit_and_university():
    pipe = CollegeResourcePipeline(store=object())
    qs = pipe._build_queries(
        subject_id="rtu_cse_7cs4_01", subject_name="Internet of Things",
        topic="Sensors", university_name="Rajasthan Technical University",
        subject_code="7CS4-01", unit=3, university_short="RTU")
    web, yt = qs["web"], qs["youtube"]
    assert web[0] == ("7CS4-01 Internet of Things previous year "
                      "question paper RTU")
    assert "important questions" in web[1]
    assert "notes pdf" in web[2]
    assert "one shot" in yt[0] and "unit 3" in yt[0]
    joined = " ".join(web + yt).lower()
    assert "nptel" not in joined
    assert "site:youtube.com" not in joined
    assert "syllabus" not in joined


def test_queries_without_code_fall_back_to_pyq_lane():
    pipe = CollegeResourcePipeline(store=object())
    qs = pipe._build_queries(
        subject_id="sub_x", subject_name="DBMS", topic="Normalization",
        university_name=None)
    web = qs["web"]
    assert "important questions" in web[0]
    assert "pyq solved" in web[1]
    assert "notes pdf" in web[2]
    assert len(web) == 3 and len(qs["youtube"]) == 3


# ---------------------------------------------------------------------------
# Lanes + ranking
# ---------------------------------------------------------------------------

def test_classify_lane():
    assert classify_lane("DBMS Unit 3 in One Shot | Complete Revision") \
        == "ONE_SHOT"
    assert classify_lane("DBMS PYQ solved | RGPV 2024") == "PYQ"
    assert classify_lane("DBMS previous year question paper") == "PYQ"
    assert classify_lane("DBMS Important Questions Unit 3") \
        == "IMPORTANT_QUESTIONS"
    assert classify_lane("DBMS Unit 3 Notes PDF") == "NOTES"
    assert classify_lane("Normalization lecture by Prof. Sharma") is None


def _video(title, views=100_000):
    return {"kind": "VIDEO", "title": title,
            "url": "https://www.youtube.com/watch?v=abc",
            "quality_signals": {"view_count": views,
                                "like_count": 2_000,
                                "comment_count": 100}}


def test_lane_bonus_reorders_videos_without_overriding_engagement():
    plain = _video("DBMS Normalization full lecture")
    oneshot = _video("DBMS Normalization in One Shot — Unit 3")
    assert _candidate_quality(oneshot) > _candidate_quality(plain)
    assert _candidate_rank_key(oneshot) > _candidate_rank_key(plain)
    # A decisively more-watched plain lecture still wins: the bonus is
    # ~one order of magnitude of views, not an override.
    viral_plain = _video("DBMS Normalization full lecture", views=50_000_000)
    assert _candidate_quality(viral_plain) > _candidate_quality(oneshot)


def test_lane_bonus_applies_to_web_docs():
    plain = {"kind": "WEB", "title": "Normalization tutorial",
             "url": "https://example.com/norm",
             "quality_signals": {"search_score": 0.5}}
    important = {"kind": "WEB",
                 "title": "DBMS Normalization important questions",
                 "url": "https://example.com/iq",
                 "quality_signals": {"search_score": 0.5}}
    assert _candidate_quality(important) > _candidate_quality(plain)


def test_youtube_id_from_url():
    f = CollegeResourcePipeline._youtube_id_from_url
    assert f("https://www.youtube.com/watch?v=dQw4w9WgXcQ&t=3") \
        == "dQw4w9WgXcQ"
    assert f("https://youtu.be/dQw4w9WgXcQ") == "dQw4w9WgXcQ"
    assert f("https://example.com/watch") is None


# ---------------------------------------------------------------------------
# Subject-context resolution
# ---------------------------------------------------------------------------

class _Resp:
    def __init__(self, data):
        self.data = data


class _Query:
    def __init__(self, rows):
        self._rows = rows

    def select(self, *a, **k):
        return self

    def eq(self, *a, **k):
        return self

    def limit(self, *a, **k):
        return self

    def execute(self):
        return _Resp(self._rows)


class _StubClient:
    def __init__(self, tables):
        self._tables = tables

    def table(self, name):
        return _Query(self._tables.get(name, []))


class _StubStore:
    def __init__(self, tables):
        self.adapter = type("A", (), {"client": _StubClient(tables)})()


def test_resolve_subject_context():
    store = _StubStore({
        "subjects": [{"code": "7CS4-01", "name": "Internet of Things"}],
        "curriculum_units": [
            {"unit": 2, "title": "Introduction to IoT",
             "topics": ["IoT basics"]},
            {"unit": 3, "title": "IoT Hardware and Software",
             "topics": ["Sensors and Actuators", "Arduino"]},
        ],
        "curriculum_subjects": [{"curriculum_id": "cur_1"}],
        "curricula": [{"university_id": "univ_rtu"}],
        "universities": [{"name": "Rajasthan Technical University"}],
    })
    pipe = CollegeResourcePipeline(store=store)
    ctx = pipe._resolve_subject_context("rtu_cse_7cs4_01", "Sensors")
    assert ctx["code"] == "7CS4-01"
    assert ctx["name"] == "Internet of Things"
    assert ctx["unit"] == 3
    assert ctx["university_short"] == "RTU"
    assert ctx["university"] == "Rajasthan Technical University"


def test_resolve_subject_context_degrades_silently():
    pipe = CollegeResourcePipeline(store=object())
    assert pipe._resolve_subject_context("nope", "anything") == {}


# ---------------------------------------------------------------------------
# Diagnostic exam-pattern spec + title
# ---------------------------------------------------------------------------

DIAGNOSTIC = [
    {"id": "dq1", "text": "What is the time complexity of head insertion in a singly linked list?",
     "type": "MCQ", "options": ["O(1)", "O(n)", "O(log n)", "O(n log n)"],
     "answer": "A", "topic": "Linked Lists", "marks": 2, "probe": "concept",
     "source": "verified_curriculum"},
    {"id": "dq2", "text": "Which scheduling algorithm can cause starvation?",
     "type": "MCQ", "options": ["Round Robin", "SJF", "FCFS", "Multilevel"],
     "answer": "B", "topic": "Scheduling", "marks": 2, "probe": "concept",
     "source": "verified_curriculum"},
    {"id": "dq3", "text": "In paging, a page fault occurs when?",
     "type": "MCQ", "options": ["Page in RAM", "Page not in RAM", "TLB hit", "Cache miss"],
     "answer": "B", "topic": "Paging", "marks": 2, "probe": "misconception",
     "source": "model_generated"},
    {"id": "dq4", "text": "Explain why arrays give O(1) random access but linked lists do not.",
     "type": "SHORT_ANSWER",
     "rubric": "Contiguous memory + index arithmetic vs pointer traversal",
     "topic": "Arrays", "marks": 5, "probe": "concept",
     "source": "verified_curriculum"},
    {"id": "dq5", "text": "Describe how virtual memory lets processes exceed physical RAM.",
     "type": "SHORT_ANSWER",
     "rubric": "Pages swapped between disk and RAM on demand",
     "topic": "Virtual Memory", "marks": 5, "probe": "application",
     "source": "model_generated"},
]


class _Recorder:
    def __init__(self, text):
        self.calls = []
        self._text = text

    async def __call__(self, agent_key, prompt, **kwargs):
        self.calls.append((agent_key, prompt))
        return self._text


class _Model:
    def generate_content(self, prompt):
        return type("R", (), {"text": json.dumps(DIAGNOSTIC)})()


def test_diagnostic_prompt_carries_exam_pattern_spec(monkeypatch):
    r = client.post("/api/college/profile",
                    json={"name": "Alice", "email": "alice@example.com"},
                    headers=ALICE)
    assert r.status_code == 200, r.text
    r = client.post("/api/college/academic-context", json={
        "university_id": "univ_aicte_model",
        "branch": "COMPUTER_SCIENCE_ENGINEER",
        "semester": 3, "subjects": ["CS-301", "CS-302"],
        "available_hours_per_week": 10,
    }, headers=ALICE)
    assert r.status_code == 200, r.text

    recorder = _Recorder(json.dumps(DIAGNOSTIC))
    monkeypatch.setattr(assessment_mod, "run_agent_generation", recorder)
    monkeypatch.setattr(gemini_mod, "get_gemini_model", lambda: _Model())

    r = client.post("/api/college/assessments/diagnostic", json={},
                    headers=ALICE)
    assert r.status_code == 200, r.text
    asmt = r.json()
    assert asmt["title"].startswith("Exam Readiness:")
    assert recorder.calls, "ADK seam was not invoked"
    prompt = recorder.calls[0][1]
    assert "EXAM PATTERN" in prompt
    assert "at least half" in prompt          # PYQ-first rule
    assert "EASIEST FIRST" in prompt           # confidence ramp
    assert "COVER LIKE THE PAPER" in prompt    # unit coverage
    assert "MARKS MIRROR THE PAPER" in prompt  # marks realism
    # The honesty contract survived the spec addition.
    assert "SOURCE HONESTY (strict)" in prompt


def test_adk_assessment_instruction_carries_spec():
    from backend.agents.college_adk_agents import (
        ASSESSMENT_AGENT_INSTRUCTION)
    assert "past-year" in ASSESSMENT_AGENT_INSTRUCTION
    assert "easiest first" in ASSESSMENT_AGENT_INSTRUCTION
    assert "exam-readiness" in ASSESSMENT_AGENT_INSTRUCTION


# ---------------------------------------------------------------------------
# Research flow: legs merge, web-surfaced YouTube is a VIDEO
# (regression: sequential legs let one slow provider starve the whole
# budget and research returned zero resources)
# ---------------------------------------------------------------------------

class _DummyHttp:
    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        return False


async def test_research_topic_merges_concurrent_legs(monkeypatch):
    # The sandbox's proxy env breaks real httpx client construction;
    # verification is stubbed anyway, so stub the client too.
    monkeypatch.setattr("httpx.AsyncClient", lambda *a, **k: _DummyHttp())
    pipe = CollegeResourcePipeline(store=object())

    async def fake_web(query, deadline):
        return [{"url": "https://www.youtube.com/watch?v=abc123XYZ",
                 "title": "IoT Unit 3 One Shot", "snippet": "",
                 "provider": "youtube.com",
                 "quality_signals": {"search_engine": "duckduckgo"}}]

    async def fake_yt(query, deadline):
        return [{"url": "https://www.youtube.com/watch?v=def456UVW",
                 "title": "IoT sensors lecture", "provider": "youtube.com",
                 "quality_signals": {"view_count": 1000}}]

    seen = {}

    async def fake_verify(http, cand, subject_id, topic):
        seen[cand["url"]] = cand["kind"]
        return {"resource_id": "res_x", "url": cand["url"]}

    pipe._search_web = fake_web
    pipe._search_youtube = fake_yt
    pipe._verify_and_persist = fake_verify
    out = await pipe.research_topic(
        "sub_x", "Sensors", subject_name="Internet of Things",
        time_budget_seconds=10)
    assert out["status"] == "VERIFIED"
    assert out["resources_added"] == 2  # deduped across the 3+2 queries
    assert seen["https://www.youtube.com/watch?v=abc123XYZ"] == "VIDEO"
    assert seen["https://www.youtube.com/watch?v=def456UVW"] == "VIDEO"


async def test_research_topic_survives_a_dead_leg(monkeypatch):
    monkeypatch.setattr("httpx.AsyncClient", lambda *a, **k: _DummyHttp())
    pipe = CollegeResourcePipeline(store=object())

    async def dead_web(query, deadline):
        raise RuntimeError("provider down")

    async def fake_yt(query, deadline):
        return [{"url": "https://www.youtube.com/watch?v=def456UVW",
                 "title": "IoT sensors lecture", "provider": "youtube.com",
                 "quality_signals": {"view_count": 1000}}]

    async def fake_verify(http, cand, subject_id, topic):
        return {"resource_id": "res_x", "url": cand["url"]}

    pipe._search_web = dead_web
    pipe._search_youtube = fake_yt
    pipe._verify_and_persist = fake_verify
    out = await pipe.research_topic(
        "sub_x", "Sensors", subject_name="Internet of Things",
        time_budget_seconds=10)
    assert out["status"] == "VERIFIED"
    assert out["resources_added"] == 1
