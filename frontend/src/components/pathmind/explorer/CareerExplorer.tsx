"use client";

import { useState, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import Link from "next/link";

interface SkillGapItem {
  skill_name: string;
  category: "FOUNDATIONAL" | "CORE" | "SPECIALIZED" | "EXPERIENCE" | "EVIDENCE" | "CREDENTIAL" | string;
  current_status: "HELD" | "PARTIAL" | "MISSING" | string;
  description: string;
  recommended_action: string;
}

interface EducationRouteItem {
  route_type: string;
  title: string;
  description: string;
  estimated_duration: string;
  institutions_or_paths?: string[];
  geographic_relevance?: string;
}

interface CredentialOptionItem {
  title: string;
  issuer: string;
  classification: "MANDATORY" | "STRONGLY_USEFUL" | "OPTIONAL" | "LOW_VALUE" | string;
  purpose: string;
  prerequisites?: string[];
  verified_cost?: string;
  preparation_effort?: string;
}

interface TrajectoryCaseItem {
  trajectory_id: string;
  title: string;
  archetype: string;
  source_type: string;
  starting_conditions?: Record<string, unknown>;
  learning_milestones?: string[];
  major_transitions?: string[];
  obstacles_and_failures?: string[];
  outcome_role: string;
  similarity_rationale: string;
  important_differences: string;
}

interface CandidatePathItem {
  path_id: string;
  title: string;
  domain: string;
  description: string;
  fit_score: number;
  fit_level: string;
  confidence: string;
  why_it_matches: string[];
  supporting_evidence: string[];
  missing_evidence: string[];
  required_skills: string[];
  current_skills_held: string[];
  transferable_skills: string[];
  skill_gaps: SkillGapItem[];
  education_routes: EducationRouteItem[];
  credential_options: CredentialOptionItem[];
  india_context?: Record<string, unknown>;
  global_context?: Record<string, unknown>;
  experience_requirements: string[];
  advantages: string[];
  disadvantages: string[];
  risks: string[];
  alternatives: string[];
  similar_trajectories: TrajectoryCaseItem[];
  source_references?: Array<Record<string, unknown>>;
}

interface TrajectoryPatternItem {
  pattern_title: string;
  description: string;
  evidence_trajectories_count: number;
  evidence_summary: string;
  confidence: string;
}

export function CareerExplorer() {
  const [candidatePaths, setCandidatePaths] = useState<CandidatePathItem[]>([]);
  const [patterns, setPatterns] = useState<TrajectoryPatternItem[]>([]);
  const [overallReasoning, setOverallReasoning] = useState<string>("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Active / Selected Path State
  const [selectedPathId, setSelectedPathId] = useState<string | null>(null);
  const [selectionVersion, setSelectionVersion] = useState<number>(1);
  const [isSelecting, setIsSelecting] = useState(false);
  const [selectionConfirmed, setSelectionConfirmed] = useState(false);

  // Interactive Drawers & Modals
  const [expandedWhyId, setExpandedWhyId] = useState<string | null>(null);
  const [activeTrajectoryModal, setActiveTrajectoryModal] = useState<TrajectoryCaseItem | null>(null);
  const [geoTab, setGeoTab] = useState<"india" | "global">("india");

  // Counterfactual Sandbox State
  const [counterfactualPrompt, setCounterfactualPrompt] = useState("");
  const [counterfactualLoading, setCounterfactualLoading] = useState(false);
  const [counterfactualNotes, setCounterfactualNotes] = useState<string[]>([]);
  const [counterfactualActiveFor, setCounterfactualActiveFor] = useState<string | null>(null);

  const fetchPaths = async () => {
    setLoading(true);
    setError(null);
    try {
      const baseUrl = process.env.NEXT_PUBLIC_API_BASE_URL || "https://pathmind-api.onrender.com";
      const personId = typeof window !== "undefined" 
        ? (localStorage.getItem("pathmind_user_name")?.toLowerCase().replace(/\s+/g, "-") || "scholar-user")
        : "scholar-user";

      const res = await fetch(`${baseUrl}/api/trajectories/discover`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-Person-ID": personId
        },
        body: JSON.stringify({
          person_id: personId,
          goals: ["Explore Applied AI, Robotics, and Systems Engineering"],
          geographic_preference: "India & Global"
        })
      });

      if (!res.ok) {
        throw new Error("Discovery request failed");
      }

      const data = await res.json();
      setCandidatePaths(data.candidate_paths || []);
      setPatterns(data.extracted_patterns || []);
      setOverallReasoning(data.overall_reasoning || "");
      if (data.candidate_paths && data.candidate_paths.length > 0) {
        setSelectedPathId(data.candidate_paths[0].path_id);
      }
    } catch (err) {
      console.error(err);
      setError("Unable to load live trajectory pathways. Falling back to offline discovery cache.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchPaths();
  }, []);

  const handleSelectPath = async (path: CandidatePathItem) => {
    setIsSelecting(true);
    try {
      const baseUrl = process.env.NEXT_PUBLIC_API_BASE_URL || "https://pathmind-api.onrender.com";
      const personId = typeof window !== "undefined" 
        ? (localStorage.getItem("pathmind_user_name")?.toLowerCase().replace(/\s+/g, "-") || "scholar-user")
        : "scholar-user";

      const res = await fetch(`${baseUrl}/api/trajectories/select`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-Person-ID": personId
        },
        body: JSON.stringify({
          person_id: personId,
          selected_path_id: path.path_id,
          selected_path: path,
          all_candidate_paths: candidatePaths,
          selection_reason: `Selected by candidate as primary roadmap target (${path.title}).`
        })
      });

      if (res.ok) {
        const data = await res.json();
        setSelectionVersion(data.version || 1);
        setSelectedPathId(path.path_id);
        setSelectionConfirmed(true);
        if (typeof window !== "undefined") {
          localStorage.setItem("pathmind_selected_path_id", path.path_id);
          localStorage.setItem("pathmind_selected_path_title", path.title);
        }
      }
    } catch (err) {
      console.error(err);
      setSelectedPathId(path.path_id);
      setSelectionConfirmed(true);
    } finally {
      setIsSelecting(false);
    }
  };

  const handleCounterfactual = async (pathId: string, modType: string, customPrompt?: string) => {
    setCounterfactualLoading(true);
    const promptText = customPrompt || (
      modType === "LOW_BUDGET" ? "What if I cannot afford a four-year private degree and need an open-source route?" :
      modType === "SELF_PACED_5_HOURS" ? "What if I only have 5 hours per week?" :
      modType === "GLOBAL_MIGRATION" ? "What if I want to target international/global remote opportunities?" :
      "What if?"
    );

    try {
      const baseUrl = process.env.NEXT_PUBLIC_API_BASE_URL || "https://pathmind-api.onrender.com";
      const personId = typeof window !== "undefined" 
        ? (localStorage.getItem("pathmind_user_name")?.toLowerCase().replace(/\s+/g, "-") || "scholar-user")
        : "scholar-user";

      const res = await fetch(`${baseUrl}/api/trajectories/counterfactual`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-Person-ID": personId
        },
        body: JSON.stringify({
          person_id: personId,
          base_path_id: pathId,
          modification_type: modType,
          modification_prompt: promptText
        })
      });

      if (res.ok) {
        const data = await res.json();
        // Replace candidate path in state with adjusted variant
        setCandidatePaths(prev => prev.map(p => p.path_id === pathId ? data.adjusted_path : p));
        setCounterfactualNotes(data.trade_off_notes || []);
        setCounterfactualActiveFor(pathId);
      }
    } catch (err) {
      console.error(err);
    } finally {
      setCounterfactualLoading(false);
    }
  };

  const getGapBadgeClass = (category: string) => {
    switch (category) {
      case "FOUNDATIONAL":
        return "bg-amber-950/40 text-amber-300 border-amber-700/60";
      case "CORE":
        return "bg-sky-950/40 text-sky-300 border-sky-700/60";
      case "SPECIALIZED":
        return "bg-purple-950/40 text-purple-300 border-purple-700/60";
      case "EXPERIENCE":
        return "bg-emerald-950/40 text-emerald-300 border-emerald-700/60";
      default:
        return "bg-surface-container text-on-surface-variant border-outline";
    }
  };

  return (
    <div className="w-full max-w-6xl mx-auto px-4 py-8">
      {/* Header & Principle Banner */}
      <div className="text-center mb-10">
        <div className="inline-flex items-center gap-2 px-4 py-1.5 sketchy-chip text-tertiary mb-4 bg-surface-container-low">
          <span className="material-symbols-outlined text-lg" style={{ fontVariationSettings: "'FILL' 1" }}>
            alt_route
          </span>
          <span className="font-note-handwritten text-xl font-medium">
            Chapter III: Trajectory Discovery
          </span>
        </div>
        <h1 className="font-headline-lg text-4xl sm:text-5xl text-on-surface mb-3">
          Candidate Career Pathways
        </h1>
        <p className="font-note-handwritten text-2xl text-on-surface-variant max-w-2xl mx-auto">
          The agent recommends grounded options. The scholar decides the path.
        </p>
      </div>

      {/* Rationale & Cross-Trajectory Patterns Banner */}
      {overallReasoning && (
        <div className="mb-8 p-6 sketch-border bg-surface-container-low/95">
          <div className="flex items-start gap-4">
            <span className="material-symbols-outlined text-primary text-3xl shrink-0 mt-0.5" style={{ fontVariationSettings: "'FILL' 1" }}>
              insights
            </span>
            <div className="flex-1">
              <h2 className="font-headline-sm text-xl text-on-surface mb-1.5">
                Multi-Agent Trajectory Synthesis
              </h2>
              <p className="font-body-md text-sm text-on-surface-variant leading-relaxed mb-4">
                {overallReasoning}
              </p>

              {/* Empirical Patterns */}
              {patterns.length > 0 && (
                <div className="space-y-2 pt-3 border-t border-outline-variant/30">
                  <span className="font-label-md text-xs font-bold uppercase tracking-wider text-outline block">
                    Attributed Empirical Patterns From Similar Scholar Journeys:
                  </span>
                  <div className="grid sm:grid-cols-2 gap-3 mt-1">
                    {patterns.slice(0, 2).map((pat, idx) => (
                      <div key={idx} className="p-3 rounded bg-surface-container/60 border border-outline-variant/20 text-xs">
                        <span className="font-headline-sm text-sm text-secondary font-bold block mb-1">
                          &bull; {pat.pattern_title}
                        </span>
                        <p className="text-on-surface-variant font-body-md leading-snug">{pat.description}</p>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      {loading && (
        <div className="text-center py-20 flex flex-col items-center">
          <div className="w-14 h-14 rounded-full border-2 border-primary bg-primary/10 flex items-center justify-center mb-4">
            <span className="material-symbols-outlined text-3xl text-primary animate-spin">
              progress_activity
            </span>
          </div>
          <h3 className="font-headline-sm text-2xl text-on-surface mb-1">Retrieving Trajectory Patterns &amp; Knowledge...</h3>
          <p className="font-note-handwritten text-xl text-on-surface-variant">Connecting ESCO/NCO occupational data with your psychometric profile.</p>
        </div>
      )}

      {error && !loading && (
        <div className="mb-8 p-4 sketch-border border-amber-600 bg-amber-950/20 text-on-surface text-sm">
          <p>{error}</p>
        </div>
      )}

      {/* Selected Confirmation Banner */}
      {selectionConfirmed && selectedPathId && (
        <motion.div
          initial={{ opacity: 0, scale: 0.95 }}
          animate={{ opacity: 1, scale: 1 }}
          className="mb-8 p-6 sketch-border border-primary bg-primary-fixed/30 flex items-center justify-between flex-wrap gap-4"
        >
          <div className="flex items-center gap-3">
            <span className="material-symbols-outlined text-primary text-3xl" style={{ fontVariationSettings: "'FILL' 1" }}>
              check_circle
            </span>
            <div>
              <h3 className="font-headline-sm text-lg font-bold text-on-surface">
                Active Pathway Selected (Version {selectionVersion})
              </h3>
              <p className="font-note-handwritten text-lg text-on-surface-variant">
                Your choice is preserved in your longitudinal decision history.
              </p>
            </div>
          </div>
          <Link
            href="/journey"
            className="ink-wash-btn-primary px-6 py-2 text-base flex items-center gap-2"
          >
            <span>Proceed to Learning Journey</span>
            <span className="material-symbols-outlined text-sm">east</span>
          </Link>
        </motion.div>
      )}

      {/* Counterfactual Trade-off Notice */}
      {counterfactualNotes.length > 0 && counterfactualActiveFor && (
        <div className="mb-8 p-5 sketch-border border-tertiary bg-tertiary-fixed/30">
          <div className="flex items-start gap-3">
            <span className="material-symbols-outlined text-tertiary text-2xl mt-0.5">swap_horiz</span>
            <div>
              <h4 className="font-headline-sm text-base text-tertiary font-bold mb-1">
                Counterfactual Pathway Variant Applied
              </h4>
              <ul className="space-y-1 text-xs text-on-surface font-body-md">
                {counterfactualNotes.map((note, i) => (
                  <li key={i}>&bull; {note}</li>
                ))}
              </ul>
            </div>
          </div>
        </div>
      )}

      {/* 2–3 Candidate Paths Side-by-Side Grid */}
      {!loading && candidatePaths.length > 0 && (
        <div className="grid lg:grid-cols-3 gap-6 mb-12">
          {candidatePaths.map((path) => {
            const isSelected = selectedPathId === path.path_id;
            const isWhyExpanded = expandedWhyId === path.path_id;

            return (
              <div
                key={path.path_id}
                className={`sketch-border p-6 flex flex-col justify-between transition-all duration-300 ${
                  isSelected 
                    ? "bg-surface-container-low/95 border-primary shadow-md ring-2 ring-primary/40" 
                    : "bg-surface-container-low/80 hover:bg-surface-container-low/95"
                }`}
              >
                <div>
                  {/* Top Bar: Fit & Confidence */}
                  <div className="flex items-center justify-between gap-2 mb-3">
                    <span className="font-note-handwritten text-xs uppercase tracking-wider text-secondary sketchy-chip px-2.5 py-0.5">
                      {path.domain}
                    </span>
                    <div className="flex items-center gap-1.5">
                      <span className="font-headline-lg text-lg font-bold text-primary">
                        {Math.round(path.fit_score)}%
                      </span>
                      <span className="text-[10px] font-bold uppercase px-1.5 py-0.5 rounded border border-primary/30 bg-primary/10 text-primary">
                        {path.fit_level} FIT
                      </span>
                    </div>
                  </div>

                  {/* Title & Description */}
                  <h3 className="font-headline-sm text-2xl font-bold text-on-surface mb-2 leading-tight">
                    {path.title}
                  </h3>
                  <p className="font-body-md text-xs text-on-surface-variant mb-4 leading-relaxed line-clamp-3">
                    {path.description}
                  </p>

                  {/* Expandable "Why am I seeing this path?" Button */}
                  <div className="mb-4">
                    <button
                      type="button"
                      onClick={() => setExpandedWhyId(isWhyExpanded ? null : path.path_id)}
                      className="text-xs font-headline-sm text-primary flex items-center gap-1 hover:underline cursor-pointer"
                    >
                      <span>Why this pathway? ({path.why_it_matches.length} signals)</span>
                      <span className="material-symbols-outlined text-sm">
                        {isWhyExpanded ? "expand_less" : "expand_more"}
                      </span>
                    </button>

                    {isWhyExpanded && (
                      <div className="mt-2 p-3 rounded bg-surface-container/70 border border-outline-variant/30 text-xs space-y-1.5">
                        <span className="font-bold text-[10px] uppercase text-outline block">Grounded Evidence:</span>
                        {path.why_it_matches.map((w, i) => (
                          <div key={i} className="flex items-start gap-1.5 text-on-surface">
                            <span className="text-primary font-bold">&check;</span>
                            <span>{w}</span>
                          </div>
                        ))}
                        {path.missing_evidence.length > 0 && (
                          <div className="mt-2 pt-2 border-t border-outline-variant/20">
                            <span className="font-bold text-[10px] uppercase text-amber-400 block">Missing Artifacts:</span>
                            {path.missing_evidence.map((m, i) => (
                              <div key={i} className="flex items-start gap-1.5 text-on-surface-variant text-[11px]">
                                <span className="text-amber-400 font-bold">&bull;</span>
                                <span>{m}</span>
                              </div>
                            ))}
                          </div>
                        )}
                      </div>
                    )}
                  </div>

                  {/* Skill Gaps Breakdown */}
                  <div className="mb-4 pt-3 border-t border-outline-variant/20">
                    <span className="font-label-md text-xs font-bold uppercase tracking-wider text-outline block mb-2">
                      Categorized Skill Gaps:
                    </span>
                    <div className="space-y-2">
                      {path.skill_gaps.slice(0, 3).map((gap, i) => (
                        <div key={i} className="p-2 rounded bg-surface-container/50 border border-outline-variant/20 text-xs">
                          <div className="flex items-center justify-between gap-1 mb-0.5">
                            <span className="font-headline-sm font-bold text-on-surface">{gap.skill_name}</span>
                            <span className={`text-[9px] font-bold px-1.5 py-0.2 rounded border ${getGapBadgeClass(gap.category)}`}>
                              {gap.category}
                            </span>
                          </div>
                          <p className="text-[11px] text-on-surface-variant font-note-handwritten">{gap.recommended_action}</p>
                        </div>
                      ))}
                    </div>
                  </div>

                  {/* Education & Credentials */}
                  <div className="mb-4 pt-3 border-t border-outline-variant/20 text-xs">
                    <span className="font-label-md text-xs font-bold uppercase tracking-wider text-outline block mb-1">
                      Primary Route:
                    </span>
                    <p className="font-headline-sm text-sm text-secondary font-medium">
                      {path.education_routes[0]?.title || "4-Year Technical Degree"}
                    </p>
                    <span className="text-[11px] text-on-surface-variant font-note-handwritten">
                      Duration: {path.education_routes[0]?.estimated_duration || "4 Years"}
                    </span>
                  </div>

                  {/* Geographic Context Toggle */}
                  <div className="mb-4 p-3 rounded bg-surface-container/60 border border-outline-variant/20 text-xs">
                    <div className="flex items-center justify-between mb-1">
                      <span className="font-bold text-[10px] uppercase text-outline">Geographic Provenance:</span>
                      <div className="flex gap-1 text-[10px]">
                        <button
                          type="button"
                          onClick={() => setGeoTab("india")}
                          className={`px-1.5 py-0.5 rounded ${geoTab === "india" ? "bg-primary/20 text-primary font-bold" : "text-on-surface-variant"}`}
                        >
                          India
                        </button>
                        <button
                          type="button"
                          onClick={() => setGeoTab("global")}
                          className={`px-1.5 py-0.5 rounded ${geoTab === "global" ? "bg-primary/20 text-primary font-bold" : "text-on-surface-variant"}`}
                        >
                          Global
                        </button>
                      </div>
                    </div>
                    {geoTab === "india" ? (
                      <p className="text-[11px] text-on-surface-variant font-mono">
                        {String(path.india_context?.nco_code || "NCO: 2512.01")} &bull; Hubs: {Array.isArray(path.india_context?.industry_hubs) ? path.india_context.industry_hubs.join(", ") : "Bengaluru, Hyderabad"}
                      </p>
                    ) : (
                      <p className="text-[11px] text-on-surface-variant font-mono">
                        {String(path.global_context?.esco_title || "ESCO: ICT Developer")}
                      </p>
                    )}
                  </div>

                  {/* "People Like You" Attributed Trajectory Link */}
                  {path.similar_trajectories && path.similar_trajectories.length > 0 && (
                    <div className="mb-5">
                      <button
                        type="button"
                        onClick={() => setActiveTrajectoryModal(path.similar_trajectories[0])}
                        className="font-note-handwritten text-base text-tertiary hover:underline flex items-center gap-1 cursor-pointer"
                      >
                        <span className="material-symbols-outlined text-sm">person_pin</span>
                        <span>View Attributed Case Study ({path.similar_trajectories[0].title})</span>
                      </button>
                    </div>
                  )}

                  {/* Counterfactual Quick Actions */}
                  <div className="mb-6 pt-3 border-t border-outline-variant/20">
                    <span className="font-label-md text-[10px] font-bold uppercase tracking-wider text-outline block mb-1.5">
                      Counterfactual Sandbox (&ldquo;What If?&rdquo;):
                    </span>
                    <div className="flex flex-wrap gap-1.5">
                      <button
                        type="button"
                        onClick={() => handleCounterfactual(path.path_id, "LOW_BUDGET")}
                        disabled={counterfactualLoading}
                        className="text-[10px] font-note-handwritten px-2 py-0.5 rounded border border-outline-variant/40 bg-surface-container hover:border-primary text-on-surface cursor-pointer"
                      >
                        Low Budget / Free
                      </button>
                      <button
                        type="button"
                        onClick={() => handleCounterfactual(path.path_id, "SELF_PACED_5_HOURS")}
                        disabled={counterfactualLoading}
                        className="text-[10px] font-note-handwritten px-2 py-0.5 rounded border border-outline-variant/40 bg-surface-container hover:border-primary text-on-surface cursor-pointer"
                      >
                        5 Hrs/Week
                      </button>
                      <button
                        type="button"
                        onClick={() => handleCounterfactual(path.path_id, "GLOBAL_MIGRATION")}
                        disabled={counterfactualLoading}
                        className="text-[10px] font-note-handwritten px-2 py-0.5 rounded border border-outline-variant/40 bg-surface-container hover:border-primary text-on-surface cursor-pointer"
                      >
                        Global Focus
                      </button>
                    </div>
                    <form 
                      onSubmit={(e) => {
                        e.preventDefault();
                        if (counterfactualPrompt.trim()) {
                          handleCounterfactual(path.path_id, "CUSTOM", counterfactualPrompt.trim());
                          setCounterfactualPrompt("");
                        }
                      }}
                      className="flex gap-1 mt-2"
                    >
                      <input
                        type="text"
                        value={counterfactualPrompt}
                        onChange={(e) => setCounterfactualPrompt(e.target.value)}
                        placeholder="e.g. What if I want a hybrid role?"
                        className="flex-1 hand-drawn-input text-[11px] px-2 py-1 bg-surface-container"
                      />
                      <button
                        type="submit"
                        disabled={!counterfactualPrompt.trim() || counterfactualLoading}
                        className="ink-wash-btn-primary px-2.5 py-1 text-[11px] disabled:opacity-50"
                      >
                        Explore
                      </button>
                    </form>
                  </div>
                </div>

                {/* Selection Action Button */}
                <div className="pt-4 border-t border-outline-variant/30">
                  <button
                    type="button"
                    onClick={() => handleSelectPath(path)}
                    disabled={isSelecting}
                    className={`w-full py-2.5 px-4 text-lg font-headline-sm transition-all cursor-pointer flex items-center justify-center gap-2 ${
                      isSelected 
                        ? "ink-wash-btn-primary" 
                        : "ink-wash-btn hover:border-primary text-on-surface"
                    }`}
                  >
                    <span>{isSelected ? "Selected Target Pathway" : "Select This Pathway"}</span>
                    <span className="material-symbols-outlined text-sm">
                      {isSelected ? "check" : "arrow_forward"}
                    </span>
                  </button>
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* Trajectory Modal / Drawer */}
      <AnimatePresence>
        {activeTrajectoryModal && (
          <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-xs">
            <motion.div
              initial={{ opacity: 0, scale: 0.9 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, scale: 0.9 }}
              className="w-full max-w-2xl sketch-border bg-surface p-6 max-h-[85vh] overflow-y-auto"
            >
              <div className="flex items-start justify-between gap-3 mb-4 pb-3 border-b border-outline-variant/30">
                <div>
                  <span className="font-note-handwritten text-xs text-secondary sketchy-chip px-2 py-0.5">
                    Attributed Case Study ({activeTrajectoryModal.source_type})
                  </span>
                  <h3 className="font-headline-sm text-2xl text-on-surface mt-1">
                    {activeTrajectoryModal.title}
                  </h3>
                  <p className="text-xs text-on-surface-variant font-mono">
                    Outcome: {activeTrajectoryModal.outcome_role}
                  </p>
                </div>
                <button
                  type="button"
                  onClick={() => setActiveTrajectoryModal(null)}
                  className="text-on-surface-variant hover:text-on-surface text-xl font-bold px-2 py-1 cursor-pointer"
                >
                  &times;
                </button>
              </div>

              <div className="space-y-4 text-xs font-body-md text-on-surface">
                <div>
                  <h4 className="font-bold text-xs uppercase text-outline mb-1">Starting Conditions:</h4>
                  <div className="p-2.5 rounded bg-surface-container/60 border border-outline-variant/20">
                    <p><strong>Education:</strong> {String(activeTrajectoryModal.starting_conditions?.education || "Class 12 STEM")}</p>
                    <p><strong>Skills:</strong> {Array.isArray(activeTrajectoryModal.starting_conditions?.starting_skills) ? activeTrajectoryModal.starting_conditions.starting_skills.join(", ") : "Basics"}</p>
                  </div>
                </div>

                <div>
                  <h4 className="font-bold text-xs uppercase text-outline mb-1">Learning Milestones:</h4>
                  <ul className="space-y-1 list-disc pl-4 text-on-surface-variant">
                    {activeTrajectoryModal.learning_milestones?.map((m, i) => (
                      <li key={i}>{m}</li>
                    ))}
                  </ul>
                </div>

                <div>
                  <h4 className="font-bold text-xs uppercase text-amber-500 mb-1">Obstacles &amp; Turning Points:</h4>
                  <ul className="space-y-1 list-disc pl-4 text-on-surface-variant">
                    {activeTrajectoryModal.obstacles_and_failures?.map((o, i) => (
                      <li key={i}>{o}</li>
                    ))}
                  </ul>
                </div>

                <div className="p-3 rounded bg-surface-container-low border border-outline-variant/30 text-on-surface-variant">
                  <p><strong>Why Relevant:</strong> {activeTrajectoryModal.similarity_rationale}</p>
                  <p className="mt-1"><strong>Important Differences:</strong> {activeTrajectoryModal.important_differences}</p>
                </div>
              </div>

              <div className="mt-6 flex justify-end">
                <button
                  type="button"
                  onClick={() => setActiveTrajectoryModal(null)}
                  className="ink-wash-btn px-6 py-1.5 text-base cursor-pointer"
                >
                  Close Case Study
                </button>
              </div>
            </motion.div>
          </div>
        )}
      </AnimatePresence>
    </div>
  );
}
