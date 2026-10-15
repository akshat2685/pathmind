"""
PathMind intelligence pack — integration service.

Wraps the vendored intelligence components (backend/intelligence/):
  1. readiness-to-change classifier  -> predict_readiness()
  2. Indian learning-resources KB    -> retrieve_resources()
  3. professions encyclopedia KB     -> retrieve_professions()

Honesty architecture (non-negotiable, mirrors intelligence/README.md):
  - The classifier output is a SCREENING HEURISTIC, never a psychological
    diagnosis. The disclaimer travels with every prediction.
  - The KBs are curated, verified, ML-indexed knowledge — NOT "trained models".
  - Profession salaries are ranges marked "estimate", never precise facts.

Lazy loading: the sklearn-dependent vendored modules are imported on first
use, never at import time, so importing this service can never break the app
when dependencies are missing. Every public method fails soft (None / [])
so intelligence-pack failures never break onboarding or counseling.
"""

import importlib.util
import os
import sys
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

_INTEL_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "intelligence"
)

# Version pins — model files and KB snapshots carry versions so retraining /
# refreshing later is clean and old behavior stays reproducible.
READINESS_MODEL_VERSION = "readiness-svc-v1"
RESOURCES_KB_VERSION = "resources-kb-2026-10-15"
PROFESSIONS_KB_VERSION = "professions-kb-2026-10-15"

READINESS_STAGES = (
    "precontemplation",
    "contemplation",
    "preparation",
    "action",
    "maintenance",
)

# Counselor steering per readiness stage. The raw label is NEVER shown to the
# user as a verdict — it steers tone only. See intelligence/README.md.
READINESS_STEERING = {
    "precontemplation": (
        "Motivational, exploratory framing. The learner is not yet considering "
        "change — do NOT dump a roadmap or push commitments. Ask what matters "
        "to them; surface ambivalence gently."
    ),
    "contemplation": (
        "Gentle, exploratory framing. The learner is weighing whether to "
        "commit — help them weigh pros and cons, do NOT push a full plan yet."
    ),
    "preparation": (
        "Concrete planning may begin. The learner is getting ready — small, "
        "specific next steps are welcome."
    ),
    "action": (
        "Full planning and accountability welcome. The learner is actively "
        "working toward change — be concrete and actionable."
    ),
    "maintenance": (
        "Full planning welcome, with emphasis on sustaining progress and "
        "preventing relapse into old patterns."
    ),
}


def _load_module(name: str, path: str):
    """Load a vendored script file as a module (they are scripts, not packages)."""
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Cannot load intelligence module from {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


class IntelligenceService:
    """Lazy, fail-soft access to the PathMind intelligence pack."""

    def __init__(self):
        self._predict_fn = None
        self._retrieve_resources_fn = None
        self._retrieve_professions_fn = None
        self._load_error: Optional[str] = None
        self._attempted = False

    def _ensure_loaded(self) -> bool:
        if self._attempted:
            return self._load_error is None
        self._attempted = True
        try:
            inference = _load_module(
                "pm_intel_inference",
                os.path.join(_INTEL_DIR, "classifier", "inference.py"),
            )
            resources_retrieval = _load_module(
                "pm_intel_resources_retrieval",
                os.path.join(_INTEL_DIR, "resources_kb", "retrieval.py"),
            )
            professions_retrieval = _load_module(
                "pm_intel_professions_retrieval",
                os.path.join(_INTEL_DIR, "professions_kb", "retrieval.py"),
            )
            self._predict_fn = inference.predict
            self._retrieve_resources_fn = resources_retrieval.retrieve
            self._retrieve_professions_fn = professions_retrieval.retrieve
        except Exception as e:  # missing sklearn, missing files, etc.
            self._load_error = str(e)
        return self._load_error is None

    @property
    def available(self) -> bool:
        """True when all three components loaded successfully."""
        return self._ensure_loaded()

    @property
    def load_error(self) -> Optional[str]:
        self._ensure_loaded()
        return self._load_error

    # ------------------------------------------------------------------
    # 1. Readiness classifier (the actual trained ML model)
    # ------------------------------------------------------------------
    def predict_readiness(
        self,
        text: str,
        personal_context: Optional[Dict[str, Any]] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        Classify onboarding free text into a readiness stage.

        Returns {"stage", "confidence", "note", "model_version", "assessed_at"}
        or None when the classifier is unavailable. `note` always carries the
        screening-heuristic disclaimer — it must travel with the prediction
        into storage and any downstream use.

        personal_context (optional, honest personalization): behavioral facts
        about THIS learner, e.g. {"completions_per_week": 1.5, "lapsed": 2}.
        It never changes the stage label (honest held-out accuracy 0.4927 —
        the label stays a weak generic signal); it only appends a momentum
        sentence to `note` so downstream steering reflects the person's own
        demonstrated pace. This is the data foundation a future personal
        model trains on — recorded, not pretended.
        """
        if not self._ensure_loaded():
            return None
        try:
            result = self._predict_fn(text or "")
        except Exception:
            return None
        if not isinstance(result, dict) or result.get("stage") not in READINESS_STAGES:
            return None
        note = result.get("note", "")
        if personal_context:
            try:
                per_week = personal_context.get("completions_per_week")
                lapsed = personal_context.get("lapsed", 0) or 0
                bits = []
                if isinstance(per_week, (int, float)) and per_week > 0:
                    bits.append(
                        f"their own measured pace is {per_week} commitments/week"
                    )
                if lapsed:
                    bits.append(
                        f"{lapsed} commitment{'s' if lapsed != 1 else ''} lapsed "
                        f"unfinished"
                    )
                if bits:
                    note = (note + " Personal momentum (" + "; ".join(bits) +
                            ") — from this learner's behavior, not the model.").strip()
            except Exception:
                pass
        return {
            "stage": result["stage"],
            "confidence": result.get("confidence", 0.0),
            "note": note,
            "model_version": READINESS_MODEL_VERSION,
            "assessed_at": datetime.now(timezone.utc).isoformat(),
        }

    # ------------------------------------------------------------------
    # 2 & 3. KB retrieval (curated, verified, ML-indexed knowledge)
    # ------------------------------------------------------------------
    def retrieve_resources(self, query: str, k: int = 5) -> List[Dict[str, Any]]:
        """retrieve(query, k) -> [{"entry": dict, "score": float}]; [] on failure."""
        if not self._ensure_loaded():
            return []
        try:
            hits = self._retrieve_resources_fn(query or "", k=k) or []
        except Exception:
            return []
        return [
            {"entry": h["entry"], "score": float(h["score"])}
            for h in hits
            if isinstance(h, dict) and isinstance(h.get("entry"), dict)
        ]

    def retrieve_professions(self, query: str, k: int = 5) -> List[Dict[str, Any]]:
        """retrieve(query, k) -> [{"entry": dict, "score": float}]; [] on failure."""
        if not self._ensure_loaded():
            return []
        try:
            hits = self._retrieve_professions_fn(query or "", k=k) or []
        except Exception:
            return []
        return [
            {"entry": h["entry"], "score": float(h["score"])}
            for h in hits
            if isinstance(h, dict) and isinstance(h.get("entry"), dict)
        ]


_service: Optional[IntelligenceService] = None


def get_intelligence_service() -> IntelligenceService:
    """Process-wide singleton (mirrors get_pm_store() pattern)."""
    global _service
    if _service is None:
        _service = IntelligenceService()
    return _service


# ----------------------------------------------------------------------
# Evidence-block formatting for the counselor prompt
# ----------------------------------------------------------------------
_SCORE_FLOOR = 0.10  # ignore retrieval hits below this; prompt says "use if relevant"


def _format_resource_entry(e: Dict[str, Any]) -> str:
    cost = e.get("cost_inr")
    cost_str = "Free" if cost == 0 else (f"~Rs {cost}" if cost else "see provider page")
    verified = "" if e.get("url_verified", True) else " (URL not re-verified)"
    return (
        f"- {e.get('name')} [{e.get('type')}, {e.get('language')}, "
        f"{e.get('level')}] — {cost_str}{verified}\n"
        f"  {e.get('url')}\n"
        f"  {e.get('notes', '')}"
    )


def _format_profession_entry(e: Dict[str, Any]) -> str:
    sal = e.get("salary_inr") or {}
    entry_pay = sal.get("entry", "?")
    exp_pay = sal.get("experienced", "?")
    pros = "; ".join((e.get("pros") or [])[:3])
    cons = "; ".join((e.get("cons") or [])[:3])
    return (
        f"- {e.get('name')} ({e.get('category')})\n"
        f"  {e.get('description', '')[:280]}\n"
        f"  Entry paths: {', '.join(e.get('entry_paths') or [])[:200]}\n"
        f"  Salary (ESTIMATE, not a fact): {entry_pay} entry / {exp_pay} experienced\n"
        f"  Pros: {pros}\n"
        f"  Cons: {cons}"
    )


def build_evidence_block(
    user_message: str,
    aspiration: Optional[str] = None,
    k: int = 3,
) -> Optional[str]:
    """
    Retrieve intelligence-pack evidence for a counselor turn and format it as
    a prompt block with hard grounding instructions.

    Calibrated uncertainty: when nothing relevant is retrieved, returns an
    explicit NO_VERIFIED_RESULTS marker (not None) so the counselor says
    plainly that it has no verified data instead of inventing an answer.
    Returns None only when the service itself is unavailable.
    """
    service = get_intelligence_service()
    if not service.available:
        return None
    query = user_message or ""
    if aspiration:
        query = f"{query} {aspiration}"
    prof_hits = [h for h in service.retrieve_professions(query, k=k) if h["score"] >= _SCORE_FLOOR]
    res_hits = [h for h in service.retrieve_resources(query, k=k) if h["score"] >= _SCORE_FLOOR]
    if not prof_hits and not res_hits:
        return (
            "NO_VERIFIED_RESULTS: the intelligence pack has no verified "
            "entries relevant to this message. Say plainly that you don't "
            "have verified data on this topic — do NOT answer from general "
            "knowledge as if it were verified."
        )

    parts = [
        "INTELLIGENCE EVIDENCE — verified PathMind knowledge. Cite these entries "
        "when relevant; never invent names, URLs, prices, or salaries."
    ]
    if res_hits:
        parts.append("Learning resources (India-specific, verified):")
        parts.extend(_format_resource_entry(h["entry"]) for h in res_hits)
    if prof_hits:
        parts.append("Professions (balanced pros/cons, India-grounded):")
        parts.extend(_format_profession_entry(h["entry"]) for h in prof_hits)
    parts.append(
        "HARD RULES: names, URLs, prices, salaries ONLY from the entries above. "
        "Salaries are ESTIMATES — always label them as such ('estimated'). "
        "Prices drift — prefer 'check the provider page' over quoting a number "
        "as fact. If none of these entries are relevant to the user's message, "
        "ignore them and say so rather than inventing alternatives."
    )
    return "\n".join(parts)


def readiness_steering_text(stage: Optional[str]) -> Optional[str]:
    """Tone-steering line for the counselor system prompt. Never a user verdict."""
    if stage in READINESS_STEERING:
        return (
            "Readiness screening (heuristic, NOT a diagnosis — never state the "
            f"stage label to the user as a verdict): {stage}. "
            f"{READINESS_STEERING[stage]}"
        )
    return None
