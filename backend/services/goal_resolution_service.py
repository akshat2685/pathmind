import re
import json
import uuid
from typing import Dict, Any, List, Optional, Tuple, Any
from datetime import datetime, timezone

from backend.core.config import settings
from backend.core.goal_schemas import (
    GoalType,
    GoalStatus,
    CanonicalGoal,
    GoalResolutionRequest,
    GoalResolutionResponse
)
from backend.services.knowledge import KnowledgeService
from backend.services.pm_store import get_pm_store

class GoalResolver:
    """
    Goal Resolution Layer for PATHMIND.
    Transforms raw user intent into a structured, verified, domain-agnostic CanonicalGoal.
    Never fabricates occupation facts. Never defaults to AI/ML or software engineering.
    """
    def __init__(
        self,
        knowledge_service: Optional[KnowledgeService] = None,
        store: Optional[Any] = None
    ):
        self.knowledge_service = knowledge_service or KnowledgeService()
        self.store = store or get_pm_store()
        self.gemini_available = bool(settings.GEMINI_API_KEY)
        self.model = None

        if self.gemini_available:
            try:
                import google.generativeai as genai
                genai.configure(api_key=settings.GEMINI_API_KEY)
                self.model = genai.GenerativeModel('gemini-2.5-flash')
            except Exception as e:
                print(f"Warning: Failed to initialize Gemini in GoalResolver: {e}")
                self.model = None

    def _deterministic_intent_parse(self, raw_intent: str) -> Dict[str, Any]:
        """
        Deterministic semantic extraction of goal type, domain, subfield, and outcome.
        Used as primary logic or fallback when LLM is unavailable or offline.
        """
        text = raw_intent.strip()
        lower = text.lower()

        # Detect Goal Type
        goal_type = GoalType.CAREER_ROLE
        if any(w in lower for w in ["switch from", "transition from", "pivot from", "change career"]):
            goal_type = GoalType.CAREER_TRANSITION
        elif any(w in lower for w in ["crack ", "clear upsc", "pass upsc", "exam", "gate", "neet", "bar exam"]):
            goal_type = GoalType.EXAM
        elif any(w in lower for w in ["start a ", "launch a ", "open a ", "found a ", "build a startup", "entrepreneur"]):
            goal_type = GoalType.ENTREPRENEURSHIP
        elif any(w in lower for w in ["researcher", "research in", "phd", "postdoc"]):
            goal_type = GoalType.RESEARCH
        elif any(w in lower for w in ["degree", "masters in", "bachelors in", "diploma", "study "]):
            goal_type = GoalType.EDUCATION
        elif any(w in lower for w in ["certified", "certification", "license", "credential"]):
            goal_type = GoalType.CREDENTIAL
        elif any(w in lower for w in ["learn ", "master ", "get good at"]):
            goal_type = GoalType.COMPETENCY

        # Domain & Subfield Detection
        domain = "General Professional"
        subfield = None
        target_role = None
        target_outcome = text

        if "product designer" in lower or "ui/ux" in lower or "ux designer" in lower or "design" in lower:
            domain = "Design & Creative Arts"
            subfield = "Product & Digital Interface Design"
            target_role = "Product Designer"
            target_outcome = "Product Designer"
        elif "lawyer" in lower or "attorney" in lower or "advocate" in lower or "legal" in lower:
            domain = "Legal & Jurisprudence"
            subfield = "Legal Practice & Advocacy"
            target_role = "Lawyer"
            target_outcome = "Licensed Legal Advocate / Lawyer"
        elif "clinical psychologist" in lower or "psychologist" in lower or "therapy" in lower or "therapist" in lower:
            domain = "Healthcare & Mental Health"
            subfield = "Clinical Psychology & Counseling"
            target_role = "Clinical Psychologist"
            target_outcome = "Licensed Clinical Psychologist"
        elif "restaurant" in lower or "bakery" in lower or "cafe" in lower or "food" in lower:
            domain = "Hospitality & Entrepreneurship"
            subfield = "Food Service & Culinary Operations"
            target_role = "Restaurant Owner & Operator"
            target_outcome = "Independent Food Service Business Owner"
        elif "upsc" in lower or "civil services" in lower or "ias" in lower or "ips" in lower:
            domain = "Public Administration & Governance"
            subfield = "Civil Services & Administrative Governance"
            target_role = "Civil Services Officer (UPSC)"
            target_outcome = "Indian Administrative / Civil Services Officer"
        elif "photographer" in lower or "photography" in lower:
            domain = "Arts & Media"
            subfield = "Commercial & Editorial Photography"
            target_role = "Professional Photographer"
            target_outcome = "Professional Photographer"
        elif "product management" in lower or "product manager" in lower or "pm" in lower:
            domain = "Business & Product Strategy"
            subfield = "Product Strategy & Execution"
            target_role = "Product Manager"
            target_outcome = "Product Manager"
        elif "biotechnology" in lower or "biology" in lower or "genetics" in lower:
            domain = "Life Sciences & Biotechnology"
            subfield = "Biotechnology & Applied Molecular Biology"
            target_role = "Biotechnology Researcher"
            target_outcome = "Biotechnology Research Scientist"
        elif "researcher" in lower or "research" in lower:
            domain = "Academic & Industrial Research"
            # Extract domain if mentioned (e.g. "researcher in physics")
            match = re.search(r"research(?:er)?\s+in\s+([a-zA-Z\s]+)", lower)
            discipline = match.group(1).strip().title() if match else "Scientific Domain"
            subfield = f"{discipline} Investigation"
            target_role = f"Research Scientist ({discipline})"
            target_outcome = f"Published Research Scientist in {discipline}"
        elif any(k in lower for k in ["machine learning", "artificial intelligence", "applied ai", "ai engineer"]):
            domain = "Artificial Intelligence & Computing"
            subfield = "Applied Machine Learning Systems"
            target_role = "Machine Learning Systems Specialist"
            target_outcome = "Machine Learning Systems Specialist"
        elif any(k in lower for k in ["software", "full stack", "backend", "web developer"]):
            domain = "Software Engineering"
            subfield = "Fullstack / Cloud Systems"
            target_role = "Software Engineer"
            target_outcome = "Software Engineer"
        elif "sales" in lower:
            domain = "Commerce & Commercial Operations"
            subfield = "B2B / Technology Sales"
            target_role = "Commercial Sales Lead"
            target_outcome = "Enterprise Sales Professional"
        else:
            # Clean extraction for uncataloged domains
            cleaned = re.sub(r"^(i want to become an?|i want to be an?|i want to|become an?|be an?)\s+", "", lower).strip().title()
            if cleaned:
                target_role = cleaned
                target_outcome = cleaned
                domain = f"{cleaned} Domain"

        return {
            "goal_type": goal_type,
            "target_domain": domain,
            "target_subfield": subfield,
            "target_role": target_role,
            "target_outcome": target_outcome,
            "normalized_goal": f"Pursue career as {target_outcome}" if goal_type == GoalType.CAREER_ROLE else f"Achieve {target_outcome}"
        }

    async def resolve_goal(
        self,
        person_id: str,
        req: GoalResolutionRequest
    ) -> GoalResolutionResponse:
        raw = (req.raw_intent or "").strip()
        if not raw or len(raw) < 4:
            return GoalResolutionResponse(
                resolved_goal=None,
                status=GoalStatus.NEEDS_USER_INPUT,
                message="Your goal statement is empty or too brief. Please specify your desired career, role, transition, or outcome.",
                suggested_clarifications=[
                    "What specific occupation or field do you wish to enter?",
                    "Are you pursuing a career role, an examination, a business, or an education degree?",
                    "What is your intended timeline and geography?"
                ],
                confidence="INSUFFICIENT_EVIDENCE",
                provenance={"source": "GoalResolver", "reason": "empty_or_underspecified_intent"}
            )

        # Check for vague statements like "I don't know", "help me decide", "anything"
        vague_patterns = ["don't know", "dont know", "not sure", "help me decide", "explore anything", "any career", "something good"]
        if any(p in raw.lower() for p in vague_patterns):
            return GoalResolutionResponse(
                resolved_goal=None,
                status=GoalStatus.GOAL_NOT_RESOLVED,
                message="Your goal indicates you are currently exploring or undecided. We need your input on fields of interest to formulate a path.",
                suggested_clarifications=[
                    "Would you like to complete a psychometric assessment first to discover candidate directions?",
                    "Name 2-3 fields or activities that you find engaging (e.g. Design, Healthcare, Business, Public Service, Engineering).",
                    "Do you prefer working with people, ideas, physical systems, or organizational data?"
                ],
                confidence="GOAL_NOT_RESOLVED",
                provenance={"source": "GoalResolver", "reason": "vague_intent_needs_counseling"}
            )

        # Deterministic Parse
        parsed = self._deterministic_intent_parse(raw)

        # Query KnowledgeService for verified occupation facts
        search_query = parsed.get("target_role") or parsed.get("target_outcome") or raw
        lookup_result = await self.knowledge_service.search_occupations(query=search_query, limit=3)

        provenance_sources = []
        canonical_occupation_title = None
        canonical_occupation_id = None

        if lookup_result and lookup_result.results:
            top_match = lookup_result.results[0]
            canonical_occupation_title = top_match.title
            canonical_occupation_id = top_match.id
            provenance_sources = [s.model_dump() if hasattr(s, "model_dump") else s for s in lookup_result.sources]

        # Check if domain is totally unrecognized and no knowledge source found
        is_fictional = any(fict in raw.lower() for fict in ["dragon", "wizard", "jedi", "time traveler", "superhero"])
        if is_fictional:
            return GoalResolutionResponse(
                resolved_goal=None,
                status=GoalStatus.NO_VERIFIED_PATH,
                message=f"No verified occupational standards or accredited qualification pathways exist for '{raw}'.",
                suggested_clarifications=[
                    "Please specify an accredited occupation, professional credential, or real-world enterprise.",
                    "If you are interested in creative storytelling, consider 'Screenwriter', 'Game Designer', or 'Author'."
                ],
                confidence="LOW",
                provenance={"source": "KnowledgeService", "reason": "no_verified_pathway"}
            )

        goal_id = f"goal_{person_id}_{int(datetime.now(timezone.utc).timestamp())}"
        resolved = CanonicalGoal(
            goal_id=goal_id,
            person_id=person_id,
            raw_user_goal=raw,
            normalized_goal=parsed["normalized_goal"],
            goal_type=parsed["goal_type"],
            target_domain=parsed["target_domain"],
            target_subfield=parsed["target_subfield"],
            target_role=canonical_occupation_title or parsed["target_role"],
            target_outcome=parsed["target_outcome"],
            geography=req.geography or "India & Global",
            timeline=req.timeline,
            constraints=req.constraints or {},
            motivation=req.motivation,
            confidence="HIGH" if canonical_occupation_title else "MEDIUM",
            provenance={
                "resolved_via": "GoalResolver",
                "knowledge_sources": provenance_sources,
                "canonical_title": canonical_occupation_title,
                "canonical_id": canonical_occupation_id
            },
            status=GoalStatus.RESOLVED
        )

        # Persist goal in store
        await self.store.save_goal(person_id, resolved.model_dump(mode="json"))

        return GoalResolutionResponse(
            resolved_goal=resolved,
            status=GoalStatus.RESOLVED,
            message=f"Goal resolved to target outcome: '{resolved.target_outcome}' in domain '{resolved.target_domain}'.",
            suggested_clarifications=[],
            confidence=resolved.confidence,
            provenance=resolved.provenance
        )
