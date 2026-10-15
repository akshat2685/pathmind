"""
Tests for the PathMind intelligence pack integration.

Covers the lazy-loaded intelligence service (classifier + both KB retrievals),
the evidence-block formatting, readiness steering, and the KnowledgeService
provider registration. No network, no Supabase, no LLM key required.
"""
import pytest

from backend.services import intelligence_service as intel
from backend.services.intelligence_service import (
    READINESS_MODEL_VERSION,
    build_evidence_block,
    get_intelligence_service,
    readiness_steering_text,
)


@pytest.fixture(scope="module")
def service():
    svc = get_intelligence_service()
    assert svc.available, f"intelligence pack failed to load: {svc.load_error}"
    return svc


class TestReadinessClassifier:
    SAMPLES = [
        (
            "I don't see any problem with my maths marks, everyone should stop bothering me.",
            "precontemplation",
        ),
        (
            "I've been wondering lately if I should do something about my coding practice, "
            "but I'm not sure where to begin.",
            "contemplation",
        ),
        (
            "I've decided to work on my placement preparation starting next month and "
            "bought the books already.",
            "preparation",
        ),
        (
            "I've been working on my DSA practice every day for the past two weeks and "
            "I'm sticking to it.",
            "action",
        ),
        (
            "I've kept up my study routine for over six months now; it's just part of who I am.",
            "maintenance",
        ),
    ]

    def test_predict_all_stages(self, service):
        for text, expected in self.SAMPLES:
            result = service.predict_readiness(text)
            assert result is not None
            assert result["stage"] == expected, f"{text!r} -> {result['stage']}"
            assert 0.0 <= result["confidence"] <= 1.0
            assert result["model_version"] == READINESS_MODEL_VERSION

    def test_disclaimer_travels_with_prediction(self, service):
        result = service.predict_readiness("I want to learn python")
        note = result["note"].lower()
        assert "heuristic" in note and "diagnosis" in note

    def test_empty_text_returns_default(self, service):
        result = service.predict_readiness("")
        assert result["stage"] == "contemplation"
        assert result["confidence"] == 0.0


class TestKBRetrieval:
    def test_resources_retrieval(self, service):
        hits = service.retrieve_resources(
            "best free YouTube channel for class 12 physics in Hindi", k=3
        )
        assert len(hits) >= 1
        entry = hits[0]["entry"]
        assert entry["url"].startswith("http")
        assert entry["url_verified"] is True

    def test_professions_retrieval(self, service):
        hits = service.retrieve_professions("pros and cons of opening a tea shop", k=3)
        assert len(hits) >= 1
        entry = hits[0]["entry"]
        assert "tea shop" in entry["name"].lower()
        assert entry["salary_inr"]["note"] == "estimate"
        assert len(entry["cons"]) >= 3  # balanced, honest cons


class TestEvidenceBlock:
    def test_block_contains_grounding_rules(self, service):
        block = build_evidence_block("pros and cons of opening a tea shop")
        assert block is not None
        assert "HARD RULES" in block
        assert "ESTIMATE" in block

    def test_block_none_when_irrelevant(self, service):
        # Gibberish should not force irrelevant evidence into the prompt.
        # Calibrated uncertainty: an explicit NO_VERIFIED_RESULTS marker
        # (not None) so the counselor says it plainly instead of inventing.
        block = build_evidence_block("zxqvkw blorpt fnord")
        assert block is not None
        assert block.startswith("NO_VERIFIED_RESULTS")


class TestReadinessSteering:
    def test_precontemplation_is_motivational(self):
        text = readiness_steering_text("precontemplation")
        assert text is not None
        assert "NOT a diagnosis" in text
        assert "do NOT dump a roadmap" in text
        # The raw label must never be presented as a verdict to the user.
        assert "never state the stage label" in text

    def test_unknown_stage_returns_none(self):
        assert readiness_steering_text("nonsense") is None
        assert readiness_steering_text(None) is None


class TestKnowledgeServiceProvider:
    def test_professions_provider_registered(self, monkeypatch, service):
        import backend.services.knowledge as knowledge_mod
        from backend.tests.in_memory_store import InMemoryStore
        from backend.services.knowledge import KnowledgeService

        # knowledge.py binds get_pm_store at import; patch its namespace.
        monkeypatch.setattr(
            knowledge_mod, "get_pm_store", lambda: InMemoryStore()
        )
        ks = KnowledgeService()
        assert "intelligence_professions" in ks.providers
        provider = ks.providers["intelligence_professions"]

        import asyncio

        assert asyncio.run(provider.check_health()) == "CONNECTED"
        occs = asyncio.run(provider.search_occupations("tea shop owner", limit=3))
        assert occs and "tea shop" in occs[0].title.lower()
        assert "ESTIMATE" in (occs[0].description or "")
