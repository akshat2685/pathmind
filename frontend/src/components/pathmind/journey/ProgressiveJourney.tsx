"use client";

import { useState, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import Link from "next/link";

interface ResourceItem {
  title: string;
  url: string;
  resource_type: string;
  estimated_duration: string;
  provenance: string;
  is_free: boolean;
}

interface MissionItem {
  mission_id: string;
  stage_id: string;
  objective: string;
  why: string;
  estimated_time: string;
  steps: string[];
  resources: ResourceItem[];
  evidence_requirements: string[];
  completion_criteria: string;
  status: "ACTIVE" | "COMPLETED" | "PENDING" | "REINFORCING" | string;
}

interface DisclosedStageItem {
  stage_id: string;
  phase_id: string;
  stage_number: number;
  title: string;
  objective: string;
  skills: string[];
  estimated_effort: string;
  locked: boolean;
  status: "LOCKED" | "ACTIVE" | "COMPLETED" | "REINFORCEMENT" | string;
  current_mission?: MissionItem | null;
  resources?: ResourceItem[];
  evidence_requirements?: string[];
}

interface MasteryDimensionsItem {
  understanding: number;
  application: number;
  transfer: number;
  accuracy: number;
  explanation: number;
}

interface EvaluationResultItem {
  submission_id: string;
  stage_id: string;
  mission_id?: string;
  status: "PASS" | "REINFORCE" | "INSUFFICIENT_EVIDENCE" | string;
  mastery_dimensions: MasteryDimensionsItem;
  demonstrated: string[];
  missing: string[];
  feedback: string;
  recommended_next_action: string;
  confidence: string;
  evaluated_at: string;
}

interface DisclosedRoadmapData {
  roadmap_id: string;
  person_id: string;
  path_id: string;
  version: number;
  target_outcome: string;
  current_stage_id: string;
  total_stages: number;
  completed_stages: number;
  overall_progress_percent: number;
  stages: DisclosedStageItem[];
  active_stage?: DisclosedStageItem | null;
  active_mission?: MissionItem | null;
  personal_agent_note?: string;
  memory_moment?: {
    related_concept: string;
    context: string;
    stage_learned: string;
    connection_statement: string;
  } | null;
}

export function ProgressiveJourney() {
  const [roadmap, setRoadmap] = useState<DisclosedRoadmapData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Evidence submission state
  const [evidenceText, setEvidenceText] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [evalResult, setEvalResult] = useState<EvaluationResultItem | null>(null);
  const [unlockAnnounced, setUnlockAnnounced] = useState(false);

  // Step Checklist state
  const [completedSteps, setCompletedSteps] = useState<Record<number, boolean>>({});

  // Constraint Adaptation Sandbox
  const [adaptOpen, setAdaptOpen] = useState(false);
  const [weeklyHours, setWeeklyHours] = useState(10);
  const [isAdapting, setIsAdapting] = useState(false);

  const fetchRoadmap = async () => {
    setLoading(true);
    setError(null);
    try {
      const baseUrl = process.env.NEXT_PUBLIC_API_BASE_URL || "https://pathmind-api.onrender.com";
      const personId = typeof window !== "undefined"
        ? (localStorage.getItem("pathmind_user_name")?.toLowerCase().replace(/\s+/g, "-") || "scholar-user")
        : "scholar-user";

      const res = await fetch(`${baseUrl}/api/roadmap/current`, {
        headers: {
          "X-Person-ID": personId
        }
      });

      if (!res.ok) {
        throw new Error("Failed to load active roadmap");
      }

      const data: DisclosedRoadmapData = await res.json();
      setRoadmap(data);
    } catch (err) {
      console.error(err);
      setError("Unable to connect to live roadmap engine. Please ensure backend is running.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchRoadmap();
  }, []);

  const handleToggleStep = (index: number) => {
    setCompletedSteps(prev => ({
      ...prev,
      [index]: !prev[index]
    }));
  };

  const handleSubmitEvidence = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!evidenceText.trim() || !roadmap) return;

    setIsSubmitting(true);
    try {
      const baseUrl = process.env.NEXT_PUBLIC_API_BASE_URL || "https://pathmind-api.onrender.com";
      const personId = typeof window !== "undefined"
        ? (localStorage.getItem("pathmind_user_name")?.toLowerCase().replace(/\s+/g, "-") || "scholar-user")
        : "scholar-user";

      const res = await fetch(`${baseUrl}/api/roadmap/evidence/submit`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-Person-ID": personId
        },
        body: JSON.stringify({
          person_id: personId,
          roadmap_id: roadmap.roadmap_id,
          stage_id: roadmap.current_stage_id,
          mission_id: roadmap.active_mission?.mission_id,
          evidence_type: "CODE_REPO",
          content_payload: {
            code: evidenceText.trim()
          }
        })
      });

      if (!res.ok) {
        const errData = await res.json().catch(() => ({}));
        throw new Error(errData.detail || "Evidence evaluation failed");
      }

      const result: EvaluationResultItem = await res.json();
      setEvalResult(result);

      if (result.status === "PASS") {
        setUnlockAnnounced(true);
        // Refresh roadmap to reflect newly unlocked stage
        await fetchRoadmap();
      } else {
        // Refresh to show reinforcement mission
        await fetchRoadmap();
      }
    } catch (err: unknown) {
      console.error(err);
      const message = err instanceof Error ? err.message : "Evidence submission failed";
      alert(message);
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleAdaptConstraints = async () => {
    if (!roadmap) return;
    setIsAdapting(true);
    try {
      const baseUrl = process.env.NEXT_PUBLIC_API_BASE_URL || "https://pathmind-api.onrender.com";
      const personId = typeof window !== "undefined"
        ? (localStorage.getItem("pathmind_user_name")?.toLowerCase().replace(/\s+/g, "-") || "scholar-user")
        : "scholar-user";

      const res = await fetch(`${baseUrl}/api/roadmap/adapt/constraints`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-Person-ID": personId
        },
        body: JSON.stringify({
          person_id: personId,
          weekly_hours: weeklyHours,
          notes: `Learner adjusted workload to ${weeklyHours} hrs/week`
        })
      });

      if (res.ok) {
        const data = await res.json();
        setRoadmap(data);
        setAdaptOpen(false);
      }
    } catch (err) {
      console.error(err);
    } finally {
      setIsAdapting(false);
    }
  };

  const activeMission = roadmap?.active_mission || roadmap?.active_stage?.current_mission;

  return (
    <div className="w-full max-w-5xl mx-auto px-4 py-8">
      {/* Header Banner */}
      <div className="text-center mb-8">
        <div className="inline-flex items-center gap-2 px-4 py-1.5 sketchy-chip text-primary mb-3 bg-surface-container-low">
          <span className="material-symbols-outlined text-lg" style={{ fontVariationSettings: "'FILL' 1" }}>
            map
          </span>
          <span className="font-note-handwritten text-xl font-medium">
            Chapter IV: Progressive Journey
          </span>
        </div>
        <h1 className="font-headline-lg text-4xl sm:text-5xl text-on-surface mb-2">
          {roadmap?.target_outcome || "Applied AI & Machine Learning Systems"}
        </h1>
        <p className="font-note-handwritten text-2xl text-on-surface-variant max-w-2xl mx-auto">
          One active mission at a time. Future milestones unlock upon verified evidence.
        </p>
      </div>

      {/* Progress & Constraint Bar */}
      {roadmap && (
        <div className="mb-8 p-5 sketch-border bg-surface-container-low/95 flex items-center justify-between flex-wrap gap-4">
          <div className="flex items-center gap-4">
            <div className="w-12 h-12 rounded-full border-2 border-primary bg-primary/10 flex items-center justify-center font-headline-lg text-lg text-primary">
              {Math.round(roadmap.overall_progress_percent)}%
            </div>
            <div>
              <span className="font-headline-sm text-base text-on-surface font-bold block">
                Roadmap Progress (Stage {roadmap.completed_stages + 1} of {roadmap.total_stages})
              </span>
              <span className="font-note-handwritten text-sm text-on-surface-variant">
                Version {roadmap.version} &bull; {roadmap.completed_stages} Completed &bull; {roadmap.total_stages - roadmap.completed_stages} Remaining
              </span>
            </div>
          </div>

          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={() => setAdaptOpen(!adaptOpen)}
              className="ink-wash-btn text-xs px-3 py-1.5 flex items-center gap-1.5 cursor-pointer"
            >
              <span className="material-symbols-outlined text-sm">tune</span>
              <span>Adjust Workload / Hours</span>
            </button>
          </div>
        </div>
      )}

      {/* Constraint Adaptation Drawer */}
      <AnimatePresence>
        {adaptOpen && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: "auto" }}
            exit={{ opacity: 0, height: 0 }}
            className="mb-8 p-5 sketch-border border-tertiary bg-tertiary-fixed/20"
          >
            <div className="flex items-center justify-between mb-3">
              <h3 className="font-headline-sm text-base text-on-surface font-bold">
                Adaptive Workload Calibration
              </h3>
              <button
                type="button"
                onClick={() => setAdaptOpen(false)}
                className="text-on-surface-variant hover:text-on-surface text-lg font-bold"
              >
                &times;
              </button>
            </div>
            <p className="font-body-md text-xs text-on-surface-variant mb-4">
              If your available schedule changes, the roadmap adapts milestone pacing without resetting your completed progress.
            </p>
            <div className="flex items-center gap-4 flex-wrap">
              <div className="flex items-center gap-2">
                <span className="font-note-handwritten text-base text-on-surface">Available Commitment:</span>
                <select
                  value={weeklyHours}
                  onChange={(e) => setWeeklyHours(Number(e.target.value))}
                  className="hand-drawn-input text-xs px-3 py-1.5 bg-surface-container"
                >
                  <option value={5}>5 Hours / Week (Extended Pacing)</option>
                  <option value={10}>10 Hours / Week (Standard Pacing)</option>
                  <option value={20}>20 Hours / Week (Accelerated Intensive)</option>
                </select>
              </div>
              <button
                type="button"
                onClick={handleAdaptConstraints}
                disabled={isAdapting}
                className="ink-wash-btn-primary text-xs px-4 py-1.5 cursor-pointer disabled:opacity-50"
              >
                {isAdapting ? "Recalibrating..." : "Apply Calibration"}
              </button>
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Cross-Stage Longitudinal Memory Moment */}
      {roadmap?.memory_moment && (
        <div className="mb-8 p-4 sketch-border border-secondary bg-secondary-fixed/30 flex items-start gap-3">
          <span className="material-symbols-outlined text-secondary text-2xl mt-0.5" style={{ fontVariationSettings: "'FILL' 1" }}>
            psychology
          </span>
          <div>
            <span className="font-label-md text-[10px] font-bold uppercase tracking-wider text-secondary block">
              Longitudinal Memory Bridge:
            </span>
            <p className="font-body-md text-xs text-on-surface font-medium mt-0.5">
              {roadmap.memory_moment.connection_statement}
            </p>
            <p className="font-note-handwritten text-xs text-on-surface-variant mt-1">
              Context: {roadmap.memory_moment.context}
            </p>
          </div>
        </div>
      )}

      {/* Unlock Success Announcement Banner */}
      {unlockAnnounced && (
        <motion.div
          initial={{ opacity: 0, scale: 0.95 }}
          animate={{ opacity: 1, scale: 1 }}
          className="mb-8 p-6 sketch-border border-primary bg-primary-fixed/40 flex items-center justify-between gap-4"
        >
          <div className="flex items-center gap-3">
            <span className="material-symbols-outlined text-primary text-3xl" style={{ fontVariationSettings: "'FILL' 1" }}>
              lock_open
            </span>
            <div>
              <h3 className="font-headline-sm text-lg font-bold text-on-surface">
                Stage Mastery Verified &bull; Next Milestone Unlocked!
              </h3>
              <p className="font-note-handwritten text-base text-on-surface-variant">
                Your evidence satisfied completion criteria. Progress has been permanently recorded.
              </p>
            </div>
          </div>
          <button
            type="button"
            onClick={() => setUnlockAnnounced(false)}
            className="ink-wash-btn text-xs px-3 py-1 cursor-pointer"
          >
            Dismiss
          </button>
        </motion.div>
      )}

      {loading && (
        <div className="text-center py-20 flex flex-col items-center">
          <span className="material-symbols-outlined text-4xl text-primary animate-spin mb-3">
            progress_activity
          </span>
          <h3 className="font-headline-sm text-xl text-on-surface">Loading Progressive Journey...</h3>
        </div>
      )}

      {error && !loading && (
        <div className="p-6 sketch-border border-amber-600 bg-amber-950/20 text-on-surface text-center mb-8">
          <p className="text-sm">{error}</p>
          <button
            type="button"
            onClick={fetchRoadmap}
            className="mt-3 ink-wash-btn-primary px-4 py-1 text-sm"
          >
            Retry Connection
          </button>
        </div>
      )}

      {!loading && roadmap && (
        <div className="grid lg:grid-cols-3 gap-8">
          {/* Left Column: Progressive Timeline Overview */}
          <div className="space-y-4">
            <h2 className="font-headline-sm text-lg text-on-surface flex items-center gap-2">
              <span className="material-symbols-outlined text-primary text-xl">route</span>
              <span>Milestone Stages</span>
            </h2>

            <div className="space-y-3">
              {roadmap.stages.map((stage) => {
                const isActive = stage.stage_id === roadmap.current_stage_id;
                const isCompleted = stage.status === "COMPLETED";
                const isReinforcing = stage.status === "REINFORCEMENT";

                return (
                  <div
                    key={stage.stage_id}
                    className={`sketch-border p-4 transition-all ${
                      isActive
                        ? "bg-surface-container-low/95 border-primary shadow-sm ring-1 ring-primary/30"
                        : isCompleted
                        ? "bg-surface-container-low/60 border-outline-variant/40 opacity-80"
                        : "bg-surface-container/30 border-outline-variant/20 opacity-60"
                    }`}
                  >
                    <div className="flex items-center justify-between mb-1">
                      <span className="text-[10px] font-bold uppercase tracking-wider font-label-md text-outline">
                        Stage 0{stage.stage_number}
                      </span>
                      <span className="flex items-center gap-1 text-xs">
                        {isCompleted && (
                          <span className="text-emerald-400 font-bold flex items-center gap-0.5">
                            <span className="material-symbols-outlined text-sm">check_circle</span>
                            <span>Done</span>
                          </span>
                        )}
                        {isActive && !isReinforcing && (
                          <span className="text-primary font-bold flex items-center gap-0.5">
                            <span className="material-symbols-outlined text-sm">bolt</span>
                            <span>Active</span>
                          </span>
                        )}
                        {isReinforcing && (
                          <span className="text-amber-400 font-bold flex items-center gap-0.5">
                            <span className="material-symbols-outlined text-sm">healing</span>
                            <span>Reinforce</span>
                          </span>
                        )}
                        {stage.locked && (
                          <span className="text-on-surface-variant flex items-center gap-0.5">
                            <span className="material-symbols-outlined text-sm">lock</span>
                            <span>Locked</span>
                          </span>
                        )}
                      </span>
                    </div>

                    <h3 className="font-headline-sm text-base font-bold text-on-surface mb-1">
                      {stage.title}
                    </h3>
                    <p className="font-body-md text-xs text-on-surface-variant leading-snug">
                      {stage.objective}
                    </p>

                    <div className="mt-2 pt-2 border-t border-outline-variant/20 flex items-center justify-between text-[11px] text-on-surface-variant font-note-handwritten">
                      <span>Effort: {stage.estimated_effort}</span>
                      <span>{stage.skills.slice(0, 2).join(", ")}</span>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>

          {/* Right 2 Columns: Active Mission & Evidence Submission */}
          <div className="lg:col-span-2 space-y-6">
            {/* Active Mission Card */}
            {activeMission && (
              <div className="sketch-border p-6 bg-surface-container-low/95">
                <div className="flex items-center justify-between gap-2 mb-3">
                  <span className="font-note-handwritten text-xs text-primary sketchy-chip px-2.5 py-0.5">
                    Primary Current Mission
                  </span>
                  <span className="font-note-handwritten text-sm text-on-surface-variant">
                    Estimated Time: {activeMission.estimated_time}
                  </span>
                </div>

                <h3 className="font-headline-sm text-2xl text-on-surface font-bold mb-2">
                  {activeMission.objective}
                </h3>
                
                <div className="mb-4 p-3 rounded bg-surface-container/60 border border-outline-variant/20 text-xs">
                  <span className="font-bold text-[10px] uppercase text-outline block mb-0.5">Why this matters:</span>
                  <p className="text-on-surface-variant font-body-md">{activeMission.why}</p>
                </div>

                {/* Steps Checklist */}
                {activeMission.steps && activeMission.steps.length > 0 && (
                  <div className="mb-5">
                    <h4 className="font-label-md text-xs font-bold uppercase tracking-wider text-outline mb-2">
                      Actionable Steps:
                    </h4>
                    <div className="space-y-2">
                      {activeMission.steps.map((step, idx) => (
                        <button
                          key={idx}
                          type="button"
                          onClick={() => handleToggleStep(idx)}
                          className="w-full text-left flex items-start gap-2.5 p-2 rounded hover:bg-surface-container/50 text-xs text-on-surface font-body-md transition-colors cursor-pointer"
                        >
                          <span className={`material-symbols-outlined text-base mt-0.5 ${completedSteps[idx] ? "text-primary" : "text-outline"}`}>
                            {completedSteps[idx] ? "check_box" : "check_box_outline_blank"}
                          </span>
                          <span className={completedSteps[idx] ? "line-through opacity-60" : ""}>{step}</span>
                        </button>
                      ))}
                    </div>
                  </div>
                )}

                {/* Curated Resources with Provenance */}
                {activeMission.resources && activeMission.resources.length > 0 && (
                  <div className="mb-6 pt-4 border-t border-outline-variant/20">
                    <h4 className="font-label-md text-xs font-bold uppercase tracking-wider text-outline mb-2">
                      Curated Verified Resources:
                    </h4>
                    <div className="space-y-2">
                      {activeMission.resources.map((res, idx) => (
                        <a
                          key={idx}
                          href={res.url}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="p-3 rounded bg-surface-container/60 border border-outline-variant/20 flex items-center justify-between hover:border-primary transition-colors block text-xs group"
                        >
                          <div>
                            <span className="font-headline-sm font-bold text-on-surface group-hover:text-primary transition-colors block">
                              {res.title}
                            </span>
                            <span className="text-[10px] text-on-surface-variant font-mono">
                              {res.resource_type} &bull; {res.estimated_duration} &bull; Source: {res.provenance}
                            </span>
                          </div>
                          <span className="material-symbols-outlined text-sm text-outline group-hover:text-primary transition-colors">
                            open_in_new
                          </span>
                        </a>
                      ))}
                    </div>
                  </div>
                )}

                {/* Evidence Submission Area */}
                <div className="pt-4 border-t border-outline-variant/30">
                  <h4 className="font-headline-sm text-lg text-on-surface font-bold mb-1">
                    Submit Mission Evidence
                  </h4>
                  <p className="font-note-handwritten text-sm text-on-surface-variant mb-3">
                    Paste your repository URL, code snippet, or unit test output for evaluation.
                  </p>

                  <form onSubmit={handleSubmitEvidence} className="space-y-3">
                    <textarea
                      value={evidenceText}
                      onChange={(e) => setEvidenceText(e.target.value)}
                      placeholder="e.g. GitHub Repository URL or Python code implementation..."
                      rows={4}
                      className="w-full hand-drawn-input text-xs p-3 font-mono bg-surface-container"
                    />

                    <div className="flex items-center justify-between flex-wrap gap-2">
                      <span className="text-[10px] text-on-surface-variant font-mono">
                        Rule: Evaluated by ADK EvidenceEvaluatorAgent
                      </span>
                      <button
                        type="submit"
                        disabled={!evidenceText.trim() || isSubmitting}
                        className="ink-wash-btn-primary px-6 py-2 text-sm flex items-center gap-2 cursor-pointer disabled:opacity-50"
                      >
                        <span>{isSubmitting ? "Evaluating..." : "Submit for Evaluation"}</span>
                        <span className="material-symbols-outlined text-sm">send</span>
                      </button>
                    </div>
                  </form>
                </div>
              </div>
            )}

            {/* Evaluation Result Feedback Card */}
            {evalResult && (
              <motion.div
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                className={`sketch-border p-6 ${
                  evalResult.status === "PASS"
                    ? "bg-emerald-950/20 border-emerald-600/70"
                    : "bg-amber-950/20 border-amber-600/70"
                }`}
              >
                <div className="flex items-center justify-between mb-3">
                  <div className="flex items-center gap-2">
                    <span className={`material-symbols-outlined text-2xl ${evalResult.status === "PASS" ? "text-emerald-400" : "text-amber-400"}`} style={{ fontVariationSettings: "'FILL' 1" }}>
                      {evalResult.status === "PASS" ? "verified" : "pending_actions"}
                    </span>
                    <h4 className="font-headline-sm text-lg font-bold text-on-surface">
                      Evaluation Result: {evalResult.status}
                    </h4>
                  </div>
                  <span className="text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 rounded border border-outline text-on-surface-variant">
                    {evalResult.confidence} Confidence
                  </span>
                </div>

                <p className="font-body-md text-xs text-on-surface leading-relaxed mb-4">
                  {evalResult.feedback}
                </p>

                {/* Multidimensional Mastery Breakdown */}
                <div className="mb-4 p-3 rounded bg-surface-container/60 border border-outline-variant/20">
                  <span className="font-bold text-[10px] uppercase text-outline block mb-2">Mastery Dimensions:</span>
                  <div className="grid grid-cols-3 sm:grid-cols-5 gap-2 text-center text-xs">
                    <div className="p-1.5 rounded bg-surface-container/50">
                      <span className="text-[10px] text-on-surface-variant block">Understanding</span>
                      <span className="font-bold text-on-surface">{Math.round(evalResult.mastery_dimensions.understanding)}%</span>
                    </div>
                    <div className="p-1.5 rounded bg-surface-container/50">
                      <span className="text-[10px] text-on-surface-variant block">Application</span>
                      <span className="font-bold text-on-surface">{Math.round(evalResult.mastery_dimensions.application)}%</span>
                    </div>
                    <div className="p-1.5 rounded bg-surface-container/50">
                      <span className="text-[10px] text-on-surface-variant block">Transfer</span>
                      <span className="font-bold text-on-surface">{Math.round(evalResult.mastery_dimensions.transfer)}%</span>
                    </div>
                    <div className="p-1.5 rounded bg-surface-container/50">
                      <span className="text-[10px] text-on-surface-variant block">Accuracy</span>
                      <span className="font-bold text-on-surface">{Math.round(evalResult.mastery_dimensions.accuracy)}%</span>
                    </div>
                    <div className="p-1.5 rounded bg-surface-container/50">
                      <span className="text-[10px] text-on-surface-variant block">Explanation</span>
                      <span className="font-bold text-on-surface">{Math.round(evalResult.mastery_dimensions.explanation)}%</span>
                    </div>
                  </div>
                </div>

                {evalResult.demonstrated && evalResult.demonstrated.length > 0 && (
                  <div className="mb-2 text-xs">
                    <span className="font-bold text-[10px] uppercase text-emerald-400 block mb-1">Demonstrated:</span>
                    <ul className="space-y-1 text-on-surface-variant">
                      {evalResult.demonstrated.map((d, i) => (
                        <li key={i} className="flex items-start gap-1">
                          <span className="text-emerald-400 font-bold">&check;</span>
                          <span>{d}</span>
                        </li>
                      ))}
                    </ul>
                  </div>
                )}

                {evalResult.missing && evalResult.missing.length > 0 && (
                  <div className="mb-3 text-xs">
                    <span className="font-bold text-[10px] uppercase text-amber-400 block mb-1">Needs Work:</span>
                    <ul className="space-y-1 text-on-surface-variant">
                      {evalResult.missing.map((m, i) => (
                        <li key={i} className="flex items-start gap-1">
                          <span className="text-amber-400 font-bold">&bull;</span>
                          <span>{m}</span>
                        </li>
                      ))}
                    </ul>
                  </div>
                )}

                <div className="pt-2 border-t border-outline-variant/20 text-xs font-headline-sm text-secondary font-medium">
                  Next Step: {evalResult.recommended_next_action}
                </div>
              </motion.div>
            )}
          </div>
        </div>
      )}

      {/* Navigation Footer */}
      <div className="flex flex-wrap justify-center gap-4 mt-12 pt-6 border-t border-outline-variant/40">
        <Link
          href="/explorer"
          className="ink-wash-btn px-6 py-2 text-base flex items-center gap-2"
        >
          <span className="material-symbols-outlined text-sm">arrow_back</span>
          <span>Return to Career Explorer</span>
        </Link>
        <Link
          href="/"
          className="ink-wash-btn-primary px-8 py-2 text-base flex items-center gap-2"
        >
          <span className="material-symbols-outlined text-sm">home</span>
          <span>Home Overview</span>
        </Link>
      </div>
    </div>
  );
}
