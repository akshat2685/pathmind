"use client";

export interface ClassifiedClaim {
  text: string;
  claim_category: string;
  verification_status: string;
}

/**
 * ClaimBadge — renders the trust provenance of a single AI claim.
 * Every statement the model makes about the learner carries a FACT /
 * INFERENCE / UNKNOWN label backed by a persisted provenance record.
 * This is how the user sees *why* they should believe a claim.
 */
export function ClaimBadge({ claim }: { claim: ClassifiedClaim | string }) {
  const category =
    typeof claim === "string" ? "UNKNOWN" : (claim.claim_category || "UNKNOWN").toUpperCase();
  const text = typeof claim === "string" ? claim : claim.text;

  const styles: Record<string, { label: string; cls: string }> = {
    FACT: { label: "Verified fact", cls: "bg-emerald-500/10 text-emerald-600 border-emerald-500/30" },
    USER_STATED: { label: "You stated", cls: "bg-emerald-500/10 text-emerald-600 border-emerald-500/30" },
    OBSERVATION: { label: "Observed", cls: "bg-sky-500/10 text-sky-600 border-sky-500/30" },
    ASSESSMENT: { label: "Assessment", cls: "bg-sky-500/10 text-sky-600 border-sky-500/30" },
    INFERENCE: { label: "Model inference", cls: "bg-sky-500/10 text-sky-600 border-sky-500/30" },
    RECOMMENDATION: { label: "Recommendation", cls: "bg-violet-500/10 text-violet-600 border-violet-500/30" },
    UNKNOWN: { label: "Unverified", cls: "bg-amber-500/10 text-amber-600 border-amber-500/30" },
  };
  const s = styles[category] || styles.UNKNOWN;

  return (
    <span className="inline-flex flex-col gap-1">
      <span>{text}</span>
      <span
        title={
          category === "FACT" || category === "USER_STATED"
            ? "Backed by evidence you provided and verified"
            : category === "UNKNOWN"
              ? "The system could not ground this in your evidence — treat as provisional"
              : "The model's judgment based on your evidence — not a verified fact"
        }
        className={`inline-flex w-fit items-center gap-1 rounded-full border px-2 py-0.5 text-[10px] font-medium ${s.cls}`}
      >
        <span className="material-symbols-outlined text-[11px]">
          {category === "FACT" || category === "USER_STATED" ? "verified" : category === "UNKNOWN" ? "help" : "psychology"}
        </span>
        {s.label}
      </span>
    </span>
  );
}
