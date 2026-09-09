"use client";

import { useState, useEffect, useCallback } from "react";
import Link from "next/link";
import {
  Target,
  Sparkles,
  ShieldCheck,
  Award,
  Briefcase,
  FileText,
  Clock,
  Compass,
  CheckCircle2,
  AlertTriangle,
  ExternalLink,
  ChevronRight,
  TrendingUp,
  RefreshCw,
  GitBranch,
  Layers,
  Check,
  Info,
  Calendar,
  Zap,
  FolderGit2
} from "lucide-react";

type TabType = "REQUIREMENTS" | "GAPS" | "TRANSFERABLE" | "CREDENTIALS" | "EXPERIENCE" | "OPPORTUNITIES" | "RESUME" | "CHECKPOINTS";

interface RequirementNodeData {
  name: string;
  category: string;
  importance: string;
  description: string;
  source: string;
  status_for_person: "AVAILABLE" | "TRANSFERABLE" | "MISSING" | "UNCERTAIN" | string;
}

interface CareerRequirementGraphData {
  target_role: string;
  target_industry: string;
  source_standards: string[];
  core_skills: RequirementNodeData[];
  supporting_skills: RequirementNodeData[];
  education_requirements: RequirementNodeData[];
  credential_recommendations: RequirementNodeData[];
  experience_requirements: RequirementNodeData[];
  project_evidence_requirements: RequirementNodeData[];
  eligibility_criteria: RequirementNodeData[];
  market_context_notes: string[];
}

interface CategorizedGapData {
  gap_id: string;
  gap_type: string;
  title: string;
  description: string;
  importance: "HIGH" | "MEDIUM" | "LOW" | string;
  source: string;
  reason: string;
  recommended_action: string;
}

interface TransferableSkillsData {
  already_have: string[];
  can_transfer: string[];
  need_to_develop: string[];
  analysis_summary: string;
}

interface VerifiedCredentialData {
  credential_id: string;
  title: string;
  issuer: string;
  classification: "MANDATORY" | "STRONGLY_USEFUL" | "OPTIONAL" | "LOW_VALUE" | "NOT_RELEVANT" | string;
  target_roles: string[];
  prerequisites: string[];
  preparation_effort: string;
  verified_cost?: string | null;
  geographic_relevance: string;
  official_url: string;
  strategic_advice: string;
  decision_rationale: string;
}

interface ExperienceGapData {
  gap_id: string;
  experience_type: string;
  title: string;
  why_it_matters: string;
  how_to_obtain: string;
  evidence_to_prove: string;
  associated_roadmap_stage?: string | null;
}

interface EvidenceRequirementStatusData {
  requirement: string;
  category: string;
  status: "SATISFIED" | "PARTIALLY_SATISFIED" | "MISSING" | "UNKNOWN" | string;
  grounding_evidence: string[];
}

interface EvidencePortfolioData {
  person_id: string;
  skill_evidence: EvidenceRequirementStatusData[];
  project_evidence: EvidenceRequirementStatusData[];
  work_evidence: EvidenceRequirementStatusData[];
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
  source: string;
  fit_level: "HIGH" | "MEDIUM" | "LOW" | string;
  fit_reasons: string[];
  missing_requirements: string[];
  eligibility_blockers: string[];
  pre_application_advice: string;
  market_context?: {
    salary_range?: string;
    employment_outlook: string;
    geography: string;
    data_period: string;
    source: string;
  } | null;
}

interface TailoredResumeData {
  resume_id: string;
  person_id: string;
  target_role: string;
  summary: string;
  highlighted_skills: string[];
  tailored_projects: Array<{
    title: string;
    technologies: string[];
    description: string;
    provenance: string;
  }>;
  verified_experience: Array<{
    role: string;
    organization: string;
    duration: string;
    description: string;
  }>;
  education: Array<{
    degree: string;
    field: string;
    institution: string;
    year: string;
  }>;
  ats_match_score: number;
  ats_matched_keywords: string[];
  ats_missing_keywords: string[];
  ats_recommendations: string[];
  fact_validation_status: "PASSED" | "FAILED" | string;
  unsupported_claims_rejected: string[];
}

interface CareerCheckpointData {
  checkpoint_id: string;
  person_id: string;
  current_role_status: string;
  target: string;
  progress: string;
  what_changed: string;
  skills_gained: string[];
  remaining_gaps: string[];
  credential_status: string;
  experience_status: string;
  opportunity_readiness: string;
  next_best_action: string;
  timestamp: string;
}

interface CareerReadinessReportData {
  person_id: string;
  target_goal: {
    target_role: string;
    target_industry: string;
    geography: string;
    target_timeline: string;
    priority: string;
    version: number;
  };
  current_person_state: string;
  readiness_state: "FOUNDATIONAL" | "DEVELOPING" | "INTERNSHIP_READY" | "ENTRY_LEVEL_READY" | "TRANSITION_READY" | "TARGET_READY" | "ADVANCED" | string;
  readiness_explanation: string;
  next_readiness_milestone: string;
  requirement_graph?: CareerRequirementGraphData | null;
  categorized_gaps: CategorizedGapData[];
  transferable_skills: TransferableSkillsData;
  credentials_strategy: VerifiedCredentialData[];
  experience_gaps: ExperienceGapData[];
  evidence_portfolio?: EvidencePortfolioData | null;
  accountability: AccountabilityData;
  matched_opportunities: VerifiedOpportunityData[];
  tailored_resume_preview?: TailoredResumeData | null;
  error_state?: string | null;
}

export function CareerLaunchpad() {
  const [report, setReport] = useState<CareerReadinessReportData | null>(null);
  const [checkpoints, setCheckpoints] = useState<CareerCheckpointData[]>([]);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState<TabType>("REQUIREMENTS");
  const [personState, setPersonState] = useState<string>("college_student");
  const [isRecordingCheckpoint, setIsRecordingCheckpoint] = useState(false);
  const [checkpointSuccess, setCheckpointSuccess] = useState(false);

  const fetchReadiness = useCallback(async (stateVal = personState) => {
    setLoading(true);
    try {
      const baseUrl = process.env.NEXT_PUBLIC_API_BASE_URL || "https://pathmind-api.onrender.com";
      const personId = typeof window !== "undefined"
        ? (localStorage.getItem("pathmind_user_name")?.toLowerCase().replace(/\s+/g, "-") || "scholar-user")
        : "scholar-user";

      const [resReport, resCheckpoints] = await Promise.all([
        fetch(`${baseUrl}/api/career/readiness?current_state=${encodeURIComponent(stateVal)}`, {
          headers: { "X-Person-ID": personId }
        }),
        fetch(`${baseUrl}/api/career/checkpoints`, {
          headers: { "X-Person-ID": personId }
        })
      ]);

      if (resReport.ok) {
        const data = await resReport.json();
        setReport(data);
      }
      if (resCheckpoints.ok) {
        const chkData = await resCheckpoints.json();
        setCheckpoints(chkData);
      }
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  }, [personState]);

  useEffect(() => {
    fetchReadiness(personState);
  }, [fetchReadiness, personState]);

  const handleStateChange = (newState: string) => {
    setPersonState(newState);
    fetchReadiness(newState);
  };

  const handleRecordCheckpoint = async () => {
    setIsRecordingCheckpoint(true);
    setCheckpointSuccess(false);
    try {
      const baseUrl = process.env.NEXT_PUBLIC_API_BASE_URL || "https://pathmind-api.onrender.com";
      const personId = typeof window !== "undefined"
        ? (localStorage.getItem("pathmind_user_name")?.toLowerCase().replace(/\s+/g, "-") || "scholar-user")
        : "scholar-user";

      const res = await fetch(`${baseUrl}/api/career/checkpoint`, {
        method: "POST",
        headers: { "X-Person-ID": personId }
      });
      if (res.ok) {
        const newChk = await res.json();
        setCheckpoints((prev) => [newChk, ...prev]);
        setCheckpointSuccess(true);
        setTimeout(() => setCheckpointSuccess(false), 4000);
      }
    } catch (e) {
      console.error(e);
    } finally {
      setIsRecordingCheckpoint(false);
    }
  };

  const getReadinessBadge = (stateStr: string) => {
    switch (stateStr) {
      case "TARGET_READY":
      case "ENTRY_LEVEL_READY":
        return "bg-emerald-950/60 text-emerald-300 border-emerald-600/60";
      case "TRANSITION_READY":
      case "INTERNSHIP_READY":
        return "bg-cyan-950/60 text-cyan-300 border-cyan-600/60";
      case "DEVELOPING":
        return "bg-amber-950/60 text-amber-300 border-amber-600/60";
      case "FOUNDATIONAL":
      default:
        return "bg-surface-container text-on-surface-variant border-outline";
    }
  };

  const getClassificationBadge = (classification: string) => {
    switch (classification) {
      case "MANDATORY":
        return "bg-rose-950/60 text-rose-300 border-rose-600/60";
      case "STRONGLY_USEFUL":
        return "bg-emerald-950/60 text-emerald-300 border-emerald-600/60";
      case "OPTIONAL":
        return "bg-blue-950/60 text-blue-300 border-blue-600/60";
      case "LOW_VALUE":
      case "NOT_RELEVANT":
      default:
        return "bg-surface-container text-on-surface-variant border-outline";
    }
  };

  const getStatusNodeBadge = (status: string) => {
    switch (status) {
      case "AVAILABLE":
        return "bg-emerald-950/60 text-emerald-300 border-emerald-600/60";
      case "TRANSFERABLE":
        return "bg-cyan-950/60 text-cyan-300 border-cyan-600/60";
      case "MISSING":
        return "bg-rose-950/60 text-rose-300 border-rose-600/60";
      default:
        return "bg-amber-950/60 text-amber-300 border-amber-600/60";
    }
  };

  return (
    <div className="w-full max-w-7xl mx-auto space-y-8 animate-in fade-in duration-500">
      {/* Header Banner */}
      <div className="relative rounded-3xl overflow-hidden p-8 md:p-12 border border-outline bg-gradient-to-br from-surface-container via-surface to-surface-container-high shadow-2xl">
        <div className="absolute top-0 right-0 w-96 h-96 bg-primary/10 rounded-full blur-3xl pointer-events-none -mr-20 -mt-20" />
        <div className="relative z-10 flex flex-col md:flex-row md:items-center justify-between gap-6">
          <div className="space-y-3">
            <div className="inline-flex items-center gap-2 px-3.5 py-1 rounded-full text-xs font-semibold tracking-wider uppercase bg-primary/15 text-primary border border-primary/30">
              <Sparkles className="w-3.5 h-3.5" />
              Dynamic Career Intelligence &amp; Opportunity Execution
            </div>
            <h1 className="text-3xl md:text-5xl font-extrabold tracking-tight text-on-surface">
              Career Launchpad
            </h1>
            <p className="text-on-surface-variant max-w-3xl text-sm md:text-base leading-relaxed">
              Real-world career navigation driven by verified standards, requirement graphs, transferable skill analysis,
              official credentials, live opportunities, and strict fact-grounded resumes.
            </p>
          </div>

          {/* Persona / State Selector */}
          <div className="flex flex-col gap-2 bg-surface/80 p-4 rounded-2xl border border-outline backdrop-blur-md min-w-[280px]">
            <label className="text-xs font-semibold uppercase tracking-wider text-on-surface-variant flex items-center gap-1.5">
              <Compass className="w-3.5 h-3.5 text-primary" /> Active Career State
            </label>
            <select
              value={personState}
              onChange={(e) => handleStateChange(e.target.value)}
              className="bg-surface-container border border-outline text-on-surface rounded-xl px-3.5 py-2 text-sm font-medium focus:outline-none focus:ring-2 focus:ring-primary transition-all cursor-pointer"
            >
              <option value="college_student">🎓 College / STEM Student (Class 12 / B.Tech)</option>
              <option value="mechanical_engineer">⚙️ Mechanical Engineer (Career Switcher)</option>
              <option value="frontend_developer">💻 Frontend Developer (AI Switcher)</option>
              <option value="working_professional">👔 Working Professional (Promotion / Growth)</option>
              <option value="graduate">🎓 Recent Graduate (First Job Search)</option>
            </select>
          </div>
        </div>
      </div>

      {/* Top Intelligence Grid: Target Outcome, Qualitative Readiness & Accountability */}
      {report && (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* 1. Target Outcome */}
          <div className="bg-surface-container border border-outline rounded-3xl p-6 flex flex-col justify-between shadow-lg relative overflow-hidden">
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <span className="text-xs font-bold uppercase tracking-wider text-on-surface-variant flex items-center gap-1.5">
                  <Target className="w-4 h-4 text-primary" /> Target Outcome
                </span>
                <span className="text-xs px-2.5 py-0.5 rounded-full font-semibold bg-primary/20 text-primary border border-primary/30">
                  Version {report.target_goal.version || 1}
                </span>
              </div>
              <div>
                <h3 className="text-2xl font-bold text-on-surface">
                  {report.target_goal.target_role}
                </h3>
                <p className="text-xs text-on-surface-variant mt-1">
                  {report.target_goal.target_industry} • {report.target_goal.geography}
                </p>
              </div>
              <div className="grid grid-cols-2 gap-2 pt-2 border-t border-outline/50 text-xs text-on-surface-variant">
                <div>
                  <span className="block text-[11px] text-on-surface-variant/70">Timeline</span>
                  <span className="font-semibold text-on-surface">{report.target_goal.target_timeline}</span>
                </div>
                <div>
                  <span className="block text-[11px] text-on-surface-variant/70">Priority</span>
                  <span className="font-semibold text-primary">{report.target_goal.priority}</span>
                </div>
              </div>
            </div>
            <div className="pt-4 mt-4 border-t border-outline/50">
              <Link
                href="/journey"
                className="w-full inline-flex items-center justify-center gap-2 py-2.5 px-4 rounded-xl text-xs font-semibold bg-primary/10 hover:bg-primary/20 text-primary border border-primary/30 transition-all"
              >
                View Active Roadmap Milestones <ChevronRight className="w-3.5 h-3.5" />
              </Link>
            </div>
          </div>

          {/* 2. Qualitative Readiness State */}
          <div className="bg-surface-container border border-outline rounded-3xl p-6 flex flex-col justify-between shadow-lg">
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <span className="text-xs font-bold uppercase tracking-wider text-on-surface-variant flex items-center gap-1.5">
                  <TrendingUp className="w-4 h-4 text-primary" /> Career Readiness
                </span>
                <span className={`text-xs px-3 py-1 rounded-full font-bold uppercase tracking-wider border ${getReadinessBadge(report.readiness_state)}`}>
                  {report.readiness_state.replace(/_/g, " ")}
                </span>
              </div>
              <p className="text-sm text-on-surface leading-relaxed">
                {report.readiness_explanation}
              </p>
              <div className="p-3.5 rounded-2xl bg-surface/70 border border-outline/60 text-xs">
                <span className="text-on-surface-variant font-semibold block text-[11px] uppercase tracking-wider">Next Readiness Milestone</span>
                <span className="text-on-surface font-medium mt-0.5 block">{report.next_readiness_milestone}</span>
              </div>
            </div>
            <div className="pt-4 mt-4 border-t border-outline/50 flex items-center justify-between text-xs text-on-surface-variant">
              <span>Grounded in Code Evidence</span>
              <span className="text-emerald-400 flex items-center gap-1 font-medium">
                <CheckCircle2 className="w-3.5 h-3.5" /> Zero Fake Scoring
              </span>
            </div>
          </div>

          {/* 3. ADK Accountability Partner */}
          <div className="bg-surface-container border border-outline rounded-3xl p-6 flex flex-col justify-between shadow-lg">
            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <span className="text-xs font-bold uppercase tracking-wider text-on-surface-variant flex items-center gap-1.5">
                  <ShieldCheck className="w-4 h-4 text-primary" /> Accountability Partner
                </span>
                <span className="text-xs px-2.5 py-0.5 rounded-full font-bold uppercase tracking-wider bg-emerald-950/60 text-emerald-300 border border-emerald-600/60">
                  {report.accountability.status.replace(/_/g, " ")}
                </span>
              </div>
              <p className="text-xs md:text-sm text-on-surface italic leading-relaxed bg-surface/50 p-3 rounded-2xl border border-outline/50">
                &quot;{report.accountability.mentor_observation}&quot;
              </p>
              {report.accountability.suggested_adjustment && (
                <div className="p-3 rounded-xl bg-primary/10 border border-primary/25 text-xs text-on-surface">
                  <span className="font-semibold text-primary block">Suggested Pacing Adjustment:</span>
                  {report.accountability.suggested_adjustment}
                </div>
              )}
            </div>
            <div className="pt-4 mt-3 border-t border-outline/50 flex items-center justify-between text-xs text-on-surface-variant">
              <span className="flex items-center gap-1">
                <Clock className="w-3.5 h-3.5 text-primary" /> {report.accountability.weekly_commitment_hours} hrs/week commitment
              </span>
              <button
                onClick={handleRecordCheckpoint}
                disabled={isRecordingCheckpoint}
                className="inline-flex items-center gap-1.5 text-xs font-semibold text-primary hover:underline cursor-pointer"
              >
                <RefreshCw className={`w-3.5 h-3.5 ${isRecordingCheckpoint ? "animate-spin" : ""}`} />
                Record Checkpoint
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Checkpoint confirmation toast */}
      {checkpointSuccess && (
        <div className="p-4 rounded-2xl bg-emerald-950/80 border border-emerald-600 text-emerald-300 text-sm font-semibold flex items-center gap-2 animate-in fade-in">
          <CheckCircle2 className="w-4 h-4" /> Career checkpoint snapshot successfully recorded to your longitudinal trajectory!
        </div>
      )}

      {/* Navigation Tabs */}
      <div className="flex flex-wrap gap-2 border-b border-outline pb-4">
        {[
          { id: "REQUIREMENTS", label: "Requirement Graph", icon: GitBranch },
          { id: "GAPS", label: "Gap Analysis", icon: AlertTriangle },
          { id: "TRANSFERABLE", label: "Transferable Skills", icon: Layers },
          { id: "CREDENTIALS", label: "Credential Strategy", icon: Award },
          { id: "EXPERIENCE", label: "Experience & Evidence", icon: FolderGit2 },
          { id: "OPPORTUNITIES", label: "Verified Opportunities", icon: Briefcase },
          { id: "RESUME", label: "Tailored Resume & ATS", icon: FileText },
          { id: "CHECKPOINTS", label: "Checkpoints Timeline", icon: Calendar }
        ].map((tab) => {
          const Icon = tab.icon;
          const isActive = activeTab === tab.id;
          return (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id as TabType)}
              className={`flex items-center gap-2 px-4 py-2.5 rounded-2xl text-xs md:text-sm font-semibold transition-all cursor-pointer ${
                isActive
                  ? "bg-primary text-on-primary shadow-md shadow-primary/20 scale-102"
                  : "bg-surface-container text-on-surface-variant hover:text-on-surface hover:bg-surface-container-high border border-outline"
              }`}
            >
              <Icon className="w-4 h-4" />
              {tab.label}
            </button>
          );
        })}
      </div>

      {/* Tab Panels */}
      {loading ? (
        <div className="py-24 text-center space-y-4">
          <RefreshCw className="w-8 h-8 text-primary animate-spin mx-auto" />
          <p className="text-sm font-medium text-on-surface-variant">Synthesizing verified career intelligence...</p>
        </div>
      ) : report ? (
        <div className="space-y-6">
          {/* TAB 1: REQUIREMENT GRAPH */}
          {activeTab === "REQUIREMENTS" && report.requirement_graph && (
            <div className="space-y-6">
              <div className="bg-surface-container border border-outline rounded-3xl p-6 md:p-8 space-y-6">
                <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
                  <div>
                    <h3 className="text-xl font-bold text-on-surface flex items-center gap-2">
                      <GitBranch className="w-5 h-5 text-primary" /> Target Role Requirement Graph
                    </h3>
                    <p className="text-xs text-on-surface-variant mt-1">
                      Structured requirement graph mapped from official occupational classifications ({report.requirement_graph.source_standards.join(" & ")})
                    </p>
                  </div>
                  <div className="flex items-center gap-2 text-xs">
                    <span className="px-2.5 py-1 rounded-full bg-emerald-950/60 text-emerald-300 border border-emerald-600/60 font-semibold">AVAILABLE</span>
                    <span className="px-2.5 py-1 rounded-full bg-cyan-950/60 text-cyan-300 border border-cyan-600/60 font-semibold">TRANSFERABLE</span>
                    <span className="px-2.5 py-1 rounded-full bg-rose-950/60 text-rose-300 border border-rose-600/60 font-semibold">MISSING</span>
                  </div>
                </div>

                {/* Core & Supporting Skills Breakdown */}
                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                  {/* Core Skills */}
                  <div className="space-y-3">
                    <h4 className="text-xs font-bold uppercase tracking-wider text-on-surface-variant">Core Technical Competencies</h4>
                    <div className="space-y-2.5">
                      {report.requirement_graph.core_skills.map((node, i) => (
                        <div key={i} className="p-4 rounded-2xl bg-surface border border-outline/70 space-y-1.5">
                          <div className="flex items-center justify-between">
                            <span className="font-bold text-sm text-on-surface">{node.name}</span>
                            <span className={`text-[11px] px-2.5 py-0.5 rounded-full font-bold uppercase border ${getStatusNodeBadge(node.status_for_person)}`}>
                              {node.status_for_person}
                            </span>
                          </div>
                          <p className="text-xs text-on-surface-variant">{node.description}</p>
                          <span className="text-[10px] text-on-surface-variant/70 block">Source: {node.source}</span>
                        </div>
                      ))}
                    </div>
                  </div>

                  {/* Supporting Skills & Project Evidence */}
                  <div className="space-y-6">
                    <div className="space-y-3">
                      <h4 className="text-xs font-bold uppercase tracking-wider text-on-surface-variant">Supporting Skills</h4>
                      <div className="space-y-2.5">
                        {report.requirement_graph.supporting_skills.map((node, i) => (
                          <div key={i} className="p-4 rounded-2xl bg-surface border border-outline/70 space-y-1.5">
                            <div className="flex items-center justify-between">
                              <span className="font-bold text-sm text-on-surface">{node.name}</span>
                              <span className={`text-[11px] px-2.5 py-0.5 rounded-full font-bold uppercase border ${getStatusNodeBadge(node.status_for_person)}`}>
                                {node.status_for_person}
                              </span>
                            </div>
                            <p className="text-xs text-on-surface-variant">{node.description}</p>
                          </div>
                        ))}
                      </div>
                    </div>

                    <div className="space-y-3">
                      <h4 className="text-xs font-bold uppercase tracking-wider text-on-surface-variant">Project &amp; Portfolio Evidence Standards</h4>
                      <div className="space-y-2.5">
                        {report.requirement_graph.project_evidence_requirements.map((node, i) => (
                          <div key={i} className="p-4 rounded-2xl bg-surface border border-outline/70 space-y-1">
                            <div className="flex items-center justify-between">
                              <span className="font-bold text-sm text-on-surface">{node.name}</span>
                              <span className="text-[10px] px-2 py-0.5 rounded-md font-semibold bg-primary/10 text-primary border border-primary/20 uppercase">
                                High Signal
                              </span>
                            </div>
                            <p className="text-xs text-on-surface-variant">{node.description}</p>
                          </div>
                        ))}
                      </div>
                    </div>
                  </div>
                </div>

                {/* Market Context Notes */}
                {report.requirement_graph.market_context_notes.length > 0 && (
                  <div className="p-4 rounded-2xl bg-primary/5 border border-primary/20 space-y-2">
                    <h4 className="text-xs font-bold uppercase tracking-wider text-primary flex items-center gap-1.5">
                      <Info className="w-3.5 h-3.5" /> Market Intelligence &amp; Industry Standard Notes
                    </h4>
                    <ul className="space-y-1 text-xs text-on-surface-variant">
                      {report.requirement_graph.market_context_notes.map((note, i) => (
                        <li key={i} className="flex items-start gap-2">
                          <span className="text-primary font-bold">•</span>
                          <span>{note}</span>
                        </li>
                      ))}
                    </ul>
                  </div>
                )}
              </div>
            </div>
          )}

          {/* TAB 2: GAP ANALYSIS */}
          {activeTab === "GAPS" && (
            <div className="space-y-6">
              <div className="bg-surface-container border border-outline rounded-3xl p-6 md:p-8 space-y-6">
                <div className="space-y-1">
                  <h3 className="text-xl font-bold text-on-surface flex items-center gap-2">
                    <AlertTriangle className="w-5 h-5 text-amber-400" /> Multi-Category Gap Analysis
                  </h3>
                  <p className="text-xs text-on-surface-variant">
                    Evaluated across 8 canonical categories (SKILL, EXPERIENCE, EVIDENCE, EDUCATION, CREDENTIAL, PORTFOLIO, ELIGIBILITY, EXPOSURE).
                  </p>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  {report.categorized_gaps.map((gap, i) => (
                    <div key={i} className="p-5 rounded-3xl bg-surface border border-outline space-y-3 shadow-sm">
                      <div className="flex items-center justify-between">
                        <span className="text-[11px] px-2.5 py-0.5 rounded-full font-bold uppercase tracking-wider bg-surface-container-high text-on-surface border border-outline">
                          {gap.gap_type}
                        </span>
                        <span className={`text-[11px] px-2.5 py-0.5 rounded-full font-bold uppercase ${
                          gap.importance === "HIGH" ? "bg-rose-950/60 text-rose-300 border border-rose-600/60" : "bg-blue-950/60 text-blue-300 border border-blue-600/60"
                        }`}>
                          {gap.importance} Severity
                        </span>
                      </div>
                      <div>
                        <h4 className="font-bold text-sm text-on-surface">{gap.title}</h4>
                        <p className="text-xs text-on-surface-variant mt-1 leading-relaxed">{gap.description}</p>
                      </div>
                      <div className="p-3 rounded-2xl bg-surface-container text-xs space-y-1 border border-outline/50">
                        <span className="font-semibold text-primary block text-[11px]">Recommended Action:</span>
                        <p className="text-on-surface">{gap.recommended_action}</p>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          )}

          {/* TAB 3: TRANSFERABLE SKILLS */}
          {activeTab === "TRANSFERABLE" && (
            <div className="space-y-6">
              <div className="bg-surface-container border border-outline rounded-3xl p-6 md:p-8 space-y-6">
                <div>
                  <h3 className="text-xl font-bold text-on-surface flex items-center gap-2">
                    <Layers className="w-5 h-5 text-primary" /> Transferable Capability Engine
                  </h3>
                  <p className="text-xs text-on-surface-variant mt-1">
                    Prevents treating career switchers, experienced developers, or STEM scholars as zero-skill beginners.
                  </p>
                </div>

                <div className="p-4 rounded-2xl bg-primary/10 border border-primary/30 text-xs md:text-sm text-on-surface leading-relaxed font-medium">
                  {report.transferable_skills.analysis_summary}
                </div>

                <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                  {/* YOU ALREADY HAVE */}
                  <div className="p-6 rounded-3xl bg-surface border border-emerald-700/40 space-y-4">
                    <h4 className="text-xs font-bold uppercase tracking-wider text-emerald-400 flex items-center gap-1.5">
                      <CheckCircle2 className="w-4 h-4" /> You Already Have
                    </h4>
                    <ul className="space-y-2 text-xs">
                      {report.transferable_skills.already_have.map((s, i) => (
                        <li key={i} className="flex items-center gap-2 text-on-surface bg-surface-container px-3 py-2 rounded-xl">
                          <span className="w-1.5 h-1.5 rounded-full bg-emerald-400" />
                          <span className="font-medium">{s}</span>
                        </li>
                      ))}
                    </ul>
                  </div>

                  {/* YOU CAN TRANSFER */}
                  <div className="p-6 rounded-3xl bg-surface border border-cyan-700/40 space-y-4">
                    <h4 className="text-xs font-bold uppercase tracking-wider text-cyan-400 flex items-center gap-1.5">
                      <Layers className="w-4 h-4" /> You Can Transfer
                    </h4>
                    <ul className="space-y-2 text-xs">
                      {report.transferable_skills.can_transfer.map((s, i) => (
                        <li key={i} className="flex items-center gap-2 text-on-surface bg-surface-container px-3 py-2 rounded-xl">
                          <span className="w-1.5 h-1.5 rounded-full bg-cyan-400" />
                          <span className="font-medium">{s}</span>
                        </li>
                      ))}
                    </ul>
                  </div>

                  {/* YOU NEED TO DEVELOP */}
                  <div className="p-6 rounded-3xl bg-surface border border-amber-700/40 space-y-4">
                    <h4 className="text-xs font-bold uppercase tracking-wider text-amber-400 flex items-center gap-1.5">
                      <Sparkles className="w-4 h-4" /> You Need To Develop
                    </h4>
                    <ul className="space-y-2 text-xs">
                      {report.transferable_skills.need_to_develop.map((s, i) => (
                        <li key={i} className="flex items-center gap-2 text-on-surface bg-surface-container px-3 py-2 rounded-xl">
                          <span className="w-1.5 h-1.5 rounded-full bg-amber-400" />
                          <span className="font-medium">{s}</span>
                        </li>
                      ))}
                    </ul>
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* TAB 4: CREDENTIAL STRATEGY */}
          {activeTab === "CREDENTIALS" && (
            <div className="space-y-6">
              <div className="bg-surface-container border border-outline rounded-3xl p-6 md:p-8 space-y-6">
                <div>
                  <h3 className="text-xl font-bold text-on-surface flex items-center gap-2">
                    <Award className="w-5 h-5 text-primary" /> Credential Recommendation Engine
                  </h3>
                  <p className="text-xs text-on-surface-variant mt-1">
                    Answers: &quot;Do I actually need this certification?&quot; — Enforces that public code repositories carry higher weight than paid certificates.
                  </p>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                  {report.credentials_strategy.map((cred, i) => (
                    <div key={i} className="p-6 rounded-3xl bg-surface border border-outline flex flex-col justify-between space-y-4 shadow-sm">
                      <div className="space-y-3">
                        <div className="flex items-center justify-between">
                          <span className={`text-[11px] px-3 py-1 rounded-full font-bold uppercase border ${getClassificationBadge(cred.classification)}`}>
                            {cred.classification.replace(/_/g, " ")}
                          </span>
                          <span className="text-xs text-on-surface-variant">{cred.preparation_effort}</span>
                        </div>
                        <div>
                          <h4 className="font-bold text-base text-on-surface">{cred.title}</h4>
                          <p className="text-xs text-on-surface-variant mt-0.5">Issuer: {cred.issuer} • {cred.geographic_relevance}</p>
                        </div>
                        <div className="p-3.5 rounded-2xl bg-surface-container border border-outline/50 space-y-1.5 text-xs">
                          <span className="font-semibold text-primary block text-[11px] uppercase tracking-wider">Strategic Recommendation</span>
                          <p className="text-on-surface leading-relaxed">{cred.strategic_advice}</p>
                        </div>
                      </div>

                      <div className="pt-3 border-t border-outline/50 flex items-center justify-between text-xs">
                        <span className="text-on-surface-variant font-medium">Cost: {cred.verified_cost || "Verified Official"}</span>
                        <a
                          href={cred.official_url}
                          target="_blank"
                          rel="noreferrer"
                          className="inline-flex items-center gap-1.5 text-primary font-semibold hover:underline"
                        >
                          Official Portal <ExternalLink className="w-3.5 h-3.5" />
                        </a>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          )}

          {/* TAB 5: EXPERIENCE & EVIDENCE */}
          {activeTab === "EXPERIENCE" && (
            <div className="space-y-6">
              <div className="bg-surface-container border border-outline rounded-3xl p-6 md:p-8 space-y-6">
                <div>
                  <h3 className="text-xl font-bold text-on-surface flex items-center gap-2">
                    <FolderGit2 className="w-5 h-5 text-primary" /> Experience Gaps &amp; Evidence Portfolio
                  </h3>
                  <p className="text-xs text-on-surface-variant mt-1">
                    Maps required experience types directly to verifiable roadmap stages and evidence portfolio records.
                  </p>
                </div>

                {/* Experience Gaps */}
                <div className="space-y-3">
                  <h4 className="text-xs font-bold uppercase tracking-wider text-on-surface-variant">Required Experience Types</h4>
                  <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                    {report.experience_gaps.map((exp, i) => (
                      <div key={i} className="p-5 rounded-3xl bg-surface border border-outline space-y-3 shadow-sm">
                        <span className="text-[11px] px-2.5 py-0.5 rounded-full font-bold uppercase tracking-wider bg-surface-container-high text-primary border border-outline">
                          {exp.experience_type}
                        </span>
                        <h5 className="font-bold text-sm text-on-surface">{exp.title}</h5>
                        <p className="text-xs text-on-surface-variant">{exp.why_it_matters}</p>
                        <div className="p-3 rounded-2xl bg-surface-container text-xs space-y-1">
                          <span className="text-[10px] uppercase font-bold text-on-surface-variant block">Evidence to Prove:</span>
                          <p className="text-on-surface">{exp.evidence_to_prove}</p>
                        </div>
                        {exp.associated_roadmap_stage && (
                          <span className="text-[11px] text-primary font-semibold block">
                            ↳ Linked to: {exp.associated_roadmap_stage}
                          </span>
                        )}
                      </div>
                    ))}
                  </div>
                </div>

                {/* Evidence Portfolio Satisfaction */}
                {report.evidence_portfolio && (
                  <div className="space-y-3 pt-4 border-t border-outline/60">
                    <h4 className="text-xs font-bold uppercase tracking-wider text-on-surface-variant">Evidence Portfolio Audit</h4>
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                      {report.evidence_portfolio.skill_evidence.map((ev, i) => (
                        <div key={i} className="p-4 rounded-2xl bg-surface border border-outline flex items-center justify-between">
                          <div className="space-y-0.5">
                            <span className="font-bold text-sm text-on-surface">{ev.requirement}</span>
                            <p className="text-xs text-on-surface-variant">{ev.grounding_evidence.join(", ") || "Awaiting code submission"}</p>
                          </div>
                          <span className={`text-[11px] px-2.5 py-0.5 rounded-full font-bold uppercase ${
                            ev.status === "SATISFIED" ? "bg-emerald-950/60 text-emerald-300 border border-emerald-600/60" : "bg-amber-950/60 text-amber-300 border border-amber-600/60"
                          }`}>
                            {ev.status.replace(/_/g, " ")}
                          </span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            </div>
          )}

          {/* TAB 6: VERIFIED OPPORTUNITIES */}
          {activeTab === "OPPORTUNITIES" && (
            <div className="space-y-6">
              <div className="bg-surface-container border border-outline rounded-3xl p-6 md:p-8 space-y-6">
                <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
                  <div>
                    <h3 className="text-xl font-bold text-on-surface flex items-center gap-2">
                      <Briefcase className="w-5 h-5 text-primary" /> Verified Opportunity Matching
                    </h3>
                    <p className="text-xs text-on-surface-variant mt-1">
                      Matched against your active skill evidence. Every result features verified official application portals (zero fabricated listings).
                    </p>
                  </div>
                  <span className="text-xs px-3 py-1 rounded-full font-semibold bg-emerald-950/60 text-emerald-300 border border-emerald-600/60">
                    {report.matched_opportunities.length} Verified Programs Available
                  </span>
                </div>

                <div className="grid grid-cols-1 gap-4">
                  {report.matched_opportunities.map((opp, i) => (
                    <div key={i} className="p-6 rounded-3xl bg-surface border border-outline space-y-4 shadow-sm hover:border-primary/50 transition-all">
                      <div className="flex flex-col md:flex-row md:items-center justify-between gap-2">
                        <div>
                          <div className="flex items-center gap-2">
                            <span className="text-xs px-2.5 py-0.5 rounded-full font-bold uppercase tracking-wider bg-surface-container-high text-on-surface border border-outline">
                              {opp.employment_type}
                            </span>
                            <span className={`text-xs px-2.5 py-0.5 rounded-full font-bold uppercase tracking-wider ${
                              opp.fit_level === "HIGH" ? "bg-emerald-950/60 text-emerald-300 border border-emerald-600/60" : "bg-blue-950/60 text-blue-300 border border-blue-600/60"
                            }`}>
                              {opp.fit_level} MATCH
                            </span>
                          </div>
                          <h4 className="text-lg font-bold text-on-surface mt-2">{opp.title}</h4>
                          <p className="text-xs text-on-surface-variant">{opp.organization} • {opp.location}</p>
                        </div>

                        <a
                          href={opp.apply_url}
                          target="_blank"
                          rel="noreferrer"
                          className="inline-flex items-center justify-center gap-2 px-6 py-3 rounded-2xl text-xs md:text-sm font-bold bg-primary text-on-primary shadow-lg shadow-primary/20 hover:opacity-95 transition-all"
                        >
                          APPLY (Official Portal) <ExternalLink className="w-4 h-4" />
                        </a>
                      </div>

                      {/* Fit reasons and timing */}
                      <div className="grid grid-cols-1 md:grid-cols-2 gap-4 pt-3 border-t border-outline/50 text-xs">
                        <div className="space-y-1.5">
                          <span className="font-semibold text-emerald-400 flex items-center gap-1">
                            <Check className="w-3.5 h-3.5" /> Why This Opportunity Fits
                          </span>
                          <ul className="space-y-1 text-on-surface-variant">
                            {opp.fit_reasons.map((r, idx) => (
                              <li key={idx} className="flex items-start gap-1.5">
                                <span className="text-emerald-400">•</span>
                                <span>{r}</span>
                              </li>
                            ))}
                          </ul>
                        </div>

                        <div className="space-y-1.5">
                          <span className="font-semibold text-amber-400 flex items-center gap-1">
                            <Clock className="w-3.5 h-3.5" /> Timing &amp; Pre-Application Advice
                          </span>
                          <p className="text-on-surface-variant leading-relaxed">{opp.pre_application_advice}</p>
                          {opp.missing_requirements.length > 0 && (
                            <span className="text-[11px] text-rose-300 block">
                              Missing: {opp.missing_requirements.join(", ")}
                            </span>
                          )}
                        </div>
                      </div>

                      {opp.market_context && (
                        <div className="p-3 rounded-xl bg-surface-container text-xs text-on-surface-variant flex flex-wrap items-center justify-between gap-2 border border-outline/40">
                          <span>Compensation / Outlook: <strong className="text-on-surface">{opp.market_context.salary_range}</strong> ({opp.market_context.employment_outlook})</span>
                          <span className="text-[11px] text-on-surface-variant/70">Source: {opp.market_context.source}</span>
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            </div>
          )}

          {/* TAB 7: FACT-VALIDATED RESUME & ATS */}
          {activeTab === "RESUME" && report.tailored_resume_preview && (
            <div className="space-y-6">
              <div className="bg-surface-container border border-outline rounded-3xl p-6 md:p-8 space-y-6">
                <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
                  <div>
                    <h3 className="text-xl font-bold text-on-surface flex items-center gap-2">
                      <FileText className="w-5 h-5 text-primary" /> Role-Specific Tailored Resume (Strictly Fact-Validated)
                    </h3>
                    <p className="text-xs text-on-surface-variant mt-1">
                      Derived exclusively from verified profile facts. Failsafe validation rejects any hallucinated experience or technologies.
                    </p>
                  </div>
                  <div className="flex items-center gap-3">
                    <span className="text-xs px-3 py-1 rounded-full font-bold bg-emerald-950/60 text-emerald-300 border border-emerald-600/60 flex items-center gap-1.5">
                      <ShieldCheck className="w-4 h-4" /> FACT VALIDATION: {report.tailored_resume_preview.fact_validation_status}
                    </span>
                    <span className="text-xs px-3 py-1 rounded-full font-bold bg-primary/20 text-primary border border-primary/30">
                      ATS Score: {report.tailored_resume_preview.ats_match_score}/100
                    </span>
                  </div>
                </div>

                {/* ATS Analysis Panel */}
                <div className="p-5 rounded-2xl bg-surface border border-outline space-y-3">
                  <h4 className="text-xs font-bold uppercase tracking-wider text-primary flex items-center gap-1.5">
                    <Zap className="w-3.5 h-3.5" /> ATS Keyword &amp; Evidence Optimization
                  </h4>
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs">
                    <div>
                      <span className="text-on-surface-variant font-semibold block mb-1">Matched Keywords in Profile:</span>
                      <div className="flex flex-wrap gap-1.5">
                        {report.tailored_resume_preview.ats_matched_keywords.map((kw, i) => (
                          <span key={i} className="px-2 py-0.5 rounded-md bg-emerald-950/60 text-emerald-300 border border-emerald-700/50 text-[11px] font-medium">
                            ✓ {kw}
                          </span>
                        ))}
                      </div>
                    </div>
                    <div>
                      <span className="text-on-surface-variant font-semibold block mb-1">Upcoming Target Keywords:</span>
                      <div className="flex flex-wrap gap-1.5">
                        {report.tailored_resume_preview.ats_missing_keywords.map((kw, i) => (
                          <span key={i} className="px-2 py-0.5 rounded-md bg-rose-950/60 text-rose-300 border border-rose-700/50 text-[11px] font-medium">
                            ⚠ {kw}
                          </span>
                        ))}
                      </div>
                    </div>
                  </div>
                </div>

                {/* Document View */}
                <div className="p-8 rounded-3xl bg-surface border border-outline space-y-6 shadow-inner font-mono text-xs text-on-surface">
                  <div className="border-b border-outline pb-4 space-y-1">
                    <h4 className="text-base font-bold tracking-tight text-primary uppercase">{report.tailored_resume_preview.target_role}</h4>
                    <p className="text-on-surface-variant leading-relaxed text-xs font-sans">{report.tailored_resume_preview.summary}</p>
                  </div>

                  {/* Highlighted Skills */}
                  <div className="space-y-2">
                    <span className="font-bold text-[11px] uppercase tracking-wider text-on-surface-variant">Technical Skills &amp; Foundations</span>
                    <p className="font-sans text-xs text-on-surface">{report.tailored_resume_preview.highlighted_skills.join(" • ")}</p>
                  </div>

                  {/* Tailored Projects */}
                  <div className="space-y-3">
                    <span className="font-bold text-[11px] uppercase tracking-wider text-on-surface-variant">Verified Project Repositories</span>
                    <div className="space-y-3">
                      {report.tailored_resume_preview.tailored_projects.map((proj, i) => (
                        <div key={i} className="p-3.5 rounded-xl bg-surface-container border border-outline/50 space-y-1 font-sans">
                          <div className="flex items-center justify-between">
                            <span className="font-bold text-xs text-on-surface">{proj.title}</span>
                            <span className="text-[10px] px-2 py-0.5 rounded-md bg-primary/10 text-primary border border-primary/20">
                              {proj.provenance}
                            </span>
                          </div>
                          <p className="text-xs text-on-surface-variant">{proj.description}</p>
                          <span className="text-[11px] text-on-surface-variant/80 font-mono block">Tech: {proj.technologies.join(", ")}</span>
                        </div>
                      ))}
                    </div>
                  </div>

                  {/* Education */}
                  <div className="space-y-2">
                    <span className="font-bold text-[11px] uppercase tracking-wider text-on-surface-variant">Education &amp; Academic Record</span>
                    {report.tailored_resume_preview.education.map((edu, i) => (
                      <div key={i} className="font-sans text-xs flex items-center justify-between">
                        <span>{edu.degree} — {edu.field} ({edu.institution})</span>
                        <span className="text-on-surface-variant">{edu.year}</span>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* TAB 8: CHECKPOINTS TIMELINE */}
          {activeTab === "CHECKPOINTS" && (
            <div className="space-y-6">
              <div className="bg-surface-container border border-outline rounded-3xl p-6 md:p-8 space-y-6">
                <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
                  <div>
                    <h3 className="text-xl font-bold text-on-surface flex items-center gap-2">
                      <Calendar className="w-5 h-5 text-primary" /> Longitudinal Career Checkpoints
                    </h3>
                    <p className="text-xs text-on-surface-variant mt-1">
                      Historical record of readiness state evolution, skills gained, remaining gaps, and next best actions.
                    </p>
                  </div>
                  <button
                    onClick={handleRecordCheckpoint}
                    disabled={isRecordingCheckpoint}
                    className="inline-flex items-center gap-2 px-5 py-2.5 rounded-2xl text-xs font-bold bg-primary text-on-primary shadow-md hover:opacity-95 cursor-pointer"
                  >
                    <RefreshCw className={`w-3.5 h-3.5 ${isRecordingCheckpoint ? "animate-spin" : ""}`} />
                    Record Current Checkpoint
                  </button>
                </div>

                {checkpoints.length === 0 ? (
                  <div className="p-8 text-center rounded-2xl bg-surface border border-outline text-xs text-on-surface-variant">
                    No checkpoints recorded yet. Click &quot;Record Current Checkpoint&quot; to generate your first longitudinal career checkpoint snapshot.
                  </div>
                ) : (
                  <div className="space-y-4">
                    {checkpoints.map((chk, i) => (
                      <div key={i} className="p-6 rounded-3xl bg-surface border border-outline space-y-3 shadow-sm">
                        <div className="flex items-center justify-between text-xs">
                          <span className="font-bold text-primary">{chk.target}</span>
                          <span className="text-on-surface-variant">{new Date(chk.timestamp).toLocaleString()}</span>
                        </div>
                        <div className="p-3 rounded-xl bg-surface-container text-xs text-on-surface">
                          <strong>Progress:</strong> {chk.progress}
                        </div>
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs text-on-surface-variant">
                          <div>
                            <span className="font-semibold text-on-surface block mb-1">What Changed / Verified:</span>
                            <p>{chk.what_changed}</p>
                          </div>
                          <div>
                            <span className="font-semibold text-primary block mb-1">Next Best Action:</span>
                            <p className="text-on-surface">{chk.next_best_action}</p>
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>
          )}
        </div>
      ) : (
        <div className="p-12 text-center rounded-3xl bg-surface-container border border-outline space-y-3">
          <AlertTriangle className="w-8 h-8 text-amber-400 mx-auto" />
          <h3 className="text-base font-bold text-on-surface">Unable to load live career readiness</h3>
          <p className="text-xs text-on-surface-variant">Please verify that the backend services are reachable.</p>
        </div>
      )}
    </div>
  );
}
