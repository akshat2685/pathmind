"use client";

import { useState, useEffect, useCallback } from "react";
import {
  ShieldCheck,
  X,
  CheckCircle2,
  AlertCircle,
  ThumbsUp,
  ThumbsDown,
  Sparkles
} from "lucide-react";

interface TraceableClaimItem {
  claim_id: string;
  claim_text: string;
  claim_category: "FACT" | "USER_STATED" | "OBSERVATION" | "INFERENCE" | "UNKNOWN";
  provenance?: {
    provider: string;
    source_type: string;
    source_url?: string;
    verification_status: string;
    confidence: string;
  } | null;
  supporting_evidence_ids: string[];
}

interface StructuredRecommendationItem {
  recommendation_id: string;
  person_id: string;
  type: string;
  title: string;
  summary: string;
  target_role: string;
  why_now: string;
  grounding_claims: TraceableClaimItem[];
  options: { name: string; pace?: string; proof?: string }[];
  tradeoffs: string[];
  uncertainties: string[];
  recommended_choice: string;
  alternative_choices: string[];
  status: string;
}

interface ExplanationItem {
  explanation_id: string;
  recommendation_id: string;
  why_this: string;
  why_not_alternative: string;
  facts_summary: string[];
  evidence_summary: string[];
  inference_summary: string[];
  unknowns_summary: string[];
  safety_disclaimer: string;
}

interface Props {
  recommendationId?: string;
  isOpen: boolean;
  onClose: () => void;
  onDecisionMade?: (choice: string) => void;
}

export function RecommendationDetailModal({
  recommendationId,
  isOpen,
  onClose,
  onDecisionMade
}: Props) {
  const [recommendation, setRecommendation] = useState<StructuredRecommendationItem | null>(null);
  const [explanation, setExplanation] = useState<ExplanationItem | null>(null);
  const [loading, setLoading] = useState(false);
  const [feedbackSubmitted, setFeedbackSubmitted] = useState(false);
  const [feedbackNote, setFeedbackNote] = useState("");

  const fetchDetail = useCallback(async () => {
    setLoading(true);
    try {
      const baseUrl = process.env.NEXT_PUBLIC_API_BASE_URL || "https://pathmind-api.onrender.com";
      const personId = typeof window !== "undefined"
        ? (localStorage.getItem("pathmind_user_name")?.toLowerCase().replace(/\s+/g, "-") || "scholar-user")
        : "scholar-user";

      // 1. Fetch recommendations list if ID not provided
      let recId = recommendationId;
      if (!recId) {
        const recsRes = await fetch(`${baseUrl}/api/trust/recommendations`, {
          headers: { "X-Person-ID": personId }
        });
        if (recsRes.ok) {
          const recs: StructuredRecommendationItem[] = await recsRes.json();
          if (recs.length > 0) {
            recId = recs[0].recommendation_id;
            setRecommendation(recs[0]);
          }
        }
      }

      if (recId) {
        const expRes = await fetch(`${baseUrl}/api/trust/recommendations/${recId}/explain`, {
          headers: { "X-Person-ID": personId }
        });
        if (expRes.ok) {
          const exp: ExplanationItem = await expRes.json();
          setExplanation(exp);
        }
      }
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  }, [recommendationId]);

  useEffect(() => {
    if (isOpen) {
      fetchDetail();
      setFeedbackSubmitted(false);
    }
  }, [isOpen, fetchDetail]);

  const handleDecision = async (choice: string) => {
    if (!recommendation) return;
    try {
      const baseUrl = process.env.NEXT_PUBLIC_API_BASE_URL || "https://pathmind-api.onrender.com";
      const personId = typeof window !== "undefined"
        ? (localStorage.getItem("pathmind_user_name")?.toLowerCase().replace(/\s+/g, "-") || "scholar-user")
        : "scholar-user";

      await fetch(`${baseUrl}/api/trust/recommendations/${recommendation.recommendation_id}/decide`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-Person-ID": personId
        },
        body: JSON.stringify({ user_choice: choice, notes: "Decision recorded by learner." })
      });

      if (onDecisionMade) onDecisionMade(choice);
      onClose();
    } catch (err) {
      console.error(err);
    }
  };

  const handleFeedback = async (feedbackType: string) => {
    if (!recommendation) return;
    try {
      const baseUrl = process.env.NEXT_PUBLIC_API_BASE_URL || "https://pathmind-api.onrender.com";
      const personId = typeof window !== "undefined"
        ? (localStorage.getItem("pathmind_user_name")?.toLowerCase().replace(/\s+/g, "-") || "scholar-user")
        : "scholar-user";

      await fetch(`${baseUrl}/api/trust/recommendations/${recommendation.recommendation_id}/feedback`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-Person-ID": personId
        },
        body: JSON.stringify({ feedback_type: feedbackType, notes: feedbackNote || null })
      });
      setFeedbackSubmitted(true);
    } catch (err) {
      console.error(err);
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm animate-in fade-in">
      <div className="bg-surface border border-outline rounded-3xl max-w-2xl w-full max-h-[90vh] flex flex-col shadow-2xl animate-in zoom-in-95 duration-200">
        {/* Header */}
        <div className="p-6 border-b border-outline flex items-center justify-between">
          <div className="flex items-center gap-2.5">
            <ShieldCheck className="w-5 h-5 text-primary" />
            <div>
              <span className="text-[10px] font-bold uppercase tracking-wider text-primary">Trust &amp; Explainability Layer</span>
              <h3 className="font-bold text-lg text-on-surface">Why Are We Recommending This?</h3>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-2 rounded-xl hover:bg-surface-container text-on-surface-variant cursor-pointer"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Content Body */}
        <div className="flex-1 overflow-y-auto p-6 space-y-6 text-xs">
          {loading ? (
            <div className="p-8 text-center text-on-surface-variant space-y-2">
              <Sparkles className="w-6 h-6 text-primary animate-spin mx-auto" />
              <p>Grounding rationale in occupational standards and verified evidence...</p>
            </div>
          ) : (
            <>
              {/* Target & Why This Choice */}
              {explanation && (
                <div className="p-5 rounded-3xl bg-surface-container border border-outline space-y-3">
                  <span className="text-[10px] uppercase font-bold text-primary block">1. Why This Recommendation?</span>
                  <p className="text-sm font-semibold text-on-surface leading-relaxed">{explanation.why_this}</p>
                </div>
              )}

              {/* Epistemic Breakdown Matrix */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {/* FACTS */}
                <div className="p-4 rounded-2xl bg-surface border border-emerald-500/30 space-y-2">
                  <span className="text-[10px] font-bold uppercase tracking-wider text-emerald-400 block flex items-center gap-1.5">
                    <CheckCircle2 className="w-3.5 h-3.5" /> Verified Facts (Standard Career Taxonomy: ESCO)
                  </span>
                  <ul className="space-y-1 text-[11px] text-on-surface-variant">
                    {explanation?.facts_summary.map((f, i) => (
                      <li key={i} className="flex items-start gap-1">
                        <span className="text-emerald-400">•</span>
                        <span>{f}</span>
                      </li>
                    )) || <li>Target role graph requires hands-on software development proof.</li>}
                  </ul>
                </div>

                {/* UNKNOWNS */}
                <div className="p-4 rounded-2xl bg-surface border border-amber-500/30 space-y-2">
                  <span className="text-[10px] font-bold uppercase tracking-wider text-amber-400 block flex items-center gap-1.5">
                    <AlertCircle className="w-3.5 h-3.5" /> What Remains Unknown
                  </span>
                  <ul className="space-y-1 text-[11px] text-on-surface-variant">
                    {explanation?.unknowns_summary.map((u, i) => (
                      <li key={i} className="flex items-start gap-1">
                        <span className="text-amber-400">•</span>
                        <span>{u}</span>
                      </li>
                    )) || <li>Concurrency throughput under heavy loads not yet verified.</li>}
                  </ul>
                </div>
              </div>

              {/* WHY NOT THE ALTERNATIVE? */}
              {explanation && (
                <div className="p-5 rounded-2xl bg-surface-container border border-outline space-y-2">
                  <span className="text-[10px] uppercase font-bold text-secondary block">2. Why Not Alternative Options?</span>
                  <p className="text-xs text-on-surface-variant leading-relaxed">{explanation.why_not_alternative}</p>
                </div>
              )}

              {/* USER AUTONOMY: Decision Controls */}
              <div className="p-5 rounded-2xl bg-gradient-to-br from-surface to-surface-container border border-primary/40 space-y-3">
                <span className="text-[10px] uppercase font-bold text-primary block">3. Your Autonomous Choice</span>
                <p className="text-[11px] text-on-surface-variant">
                  PATHMIND provides evidence-grounded guidance. You retain full control over which path you choose.
                </p>

                <div className="flex flex-wrap items-center gap-2.5 pt-1">
                  <button
                    onClick={() => handleDecision(recommendation?.recommended_choice || "Recommended Path")}
                    className="px-4 py-2 rounded-xl bg-primary text-on-primary font-bold text-xs shadow-md hover:opacity-95 cursor-pointer"
                  >
                    Accept Recommendation ({recommendation?.recommended_choice || "Primary Path"})
                  </button>

                  {recommendation?.alternative_choices.map((alt, i) => (
                    <button
                      key={i}
                      onClick={() => handleDecision(alt)}
                      className="px-3.5 py-2 rounded-xl border border-outline hover:bg-surface text-on-surface font-semibold text-xs cursor-pointer"
                    >
                      Choose {alt}
                    </button>
                  ))}

                  <button
                    onClick={() => handleDecision("DECLINED")}
                    className="px-3.5 py-2 rounded-xl text-on-surface-variant hover:text-on-surface font-medium text-xs cursor-pointer"
                  >
                    Decline / Defer
                  </button>
                </div>
              </div>

              {/* Feedback Section */}
              <div className="p-4 rounded-2xl bg-surface border border-outline space-y-2.5">
                <div className="flex items-center justify-between">
                  <span className="text-[11px] font-bold text-on-surface">Was this explanation helpful?</span>
                  {feedbackSubmitted ? (
                    <span className="text-[11px] text-emerald-400 font-bold">Thank you for your feedback!</span>
                  ) : (
                    <div className="flex items-center gap-2">
                      <button
                        onClick={() => handleFeedback("HELPFUL")}
                        className="p-1.5 rounded-lg border border-outline hover:bg-surface-container text-on-surface cursor-pointer"
                        title="Helpful"
                      >
                        <ThumbsUp className="w-3.5 h-3.5" />
                      </button>
                      <button
                        onClick={() => handleFeedback("NOT_HELPFUL")}
                        className="p-1.5 rounded-lg border border-outline hover:bg-surface-container text-on-surface cursor-pointer"
                        title="Not Helpful"
                      >
                        <ThumbsDown className="w-3.5 h-3.5" />
                      </button>
                    </div>
                  )}
                </div>
                {!feedbackSubmitted && (
                  <input
                    type="text"
                    value={feedbackNote}
                    onChange={(e) => setFeedbackNote(e.target.value)}
                    placeholder="Optional feedback notes or missing context..."
                    className="w-full bg-surface-container border border-outline rounded-xl p-2 text-[11px] text-on-surface focus:outline-none focus:ring-1 focus:ring-primary"
                  />
                )}
              </div>

              {/* Disclaimer */}
              {explanation?.safety_disclaimer && (
                <p className="text-[10px] text-on-surface-variant/70 italic text-center">
                  {explanation.safety_disclaimer}
                </p>
              )}
            </>
          )}
        </div>
      </div>
    </div>
  );
}
