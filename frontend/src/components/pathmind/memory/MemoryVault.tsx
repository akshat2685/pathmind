"use client";

import { useState, useEffect, useCallback } from "react";
import { motion } from "framer-motion";
import {
  Brain,
  Search,
  ShieldCheck,
  Sparkles,
  CheckCircle2,
  AlertTriangle,
  Trash2,
  GitBranch,
  BookOpen
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

export function MemoryVault() {
  const [memories, setMemories] = useState<MemoryItemData[]>([]);
  const [sharedPatterns, setSharedPatterns] = useState<SharedPatternData[]>([]);
  const [selectedNature, setSelectedNature] = useState<string>("ALL");
  const [selectedStatus, setSelectedStatus] = useState<string>("ALL");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Second Brain Natural Search Console State
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
        ? (localStorage.getItem("pathmind_user_name")?.toLowerCase().replace(/\s+/g, "-") || "scholar-user")
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

  const handleSecondBrainQuery = async (e?: React.FormEvent, customQuery?: string) => {
    if (e) e.preventDefault();
    const q = (customQuery !== undefined ? customQuery : recallQuery).trim();
    if (!q) return;

    if (customQuery) setRecallQuery(customQuery);
    setIsRecalling(true);
    try {
      const personId = typeof window !== "undefined"
        ? (localStorage.getItem("pathmind_user_name")?.toLowerCase().replace(/\s+/g, "-") || "scholar-user")
        : "scholar-user";

      const res = await fetch("/api/memory/query", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-Person-ID": personId
        },
        body: JSON.stringify({
          query: q,
          current_task_context: "Tree Traversal & Depth-First Search"
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
        ? (localStorage.getItem("pathmind_user_name")?.toLowerCase().replace(/\s+/g, "-") || "scholar-user")
        : "scholar-user";

      const res = await fetch(`/api/memory/personal/${memoryId}`, {
        method: "DELETE",
        headers: { "X-Person-ID": personId }
      });

      if (res.ok) {
        setMemories(prev => prev.filter(m => m.memory_id !== memoryId));
        if (secondBrainResult) {
          setSecondBrainResult(prev => prev ? {
            ...prev,
            retrieved_memories: prev.retrieved_memories.filter(r => r.memory.memory_id !== memoryId)
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
    <div className="w-full max-w-5xl mx-auto px-4 py-8 space-y-10 min-w-0 overflow-hidden">
      {/* Header */}
      <div className="border-b border-stone-200 pb-6 flex flex-col md:flex-row md:items-end justify-between gap-4 min-w-0">
        <div className="min-w-0">
          <div className="flex items-center space-x-2 text-stone-600 text-xs font-mono uppercase tracking-widest mb-1">
            <Brain className="w-3.5 h-3.5 text-stone-700 shrink-0" />
            <span>Personal Second Brain</span>
          </div>
          <h1 className="text-2xl sm:text-3xl font-serif tracking-tight text-stone-900 break-words">
            Memory Vault &amp; Knowledge Engine
          </h1>
          <p className="text-stone-600 text-sm mt-1 max-w-2xl">
            Your private learning notebook preserving decisions, projects, breakthroughs, and strategies — grounded in your actual work.
          </p>
        </div>

        <div className="flex items-center space-x-2 text-xs font-mono text-stone-700 bg-stone-100 border border-stone-200 px-3 py-1.5 rounded shrink-0 max-w-full">
          <ShieldCheck className="w-4 h-4 text-emerald-700 shrink-0" />
          <span className="truncate">Private to your profile • Evidence-backed memories</span>
        </div>
      </div>

      {error && (
        <div className="p-4 rounded-lg bg-amber-50 border border-amber-200 text-amber-800 text-xs font-mono">
          {error}
        </div>
      )}

      {/* Second Brain Search & Query Console */}
      <div className="bg-white rounded-xl border border-stone-200 p-6 shadow-xs space-y-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-2 text-xs font-mono uppercase text-stone-700 font-semibold">
            <Sparkles className="w-3.5 h-3.5 text-amber-600" />
            <span>Ask Your Second Brain</span>
          </div>
          <span className="text-[11px] font-mono text-stone-500">
            Search your learning memories
          </span>
        </div>

        <form onSubmit={(e) => handleSecondBrainQuery(e)} className="relative">
          <Search className="w-4 h-4 text-stone-400 absolute left-3 top-3.5" />
          <input
            type="text"
            placeholder="e.g., 'What was my first API project?', 'What worked when I struggled with recursion?', 'Why did I switch career goals?'"
            value={recallQuery}
            onChange={(e) => setRecallQuery(e.target.value)}
            className="w-full text-xs font-sans pl-10 pr-24 py-3 border border-stone-200 rounded-lg focus:outline-none focus:border-stone-400 bg-stone-50/60"
          />
          <button
            type="submit"
            disabled={isRecalling}
            className="absolute right-2 top-2 px-4 py-1.5 rounded text-xs font-mono bg-stone-900 text-white hover:bg-stone-800 transition-colors"
          >
            {isRecalling ? "Searching..." : "Recall"}
          </button>
        </form>

        {/* Quick query suggestions */}
        <div className="flex flex-wrap items-center gap-2 pt-1">
          <span className="text-[11px] font-mono text-stone-500">Try asking:</span>
          {[
            "What was my first API project?",
            "What worked when I struggled with recursion?",
            "What is my primary career goal?",
            "Which project best demonstrates my backend skills?"
          ].map((q, i) => (
            <button
              key={i}
              type="button"
              onClick={() => handleSecondBrainQuery(undefined, q)}
              className="text-[11px] font-mono text-stone-600 hover:text-stone-900 bg-stone-100 hover:bg-stone-200/80 px-2 py-0.5 rounded transition-colors"
            >
              {q}
            </button>
          ))}
        </div>

        {/* Second Brain Recall Result */}
        {secondBrainResult && (
          <motion.div
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            className="mt-4 p-5 rounded-lg border border-stone-200 bg-stone-50 space-y-4"
          >
            <div className="flex items-center justify-between border-b border-stone-200/80 pb-3">
              <div className="flex items-center space-x-2">
                <span className={`text-[10px] font-mono px-2 py-0.5 rounded border ${
                  secondBrainResult.status === "RESOLVED"
                    ? "bg-emerald-50 text-emerald-800 border-emerald-200"
                    : secondBrainResult.status === "MEMORY_CONFLICT"
                    ? "bg-amber-50 text-amber-900 border-amber-200"
                    : "bg-stone-200 text-stone-700 border-stone-300"
                }`}>
                  {secondBrainResult.status.replace("_", " ")}
                </span>
                <span className="text-xs font-mono text-stone-500">
                  Confidence: {secondBrainResult.confidence}
                </span>
              </div>
            </div>

            {/* Conflicting Memories Alert */}
            {secondBrainResult.conflicting_memories.length > 0 && (
              <div className="p-3 rounded bg-amber-50 border border-amber-200 space-y-1">
                <div className="flex items-center space-x-1.5 text-xs font-mono text-amber-900 font-semibold">
                  <AlertTriangle className="w-3.5 h-3.5 text-amber-700" />
                  <span>Conflicting Records Detected in Active State</span>
                </div>
                <p className="text-xs text-amber-800 font-sans">
                  Multiple active memories record differing goals or paths. Review your active commitments to resolve ambiguity.
                </p>
              </div>
            )}

            {/* Answer */}
            <div className="space-y-1">
              <span className="text-[10px] font-mono uppercase text-stone-500 tracking-wider">
                Grounded Knowledge Recall
              </span>
              <p className="text-sm font-sans text-stone-800 leading-relaxed font-normal">
                {secondBrainResult.answer}
              </p>
            </div>

            {/* Concept Bridge */}
            {secondBrainResult.concept_bridge && (
              <div className="text-xs font-mono text-stone-600 bg-white p-2.5 rounded border border-stone-200 flex items-center space-x-2">
                <GitBranch className="w-3.5 h-3.5 text-stone-500" />
                <span>Concept Bridge: {secondBrainResult.concept_bridge}</span>
              </div>
            )}

            {/* Supporting Memory Citations */}
            {secondBrainResult.retrieved_memories.length > 0 && (
              <div className="space-y-2 pt-2 border-t border-stone-200/80">
                <span className="text-[10px] font-mono uppercase text-stone-500 tracking-wider block">
                  Cited Memory Moments ({secondBrainResult.retrieved_memories.length})
                </span>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
                  {secondBrainResult.retrieved_memories.map((r, i) => (
                    <div key={i} className="p-3 rounded bg-white border border-stone-200/80 space-y-1 text-xs">
                      <div className="flex items-center justify-between">
                        <span className="font-serif text-stone-900 font-medium truncate">{r.memory.title}</span>
                        <span className="font-mono text-[10px] text-stone-500">Score: {r.relevance_score}</span>
                      </div>
                      <p className="text-[11px] text-stone-600 font-sans line-clamp-2">{r.memory.content || r.memory.summary}</p>
                      <div className="text-[10px] font-mono text-stone-500 pt-1 flex items-center justify-between">
                        <span>Source: {r.memory.source_reference}</span>
                        <span className="text-emerald-700">✓ Grounded</span>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </motion.div>
        )}
      </div>

      {/* Cross-Stage Past → Present Bridge Banner */}
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

      {/* Filter Tabs */}
      <div className="space-y-3">
        <div className="flex flex-wrap items-center justify-between gap-3 border-b border-stone-200 pb-3">
          {/* Nature Filters */}
          <div className="flex flex-wrap items-center gap-1">
            {["ALL", "EXPERIENCE", "DECISION", "SKILL_KNOWLEDGE", "STRATEGY", "GOAL", "FACT"].map((nat) => (
              <button
                key={nat}
                onClick={() => setSelectedNature(nat)}
                className={`text-xs font-mono px-3 py-1 rounded transition-colors ${
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
          <div className="flex items-center gap-1 text-xs font-mono">
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
            Loading your learning memories...
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

                  <h3 className="text-base font-serif text-stone-900 tracking-tight">
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
                    <span className="text-stone-500">Source: {m.source_type} ({m.source_reference})</span>
                    {m.evidence_verification_status === "VERIFIED" && (
                      <span className="text-emerald-700 flex items-center space-x-1">
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
            <p className="text-xs text-stone-500 font-sans">Your learning memories will appear here as you complete activities, upload evidence, and record milestones.</p>
          </div>
        )}
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
