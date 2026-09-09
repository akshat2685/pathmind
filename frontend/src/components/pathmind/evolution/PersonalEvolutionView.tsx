"use client";

import { useState, useEffect, useCallback } from "react";
import {
  History,
  TrendingUp,
  Sparkles,
  Search,
  RefreshCw,
  Layers,
  Milestone
} from "lucide-react";

interface CapabilityItem {
  skill_name: string;
  first_demonstrated_at?: string | null;
  current_mastery_state: string;
  evidence_count: number;
  progress_classification: string;
  regression_events: string[];
  recovery_events: string[];
}

interface StrategyItem {
  strategy_id: string;
  strategy_dimension: string;
  observed_attempts_count: number;
  successful_evaluations: number;
  effectiveness_status: string;
}

interface TurningPointItem {
  turning_point_id: string;
  event_type: string;
  title: string;
  what_happened: string;
  why_significant: string;
  what_changed_afterward: string;
  timestamp: string;
}

interface ProgressInsightItem {
  insight_id: string;
  type: string;
  claim: string;
  time_range: string;
  confidence: string;
  status: string;
  dispute_reason?: string | null;
}

interface LongitudinalStateData {
  person_id: string;
  current_state_summary: Record<string, unknown>;
  capability_history: CapabilityItem[];
  strategy_profiles: StrategyItem[];
  turning_points: TurningPointItem[];
  historical_then_transition_now_next: {
    then: { role_focus: string; verified_skills_count: number; summary: string };
    transition: { turning_point: string; trigger_event: string; adaptation_count: number };
    now: { active_target_role: string; current_stage: string; completed_stages: number; verified_skills_count: number; readiness_tier: string };
    next: { next_milestone: string; target_horizon: string; upcoming_opportunity: string };
  };
}

export function PersonalEvolutionView() {
  const [state, setState] = useState<LongitudinalStateData | null>(null);
  const [insights, setInsights] = useState<ProgressInsightItem[]>([]);
  const [loading, setLoading] = useState(true);

  // Temporal Query State
  const [queryText, setQueryText] = useState("");
  const [queryAnswer, setQueryAnswer] = useState<{ answer: string; status: string } | null>(null);
  const [isQuerying, setIsQuerying] = useState(false);

  // Dispute Modal State
  const [disputeModalOpen, setDisputeModalOpen] = useState(false);
  const [selectedInsightId, setSelectedInsightId] = useState<string>("");
  const [disputeReason, setDisputeReason] = useState("");
  const [isSubmittingDispute, setIsSubmittingDispute] = useState(false);

  const fetchLongitudinalData = useCallback(async () => {
    setLoading(true);
    try {
      const baseUrl = process.env.NEXT_PUBLIC_API_BASE_URL || "https://pathmind-api.onrender.com";
      const personId = typeof window !== "undefined"
        ? (localStorage.getItem("pathmind_user_name")?.toLowerCase().replace(/\s+/g, "-") || "scholar-user")
        : "scholar-user";

      const [stateRes, insightsRes] = await Promise.all([
        fetch(`${baseUrl}/api/longitudinal/state`, { headers: { "X-Person-ID": personId } }),
        fetch(`${baseUrl}/api/longitudinal/insights`, { headers: { "X-Person-ID": personId } })
      ]);

      if (stateRes.ok) {
        const sData: LongitudinalStateData = await stateRes.json();
        setState(sData);
      }
      if (insightsRes.ok) {
        const iData: ProgressInsightItem[] = await insightsRes.json();
        setInsights(iData);
      }
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchLongitudinalData();
  }, [fetchLongitudinalData]);

  const handleTemporalQuery = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!queryText.trim()) return;
    setIsQuerying(true);
    setQueryAnswer(null);

    try {
      const baseUrl = process.env.NEXT_PUBLIC_API_BASE_URL || "https://pathmind-api.onrender.com";
      const personId = typeof window !== "undefined"
        ? (localStorage.getItem("pathmind_user_name")?.toLowerCase().replace(/\s+/g, "-") || "scholar-user")
        : "scholar-user";

      const res = await fetch(`${baseUrl}/api/longitudinal/temporal-query`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-Person-ID": personId
        },
        body: JSON.stringify({ query_text: queryText.trim() })
      });

      if (res.ok) {
        const data = await res.json();
        setQueryAnswer({ answer: data.answer, status: data.status });
      }
    } catch (err) {
      console.error(err);
    } finally {
      setIsQuerying(false);
    }
  };

  const handleDispute = async () => {
    if (!disputeReason.trim()) return;
    setIsSubmittingDispute(true);
    try {
      const baseUrl = process.env.NEXT_PUBLIC_API_BASE_URL || "https://pathmind-api.onrender.com";
      const personId = typeof window !== "undefined"
        ? (localStorage.getItem("pathmind_user_name")?.toLowerCase().replace(/\s+/g, "-") || "scholar-user")
        : "scholar-user";

      const res = await fetch(`${baseUrl}/api/longitudinal/insights/${selectedInsightId}/dispute`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-Person-ID": personId
        },
        body: JSON.stringify({ dispute_reason: disputeReason.trim() })
      });

      if (res.ok) {
        setDisputeModalOpen(false);
        await fetchLongitudinalData();
      }
    } catch (err) {
      console.error(err);
    } finally {
      setIsSubmittingDispute(false);
    }
  };

  if (loading && !state) {
    return (
      <div className="w-full p-12 flex items-center justify-center space-x-3 text-xs text-on-surface-variant">
        <RefreshCw className="w-5 h-5 text-primary animate-spin" />
        <span>Reconstructing Longitudinal Development &amp; Trajectory...</span>
      </div>
    );
  }

  const flow = state?.historical_then_transition_now_next;

  return (
    <div className="w-full max-w-6xl mx-auto space-y-10 animate-in fade-in duration-500 pb-16">
      {/* Header Banner */}
      <div className="space-y-2">
        <div className="inline-flex items-center gap-2 px-3.5 py-1 rounded-full text-xs font-bold uppercase tracking-wider bg-primary/20 text-primary border border-primary/40">
          <History className="w-3.5 h-3.5" /> Longitudinal Learner Model
        </div>
        <h2 className="text-3xl font-black text-on-surface">Multi-Stage Personal Evolution</h2>
        <p className="text-xs text-on-surface-variant max-w-2xl leading-relaxed">
          Observable development across capabilities, strategy effectiveness, milestones, and turning points grounded strictly in verified evidence.
        </p>
      </div>

      {/* 1. FOUR-STAGE TEMPORAL FRAMEWORK: THEN -> TRANSITION -> NOW -> NEXT */}
      {flow && (
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          {/* THEN */}
          <div className="p-6 rounded-3xl bg-surface-container border border-outline space-y-3 shadow-sm">
            <span className="text-[10px] uppercase font-bold text-on-surface-variant tracking-wider block">1. Then (Earlier State)</span>
            <h4 className="font-bold text-base text-on-surface">{flow.then.role_focus}</h4>
            <p className="text-xs text-on-surface-variant leading-relaxed">{flow.then.summary}</p>
            <div className="pt-2 border-t border-outline/50 text-[11px] text-on-surface-variant flex justify-between">
              <span>Verified Proof:</span>
              <span className="font-bold text-on-surface">{flow.then.verified_skills_count} Artifacts</span>
            </div>
          </div>

          {/* TRANSITION */}
          <div className="p-6 rounded-3xl bg-surface-container border border-outline space-y-3 shadow-sm">
            <span className="text-[10px] uppercase font-bold text-primary tracking-wider block">2. Transition (What Changed)</span>
            <h4 className="font-bold text-base text-on-surface">{flow.transition.turning_point}</h4>
            <p className="text-xs text-on-surface-variant leading-relaxed">{flow.transition.trigger_event}</p>
            <div className="pt-2 border-t border-outline/50 text-[11px] text-on-surface-variant flex justify-between">
              <span>Plan Revisions:</span>
              <span className="font-bold text-primary">{flow.transition.adaptation_count} Adaptations</span>
            </div>
          </div>

          {/* NOW */}
          <div className="p-6 rounded-3xl bg-gradient-to-br from-surface-container-high to-surface border border-primary/40 space-y-3 shadow-md">
            <span className="text-[10px] uppercase font-bold text-emerald-400 tracking-wider block">3. Now (Current State)</span>
            <h4 className="font-bold text-base text-on-surface">{flow.now.active_target_role}</h4>
            <p className="text-xs text-on-surface-variant leading-relaxed">
              {flow.now.current_stage} • {flow.now.completed_stages} Completed Stages
            </p>
            <div className="pt-2 border-t border-outline/50 text-[11px] text-on-surface-variant flex justify-between">
              <span>Verified Skills:</span>
              <span className="font-bold text-emerald-400">{flow.now.verified_skills_count} Proven</span>
            </div>
          </div>

          {/* NEXT */}
          <div className="p-6 rounded-3xl bg-surface-container border border-secondary/40 space-y-3 shadow-sm">
            <span className="text-[10px] uppercase font-bold text-secondary tracking-wider block">4. Next (Upcoming Horizon)</span>
            <h4 className="font-bold text-base text-on-surface">{flow.next.next_milestone}</h4>
            <p className="text-xs text-on-surface-variant leading-relaxed">{flow.next.upcoming_opportunity}</p>
            <div className="pt-2 border-t border-outline/50 text-[11px] text-on-surface-variant flex justify-between">
              <span>Target Horizon:</span>
              <span className="font-bold text-secondary">{flow.next.target_horizon}</span>
            </div>
          </div>
        </div>
      )}

      {/* 2. INTERACTIVE TEMPORAL QUERY ENGINE */}
      <div className="p-8 rounded-3xl bg-surface-container border border-outline space-y-4 shadow-sm">
        <div className="space-y-1">
          <h3 className="font-bold text-lg text-on-surface flex items-center gap-2">
            <Search className="w-5 h-5 text-primary" /> Ask Your Longitudinal History
          </h3>
          <p className="text-xs text-on-surface-variant">
            Query past learning events, turning points, or strategy outcomes grounded in your real persisted timeline.
          </p>
        </div>

        <form onSubmit={handleTemporalQuery} className="flex flex-col sm:flex-row gap-3">
          <input
            type="text"
            value={queryText}
            onChange={(e) => setQueryText(e.target.value)}
            placeholder="e.g., When did I first demonstrate Python? or What strategy worked best?"
            className="flex-1 bg-surface border border-outline rounded-2xl px-4 py-3 text-xs text-on-surface focus:outline-none focus:ring-2 focus:ring-primary"
          />
          <button
            type="submit"
            disabled={isQuerying || !queryText.trim()}
            className="px-6 py-3 rounded-2xl bg-primary text-on-primary font-bold text-xs shadow-md hover:opacity-95 disabled:opacity-50 cursor-pointer"
          >
            {isQuerying ? "Querying..." : "Search Timeline"}
          </button>
        </form>

        {queryAnswer && (
          <div className="p-4 rounded-2xl bg-surface border border-primary/30 space-y-1 text-xs animate-in fade-in">
            <div className="flex items-center gap-2">
              <span className={`text-[10px] px-2 py-0.5 rounded-full font-bold uppercase ${
                queryAnswer.status === "ANSWERED" ? "bg-emerald-950/60 text-emerald-300 border border-emerald-600/50" : "bg-amber-950/60 text-amber-300 border border-amber-600/50"
              }`}>
                {queryAnswer.status}
              </span>
            </div>
            <p className="text-on-surface leading-relaxed pt-1">{queryAnswer.answer}</p>
          </div>
        )}
      </div>

      {/* 3. CAPABILITY EVOLUTION TRAJECTORY */}
      <div className="p-8 rounded-3xl bg-surface-container border border-outline space-y-6">
        <div className="flex items-center justify-between border-b border-outline pb-4">
          <div>
            <h3 className="font-bold text-xl text-on-surface flex items-center gap-2">
              <TrendingUp className="w-5 h-5 text-primary" /> Capability Trajectory &amp; Growth
            </h3>
            <p className="text-xs text-on-surface-variant mt-0.5">
              Deterministic progress classifications based on empirical code submissions.
            </p>
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {state?.capability_history.map((cap, i) => (
            <div key={i} className="p-5 rounded-2xl bg-surface border border-outline space-y-3 text-xs">
              <div className="flex items-center justify-between">
                <span className="font-bold text-sm text-on-surface">{cap.skill_name}</span>
                <span className={`text-[10px] px-2.5 py-0.5 rounded-full font-bold uppercase ${
                  cap.progress_classification === "IMPROVING" ? "bg-emerald-950/60 text-emerald-300 border border-emerald-600/50" :
                  cap.progress_classification === "REGRESSING" ? "bg-rose-950/60 text-rose-300 border border-rose-600/50" :
                  "bg-surface-container text-on-surface-variant border border-outline"
                }`}>
                  {cap.progress_classification}
                </span>
              </div>

              <div className="space-y-1.5 text-[11px] text-on-surface-variant">
                <div className="flex justify-between">
                  <span>Current Mastery State:</span>
                  <strong className="text-primary">{cap.current_mastery_state}</strong>
                </div>
                <div className="flex justify-between">
                  <span>Verified Evidence Count:</span>
                  <strong className="text-on-surface">{cap.evidence_count} Proofs</strong>
                </div>
                {cap.first_demonstrated_at && (
                  <div className="flex justify-between">
                    <span>First Demonstrated:</span>
                    <span>{new Date(cap.first_demonstrated_at).toLocaleDateString()}</span>
                  </div>
                )}
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* 4. LEARNING STRATEGY PROFILES & TURNING POINTS */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Strategy Effectiveness */}
        <div className="p-6 rounded-3xl bg-surface-container border border-outline space-y-4">
          <h3 className="font-bold text-lg text-on-surface flex items-center gap-2">
            <Layers className="w-5 h-5 text-secondary" /> Learning Strategy Effectiveness
          </h3>
          <p className="text-xs text-on-surface-variant">
            Empirically calibrated relationship between learning formats and successful evaluation attempts.
          </p>

          <div className="space-y-3 pt-2">
            {state?.strategy_profiles.map((strat, i) => (
              <div key={i} className="p-4 rounded-2xl bg-surface border border-outline flex items-center justify-between text-xs">
                <div className="space-y-0.5">
                  <span className="font-bold text-on-surface">{strat.strategy_dimension.replace(/_/g, " ")}</span>
                  <p className="text-[11px] text-on-surface-variant">
                    {strat.successful_evaluations} Passes / {strat.observed_attempts_count} Attempts
                  </p>
                </div>
                <span className={`text-[10px] px-2.5 py-0.5 rounded-full font-bold uppercase ${
                  strat.effectiveness_status === "SUPPORTED" ? "bg-emerald-950/60 text-emerald-300 border border-emerald-600/50" :
                  "bg-surface-container text-on-surface-variant border border-outline"
                }`}>
                  {strat.effectiveness_status}
                </span>
              </div>
            ))}
          </div>
        </div>

        {/* Milestone Turning Points */}
        <div className="p-6 rounded-3xl bg-surface-container border border-outline space-y-4">
          <h3 className="font-bold text-lg text-on-surface flex items-center gap-2">
            <Milestone className="w-5 h-5 text-tertiary" /> Milestone Turning Points
          </h3>
          <p className="text-xs text-on-surface-variant">
            Major pivots, capability breakthroughs, and roadmap transformations.
          </p>

          <div className="space-y-3 pt-2">
            {state?.turning_points.map((tp, i) => (
              <div key={i} className="p-4 rounded-2xl bg-surface border border-outline space-y-1.5 text-xs">
                <div className="flex items-center justify-between">
                  <span className="font-bold text-primary">{tp.title}</span>
                  <span className="text-[10px] text-on-surface-variant">{new Date(tp.timestamp).toLocaleDateString()}</span>
                </div>
                <p className="text-on-surface-variant text-[11px]">{tp.what_happened}</p>
                <div className="text-[10px] text-on-surface-variant/80 pt-1 border-t border-outline/40">
                  <strong>Impact:</strong> {tp.what_changed_afterward}
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* 5. PROGRESS INSIGHTS & DISPUTE SECTION */}
      {insights.length > 0 && (
        <div className="p-8 rounded-3xl bg-surface-container border border-outline space-y-6">
          <div className="flex items-center justify-between border-b border-outline pb-4">
            <div>
              <h3 className="font-bold text-xl text-on-surface flex items-center gap-2">
                <Sparkles className="w-5 h-5 text-primary" /> Progress Insights &amp; Growth Signals
              </h3>
              <p className="text-xs text-on-surface-variant mt-0.5">
                Transparent conclusions derived from longitudinal development. You retain the authority to challenge any insight.
              </p>
            </div>
          </div>

          <div className="space-y-3">
            {insights.map((ins, i) => (
              <div key={i} className="p-5 rounded-2xl bg-surface border border-outline flex flex-col sm:flex-row sm:items-center justify-between gap-4 text-xs">
                <div className="space-y-1 flex-1">
                  <div className="flex items-center gap-2">
                    <span className="text-[10px] px-2 py-0.5 rounded-full font-bold uppercase bg-primary/20 text-primary border border-primary/40">
                      {ins.type.replace(/_/g, " ")}
                    </span>
                    <span className="font-bold text-on-surface">{ins.claim}</span>
                  </div>
                  <p className="text-[11px] text-on-surface-variant">Time Range: {ins.time_range}</p>
                  {ins.status === "DISPUTED" && (
                    <div className="text-[11px] text-amber-300 font-semibold mt-1">
                      Disputed by learner: {ins.dispute_reason}
                    </div>
                  )}
                </div>

                {ins.status !== "DISPUTED" && (
                  <button
                    onClick={() => {
                      setSelectedInsightId(ins.insight_id);
                      setDisputeReason("");
                      setDisputeModalOpen(true);
                    }}
                    className="px-3.5 py-1.5 rounded-xl border border-outline hover:bg-surface-container text-on-surface-variant font-semibold text-[11px] shrink-0 cursor-pointer"
                  >
                    Challenge / Add Context
                  </button>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Dispute Modal */}
      {disputeModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm animate-in fade-in">
          <div className="bg-surface border border-outline rounded-3xl p-6 md:p-8 max-w-lg w-full space-y-6 shadow-2xl">
            <div className="space-y-1">
              <h3 className="text-xl font-bold text-on-surface">Challenge Progress Insight</h3>
              <p className="text-xs text-on-surface-variant">
                Provide your correction or additional context. This updates the Personal Agent Learning Loop calibration while preserving historical records.
              </p>
            </div>

            <div className="space-y-3 text-xs">
              <label className="font-bold uppercase tracking-wider text-on-surface">Your Context / Correction</label>
              <textarea
                value={disputeReason}
                onChange={(e) => setDisputeReason(e.target.value)}
                placeholder="Explain why this insight does not match your experience..."
                rows={4}
                className="w-full bg-surface-container border border-outline rounded-2xl p-3 text-on-surface focus:outline-none focus:ring-2 focus:ring-primary"
              />
            </div>

            <div className="flex items-center justify-end gap-3 pt-2">
              <button
                onClick={() => setDisputeModalOpen(false)}
                className="px-4 py-2.5 rounded-xl font-semibold text-xs bg-surface border border-outline text-on-surface hover:bg-surface-container cursor-pointer"
              >
                Cancel
              </button>
              <button
                onClick={handleDispute}
                disabled={isSubmittingDispute || !disputeReason.trim()}
                className="px-5 py-2.5 rounded-xl font-bold text-xs bg-primary text-on-primary shadow-md hover:opacity-95 disabled:opacity-50 cursor-pointer"
              >
                {isSubmittingDispute ? "Saving..." : "Save Correction"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
