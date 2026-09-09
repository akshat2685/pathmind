"use client";

import { useState, useEffect, useCallback } from "react";
import {
  ShieldCheck,
  CheckCircle2,
  Lock,
  Clock,
  AlertTriangle,
  RefreshCw,
  Sparkles,
  FileCode,
  HelpCircle,
  MessageSquare
} from "lucide-react";

interface SkillMasteryItem {
  skill_name: string;
  category: string;
  mastery_state: string;
  evidence_count: number;
  primary_evidence_id?: string | null;
  last_verified_at: string;
  is_regression_risk: boolean;
  regression_reason?: string | null;
}

interface CapabilityItem {
  stage_id: string;
  stage_number: number;
  title: string;
  objective: string;
  skills: string[];
}

interface EvidenceNeededItem {
  stage_id: string;
  requirements: string[];
  minimum_quality: string;
  accepted_formats: string[];
}

interface LockedStageItem {
  stage_id: string;
  stage_number: number;
  title: string;
  prerequisite_stage_id: string;
  prerequisite_title: string;
  missing_capabilities: string[];
  required_evidence_type: string;
  unlock_rule: string;
}

interface EvaluationAttemptItem {
  attempt_id: string;
  submission_id: string;
  evidence_id: string;
  stage_id: string;
  person_id: string;
  attempt_number: number;
  status: string;
  score_accuracy: number;
  evaluation_detail: {
    observed: string[];
    inferred: string[];
    recommendation: string[];
    mastery_state_achieved: string;
    observable_misconceptions: string[];
    transfer_validated: boolean;
    evidence_quality_awarded: string;
  };
  evaluated_at: string;
}

interface EvidenceDisputeItem {
  dispute_id: string;
  person_id: string;
  attempt_id: string;
  reason: string;
  additional_evidence_reference?: string | null;
  status: string;
  resolution_note?: string | null;
  created_at: string;
}

interface MasteryDashboardStateData {
  person_id: string;
  skills_mastered: SkillMasteryItem[];
  capabilities_working_on: CapabilityItem[];
  evidence_needed: EvidenceNeededItem[];
  locked_stages: LockedStageItem[];
  recent_evaluations: EvaluationAttemptItem[];
  active_disputes: EvidenceDisputeItem[];
}

export function MasteryDashboard() {
  const [dashboard, setDashboard] = useState<MasteryDashboardStateData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Dispute Modal State
  const [disputeModalOpen, setDisputeModalOpen] = useState(false);
  const [selectedAttemptId, setSelectedAttemptId] = useState<string>("");
  const [disputeReason, setDisputeReason] = useState("");
  const [disputeRef, setDisputeRef] = useState("");
  const [isSubmittingDispute, setIsSubmittingDispute] = useState(false);
  const [disputeToast, setDisputeToast] = useState(false);

  const fetchDashboard = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const baseUrl = process.env.NEXT_PUBLIC_API_BASE_URL || "https://pathmind-api.onrender.com";
      const personId = typeof window !== "undefined"
        ? (localStorage.getItem("pathmind_user_name")?.toLowerCase().replace(/\s+/g, "-") || "scholar-user")
        : "scholar-user";

      const res = await fetch(`${baseUrl}/api/evidence/dashboard`, {
        headers: { "X-Person-ID": personId }
      });

      if (!res.ok) throw new Error("Failed to fetch mastery dashboard");
      const data: MasteryDashboardStateData = await res.json();
      setDashboard(data);
    } catch (err) {
      console.error(err);
      setError("Unable to connect to live Evidence & Mastery engine.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchDashboard();
  }, [fetchDashboard]);

  const handleOpenDispute = (attemptId: string) => {
    setSelectedAttemptId(attemptId);
    setDisputeReason("");
    setDisputeRef("");
    setDisputeModalOpen(true);
  };

  const handleSubmitDispute = async () => {
    if (!disputeReason.trim()) return;
    setIsSubmittingDispute(true);
    try {
      const baseUrl = process.env.NEXT_PUBLIC_API_BASE_URL || "https://pathmind-api.onrender.com";
      const personId = typeof window !== "undefined"
        ? (localStorage.getItem("pathmind_user_name")?.toLowerCase().replace(/\s+/g, "-") || "scholar-user")
        : "scholar-user";

      const res = await fetch(`${baseUrl}/api/evidence/dispute`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-Person-ID": personId
        },
        body: JSON.stringify({
          attempt_id: selectedAttemptId,
          reason: disputeReason.trim(),
          additional_evidence_reference: disputeRef.trim() || undefined
        })
      });

      if (res.ok) {
        setDisputeModalOpen(false);
        setDisputeToast(true);
        setTimeout(() => setDisputeToast(false), 4000);
        await fetchDashboard();
      }
    } catch (err) {
      console.error(err);
    } finally {
      setIsSubmittingDispute(false);
    }
  };

  const getMasteryBadge = (stateStr: string, isRisk: boolean) => {
    if (isRisk) {
      return "bg-rose-950/60 text-rose-300 border-rose-600/60";
    }
    switch (stateStr) {
      case "DEMONSTRATED_MASTERY":
        return "bg-emerald-950/60 text-emerald-300 border-emerald-600/60";
      case "TRANSFER":
        return "bg-cyan-950/60 text-cyan-300 border-cyan-600/60";
      case "APPLICATION":
        return "bg-blue-950/60 text-blue-300 border-blue-600/60";
      case "UNDERSTANDING":
        return "bg-amber-950/60 text-amber-300 border-amber-600/60";
      case "NEEDS_REINFORCEMENT":
      default:
        return "bg-surface-container text-on-surface-variant border-outline";
    }
  };

  if (loading && !dashboard) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[60vh] space-y-4">
        <RefreshCw className="w-8 h-8 text-primary animate-spin" />
        <p className="text-xs text-on-surface-variant font-semibold">
          Loading evidence-based mastery states and verification audits...
        </p>
      </div>
    );
  }

  if (error || !dashboard) {
    return (
      <div className="max-w-2xl mx-auto p-8 rounded-3xl bg-surface-container border border-outline text-center space-y-4">
        <AlertTriangle className="w-8 h-8 text-amber-400 mx-auto" />
        <h3 className="text-lg font-bold text-on-surface">Evidence Engine Offline</h3>
        <p className="text-xs text-on-surface-variant">{error || "Backend service unreachable."}</p>
        <button
          onClick={() => fetchDashboard()}
          className="px-5 py-2.5 rounded-xl bg-primary text-on-primary text-xs font-bold shadow-md cursor-pointer"
        >
          Retry
        </button>
      </div>
    );
  }

  return (
    <div className="w-full max-w-7xl mx-auto space-y-8 animate-in fade-in duration-500">
      {/* Header Banner */}
      <div className="relative rounded-3xl overflow-hidden p-8 md:p-12 border border-outline bg-gradient-to-br from-surface-container via-surface to-surface-container-high shadow-2xl">
        <div className="absolute top-0 right-0 w-96 h-96 bg-primary/10 rounded-full blur-3xl pointer-events-none -mr-20 -mt-20" />
        <div className="relative z-10 flex flex-col md:flex-row md:items-center justify-between gap-6">
          <div className="space-y-3">
            <div className="inline-flex items-center gap-2 px-3.5 py-1 rounded-full text-xs font-semibold tracking-wider uppercase bg-primary/15 text-primary border border-primary/30">
              <ShieldCheck className="w-3.5 h-3.5" />
              Evidence-Based Mastery &amp; Verification Engine
            </div>
            <h1 className="text-3xl md:text-5xl font-extrabold tracking-tight text-on-surface">
              Evidence &amp; Mastery
            </h1>
            <p className="text-on-surface-variant max-w-3xl text-sm md:text-base leading-relaxed">
              Transparent proof-of-competency: answers &quot;Can you actually demonstrate the capability?&quot; instead of &quot;Did you click complete?&quot;
            </p>
          </div>

          <div className="flex flex-col gap-2 min-w-[200px] text-xs">
            <div className="p-4 rounded-2xl bg-surface border border-outline space-y-1">
              <span className="text-on-surface-variant font-semibold block uppercase text-[10px]">Verified Capabilities</span>
              <span className="text-2xl font-black text-primary">{dashboard.skills_mastered.length} Skills Proven</span>
            </div>
          </div>
        </div>
      </div>

      {/* Dispute Toast */}
      {disputeToast && (
        <div className="p-4 rounded-2xl bg-emerald-950/80 border border-emerald-600 text-emerald-300 text-sm font-semibold flex items-center gap-2 animate-in fade-in">
          <CheckCircle2 className="w-4 h-4" /> Evaluation challenge recorded. Your dispute has been submitted for audit review.
        </div>
      )}

      {/* 1. What I Can Do (Demonstrated Skills Grid) */}
      <div className="bg-surface-container border border-outline rounded-3xl p-6 md:p-8 space-y-6">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-2 border-b border-outline pb-4">
          <div>
            <h3 className="text-xl font-bold text-on-surface flex items-center gap-2">
              <CheckCircle2 className="w-5 h-5 text-emerald-400" /> What I Can Do (Verified Competencies)
            </h3>
            <p className="text-xs text-on-surface-variant mt-0.5">
              Capabilities grounded in passing code artifacts, unit tests, and structured evaluations.
            </p>
          </div>
          <span className="text-xs px-3 py-1 rounded-full font-bold bg-surface text-on-surface border border-outline">
            {dashboard.skills_mastered.length} Active Masteries
          </span>
        </div>

        {dashboard.skills_mastered.length === 0 ? (
          <div className="p-8 text-center rounded-2xl bg-surface border border-outline text-xs text-on-surface-variant">
            No demonstrated skills recorded yet. Complete your first stage mission evidence to unlock verified competency badges.
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {dashboard.skills_mastered.map((sk, i) => (
              <div key={i} className="p-5 rounded-3xl bg-surface border border-outline space-y-3 shadow-sm hover:border-primary/50 transition-all">
                <div className="flex items-center justify-between">
                  <span className={`text-[11px] px-2.5 py-0.5 rounded-full font-bold uppercase tracking-wider border ${getMasteryBadge(sk.mastery_state, sk.is_regression_risk)}`}>
                    {sk.is_regression_risk ? "MASTERY AT RISK" : sk.mastery_state.replace(/_/g, " ")}
                  </span>
                  <span className="text-[11px] text-on-surface-variant font-medium">
                    {sk.evidence_count} {sk.evidence_count === 1 ? "Artifact" : "Artifacts"}
                  </span>
                </div>
                <h4 className="font-bold text-base text-on-surface">{sk.skill_name}</h4>
                <p className="text-xs text-on-surface-variant">{sk.category}</p>
                {sk.is_regression_risk && sk.regression_reason && (
                  <div className="p-2.5 rounded-xl bg-rose-950/40 border border-rose-600/40 text-[11px] text-rose-300">
                    <strong>Regression Risk:</strong> {sk.regression_reason}
                  </div>
                )}
                <div className="pt-2 border-t border-outline/50 flex items-center justify-between text-[11px] text-on-surface-variant">
                  <span>Verified Recency</span>
                  <span>{new Date(sk.last_verified_at).toLocaleDateString()}</span>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* 2. What I Am Working On & What I Need To Prove */}
      {dashboard.capabilities_working_on.length > 0 && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Working On */}
          <div className="bg-surface-container border border-outline rounded-3xl p-6 md:p-8 space-y-4">
            <h3 className="text-lg font-bold text-on-surface flex items-center gap-2">
              <Sparkles className="w-5 h-5 text-primary" /> What I Am Working On
            </h3>
            {dashboard.capabilities_working_on.map((cap, i) => (
              <div key={i} className="p-5 rounded-2xl bg-surface border border-outline space-y-2">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-bold text-primary">Stage 0{cap.stage_number} Active Focus</span>
                </div>
                <h4 className="font-bold text-base text-on-surface">{cap.title}</h4>
                <p className="text-xs text-on-surface-variant leading-relaxed">{cap.objective}</p>
                <div className="flex flex-wrap gap-1.5 pt-2">
                  {cap.skills.map((s, idx) => (
                    <span key={idx} className="text-[11px] px-2.5 py-0.5 rounded-lg bg-surface-container text-on-surface border border-outline font-medium">
                      {s}
                    </span>
                  ))}
                </div>
              </div>
            ))}
          </div>

          {/* What I Need To Prove */}
          <div className="bg-surface-container border border-outline rounded-3xl p-6 md:p-8 space-y-4">
            <h3 className="text-lg font-bold text-on-surface flex items-center gap-2">
              <FileCode className="w-5 h-5 text-cyan-400" /> What I Need To Prove
            </h3>
            {dashboard.evidence_needed.map((need, i) => (
              <div key={i} className="p-5 rounded-2xl bg-surface border border-outline space-y-3">
                <div className="space-y-1">
                  <span className="text-xs font-bold text-cyan-400 uppercase tracking-wider block">Evidence Requirements</span>
                  <ul className="space-y-1 text-xs text-on-surface-variant">
                    {need.requirements.map((r, idx) => (
                      <li key={idx} className="flex items-start gap-1.5">
                        <span className="text-cyan-400">•</span>
                        <span>{r}</span>
                      </li>
                    ))}
                  </ul>
                </div>
                <div className="p-3 rounded-xl bg-surface-container border border-outline/50 text-xs space-y-1">
                  <span className="font-semibold text-primary block text-[11px] uppercase">Minimum Quality Threshold:</span>
                  <p className="text-on-surface">{need.minimum_quality}</p>
                </div>
                <div className="text-[11px] text-on-surface-variant">
                  <strong>Accepted Formats:</strong> {need.accepted_formats.join(" • ")}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* 3. Why The Next Stage Is Locked */}
      <div className="bg-surface-container border border-outline rounded-3xl p-6 md:p-8 space-y-6">
        <div className="border-b border-outline pb-4">
          <h3 className="text-xl font-bold text-on-surface flex items-center gap-2">
            <Lock className="w-5 h-5 text-amber-400" /> Why Downstream Stages Are Locked
          </h3>
          <p className="text-xs text-on-surface-variant mt-0.5">
            Server-side progression gating: courses or checkboxes cannot unlock stages without satisfying defined evidence standards.
          </p>
        </div>

        {dashboard.locked_stages.length === 0 ? (
          <div className="p-8 text-center rounded-2xl bg-surface border border-outline text-xs text-emerald-300">
            All roadmap stages unlocked! You have satisfied all prerequisite evidence gates.
          </div>
        ) : (
          <div className="space-y-4">
            {dashboard.locked_stages.map((stg, i) => (
              <div key={i} className="p-5 rounded-2xl bg-surface border border-outline flex flex-col md:flex-row md:items-center justify-between gap-4">
                <div className="space-y-1.5 flex-1">
                  <div className="flex items-center gap-2">
                    <span className="text-xs font-bold text-amber-400">Stage 0{stg.stage_number}</span>
                    <span className="text-xs font-bold text-on-surface">{stg.title}</span>
                  </div>
                  <p className="text-xs text-rose-300">
                    Locked by: <strong>{stg.prerequisite_title}</strong>
                  </p>
                  <div className="flex flex-wrap gap-1.5 pt-1">
                    {stg.missing_capabilities.map((c, idx) => (
                      <span key={idx} className="text-[10px] px-2 py-0.5 rounded-md bg-rose-950/50 text-rose-300 border border-rose-700/40">
                        Missing: {c}
                      </span>
                    ))}
                  </div>
                </div>

                <div className="p-3.5 rounded-xl bg-surface-container border border-outline text-xs max-w-sm">
                  <span className="font-semibold text-primary block text-[11px] uppercase">Unlock Rule</span>
                  <p className="text-on-surface-variant text-[11px] mt-0.5">{stg.unlock_rule}</p>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* 4. Sequential Evaluation Attempt History & Dispute Flow */}
      <div className="bg-surface-container border border-outline rounded-3xl p-6 md:p-8 space-y-6">
        <div className="flex items-center justify-between border-b border-outline pb-4">
          <div>
            <h3 className="text-xl font-bold text-on-surface flex items-center gap-2">
              <Clock className="w-5 h-5 text-primary" /> Evaluation History &amp; Evidence Audit
            </h3>
            <p className="text-xs text-on-surface-variant mt-0.5">
              Historical record of every submission attempt with explicit separation of observations, inferences, and recommendations.
            </p>
          </div>
        </div>

        {dashboard.recent_evaluations.length === 0 ? (
          <div className="p-8 text-center rounded-2xl bg-surface border border-outline text-xs text-on-surface-variant">
            No evaluation attempts recorded yet.
          </div>
        ) : (
          <div className="space-y-4">
            {dashboard.recent_evaluations.map((att, i) => (
              <div key={i} className="p-6 rounded-3xl bg-surface border border-outline space-y-4 shadow-sm">
                <div className="flex flex-col md:flex-row md:items-center justify-between gap-2 border-b border-outline/50 pb-3">
                  <div className="flex items-center gap-3">
                    <span className="text-xs px-3 py-1 rounded-full font-bold bg-primary/20 text-primary border border-primary/30">
                      Attempt #{att.attempt_number}
                    </span>
                    <span className={`text-xs px-3 py-1 rounded-full font-bold uppercase tracking-wider ${
                      att.status === "PASS" ? "bg-emerald-950/60 text-emerald-300 border border-emerald-600/60" : "bg-amber-950/60 text-amber-300 border border-amber-600/60"
                    }`}>
                      {att.status}
                    </span>
                  </div>
                  <div className="flex items-center gap-3 text-xs">
                    <span className="text-on-surface-variant">{new Date(att.evaluated_at).toLocaleString()}</span>
                    <button
                      onClick={() => handleOpenDispute(att.attempt_id)}
                      className="text-primary hover:underline font-semibold flex items-center gap-1 cursor-pointer"
                    >
                      <MessageSquare className="w-3.5 h-3.5" /> Challenge / Dispute
                    </button>
                  </div>
                </div>

                {/* Structured Observations Grid */}
                <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-xs">
                  <div className="p-4 rounded-2xl bg-surface-container border border-outline/60 space-y-1.5">
                    <span className="font-bold text-emerald-400 uppercase tracking-wider text-[11px] block">Observed Facts</span>
                    <ul className="space-y-1 text-on-surface-variant">
                      {att.evaluation_detail.observed.map((o, idx) => (
                        <li key={idx} className="flex items-start gap-1.5">
                          <span className="text-emerald-400">•</span>
                          <span>{o}</span>
                        </li>
                      ))}
                    </ul>
                  </div>

                  <div className="p-4 rounded-2xl bg-surface-container border border-outline/60 space-y-1.5">
                    <span className="font-bold text-primary uppercase tracking-wider text-[11px] block">Inferred Insights</span>
                    <ul className="space-y-1 text-on-surface-variant">
                      {att.evaluation_detail.inferred.map((inf, idx) => (
                        <li key={idx} className="flex items-start gap-1.5">
                          <span className="text-primary">•</span>
                          <span>{inf}</span>
                        </li>
                      ))}
                    </ul>
                  </div>

                  <div className="p-4 rounded-2xl bg-surface-container border border-outline/60 space-y-1.5">
                    <span className="font-bold text-cyan-400 uppercase tracking-wider text-[11px] block">Target Recommendations</span>
                    <ul className="space-y-1 text-on-surface-variant">
                      {att.evaluation_detail.recommendation.map((r, idx) => (
                        <li key={idx} className="flex items-start gap-1.5">
                          <span className="text-cyan-400">•</span>
                          <span>{r}</span>
                        </li>
                      ))}
                    </ul>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Dispute Modal */}
      {disputeModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm animate-in fade-in">
          <div className="bg-surface border border-outline rounded-3xl p-6 md:p-8 max-w-lg w-full space-y-6 shadow-2xl">
            <div className="space-y-1">
              <span className="text-xs font-bold uppercase tracking-wider text-primary flex items-center gap-1.5">
                <HelpCircle className="w-4 h-4" /> Person-Controlled Correction
              </span>
              <h3 className="text-xl font-bold text-on-surface">Challenge Evaluation Result</h3>
              <p className="text-xs text-on-surface-variant">
                If an automated evaluation failed to detect an external fixture or custom implementation, provide your rationale and supplementary evidence link. Both states will be preserved in history.
              </p>
            </div>

            <div className="space-y-4 text-xs">
              <div className="space-y-1.5">
                <label className="font-bold uppercase tracking-wider text-on-surface">Dispute Rationale / Explanation</label>
                <textarea
                  value={disputeReason}
                  onChange={(e) => setDisputeReason(e.target.value)}
                  placeholder="Explain why the evaluation should be reassessed (e.g. fixtures were placed in conftest.py)..."
                  rows={4}
                  className="w-full bg-surface-container border border-outline rounded-2xl p-3 text-on-surface focus:outline-none focus:ring-2 focus:ring-primary"
                />
              </div>

              <div className="space-y-1.5">
                <label className="font-bold uppercase tracking-wider text-on-surface">Additional Artifact / Repository Link (Optional)</label>
                <input
                  type="text"
                  value={disputeRef}
                  onChange={(e) => setDisputeRef(e.target.value)}
                  placeholder="https://github.com/user/repo/blob/main/conftest.py"
                  className="w-full bg-surface-container border border-outline rounded-xl p-3 text-on-surface focus:outline-none focus:ring-2 focus:ring-primary"
                />
              </div>
            </div>

            <div className="flex items-center justify-end gap-3 pt-2">
              <button
                onClick={() => setDisputeModalOpen(false)}
                className="px-4 py-2.5 rounded-xl font-semibold text-xs bg-surface border border-outline text-on-surface hover:bg-surface-container cursor-pointer"
              >
                Cancel
              </button>
              <button
                onClick={handleSubmitDispute}
                disabled={isSubmittingDispute || !disputeReason.trim()}
                className="px-5 py-2.5 rounded-xl font-bold text-xs bg-primary text-on-primary shadow-md hover:opacity-95 disabled:opacity-50 cursor-pointer"
              >
                {isSubmittingDispute ? "Submitting..." : "Submit Dispute"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
