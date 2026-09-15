"""
Test Domain Neutrality — Adversarial Tests for PATHMIND Goal Agnosticism.

Validates that:
1. CanonicalGoal correctly captures any domain (Cricket, Medicine, Law, Fashion, etc.)
2. GoalInterpretationService does NOT hallucinate tech/software domains
3. RequirementGraphService produces domain-appropriate requirements
4. GoalAlignmentValidator catches cross-domain contamination
5. Assessment items contain zero software/tech-specific language
6. CareerReadinessEngine produces empty profiles (no hardcoded defaults)
"""
import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock

from backend.core.career_schemas import CanonicalGoal, UniversalCareerProfile, CareerRequirementGraph
from backend.services.goal_interpretation_service import GoalInterpretationService
from backend.services.goal_alignment_validator import GoalAlignmentValidator, GoalAlignmentError
from backend.services.requirement_graph_service import RequirementGraphService
from backend.services.career_readiness_engine import CareerReadinessEngine
from backend.services.assessment import RIASEC_ITEMS, LEARNING_ITEMS


# ============================================================
# 1. ASSESSMENT DOMAIN NEUTRALITY
# ============================================================

# Software/tech keywords that should NOT appear in universal assessment items
TECH_KEYWORDS = [
    "software", "code", "algorithm", "database", "microservice", "monolith",
    "stack", "queue", "data structure", "10gb log", "ram", "compiler",
    "array.length", "console.log", "indexing a database", "git", "github",
    "robotics", "engineering equipment", "python", "javascript",
    "digital media", "user experiences", "user interfaces"
]


class TestAssessmentDomainNeutrality:
    """Verify that RIASEC and Learning items contain zero tech-specific language."""

    def test_riasec_items_are_domain_neutral(self):
        for item in RIASEC_ITEMS:
            text_lower = item.text.lower()
            for kw in TECH_KEYWORDS:
                assert kw not in text_lower, (
                    f"RIASEC item '{item.id}' contains tech keyword '{kw}': {item.text}"
                )

    def test_learning_items_are_domain_neutral(self):
        for item in LEARNING_ITEMS:
            text_lower = item.text.lower()
            for kw in TECH_KEYWORDS:
                assert kw not in text_lower, (
                    f"Learning item '{item.id}' contains tech keyword '{kw}': {item.text}"
                )


# ============================================================
# 2. CANONICAL GOAL MODEL
# ============================================================

class TestCanonicalGoalModel:
    """Verify CanonicalGoal correctly stores any domain."""

    @pytest.mark.parametrize("raw,domain,field,role", [
        ("I want to become a professional cricketer", "Sports", "Cricket", "Professional Cricketer"),
        ("I want to be a doctor", "Healthcare", "Medicine", "Doctor"),
        ("I want to become a lawyer", "Law", "Legal Practice", "Lawyer"),
        ("I want to be a fashion designer", "Fashion", "Fashion Design", "Fashion Designer"),
        ("I want to become a musician", "Music", "Performance", "Musician"),
        ("I want to be an entrepreneur", "Business", "Entrepreneurship", "Entrepreneur"),
        ("I want to become a chef", "Hospitality", "Culinary Arts", "Chef"),
        ("I want to be a teacher", "Education", "Teaching", "Teacher"),
        ("I want to become a researcher", "Academia", "Research", "Researcher"),
        ("I want to be a software engineer", "Technology", "Software Engineering", "Software Engineer"),
    ])
    def test_canonical_goal_preserves_domain(self, raw, domain, field, role):
        goal = CanonicalGoal(
            person_id="test_user",
            raw_statement=raw,
            normalized_statement=raw.title(),
            domain=domain,
            field=field,
            target_role=role,
            target_outcome=role,
        )
        assert goal.domain == domain
        assert goal.field == field
        assert goal.target_role == role
        assert goal.raw_statement == raw


# ============================================================
# 3. GOAL INTERPRETATION — DETERMINISTIC VALIDATION
# ============================================================

class TestGoalInterpretationValidation:
    """Verify the deterministic validation layer catches tech hallucinations."""

    def test_cricket_goal_not_converted_to_software(self):
        """The critical test: 'cricketer' must NOT become AI Engineer."""
        service = GoalInterpretationService.__new__(GoalInterpretationService)
        service.store = MagicMock()
        service.model = None

        goal = CanonicalGoal(
            person_id="test",
            raw_statement="I want to become a professional cricketer",
            normalized_statement="Professional Cricketer",
            domain="Software Engineering",  # Simulate LLM hallucination
            field="Artificial Intelligence",
            target_role="Applied AI Specialist",
            target_outcome="Applied AI Specialist",
        )

        # The validation layer should OVERRIDE the hallucination
        service._validate_interpretation(goal)
        assert "software" not in goal.domain.lower()
        assert "artificial intelligence" not in goal.field.lower()
        assert "applied ai" not in goal.target_role.lower()

    def test_doctor_goal_not_converted_to_tech(self):
        service = GoalInterpretationService.__new__(GoalInterpretationService)
        service.store = MagicMock()
        service.model = None

        goal = CanonicalGoal(
            person_id="test",
            raw_statement="I want to become a doctor",
            normalized_statement="Doctor",
            domain="Machine Learning",
            field="Machine Learning",
            target_role="ML Engineer",
            target_outcome="ML Engineer",
        )
        service._validate_interpretation(goal)
        assert "machine learning" not in goal.domain.lower()

    def test_tech_goal_remains_tech(self):
        """If user actually says 'software engineer', domain should stay tech."""
        service = GoalInterpretationService.__new__(GoalInterpretationService)
        service.store = MagicMock()
        service.model = None

        goal = CanonicalGoal(
            person_id="test",
            raw_statement="I want to become a software engineer",
            normalized_statement="Software Engineer",
            domain="Technology",
            field="Software Engineering",
            target_role="Software Engineer",
            target_outcome="Software Engineer",
        )
        service._validate_interpretation(goal)
        # Should NOT be overridden because user actually said "software"
        assert goal.domain == "Technology"


# ============================================================
# 4. GOAL ALIGNMENT VALIDATOR
# ============================================================

class TestGoalAlignmentValidator:
    """Verify structural and semantic alignment checks."""

    def test_goal_id_mismatch_raises_error(self):
        canonical = {"id": "goal_cricket_1", "domain": "Sports"}
        output = {"goal_id": "goal_ai_99", "domain": "Sports"}
        with pytest.raises(GoalAlignmentError, match="GOAL_ALIGNMENT_ERROR"):
            GoalAlignmentValidator.validate_output(canonical, output, "test_roadmap")

    def test_domain_mismatch_raises_error(self):
        canonical = {"id": "goal_1", "domain": "Sports"}
        output = {"id": "goal_1", "domain": "Artificial Intelligence & Software Engineering"}
        with pytest.raises(GoalAlignmentError, match="GOAL_ALIGNMENT_ERROR"):
            GoalAlignmentValidator.validate_output(canonical, output, "test_path")

    def test_semantic_contamination_detected(self):
        """A roadmap that says 'Sports' but contains Python/GitHub stages should fail."""
        contamination = GoalAlignmentValidator.validate_no_cross_domain_contamination(
            canonical_domain="Sports",
            content_to_check="Stage 1: Learn Python. Stage 2: Push to GitHub. Stage 3: Build neural network."
        )
        assert "python" in contamination
        assert "github" in contamination
        assert "neural network" in contamination

    def test_tech_domain_allows_tech_keywords(self):
        """Technology domain should pass even with tech keywords."""
        contamination = GoalAlignmentValidator.validate_no_cross_domain_contamination(
            canonical_domain="Technology",
            content_to_check="Learn Python, push to GitHub, build microservices."
        )
        assert contamination == []

    def test_clean_sports_roadmap_passes(self):
        """A clean cricket roadmap should pass validation."""
        canonical = {"id": "goal_1", "domain": "Sports"}
        output = {
            "id": "goal_1",
            "domain": "Sports",
            "stages": [
                {"name": "Batting technique fundamentals"},
                {"name": "Fielding drills and fitness conditioning"},
                {"name": "Match strategy and game awareness"}
            ]
        }
        report = GoalAlignmentValidator.validate_output(canonical, output, "roadmap", strict=False)
        assert report["passed"] is True


# ============================================================
# 5. CAREER READINESS ENGINE — NO HARDCODED FALLBACKS
# ============================================================

class TestCareerReadinessNoFallbacks:
    """Verify that new profiles are empty, not pre-filled with mechanical/tech data."""

    @pytest.mark.asyncio
    async def test_new_profile_is_empty(self):
        engine = CareerReadinessEngine.__new__(CareerReadinessEngine)
        engine.store = MagicMock()
        engine.store.get_career_profile = AsyncMock(return_value=None)
        engine.store.save_career_profile = AsyncMock()

        profile = await engine.get_or_create_canonical_profile("new_user")

        assert profile.current_role == "Unknown"
        assert profile.skills == []
        assert profile.projects == []
        assert profile.experience == []
        assert profile.education == []
        assert "mechanical" not in profile.current_role.lower()
        assert "senior" not in profile.current_role.lower()

    @pytest.mark.asyncio
    async def test_switcher_profile_is_still_empty(self):
        """Even 'career_switcher' state should not produce hardcoded Mechanical Engineer."""
        engine = CareerReadinessEngine.__new__(CareerReadinessEngine)
        engine.store = MagicMock()
        engine.store.get_career_profile = AsyncMock(return_value=None)
        engine.store.save_career_profile = AsyncMock()

        profile = await engine.get_or_create_canonical_profile("switcher_user", "career_switcher")

        assert "mechanical" not in profile.current_role.lower()
        assert "thermal" not in profile.current_role.lower()
        assert profile.skills == []


# ============================================================
# 6. REQUIREMENT GRAPH — DOMAIN APPROPRIATE
# ============================================================

class TestRequirementGraphDomainNeutrality:
    """Verify requirement graphs are domain-appropriate."""

    def _make_goal(self, role: str, domain: str) -> CanonicalGoal:
        return CanonicalGoal(
            person_id="test",
            raw_statement=f"I want to become a {role}",
            normalized_statement=role,
            domain=domain,
            field=domain,
            target_role=role,
            target_outcome=role,
        )

    def test_lawyer_graph_has_law_requirements(self):
        service = RequirementGraphService()
        goal = self._make_goal("Lawyer", "Law")
        graph = service.build_requirement_graph_for_outcome(goal)

        all_names = [n.name.lower() for n in graph.core_skills + graph.supporting_skills]
        # Should have legal content
        assert any("law" in n or "jurisprud" in n or "legal" in n or "statutory" in n for n in all_names), \
            f"Lawyer graph missing law content: {all_names}"
        # Should NOT have software content
        assert not any("python" in n or "github" in n or "machine learning" in n for n in all_names), \
            f"Lawyer graph has tech contamination: {all_names}"

    def test_generic_cricketer_graph_has_no_tech(self):
        service = RequirementGraphService()
        goal = self._make_goal("Professional Cricketer", "Sports")
        graph = service.build_requirement_graph_for_outcome(goal)

        import json
        graph_str = json.dumps(graph.model_dump(mode="json"), default=str).lower()

        # Should NOT contain software defaults
        assert "python" not in graph_str, f"Cricketer graph contains 'python'"
        assert "github" not in graph_str, f"Cricketer graph contains 'github'"
        assert "machine learning" not in graph_str, f"Cricketer graph contains 'machine learning'"
        assert "software" not in graph_str or "software" in graph.target_role.lower(), \
            f"Cricketer graph contains 'software'"
