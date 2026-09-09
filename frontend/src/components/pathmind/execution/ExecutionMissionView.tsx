"use client";

import { useState, useEffect, useCallback } from "react";
import {
  Target,
  CheckCircle2,
  AlertCircle,
  Pause,
  Play,
  Calendar,
  ShieldCheck,
  Briefcase,
  Plus,
  Compass,
  Layers
} from "lucide-react";

interface Blocker {
  blocker_id: string;
  blocker_type: string;
  description: string;
  workaround?: string | null;
  suggested_resolution_action?: string | null;
  is_active: boolean;
}

interface RescheduleHistoryItem {
  original_due_at: string;
  new_due_at: string;
  reason: string;
  rescheduled_at: string;
}

interface ActionItem {
  action_id: string;
  person_id: string;
  title: string;
  description: string;
  action_type: string;
  goal_id?: string | null;
  goal_title?: string | null;
  stage_id?: string | null;
  stage_title?: string | null;
  capability_ids: string[];
  evidence_requirement_ids: string[];
  priority: string;
  status: string;
  dependencies: string[];
  blocking_reason?: Blocker | null;
  verification_requirement: string;
  outcome: string;
  outcome_notes?: string | null;
  source: string;
  due_at?: string | null;
  started_at?: string | null;
  completed_at?: string | null;
  reschedule_history: RescheduleHistoryItem[];
}

interface DailyPlan {
  person_id: string;
  primary_action?: ActionItem | null;
  secondary_actions: ActionItem[];
  why_it_matters: string;
  evidence_proof_required: string;
  active_blockers: Blocker[];
  next_subsequent_step: string;
  is_paused: boolean;
  pause_reason?: string | null;
  as_of_date: string;
}

interface AccountabilityItem {
  intervention_id: string;
  person_id: string;
  missed_action_id: string;
  action_title: string;
  original_due_at: string;
  days_overdue: number;
  non_judgmental_message: string;
  suggested_options: string[];
}

interface OpportunityApp {
  application_id: string;
  opportunity_id: string;
  opportunity_title: string;
  organization: string;
  status: string;
  notes?: string | null;
  applied_at?: string | null;
  updated_at: string;
}

export function ExecutionMissionView() {
  const [plan, setPlan] = useState<DailyPlan | null>(null);
  const [actions, setActions] = useState<ActionItem[]>([]);
  const [accountability, setAccountability] = useState<AccountabilityItem[]>([]);
  const [applications, setApplications] = useState<OpportunityApp[]>([]);
  const [loading, setLoading] = useState(true);

  // Modals & form state
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [createForm, setCreateForm] = useState({
    title: "",
    description: "",
    action_type: "LEARNING",
    priority: "NOW",
    due_at: ""
  });

  const [rescheduleActionId, setRescheduleActionId] = useState<string | null>(null);
  const [rescheduleForm, setRescheduleForm] = useState({
    new_due_at: "",
    reason: ""
  });

  const [blockActionId, setBlockActionId] = useState<string | null>(null);
  const [blockForm, setBlockForm] = useState({
    blocker_type: "TECHNICAL_BLOCKER",
    description: "",
    workaround: ""
  });

  const [completeActionId, setCompleteActionId] = useState<string | null>(null);
  const [completeForm, setCompleteForm] = useState({
    outcome: "COMPLETED_SUCCESSFULLY",
    outcome_notes: "",
    evidence_id: ""
  });

  const [showAppModal, setShowAppModal] = useState(false);
  const [appForm, setAppForm] = useState({
    opportunity_id: "opp_custom",
    opportunity_title: "",
    organization: "",
    status: "SAVED",
    notes: ""
  });

  const fetchData = useCallback(async () => {
    try {
      const headers = { "x-person-id": "scholar-user" };
      const [planRes, actionsRes, accRes, appRes] = await Promise.all([
        fetch("/api/execution/daily", { headers }),
        fetch("/api/execution/actions", { headers }),
        fetch("/api/execution/accountability", { headers }),
        fetch("/api/execution/applications", { headers })
      ]);

      if (planRes.ok) setPlan(await planRes.json());
      if (actionsRes.ok) setActions(await actionsRes.json());
      if (accRes.ok) setAccountability(await accRes.json());
      if (appRes.ok) setApplications(await appRes.json());
    } catch (err) {
      console.error("Failed to load execution data:", err);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  // Action handlers
  const handleStart = async (actionId: string) => {
    try {
      const res = await fetch(`/api/execution/actions/${actionId}/start`, {
        method: "POST",
        headers: { "x-person-id": "scholar-user" }
      });
      if (res.ok) fetchData();
      else {
        const err = await res.json();
        alert(err.detail || "Cannot start action.");
      }
    } catch (err) {
      console.error(err);
    }
  };

  const handleCompleteSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!completeActionId) return;
    try {
      const res = await fetch(`/api/execution/actions/${completeActionId}/complete`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "x-person-id": "scholar-user"
        },
        body: JSON.stringify(completeForm)
      });
      if (res.ok) {
        setCompleteActionId(null);
        fetchData();
      }
    } catch (err) {
      console.error(err);
    }
  };

  const handleRescheduleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!rescheduleActionId) return;
    try {
      const res = await fetch(`/api/execution/actions/${rescheduleActionId}/reschedule`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "x-person-id": "scholar-user"
        },
        body: JSON.stringify(rescheduleForm)
      });
      if (res.ok) {
        setRescheduleActionId(null);
        fetchData();
      }
    } catch (err) {
      console.error(err);
    }
  };

  const handleBlockSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!blockActionId) return;
    try {
      const res = await fetch(`/api/execution/actions/${blockActionId}/block`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "x-person-id": "scholar-user"
        },
        body: JSON.stringify(blockForm)
      });
      if (res.ok) {
        setBlockActionId(null);
        fetchData();
      }
    } catch (err) {
      console.error(err);
    }
  };

  const handleResolveBlocker = async (actionId: string) => {
    try {
      const res = await fetch(`/api/execution/actions/${actionId}/resolve-blocker`, {
        method: "POST",
        headers: { "x-person-id": "scholar-user" }
      });
      if (res.ok) fetchData();
    } catch (err) {
      console.error(err);
    }
  };

  const handleTogglePause = async () => {
    if (!plan) return;
    const url = plan.is_paused ? "/api/execution/resume" : "/api/execution/pause";
    const body = plan.is_paused ? {} : { reason: "Learner-requested pause to focus on university exams." };
    try {
      await fetch(url, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "x-person-id": "scholar-user"
        },
        body: JSON.stringify(body)
      });
      fetchData();
    } catch (err) {
      console.error(err);
    }
  };

  const handleCreateAction = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      const res = await fetch("/api/execution/actions", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "x-person-id": "scholar-user"
        },
        body: JSON.stringify(createForm)
      });
      if (res.ok) {
        setShowCreateModal(false);
        setCreateForm({ title: "", description: "", action_type: "LEARNING", priority: "NOW", due_at: "" });
        fetchData();
      }
    } catch (err) {
      console.error(err);
    }
  };

  const handleCreateApp = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      const res = await fetch("/api/execution/applications", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "x-person-id": "scholar-user"
        },
        body: JSON.stringify(appForm)
      });
      if (res.ok) {
        setShowAppModal(false);
        setAppForm({ opportunity_id: "opp_custom", opportunity_title: "", organization: "", status: "SAVED", notes: "" });
        fetchData();
      }
    } catch (err) {
      console.error(err);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[500px]">
        <div className="flex items-center space-x-3 text-stone-600">
          <div className="w-5 h-5 border-2 border-stone-400 border-t-transparent rounded-full animate-spin" />
          <span className="font-serif italic text-sm">Preparing your daily plan &amp; learning actions...</span>
        </div>
      </div>
    );
  }

  const primary = plan?.primary_action;

  return (
    <div className="max-w-6xl mx-auto px-4 py-8 space-y-10">
      {/* Editorial Header */}
      <div className="border-b border-stone-200 pb-6 flex flex-col md:flex-row md:items-end justify-between gap-4">
        <div>
          <div className="flex items-center space-x-2 text-stone-700 text-xs font-mono uppercase tracking-widest mb-1">
            <Target className="w-3.5 h-3.5 text-stone-700" />
            <span>Today&apos;s Plan &amp; Actions</span>
          </div>
          <h1 className="text-3xl font-serif tracking-tight text-stone-900">
            Today&apos;s Plan &amp; Progress
          </h1>
          <p className="text-stone-600 text-sm mt-1 max-w-xl">
            Turn your learning roadmap and target career goals into clear, verified daily actions.
          </p>
        </div>

        <div className="flex items-center space-x-3">
          <button
            onClick={handleTogglePause}
            className={`flex items-center space-x-2 text-xs font-mono px-3.5 py-2 rounded border transition-colors ${
              plan?.is_paused
                ? "bg-amber-50 text-amber-800 border-amber-300 hover:bg-amber-100"
                : "bg-white text-stone-700 border-stone-300 hover:bg-stone-50"
            }`}
          >
            {plan?.is_paused ? <Play className="w-3.5 h-3.5 text-amber-700" /> : <Pause className="w-3.5 h-3.5 text-stone-500" />}
            <span>{plan?.is_paused ? "Resume Execution" : "Pause Timers"}</span>
          </button>

          <button
            onClick={() => setShowCreateModal(true)}
            className="flex items-center space-x-2 bg-stone-900 hover:bg-stone-800 text-white text-xs font-mono px-3.5 py-2 rounded transition-colors"
          >
            <Plus className="w-3.5 h-3.5" />
            <span>New Custom Action</span>
          </button>
        </div>
      </div>

      {/* Non-Judgmental Accountability Banner */}
      {accountability.length > 0 && !plan?.is_paused && (
        <div className="p-5 rounded-lg border border-amber-200 bg-amber-50/70 space-y-3">
          <div className="flex items-start justify-between">
            <div className="flex items-center space-x-2 text-amber-900 font-medium text-sm">
              <AlertCircle className="w-4 h-4 text-amber-700 shrink-0" />
              <span>Context-Aware Accountability Check-in</span>
            </div>
            <span className="text-xs font-mono text-amber-700">Non-judgmental reflection</span>
          </div>
          {accountability.map((item) => (
            <div key={item.intervention_id} className="text-xs text-amber-900/90 space-y-2">
              <p className="leading-relaxed font-sans">{item.non_judgmental_message}</p>
              <div className="flex flex-wrap gap-2 pt-1">
                {item.suggested_options.map((opt, i) => (
                  <button
                    key={i}
                    onClick={() => setRescheduleActionId(item.missed_action_id)}
                    className="text-[11px] font-mono bg-white border border-amber-300 hover:border-amber-400 text-amber-900 px-2.5 py-1 rounded shadow-xs"
                  >
                    {opt}
                  </button>
                ))}
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Paused Banner */}
      {plan?.is_paused && (
        <div className="p-4 rounded-lg border border-stone-300 bg-stone-100/70 flex items-center justify-between text-xs text-stone-700 font-mono">
          <div className="flex items-center space-x-2">
            <Pause className="w-4 h-4 text-stone-500" />
            <span>Execution is paused: {plan.pause_reason}</span>
          </div>
          <span className="text-stone-500">Overdue checks and action aging are frozen.</span>
        </div>
      )}

      {/* Primary Action Hero Card (Today's Anchor) */}
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-2 text-xs font-mono uppercase tracking-wider text-stone-500">
            <Compass className="w-3.5 h-3.5 text-stone-700" />
            <span>Primary Focus • Today</span>
          </div>
          {primary && (
            <span className={`text-[11px] font-mono px-2 py-0.5 rounded border ${
              primary.status === "IN_PROGRESS"
                ? "bg-blue-50 text-blue-800 border-blue-200"
                : primary.status === "BLOCKED"
                ? "bg-rose-50 text-rose-800 border-rose-200"
                : "bg-emerald-50 text-emerald-800 border-emerald-200"
            }`}>
              {primary.status.replace("_", " ")}
            </span>
          )}
        </div>

        {primary ? (
          <div className="border border-stone-200 bg-white rounded-xl p-6 md:p-8 shadow-xs space-y-6">
            <div className="flex flex-col md:flex-row md:items-start justify-between gap-4">
              <div className="space-y-2">
                <span className="text-[11px] font-mono text-stone-500 uppercase tracking-wider">
                  {primary.action_type} • {primary.stage_title || "Active Roadmap"}
                </span>
                <h2 className="text-2xl font-serif text-stone-900 tracking-tight">
                  {primary.title}
                </h2>
                <p className="text-sm text-stone-600 leading-relaxed max-w-2xl">
                  {primary.description}
                </p>
              </div>

              {/* Action Operations */}
              <div className="flex flex-wrap md:flex-col gap-2 shrink-0">
                {primary.status === "READY" && (
                  <button
                    onClick={() => handleStart(primary.action_id)}
                    className="flex items-center justify-center space-x-1.5 bg-stone-900 hover:bg-stone-800 text-white text-xs font-mono px-4 py-2 rounded transition-colors"
                  >
                    <Play className="w-3.5 h-3.5" />
                    <span>Start Action</span>
                  </button>
                )}

                {primary.status === "IN_PROGRESS" && (
                  <button
                    onClick={() => setCompleteActionId(primary.action_id)}
                    className="flex items-center justify-center space-x-1.5 bg-emerald-700 hover:bg-emerald-800 text-white text-xs font-mono px-4 py-2 rounded transition-colors"
                  >
                    <CheckCircle2 className="w-3.5 h-3.5" />
                    <span>Complete with Proof</span>
                  </button>
                )}

                {primary.status === "BLOCKED" ? (
                  <button
                    onClick={() => handleResolveBlocker(primary.action_id)}
                    className="flex items-center justify-center space-x-1.5 bg-amber-600 hover:bg-amber-700 text-white text-xs font-mono px-4 py-2 rounded transition-colors"
                  >
                    <CheckCircle2 className="w-3.5 h-3.5" />
                    <span>Resolve Blocker</span>
                  </button>
                ) : (
                  <button
                    onClick={() => setBlockActionId(primary.action_id)}
                    className="flex items-center justify-center space-x-1.5 border border-stone-300 hover:bg-stone-50 text-stone-700 text-xs font-mono px-4 py-2 rounded transition-colors"
                  >
                    <AlertCircle className="w-3.5 h-3.5 text-stone-500" />
                    <span>Report Blocker</span>
                  </button>
                )}

                <button
                  onClick={() => setRescheduleActionId(primary.action_id)}
                  className="flex items-center justify-center space-x-1.5 border border-stone-300 hover:bg-stone-50 text-stone-700 text-xs font-mono px-4 py-2 rounded transition-colors"
                >
                  <Calendar className="w-3.5 h-3.5 text-stone-500" />
                  <span>Reschedule</span>
                </button>
              </div>
            </div>

            {/* Traceable Execution Chain Details */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4 pt-4 border-t border-stone-100 text-xs">
              <div className="space-y-1 bg-stone-50/70 p-3.5 rounded-lg border border-stone-200/60">
                <span className="font-mono text-[10px] text-stone-500 uppercase tracking-wider block">
                  Why Am I Doing This?
                </span>
                <p className="text-stone-700 font-sans leading-normal">
                  {plan?.why_it_matters}
                </p>
              </div>

              <div className="space-y-1 bg-stone-50/70 p-3.5 rounded-lg border border-stone-200/60">
                <span className="font-mono text-[10px] text-stone-500 uppercase tracking-wider block">
                  Proof of Completion
                </span>
                <p className="text-stone-700 font-sans leading-normal">
                  {plan?.evidence_proof_required}
                </p>
              </div>

              <div className="space-y-1 bg-stone-50/70 p-3.5 rounded-lg border border-stone-200/60">
                <span className="font-mono text-[10px] text-stone-500 uppercase tracking-wider block">
                  What Follows Next
                </span>
                <p className="text-stone-700 font-sans leading-normal">
                  {plan?.next_subsequent_step}
                </p>
              </div>
            </div>

            {/* Active Blocker Alert if present */}
            {primary.blocking_reason && primary.blocking_reason.is_active && (
              <div className="p-4 rounded-lg bg-rose-50 border border-rose-200 text-xs text-rose-900 space-y-2">
                <div className="flex items-center space-x-2 font-mono font-medium">
                  <AlertCircle className="w-4 h-4 text-rose-600 shrink-0" />
                  <span>Blocked: {primary.blocking_reason.blocker_type.replace("_", " ")}</span>
                </div>
                <p className="font-sans">{primary.blocking_reason.description}</p>
                {primary.blocking_reason.workaround && (
                  <div className="mt-2 pt-2 border-t border-rose-200/60 text-rose-800 font-sans">
                    <span className="font-mono font-semibold">Recommended Workaround: </span>
                    {primary.blocking_reason.workaround}
                  </div>
                )}
              </div>
            )}
          </div>
        ) : (
          <div className="p-8 text-center border border-dashed border-stone-300 rounded-xl bg-stone-50/50 space-y-3">
            <ShieldCheck className="w-8 h-8 text-stone-400 mx-auto" />
            <h3 className="font-serif text-lg text-stone-800">All Stage Objectives Complete</h3>
            <p className="text-xs text-stone-600 max-w-md mx-auto">
              You have completed all actionable milestones for the active roadmap stage. Submit your stage evidence or explore upcoming milestones below.
            </p>
          </div>
        )}
      </div>

      {/* Secondary & Upcoming Execution Horizon */}
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-2 text-xs font-mono uppercase tracking-wider text-stone-500">
            <Layers className="w-3.5 h-3.5 text-stone-700" />
            <span>Execution Horizon • Active Stage Actions</span>
          </div>
          <span className="text-xs font-mono text-stone-500">
            {actions.filter(a => a.status === "COMPLETED").length} of {actions.length} Completed
          </span>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {actions.map((act) => (
            <div
              key={act.action_id}
              className={`p-5 rounded-lg border transition-all ${
                act.status === "COMPLETED"
                  ? "bg-stone-50/80 border-stone-200 text-stone-500"
                  : act.status === "BLOCKED"
                  ? "bg-rose-50/30 border-rose-200/60 text-stone-900"
                  : "bg-white border-stone-200 hover:border-stone-300 text-stone-900"
              }`}
            >
              <div className="flex items-start justify-between gap-2 mb-2">
                <span className="text-[10px] font-mono uppercase px-2 py-0.5 rounded bg-stone-100 text-stone-600 border border-stone-200">
                  {act.action_type}
                </span>
                <span className={`text-[10px] font-mono px-2 py-0.5 rounded ${
                  act.status === "COMPLETED"
                    ? "text-emerald-700 bg-emerald-50 border border-emerald-200"
                    : act.status === "BLOCKED"
                    ? "text-rose-700 bg-rose-50 border border-rose-200"
                    : "text-stone-600 bg-stone-100"
                }`}>
                  {act.status}
                </span>
              </div>

              <h4 className={`text-base font-serif mb-1 ${act.status === "COMPLETED" ? "line-through text-stone-400" : "text-stone-900"}`}>
                {act.title}
              </h4>
              <p className="text-xs text-stone-600 line-clamp-2 leading-relaxed mb-3">
                {act.description}
              </p>

              <div className="flex items-center justify-between text-[11px] font-mono text-stone-500 pt-2 border-t border-stone-100">
                <span>Proof: {act.verification_requirement.replace("_", " ").toLowerCase()}</span>
                {act.due_at && (
                  <span>Due: {new Date(act.due_at).toLocaleDateString()}</span>
                )}
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Real Career Opportunity Application Pipeline */}
      <div className="space-y-4 pt-4 border-t border-stone-200">
        <div className="flex items-center justify-between">
          <div>
            <div className="flex items-center space-x-2 text-xs font-mono uppercase tracking-wider text-stone-500">
              <Briefcase className="w-3.5 h-3.5 text-stone-700" />
              <span>Career Opportunities & Application Pipeline</span>
            </div>
            <h3 className="font-serif text-xl text-stone-900 mt-0.5">
              Verified Opportunity Tracking
            </h3>
          </div>
          <button
            onClick={() => setShowAppModal(true)}
            className="flex items-center space-x-1.5 border border-stone-300 hover:bg-stone-50 text-stone-700 text-xs font-mono px-3 py-1.5 rounded transition-colors"
          >
            <Plus className="w-3 h-3" />
            <span>Track Application</span>
          </button>
        </div>

        {applications.length > 0 ? (
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {applications.map((app) => (
              <div key={app.application_id} className="p-4 rounded-lg border border-stone-200 bg-white space-y-2">
                <div className="flex items-center justify-between">
                  <span className="text-[10px] font-mono uppercase text-stone-500">{app.organization}</span>
                  <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-stone-100 text-stone-700">
                    {app.status}
                  </span>
                </div>
                <h4 className="font-serif text-base text-stone-900">{app.opportunity_title}</h4>
                {app.notes && <p className="text-xs text-stone-600 line-clamp-2">{app.notes}</p>}
                <div className="text-[10px] font-mono text-stone-500 pt-1 border-t border-stone-100">
                  {app.applied_at ? `Applied: ${new Date(app.applied_at).toLocaleDateString()}` : "Not yet submitted"}
                </div>
              </div>
            ))}
          </div>
        ) : (
          <div className="p-6 text-center border border-dashed border-stone-300 rounded-lg bg-stone-50/50 text-xs text-stone-600 font-mono">
            No active opportunity applications tracked yet. Use &quot;Track Application&quot; to monitor real submissions.
          </div>
        )}
      </div>

      {/* Complete Action Modal */}
      {completeActionId && (
        <div className="fixed inset-0 bg-stone-900/50 backdrop-blur-xs flex items-center justify-center p-4 z-50">
          <div className="bg-white border border-stone-200 rounded-xl p-6 max-w-md w-full space-y-4 shadow-xl">
            <h3 className="text-lg font-serif text-stone-900">Complete Action with Proof</h3>
            <form onSubmit={handleCompleteSubmit} className="space-y-3">
              <div>
                <label className="text-xs font-mono text-stone-600 block mb-1">Outcome Status</label>
                <select
                  value={completeForm.outcome}
                  onChange={(e) => setCompleteForm({ ...completeForm, outcome: e.target.value })}
                  className="w-full text-xs font-mono p-2 border border-stone-300 rounded bg-stone-50"
                >
                  <option value="COMPLETED_SUCCESSFULLY">Completed Successfully</option>
                  <option value="COMPLETED_WITH_GAP">Completed with Minor Capability Gap</option>
                  <option value="COMPLETED_NOT_VERIFIED">Completed (Pending Verification Proof)</option>
                </select>
              </div>

              <div>
                <label className="text-xs font-mono text-stone-600 block mb-1">Evidence Reference (Artifact / Test Run ID)</label>
                <input
                  type="text"
                  placeholder="art_... or leave blank if conceptual summary"
                  value={completeForm.evidence_id}
                  onChange={(e) => setCompleteForm({ ...completeForm, evidence_id: e.target.value })}
                  className="w-full text-xs font-mono p-2 border border-stone-300 rounded"
                />
              </div>

              <div>
                <label className="text-xs font-mono text-stone-600 block mb-1">Notes / Reflection</label>
                <textarea
                  rows={3}
                  placeholder="Key takeaway or reflection from this execution sprint..."
                  value={completeForm.outcome_notes}
                  onChange={(e) => setCompleteForm({ ...completeForm, outcome_notes: e.target.value })}
                  className="w-full text-xs font-sans p-2 border border-stone-300 rounded"
                />
              </div>

              <div className="flex justify-end space-x-2 pt-2">
                <button
                  type="button"
                  onClick={() => setCompleteActionId(null)}
                  className="px-3 py-1.5 text-xs font-mono text-stone-600 hover:bg-stone-100 rounded"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="px-4 py-1.5 text-xs font-mono bg-stone-900 text-white rounded hover:bg-stone-800"
                >
                  Save Outcome
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Reschedule Modal */}
      {rescheduleActionId && (
        <div className="fixed inset-0 bg-stone-900/50 backdrop-blur-xs flex items-center justify-center p-4 z-50">
          <div className="bg-white border border-stone-200 rounded-xl p-6 max-w-md w-full space-y-4 shadow-xl">
            <h3 className="text-lg font-serif text-stone-900">Reschedule Action</h3>
            <p className="text-xs text-stone-600">
              Preserving original schedule history ensures your longitudinal learning model understands pacing adjustments without penalty.
            </p>
            <form onSubmit={handleRescheduleSubmit} className="space-y-3">
              <div>
                <label className="text-xs font-mono text-stone-600 block mb-1">New Target Due Date</label>
                <input
                  type="date"
                  required
                  value={rescheduleForm.new_due_at}
                  onChange={(e) => setRescheduleForm({ ...rescheduleForm, new_due_at: e.target.value })}
                  className="w-full text-xs font-mono p-2 border border-stone-300 rounded"
                />
              </div>

              <div>
                <label className="text-xs font-mono text-stone-600 block mb-1">Reason for Rescheduling</label>
                <textarea
                  rows={3}
                  required
                  placeholder="e.g., University midterms, work project sprint, or needed additional foundational reading..."
                  value={rescheduleForm.reason}
                  onChange={(e) => setRescheduleForm({ ...rescheduleForm, reason: e.target.value })}
                  className="w-full text-xs font-sans p-2 border border-stone-300 rounded"
                />
              </div>

              <div className="flex justify-end space-x-2 pt-2">
                <button
                  type="button"
                  onClick={() => setRescheduleActionId(null)}
                  className="px-3 py-1.5 text-xs font-mono text-stone-600 hover:bg-stone-100 rounded"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="px-4 py-1.5 text-xs font-mono bg-stone-900 text-white rounded hover:bg-stone-800"
                >
                  Record Reschedule
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Block Action Modal */}
      {blockActionId && (
        <div className="fixed inset-0 bg-stone-900/50 backdrop-blur-xs flex items-center justify-center p-4 z-50">
          <div className="bg-white border border-stone-200 rounded-xl p-6 max-w-md w-full space-y-4 shadow-xl">
            <h3 className="text-lg font-serif text-stone-900">Report an Execution Blocker</h3>
            <form onSubmit={handleBlockSubmit} className="space-y-3">
              <div>
                <label className="text-xs font-mono text-stone-600 block mb-1">Blocker Category</label>
                <select
                  value={blockForm.blocker_type}
                  onChange={(e) => setBlockForm({ ...blockForm, blocker_type: e.target.value })}
                  className="w-full text-xs font-mono p-2 border border-stone-300 rounded bg-stone-50"
                >
                  <option value="TECHNICAL_BLOCKER">Technical Blocker (Code/Compiler/Bug)</option>
                  <option value="KNOWLEDGE_GAP">Knowledge Gap (Missing Prerequisite)</option>
                  <option value="TIME_CONSTRAINT">Time Constraint (Capacity Shift)</option>
                  <option value="FINANCIAL_CONSTRAINT">Financial Constraint (Resource/Tool Cost)</option>
                  <option value="ACCESS_CONSTRAINT">Access Constraint (Permissions/API Key)</option>
                  <option value="EXTERNAL_DEPENDENCY">External Dependency</option>
                  <option value="OTHER">Other Blocker</option>
                </select>
              </div>

              <div>
                <label className="text-xs font-mono text-stone-600 block mb-1">Detailed Explanation</label>
                <textarea
                  rows={3}
                  required
                  placeholder="What specifically is impeding execution?"
                  value={blockForm.description}
                  onChange={(e) => setBlockForm({ ...blockForm, description: e.target.value })}
                  className="w-full text-xs font-sans p-2 border border-stone-300 rounded"
                />
              </div>

              <div className="flex justify-end space-x-2 pt-2">
                <button
                  type="button"
                  onClick={() => setBlockActionId(null)}
                  className="px-3 py-1.5 text-xs font-mono text-stone-600 hover:bg-stone-100 rounded"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="px-4 py-1.5 text-xs font-mono bg-rose-700 text-white rounded hover:bg-rose-800"
                >
                  Report & Diagnose
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* New Custom Action Modal */}
      {showCreateModal && (
        <div className="fixed inset-0 bg-stone-900/50 backdrop-blur-xs flex items-center justify-center p-4 z-50">
          <div className="bg-white border border-stone-200 rounded-xl p-6 max-w-md w-full space-y-4 shadow-xl">
            <h3 className="text-lg font-serif text-stone-900">Create Personal Action</h3>
            <form onSubmit={handleCreateAction} className="space-y-3">
              <div>
                <label className="text-xs font-mono text-stone-600 block mb-1">Title</label>
                <input
                  type="text"
                  required
                  placeholder="e.g. Implement custom benchmark script"
                  value={createForm.title}
                  onChange={(e) => setCreateForm({ ...createForm, title: e.target.value })}
                  className="w-full text-xs font-mono p-2 border border-stone-300 rounded"
                />
              </div>

              <div>
                <label className="text-xs font-mono text-stone-600 block mb-1">Action Category</label>
                <select
                  value={createForm.action_type}
                  onChange={(e) => setCreateForm({ ...createForm, action_type: e.target.value })}
                  className="w-full text-xs font-mono p-2 border border-stone-300 rounded bg-stone-50"
                >
                  <option value="LEARNING">Learning & Theory</option>
                  <option value="PRACTICE">Practice & Coding</option>
                  <option value="PROJECT">Project Implementation</option>
                  <option value="EVIDENCE">Evidence & Testing</option>
                  <option value="NETWORKING">Networking & Community</option>
                  <option value="APPLICATION">Career Application</option>
                </select>
              </div>

              <div>
                <label className="text-xs font-mono text-stone-600 block mb-1">Description</label>
                <textarea
                  rows={2}
                  value={createForm.description}
                  onChange={(e) => setCreateForm({ ...createForm, description: e.target.value })}
                  className="w-full text-xs font-sans p-2 border border-stone-300 rounded"
                />
              </div>

              <div>
                <label className="text-xs font-mono text-stone-600 block mb-1">Target Due Date (Optional)</label>
                <input
                  type="date"
                  value={createForm.due_at}
                  onChange={(e) => setCreateForm({ ...createForm, due_at: e.target.value })}
                  className="w-full text-xs font-mono p-2 border border-stone-300 rounded"
                />
              </div>

              <div className="flex justify-end space-x-2 pt-2">
                <button
                  type="button"
                  onClick={() => setShowCreateModal(false)}
                  className="px-3 py-1.5 text-xs font-mono text-stone-600 hover:bg-stone-100 rounded"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="px-4 py-1.5 text-xs font-mono bg-stone-900 text-white rounded hover:bg-stone-800"
                >
                  Create Action
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Track Application Modal */}
      {showAppModal && (
        <div className="fixed inset-0 bg-stone-900/50 backdrop-blur-xs flex items-center justify-center p-4 z-50">
          <div className="bg-white border border-stone-200 rounded-xl p-6 max-w-md w-full space-y-4 shadow-xl">
            <h3 className="text-lg font-serif text-stone-900">Track Career Application</h3>
            <form onSubmit={handleCreateApp} className="space-y-3">
              <div>
                <label className="text-xs font-mono text-stone-600 block mb-1">Role / Position Title</label>
                <input
                  type="text"
                  required
                  placeholder="e.g. Applied Machine Learning Intern"
                  value={appForm.opportunity_title}
                  onChange={(e) => setAppForm({ ...appForm, opportunity_title: e.target.value })}
                  className="w-full text-xs font-mono p-2 border border-stone-300 rounded"
                />
              </div>

              <div>
                <label className="text-xs font-mono text-stone-600 block mb-1">Organization / Lab</label>
                <input
                  type="text"
                  required
                  placeholder="e.g. Deep Learning Research Group"
                  value={appForm.organization}
                  onChange={(e) => setAppForm({ ...appForm, organization: e.target.value })}
                  className="w-full text-xs font-mono p-2 border border-stone-300 rounded"
                />
              </div>

              <div>
                <label className="text-xs font-mono text-stone-600 block mb-1">Application Pipeline State</label>
                <select
                  value={appForm.status}
                  onChange={(e) => setAppForm({ ...appForm, status: e.target.value })}
                  className="w-full text-xs font-mono p-2 border border-stone-300 rounded bg-stone-50"
                >
                  <option value="SAVED">Saved for Later</option>
                  <option value="PREPARING">Preparing Application & Resume</option>
                  <option value="APPLIED">Submitted Application</option>
                  <option value="INTERVIEWING">Interviewing</option>
                </select>
              </div>

              <div>
                <label className="text-xs font-mono text-stone-600 block mb-1">Notes (Optional)</label>
                <textarea
                  rows={2}
                  placeholder="Key contacts or notes on tailored portfolio..."
                  value={appForm.notes}
                  onChange={(e) => setAppForm({ ...appForm, notes: e.target.value })}
                  className="w-full text-xs font-sans p-2 border border-stone-300 rounded"
                />
              </div>

              <div className="flex justify-end space-x-2 pt-2">
                <button
                  type="button"
                  onClick={() => setShowAppModal(false)}
                  className="px-3 py-1.5 text-xs font-mono text-stone-600 hover:bg-stone-100 rounded"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="px-4 py-1.5 text-xs font-mono bg-stone-900 text-white rounded hover:bg-stone-800"
                >
                  Save to Pipeline
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
