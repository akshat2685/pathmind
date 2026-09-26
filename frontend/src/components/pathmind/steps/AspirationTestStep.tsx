"use client";

import { motion } from "framer-motion";
import { useEffect, useState } from "react";
import { authedFetch } from "@/lib/api";

export interface TestQuestion {
  id: string;
  type: "mcq" | "short" | "self_assess";
  question: string;
  options?: string[];
  points: number;
  skill_tag: string;
  tier?: "VERIFIED" | "EXPERT_REVIEWED" | "AI_DRAFT";
  source_name?: string;
}

export interface TestProvenance {
  test_tier: "VERIFIED" | "EXPERT_REVIEWED" | "AI_DRAFT";
  total: number;
  verified_count: number;
  expert_reviewed_count: number;
  sources: string[];
  label: string;
}

export interface TestEvaluation {
  result_id: string;
  test_id: string;
  aspiration?: string;
  score: number;
  max_score: number;
  scored_max: number;
  percentage: number;
  skill_breakdown: Record<
    string,
    { earned: number; max: number; percentage: number | null; avg_self_rating: number | null }
  >;
  strengths: string[];
  gaps: string[];
  recommended_focus: string[];
  short_answers_pending_review: boolean;
}

interface AspirationTestStepProps {
  onNext: (result: TestEvaluation) => void;
  onBack: () => void;
  aspiration?: string;
  stage?: string;
  userType?: string;
  verificationData?: Record<string, unknown>;
}

type Phase = "loading" | "testing" | "submitting" | "results" | "error";

function readStored(key: string): string | null {
  if (typeof window === "undefined") return null;
  try {
    return localStorage.getItem(key);
  } catch {
    return null;
  }
}

export function AspirationTestStep({
  onNext,
  onBack,
  aspiration: aspirationProp,
  stage: stageProp,
  userType: userTypeProp,
  verificationData: verificationDataProp,
}: AspirationTestStepProps) {
  const [phase, setPhase] = useState<Phase>("loading");
  const [error, setError] = useState<string>("");
  const [testId, setTestId] = useState<string>("");
  const [aspiration, setAspiration] = useState<string>("");
  const [questions, setQuestions] = useState<TestQuestion[]>([]);
  const [timeSuggestion, setTimeSuggestion] = useState<number | null>(null);
  const [qIndex, setQIndex] = useState(0);
  const [answers, setAnswers] = useState<Record<string, number | string>>({});
  const [evaluation, setEvaluation] = useState<TestEvaluation | null>(null);
  const [provenance, setProvenance] = useState<TestProvenance | null>(null);

  // ---- load or generate the test on mount ----
  useEffect(() => {
    let cancelled = false;
    async function init() {
      setPhase("loading");
      setError("");
      try {
        // 1. Resume a pending test, or show results if already submitted.
        const cur = await authedFetch("/api/test/current");
        if (cur.ok) {
          const data = await cur.json();
          if (cancelled) return;
          setTestId(data.test_id);
          setAspiration(data.aspiration || "");
          setQuestions(data.questions || []);
          setTimeSuggestion(data.time_suggestion_minutes ?? null);
          if (data.submitted && data.evaluation) {
            setEvaluation(data.evaluation as TestEvaluation);
            setPhase("results");
          } else {
            setPhase("testing");
          }
          return;
        }
        if (cur.status !== 404) {
          const err = await cur.json().catch(() => ({}));
          throw new Error(err.detail || "Could not load your test.");
        }

        // 2. No test yet — generate one from aspiration + verification context.
        const aspiration =
          aspirationProp || readStored("pathmind_aspiration") || "";
        const stage = stageProp || readStored("pathmind_stage") || "";
        const userType = userTypeProp || readStored("pathmind_user_type") || "";
        let verificationData: Record<string, unknown> | undefined = verificationDataProp;
        if (!verificationData) {
          const raw = readStored("pathmind_verification_data");
          if (raw) {
            try {
              verificationData = JSON.parse(raw) as Record<string, unknown>;
            } catch {
              verificationData = undefined;
            }
          }
        }
        if (!aspiration.trim()) {
          throw new Error(
            "Your aspiration is missing. Please go back and complete the earlier steps."
          );
        }
        const gen = await authedFetch("/api/test/generate", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            aspiration: aspiration.trim(),
            stage,
            user_type: userType,
            verification_data: verificationData,
          }),
        });
        if (!gen.ok) {
          const err = await gen.json().catch(() => ({}));
          throw new Error(
            err.detail ||
              (gen.status === 503
                ? "Test generation is temporarily unavailable. Please try again in a few minutes."
                : "Could not generate your test.")
          );
        }
        const data = await gen.json();
        if (cancelled) return;
        setTestId(data.test_id);
        setAspiration(data.aspiration || aspiration);
        setQuestions(data.questions || []);
        setTimeSuggestion(data.time_suggestion_minutes ?? null);
        if (data.provenance) setProvenance(data.provenance as TestProvenance);
        setPhase("testing");
      } catch (e) {
        if (cancelled) return;
        setError(e instanceof Error ? e.message : "Something went wrong.");
        setPhase("error");
      }
    }
    init();
    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const current = questions[qIndex];
  const total = questions.length;

  function setAnswer(qid: string, value: number | string) {
    setAnswers((prev) => ({ ...prev, [qid]: value }));
  }

  function isAnswered(q: TestQuestion): boolean {
    const a = answers[q.id];
    if (a === undefined || a === null) return false;
    if (q.type === "short") return String(a).trim().length > 0;
    return true;
  }

  async function submitTest() {
    setPhase("submitting");
    setError("");
    try {
      const res = await authedFetch(`/api/test/${testId}/submit`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          answers: questions.map((q) => ({
            question_id: q.id,
            answer: answers[q.id] ?? null,
          })),
        }),
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail || "Could not evaluate your test.");
      }
      const data = (await res.json()) as TestEvaluation;
      setEvaluation(data);
      setPhase("results");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Submission failed.");
      setPhase("error");
    }
  }

  function retry() {
    setPhase("loading");
    setError("");
    // simplest honest retry: reload the step state
    window.location.reload();
  }

  return (
    <motion.div
      initial={{ opacity: 0, x: 20 }}
      animate={{ opacity: 1, x: 0 }}
      exit={{ opacity: 0, x: -20 }}
      transition={{ duration: 0.4 }}
      className="max-w-2xl mx-auto px-4 py-8"
    >
      <div className="mb-8 text-center">
        <span className="font-note-handwritten text-xl text-tertiary sketchy-chip px-3 py-1 mb-2 inline-block">
          Aptitude Calibration
        </span>
        <h2 className="font-headline-lg text-3xl sm:text-4xl text-on-surface mb-2">
          Prove your starting line
        </h2>
        <p className="font-body-md text-on-surface-variant max-w-md mx-auto">
          {aspiration
            ? `A short diagnostic tuned for "${aspiration}" — it shapes your personal path, not your worth.`
            : "A short diagnostic tuned for your aspiration."}
        </p>
      </div>

      {/* ---------- loading ---------- */}
      {phase === "loading" && (
        <div className="sketch-border p-10 bg-surface-container-low/90 text-center space-y-4">
          <span className="material-symbols-outlined text-4xl text-secondary animate-pulse">
            psychology
          </span>
          <p className="font-body-md text-on-surface-variant">
            Designing your test around your aspiration and background…
          </p>
        </div>
      )}

      {/* ---------- error ---------- */}
      {phase === "error" && (
        <div className="sketch-border p-8 bg-surface-container-low/90 text-center space-y-4">
          <span className="material-symbols-outlined text-4xl text-error">
            error_outline
          </span>
          <p className="font-body-md text-on-surface">{error}</p>
          <div className="flex justify-center gap-3 pt-2">
            <button
              type="button"
              onClick={onBack}
              className="ink-wash-btn px-6 py-2 text-xl cursor-pointer"
            >
              Back
            </button>
            <button
              type="button"
              onClick={retry}
              className="ink-wash-btn-primary px-6 py-2 text-xl cursor-pointer flex items-center gap-2"
            >
              <span className="material-symbols-outlined text-sm">refresh</span>
              <span>Try again</span>
            </button>
          </div>
        </div>
      )}

      {/* ---------- provenance banner ---------- */}
      {provenance && (phase === "testing" || phase === "submitting") && (
        <div
          className={
            "sketch-border p-4 flex items-start gap-3 " +
            (provenance.test_tier === "VERIFIED"
              ? "bg-emerald-500/10 border-emerald-500/30"
              : provenance.test_tier === "EXPERT_REVIEWED"
                ? "bg-sky-500/10 border-sky-500/30"
                : "bg-amber-500/10 border-amber-500/30")
          }
        >
          <span className="material-symbols-outlined text-xl mt-0.5">
            {provenance.test_tier === "VERIFIED"
              ? "verified"
              : provenance.test_tier === "EXPERT_REVIEWED"
                ? "rate_review"
                : "science"}
          </span>
          <p className="font-body-sm text-on-surface">{provenance.label}</p>
        </div>
      )}

      {/* ---------- testing ---------- */}
      {(phase === "testing" || phase === "submitting") && current && (
        <div className="space-y-6">
          {/* progress */}
          <div className="space-y-2">
            <div className="flex justify-between items-center text-xs font-label-md text-on-surface-variant">
              <span>
                Question {qIndex + 1} of {total}
              </span>
              {timeSuggestion && (
                <span className="flex items-center gap-1">
                  <span className="material-symbols-outlined text-sm">timer</span>
                  ~{timeSuggestion} min suggested
                </span>
              )}
            </div>
            <div className="h-2 rounded bg-surface-container-high/60 overflow-hidden">
              <div
                className="h-full bg-secondary transition-all duration-300"
                style={{ width: `${((qIndex + 1) / total) * 100}%` }}
              />
            </div>
          </div>

          {/* question card */}
          <div className="sketch-border p-6 bg-surface-container-low/90 space-y-5">
            <div className="flex items-start gap-3">
              <span className="font-note-handwritten text-lg text-tertiary shrink-0">
                {String(qIndex + 1).padStart(2, "0")}
              </span>
              <div className="space-y-1">
                <p className="font-body-md text-lg text-on-surface leading-relaxed">
                  {current.question}
                </p>
                <p className="text-[11px] font-label-md text-on-surface-variant/70 uppercase tracking-wide">
                  {current.skill_tag.replace(/-/g, " ")} · {current.points} pts
                  {current.type === "self_assess" ? " · not scored" : ""}
                </p>
                {current.tier && current.tier !== "AI_DRAFT" && (
                  <span
                    className={
                      "inline-flex items-center gap-1 text-[11px] font-label-md px-2 py-0.5 rounded-full border " +
                      (current.tier === "VERIFIED"
                        ? "text-emerald-600 border-emerald-500/40 bg-emerald-500/10"
                        : "text-sky-600 border-sky-500/40 bg-sky-500/10")
                    }
                    title={
                      current.tier === "VERIFIED"
                        ? `Verified question from ${current.source_name || "an official source"}`
                        : `Expert-reviewed question${current.source_name ? ` — ${current.source_name}` : ""}`
                    }
                  >
                    <span className="material-symbols-outlined text-[13px]">
                      {current.tier === "VERIFIED" ? "verified" : "rate_review"}
                    </span>
                    {current.tier === "VERIFIED" ? "Verified" : "Expert-reviewed"}
                  </span>
                )}
              </div>
            </div>

            {current.type === "mcq" && (
              <div className="space-y-2">
                {(current.options || []).map((opt, idx) => {
                  const selected = answers[current.id] === idx;
                  return (
                    <button
                      key={idx}
                      type="button"
                      onClick={() => setAnswer(current.id, idx)}
                      className={`w-full text-left p-3.5 flex items-start gap-3 sketch-border transition-all duration-150 cursor-pointer ${
                        selected
                          ? "bg-primary-fixed/40 border-primary shadow-sm"
                          : "bg-surface-container/60 hover:bg-surface-container-high/60 border-outline/20"
                      }`}
                    >
                      <span
                        className={`w-6 h-6 rounded-full border-2 flex items-center justify-center shrink-0 mt-0.5 text-xs font-bold ${
                          selected
                            ? "border-primary bg-primary text-white"
                            : "border-outline/50 text-on-surface-variant"
                        }`}
                      >
                        {String.fromCharCode(65 + idx)}
                      </span>
                      <span className="font-body-md text-sm text-on-surface leading-snug">
                        {opt}
                      </span>
                    </button>
                  );
                })}
              </div>
            )}

            {current.type === "short" && (
              <textarea
                value={String(answers[current.id] ?? "")}
                onChange={(e) => setAnswer(current.id, e.target.value)}
                placeholder="Write your answer in your own words…"
                rows={5}
                className="w-full bg-transparent hand-drawn-input resize-y focus:outline-none placeholder:text-outline/60 text-base leading-relaxed p-1"
              />
            )}

            {current.type === "self_assess" && (
              <div className="space-y-3">
                <div className="flex justify-between gap-2">
                  {[1, 2, 3, 4, 5].map((n) => {
                    const selected = answers[current.id] === n;
                    return (
                      <button
                        key={n}
                        type="button"
                        onClick={() => setAnswer(current.id, n)}
                        className={`flex-1 py-3 sketch-border font-headline-sm text-lg cursor-pointer transition-all ${
                          selected
                            ? "bg-primary-fixed/40 border-primary shadow-sm text-on-surface"
                            : "bg-surface-container/60 hover:bg-surface-container-high/60 border-outline/20 text-on-surface-variant"
                        }`}
                      >
                        {n}
                      </button>
                    );
                  })}
                </div>
                <div className="flex justify-between text-[11px] text-on-surface-variant/70">
                  <span>1 — just starting</span>
                  <span>5 — confident</span>
                </div>
              </div>
            )}
          </div>

          {/* nav */}
          <div className="flex justify-between items-center pt-2">
            <button
              type="button"
              onClick={() => (qIndex === 0 ? onBack() : setQIndex(qIndex - 1))}
              className="ink-wash-btn px-6 py-2 text-xl cursor-pointer"
            >
              Back
            </button>
            {qIndex < total - 1 ? (
              <button
                type="button"
                disabled={!isAnswered(current)}
                onClick={() => setQIndex(qIndex + 1)}
                className={`px-8 py-2.5 text-xl flex items-center gap-2 cursor-pointer ${
                  isAnswered(current)
                    ? "ink-wash-btn-primary"
                    : "opacity-40 cursor-not-allowed bg-surface-dim border-2 border-outline text-outline"
                }`}
              >
                <span>Next</span>
                <span className="material-symbols-outlined text-sm">east</span>
              </button>
            ) : (
              <button
                type="button"
                disabled={!isAnswered(current) || phase === "submitting"}
                onClick={submitTest}
                className={`px-8 py-2.5 text-xl flex items-center gap-2 cursor-pointer ${
                  isAnswered(current) && phase !== "submitting"
                    ? "ink-wash-btn-primary"
                    : "opacity-40 cursor-not-allowed bg-surface-dim border-2 border-outline text-outline"
                }`}
              >
                <span>{phase === "submitting" ? "Evaluating…" : "Submit test"}</span>
                <span className="material-symbols-outlined text-sm">send</span>
              </button>
            )}
          </div>
        </div>
      )}

      {/* ---------- results ---------- */}
      {phase === "results" && evaluation && (
        <div className="space-y-6">
          <div className="sketch-border p-8 bg-surface-container-low/90 text-center space-y-3">
            <span className="font-note-handwritten text-xl text-tertiary">
              Diagnostic complete
            </span>
            <div className="flex items-baseline justify-center gap-2">
              <span className="font-headline-lg text-6xl text-on-surface">
                {evaluation.percentage}%
              </span>
            </div>
            <p className="font-body-md text-on-surface-variant">
              {evaluation.score} of {evaluation.scored_max ?? evaluation.max_score} points
              scored
              {evaluation.short_answers_pending_review &&
                " · some written answers pending review"}
            </p>
            {evaluation.short_answers_pending_review && (
              <p className="text-xs text-on-surface-variant/80 italic flex items-center justify-center gap-1">
                <span className="material-symbols-outlined text-sm">hourglass_top</span>
                Written answers couldn't be auto-scored right now — they'll be
                reviewed and your profile will refine.
              </p>
            )}
          </div>

          {evaluation.strengths.length > 0 && (
            <div className="sketch-border p-5 bg-surface-container-low/70 space-y-2">
              <p className="font-headline-sm text-sm text-secondary flex items-center gap-2">
                <span className="material-symbols-outlined text-base">military_tech</span>
                Strengths
              </p>
              <div className="flex flex-wrap gap-2">
                {evaluation.strengths.map((s) => (
                  <span
                    key={s}
                    className="sketchy-chip px-3 py-1 text-xs font-label-md text-on-surface bg-surface-container/70"
                  >
                    {s.replace(/-/g, " ")}
                  </span>
                ))}
              </div>
            </div>
          )}

          {evaluation.gaps.length > 0 && (
            <div className="sketch-border p-5 bg-surface-container-low/70 space-y-2">
              <p className="font-headline-sm text-sm text-tertiary flex items-center gap-2">
                <span className="material-symbols-outlined text-base">target</span>
                Gaps to close
              </p>
              <div className="flex flex-wrap gap-2">
                {evaluation.gaps.map((g) => (
                  <span
                    key={g}
                    className="sketchy-chip px-3 py-1 text-xs font-label-md text-on-surface bg-surface-container/70"
                  >
                    {g.replace(/-/g, " ")}
                  </span>
                ))}
              </div>
            </div>
          )}

          <div className="sketch-border p-5 bg-surface-container-low/70 space-y-2">
            <p className="font-headline-sm text-sm text-on-surface flex items-center gap-2">
              <span className="material-symbols-outlined text-base">route</span>
              Recommended focus
            </p>
            <ul className="space-y-1.5">
              {evaluation.recommended_focus.map((f, i) => (
                <li
                  key={i}
                  className="font-body-md text-sm text-on-surface-variant leading-snug flex gap-2"
                >
                  <span className="text-secondary shrink-0">→</span>
                  <span>{f}</span>
                </li>
              ))}
            </ul>
          </div>

          <div className="flex justify-between items-center pt-4 border-t border-outline-variant/40">
            <button
              type="button"
              onClick={onBack}
              className="ink-wash-btn px-6 py-2 text-xl cursor-pointer"
            >
              Back
            </button>
            <button
              type="button"
              onClick={() => onNext(evaluation)}
              className="ink-wash-btn-primary px-8 py-2.5 text-xl flex items-center gap-2 cursor-pointer"
            >
              <span>Build my path</span>
              <span className="material-symbols-outlined text-sm">east</span>
            </button>
          </div>
        </div>
      )}
    </motion.div>
  );
}
