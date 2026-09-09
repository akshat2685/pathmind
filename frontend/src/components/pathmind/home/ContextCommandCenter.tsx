"use client";

import { useState, useEffect, useCallback } from "react";
import Link from "next/link";
import {
  Compass,
  Rocket,
  Sparkles,
  AlertCircle,
  ArrowRight,
  ShieldCheck,
  RefreshCw,
  History,
  HelpCircle
} from "lucide-react";

import { RecommendationDetailModal } from "@/components/pathmind/trust/RecommendationDetailModal";

interface NextActionItem {
  action_id: string;
  action_title: string;
  action_type: string;
  priority: string;
  target_stage_id?: string | null;
  target_skill?: string | null;
  target_opportunity_id?: string | null;
  facts: string[];
  interpretation: string[];
  tradeoffs: string[];
  recommendation_rationale: string;
  downstream_consequence: string;
}

interface DecisionRecordItem {
  decision_id: string;
  person_id: string;
  decision_type: string;
  title: string;
  user_choice: string;
  alternatives_considered: string[];
  supporting_evidence_ids: string[];
  context_snapshot_summary: Record<string, unknown>;
  outcome_state: string;
  outcome_note?: string | null;
  timestamp: string;
}

interface CommandCenterData {
  person_id: string;
  where_am_i: {
    current_stage: string;
    stage_number: number;
    progress_percent: number;
    completed_stages: number;
    total_stages: number;
    verified_skills_count: number;
  };
  where_am_i_going: {
    target_role: string;
    readiness_tier: string;
    match_score: number;
    target_timeline: string;
  };
  what_changed: {
    event_title: string;
    observation: string;
    timestamp: string;
  };
  what_is_blocking_me?: {
    title: string;
    description: string;
    missing_requirements: string[];
  } | null;
  what_should_i_do_now: NextActionItem;
  what_happens_after_that: string;
  recent_decisions: DecisionRecordItem[];
}

export function ContextCommandCenter() {
  const [data, setData] = useState<CommandCenterData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Outcome Modal State
  const [outcomeModalOpen, setOutcomeModalOpen] = useState(false);
  const [selectedDecisionId, setSelectedDecisionId] = useState<string>("");
  const [outcomeState, setOutcomeState] = useState("POSITIVE");
  const [outcomeNote, setOutcomeNote] = useState("");
  const [isSubmittingOutcome, setIsSubmittingOutcome] = useState(false);

  // Trace Drawer State
  const [selectedTrace, setSelectedTrace] = useState<DecisionRecordItem | null>(null);
  const [explainModalOpen, setExplainModalOpen] = useState(false);

  const fetchCommandCenter = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const baseUrl = process.env.NEXT_PUBLIC_API_BASE_URL || "https://pathmind-api.onrender.com";
      const personId = typeof window !== "undefined"
        ? (localStorage.getItem("pathmind_user_name")?.toLowerCase().replace(/\s+/g, "-") || "scholar-user")
        : "scholar-user";

      const res = await fetch(`${baseUrl}/api/context/command-center`, {
        headers: { "X-Person-ID": personId }
      });

      if (!res.ok) throw new Error("Failed to fetch context command center");
      const json: CommandCenterData = await res.json();
      setData(json);
    } catch (err) {
      console.error(err);
      setError("Unable to connect to live Personal Context Graph.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchCommandCenter();
  }, [fetchCommandCenter]);

  const handleOpenOutcome = (decId: string) => {
    setSelectedDecisionId(decId);
    setOutcomeState("POSITIVE");
    setOutcomeNote("");
    setOutcomeModalOpen(true);
  };

  const handleSubmitOutcome = async () => {
    if (!outcomeNote.trim()) return;
    setIsSubmittingOutcome(true);
    try {
      const baseUrl = process.env.NEXT_PUBLIC_API_BASE_URL || "https://pathmind-api.onrender.com";
      const personId = typeof window !== "undefined"
        ? (localStorage.getItem("pathmind_user_name")?.toLowerCase().replace(/\s+/g, "-") || "scholar-user")
        : "scholar-user";

      const res = await fetch(`${baseUrl}/api/context/decisions/${selectedDecisionId}/outcome`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-Person-ID": personId
        },
        body: JSON.stringify({
          outcome_state: outcomeState,
          outcome_note: outcomeNote.trim()
        })
      });

      if (res.ok) {
        setOutcomeModalOpen(false);
        await fetchCommandCenter();
      }
    } catch (err) {
      console.error(err);
    } finally {
      setIsSubmittingOutcome(false);
    }
  };

  if (loading && !data) {
    return (
      <div className="w-full p-8 flex items-center justify-center space-x-3 text-xs text-on-surface-variant">
        <RefreshCw className="w-5 h-5 text-primary animate-spin" />
        <span>Preparing your personalized guidance &amp; recommendations...</span>
      </div>
    );
  }

  if (error || !data) {
    return (
      <div className="w-full p-6 rounded-3xl bg-surface-container border border-outline text-center text-xs space-y-2">
        <p className="text-on-surface font-semibold">{error || "Context service unavailable"}</p>
        <button
          onClick={() => fetchCommandCenter()}
          className="px-4 py-2 rounded-xl bg-primary text-on-primary font-bold cursor-pointer"
        >
          Retry
        </button>
      </div>
    );
  }

  const act = data.what_should_i_do_now;

  return (
    <div className="w-full max-w-5xl mx-auto space-y-6 animate-in fade-in duration-300">
      {/* 1-3. Compact Context Summary Strip */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
        {/* 1. WHERE AM I? */}
        <div className="p-4 rounded-2xl bg-surface-container border border-outline/60 space-y-1.5 shadow-xs hover:border-primary/40 transition-colors">
          <div className="flex items-center justify-between">
            <span className="text-[10px] uppercase font-bold tracking-wider text-primary flex items-center gap-1">
              <Compass className="w-3 h-3" /> 1. Where Am I?
            </span>
            <span className="text-[11px] font-bold text-on-surface bg-surface px-2 py-0.5 rounded-md border border-outline/40">
              {data.where_am_i.progress_percent}% Roadmap
            </span>
          </div>
          <h4 className="font-bold text-sm text-on-surface truncate">{data.where_am_i.current_stage}</h4>
          <p className="text-[11px] text-on-surface-variant leading-tight">
            Stage 0{data.where_am_i.stage_number} Active • {data.where_am_i.verified_skills_count} Proven Skills
          </p>
        </div>

        {/* 2. WHERE AM I GOING? */}
        <div className="p-4 rounded-2xl bg-surface-container border border-outline/60 space-y-1.5 shadow-xs hover:border-secondary/40 transition-colors">
          <div className="flex items-center justify-between">
            <span className="text-[10px] uppercase font-bold tracking-wider text-secondary flex items-center gap-1">
              <Rocket className="w-3 h-3" /> 2. Where Am I Going?
            </span>
            <span className="text-[10px] px-2 py-0.5 rounded-md font-bold bg-secondary/15 text-secondary border border-secondary/30">
              {data.where_am_i_going.readiness_tier}
            </span>
          </div>
          <h4 className="font-bold text-sm text-on-surface truncate">{data.where_am_i_going.target_role}</h4>
          <p className="text-[11px] text-on-surface-variant leading-tight">
            Target Horizon: {data.where_am_i_going.target_timeline} • Match: {data.where_am_i_going.match_score}%
          </p>
        </div>

        {/* 3. WHAT CHANGED? */}
        <div className="p-4 rounded-2xl bg-surface-container border border-outline/60 space-y-1.5 shadow-xs hover:border-tertiary/40 transition-colors">
          <div className="flex items-center justify-between">
            <span className="text-[10px] uppercase font-bold tracking-wider text-tertiary flex items-center gap-1">
              <Sparkles className="w-3 h-3" /> 3. What Changed?
            </span>
            <span className="text-[10px] text-on-surface-variant">
              {new Date(data.what_changed.timestamp).toLocaleDateString()}
            </span>
          </div>
          <h4 className="font-bold text-sm text-on-surface truncate">{data.what_changed.event_title}</h4>
          <p className="text-[11px] text-on-surface-variant leading-tight truncate">
            {data.what_changed.observation}
          </p>
        </div>
      </div>

      {/* 4. WHAT IS BLOCKING ME? (If active) */}
      {data.what_is_blocking_me && (
        <div className="p-4 rounded-2xl bg-amber-950/30 border border-amber-600/50 text-xs text-amber-200 flex flex-col md:flex-row md:items-center justify-between gap-3">
          <div className="space-y-0.5">
            <div className="flex items-center gap-2 font-bold text-amber-300">
              <AlertCircle className="w-4 h-4 shrink-0" /> 4. What Is Blocking Me: {data.what_is_blocking_me.title}
            </div>
            <p className="text-[11px] text-amber-200/90">{data.what_is_blocking_me.description}</p>
          </div>
          <div className="flex flex-wrap gap-1 shrink-0">
            {data.what_is_blocking_me.missing_requirements.map((r, i) => (
              <span key={i} className="text-[10px] px-2 py-0.5 rounded-md bg-amber-900/50 border border-amber-600/40 text-amber-100 font-medium">
                {r}
              </span>
            ))}
          </div>
        </div>
      )}

      {/* 5. WHAT SHOULD I DO NOW? (Clear Focal Point) */}
      <div className="p-6 md:p-7 rounded-3xl bg-surface border-2 border-primary/40 shadow-lg space-y-5 relative overflow-hidden">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div className="space-y-1.5 max-w-xl">
            <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-[11px] font-bold uppercase tracking-wider bg-primary/15 text-primary border border-primary/30">
              <ShieldCheck className="w-3.5 h-3.5" /> 5. What Should I Do Now? • Priority {act.priority}
            </div>
            <h3 className="text-xl md:text-2xl font-bold font-headline-md text-on-surface tracking-tight leading-snug">
              {act.action_title}
            </h3>
            <p className="text-xs text-on-surface-variant">
              {act.recommendation_rationale}
            </p>
          </div>

          {/* Action Hierarchy: 1 Filled Primary + 1 Outlined Secondary */}
          <div className="flex flex-col sm:flex-row items-stretch sm:items-center gap-2.5 shrink-0">
            <button
              onClick={() => setExplainModalOpen(true)}
              className="inline-flex items-center justify-center gap-1.5 px-4 py-2.5 min-h-[44px] rounded-xl bg-surface border border-outline/70 hover:bg-surface-container text-on-surface font-medium text-xs transition-colors cursor-pointer"
            >
              <HelpCircle className="w-3.5 h-3.5 text-primary" />
              <span>Why This Recommendation?</span>
            </button>
            <Link
              href={act.action_type === "APPLY_OPPORTUNITY" ? "/readiness" : "/journey"}
              className="inline-flex items-center justify-center gap-2 px-6 py-3 min-h-[48px] rounded-xl bg-primary text-white font-bold text-sm shadow-md hover:bg-primary/90 transition-all cursor-pointer"
            >
              <span>Take Action Now</span>
              <ArrowRight className="w-4 h-4" />
            </Link>
          </div>
        </div>

        {/* Structured Context Breakdown: Facts vs Guidance Reasoning vs Key Considerations */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-3.5 text-xs pt-1">
          {/* Verified Facts */}
          <div className="p-3.5 rounded-xl bg-surface-container-low border border-outline/50 space-y-1.5">
            <span className="font-bold text-emerald-600 dark:text-emerald-400 uppercase tracking-wider text-[10px] block">
              Verified Facts (Your Track Record)
            </span>
            <ul className="space-y-1 text-on-surface-variant text-[11px] leading-relaxed">
              {act.facts.slice(0, 3).map((f, i) => (
                <li key={i} className="flex items-start gap-1.5">
                  <span className="text-emerald-500 font-bold shrink-0">•</span>
                  <span>{f}</span>
                </li>
              ))}
            </ul>
          </div>

          {/* Guidance Reasoning */}
          <div className="p-3.5 rounded-xl bg-surface-container-low border border-outline/50 space-y-1.5">
            <span className="font-bold text-primary uppercase tracking-wider text-[10px] block">
              Guidance Reasoning &amp; Inferences
            </span>
            <ul className="space-y-1 text-on-surface-variant text-[11px] leading-relaxed">
              {act.interpretation.slice(0, 3).map((inf, i) => (
                <li key={i} className="flex items-start gap-1.5">
                  <span className="text-primary font-bold shrink-0">•</span>
                  <span>{inf}</span>
                </li>
              ))}
            </ul>
          </div>

          {/* Key Considerations & Time Commitment */}
          <div className="p-3.5 rounded-xl bg-surface-container-low border border-outline/50 space-y-1.5">
            <span className="font-bold text-amber-600 dark:text-amber-400 uppercase tracking-wider text-[10px] block">
              Key Considerations &amp; Time Commitment
            </span>
            <ul className="space-y-1 text-on-surface-variant text-[11px] leading-relaxed">
              {act.tradeoffs.slice(0, 3).map((t, i) => (
                <li key={i} className="flex items-start gap-1.5">
                  <span className="text-amber-500 font-bold shrink-0">•</span>
                  <span>{t}</span>
                </li>
              ))}
            </ul>
          </div>
        </div>

        {/* 6. WHAT HAPPENS AFTER THAT? */}
        <div className="p-3 rounded-xl bg-surface-container-low/70 border border-outline/40 flex items-center justify-between gap-3 text-xs">
          <div className="flex items-center gap-2 text-on-surface-variant text-[11px] leading-tight min-w-0">
            <span className="font-bold text-on-surface text-[10px] uppercase tracking-wider shrink-0">6. Next Consequence:</span>
            <span className="truncate">{data.what_happens_after_that}</span>
          </div>
          <span className="text-[10px] text-primary font-bold uppercase tracking-wider shrink-0">Continuous Loop</span>
        </div>
      </div>

      {/* Decision Vault & Rationale Traces */}
      {data.recent_decisions.length > 0 && (
        <div className="bg-surface-container border border-outline rounded-3xl p-6 md:p-8 space-y-6">
          <div className="flex items-center justify-between border-b border-outline pb-4">
            <div>
              <h3 className="text-xl font-bold text-on-surface flex items-center gap-2">
                <History className="w-5 h-5 text-primary" /> Decision Vault &amp; Rationale History
              </h3>
              <p className="text-xs text-on-surface-variant mt-0.5">
                Transparent answers to &quot;Why did I choose this path?&quot; backed by context snapshots at decision time.
              </p>
            </div>
          </div>

          <div className="space-y-3">
            {data.recent_decisions.map((dec, i) => (
              <div key={i} className="p-5 rounded-2xl bg-surface border border-outline flex flex-col md:flex-row md:items-center justify-between gap-4 text-xs">
                <div className="space-y-1 flex-1">
                  <div className="flex items-center gap-2">
                    <span className="text-xs font-bold text-primary uppercase tracking-wider">{dec.decision_type.replace(/_/g, " ")}</span>
                    <span className="font-bold text-on-surface">{dec.title}</span>
                  </div>
                  <p className="text-on-surface-variant">
                    User Choice: <strong className="text-on-surface">{dec.user_choice}</strong> • Alternatives: {dec.alternatives_considered.join(", ") || "None"}
                  </p>
                  {dec.outcome_note && (
                    <div className="text-[11px] text-emerald-400 mt-1">
                      <strong>Observed Outcome ({dec.outcome_state}):</strong> {dec.outcome_note}
                    </div>
                  )}
                </div>

                <div className="flex items-center gap-2 shrink-0">
                  <button
                    onClick={() => setSelectedTrace(dec)}
                    className="px-3.5 py-1.5 rounded-xl border border-outline hover:bg-surface-container font-semibold text-on-surface cursor-pointer"
                  >
                    Why This Choice?
                  </button>
                  <button
                    onClick={() => handleOpenOutcome(dec.decision_id)}
                    className="px-3.5 py-1.5 rounded-xl bg-primary text-on-primary font-bold cursor-pointer"
                  >
                    Record Outcome
                  </button>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Why This Choice Drawer / Modal */}
      {selectedTrace && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm animate-in fade-in">
          <div className="bg-surface border border-outline rounded-3xl p-6 md:p-8 max-w-lg w-full space-y-6 shadow-2xl">
            <div className="space-y-1">
              <span className="text-xs font-bold uppercase tracking-wider text-primary flex items-center gap-1.5">
                <HelpCircle className="w-4 h-4" /> Context At Decision Time
              </span>
              <h3 className="text-xl font-bold text-on-surface">{selectedTrace.title}</h3>
              <p className="text-xs text-on-surface-variant">
                Recorded on {new Date(selectedTrace.timestamp).toLocaleString()}
              </p>
            </div>

            <div className="space-y-3 text-xs">
              <div className="p-3.5 rounded-2xl bg-surface-container border border-outline space-y-1">
                <span className="font-bold text-on-surface block text-[11px] uppercase">User Decision Choice</span>
                <p className="text-primary font-bold">{selectedTrace.user_choice}</p>
              </div>

              <div className="p-3.5 rounded-2xl bg-surface-container border border-outline space-y-1">
                <span className="font-bold text-on-surface block text-[11px] uppercase">Alternatives Evaluated</span>
                <p className="text-on-surface-variant">{selectedTrace.alternatives_considered.join(", ") || "Direct Selection"}</p>
              </div>

              <div className="p-3.5 rounded-2xl bg-surface-container border border-outline space-y-1">
                <span className="font-bold text-on-surface block text-[11px] uppercase">Snapshot Context</span>
                <pre className="text-[10px] text-on-surface-variant overflow-x-auto whitespace-pre-wrap">
                  {JSON.stringify(selectedTrace.context_snapshot_summary, null, 2)}
                </pre>
              </div>
            </div>

            <div className="flex justify-end">
              <button
                onClick={() => setSelectedTrace(null)}
                className="px-5 py-2.5 rounded-xl font-bold text-xs bg-primary text-on-primary cursor-pointer"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Record Outcome Modal */}
      {outcomeModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm animate-in fade-in">
          <div className="bg-surface border border-outline rounded-3xl p-6 md:p-8 max-w-lg w-full space-y-6 shadow-2xl">
            <div className="space-y-1">
              <h3 className="text-xl font-bold text-on-surface">Record Decision Outcome</h3>
              <p className="text-xs text-on-surface-variant">
                Log the empirical outcome of your decision to help the Personal Agent Learning Loop calibrate future strategy recommendations.
              </p>
            </div>

            <div className="space-y-4 text-xs">
              <div className="space-y-1.5">
                <label className="font-bold uppercase tracking-wider text-on-surface">Outcome State</label>
                <select
                  value={outcomeState}
                  onChange={(e) => setOutcomeState(e.target.value)}
                  className="w-full bg-surface-container border border-outline rounded-xl p-3 text-on-surface focus:outline-none focus:ring-2 focus:ring-primary"
                >
                  <option value="POSITIVE">Positive (Goal Advanced)</option>
                  <option value="MIXED">Mixed (Partially Effective)</option>
                  <option value="NEGATIVE">Negative (Encountered Blockers)</option>
                  <option value="SUPERSEDED">Superseded (Goals Shifted)</option>
                </select>
              </div>

              <div className="space-y-1.5">
                <label className="font-bold uppercase tracking-wider text-on-surface">Observed Outcome Note</label>
                <textarea
                  value={outcomeNote}
                  onChange={(e) => setOutcomeNote(e.target.value)}
                  placeholder="Describe what happened after executing this decision..."
                  rows={3}
                  className="w-full bg-surface-container border border-outline rounded-2xl p-3 text-on-surface focus:outline-none focus:ring-2 focus:ring-primary"
                />
              </div>
            </div>

            <div className="flex items-center justify-end gap-3 pt-2">
              <button
                onClick={() => setOutcomeModalOpen(false)}
                className="px-4 py-2.5 rounded-xl font-semibold text-xs bg-surface border border-outline text-on-surface hover:bg-surface-container cursor-pointer"
              >
                Cancel
              </button>
              <button
                onClick={handleSubmitOutcome}
                disabled={isSubmittingOutcome || !outcomeNote.trim()}
                className="px-5 py-2.5 rounded-xl font-bold text-xs bg-primary text-on-primary shadow-md hover:opacity-95 disabled:opacity-50 cursor-pointer"
              >
                {isSubmittingOutcome ? "Saving..." : "Save Outcome"}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Recommendation Explainability Modal */}
      <RecommendationDetailModal
        isOpen={explainModalOpen}
        onClose={() => setExplainModalOpen(false)}
        onDecisionMade={() => fetchCommandCenter()}
      />
    </div>
  );
}
