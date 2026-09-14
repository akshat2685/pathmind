import pytest
import asyncio
from datetime import datetime, timezone

from backend.core.trust_schemas import (
    ClaimCategory,
    ProvenanceOrigin,
    VerificationStatus,
    ConfidenceCategory,
    DecisionReversibility,
    SourceFreshness,
    ProvenanceMetadata,
    TraceableClaim,
    DecisionRecord,
    ConflictNotice
)
from backend.core.trajectory_schemas import CandidatePath
from backend.core.assessment_schemas import AssessmentResult, CounselingProfile, Contradiction
from backend.core.career_schemas import UniversalCareerProfile, TailoredResume, TargetOutcome
from backend.core.roadmap_schemas import Stage, Mission, DisclosedRoadmapView, DisclosedStageView
from backend.services.trajectory_engine import TrajectoryEngine
from backend.services.counseling import CounselingAgent
from backend.services.roadmap_engine import RoadmapEngine
from backend.services.resume_validator import ResumeFactValidator
from backend.services.context_graph_service import ContextGraphService


def test_canonical_trust_schemas_and_provenance():
    """Validates strict trust categories, source freshness, and decision reversibility."""
    freshness = SourceFreshness(
        retrieved_at="2026-09-14T00:00:00Z",
        source_version="v2.1",
        valid_until="2027-09-14T00:00:00Z"
    )
    assert freshness.is_current() is True

    provenance = ProvenanceMetadata(
        provider="ESCO Occupational Standard",
        source_type="EXTERNAL_STANDARD",
        source_url="http://data.europa.eu/esco/occupation/2512",
        verification_status=VerificationStatus.VERIFIED,
        confidence=ConfidenceCategory.HIGH,
        origin=ProvenanceOrigin.EXTERNAL_SOURCE,
        freshness=freshness
    )
    assert provenance.verification_status == "VERIFIED"
    assert provenance.origin == "EXTERNAL_SOURCE"

    claim = TraceableClaim(
        claim_id="claim_001",
        claim_text="Target role requires distributed systems architecture mastery.",
        claim_category=ClaimCategory.FACT,
        provenance=provenance
    )
    assert claim.claim_category == "FACT"

    conflict = ConflictNotice(
        what_conflicts=["Stated disinterest in programming", "Verified hackathon repository in profile"],
        discrepancy_description="User declared aversion to coding while profile contains verified software artifacts.",
        resolution_strategy="user_clarification",
        user_action_needed="Clarify whether you prefer avoiding programming entirely or if past frustration was coursework-specific."
    )
    assert conflict.resolution_strategy == "user_clarification"

    decision = DecisionRecord(
        decision_id="dec_001",
        person_id="test_user",
        decision_type="TRAJECTORY_RECOMMENDATION",
        recommended_choice="Civil Services & Public Administration",
        confidence=ConfidenceCategory.MEDIUM,
        confidence_justification="High stated alignment with constitutional law, pending evaluated Mains mock copies.",
        reversibility=DecisionReversibility.REVERSIBLE,
        reversal_cost_notes="Foundation studies in public policy transfer to corporate governance and regulatory compliance.",
        grounding_claims=[claim],
        conflict_notices=[conflict]
    )
    assert decision.reversibility == "REVERSIBLE"
    assert decision.confidence == "MEDIUM"


def test_trajectory_fit_vs_confidence_decoupling():
    """Ensures fit is decoupled from confidence and no arbitrary decimal scores are fabricated."""
    engine = TrajectoryEngine()
    
    # Non-technical path: Law
    paths_law = engine.generate_deterministic_candidate_paths(
        person_id="test_user",
        goals=["Corporate Law and Legal Advisory"],
        constraints=[]
    )
    assert len(paths_law) >= 1
    law_path = paths_law[0]
    assert law_path.fit_score is None  # No arbitrary fake decimal score
    assert law_path.fit_level in ["STRONG", "HIGH", "PROMISING"]
    assert law_path.confidence == "LOW"  # Unverified candidate has low confidence
    assert "what_we_know" in law_path.transparency_summary
    assert "how_we_know_it" in law_path.transparency_summary
    assert "what_remains_unknown" in law_path.transparency_summary
    assert "what_could_change_this" in law_path.transparency_summary

    # Technical path: Applied AI
    paths_ai = engine.generate_deterministic_candidate_paths(
        person_id="test_user",
        goals=["Applied AI Engineer and Machine Learning Systems"],
        constraints=[]
    )
    assert len(paths_ai) >= 1
    ai_path = paths_ai[0]
    assert ai_path.fit_score is None  # No arbitrary 92.0
    assert ai_path.fit_level in ["STRONG", "HIGH", "PROMISING"]
    assert ai_path.confidence in ["MEDIUM", "LOW"]
    assert len(ai_path.transparency_summary["what_we_know"]) > 0


def test_counseling_riasec_non_deterministic_framing():
    """Verifies that RIASEC assessment claims are framed as preferences, not identity or guarantees."""
    agent = CounselingAgent()
    res = AssessmentResult(
        assessment_id="riasec_001",
        person_id="scholar-test-user",
        version="v1",
        raw_responses=[{"item_id": "q1", "response_value": 5}],
        dimension_scores={"I": 88.0, "R": 65.0, "A": 45.0, "S": 30.0, "E": 40.0, "C": 50.0},
        calculated_scores={"normalized_vector": {"I": 88.0, "R": 65.0, "A": 45.0, "S": 30.0, "E": 40.0, "C": 50.0}}
    )
    profile = agent.synthesize_deterministic_profile(
        person_id="scholar-test-user",
        assessment_results=[res],
        goals=["AI Research Scientist"],
        constraints=["Max 15 hours/week"],
        evidence_items=[]
    )
    
    assert len(profile.strengths) >= 1
    riasec_fact = profile.strengths[0]
    assert "indicat" in riasec_fact.claim.lower()
    assert "preferences, not ability or guaranteed outcome" in riasec_fact.claim
    assert riasec_fact.confidence == "MEDIUM"


def test_counseling_conflict_notice_generation():
    """Validates that contradictions produce calm, actionable ConflictNotices."""
    agent = CounselingAgent()
    contradictions = agent.detect_contradictions(
        stated_goals=["I hate coding and want no programming in my career"],
        stated_constraints=[],
        evidence_items=[{"name": "Autonomous Robot Arduino Firmware", "type": "github_repo"}],
        riasec_scores={"I": 70.0, "R": 80.0}
    )
    assert len(contradictions) >= 1
    contra = contradictions[0]
    assert "There's a difference in the information PATHMIND has" in contra.suggested_clarification
    assert contra.discrepancy_description is not None
    assert contra.resolution_strategy == "user_clarification"
    assert contra.user_action_needed is not None


def test_roadmap_disclosed_stage_transparency():
    """Verifies that build_disclosed_view systematically attaches why_now, what_will_this_unlock, and what_evidence_will_count."""
    engine = RoadmapEngine()
    roadmap = engine.generate_ai_ml_roadmap(person_id="test_user")
    disclosed = engine.build_disclosed_view(roadmap)

    assert len(disclosed.stages) >= 1
    stage_1 = disclosed.stages[0]
    assert stage_1.locked is False
    assert stage_1.why_now is not None
    assert "foundational prerequisite" in stage_1.why_now.lower()
    assert stage_1.what_will_this_unlock is not None
    assert stage_1.what_evidence_will_count is not None

    stage_2 = disclosed.stages[1]
    assert stage_2.locked is True
    assert "unlocks sequentially" in stage_2.why_now.lower()
    assert stage_2.what_will_this_unlock is not None
    assert stage_2.what_evidence_will_count is not None


def test_resume_validator_rejects_unverified_inferences():
    """Ensures memory inferences and unverified recommendation claims cannot become resume facts."""
    validator = ResumeFactValidator()
    profile = UniversalCareerProfile(
        person_id="test_user",
        skills=["Python", "Data Analysis"],
        projects=[],
        experience=[],
        education=[]
    )
    resume = TailoredResume(
        resume_id="res_001",
        person_id="test_user",
        target_role="Data Scientist",
        summary="Aspiring data professional.",
        highlighted_skills=["Python", "Data Analysis"],
        tailored_projects=[
            {
                "title": "Speculative Recommendation System",
                "provenance": "Inferred from chat discussion / unverified recommendation",
                "claim_category": "INFERENCE",
                "technologies": ["Python"]
            }
        ]
    )
    sanitized, is_valid = validator.validate_and_sanitize(resume, profile)
    assert len(sanitized.tailored_projects) == 0
    assert any("Inferred or unverified recommendation claim" in r for r in sanitized.unsupported_claims_rejected)


@pytest.mark.asyncio
async def test_deterministic_context_graph_scoring():
    """Verifies that context graph requirement match score is strictly deterministic and categorical."""
    service = ContextGraphService()
    graph = await service.assemble_context_graph(person_id="scholar-test-user")

    career_context = graph.career_context
    assert "readiness_tier" in career_context
    assert "alignment_level" in career_context
    assert isinstance(career_context["overall_match_score"], (int, float))
    assert career_context["overall_match_score"] >= 0.0
    # Alignment tier is categorical
    assert career_context["alignment_level"] in ["DEVELOPING", "PROMISING", "STRONG"]
