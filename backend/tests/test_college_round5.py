"""
Round-5 regression tests (college MVP):

1. PYQ vault empty for whole universities (live, 2026-09-30: RTU
   returned PYQ_NOT_AVAILABLE for every subject, theory included).
   Root cause: retrieval only ever searched the university's official
   domain, and RTU publishes no indexable question papers on rtu.ac.in —
   students get the same real papers from public exam archives. The
   vault now falls back to an attested archive search (subject code or
   university name required) and labels archive mirrors honestly via
   source_kind/trust_tier. Official sources still win and the archive
   stage never runs when the official stage found papers. The >= 2
   paper-relevance bar is unchanged: syllabi stay out of the vault.

2. Level dead-end: when only older papers exist, Level 1 returned
   has_more_levels=False and the UI disabled the wider levels. The
   empty case now reports whether a wider level actually has papers.

3. Lab subjects: no written paper usually exists (practical + viva) —
   the empty state says that instead of implying a broken archive.

4. Post-diagnose lag: _decorate_plan fetched each subject's cached
   resources sequentially on every plan read; it now fetches in
   parallel.
"""
import asyncio
import types

import backend.services.college_learning_service as learning_mod
import backend.services.pyq_realtime_service as pyq_mod
import backend.providers.curriculum_registry as registry_mod


def _hit(url, title, snippet, domain, tier):
    return {"url": url, "title": title, "snippet": snippet,
            "source_domain": domain, "trust_tier": tier,
            "tavily_score": 0.8}


def _patch_university(monkeypatch):
    async def _fake_domains(university_id):
        return ["rtu.ac.in"]

    async def _fake_univ(university_id):
        return types.SimpleNamespace(
            name="Rajasthan Technical University",
            official_domain="rtu.ac.in")

    monkeypatch.setattr(pyq_mod, "_get_official_domains", _fake_domains)
    monkeypatch.setattr(registry_mod, "get_university_by_id", _fake_univ)


# ---------------------------------------------------------------------------
# 1. Official stage wins; archive stage stays off
# ---------------------------------------------------------------------------

def test_official_hit_never_touches_archive_stage(monkeypatch):
    _patch_university(monkeypatch)
    web_calls = []

    async def _official(query, include_domains, max_results=10):
        return [_hit(
            "https://rtu.ac.in/papers/7ee5-12-2025.pdf",
            "RTU 7EE5-12 Question Paper 2025",
            "End semester examination", "rtu.ac.in", "A")]

    async def _web(query, max_results=10):
        web_calls.append(query)
        return []

    monkeypatch.setattr(pyq_mod, "_tavily_search_official", _official)
    monkeypatch.setattr(pyq_mod, "_tavily_search_web", _web)

    papers = asyncio.run(pyq_mod.realtime_pyq_search(
        university_id="rtu", branch="EE", semester=7,
        subject_name="Power Quality and FACTS", subject_code="7EE5-12",
        scope="subject"))

    assert len(papers) == 1
    assert papers[0]["source_kind"] == "official"
    assert papers[0]["retrieval"] == "realtime"
    assert web_calls == []


# ---------------------------------------------------------------------------
# 2. Archive stage: attested papers in, everything else out
# ---------------------------------------------------------------------------

def test_archive_stage_attestation_and_relevance(monkeypatch):
    _patch_university(monkeypatch)

    async def _official(query, include_domains, max_results=10):
        return []

    async def _web(query, max_results=10):
        return [
            # The real RTU paper, mirrored by an aggregator: code + RTU
            # in the title attests it. Must be returned, honestly labeled.
            _hit("https://gkpad.com/rtu/7ee5-12-paper-2024.pdf",
                 "RTU 7EE5-12 Power Quality and FACTS Question Paper 2024",
                 "Rajasthan Technical University previous year paper",
                 "gkpad.com", "D"),
            # Same subject name, different university, no code: must NOT
            # enter RTU's vault even though it is a real paper.
            _hit("https://annauniv.edu/papers/pq-2024.pdf",
                 "Power Quality Question Paper 2024",
                 "Anna University end semester",
                 "annauniv.edu", "A"),
            # Attested (code + RTU) but it is a syllabus: the relevance
            # bar keeps it out, exactly as on the official domain.
            _hit("https://gkpad.com/rtu/7ee5-12-syllabus.pdf",
                 "RTU 7EE5-12 Syllabus PDF",
                 "Rajasthan Technical University syllabus",
                 "gkpad.com", "D"),
        ]

    monkeypatch.setattr(pyq_mod, "_tavily_search_official", _official)
    monkeypatch.setattr(pyq_mod, "_tavily_search_web", _web)

    papers = asyncio.run(pyq_mod.realtime_pyq_search(
        university_id="rtu", branch="EE", semester=7,
        subject_name="Power Quality and FACTS", subject_code="7EE5-12",
        scope="subject"))

    assert len(papers) == 1
    paper = papers[0]
    assert paper["url"] == "https://gkpad.com/rtu/7ee5-12-paper-2024.pdf"
    assert paper["source_kind"] == "archive"
    assert paper["retrieval"] == "archive"
    assert paper["source_domain"] == "gkpad.com"
    assert paper["trust_tier"] == "D"
    assert paper["year"] == 2024


# ---------------------------------------------------------------------------
# 3. Old papers only: Level 1 points at the wider archive, not a dead end
# ---------------------------------------------------------------------------

def test_level_climb_when_only_old_papers_exist(monkeypatch):
    canned = [{
        "paper_id": "p_old", "url": "https://rtu.ac.in/old.pdf",
        "year": 2019, "title": "RTU 7EE5-12 Question Paper 2019",
        "download_url": "https://rtu.ac.in/old.pdf",
        "subject_name": "Power Quality and FACTS",
        "university_id": "rtu", "source_kind": "official",
        "source_domain": "rtu.ac.in", "trust_tier": "A",
        "retrieval": "realtime", "retrieved_at": "2026-09-30T00:00:00+00:00",
    }]

    async def _no_seeded(university_id, subject_id):
        return []

    async def _fake_realtime(**kwargs):
        return list(canned)

    monkeypatch.setattr(pyq_mod, "_seeded_papers", _no_seeded)
    monkeypatch.setattr(pyq_mod, "realtime_pyq_search", _fake_realtime)

    level1 = asyncio.run(pyq_mod.get_pyqs_scoped(
        university_id="rtu", branch="EE", semester=7, subject_id="s1",
        subject_name="Power Quality and FACTS", scope="subject", level=1))
    assert level1["status"] == "PYQ_NOT_AVAILABLE"
    assert level1["papers"] == []
    assert level1["has_more_levels"] is True
    assert "Unlock Level 2" in level1["message"]

    level3 = asyncio.run(pyq_mod.get_pyqs_scoped(
        university_id="rtu", branch="EE", semester=7, subject_id="s1",
        subject_name="Power Quality and FACTS", scope="subject", level=3))
    assert level3["status"] == "VERIFIED"
    assert [p["paper_id"] for p in level3["papers"]] == ["p_old"]
    assert level3["has_more_levels"] is False


# ---------------------------------------------------------------------------
# 4. Lab subjects: honest empty state through the full retrieval path
# ---------------------------------------------------------------------------

def test_lab_subject_empty_state_is_honest(monkeypatch):
    _patch_university(monkeypatch)

    async def _no_seeded(university_id, subject_id):
        return []

    async def _official(query, include_domains, max_results=10):
        return []

    async def _web(query, max_results=10):
        return []

    monkeypatch.setattr(pyq_mod, "_seeded_papers", _no_seeded)
    monkeypatch.setattr(pyq_mod, "_tavily_search_official", _official)
    monkeypatch.setattr(pyq_mod, "_tavily_search_web", _web)

    result = asyncio.run(pyq_mod.get_pyqs_scoped(
        university_id="rtu", branch="EE", semester=7,
        subject_id="rtu_eee_7ee4_21", subject_name="Embedded Systems Lab",
        subject_code="7EE4-21", scope="subject", level=1))

    assert result["status"] == "PYQ_NOT_AVAILABLE"
    assert result["has_more_levels"] is False
    message = result["message"].lower()
    assert "lab" in message and "practical" in message
    assert "synthetic" in message  # authenticity promise kept


# ---------------------------------------------------------------------------
# 5. Plan decoration fetches subject resources in parallel
# ---------------------------------------------------------------------------

def test_decorate_plan_fetches_subject_resources_in_parallel(monkeypatch):
    from backend.core.college_schemas import (
        ActivityType, CollegeActivity, CollegeLearningPlan, CollegePlanPhase,
    )
    from backend.services.college_learning_service import CollegeLearningService

    state = {"in_flight": 0, "max_in_flight": 0}

    async def _slow_resources(subject_id):
        state["in_flight"] += 1
        state["max_in_flight"] = max(state["max_in_flight"],
                                     state["in_flight"])
        await asyncio.sleep(0.05)
        state["in_flight"] -= 1
        return []

    monkeypatch.setattr(learning_mod, "get_resources_for_subject",
                        _slow_resources)

    def _phase(subject_id, unit):
        phase_id = f"phase_plan_par_{subject_id}_s7_u{unit}"
        return CollegePlanPhase(
            phase_id=phase_id, user_id="u_par", plan_id="plan_par",
            order=unit, title=f"{subject_id}: Unit {unit}",
            objective="Learn it.", status="AVAILABLE",
            activities=[CollegeActivity(
                activity_id=f"act_par_{unit}", user_id="u_par",
                plan_id="plan_par", phase_id=phase_id,
                activity_type=ActivityType.PRACTICE,
                title="Practice", order=1, instructions="Do it.")])

    plan = CollegeLearningPlan(
        plan_id="plan_par", user_id="u_par", goal_id="goal_par",
        phases=[_phase("subj_a", 1), _phase("subj_b", 2),
                _phase("subj_c", 3)])

    decorated = asyncio.run(CollegeLearningService()._decorate_plan(plan))

    assert len(decorated.phases) == 3
    # Sequential fetching would peak at 1 concurrent call.
    assert state["max_in_flight"] >= 2
