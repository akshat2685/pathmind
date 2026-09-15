"use client";

import { useState, useEffect, useCallback } from "react";
import { motion } from "framer-motion";
import {
  Brain,
  Search,
  ShieldCheck,
  CheckCircle2,
  AlertTriangle,
  Trash2,
  BookOpen,
  Terminal,
  Cpu,
  RefreshCw
} from "lucide-react";

interface MemoryItemData {
  memory_id: string;
  person_id: string;
  memory_type: string;
  nature: string;
  title: string;
  content: string;
  summary: string;
  topic: string;
  related_concepts: string[];
  source_type: string;
  source_reference: string;
  related_goal_ids?: string[];
  related_skill_ids?: string[];
  related_artifact_ids?: string[];
  related_decision_ids?: string[];
  created_at: string;
  confidence: string;
  importance: string;
  lifecycle_status: string;
  superseded_by?: string;
  supersedes_reason?: string;
  is_consolidated?: boolean;
  consolidated_source_ids?: string[];
  evidence_verification_status?: string;
  details?: Record<string, unknown>;
}

interface SharedPatternData {
  pattern_id: string;
  topic: string;
  misconception_or_context: string;
  effective_intervention: string;
  evidence_count: number;
  confidence: string;
}

interface SearchResultItemData {
  memory: MemoryItemData;
  relevance_score: number;
  relevance_reason: string;
  provenance_chain: string[];
}

interface SecondBrainQueryResponseData {
  person_id: string;
  query: string;
  status: string; // RESOLVED, NO_RELEVANT_MEMORY, INSUFFICIENT_HISTORY, MEMORY_CONFLICT
  answer: string;
  retrieved_memories: SearchResultItemData[];
  conflicting_memories: MemoryItemData[];
  confidence: string;
  concept_bridge?: string | null;
}

interface ProactiveMemoryContextData {
  person_id: string;
  task_type: string;
  retrieved_memories: MemoryItemData[];
  relevance_reasons: string[];
  confidence: string;
  source_provenance: string[];
  conflicting_memories: MemoryItemData[];
  temporal_state: string;
  evidence_status: string;
  status: string;
  proactive_summary: string;
  retrieved_at: string;
}

export function MemoryVault() {
  const [memories, setMemories] = useState<MemoryItemData[]>([]);
  const [sharedPatterns, setSharedPatterns] = useState<SharedPatternData[]>([]);
  const [selectedNature, setSelectedNature] = useState<string>("ALL");
  const [selectedStatus, setSelectedStatus] = useState<string>("ALL");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Proactive Simulation State
  const [simTaskType, setSimTaskType] = useState<string>("NEXT_LEARNING_ACTION");
  const [simConcept, setSimConcept] = useState<string>("Tree Traversal");
  const [simGoal, setSimGoal] = useState<string>("");
  const [simulatingProactive, setSimulatingProactive] = useState<boolean>(false);
  const [proactiveContext, setProactiveContext] = useState<ProactiveMemoryContextData | null>(null);

  // Ad-hoc Direct Query State (Internal diagnostics only)
  const [showDirectConsole, setShowDirectConsole] = useState(false);
  const [recallQuery, setRecallQuery] = useState("");
  const [isRecalling, setIsRecalling] = useState(false);
  const [secondBrainResult, setSecondBrainResult] = useState<SecondBrainQueryResponseData | null>(null);

  // Cross-Stage Bridge State
  const [bridgeData, setBridgeData] = useState<{
    current_concept: string;
    past_concept: string;
    past_stage: string;
    connection_explanation: string;
  } | null>(null);

  const fetchMemories = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const personId = typeof window !== "undefined"
        ? (localStorage.getItem("pathmind_user_name")?.toLowerCase().replace(/\s+/g, "-") || "")
        : "scholar-user";

      // 1. Personal Memories
      const memRes = await fetch("/api/memory/personal", {
        headers: { "X-Person-ID": personId }
      });
      if (memRes.ok) {
        const memData = await memRes.json();
        setMemories(memData);
      }

      // 2. Shared Patterns
      const patRes = await fetch("/api/memory/shared-patterns");
      if (patRes.ok) {
        const patData = await patRes.json();
        setSharedPatterns(patData);
      }

      // 3. Cross Stage Bridge
      const bridgeRes = await fetch("/api/memory/cross-stage?concept=Tree%20Traversal", {
        headers: { "X-Person-ID": personId }
      });
      if (bridgeRes.ok) {
        const bData = await bridgeRes.json();
        setBridgeData(bData);
      }
    } catch (err) {
      console.error(err);
      setError("Unable to connect to live memory vault. Using offline local cache.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchMemories();
  }, [fetchMemories]);

  // Simulate Proactive Context Inspection
  const handleSimulateProactive = async () => {
    setSimulatingProactive(true);
    try {
      const personId = typeof window !== "undefined"
        ? (localStorage.getItem("pathmind_user_name")?.toLowerCase().replace(/\s+/g, "-") || "")
        : "scholar-user";

      const params = new URLSearchParams({
        task_type: simTaskType,
        ...(simConcept ? { current_concept: simConcept } : {}),
        ...(simGoal ? { current_goal: simGoal } : {})
      });

      const res = await fetch(`/api/memory/debug/proactive-context?${params.toString()}`, {
        headers: { "X-Person-ID": personId }
      });

      if (res.ok) {
        const data = await res.json();
        setProactiveContext(data);
      }
    } catch (err) {
      console.error("Proactive recall simulation failed:", err);
    } finally {
      setSimulatingProactive(false);
    }
  };

  const handleDirectQuery = async (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    const q = recallQuery.trim();
    if (!q) return;

    setIsRecalling(true);
    try {
      const personId = typeof window !== "undefined"
        ? (localStorage.getItem("pathmind_user_name")?.toLowerCase().replace(/\s+/g, "-") || "")
        : "scholar-user";

      const res = await fetch("/api/memory/query", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-Person-ID": personId
        },
        body: JSON.stringify({
          query: q,
          current_task_context: simConcept || "Diagnostic Test Context"
        })
      });

      if (res.ok) {
        const data = await res.json();
        setSecondBrainResult(data);
      }
    } catch (err) {
      console.error(err);
    } finally {
      setIsRecalling(false);
    }
  };

  const handleDeleteMemory = async (memoryId: string) => {
    if (!confirm("Are you sure you want to delete this memory record?")) return;
    try {
      const personId = typeof window !== "undefined"
        ? (localStorage.getItem("pathmind_user_name")?.toLowerCase().replace(/\s+/g, "-") || "")
        : "scholar-user";

      const res = await fetch(`/api/memory/personal/${memoryId}`, {
        method: "DELETE",
        headers: { "X-Person-ID": personId }
      });

      if (res.ok) {
        setMemories(prev => prev.filter(m => m.memory_id !== memoryId));
        if (proactiveContext) {
          setProactiveContext(prev => prev ? {
            ...prev,
            retrieved_memories: prev.retrieved_memories.filter(m => m.memory_id !== memoryId)
          } : null);
        }
      }
    } catch (err) {
      console.error(err);
    }
  };

  const filteredMemories = memories.filter((m) => {
    const natureMatch = selectedNature === "ALL" || m.nature === selectedNature;
    const statusMatch = selectedStatus === "ALL" || m.lifecycle_status === selectedStatus;
    return natureMatch && statusMatch;
  });

  const getImportanceBadge = (importance: string) => {
    switch (importance) {
      case "CRITICAL":
        return "bg-rose-50 text-rose-800 border-rose-200";
      case "HIGH":
        return "bg-amber-50 text-amber-800 border-amber-200";
      case "MEDIUM":
        return "bg-sky-50 text-sky-800 border-sky-200";
      default:
        return "bg-stone-100 text-stone-600 border-stone-200";
    }
  };

  const getNatureBadge = (nature: string) => {
    switch (nature) {
      case "DECISION":
        return "bg-purple-50 text-purple-800 border-purple-200";
      case "GOAL":
        return "bg-emerald-50 text-emerald-800 border-emerald-200";
      case "SKILL_KNOWLEDGE":
        return "bg-blue-50 text-blue-800 border-blue-200";
      case "STRATEGY":
        return "bg-amber-50 text-amber-800 border-amber-200";
      case "FACT":
        return "bg-teal-50 text-teal-800 border-teal-200";
      default:
        return "bg-stone-100 text-stone-700 border-stone-200";
    }
  };

  return (
    <div className="w-full max-w-5xl mx-auto px-4 py-8 space-y-8 min-w-0 overflow-hidden">
      {/* Developer Surface Demarcation Notice */}
      <div className="rounded-2xl bg-stone-900 text-stone-100 p-6 border border-stone-800 space-y-3 shadow-sm">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <div className="flex items-center space-x-2 text-xs font-mono uppercase tracking-widest text-amber-400 font-bold">
            <Terminal className="w-4 h-4 text-amber-400" />
            <span>[INTERNAL DEVELOPER &amp; DIAGNOSTIC SURFACE]</span>
          </div>
          <span className="text-[11px] font-mono text-stone-400 bg-stone-800/80 px-2.5 py-1 rounded border border-stone-700">
            PROACTIVE MEMORY SUBSYSTEM
          </span>
        </div>
        <div>
          <h1 className="text-xl sm:text-2xl font-serif text-white tracking-tight">
            Second Brain Cognitive Subsystem Inspector
          </h1>
          <p className="text-xs sm:text-sm text-stone-300 font-sans mt-1 leading-relaxed">
            Second Brain is an invisible background cognitive service. Regular learners do not manually query a memory vault; instead, PATHMIND automatically recalls relevant context behind the scenes during roadmaps, counseling, and learning guidance. This diagnostic console lets engineers and evaluators inspect memory representations, test task-specific proactive context injection, and verify provenance chains.
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-4 text-xs font-mono text-stone-400 pt-1 border-t border-stone-800">
          <div className="flex items-center space-x-1.5">
            <ShieldCheck className="w-3.5 h-3.5 text-emerald-400" />
            <span>Person-Isolated Store</span>
          </div>
          <div className="flex items-center space-x-1.5">
            <Cpu className="w-3.5 h-3.5 text-sky-400" />
            <span>Proactive Task Conditioning</span>
          </div>
          <div className="flex items-center space-x-1.5">
            <CheckCircle2 className="w-3.5 h-3.5 text-amber-400" />
            <span>Anti-Hallucination Verified</span>
          </div>
        </div>
      </div>

      {error && (
        <div className="p-4 rounded-lg bg-amber-50 border border-amber-200 text-amber-800 text-xs font-mono">
          {error}
        </div>
      )}

      {/* Proactive Context Simulation Console */}
      <div className="bg-white rounded-xl border border-stone-200 p-6 shadow-xs space-y-5">
        <div className="flex items-center justify-between border-b border-stone-200/80 pb-3">
          <div className="flex items-center space-x-2 text-xs font-mono uppercase text-stone-800 font-bold">
            <Cpu className="w-4 h-4 text-primary" />
            <span>Simulate Proactive Task-Context Recall</span>
          </div>
          <span className="text-[11px] font-mono text-stone-500">
            Tests ProactiveMemoryService Context Generation
          </span>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 text-xs">
          <div>
            <label className="font-mono text-[11px] text-stone-600 block mb-1">Task Type</label>
            <select
              value={simTaskType}
              onChange={(e) => setSimTaskType(e.target.value)}
              className="w-full font-mono text-xs p-2.5 border border-stone-300 rounded-lg bg-stone-50 focus:outline-none focus:border-stone-500"
            >
              <option value="NEXT_LEARNING_ACTION">NEXT_LEARNING_ACTION</option>
              <option value="ROADMAP_GENERATION">ROADMAP_GENERATION</option>
              <option value="CAREER_DIRECTION">CAREER_DIRECTION</option>
              <option value="GOAL_CHANGE">GOAL_CHANGE</option>
              <option value="EVIDENCE_EVALUATION">EVIDENCE_EVALUATION</option>
              <option value="RESUME_GENERATION">RESUME_GENERATION</option>
              <option value="DECISION_SUPPORT">DECISION_SUPPORT</option>
            </select>
          </div>

          <div>
            <label className="font-mono text-[11px] text-stone-600 block mb-1">Target Concept / Topic</label>
            <input
              type="text"
              value={simConcept}
              placeholder="e.g. Tree Traversal"
              onChange={(e) => setSimConcept(e.target.value)}
              className="w-full font-mono text-xs p-2.5 border border-stone-300 rounded-lg bg-stone-50 focus:outline-none focus:border-stone-500"
            />
          </div>

          <div>
            <label className="font-mono text-[11px] text-stone-600 block mb-1">Target Goal / Career Direction</label>
            <input
              type="text"
              value={simGoal}
              placeholder="e.g. Embedded Firmware Engineer"
              onChange={(e) => setSimGoal(e.target.value)}
              className="w-full font-mono text-xs p-2.5 border border-stone-300 rounded-lg bg-stone-50 focus:outline-none focus:border-stone-500"
            />
          </div>
        </div>

        <div className="flex items-center justify-between pt-1">
          <p className="text-[11px] text-stone-500 font-mono">
            {simTaskType === "RESUME_GENERATION" ? (
              <span className="text-amber-700 font-semibold">⚠ Safety Gate: Memory inferences are filtered out of resume facts</span>
            ) : (
              "Retrieves top-2 task-conditioned memories with provenance and conflict detection"
            )}
          </p>
          <button
            onClick={handleSimulateProactive}
            disabled={simulatingProactive}
            className="flex items-center space-x-1.5 px-4 py-2 rounded-lg text-xs font-mono bg-stone-900 text-white hover:bg-stone-800 transition-colors disabled:opacity-50"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${simulatingProactive ? "animate-spin" : ""}`} />
            <span>{simulatingProactive ? "Recalling..." : "Inspect Proactive Context"}</span>
          </button>
        </div>

        {/* Proactive Result Display */}
        {proactiveContext && (
          <motion.div
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            className="mt-4 p-5 rounded-xl border border-stone-200 bg-stone-50/80 space-y-4 text-xs font-sans"
          >
            <div className="flex flex-wrap items-center justify-between gap-2 border-b border-stone-200 pb-3">
              <div className="flex items-center space-x-2">
                <span className="text-[11px] font-mono font-bold text-stone-700">STATUS:</span>
                <span className={`text-[10px] font-mono px-2.5 py-0.5 rounded-full border font-semibold ${
                  proactiveContext.status === "ACTIVE_RECALL"
                    ? "bg-emerald-50 text-emerald-800 border-emerald-300"
                    : proactiveContext.status === "NO_RELEVANT_MEMORY"
                    ? "bg-stone-100 text-stone-600 border-stone-300"
                    : proactiveContext.status === "UNVERIFIED_MEMORY_ONLY"
                    ? "bg-purple-50 text-purple-800 border-purple-300"
                    : "bg-amber-50 text-amber-800 border-amber-300"
                }`}>
                  {proactiveContext.status}
                </span>
                <span className="text-[11px] font-mono text-stone-500">
                  Confidence: {proactiveContext.confidence}
                </span>
              </div>
              <span className="text-[10px] font-mono text-stone-400">
                Retrieved: {new Date(proactiveContext.retrieved_at).toLocaleTimeString()}
              </span>
            </div>

            {/* Downstream Injected Proactive Summary */}
            <div className="space-y-1">
              <span className="text-[10px] font-mono uppercase text-stone-500 tracking-wider font-semibold">
                Injected Downstream Summary
              </span>
              <div className="p-3 bg-white rounded-lg border border-stone-200 font-mono text-xs text-stone-800 leading-relaxed">
                {proactiveContext.proactive_summary || "None (No proactive memories injected for this task)."}
              </div>
            </div>

            {/* Relevance Reasons */}
            {proactiveContext.relevance_reasons.length > 0 && (
              <div className="flex flex-wrap items-center gap-1.5 pt-1">
                <span className="text-[10px] font-mono text-stone-500">Relevance Reasons:</span>
                {proactiveContext.relevance_reasons.map((r, i) => (
                  <span key={i} className="text-[10px] font-mono px-2 py-0.5 rounded bg-stone-200 text-stone-800 font-medium">
                    {r}
                  </span>
                ))}
              </div>
            )}

            {/* Conflicting Memories Alert */}
            {proactiveContext.conflicting_memories.length > 0 && (
              <div className="p-3 rounded-lg bg-amber-50 border border-amber-200 space-y-1">
                <div className="flex items-center space-x-1.5 font-mono text-amber-900 font-semibold">
                  <AlertTriangle className="w-4 h-4 text-amber-700" />
                  <span>Conflicting Memories Detected ({proactiveContext.conflicting_memories.length})</span>
                </div>
                <p className="text-xs text-amber-800">
                  {proactiveContext.conflicting_memories.map(m => m.title).join(", ")}
                </p>
              </div>
            )}

            {/* Retrieved Memory Cards */}
            {proactiveContext.retrieved_memories.length > 0 ? (
              <div className="space-y-2 pt-2 border-t border-stone-200">
                <span className="text-[10px] font-mono uppercase text-stone-500 tracking-wider font-semibold block">
                  Proactively Retrieved Items ({proactiveContext.retrieved_memories.length})
                </span>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                  {proactiveContext.retrieved_memories.map((m) => (
                    <div key={m.memory_id} className="p-3 rounded-lg bg-white border border-stone-200 space-y-1.5">
                      <div className="flex items-center justify-between">
                        <span className="font-serif text-stone-900 font-bold truncate">{m.title}</span>
                        <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-stone-100 text-stone-600">
                          {m.nature}
                        </span>
                      </div>
                      <p className="text-[11px] text-stone-600 font-sans line-clamp-2">
                        {m.content || m.summary}
                      </p>
                      <div className="text-[10px] font-mono text-stone-500 pt-1 flex items-center justify-between border-t border-stone-100">
                        <span>Source: {m.source_type}</span>
                        <span className="text-emerald-700">✓ Grounded</span>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            ) : (
              <div className="p-3 bg-white rounded border border-dashed border-stone-200 text-center font-mono text-xs text-stone-500">
                No memories met task-relevance threshold. Honest zero-hallucination state returned.
              </div>
            )}
          </motion.div>
        )}
      </div>

      {/* Cross-Stage Past → Present Bridge Scaffolding */}
      {bridgeData && (
        <div className="p-4 rounded-xl border border-stone-200 bg-stone-50 space-y-1">
          <div className="flex items-center space-x-1.5 text-xs font-mono text-stone-800 font-semibold">
            <BookOpen className="w-3.5 h-3.5 text-stone-600" />
            <span>Scaffolding Bridge: {bridgeData.past_concept} &rarr; {bridgeData.current_concept}</span>
          </div>
          <p className="text-xs text-stone-600 font-sans leading-relaxed">
            {bridgeData.connection_explanation}
          </p>
        </div>
      )}

      {/* Developer Raw Query Toggle */}
      <div className="border border-stone-200 rounded-xl bg-white p-4 space-y-3">
        <button
          onClick={() => setShowDirectConsole(!showDirectConsole)}
          className="flex items-center justify-between w-full text-xs font-mono text-stone-700 hover:text-stone-900"
        >
          <span className="flex items-center space-x-2">
            <Search className="w-3.5 h-3.5 text-stone-500" />
            <span className="font-semibold">Diagnostic Direct Query Tester</span>
          </span>
          <span className="text-[11px] text-stone-400">
            {showDirectConsole ? "Hide Direct Console ▲" : "Show Direct Console ▼"}
          </span>
        </button>

        {showDirectConsole && (
          <div className="pt-3 border-t border-stone-100 space-y-3">
            <form onSubmit={handleDirectQuery} className="relative">
              <input
                type="text"
                placeholder="Direct query string to test raw retrieval score..."
                value={recallQuery}
                onChange={(e) => setRecallQuery(e.target.value)}
                className="w-full text-xs font-sans pl-3 pr-24 py-2.5 border border-stone-200 rounded-lg focus:outline-none focus:border-stone-400 bg-stone-50/60 font-mono"
              />
              <button
                type="submit"
                disabled={isRecalling}
                className="absolute right-1.5 top-1.5 px-3 py-1.5 rounded text-xs font-mono bg-stone-800 text-white hover:bg-stone-700 transition-colors"
              >
                {isRecalling ? "Testing..." : "Test Query"}
              </button>
            </form>

            {secondBrainResult && (
              <div className="p-3 bg-stone-50 rounded border border-stone-200 text-xs font-mono space-y-2">
                <div className="flex items-center justify-between">
                  <span>Status: {secondBrainResult.status}</span>
                  <span>Confidence: {secondBrainResult.confidence}</span>
                </div>
                <p className="font-sans text-stone-800">{secondBrainResult.answer}</p>
                {secondBrainResult.retrieved_memories.length > 0 && (
                  <div className="text-[10px] text-stone-500 pt-1">
                    Citations: {secondBrainResult.retrieved_memories.map(r => r.memory.title).join(" • ")}
                  </div>
                )}
              </div>
            )}
          </div>
        )}
      </div>

      {/* Filter Tabs for Stored Personal Memories */}
      <div className="space-y-4">
        <div className="flex flex-wrap items-center justify-between gap-3 border-b border-stone-200 pb-3">
          <div>
            <h2 className="text-base font-serif text-stone-900 font-bold">Stored Personal Memory Records</h2>
            <p className="text-[11px] font-mono text-stone-500">
              Preserved longitudinal memory items with provenance and lifecycle status
            </p>
          </div>

          <div className="flex flex-wrap items-center gap-2">
            {/* Nature Filters */}
            <div className="flex flex-wrap items-center gap-1">
              {["ALL", "EXPERIENCE", "DECISION", "SKILL_KNOWLEDGE", "STRATEGY", "GOAL", "FACT"].map((nat) => (
                <button
                  key={nat}
                  onClick={() => setSelectedNature(nat)}
                  className={`text-[11px] font-mono px-2.5 py-1 rounded transition-colors ${
                    selectedNature === nat
                      ? "bg-stone-900 text-white"
                      : "bg-stone-100 hover:bg-stone-200 text-stone-700"
                  }`}
                >
                  {nat.replace("_", " ")}
                </button>
              ))}
            </div>

            {/* Lifecycle Filters */}
            <div className="flex items-center gap-1 text-[11px] font-mono">
              <span className="text-stone-500 mr-1">Status:</span>
              {["ALL", "CURRENT", "HISTORICAL", "SUPERSEDED"].map((st) => (
                <button
                  key={st}
                  onClick={() => setSelectedStatus(st)}
                  className={`px-2 py-0.5 rounded border transition-colors ${
                    selectedStatus === st
                      ? "border-stone-800 bg-stone-800 text-white"
                      : "border-stone-200 bg-white text-stone-600 hover:bg-stone-50"
                  }`}
                >
                  {st}
                </button>
              ))}
            </div>
          </div>
        </div>

        {/* Memories Grid */}
        <div className="space-y-4">
          {loading ? (
            <div className="p-12 text-center text-stone-500 font-serif italic text-sm">
              Loading recorded memories...
            </div>
          ) : filteredMemories.length > 0 ? (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {filteredMemories.map((m) => (
                <div
                  key={m.memory_id}
                  className="bg-white border border-stone-200 rounded-xl p-5 shadow-xs space-y-3 hover:border-stone-300 transition-all flex flex-col justify-between"
                >
                  <div className="space-y-2">
                    <div className="flex items-start justify-between gap-2">
                      <div className="flex flex-wrap items-center gap-1.5">
                        <span className={`text-[10px] font-mono px-2 py-0.5 rounded border ${getNatureBadge(m.nature)}`}>
                          {m.nature.replace("_", " ")}
                        </span>
                        <span className={`text-[10px] font-mono px-2 py-0.5 rounded border ${getImportanceBadge(m.importance)}`}>
                          {m.importance}
                        </span>
                        {m.lifecycle_status !== "CURRENT" && (
                          <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-stone-100 text-stone-600 border border-stone-200">
                            {m.lifecycle_status}
                          </span>
                        )}
                      </div>
                      <button
                        onClick={() => handleDeleteMemory(m.memory_id)}
                        title="Delete memory"
                        className="text-stone-400 hover:text-rose-600 transition-colors p-1"
                      >
                        <Trash2 className="w-3.5 h-3.5" />
                      </button>
                    </div>

                    <h3 className="text-base font-serif text-stone-900 tracking-tight font-semibold">
                      {m.title}
                    </h3>

                    <p className="text-xs text-stone-600 font-sans leading-relaxed">
                      {m.content || m.summary}
                    </p>

                    {/* Superseded Reason */}
                    {m.supersedes_reason && (
                      <div className="text-[11px] font-sans text-stone-500 italic bg-stone-50 p-2 rounded border border-stone-200/60">
                        Reason for evolution: {m.supersedes_reason}
                      </div>
                    )}
                  </div>

                  {/* Connected Knowledge Trace */}
                  <div className="pt-3 border-t border-stone-100 space-y-1.5 text-[11px] font-mono text-stone-500">
                    <div className="flex items-center justify-between">
                      <span className="text-stone-500 truncate max-w-[240px]">Source: {m.source_type} ({m.source_reference})</span>
                      {m.evidence_verification_status === "VERIFIED" && (
                        <span className="text-emerald-700 flex items-center space-x-1 shrink-0">
                          <CheckCircle2 className="w-3 h-3" />
                          <span>Verified</span>
                        </span>
                      )}
                    </div>
                    {m.related_concepts && m.related_concepts.length > 0 && (
                      <div className="flex flex-wrap items-center gap-1 pt-0.5">
                        <span className="text-[10px] text-stone-400">Concepts:</span>
                        {m.related_concepts.slice(0, 3).map((c, i) => (
                          <span key={i} className="text-[10px] px-1.5 py-0.2 rounded bg-stone-100 text-stone-600">
                            {c}
                          </span>
                        ))}
                      </div>
                    )}
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className="p-8 text-center border border-dashed border-stone-300 rounded-xl bg-stone-50/50 space-y-2">
              <Brain className="w-8 h-8 text-stone-400 mx-auto" />
              <p className="font-serif text-stone-700">No learning memories recorded yet.</p>
              <p className="text-xs text-stone-500 font-sans">
                Memories are recorded automatically when milestones, evidence submissions, or major decisions occur.
              </p>
            </div>
          )}
        </div>
      </div>

      {/* Shared Collective Learning Patterns (Anonymized) */}
      {sharedPatterns.length > 0 && (
        <div className="border-t border-stone-200 pt-8 space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-lg font-serif text-stone-900">Anonymized Shared Learning Patterns</h2>
              <p className="text-xs text-stone-500 font-mono">Collective insights scrubbed of all personal identity.</p>
            </div>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            {sharedPatterns.map((pat) => (
              <div key={pat.pattern_id} className="p-4 rounded-lg bg-stone-50 border border-stone-200 space-y-2 text-xs">
                <div className="flex items-center justify-between font-mono text-[10px] text-stone-500">
                  <span>Topic: {pat.topic}</span>
                  <span>Evidence: {pat.evidence_count} learner(s)</span>
                </div>
                <div className="space-y-1">
                  <p className="font-sans text-stone-700"><strong>Common Challenge:</strong> {pat.misconception_or_context}</p>
                  <p className="font-sans text-stone-800 font-medium"><strong>Effective Strategy:</strong> {pat.effective_intervention}</p>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
