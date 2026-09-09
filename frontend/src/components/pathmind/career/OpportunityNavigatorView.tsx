"use client";

import { useState, useEffect, useCallback } from "react";
import {
  Compass,
  CheckCircle2,
  ExternalLink,
  ShieldCheck,
  Calendar,
  MapPin,
  Sparkles,
  Search,
  BookOpen,
  HelpCircle,
  Check
} from "lucide-react";

interface CanonicalOpportunity {
  opportunity_id: string;
  provider: string;
  provider_record_id: string;
  type: string;
  title: string;
  organization: string;
  description: string;
  location: string;
  remote_status: string;
  eligibility: string;
  requirements: string[];
  preferred_requirements: string[];
  skills: string[];
  compensation?: string | null;
  deadline?: string | null;
  application_url: string;
  source_url: string;
  status: string;
  verification_status: string;
}

interface OpportunityMatchResult {
  opportunity: CanonicalOpportunity;
  fit_state: string;
  readiness_state: string;
  matched_requirements: string[];
  gaps: string[];
  unknowns: string[];
  why_it_matters: string;
  next_step: string;
  decision_recommendation: string;
  tradeoffs: string[];
}

interface PrepAction {
  title: string;
  description: string;
  action_type: string;
  priority: string;
  verification_requirement: string;
}

interface PrepPlan {
  opportunity_id: string;
  person_id: string;
  target_role: string;
  required_actions: PrepAction[];
  estimated_effort_days: number;
  deadline_feasibility: string;
}

interface InterviewPrep {
  opportunity_id: string;
  opportunity_title: string;
  organization: string;
  technical_competency_questions: string[];
  project_defense_questions: string[];
  gap_reinforcement_focus: string[];
}

export function OpportunityNavigatorView() {
  const [matches, setMatches] = useState<OpportunityMatchResult[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedMatch, setSelectedMatch] = useState<OpportunityMatchResult | null>(null);

  // Filters
  const [roleSearch, setRoleSearch] = useState("");
  const [typeFilter, setTypeFilter] = useState("ALL");
  const [geoFilter, setGeoFilter] = useState("ALL");

  // Drawer Action States
  const [prepPlan, setPrepPlan] = useState<PrepPlan | null>(null);
  const [prepLoading, setPrepLoading] = useState(false);
  const [planSpawned, setPlanSpawned] = useState(false);

  const [interviewPrep, setInterviewPrep] = useState<InterviewPrep | null>(null);
  const [interviewLoading, setInterviewLoading] = useState(false);

  const fetchMatches = useCallback(async () => {
    setLoading(true);
    try {
      const params = new URLSearchParams();
      if (roleSearch) params.append("role_filter", roleSearch);
      if (geoFilter !== "ALL") params.append("geography", geoFilter);

      const res = await fetch(`/api/opportunities/matched?${params.toString()}`, {
        headers: { "x-person-id": "scholar-user" }
      });
      if (res.ok) {
        const data = await res.json();
        setMatches(data);
        if (selectedMatch) {
          const updated = data.find((m: OpportunityMatchResult) => m.opportunity.opportunity_id === selectedMatch.opportunity.opportunity_id);
          if (updated) setSelectedMatch(updated);
        }
      }
    } catch (err) {
      console.error("Failed to load matched opportunities:", err);
    } finally {
      setLoading(false);
    }
  }, [roleSearch, geoFilter, selectedMatch]);

  useEffect(() => {
    fetchMatches();
  }, [fetchMatches]);

  const handleSelectOpportunity = (match: OpportunityMatchResult) => {
    setSelectedMatch(match);
    setPrepPlan(null);
    setPlanSpawned(false);
    setInterviewPrep(null);
  };

  const handleGeneratePrepPlan = async () => {
    if (!selectedMatch) return;
    setPrepLoading(true);
    try {
      const res = await fetch(`/api/opportunities/${selectedMatch.opportunity.opportunity_id}/preparation-plan`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "x-person-id": "scholar-user"
        },
        body: JSON.stringify({ spawn_actions_to_execution_engine: true })
      });
      if (res.ok) {
        const data = await res.json();
        setPrepPlan(data);
        setPlanSpawned(true);
      }
    } catch (err) {
      console.error("Failed to generate plan:", err);
    } finally {
      setPrepLoading(false);
    }
  };

  const handleFetchInterviewPrep = async () => {
    if (!selectedMatch) return;
    setInterviewLoading(true);
    try {
      const res = await fetch(`/api/opportunities/${selectedMatch.opportunity.opportunity_id}/interview-prep`, {
        headers: { "x-person-id": "scholar-user" }
      });
      if (res.ok) {
        const data = await res.json();
        setInterviewPrep(data);
      }
    } catch (err) {
      console.error("Failed to load interview prep:", err);
    } finally {
      setInterviewLoading(false);
    }
  };

  // Filter local items by type
  const filteredMatches = matches.filter((m) => {
    if (typeFilter === "ALL") return true;
    return m.opportunity.type.toUpperCase() === typeFilter.toUpperCase();
  });

  return (
    <div className="max-w-6xl mx-auto px-4 py-8 space-y-10">
      {/* Header */}
      <div className="border-b border-stone-200 pb-6 flex flex-col md:flex-row md:items-end justify-between gap-4">
        <div>
          <div className="flex items-center space-x-2 text-stone-700 text-xs font-mono uppercase tracking-widest mb-1">
            <Compass className="w-3.5 h-3.5 text-stone-700" />
            <span>Universal Opportunity Intelligence</span>
          </div>
          <h1 className="text-3xl font-serif tracking-tight text-stone-900">
            Opportunity Navigator & Matching
          </h1>
          <p className="text-stone-600 text-sm mt-1 max-w-2xl">
            Connecting your active goals and verified code evidence to authentic fellowships, internships, research positions, and open-source programs across India and Global Remote.
          </p>
        </div>

        <div className="flex items-center space-x-2 text-xs font-mono text-stone-700 bg-stone-100 border border-stone-200 px-3 py-1.5 rounded">
          <ShieldCheck className="w-4 h-4 text-emerald-700" />
          <span>Strict Provenance • Zero Fabricated Listings</span>
        </div>
      </div>

      {/* Filter & Search Bar */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-3 bg-white p-4 rounded-xl border border-stone-200 shadow-xs">
        <div className="relative">
          <Search className="w-3.5 h-3.5 text-stone-400 absolute left-3 top-3" />
          <input
            type="text"
            placeholder="Search role, skills, or program..."
            value={roleSearch}
            onChange={(e) => setRoleSearch(e.target.value)}
            className="w-full text-xs font-mono pl-9 pr-3 py-2 border border-stone-200 rounded focus:outline-none focus:border-stone-400"
          />
        </div>

        <div>
          <select
            value={typeFilter}
            onChange={(e) => setTypeFilter(e.target.value)}
            className="w-full text-xs font-mono p-2 border border-stone-200 rounded bg-stone-50 text-stone-700 focus:outline-none"
          >
            <option value="ALL">All Opportunity Types</option>
            <option value="INTERNSHIP">Internships</option>
            <option value="FELLOWSHIP">Fellowships</option>
            <option value="OPEN_SOURCE">Open Source Programs</option>
            <option value="RESEARCH">Academic Research</option>
            <option value="FULL_TIME">Full-Time Roles</option>
          </select>
        </div>

        <div>
          <select
            value={geoFilter}
            onChange={(e) => setGeoFilter(e.target.value)}
            className="w-full text-xs font-mono p-2 border border-stone-200 rounded bg-stone-50 text-stone-700 focus:outline-none"
          >
            <option value="ALL">All Geographies</option>
            <option value="India">India (Bengaluru / Delhi / Hyderabad)</option>
            <option value="Remote">Global Remote</option>
          </select>
        </div>
      </div>

      {/* Main Content: Grid + Detail Drawer */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 items-start">
        {/* Left Column: Opportunity Cards */}
        <div className="lg:col-span-7 space-y-4">
          {loading ? (
            <div className="p-12 text-center text-stone-500 font-serif italic text-sm">
              Evaluating requirement graphs and verified code evidence...
            </div>
          ) : filteredMatches.length > 0 ? (
            filteredMatches.map((m) => {
              const isSelected = selectedMatch?.opportunity.opportunity_id === m.opportunity.opportunity_id;
              return (
                <div
                  key={m.opportunity.opportunity_id}
                  onClick={() => handleSelectOpportunity(m)}
                  className={`p-5 rounded-xl border transition-all cursor-pointer ${
                    isSelected
                      ? "border-stone-800 bg-stone-50/90 shadow-sm"
                      : "border-stone-200 bg-white hover:border-stone-300 shadow-xs"
                  }`}
                >
                  <div className="flex items-start justify-between gap-2 mb-2">
                    <div className="space-y-0.5">
                      <span className="text-[10px] font-mono uppercase tracking-wider text-stone-500">
                        {m.opportunity.organization} • {m.opportunity.provider}
                      </span>
                      <h3 className="text-lg font-serif text-stone-900 tracking-tight">
                        {m.opportunity.title}
                      </h3>
                    </div>

                    <div className="flex flex-col items-end gap-1 shrink-0">
                      <span className={`text-[10px] font-mono px-2 py-0.5 rounded border ${
                        m.fit_state === "STRONG_MATCH"
                          ? "bg-emerald-50 text-emerald-800 border-emerald-200"
                          : m.fit_state === "GOOD_MATCH"
                          ? "bg-blue-50 text-blue-800 border-blue-200"
                          : "bg-amber-50 text-amber-800 border-amber-200"
                      }`}>
                        {m.fit_state.replace("_", " ")}
                      </span>
                      <span className="text-[9px] font-mono text-stone-500 uppercase">
                        Readiness: {m.readiness_state.replace("_", " ")}
                      </span>
                    </div>
                  </div>

                  <p className="text-xs text-stone-600 line-clamp-2 leading-relaxed mb-3">
                    {m.opportunity.description}
                  </p>

                  <div className="flex flex-wrap items-center gap-2 mb-3">
                    {m.matched_requirements.slice(0, 3).map((mr, i) => (
                      <span key={i} className="text-[10px] font-mono px-2 py-0.5 rounded bg-emerald-50 text-emerald-800 border border-emerald-200/60 flex items-center gap-1">
                        <Check className="w-2.5 h-2.5" />
                        <span>{mr.split(" (")[0]}</span>
                      </span>
                    ))}
                    {m.gaps.slice(0, 2).map((g, i) => (
                      <span key={i} className="text-[10px] font-mono px-2 py-0.5 rounded bg-stone-100 text-stone-600 border border-stone-200">
                        Missing: {g}
                      </span>
                    ))}
                  </div>

                  <div className="flex items-center justify-between text-[11px] font-mono text-stone-500 pt-3 border-t border-stone-100">
                    <div className="flex items-center space-x-1">
                      <MapPin className="w-3 h-3 text-stone-400" />
                      <span>{m.opportunity.location}</span>
                    </div>
                    {m.opportunity.deadline && (
                      <div className="flex items-center space-x-1">
                        <Calendar className="w-3 h-3 text-stone-400" />
                        <span>Deadline: {new Date(m.opportunity.deadline).toLocaleDateString()}</span>
                      </div>
                    )}
                  </div>
                </div>
              );
            })
          ) : (
            <div className="p-8 text-center border border-dashed border-stone-300 rounded-xl bg-stone-50/50 space-y-2">
              <Compass className="w-8 h-8 text-stone-400 mx-auto" />
              <p className="font-serif text-stone-700">No verified opportunities match current search criteria.</p>
              <p className="text-xs text-stone-500 font-mono">Try adjusting role keywords or geography filter.</p>
            </div>
          )}
        </div>

        {/* Right Column: Detailed Intelligence Drawer */}
        <div className="lg:col-span-5 sticky top-6">
          {selectedMatch ? (
            <div className="bg-white border border-stone-200 rounded-xl p-6 shadow-sm space-y-6 max-h-[85vh] overflow-y-auto">
              <div className="space-y-1.5 border-b border-stone-100 pb-4">
                <div className="flex items-center justify-between">
                  <span className="text-[10px] font-mono uppercase text-stone-500">
                    {selectedMatch.opportunity.type} • {selectedMatch.opportunity.provider}
                  </span>
                  <a
                    href={selectedMatch.opportunity.application_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="flex items-center space-x-1 text-xs font-mono text-stone-800 hover:text-stone-950 underline"
                  >
                    <span>Official Portal</span>
                    <ExternalLink className="w-3 h-3" />
                  </a>
                </div>
                <h2 className="text-xl font-serif text-stone-900">
                  {selectedMatch.opportunity.title}
                </h2>
                <p className="text-xs font-mono text-stone-600">
                  {selectedMatch.opportunity.organization} • {selectedMatch.opportunity.location}
                </p>
                {selectedMatch.opportunity.compensation && (
                  <span className="inline-block text-[11px] font-mono text-emerald-800 bg-emerald-50 px-2 py-0.5 rounded border border-emerald-200 mt-1">
                    {selectedMatch.opportunity.compensation}
                  </span>
                )}
              </div>

              {/* Why This Matches You */}
              <div className="space-y-2 text-xs">
                <span className="font-mono text-stone-500 uppercase tracking-wider block">
                  Why This Opportunity Matches
                </span>
                <p className="text-stone-700 font-sans leading-relaxed bg-stone-50 p-3 rounded border border-stone-200/60">
                  {selectedMatch.why_it_matters}
                </p>
              </div>

              {/* Matched vs Gaps vs Unknowns */}
              <div className="space-y-3 text-xs">
                <span className="font-mono text-stone-500 uppercase tracking-wider block">
                  Capability Audit & Requirements
                </span>

                <div className="space-y-1.5">
                  <span className="font-mono text-[11px] text-emerald-800 font-medium block">
                    ✓ Matched Capabilities ({selectedMatch.matched_requirements.length})
                  </span>
                  {selectedMatch.matched_requirements.map((mr, i) => (
                    <div key={i} className="text-stone-700 pl-2 border-l-2 border-emerald-500 font-sans py-0.5">
                      {mr}
                    </div>
                  ))}
                </div>

                {selectedMatch.gaps.length > 0 && (
                  <div className="space-y-1.5 pt-2">
                    <span className="font-mono text-[11px] text-rose-800 font-medium block">
                      ⚠ Gaps to Prove ({selectedMatch.gaps.length})
                    </span>
                    {selectedMatch.gaps.map((g, i) => (
                      <div key={i} className="text-stone-700 pl-2 border-l-2 border-rose-400 font-sans py-0.5">
                        {g}
                      </div>
                    ))}
                  </div>
                )}

                {selectedMatch.unknowns.length > 0 && (
                  <div className="space-y-1.5 pt-2">
                    <div className="flex items-center space-x-1 text-stone-500 font-mono text-[11px]">
                      <HelpCircle className="w-3 h-3 text-stone-400" />
                      <span>Profile Information Gaps (Not Penalized as Failure)</span>
                    </div>
                    {selectedMatch.unknowns.map((u, i) => (
                      <div key={i} className="text-stone-600 pl-2 border-l-2 border-stone-300 font-sans py-0.5 italic">
                        {u}
                      </div>
                    ))}
                  </div>
                )}
              </div>

              {/* Should I Apply? Decision Advisor */}
              <div className="p-4 rounded-lg bg-stone-50 border border-stone-200 space-y-2 text-xs">
                <div className="flex items-center justify-between">
                  <span className="font-mono uppercase font-semibold text-stone-800">
                    Decision Advisor
                  </span>
                  <span className={`font-mono text-[11px] px-2 py-0.5 rounded border ${
                    selectedMatch.decision_recommendation === "RECOMMEND_APPLYING"
                      ? "bg-emerald-100 text-emerald-900 border-emerald-300"
                      : "bg-amber-100 text-amber-900 border-amber-300"
                  }`}>
                    {selectedMatch.decision_recommendation.replace("_", " ")}
                  </span>
                </div>
                <p className="font-sans text-stone-600 leading-normal">
                  Next Step: {selectedMatch.next_step}
                </p>
                {selectedMatch.tradeoffs.length > 0 && (
                  <ul className="list-disc pl-4 space-y-1 text-stone-600 pt-1">
                    {selectedMatch.tradeoffs.map((t, i) => (
                      <li key={i}>{t}</li>
                    ))}
                  </ul>
                )}
              </div>

              {/* Action Buttons */}
              <div className="space-y-2 pt-2">
                <button
                  onClick={handleGeneratePrepPlan}
                  disabled={prepLoading || planSpawned}
                  className={`w-full py-2.5 px-4 rounded text-xs font-mono flex items-center justify-center space-x-2 transition-colors ${
                    planSpawned
                      ? "bg-emerald-50 text-emerald-800 border border-emerald-200"
                      : "bg-stone-900 hover:bg-stone-800 text-white"
                  }`}
                >
                  {planSpawned ? (
                    <>
                      <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600" />
                      <span>Preparation Actions Added to Mission Control</span>
                    </>
                  ) : (
                    <>
                      <Sparkles className="w-3.5 h-3.5 text-stone-400" />
                      <span>{prepLoading ? "Synthesizing Plan..." : "Generate Preparation Plan"}</span>
                    </>
                  )}
                </button>

                <button
                  onClick={handleFetchInterviewPrep}
                  disabled={interviewLoading}
                  className="w-full py-2.5 px-4 rounded text-xs font-mono border border-stone-300 hover:bg-stone-50 text-stone-700 flex items-center justify-center space-x-2 transition-colors"
                >
                  <BookOpen className="w-3.5 h-3.5 text-stone-500" />
                  <span>{interviewLoading ? "Extracting Questions..." : "Prepare for Interview"}</span>
                </button>
              </div>

              {/* Preparation Plan Preview */}
              {prepPlan && (
                <div className="p-4 rounded-lg border border-stone-200 bg-white space-y-3 text-xs">
                  <span className="font-mono text-stone-800 font-semibold uppercase block">
                    Execution Preparation Actions
                  </span>
                  <div className="space-y-2">
                    {prepPlan.required_actions.map((act, i) => (
                      <div key={i} className="p-2.5 rounded bg-stone-50 border border-stone-200/60 space-y-1">
                        <div className="flex items-center justify-between">
                          <span className="font-mono text-[10px] text-stone-500 uppercase">{act.action_type}</span>
                          <span className="font-mono text-[10px] text-stone-600">{act.priority}</span>
                        </div>
                        <h4 className="font-serif text-stone-900">{act.title}</h4>
                        <p className="text-[11px] text-stone-600 font-sans">{act.description}</p>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Interview Prep Questions */}
              {interviewPrep && (
                <div className="p-4 rounded-lg border border-stone-200 bg-stone-50 space-y-3 text-xs">
                  <span className="font-mono text-stone-800 font-semibold uppercase block">
                    Technical & Project Interview Questions
                  </span>

                  <div className="space-y-2">
                    <span className="font-mono text-[11px] text-stone-700 block font-medium">Competency Questions:</span>
                    {interviewPrep.technical_competency_questions.map((q, i) => (
                      <div key={i} className="text-stone-700 pl-2 border-l-2 border-stone-400 font-sans">
                        {q}
                      </div>
                    ))}

                    <span className="font-mono text-[11px] text-stone-700 block font-medium pt-2">Project Defense Questions:</span>
                    {interviewPrep.project_defense_questions.map((q, i) => (
                      <div key={i} className="text-stone-700 pl-2 border-l-2 border-blue-400 font-sans">
                        {q}
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          ) : (
            <div className="p-8 text-center border border-dashed border-stone-300 rounded-xl bg-stone-50/50 text-xs text-stone-500 font-mono">
              Select an opportunity from the list to inspect capability match intelligence, decision advice, and interview preparation.
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
