"use client";

import { useState, useEffect } from "react";
import { motion } from "framer-motion";
import Link from "next/link";

interface MemoryItemData {
  memory_id: string;
  person_id: string;
  memory_type: "EPISODIC" | "SEMANTIC_LEARNING" | "PREFERENCE" | "STRATEGY" | "GOAL" | "EVIDENCE" | string;
  title: string;
  summary: string;
  topic: string;
  related_concepts: string[];
  created_at: string;
  confidence: "HIGH" | "MEDIUM" | "LOW" | string;
  importance: "LOW" | "MEDIUM" | "HIGH" | "CRITICAL" | string;
  lifecycle_status: "ACTIVE" | "UPDATED" | "SUPERSEDED" | "ARCHIVED" | string;
  source: string;
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

interface RecallResponseData {
  query: string;
  answer: string;
  grounded_concept_bridge?: string | null;
  confidence: string;
  recalled_memories: MemoryItemData[];
}

export function MemoryVault() {
  const [memories, setMemories] = useState<MemoryItemData[]>([]);
  const [sharedPatterns, setSharedPatterns] = useState<SharedPatternData[]>([]);
  const [selectedType, setSelectedType] = useState<string>("ALL");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Natural Recall Console State
  const [recallQuery, setRecallQuery] = useState("");
  const [isRecalling, setIsRecalling] = useState(false);
  const [recallResult, setRecallResult] = useState<RecallResponseData | null>(null);

  // Cross-Stage Bridge State
  const [bridgeData, setBridgeData] = useState<{
    current_concept: string;
    past_concept: string;
    past_stage: string;
    connection_explanation: string;
  } | null>(null);

  const fetchMemories = async () => {
    setLoading(true);
    setError(null);
    try {
      const baseUrl = process.env.NEXT_PUBLIC_API_BASE_URL || "https://pathmind-api.onrender.com";
      const personId = typeof window !== "undefined"
        ? (localStorage.getItem("pathmind_user_name")?.toLowerCase().replace(/\s+/g, "-") || "scholar-user")
        : "scholar-user";

      // 1. Personal Memories
      const memRes = await fetch(`${baseUrl}/api/memory/personal`, {
        headers: { "X-Person-ID": personId }
      });
      if (memRes.ok) {
        const memData = await memRes.json();
        setMemories(memData);
      }

      // 2. Shared Patterns
      const patRes = await fetch(`${baseUrl}/api/memory/shared-patterns`);
      if (patRes.ok) {
        const patData = await patRes.json();
        setSharedPatterns(patData);
      }

      // 3. Cross Stage Bridge
      const bridgeRes = await fetch(`${baseUrl}/api/memory/cross-stage?concept=Tree%20Traversal`, {
        headers: { "X-Person-ID": personId }
      });
      if (bridgeRes.ok) {
        const bData = await bridgeRes.json();
        setBridgeData(bData);
      }
    } catch (err) {
      console.error(err);
      setError("Unable to connect to live memory vault. Using offline demonstration cache.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchMemories();
  }, []);

  const handleNaturalRecall = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!recallQuery.trim()) return;

    setIsRecalling(true);
    try {
      const baseUrl = process.env.NEXT_PUBLIC_API_BASE_URL || "https://pathmind-api.onrender.com";
      const personId = typeof window !== "undefined"
        ? (localStorage.getItem("pathmind_user_name")?.toLowerCase().replace(/\s+/g, "-") || "scholar-user")
        : "scholar-user";

      const res = await fetch(`${baseUrl}/api/memory/recall`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-Person-ID": personId
        },
        body: JSON.stringify({
          person_id: personId,
          query: recallQuery.trim()
        })
      });

      if (res.ok) {
        const data = await res.json();
        setRecallResult(data);
      }
    } catch (err) {
      console.error(err);
    } finally {
      setIsRecalling(false);
    }
  };

  const handleDeleteMemory = async (memoryId: string) => {
    if (!confirm("Are you sure you want to delete this longitudinal memory?")) return;
    try {
      const baseUrl = process.env.NEXT_PUBLIC_API_BASE_URL || "https://pathmind-api.onrender.com";
      const personId = typeof window !== "undefined"
        ? (localStorage.getItem("pathmind_user_name")?.toLowerCase().replace(/\s+/g, "-") || "scholar-user")
        : "scholar-user";

      const res = await fetch(`${baseUrl}/api/memory/personal/${memoryId}`, {
        method: "DELETE",
        headers: { "X-Person-ID": personId }
      });

      if (res.ok) {
        setMemories(prev => prev.filter(m => m.memory_id !== memoryId));
      }
    } catch (err) {
      console.error(err);
    }
  };

  const filteredMemories = selectedType === "ALL"
    ? memories
    : memories.filter(m => m.memory_type === selectedType);

  const getImportanceBadge = (importance: string) => {
    switch (importance) {
      case "CRITICAL":
        return "bg-rose-950/40 text-rose-300 border-rose-700/60";
      case "HIGH":
        return "bg-amber-950/40 text-amber-300 border-amber-700/60";
      case "MEDIUM":
        return "bg-sky-950/40 text-sky-300 border-sky-700/60";
      default:
        return "bg-surface-container text-on-surface-variant border-outline";
    }
  };

  const getTypeIcon = (type: string) => {
    switch (type) {
      case "EPISODIC":
        return "history";
      case "SEMANTIC_LEARNING":
        return "school";
      case "PREFERENCE":
        return "favorite";
      case "STRATEGY":
        return "lightbulb";
      case "GOAL":
        return "flag";
      default:
        return "psychology";
    }
  };

  return (
    <div className="w-full max-w-5xl mx-auto px-4 py-8">
      {/* Header Banner */}
      <div className="text-center mb-8">
        <div className="inline-flex items-center gap-2 px-4 py-1.5 sketchy-chip text-secondary mb-3 bg-surface-container-low">
          <span className="material-symbols-outlined text-lg" style={{ fontVariationSettings: "'FILL' 1" }}>
            memory
          </span>
          <span className="font-note-handwritten text-xl font-medium">
            Chapter V: Memory Vault &amp; Collective Intelligence
          </span>
        </div>
        <h1 className="font-headline-lg text-4xl sm:text-5xl text-on-surface mb-2">
          Longitudinal Learning Memory
        </h1>
        <p className="font-note-handwritten text-2xl text-on-surface-variant max-w-2xl mx-auto">
          Private memories preserved for your personal evolution. Collective patterns scrubbed of all identity.
        </p>
      </div>

      {/* Cross-Stage Knowledge Transfer (Past → Present) Banner */}
      {bridgeData && (
        <motion.div
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          className="mb-8 p-5 sketch-border border-primary bg-primary-fixed/30"
        >
          <div className="flex items-start gap-3">
            <span className="material-symbols-outlined text-primary text-3xl shrink-0 mt-0.5" style={{ fontVariationSettings: "'FILL' 1" }}>
              auto_awesome
            </span>
            <div className="flex-1">
              <div className="flex items-center justify-between gap-2 flex-wrap mb-1">
                <span className="font-label-md text-xs font-bold uppercase tracking-wider text-primary">
                  Signature Capability: Past &rarr; Present Concept Bridge
                </span>
                <span className="font-note-handwritten text-xs text-on-surface-variant">
                  {bridgeData.past_stage} &bull; Verified Connection
                </span>
              </div>
              <h3 className="font-headline-sm text-lg text-on-surface font-bold mb-1">
                Connecting &ldquo;{bridgeData.past_concept}&rdquo; to &ldquo;{bridgeData.current_concept}&rdquo;
              </h3>
              <p className="font-body-md text-xs text-on-surface-variant leading-relaxed">
                {bridgeData.connection_explanation}
              </p>
            </div>
          </div>
        </motion.div>
      )}

      {/* Natural Memory Recall Sandbox ("Ask Your Memory") */}
      <div className="mb-10 p-6 sketch-border bg-surface-container-low/95">
        <div className="flex items-center gap-2 mb-2">
          <span className="material-symbols-outlined text-secondary text-2xl" style={{ fontVariationSettings: "'FILL' 1" }}>
            chat_bubble
          </span>
          <h3 className="font-headline-sm text-xl text-on-surface font-bold">
            Ask Your Memory Vault
          </h3>
        </div>
        <p className="font-note-handwritten text-base text-on-surface-variant mb-4">
          Query your historical breakthroughs, effective interventions, or goal changes naturally.
        </p>

        {/* Quick Question Chips */}
        <div className="flex flex-wrap gap-2 mb-4">
          <button
            type="button"
            onClick={() => setRecallQuery("How did I learn recursion and what worked for me?")}
            className="text-xs font-note-handwritten px-3 py-1 rounded border border-outline-variant/40 bg-surface-container hover:border-primary text-on-surface cursor-pointer"
          >
            &ldquo;How did I learn recursion?&rdquo;
          </button>
          <button
            type="button"
            onClick={() => setRecallQuery("What learning format works best for me?")}
            className="text-xs font-note-handwritten px-3 py-1 rounded border border-outline-variant/40 bg-surface-container hover:border-primary text-on-surface cursor-pointer"
          >
            &ldquo;What format works best for me?&rdquo;
          </button>
          <button
            type="button"
            onClick={() => setRecallQuery("How has my career goal evolved?")}
            className="text-xs font-note-handwritten px-3 py-1 rounded border border-outline-variant/40 bg-surface-container hover:border-primary text-on-surface cursor-pointer"
          >
            &ldquo;How has my goal evolved?&rdquo;
          </button>
        </div>

        <form onSubmit={handleNaturalRecall} className="flex gap-2">
          <input
            type="text"
            value={recallQuery}
            onChange={(e) => setRecallQuery(e.target.value)}
            placeholder="Ask a question about your learning history..."
            className="flex-1 hand-drawn-input text-xs px-3 py-2 bg-surface-container"
          />
          <button
            type="submit"
            disabled={!recallQuery.trim() || isRecalling}
            className="ink-wash-btn-primary px-6 py-2 text-sm flex items-center gap-1.5 cursor-pointer disabled:opacity-50"
          >
            <span>{isRecalling ? "Searching..." : "Recall"}</span>
            <span className="material-symbols-outlined text-sm">search</span>
          </button>
        </form>

        {/* Recall Answer Card */}
        {recallResult && (
          <motion.div
            initial={{ opacity: 0, y: 5 }}
            animate={{ opacity: 1, y: 0 }}
            className="mt-4 p-4 rounded bg-surface-container border border-outline-variant/40"
          >
            <div className="flex items-center justify-between mb-2">
              <span className="font-bold text-xs uppercase text-primary">Grounded Recall Response:</span>
              <span className="text-[10px] uppercase font-mono text-outline">{recallResult.confidence} Confidence</span>
            </div>
            <p className="font-body-md text-xs text-on-surface leading-relaxed mb-3">
              {recallResult.answer}
            </p>
            {recallResult.grounded_concept_bridge && (
              <div className="text-[11px] p-2 rounded bg-surface-container-high border border-primary/30 text-primary font-headline-sm">
                Bridge: {recallResult.grounded_concept_bridge}
              </div>
            )}
          </motion.div>
        )}
      </div>

      {/* Category Tabs & Privacy Notice */}
      <div className="flex items-center justify-between flex-wrap gap-4 mb-6">
        <div className="flex flex-wrap gap-2">
          {["ALL", "EPISODIC", "SEMANTIC_LEARNING", "PREFERENCE", "STRATEGY", "GOAL"].map((cat) => (
            <button
              key={cat}
              type="button"
              onClick={() => setSelectedType(cat)}
              className={`px-3 py-1 text-xs font-headline-sm rounded transition-all cursor-pointer ${
                selectedType === cat
                  ? "bg-secondary text-on-secondary font-bold shadow-xs"
                  : "bg-surface-container-low text-on-surface-variant hover:text-on-surface border border-outline-variant/40"
              }`}
            >
              {cat.replace("_", " ")}
            </button>
          ))}
        </div>

        <span className="font-note-handwritten text-xs text-on-surface-variant flex items-center gap-1">
          <span className="material-symbols-outlined text-sm text-emerald-400">shield</span>
          <span>Private Person Memory (Strictly Isolated)</span>
        </span>
      </div>

      {loading && (
        <div className="text-center py-16 flex flex-col items-center">
          <span className="material-symbols-outlined text-4xl text-secondary animate-spin mb-3">
            progress_activity
          </span>
          <h3 className="font-headline-sm text-xl text-on-surface">Accessing Longitudinal Memory...</h3>
        </div>
      )}

      {error && !loading && (
        <div className="p-4 sketch-border border-amber-600 bg-amber-950/20 text-on-surface text-center mb-8 text-xs">
          <p>{error}</p>
        </div>
      )}

      {/* Personal Memory Cards Grid */}
      {!loading && filteredMemories.length > 0 && (
        <div className="grid md:grid-cols-2 gap-6 mb-12">
          {filteredMemories.map((mem) => (
            <div
              key={mem.memory_id}
              className="sketch-border p-5 bg-surface-container-low/90 flex flex-col justify-between hover:bg-surface-container-low transition-colors"
            >
              <div>
                {/* Card Top: Type & Badges */}
                <div className="flex items-center justify-between gap-2 mb-2">
                  <span className="font-note-handwritten text-xs text-secondary flex items-center gap-1">
                    <span className="material-symbols-outlined text-sm">{getTypeIcon(mem.memory_type)}</span>
                    <span>{mem.memory_type.replace("_", " ")}</span>
                  </span>
                  <div className="flex items-center gap-1.5">
                    <span className={`text-[9px] font-bold px-1.5 py-0.2 rounded border ${getImportanceBadge(mem.importance)}`}>
                      {mem.importance}
                    </span>
                    <span className="text-[9px] font-bold px-1.5 py-0.2 rounded border border-outline-variant/40 text-on-surface-variant">
                      {mem.confidence}
                    </span>
                  </div>
                </div>

                {/* Title & Summary */}
                <h3 className="font-headline-sm text-lg text-on-surface font-bold mb-1.5 leading-tight">
                  {mem.title}
                </h3>
                <p className="font-body-md text-xs text-on-surface-variant leading-relaxed mb-3">
                  {mem.summary}
                </p>

                {/* Related Concepts */}
                {mem.related_concepts && mem.related_concepts.length > 0 && (
                  <div className="flex flex-wrap gap-1 mb-3">
                    {mem.related_concepts.map((concept, i) => (
                      <span key={i} className="text-[10px] font-mono px-1.5 py-0.2 rounded bg-surface-container border border-outline-variant/30 text-on-surface-variant">
                        #{concept}
                      </span>
                    ))}
                  </div>
                )}
              </div>

              {/* Card Footer: Source & User Delete Action */}
              <div className="pt-3 border-t border-outline-variant/20 flex items-center justify-between text-xs">
                <span className="text-[11px] text-on-surface-variant font-note-handwritten truncate">
                  Source: {mem.source}
                </span>
                <button
                  type="button"
                  onClick={() => handleDeleteMemory(mem.memory_id)}
                  className="text-on-surface-variant/60 hover:text-rose-400 text-xs flex items-center gap-0.5 cursor-pointer transition-colors"
                  title="Delete memory"
                >
                  <span className="material-symbols-outlined text-sm">delete</span>
                </button>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Shared Generalized Collective Intelligence Section */}
      <div className="mt-12 p-6 sketch-border border-tertiary bg-tertiary-fixed/20">
        <div className="flex items-center gap-2.5 mb-2">
          <span className="material-symbols-outlined text-tertiary text-2xl" style={{ fontVariationSettings: "'FILL' 1" }}>
            hub
          </span>
          <h3 className="font-headline-sm text-xl text-on-surface font-bold">
            Shared Learning Intelligence (Anonymized Patterns)
          </h3>
        </div>
        <p className="font-note-handwritten text-sm text-on-surface-variant mb-4">
          Empirical pedagogical patterns aggregated across thousands of learning milestones. All personal data and student identities are mathematically filtered before ingestion.
        </p>

        <div className="space-y-3">
          {sharedPatterns.map((pat) => (
            <div key={pat.pattern_id} className="p-3.5 rounded bg-surface-container/70 border border-outline-variant/30 text-xs">
              <div className="flex items-center justify-between mb-1">
                <span className="font-headline-sm text-sm font-bold text-tertiary">
                  Topic: {pat.topic}
                </span>
                <span className="text-[10px] font-mono text-outline">
                  Aggregated from {pat.evidence_count} Learning Milestones &bull; {pat.confidence} Confidence
                </span>
              </div>
              <p className="text-on-surface font-body-md mb-1">
                <strong>Context:</strong> {pat.misconception_or_context}
              </p>
              <p className="text-on-surface-variant font-body-md">
                <strong>Effective Intervention:</strong> {pat.effective_intervention}
              </p>
            </div>
          ))}
        </div>
      </div>

      {/* Navigation Footer */}
      <div className="flex flex-wrap justify-center gap-4 mt-12 pt-6 border-t border-outline-variant/40">
        <Link
          href="/journey"
          className="ink-wash-btn px-6 py-2 text-base flex items-center gap-2"
        >
          <span className="material-symbols-outlined text-sm">map</span>
          <span>Return to Learning Journey</span>
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
