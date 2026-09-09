"use client";

import { useState, useEffect, useCallback } from "react";
import { motion } from "framer-motion";
import {
  Sparkles,
  Clock,
  ShieldCheck,
  AlertTriangle,
  CheckCircle2,
  Lock,
  Compass,
  RefreshCw,
  GitBranch,
  Layers,
  ArrowRight,
  History,
  Check,
  X
} from "lucide-react";

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

interface ProposedAdaptationItem {
  adaptation_id: string;
  person_id: string;
  change_event: {
    title: string;
    change_type: string;
    description: string;
    trigger_data: Record<string, unknown>;
  };
  impact_analysis: {
    impact_level: string;
    what_changed: string;
    why: string;
    affected_roadmap_stages: string[];
    preserved_assets: string[];
    requires_user_approval: boolean;
    approval_type: string;
    next_action_recommendation: string;
  };
  previous_roadmap_version: number;
  proposed_roadmap_version: number;
  change_summary: string;
  rationale: string;
  status: string;
  changed_stages: Array<{
    stage_id: string;
    title: string;
    action: string;
    rationale: string;
  }>;
}

interface ContinuousIntelligenceStateData {
  person_id: string;
  active_target_role: string;
  current_roadmap_version: number;
  plan_stability_status: string;
  pending_adaptations: ProposedAdaptationItem[];
  pause_status: {
    elapsed_days: number;
    status: string;
    recommended_action: string;
    reassessment_rationale: string;
    suggested_refresher_concept?: string | null;
  };
  conflict_status: {
    has_conflict: boolean;
    self_report_claim?: string | null;
    observed_task_evidence?: string | null;
    explanation?: string | null;
    recommended_verification_task?: string | null;
  };
}

export function ProgressiveJourney() {
  const [roadmap, setRoadmap] = useState<DisclosedRoadmapData | null>(null);
  const [intelligenceState, setIntelligenceState] = useState<ContinuousIntelligenceStateData | null>(null);
  const [allVersions, setAllVersions] = useState<Array<{ version?: number; revision_reason?: string }>>([]);
  const [selectedVersionNum, setSelectedVersionNum] = useState<number | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Evidence submission state
  const [evidenceText, setEvidenceText] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [evalResult, setEvalResult] = useState<EvaluationResultItem | null>(null);
  const [completedSteps, setCompletedSteps] = useState<Record<number, boolean>>({});

  // Constraint Adaptation Modal
  const [adaptOpen, setAdaptOpen] = useState(false);
  const [weeklyHours, setWeeklyHours] = useState(10);
  const [isAdapting, setIsAdapting] = useState(false);

  // Goal Change Modal
  const [goalModalOpen, setGoalModalOpen] = useState(false);
  const [selectedGoal, setSelectedGoal] = useState("Robotics & Autonomous Systems Engineer");
  const [isChangingGoal, setIsChangingGoal] = useState(false);

  // Adaptation Decision Loading
  const [isDeciding, setIsDeciding] = useState(false);

  const fetchRoadmap = useCallback(async (versionNum?: number) => {
    setLoading(true);
    setError(null);
    try {
      const baseUrl = process.env.NEXT_PUBLIC_API_BASE_URL || "https://pathmind-api.onrender.com";
      const personId = typeof window !== "undefined"
        ? (localStorage.getItem("pathmind_user_name")?.toLowerCase().replace(/\s+/g, "-") || "scholar-user")
        : "scholar-user";

      const roadmapUrl = versionNum 
        ? `${baseUrl}/api/roadmap/version/${versionNum}`
        : `${baseUrl}/api/roadmap/current`;

      const [resRoadmap, resIntel, resVersions] = await Promise.all([
        fetch(roadmapUrl, { headers: { "X-Person-ID": personId } }),
        fetch(`${baseUrl}/api/adaptation/state`, { headers: { "X-Person-ID": personId } }),
        fetch(`${baseUrl}/api/roadmap/versions`, { headers: { "X-Person-ID": personId } })
      ]);

      if (!resRoadmap.ok) throw new Error("Failed to load roadmap");
      const data: DisclosedRoadmapData = await resRoadmap.json();
      setRoadmap(data);

      if (resIntel.ok) {
        const intelData: ContinuousIntelligenceStateData = await resIntel.json();
        setIntelligenceState(intelData);
      }

      if (resVersions.ok) {
        const verData = await resVersions.json();
        setAllVersions(verData);
      }
    } catch (err) {
      console.error(err);
      setError("Unable to connect to live roadmap engine. Please ensure backend services are reachable.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchRoadmap();
  }, [fetchRoadmap]);

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
        await fetchRoadmap();
      } else {
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

      const res = await fetch(`${baseUrl}/api/adaptation/constraint-change`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-Person-ID": personId
        },
        body: JSON.stringify({
          weekly_hours: weeklyHours,
          preferred_format: "project-based"
        })
      });

      if (res.ok) {
        setAdaptOpen(false);
        await fetchRoadmap();
      }
    } catch (err) {
      console.error(err);
    } finally {
      setIsAdapting(false);
    }
  };

  const handleGoalChangeSubmit = async () => {
    setIsChangingGoal(true);
    try {
      const baseUrl = process.env.NEXT_PUBLIC_API_BASE_URL || "https://pathmind-api.onrender.com";
      const personId = typeof window !== "undefined"
        ? (localStorage.getItem("pathmind_user_name")?.toLowerCase().replace(/\s+/g, "-") || "scholar-user")
        : "scholar-user";

      const res = await fetch(`${baseUrl}/api/adaptation/goal-change`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-Person-ID": personId
        },
        body: JSON.stringify({
          new_target_role: selectedGoal,
          target_industry: "Applied AI & Engineering",
          geography: "Global / India",
          target_timeline: "6–9 Months"
        })
      });

      if (res.ok) {
        setGoalModalOpen(false);
        await fetchRoadmap();
      }
    } catch (err) {
      console.error(err);
    } finally {
      setIsChangingGoal(false);
    }
  };

  const handleAdaptationDecision = async (adaptationId: string, action: "APPROVE" | "REJECT") => {
    setIsDeciding(true);
    try {
      const baseUrl = process.env.NEXT_PUBLIC_API_BASE_URL || "https://pathmind-api.onrender.com";
      const personId = typeof window !== "undefined"
        ? (localStorage.getItem("pathmind_user_name")?.toLowerCase().replace(/\s+/g, "-") || "scholar-user")
        : "scholar-user";

      const res = await fetch(`${baseUrl}/api/adaptation/decide`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-Person-ID": personId
        },
        body: JSON.stringify({
          adaptation_id: adaptationId,
          person_id: personId,
          action: action,
          user_feedback: action === "APPROVE" ? "Approved transition to new trajectory." : "Preserved existing roadmap."
        })
      });

      if (res.ok) {
        setSelectedVersionNum(null);
        await fetchRoadmap();
      }
    } catch (err) {
      console.error(err);
    } finally {
      setIsDeciding(false);
    }
  };

  const handleSelectVersion = (verNum: number) => {
    setSelectedVersionNum(verNum);
    fetchRoadmap(verNum);
  };

  if (loading && !roadmap) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[60vh] space-y-4">
        <RefreshCw className="w-8 h-8 text-primary animate-spin" />
        <p className="font-label-md text-on-surface-variant font-semibold">
          Synchronizing verified progressive roadmap &amp; adaptation intelligence...
        </p>
      </div>
    );
  }

  if (error || !roadmap) {
    return (
      <div className="max-w-2xl mx-auto p-8 rounded-3xl bg-surface-container border border-outline text-center space-y-4">
        <AlertTriangle className="w-8 h-8 text-amber-400 mx-auto" />
        <h3 className="font-headline-sm text-lg font-bold text-on-surface">Roadmap Engine Offline</h3>
        <p className="font-body-md text-xs text-on-surface-variant">{error || "Please verify backend server status."}</p>
        <button
          onClick={() => fetchRoadmap()}
          className="px-5 py-2.5 rounded-xl bg-primary text-on-primary text-xs font-bold shadow-md hover:opacity-95 cursor-pointer"
        >
          Retry Connection
        </button>
      </div>
    );
  }

  const activeStage = roadmap.active_stage || roadmap.stages.find(s => s.stage_id === roadmap.current_stage_id);
  const activeMission = roadmap.active_mission || activeStage?.current_mission;
  const pendingAdaptation = intelligenceState?.pending_adaptations?.[0];

  return (
    <div className="w-full max-w-7xl mx-auto space-y-8 animate-in fade-in duration-500">
      {/* 1. Header Banner & Plan Stability Controller */}
      <div className="relative rounded-3xl overflow-hidden p-8 md:p-12 border border-outline bg-gradient-to-br from-surface-container via-surface to-surface-container-high shadow-2xl">
        <div className="absolute top-0 right-0 w-96 h-96 bg-primary/10 rounded-full blur-3xl pointer-events-none -mr-20 -mt-20" />
        <div className="relative z-10 flex flex-col md:flex-row md:items-center justify-between gap-6">
          <div className="space-y-3">
            <div className="flex flex-wrap items-center gap-2">
              <span className="inline-flex items-center gap-1.5 px-3.5 py-1 rounded-full text-xs font-bold uppercase tracking-wider bg-primary/15 text-primary border border-primary/30">
                <GitBranch className="w-3.5 h-3.5" /> Roadmap Version {roadmap.version}
              </span>
              <span className="inline-flex items-center gap-1 px-3 py-1 rounded-full text-xs font-semibold bg-emerald-950/60 text-emerald-300 border border-emerald-600/60">
                <ShieldCheck className="w-3.5 h-3.5" /> Plan Stability: {intelligenceState?.plan_stability_status || "STABLE"}
              </span>
            </div>
            <h1 className="text-3xl md:text-5xl font-extrabold tracking-tight text-on-surface">
              {roadmap.target_outcome}
            </h1>
            <p className="text-on-surface-variant max-w-3xl text-sm md:text-base leading-relaxed">
              Progressive milestone roadmap with server-side prerequisite lock enforcement, evidence-based stage advancement, and continuous adaptation.
            </p>
          </div>

          {/* Action Buttons & Version Switcher */}
          <div className="flex flex-col gap-3 min-w-[240px]">
            <button
              onClick={() => setGoalModalOpen(true)}
              className="flex items-center justify-center gap-2 px-5 py-3 rounded-2xl text-xs md:text-sm font-bold bg-primary text-on-primary shadow-lg shadow-primary/20 hover:opacity-95 transition-all cursor-pointer"
            >
              <Compass className="w-4 h-4" /> Change Target Goal
            </button>

            <button
              onClick={() => setAdaptOpen(true)}
              className="flex items-center justify-center gap-2 px-5 py-2.5 rounded-2xl text-xs font-semibold bg-surface border border-outline hover:bg-surface-container text-on-surface transition-all cursor-pointer"
            >
              <Clock className="w-4 h-4 text-primary" /> Adjust Workload &amp; Hours
            </button>

            {/* Past Version Switcher */}
            {allVersions.length > 1 && (
              <div className="flex items-center justify-between text-xs p-2.5 rounded-xl bg-surface border border-outline/70">
                <span className="text-on-surface-variant font-medium flex items-center gap-1">
                  <History className="w-3.5 h-3.5 text-primary" /> Version:
                </span>
                <div className="flex gap-1">
                  {allVersions.map((v, i) => {
                    const verNum = v.version || i + 1;
                    const isSelected = selectedVersionNum ? selectedVersionNum === verNum : roadmap.version === verNum;
                    return (
                      <button
                        key={i}
                        onClick={() => handleSelectVersion(verNum)}
                        className={`px-2.5 py-1 rounded-lg font-bold text-xs transition-all cursor-pointer ${
                          isSelected ? "bg-primary text-on-primary" : "bg-surface-container text-on-surface-variant hover:text-on-surface"
                        }`}
                      >
                        v{verNum}
                      </button>
                    );
                  })}
                </div>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* 2. Pending Adaptation Review Card (Prompt 10 Causal Before/After View) */}
      {pendingAdaptation && (
        <motion.div
          initial={{ opacity: 0, y: -10 }}
          animate={{ opacity: 1, y: 0 }}
          className="p-6 md:p-8 rounded-3xl bg-amber-950/40 border border-amber-500/60 text-on-surface space-y-6 shadow-xl"
        >
          <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-amber-500/30 pb-4">
            <div className="space-y-1">
              <span className="text-xs px-3 py-1 rounded-full font-bold uppercase tracking-wider bg-amber-500/20 text-amber-300 border border-amber-500/40 inline-flex items-center gap-1.5">
                <AlertTriangle className="w-3.5 h-3.5" /> Adaptation Review Required
              </span>
              <h3 className="text-lg md:text-xl font-bold text-on-surface mt-1">
                {pendingAdaptation.change_event.title}
              </h3>
            </div>
            <div className="flex items-center gap-3">
              <button
                onClick={() => handleAdaptationDecision(pendingAdaptation.adaptation_id, "APPROVE")}
                disabled={isDeciding}
                className="flex items-center gap-1.5 px-5 py-2.5 rounded-xl font-bold text-xs bg-emerald-600 hover:bg-emerald-500 text-white shadow-md cursor-pointer transition-all"
              >
                <Check className="w-4 h-4" /> Approve &amp; Activate Version {pendingAdaptation.proposed_roadmap_version}
              </button>
              <button
                onClick={() => handleAdaptationDecision(pendingAdaptation.adaptation_id, "REJECT")}
                disabled={isDeciding}
                className="flex items-center gap-1.5 px-4 py-2.5 rounded-xl font-semibold text-xs bg-surface border border-outline hover:bg-surface-container text-on-surface cursor-pointer"
              >
                <X className="w-4 h-4" /> Keep Current Plan
              </button>
            </div>
          </div>

          {/* Causal Explainability Grid */}
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 text-xs">
            <div className="p-4 rounded-2xl bg-surface/70 border border-outline space-y-1.5">
              <span className="font-bold text-amber-300 uppercase tracking-wider text-[11px] block">What Changed?</span>
              <p className="text-on-surface leading-relaxed">{pendingAdaptation.impact_analysis.what_changed}</p>
            </div>

            <div className="p-4 rounded-2xl bg-surface/70 border border-outline space-y-1.5">
              <span className="font-bold text-primary uppercase tracking-wider text-[11px] block">Why? (Causal Rationale)</span>
              <p className="text-on-surface leading-relaxed">{pendingAdaptation.impact_analysis.why}</p>
            </div>

            <div className="p-4 rounded-2xl bg-surface/70 border border-outline space-y-1.5">
              <span className="font-bold text-emerald-300 uppercase tracking-wider text-[11px] block">What Stays The Same?</span>
              <p className="text-on-surface leading-relaxed">{pendingAdaptation.impact_analysis.preserved_assets.join(", ") || "Foundations preserved"}</p>
            </div>

            <div className="p-4 rounded-2xl bg-surface/70 border border-outline space-y-1.5">
              <span className="font-bold text-cyan-300 uppercase tracking-wider text-[11px] block">What Happens Next?</span>
              <p className="text-on-surface leading-relaxed">{pendingAdaptation.impact_analysis.next_action_recommendation}</p>
            </div>
          </div>
        </motion.div>
      )}

      {/* 3. Pause & Resume Alert (if returning from extended absence) */}
      {intelligenceState?.pause_status && intelligenceState.pause_status.status !== "ACTIVE" && (
        <div className="p-5 rounded-2xl bg-cyan-950/40 border border-cyan-600/60 text-xs text-on-surface flex items-start gap-3">
          <Clock className="w-5 h-5 text-cyan-400 shrink-0 mt-0.5" />
          <div className="space-y-1 flex-1">
            <span className="font-bold text-cyan-300 uppercase tracking-wider block">
              Resume Intelligence: {intelligenceState.pause_status.recommended_action} Recommendation
            </span>
            <p className="text-on-surface-variant leading-relaxed">
              {intelligenceState.pause_status.reassessment_rationale}
            </p>
          </div>
        </div>
      )}

      {/* 4. Evidence Conflict Alert (if self-report diverges from execution evidence) */}
      {intelligenceState?.conflict_status?.has_conflict && (
        <div className="p-5 rounded-2xl bg-rose-950/40 border border-rose-600/60 text-xs text-on-surface flex items-start gap-3">
          <AlertTriangle className="w-5 h-5 text-rose-400 shrink-0 mt-0.5" />
          <div className="space-y-1 flex-1">
            <span className="font-bold text-rose-300 uppercase tracking-wider block">
              Evidence Discrepancy Flagged
            </span>
            <p className="text-on-surface-variant leading-relaxed">
              {intelligenceState.conflict_status.explanation}
            </p>
            {intelligenceState.conflict_status.recommended_verification_task && (
              <span className="font-semibold text-rose-200 block pt-1">
                ↳ Suggested: {intelligenceState.conflict_status.recommended_verification_task}
              </span>
            )}
          </div>
        </div>
      )}

      {/* 5. Cross-Stage Memory Moment Banner */}
      {roadmap.memory_moment && (
        <motion.div
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          className="p-5 rounded-2xl border border-primary/40 bg-primary/10 flex items-start gap-3 text-xs"
        >
          <Sparkles className="w-5 h-5 text-primary shrink-0 mt-0.5" />
          <div className="space-y-1 flex-1">
            <span className="font-bold uppercase tracking-wider text-primary block">
              Cross-Stage Knowledge Bridge
            </span>
            <p className="text-on-surface leading-relaxed">
              {roadmap.memory_moment.connection_statement}
            </p>
            <span className="text-[11px] text-on-surface-variant block">
              Origin: {roadmap.memory_moment.stage_learned} &bull; Verified Memory
            </span>
          </div>
        </motion.div>
      )}

      {/* 6. Active Mission & Submission Workspace */}
      {activeStage && activeMission && (
        <div className="bg-surface-container border border-outline rounded-3xl p-6 md:p-8 space-y-6 shadow-xl">
          <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-outline pb-6">
            <div>
              <span className="text-xs px-3 py-1 rounded-full font-bold uppercase tracking-wider bg-primary/15 text-primary border border-primary/30">
                Active Stage {activeStage.stage_number} Mission
              </span>
              <h2 className="text-2xl font-bold text-on-surface mt-2">{activeStage.title}</h2>
              <p className="text-xs text-on-surface-variant mt-1">{activeStage.objective}</p>
            </div>
            <div className="flex items-center gap-2 text-xs">
              <span className="px-3 py-1 rounded-xl bg-surface text-on-surface border border-outline">
                Estimated Effort: {activeStage.estimated_effort}
              </span>
            </div>
          </div>

          {/* Mission Objective & Steps */}
          <div className="space-y-4">
            <div className="p-4 rounded-2xl bg-surface border border-outline space-y-2">
              <h4 className="text-xs font-bold uppercase tracking-wider text-primary">Mission Objective</h4>
              <p className="text-sm font-semibold text-on-surface">{activeMission.objective}</p>
              <p className="text-xs text-on-surface-variant leading-relaxed">{activeMission.why}</p>
            </div>

            {/* Checklist Steps */}
            <div className="space-y-2">
              <h4 className="text-xs font-bold uppercase tracking-wider text-on-surface-variant">Mission Steps</h4>
              <div className="space-y-2">
                {activeMission.steps.map((step, idx) => (
                  <div
                    key={idx}
                    onClick={() => handleToggleStep(idx)}
                    className="flex items-start gap-3 p-3.5 rounded-2xl bg-surface border border-outline/70 hover:border-primary/50 cursor-pointer transition-all text-xs"
                  >
                    <div className={`w-4 h-4 rounded-md border flex items-center justify-center mt-0.5 ${
                      completedSteps[idx] ? "bg-primary border-primary text-on-primary" : "border-outline"
                    }`}>
                      {completedSteps[idx] && <Check className="w-3 h-3" />}
                    </div>
                    <span className={completedSteps[idx] ? "line-through text-on-surface-variant" : "text-on-surface font-medium"}>
                      {step}
                    </span>
                  </div>
                ))}
              </div>
            </div>

            {/* Verified Resources */}
            {activeMission.resources.length > 0 && (
              <div className="space-y-2 pt-2">
                <h4 className="text-xs font-bold uppercase tracking-wider text-on-surface-variant">Verified Learning Resources</h4>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                  {activeMission.resources.map((res, i) => (
                    <a
                      key={i}
                      href={res.url}
                      target="_blank"
                      rel="noreferrer"
                      className="p-3.5 rounded-2xl bg-surface border border-outline hover:border-primary/50 flex items-center justify-between text-xs transition-all"
                    >
                      <div className="space-y-0.5">
                        <span className="font-bold text-on-surface block">{res.title}</span>
                        <span className="text-[11px] text-on-surface-variant">{res.provenance} • {res.estimated_duration}</span>
                      </div>
                      <ArrowRight className="w-4 h-4 text-primary" />
                    </a>
                  ))}
                </div>
              </div>
            )}

            {/* Evidence Submission Form */}
            <form onSubmit={handleSubmitEvidence} className="space-y-4 pt-4 border-t border-outline">
              <div className="space-y-1.5">
                <label className="text-xs font-bold uppercase tracking-wider text-on-surface flex items-center gap-1.5">
                  <ShieldCheck className="w-4 h-4 text-primary" /> Submit Practical Code / Repository Evidence
                </label>
                <p className="text-xs text-on-surface-variant">
                  Paste your Python implementation or GitHub repository URL. The automated evaluator verifies type safety, unit test assertions, and memory architecture.
                </p>
                <textarea
                  value={evidenceText}
                  onChange={(e) => setEvidenceText(e.target.value)}
                  placeholder="def parse_stream(records: list[dict]) -> Generator:... (or GitHub URL)"
                  rows={4}
                  className="w-full bg-surface border border-outline rounded-2xl p-4 font-mono text-xs text-on-surface focus:outline-none focus:ring-2 focus:ring-primary"
                />
              </div>

              <div className="flex items-center justify-between">
                <span className="text-xs text-on-surface-variant font-medium">
                  Prerequisites verified before unlock
                </span>
                <button
                  type="submit"
                  disabled={isSubmitting || !evidenceText.trim()}
                  className="px-6 py-2.5 rounded-xl font-bold text-xs bg-primary text-on-primary shadow-md hover:opacity-95 disabled:opacity-50 cursor-pointer"
                >
                  {isSubmitting ? "Evaluating Code Evidence..." : "Submit Evidence & Progress"}
                </button>
              </div>
            </form>

            {/* Evaluation Result Banner */}
            {evalResult && (
              <div className={`p-5 rounded-2xl border text-xs space-y-2 ${
                evalResult.status === "PASS"
                  ? "bg-emerald-950/50 border-emerald-600/60 text-emerald-200"
                  : "bg-amber-950/50 border-amber-600/60 text-amber-200"
              }`}>
                <div className="flex items-center justify-between">
                  <span className="font-bold uppercase tracking-wider flex items-center gap-1.5">
                    {evalResult.status === "PASS" ? <CheckCircle2 className="w-4 h-4" /> : <AlertTriangle className="w-4 h-4" />}
                    Evaluation: {evalResult.status}
                  </span>
                  <span className="text-[11px] font-semibold">{evalResult.confidence} Confidence</span>
                </div>
                <p>{evalResult.feedback}</p>
                <span className="font-semibold block pt-1">Next Action: {evalResult.recommended_next_action}</span>
              </div>
            )}
          </div>
        </div>
      )}

      {/* 7. Milestone Timeline with Prerequisite Locks */}
      <div className="bg-surface-container border border-outline rounded-3xl p-6 md:p-8 space-y-6">
        <div className="flex items-center justify-between border-b border-outline pb-4">
          <div>
            <h3 className="text-xl font-bold text-on-surface flex items-center gap-2">
              <Layers className="w-5 h-5 text-primary" /> Multi-Stage Milestone Sequence
            </h3>
            <p className="text-xs text-on-surface-variant mt-0.5">
              Downstream stages remain strictly locked until preceding prerequisite milestones pass evidence evaluation.
            </p>
          </div>
          <span className="text-xs px-3 py-1 rounded-full font-bold bg-surface text-on-surface border border-outline">
            {roadmap.completed_stages} of {roadmap.total_stages} Stages Completed
          </span>
        </div>

        <div className="space-y-4">
          {roadmap.stages.map((stg) => {
            const isCompleted = stg.status === "COMPLETED";
            const isActive = stg.stage_id === roadmap.current_stage_id;
            const isLocked = stg.locked;

            return (
              <div
                key={stg.stage_id}
                className={`p-6 rounded-3xl border transition-all flex flex-col md:flex-row md:items-center justify-between gap-4 ${
                  isActive
                    ? "bg-surface border-primary shadow-md shadow-primary/10"
                    : isCompleted
                    ? "bg-surface/80 border-emerald-800/40"
                    : "bg-surface/40 border-outline/50 opacity-75"
                }`}
              >
                <div className="space-y-2 flex-1">
                  <div className="flex items-center gap-2">
                    <span className="text-xs font-bold text-primary">Stage 0{stg.stage_number}</span>
                    <span className={`text-[10px] px-2.5 py-0.5 rounded-full font-bold uppercase tracking-wider ${
                      isCompleted
                        ? "bg-emerald-950/60 text-emerald-300 border border-emerald-600/60"
                        : isActive
                        ? "bg-primary/20 text-primary border border-primary/40"
                        : "bg-surface-container text-on-surface-variant border border-outline"
                    }`}>
                      {stg.status}
                    </span>
                  </div>
                  <h4 className="text-base font-bold text-on-surface">{stg.title}</h4>
                  <p className="text-xs text-on-surface-variant">{stg.objective}</p>
                  <div className="flex flex-wrap gap-1.5 pt-1">
                    {stg.skills.map((sk, idx) => (
                      <span key={idx} className="text-[11px] px-2 py-0.5 rounded-md bg-surface-container text-on-surface-variant border border-outline/50 font-medium">
                        {sk}
                      </span>
                    ))}
                  </div>
                </div>

                <div className="flex items-center gap-3">
                  {isLocked ? (
                    <div className="flex items-center gap-1.5 text-xs text-on-surface-variant/70 font-semibold px-4 py-2 rounded-xl bg-surface-container border border-outline/40">
                      <Lock className="w-3.5 h-3.5" /> Prerequisite Locked
                    </div>
                  ) : isCompleted ? (
                    <div className="flex items-center gap-1.5 text-xs text-emerald-400 font-bold px-4 py-2 rounded-xl bg-emerald-950/40 border border-emerald-700/50">
                      <CheckCircle2 className="w-4 h-4" /> Milestone Verified
                    </div>
                  ) : (
                    <div className="flex items-center gap-1.5 text-xs text-primary font-bold px-4 py-2 rounded-xl bg-primary/10 border border-primary/30">
                      <Sparkles className="w-3.5 h-3.5" /> Current Focus
                    </div>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* Goal Change Modal */}
      {goalModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm animate-in fade-in">
          <div className="bg-surface border border-outline rounded-3xl p-6 md:p-8 max-w-lg w-full space-y-6 shadow-2xl">
            <div className="space-y-1">
              <span className="text-xs font-bold uppercase tracking-wider text-primary flex items-center gap-1.5">
                <Compass className="w-4 h-4" /> Adaptive Replanning Engine
              </span>
              <h3 className="text-xl font-bold text-on-surface">Change Target Career Goal</h3>
              <p className="text-xs text-on-surface-variant">
                PATHMIND will evaluate your new outcome against verified occupational standards, preserve completed foundations, and propose an updated Roadmap sequence.
              </p>
            </div>

            <div className="space-y-2">
              <label className="text-xs font-bold uppercase tracking-wider text-on-surface-variant">Select New Target Role</label>
              <select
                value={selectedGoal}
                onChange={(e) => setSelectedGoal(e.target.value)}
                className="w-full bg-surface-container border border-outline rounded-xl p-3 text-sm font-medium text-on-surface focus:outline-none focus:ring-2 focus:ring-primary cursor-pointer"
              >
                <option value="Robotics & Autonomous Systems Engineer">🤖 Robotics &amp; Autonomous Systems Engineer</option>
                <option value="Applied Machine Learning Systems Engineer">🧠 Applied Machine Learning Systems Engineer</option>
                <option value="Data Platform & MLOps Infrastructure Engineer">⚙️ Data Platform &amp; MLOps Infrastructure Engineer</option>
                <option value="Full-Stack AI Application Developer">💻 Full-Stack AI Application Developer</option>
                <option value="Autonomous Vehicle Perception Specialist">🚗 Autonomous Vehicle Perception Specialist</option>
              </select>
            </div>

            <div className="p-3.5 rounded-2xl bg-primary/10 border border-primary/25 text-xs text-on-surface space-y-1">
              <span className="font-bold text-primary block">Plan Stability Guarantee</span>
              <p className="text-on-surface-variant">
                Your completed Python foundations and mathematical competencies remain fully intact and will not be erased.
              </p>
            </div>

            <div className="flex items-center justify-end gap-3 pt-2">
              <button
                onClick={() => setGoalModalOpen(false)}
                className="px-4 py-2.5 rounded-xl font-semibold text-xs bg-surface border border-outline text-on-surface hover:bg-surface-container cursor-pointer"
              >
                Cancel
              </button>
              <button
                onClick={handleGoalChangeSubmit}
                disabled={isChangingGoal}
                className="px-5 py-2.5 rounded-xl font-bold text-xs bg-primary text-on-primary shadow-md hover:opacity-95 disabled:opacity-50 cursor-pointer"
              >
                {isChangingGoal ? "Evaluating Impact..." : "Propose New Roadmap Version"}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Adjust Workload Modal */}
      {adaptOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm animate-in fade-in">
          <div className="bg-surface border border-outline rounded-3xl p-6 md:p-8 max-w-md w-full space-y-6 shadow-2xl">
            <div className="space-y-1">
              <span className="text-xs font-bold uppercase tracking-wider text-primary flex items-center gap-1.5">
                <Clock className="w-4 h-4" /> Workload &amp; Constraint Adaptation
              </span>
              <h3 className="text-xl font-bold text-on-surface">Adjust Study Commitment</h3>
              <p className="text-xs text-on-surface-variant">
                Recalibrates estimated stage durations and weekly checkpoints while preserving all completed work.
              </p>
            </div>

            <div className="space-y-3">
              <div className="flex items-center justify-between text-xs">
                <span className="font-semibold text-on-surface">Weekly Hours Commitment:</span>
                <span className="font-bold text-primary text-sm">{weeklyHours} hrs/week</span>
              </div>
              <input
                type="range"
                min={4}
                max={30}
                step={2}
                value={weeklyHours}
                onChange={(e) => setWeeklyHours(parseInt(e.target.value))}
                className="w-full accent-primary cursor-pointer"
              />
            </div>

            <div className="flex items-center justify-end gap-3 pt-2">
              <button
                onClick={() => setAdaptOpen(false)}
                className="px-4 py-2.5 rounded-xl font-semibold text-xs bg-surface border border-outline text-on-surface hover:bg-surface-container cursor-pointer"
              >
                Cancel
              </button>
              <button
                onClick={handleAdaptConstraints}
                disabled={isAdapting}
                className="px-5 py-2.5 rounded-xl font-bold text-xs bg-primary text-on-primary shadow-md hover:opacity-95 disabled:opacity-50 cursor-pointer"
              >
                {isAdapting ? "Recalibrating..." : "Save Pacing"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
