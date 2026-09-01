"use client";

import { useState, useEffect } from "react";
import { motion } from "framer-motion";
import Link from "next/link";

interface CategorizedGapData {
  gap_id: string;
  gap_type: string;
  title: string;
  description: string;
  severity: "HIGH" | "MEDIUM" | "LOW" | string;
  recommended_action: string;
}

interface TransferableSkillsData {
  already_have: string[];
  can_reuse: string[];
  need_to_build: string[];
  analysis_summary: string;
}

interface VerifiedCredentialData {
  credential_id: string;
  title: string;
  issuer: string;
  classification: "MANDATORY" | "STRONGLY_USEFUL" | "OPTIONAL" | "LOW_VALUE" | "NOT_RELEVANT" | string;
  preparation_effort: string;
  verified_cost?: string | null;
  official_url: string;
  strategic_advice: string;
}

interface AccountabilityData {
  status: "ON_TRACK" | "AT_RISK" | "DELAYED" | "BLOCKED" | "COMPLETED" | "PAUSED" | "REPLANNING" | string;
  current_streak_days: number;
  weekly_commitment_hours: number;
  mentor_observation: string;
  suggested_adjustment?: string | null;
  next_checkpoint: string;
}

interface VerifiedOpportunityData {
  opportunity_id: string;
  title: string;
  organization: string;
  location: string;
  employment_type: string;
  eligibility: string;
  required_skills: string[];
  preferred_skills: string[];
  deadline: string;
  apply_url: string;
  fit_level: "HIGH" | "MEDIUM" | "LOW" | string;
  fit_reasons: string[];
  missing_requirements: string[];
}

interface TailoredResumeData {
  resume_id: string;
  target_role: string;
  summary: string;
  highlighted_skills: string[];
  tailored_projects: Array<{
    title: string;
    technologies: string[];
    description: string;
    provenance: string;
  }>;
  ats_match_score: number;
  ats_matched_keywords: string[];
  ats_missing_keywords: string[];
  ats_recommendations: string[];
}

interface CareerReadinessReportData {
  person_id: string;
  target_goal: {
    target_role: string;
    target_industry: string;
    geography: string;
    target_timeline: string;
    priority: string;
  };
  current_person_state: string;
  readiness_state: "NOT_READY" | "FOUNDATIONAL" | "DEVELOPING" | "INTERNSHIP_READY" | "ENTRY_LEVEL_READY" | "TARGET_READY" | "ADVANCED" | string;
  readiness_explanation: string;
  next_readiness_milestone: string;
  categorized_gaps: CategorizedGapData[];
  transferable_skills: TransferableSkillsData;
  credentials_strategy: VerifiedCredentialData[];
  accountability: AccountabilityData;
  matched_opportunities: VerifiedOpportunityData[];
  tailored_resume_preview?: TailoredResumeData | null;
}

export function CareerLaunchpad() {
  const [report, setReport] = useState<CareerReadinessReportData | null>(null);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState<"GAPS" | "TRANSFERABLE" | "CREDENTIALS" | "OPPORTUNITIES" | "RESUME">("GAPS");
  const [personState, setPersonState] = useState<string>("college_student");
  const [error, setError] = useState<string | null>(null);

  const fetchReadiness = async (stateVal = personState) => {
    setLoading(true);
    setError(null);
    try {
      const baseUrl = process.env.NEXT_PUBLIC_API_BASE_URL || "https://pathmind-api.onrender.com";
      const personId = typeof window !== "undefined"
        ? (localStorage.getItem("pathmind_user_name")?.toLowerCase().replace(/\s+/g, "-") || "scholar-user")
        : "scholar-user";

      const res = await fetch(`${baseUrl}/api/career/readiness?current_state=${encodeURIComponent(stateVal)}`, {
        headers: { "X-Person-ID": personId }
      });
      if (res.ok) {
        const data = await res.json();
        setReport(data);
      }
    } catch (err) {
      console.error(err);
      setError("Unable to connect to live career readiness engine. Displaying offline demonstration view.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchReadiness(personState);
  }, []);

  const handleStateChange = (newState: string) => {
    setPersonState(newState);
    fetchReadiness(newState);
  };

  const getReadinessBadge = (stateStr: string) => {
    switch (stateStr) {
      case "TARGET_READY":
      case "ENTRY_LEVEL_READY":
        return "bg-emerald-950/50 text-emerald-300 border-emerald-700/60";
      case "INTERNSHIP_READY":
        return "bg-teal-950/50 text-teal-300 border-teal-700/60";
      case "DEVELOPING":
        return "bg-amber-950/50 text-amber-300 border-amber-700/60";
      default:
        return "bg-surface-container text-on-surface-variant border-outline";
    }
  };

  const getGapTypeBadge = (type: string) => {
    switch (type) {
      case "SKILL_GAP":
        return "bg-rose-950/40 text-rose-300 border-rose-800/40";
      case "EXPERIENCE_GAP":
        return "bg-amber-950/40 text-amber-300 border-amber-800/40";
      case "EVIDENCE_GAP":
        return "bg-sky-950/40 text-sky-300 border-sky-800/40";
      default:
        return "bg-surface-container text-on-surface-variant border-outline-variant/40";
    }
  };

  return (
    <div className="w-full max-w-5xl mx-auto px-4 py-8">
      {/* Header Banner */}
      <div className="text-center mb-8">
        <div className="inline-flex items-center gap-2 px-4 py-1.5 sketchy-chip text-primary mb-3 bg-surface-container-low">
          <span className="material-symbols-outlined text-lg" style={{ fontVariationSettings: "'FILL' 1" }}>
            rocket_launch
          </span>
          <span className="font-note-handwritten text-xl font-medium">
            Chapter VI: Accountability &amp; Career Launchpad
          </span>
        </div>
        <h1 className="font-headline-lg text-4xl sm:text-5xl text-on-surface mb-2">
          Career Readiness &amp; Real-World Execution
        </h1>
        <p className="font-note-handwritten text-2xl text-on-surface-variant max-w-2xl mx-auto">
          What it takes to reach your target role, what you already have, what you need to build, and where to apply.
        </p>
      </div>

      {/* Background Profile Selector */}
      <div className="mb-8 p-4 sketch-border bg-surface-container-low/80 flex items-center justify-between flex-wrap gap-3 text-xs">
        <div className="flex items-center gap-2">
          <span className="material-symbols-outlined text-secondary text-lg">badge</span>
          <span className="font-bold text-on-surface">Your Background Profile:</span>
        </div>
        <div className="flex flex-wrap gap-2">
          {[
            { id: "college_student", label: "CS / STEM Student" },
            { id: "mechanical_engineer", label: "Mechanical Switcher" },
            { id: "frontend_developer", label: "Frontend Engineer" },
            { id: "working_professional", label: "Working Professional" }
          ].map((item) => (
            <button
              key={item.id}
              type="button"
              onClick={() => handleStateChange(item.id)}
              className={`px-3 py-1 rounded text-xs font-headline-sm transition-all cursor-pointer ${
                personState === item.id
                  ? "bg-primary text-on-primary font-bold"
                  : "bg-surface-container text-on-surface-variant hover:text-on-surface border border-outline-variant/40"
              }`}
            >
              {item.label}
            </button>
          ))}
        </div>
      </div>

      {loading && (
        <div className="text-center py-16 flex flex-col items-center">
          <span className="material-symbols-outlined text-4xl text-primary animate-spin mb-3">
            progress_activity
          </span>
          <h3 className="font-headline-sm text-xl text-on-surface">Synthesizing Career Readiness Model...</h3>
        </div>
      )}

      {error && !loading && (
        <div className="p-4 sketch-border border-amber-600 bg-amber-950/20 text-on-surface text-center mb-8 text-xs">
          <p>{error}</p>
        </div>
      )}

      {!loading && report && (
        <div>
          {/* Target Role & Readiness Hero Card */}
          <motion.div
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            className="mb-8 p-6 sketch-border border-primary bg-surface-container-low"
          >
            <div className="flex items-start justify-between gap-4 flex-wrap mb-4">
              <div>
                <span className="font-label-md text-xs font-bold uppercase tracking-wider text-primary">
                  Active Career Target
                </span>
                <h2 className="font-headline-md text-2xl sm:text-3xl text-on-surface font-bold">
                  {report.target_goal.target_role}
                </h2>
                <span className="font-note-handwritten text-sm text-on-surface-variant">
                  {report.target_goal.target_industry} &bull; {report.target_goal.geography}
                </span>
              </div>
              <div className="flex flex-col items-end">
                <span className="text-[10px] uppercase font-mono text-on-surface-variant mb-1">
                  Readiness Level
                </span>
                <span className={`px-3 py-1 rounded-full text-xs font-bold border ${getReadinessBadge(report.readiness_state)}`}>
                  {report.readiness_state.replace("_", " ")}
                </span>
              </div>
            </div>

            <p className="font-body-md text-xs text-on-surface-variant leading-relaxed mb-4">
              {report.readiness_explanation}
            </p>

            <div className="p-3 rounded bg-surface-container border border-primary/30 flex items-center justify-between text-xs flex-wrap gap-2">
              <span className="text-primary font-bold">Next Readiness Milestone:</span>
              <span className="text-on-surface font-mono">{report.next_readiness_milestone}</span>
            </div>
          </motion.div>

          {/* Thoughtful Mentor & Accountability Partner Card */}
          <div className="mb-8 p-5 sketch-border border-secondary bg-secondary-fixed/20">
            <div className="flex items-start gap-3.5">
              <div className="w-10 h-10 rounded-full border border-secondary flex items-center justify-center text-secondary bg-secondary/10 shrink-0">
                <span className="material-symbols-outlined text-xl">psychology</span>
              </div>
              <div className="flex-1">
                <div className="flex items-center justify-between gap-2 flex-wrap mb-1">
                  <h3 className="font-headline-sm text-base text-on-surface font-bold">
                    Accountability Mentor Observation
                  </h3>
                  <div className="flex items-center gap-2">
                    <span className="text-xs px-2 py-0.5 rounded bg-surface-container font-mono text-emerald-300 border border-emerald-600/40">
                      {report.accountability.status.replace("_", " ")} ({report.accountability.current_streak_days}-Day Streak)
                    </span>
                    <span className="font-note-handwritten text-xs text-on-surface-variant">
                      {report.accountability.weekly_commitment_hours} hrs/week
                    </span>
                  </div>
                </div>
                <p className="font-body-md text-xs text-on-surface-variant leading-relaxed mb-2">
                  &ldquo;{report.accountability.mentor_observation}&rdquo;
                </p>
                {report.accountability.suggested_adjustment && (
                  <div className="text-[11px] p-2 rounded bg-surface-container border border-amber-500/30 text-amber-300">
                    Adjustment: {report.accountability.suggested_adjustment}
                  </div>
                )}
              </div>
            </div>
          </div>

          {/* Navigation Subtabs */}
          <div className="flex flex-wrap gap-2 mb-6 border-b border-outline-variant/40 pb-3">
            {[
              { id: "GAPS", label: "Gap Analysis (What You're Missing)", icon: "checklist" },
              { id: "TRANSFERABLE", label: "Transferable Skills Matrix", icon: "sync_alt" },
              { id: "CREDENTIALS", label: "Credential Strategy", icon: "verified" },
              { id: "OPPORTUNITIES", label: "Verified Opportunities", icon: "work" },
              { id: "RESUME", label: "Tailored Resume & ATS", icon: "description" }
            ].map((tab) => (
              <button
                key={tab.id}
                type="button"
                onClick={() => setActiveTab(tab.id as typeof activeTab)}
                className={`px-3 py-1.5 text-xs font-headline-sm rounded flex items-center gap-1.5 transition-all cursor-pointer ${
                  activeTab === tab.id
                    ? "bg-primary text-on-primary font-bold shadow-xs"
                    : "bg-surface-container-low text-on-surface-variant hover:text-on-surface border border-outline-variant/40"
                }`}
              >
                <span className="material-symbols-outlined text-sm">{tab.icon}</span>
                <span>{tab.label}</span>
              </button>
            ))}
          </div>

          {/* TAB 1: Categorized Gap Analysis */}
          {activeTab === "GAPS" && (
            <div className="space-y-4">
              {report.categorized_gaps.map((gap) => (
                <div key={gap.gap_id} className="sketch-border p-4 bg-surface-container-low text-xs">
                  <div className="flex items-center justify-between gap-2 mb-1.5 flex-wrap">
                    <span className={`px-2 py-0.5 rounded font-mono text-[10px] font-bold border ${getGapTypeBadge(gap.gap_type)}`}>
                      {gap.gap_type.replace("_", " ")}
                    </span>
                    <span className="text-[10px] font-mono text-outline uppercase">{gap.severity} Priority</span>
                  </div>
                  <h4 className="font-headline-sm text-base text-on-surface font-bold mb-1">
                    {gap.title}
                  </h4>
                  <p className="text-on-surface-variant font-body-md leading-relaxed mb-2.5">
                    {gap.description}
                  </p>
                  <div className="p-2.5 rounded bg-surface-container border border-primary/20 flex items-center gap-2 text-primary font-body-md">
                    <span className="material-symbols-outlined text-sm shrink-0">task_alt</span>
                    <span><strong>Action:</strong> {gap.recommended_action}</span>
                  </div>
                </div>
              ))}
            </div>
          )}

          {/* TAB 2: Transferable Skills Matrix */}
          {activeTab === "TRANSFERABLE" && (
            <div className="sketch-border p-6 bg-surface-container-low">
              <div className="mb-6">
                <h3 className="font-headline-sm text-xl text-on-surface font-bold mb-1">
                  Transferable Capabilities Breakdown
                </h3>
                <p className="font-body-md text-xs text-on-surface-variant leading-relaxed">
                  {report.transferable_skills.analysis_summary}
                </p>
              </div>

              <div className="grid md:grid-cols-3 gap-4">
                {/* Already Have */}
                <div className="p-4 rounded bg-emerald-950/20 border border-emerald-700/40">
                  <h4 className="font-headline-sm text-sm text-emerald-300 font-bold mb-3 flex items-center gap-1.5">
                    <span className="material-symbols-outlined text-base">check_circle</span>
                    <span>YOU ALREADY HAVE</span>
                  </h4>
                  <ul className="space-y-1.5 text-xs text-on-surface font-body-md">
                    {report.transferable_skills.already_have.map((s, i) => (
                      <li key={i} className="flex items-center gap-1.5">
                        <span className="text-emerald-400 text-xs">&bull;</span>
                        <span>{s}</span>
                      </li>
                    ))}
                  </ul>
                </div>

                {/* Can Reuse */}
                <div className="p-4 rounded bg-sky-950/20 border border-sky-700/40">
                  <h4 className="font-headline-sm text-sm text-sky-300 font-bold mb-3 flex items-center gap-1.5">
                    <span className="material-symbols-outlined text-base">sync</span>
                    <span>YOU CAN REUSE</span>
                  </h4>
                  <ul className="space-y-1.5 text-xs text-on-surface font-body-md">
                    {report.transferable_skills.can_reuse.map((s, i) => (
                      <li key={i} className="flex items-center gap-1.5">
                        <span className="text-sky-400 text-xs">&bull;</span>
                        <span>{s}</span>
                      </li>
                    ))}
                  </ul>
                </div>

                {/* Need to Build */}
                <div className="p-4 rounded bg-amber-950/20 border border-amber-700/40">
                  <h4 className="font-headline-sm text-sm text-amber-300 font-bold mb-3 flex items-center gap-1.5">
                    <span className="material-symbols-outlined text-base">build</span>
                    <span>YOU NEED TO BUILD</span>
                  </h4>
                  <ul className="space-y-1.5 text-xs text-on-surface font-body-md">
                    {report.transferable_skills.need_to_build.map((s, i) => (
                      <li key={i} className="flex items-center gap-1.5">
                        <span className="text-amber-400 text-xs">&bull;</span>
                        <span>{s}</span>
                      </li>
                    ))}
                  </ul>
                </div>
              </div>
            </div>
          )}

          {/* TAB 3: Credential Strategy */}
          {activeTab === "CREDENTIALS" && (
            <div className="space-y-4">
              <div className="p-4 sketch-border border-amber-600 bg-amber-950/20 text-xs text-on-surface">
                <span className="font-bold text-amber-300">PATHMIND Credential Discipline:</span> We evaluate whether certifications are truly necessary vs. building verified GitHub repositories. In software &amp; ML engineering, <strong>PROJECT &gt; ADDITIONAL CERTIFICATE</strong>.
              </div>

              {report.credentials_strategy.map((cred) => (
                <div key={cred.credential_id} className="sketch-border p-4 bg-surface-container-low text-xs">
                  <div className="flex items-center justify-between gap-2 mb-2 flex-wrap">
                    <span className="text-xs font-bold text-on-surface font-headline-sm">{cred.title}</span>
                    <span className="px-2 py-0.5 rounded text-[10px] font-mono font-bold bg-surface-container border border-outline-variant/40 text-on-surface-variant">
                      {cred.classification}
                    </span>
                  </div>
                  <p className="text-on-surface-variant font-body-md mb-2">
                    Issuer: <strong>{cred.issuer}</strong> &bull; Effort: {cred.preparation_effort} &bull; Cost: {cred.verified_cost || "Free"}
                  </p>
                  <p className="text-on-surface font-body-md mb-3 p-2.5 rounded bg-surface-container border border-outline-variant/30">
                    <strong>Strategic Recommendation:</strong> {cred.strategic_advice}
                  </p>
                  <a
                    href={cred.official_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-xs text-primary font-bold hover:underline inline-flex items-center gap-1"
                  >
                    <span>View Official Curriculum Portal</span>
                    <span className="material-symbols-outlined text-xs">open_in_new</span>
                  </a>
                </div>
              ))}
            </div>
          )}

          {/* TAB 4: Verified Opportunities */}
          {activeTab === "OPPORTUNITIES" && (
            <div className="space-y-4">
              {report.matched_opportunities.map((opp) => (
                <div key={opp.opportunity_id} className="sketch-border p-5 bg-surface-container-low text-xs">
                  <div className="flex items-start justify-between gap-4 flex-wrap mb-2">
                    <div>
                      <div className="flex items-center gap-2 mb-1">
                        <span className="font-headline-sm text-lg text-on-surface font-bold">{opp.title}</span>
                        <span className="px-2 py-0.5 rounded text-[10px] font-mono font-bold bg-emerald-950/40 text-emerald-300 border border-emerald-700/40">
                          {opp.fit_level} FIT
                        </span>
                      </div>
                      <p className="text-on-surface-variant font-body-md">
                        {opp.organization} &bull; {opp.location} &bull; {opp.employment_type}
                      </p>
                    </div>

                    <a
                      href={opp.apply_url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="ink-wash-btn-primary px-4 py-1.5 text-xs flex items-center gap-1.5 shrink-0"
                    >
                      <span>Apply via Official Portal</span>
                      <span className="material-symbols-outlined text-xs">open_in_new</span>
                    </a>
                  </div>

                  {/* Fit Reasons */}
                  <div className="mt-3 p-3 rounded bg-surface-container border border-outline-variant/30">
                    <span className="font-bold text-emerald-400 block mb-1">Why this matches your verified profile:</span>
                    <ul className="space-y-1 text-on-surface-variant font-body-md">
                      {opp.fit_reasons.map((r, i) => (
                        <li key={i} className="flex items-center gap-1.5">
                          <span className="text-emerald-400">&bull;</span>
                          <span>{r}</span>
                        </li>
                      ))}
                    </ul>

                    {opp.missing_requirements.length > 0 && (
                      <div className="mt-2 pt-2 border-t border-outline-variant/20">
                        <span className="font-bold text-amber-400 block mb-1">Prerequisite to complete first:</span>
                        <ul className="space-y-1 text-on-surface-variant font-body-md">
                          {opp.missing_requirements.map((m, i) => (
                            <li key={i} className="flex items-center gap-1.5">
                              <span className="text-amber-400">&bull;</span>
                              <span>{m}</span>
                            </li>
                          ))}
                        </ul>
                      </div>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}

          {/* TAB 5: Role-Specific Tailored Resume */}
          {activeTab === "RESUME" && report.tailored_resume_preview && (
            <div className="sketch-border p-6 bg-surface-container-low text-xs">
              <div className="flex items-center justify-between gap-4 flex-wrap mb-6 pb-4 border-b border-outline-variant/40">
                <div>
                  <h3 className="font-headline-sm text-xl text-on-surface font-bold">
                    Tailored Resume for {report.tailored_resume_preview.target_role}
                  </h3>
                  <span className="font-note-handwritten text-xs text-on-surface-variant">
                    Derived exclusively from verified learning milestones and project evidence (Zero hallucination).
                  </span>
                </div>
                <div className="flex items-center gap-2">
                  <span className="text-xs font-mono font-bold text-primary">ATS Match Score:</span>
                  <span className="px-3 py-1 rounded bg-primary-fixed text-primary font-bold text-sm border border-primary/40">
                    {report.tailored_resume_preview.ats_match_score}%
                  </span>
                </div>
              </div>

              {/* Resume Body */}
              <div className="p-6 rounded bg-surface-container border border-outline-variant/40 space-y-4 mb-6">
                <div>
                  <h4 className="font-bold text-xs uppercase text-primary mb-1">Professional Summary</h4>
                  <p className="text-on-surface font-body-md leading-relaxed">
                    {report.tailored_resume_preview.summary}
                  </p>
                </div>

                <div>
                  <h4 className="font-bold text-xs uppercase text-primary mb-1">Verified Technical Skills</h4>
                  <div className="flex flex-wrap gap-1.5">
                    {report.tailored_resume_preview.highlighted_skills.map((s, i) => (
                      <span key={i} className="px-2 py-0.5 rounded bg-surface-container-high border border-outline-variant/40 text-on-surface font-mono text-[11px]">
                        {s}
                      </span>
                    ))}
                  </div>
                </div>

                <div>
                  <h4 className="font-bold text-xs uppercase text-primary mb-2">Verified Projects</h4>
                  <div className="space-y-3">
                    {report.tailored_resume_preview.tailored_projects.map((p, i) => (
                      <div key={i} className="p-3 rounded bg-surface-container-high border border-outline-variant/30">
                        <div className="flex items-center justify-between mb-1">
                          <span className="font-bold text-on-surface">{p.title}</span>
                          <span className="text-[10px] text-emerald-400 font-mono">{p.provenance}</span>
                        </div>
                        <p className="text-on-surface-variant font-body-md mb-1">{p.description}</p>
                        <div className="flex flex-wrap gap-1 text-[10px] font-mono text-outline">
                          {p.technologies.join(" • ")}
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              </div>

              {/* ATS Keyword Breakdown */}
              <div className="p-4 rounded bg-surface-container border border-outline-variant/30">
                <h4 className="font-bold text-xs text-on-surface mb-2">ATS Alignment &amp; Recommendations</h4>
                <div className="grid sm:grid-cols-2 gap-4 mb-3">
                  <div>
                    <span className="text-[11px] font-bold text-emerald-400 block mb-1">Matched Keywords:</span>
                    <p className="text-[11px] font-mono text-on-surface-variant">
                      {report.tailored_resume_preview.ats_matched_keywords.join(", ")}
                    </p>
                  </div>
                  <div>
                    <span className="text-[11px] font-bold text-amber-400 block mb-1">Upcoming Milestone Keywords:</span>
                    <p className="text-[11px] font-mono text-on-surface-variant">
                      {report.tailored_resume_preview.ats_missing_keywords.join(", ")}
                    </p>
                  </div>
                </div>
              </div>
            </div>
          )}
        </div>
      )}

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
