"use client";

import { useState, useEffect, useCallback } from "react";
import { motion } from "framer-motion";
import {
  Cpu,
  Play,
  AlertTriangle,
  ShieldCheck,
  Ban,
  Wrench
} from "lucide-react";

interface AgentContractData {
  agent_id: string;
  name: string;
  purpose: string;
  allowed_inputs: string[];
  allowed_tools: string[];
  output_schema: string;
  forbidden_operations: string[];
  failure_states: string[];
}

interface ActionProposalData {
  proposal_id: string;
  workflow_id: string;
  person_id: string;
  action_type: string;
  target_entity: string;
  target_entity_id: string;
  proposed_change: Record<string, unknown>;
  reason: string;
  supporting_evidence: string[];
  requires_confirmation: boolean;
  status: string;
  created_at: string;
}

interface AgentStepTraceData {
  step_id: string;
  agent_id: string;
  status: string;
  input_summary: string;
  output_summary: string;
  duration_ms: number;
  error?: string | null;
}

interface OrchestrationTraceData {
  workflow_id: string;
  person_id: string;
  task_type: string;
  status: string;
  started_at: string;
  completed_at?: string | null;
  total_duration_ms: number;
  steps: AgentStepTraceData[];
  agents_invoked: string[];
  action_proposals: ActionProposalData[];
}

interface OrchestrationResponseData {
  workflow_id: string;
  person_id: string;
  task_type: string;
  status: string;
  final_answer: string;
  structured_result: Record<string, unknown>;
  action_proposals: ActionProposalData[];
  requires_approval: boolean;
  trace: OrchestrationTraceData;
}

export function OrchestrationHubView() {
  const [agents, setAgents] = useState<AgentContractData[]>([]);
  const [traces, setTraces] = useState<OrchestrationTraceData[]>([]);
  const [proposals, setProposals] = useState<ActionProposalData[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Dispatcher state
  const [intentInput, setIntentInput] = useState("");
  const [selectedTaskType, setSelectedTaskType] = useState<string>("");
  const [isDispatching, setIsDispatching] = useState(false);
  const [latestResponse, setLatestResponse] = useState<OrchestrationResponseData | null>(null);

  const fetchHubData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const baseUrl = process.env.NEXT_PUBLIC_API_BASE_URL || "https://pathmind-api.onrender.com";
      const personId = typeof window !== "undefined"
        ? (localStorage.getItem("pathmind_user_name")?.toLowerCase().replace(/\s+/g, "-") || "scholar-user")
        : "scholar-user";

      // 1. Fetch Agents Registry
      const agentRes = await fetch(`${baseUrl}/api/orchestrate/agents`);
      if (agentRes.ok) {
        const agentData = await agentRes.json();
        setAgents(agentData);
      }

      // 2. Fetch Traces
      const traceRes = await fetch(`${baseUrl}/api/orchestrate/traces`, {
        headers: { "X-Person-ID": personId }
      });
      if (traceRes.ok) {
        const traceData = await traceRes.json();
        setTraces(traceData);
      }

      // 3. Fetch Pending Action Proposals
      const propRes = await fetch(`${baseUrl}/api/orchestrate/proposals?status=PENDING`, {
        headers: { "X-Person-ID": personId }
      });
      if (propRes.ok) {
        const propData = await propRes.json();
        setProposals(propData);
      }
    } catch (err) {
      console.error(err);
      setError("Unable to connect to live orchestrator service.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchHubData();
  }, [fetchHubData]);

  const handleDispatch = async (e?: React.FormEvent, customIntent?: string, customType?: string) => {
    if (e) e.preventDefault();
    const intent = (customIntent !== undefined ? customIntent : intentInput).trim();
    if (!intent) return;

    const taskType = customType !== undefined ? customType : selectedTaskType;
    if (customIntent) setIntentInput(customIntent);
    if (customType) setSelectedTaskType(customType);

    setIsDispatching(true);
    try {
      const baseUrl = process.env.NEXT_PUBLIC_API_BASE_URL || "https://pathmind-api.onrender.com";
      const personId = typeof window !== "undefined"
        ? (localStorage.getItem("pathmind_user_name")?.toLowerCase().replace(/\s+/g, "-") || "scholar-user")
        : "scholar-user";

      const res = await fetch(`${baseUrl}/api/orchestrate`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-Person-ID": personId
        },
        body: JSON.stringify({
          intent,
          task_type: taskType || undefined,
          payload: {}
        })
      });

      if (res.ok) {
        const data = await res.json();
        setLatestResponse(data);
        fetchHubData();
      }
    } catch (err) {
      console.error(err);
    } finally {
      setIsDispatching(false);
    }
  };

  const handleApproveProposal = async (proposalId: string) => {
    try {
      const baseUrl = process.env.NEXT_PUBLIC_API_BASE_URL || "https://pathmind-api.onrender.com";
      const personId = typeof window !== "undefined"
        ? (localStorage.getItem("pathmind_user_name")?.toLowerCase().replace(/\s+/g, "-") || "scholar-user")
        : "scholar-user";

      const res = await fetch(`${baseUrl}/api/orchestrate/proposals/${proposalId}/approve`, {
        method: "POST",
        headers: { "X-Person-ID": personId }
      });

      if (res.ok) {
        setProposals(prev => prev.filter(p => p.proposal_id !== proposalId));
        fetchHubData();
      }
    } catch (err) {
      console.error(err);
    }
  };

  const handleRejectProposal = async (proposalId: string) => {
    try {
      const baseUrl = process.env.NEXT_PUBLIC_API_BASE_URL || "https://pathmind-api.onrender.com";
      const personId = typeof window !== "undefined"
        ? (localStorage.getItem("pathmind_user_name")?.toLowerCase().replace(/\s+/g, "-") || "scholar-user")
        : "scholar-user";

      const res = await fetch(`${baseUrl}/api/orchestrate/proposals/${proposalId}/reject`, {
        method: "POST",
        headers: { "X-Person-ID": personId }
      });

      if (res.ok) {
        setProposals(prev => prev.filter(p => p.proposal_id !== proposalId));
        fetchHubData();
      }
    } catch (err) {
      console.error(err);
    }
  };

  return (
    <div className="w-full max-w-6xl mx-auto px-4 py-8 space-y-10">
      {/* Header */}
      <div className="border-b border-stone-200 pb-6 flex flex-col md:flex-row md:items-end justify-between gap-4">
        <div>
          <div className="flex items-center space-x-2 text-stone-600 text-xs font-mono uppercase tracking-widest mb-1">
            <Cpu className="w-3.5 h-3.5 text-stone-700" />
            <span>Guidance Coordinator</span>
          </div>
          <h1 className="text-3xl font-serif tracking-tight text-stone-900">
            Guidance Coordinator: How PATHMIND Reasons &amp; Coordinates Plans
          </h1>
          <p className="text-stone-600 text-sm mt-1 max-w-2xl">
            Transparently coordinates specialized guidance modules to evaluate opportunities, diagnose learning blockers, adapt your roadmap, and suggest verified next steps.
          </p>
        </div>

        <div className="flex items-center space-x-2 text-xs font-mono text-stone-700 bg-stone-100 border border-stone-200 px-3 py-1.5 rounded">
          <ShieldCheck className="w-4 h-4 text-emerald-700" />
          <span>{agents.length > 0 ? `${agents.length} Guidance Modules Active` : "Guidance Modules Active"} • Private Profile</span>
        </div>
      </div>

      {error && (
        <div className="p-4 rounded-lg bg-amber-50 border border-amber-200 text-amber-800 text-xs font-mono">
          {error}
        </div>
      )}

      {/* Task Dispatcher Console */}
      <div className="bg-white rounded-xl border border-stone-200 p-6 shadow-xs space-y-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-2 text-xs font-mono uppercase text-stone-700 font-semibold">
            <Play className="w-3.5 h-3.5 text-emerald-600" />
            <span>Ask Guidance Coordinator</span>
          </div>
          <span className="text-[11px] font-mono text-stone-500">
            Multi-Perspective Guidance Analysis
          </span>
        </div>

        <form onSubmit={(e) => handleDispatch(e)} className="relative">
          <input
            type="text"
            placeholder="Ask a question or describe a challenge (e.g., 'Should I apply for this ML fellowship?', 'Diagnose my current blocker in today\'s plan')"
            value={intentInput}
            onChange={(e) => setIntentInput(e.target.value)}
            className="w-full text-xs font-sans pl-4 pr-24 py-3 border border-stone-200 rounded-lg focus:outline-none focus:border-stone-400 bg-stone-50/60"
          />
          <button
            type="submit"
            disabled={isDispatching}
            className="absolute right-2 top-2 px-4 py-1.5 rounded text-xs font-mono bg-stone-900 text-white hover:bg-stone-800 transition-colors"
          >
            {isDispatching ? "Analyzing..." : "Ask Coordinator"}
          </button>
        </form>

        {/* Preset quick actions */}
        <div className="flex flex-wrap items-center gap-2 pt-1">
          <span className="text-[11px] font-mono text-stone-500">Quick Presets:</span>
          {[
            { label: "Evaluate Opportunities & Plan", intent: "Should I apply for verified ML internships?", type: "OPPORTUNITY_MATCH" },
            { label: "Diagnose Learning Blocker", intent: "I am stuck on this task blocker in my current plan", type: "NEXT_ACTION" },
            { label: "Propose Roadmap Adaptation", intent: "Adapt my roadmap towards Autonomous Perception Systems", type: "ROADMAP_ADAPTATION" },
            { label: "Recall Past Breakthrough", intent: "What worked when I struggled with recursion?", type: "MEMORY_RECALL" }
          ].map((preset, i) => (
            <button
              key={i}
              type="button"
              onClick={() => handleDispatch(undefined, preset.intent, preset.type)}
              className="text-[11px] font-mono text-stone-600 hover:text-stone-900 bg-stone-100 hover:bg-stone-200/80 px-2 py-0.5 rounded transition-colors"
            >
              {preset.label}
            </button>
          ))}
        </div>

        {/* Dispatch Result Card */}
        {latestResponse && (
          <motion.div
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            className="mt-4 p-5 rounded-lg border border-stone-200 bg-stone-50 space-y-4"
          >
            <div className="flex items-center justify-between border-b border-stone-200/80 pb-3">
              <div className="flex items-center space-x-2">
                <span className={`text-[10px] font-mono px-2 py-0.5 rounded border ${
                  latestResponse.status === "SUCCESS"
                    ? "bg-emerald-50 text-emerald-800 border-emerald-200"
                    : latestResponse.status === "WAITING_FOR_USER_APPROVAL"
                    ? "bg-amber-50 text-amber-900 border-amber-200"
                    : "bg-stone-200 text-stone-700 border-stone-300"
                }`}>
                  {latestResponse.status.replace(/_/g, " ")}
                </span>
                <span className="text-xs font-mono text-stone-500">
                  Task: {latestResponse.task_type} • Duration: {latestResponse.trace.total_duration_ms}ms
                </span>
              </div>
              <span className="text-[10px] font-mono text-stone-400">
                ID: {latestResponse.workflow_id}
              </span>
            </div>

            {/* Answer */}
            <div className="space-y-1">
              <span className="text-[10px] font-mono uppercase text-stone-500 tracking-wider">
                Personalized Guidance Summary
              </span>
              <p className="text-sm font-sans text-stone-800 leading-relaxed font-normal">
                {latestResponse.final_answer}
              </p>
            </div>

            {/* Pipeline Step Breakdown */}
            <div className="space-y-2 pt-2 border-t border-stone-200/80">
              <span className="text-[10px] font-mono uppercase text-stone-500 tracking-wider block">
                Guidance Perspectives Consulted ({latestResponse.trace.steps.length})
              </span>
              <div className="space-y-1.5">
                {latestResponse.trace.steps.map((step, i) => (
                  <div key={i} className="flex items-center justify-between p-2.5 rounded bg-white border border-stone-200/80 text-xs">
                    <div className="flex items-center space-x-2">
                      <span className="font-mono text-stone-400 text-[10px]">{i + 1}.</span>
                      <span className="font-serif font-medium text-stone-900">{step.agent_id}</span>
                      <span className="text-stone-500 font-sans text-[11px]">— {step.output_summary}</span>
                    </div>
                    <div className="flex items-center space-x-2">
                      <span className="font-mono text-[10px] text-stone-400">{step.duration_ms}ms</span>
                      <span className="text-[10px] font-mono text-emerald-700">✓ {step.status}</span>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </motion.div>
        )}
      </div>

      {/* Approval Queue (High-Impact Mutation Gates) */}
      {proposals.length > 0 && (
        <div className="border border-amber-200 rounded-xl p-6 bg-amber-50/40 space-y-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-2 text-xs font-mono text-amber-900 font-semibold uppercase">
              <AlertTriangle className="w-4 h-4 text-amber-700" />
              <span>Pending Recommendations Requiring Your Review ({proposals.length})</span>
            </div>
            <span className="text-xs font-mono text-amber-700">Requires Your Confirmation</span>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {proposals.map((prop) => (
              <div key={prop.proposal_id} className="bg-white rounded-lg border border-amber-200 p-4 space-y-3 shadow-xs">
                <div className="flex items-center justify-between">
                  <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-amber-100 text-amber-900">
                    {prop.action_type.replace(/_/g, " ")}
                  </span>
                  <span className="text-[10px] font-mono text-stone-400">{prop.proposal_id}</span>
                </div>
                <div className="space-y-1">
                  <p className="text-xs font-sans text-stone-800 font-medium">{prop.reason}</p>
                  <pre className="text-[10px] font-mono bg-stone-50 p-2 rounded border border-stone-200 text-stone-600 overflow-x-auto">
                    {JSON.stringify(prop.proposed_change, null, 2)}
                  </pre>
                </div>
                <div className="flex items-center justify-end space-x-2 pt-2 border-t border-stone-100">
                  <button
                    onClick={() => handleRejectProposal(prop.proposal_id)}
                    className="text-xs font-mono px-3 py-1 rounded bg-stone-100 text-stone-700 hover:bg-stone-200 transition-colors"
                  >
                    Reject
                  </button>
                  <button
                    onClick={() => handleApproveProposal(prop.proposal_id)}
                    className="text-xs font-mono px-3 py-1 rounded bg-stone-900 text-white hover:bg-stone-800 transition-colors"
                  >
                    Approve & Apply
                  </button>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Agent Registry Grid */}
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-xl font-serif text-stone-900">Active Guidance Modules</h2>
            <p className="text-xs text-stone-500 font-mono">Specialized analysis modules that safeguard your plan, verify evidence, and discover opportunities.</p>
          </div>
          <span className="text-xs font-mono text-stone-500">{agents.length > 0 ? `${agents.length} Active Modules` : "Coordinated Modules"}</span>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {agents.map((agent) => (
            <div
              key={agent.agent_id}
              className="bg-white border border-stone-200 rounded-xl p-5 shadow-xs space-y-3 flex flex-col justify-between"
            >
              <div className="space-y-2">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-serif font-semibold text-stone-900">{agent.name}</span>
                  <span className="text-[10px] font-mono text-stone-400">{agent.agent_id}</span>
                </div>
                <p className="text-xs text-stone-600 font-sans leading-relaxed">{agent.purpose}</p>
              </div>

              <div className="pt-3 border-t border-stone-100 space-y-1.5 text-[11px] font-mono">
                <div className="text-stone-500 flex items-start space-x-1.5">
                  <Wrench className="w-3 h-3 text-stone-400 shrink-0 mt-0.5" />
                  <span className="truncate">Capabilities: {agent.allowed_tools.join(", ")}</span>
                </div>
                <div className="text-rose-800 flex items-start space-x-1.5 bg-rose-50/60 p-1.5 rounded border border-rose-100">
                  <Ban className="w-3 h-3 text-rose-500 shrink-0 mt-0.5" />
                  <span className="truncate">Safeguards: {agent.forbidden_operations.join(", ")}</span>
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Recent Execution Traces */}
      <div className="border-t border-stone-200 pt-8 space-y-4">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-lg font-serif text-stone-900">Recent Guidance History &amp; Reasoning Steps</h2>
            <p className="text-xs text-stone-500 font-mono">Transparent history of how your guidance and recommendations were formed.</p>
          </div>
          <span className="text-xs font-mono text-stone-500">{traces.length} Consultations</span>
        </div>

        {loading ? (
          <div className="p-8 text-center text-stone-500 font-serif italic text-sm">
            Loading guidance history...
          </div>
        ) : traces.length > 0 ? (
          <div className="space-y-2">
            {traces.slice().reverse().map((t) => (
              <div
                key={t.workflow_id}
                className="bg-white border border-stone-200 rounded-lg p-3.5 flex flex-col md:flex-row md:items-center justify-between gap-3 text-xs"
              >
                <div className="space-y-1">
                  <div className="flex items-center space-x-2">
                    <span className="font-serif font-medium text-stone-900">{t.task_type}</span>
                    <span className={`text-[10px] font-mono px-2 py-0.2 rounded border ${
                      t.status === "SUCCESS"
                        ? "bg-emerald-50 text-emerald-800 border-emerald-200"
                        : t.status === "WAITING_FOR_USER_APPROVAL"
                        ? "bg-amber-50 text-amber-900 border-amber-200"
                        : "bg-stone-100 text-stone-700 border-stone-200"
                    }`}>
                      {t.status.replace(/_/g, " ")}
                    </span>
                    <span className="font-mono text-[10px] text-stone-400">{t.workflow_id}</span>
                  </div>
                  <div className="flex items-center space-x-1 text-[11px] font-mono text-stone-500">
                    <span>Pipeline: {t.agents_invoked.join(" → ")}</span>
                  </div>
                </div>

                <div className="flex items-center space-x-3 text-stone-500 font-mono text-[11px]">
                  <span>{t.total_duration_ms}ms</span>
                  <span>{new Date(t.started_at).toLocaleTimeString()}</span>
                </div>
              </div>
            ))}
          </div>
        ) : (
          <div className="p-6 text-center border border-dashed border-stone-300 rounded-lg bg-stone-50/50 text-stone-500 text-xs font-mono">
            No guidance history recorded in this session yet. Ask a question above to consult your guidance coordinator.
          </div>
        )}
      </div>
    </div>
  );
}
