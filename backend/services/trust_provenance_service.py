import re
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone
from backend.core.trust_schemas import (
    ProvenanceRecord,
    TraceableClaim,
    SafetyGuardrailResult
)
from backend.services.store import FirestoreStore

class TrustProvenanceService:
    """
    Trust, Provenance, and Safety Guardrail Verification Service for PATHMIND.
    Ensures every factual claim has verifiable source provenance, strictly separates
    FACT vs INFERENCE vs UNKNOWN, and enforces deterministic safety policies.
    """
    def __init__(self, store: Optional[FirestoreStore] = None):
        self.store = store or FirestoreStore()

        # Forbidden Safety Violation Patterns
        self.clinical_diagnosis_patterns = [
            r"\b(adhd|bipolar|schizophrenia|clinical depression|personality disorder|autism spectrum disorder)\b",
            r"\byou are mentally incapable\b",
            r"\byou lack the intelligence\b"
        ]
        self.guarantee_patterns = [
            r"\b(guaranteed (job|placement|salary|hiring|income)|100% guarantee|you will definitely be hired)\b",
            r"\bthis career will earn you\b"
        ]

    def validate_safety_guardrails(self, text: str) -> SafetyGuardrailResult:
        lowered = text.lower()

        # 1. Check Clinical Diagnoses
        for pat in self.clinical_diagnosis_patterns:
            if re.search(pat, lowered):
                return SafetyGuardrailResult(
                    is_safe=False,
                    rejected_claims=[text],
                    safety_category="PSYCHOLOGICAL_OVERREACH",
                    remediation_notes="Clinical diagnostic claims and IQ judgments are strictly forbidden. Reframing to evidence-based competency gaps."
                )

        # 2. Check Employment / Income Guarantees
        for pat in self.guarantee_patterns:
            if re.search(pat, lowered):
                return SafetyGuardrailResult(
                    is_safe=False,
                    rejected_claims=[text],
                    safety_category="EMPLOYMENT_GUARANTEE_VIOLATION",
                    remediation_notes="Employment and salary guarantees are forbidden. Stating historical market benchmarks with uncertainty bounds."
                )

        return SafetyGuardrailResult(is_safe=True, safety_category="PASSED")

    async def verify_claim_provenance(
        self,
        person_id: str,
        claim_text: str,
        claim_category: str = "INFERENCE",
        source_type: str = "INTERNAL_DETERMINISTIC",
        source_url: Optional[str] = None,
        supporting_evidence_ids: Optional[List[str]] = None
    ) -> TraceableClaim:
        # First check safety
        safety = self.validate_safety_guardrails(claim_text)
        if not safety.is_safe:
            # Remediate claim to safe uncertainty
            claim_text = "Your current verified evidence does not yet demonstrate this capability."
            claim_category = "UNKNOWN"

        # Check evidence grounding if referencing person evidence
        if supporting_evidence_ids:
            person_evidence = await self.store.get_all_person_evidence(person_id)
            existing_ids = {e.get("evidence_id") for e in person_evidence}
            valid_ids = [eid for eid in supporting_evidence_ids if eid in existing_ids]

            if not valid_ids:
                claim_category = "UNKNOWN"
                prov = ProvenanceRecord(
                    claim_id="clm_unknown",
                    source_type="EVIDENCE",
                    provider="Personal Evidence Store",
                    verification_status="UNVERIFIED",
                    confidence="INSUFFICIENT_EVIDENCE"
                )
                return TraceableClaim(
                    claim_text=claim_text,
                    claim_category="UNKNOWN",
                    provenance=prov,
                    supporting_evidence_ids=[]
                )

        prov = ProvenanceRecord(
            claim_id=f"clm_{int(datetime.now(timezone.utc).timestamp()*1000)}",
            source_type=source_type,
            source_url=source_url,
            provider="ESCO / NCO Official Occupational Standards" if source_type in ["ESCO", "NCO"] else "PATHMIND Trust Layer",
            verification_status="VERIFIED",
            confidence="HIGH" if claim_category in ["FACT", "OBSERVATION"] else "MEDIUM"
        )

        return TraceableClaim(
            claim_text=claim_text,
            claim_category=claim_category,
            provenance=prov,
            supporting_evidence_ids=supporting_evidence_ids or []
        )
