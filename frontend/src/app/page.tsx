"use client";

import { useState, useEffect, useRef } from "react";
import { motion } from "framer-motion";
import { TopBar } from "@/components/layout/TopBar";
import { validateMeaningfulText } from "@/components/pathmind/steps/GoalStep";
import { VerificationStep } from "@/components/pathmind/steps/VerificationStep";
import { AspirationTestStep } from "@/components/pathmind/steps/AspirationTestStep";
import { authedFetch } from "@/lib/api";
import { ClaimBadge } from "@/components/pathmind/trust/ClaimBadge";
import type { TestEvaluation } from "@/components/pathmind/steps/AspirationTestStep";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000";

export interface EvidenceItem {
  source: string;
  type: string; // file, link, project_description
  name: string;
  description: string;
  url?: string;
  confidence: string;
  timestamp: string;
}

export interface AssessmentItem {
  item_id: string;
  type: string;
  construct: string;
  prompt: string;
  context: string;
  rubric?: string;
  scale?: { value: number; label: string }[];
}

export interface AssessmentBlueprint {
  blueprint_id: string;
  domain: string;
  stage_calibration: string;
  items: AssessmentItem[];
}

export interface CandidatePath {
  path_id: string;
  title: string;
  description: string;
  time_horizon_months?: number;
  risk_level?: string;
  estimated_outcomes?: { compensation_range?: string; role_trajectory?: string };
  trade_offs?: string[];
  pros?: string[];
  cons?: string[];
}

export interface RoadmapMission {
  mission_id: string;
  title: string;
  objective: string;
  activities: string[];
  evidence_type: string;
}

export interface RoadmapStage {
  stage_id: string;
  stage_number: number;
  title: string;
  locked: boolean;
  why_now?: string;
  missions?: RoadmapMission[];
  prerequisites?: string[];
}

export interface DisclosedRoadmap {
  roadmap_id: string;
  target_outcome: string;
  total_stages: number;
  stages: RoadmapStage[];
  active_stage: RoadmapStage | null;
}

export interface RecommendedEvidenceItem {
  type: string;
  category: string;
  title: string;
  description: string;
  example?: string;
}

export interface EvidenceRequirements {
  domain_title: string;
  stage_expectation: string;
  recommended_evidence?: RecommendedEvidenceItem[];
  evaluation_criteria?: string[];
}

export interface ClassifiedClaim {
  text: string;
  claim_category: string;
  verification_status: string;
}

export interface GroundedAssessment {
  potential: string;
  potential_claims?: ClassifiedClaim[];
  strengths: (string | ClassifiedClaim)[];
  gaps: (string | ClassifiedClaim)[];
  path_outline: (string | ClassifiedClaim)[];
  uncertainty: string[];
  source?: string;
  generated_at?: string;
}

export interface EvaluationResult {
  competence_score: number;
  depth_rating: string;
  demonstrated_strengths: string[];
  growth_areas: string[];
  evaluation_narrative: string;
  riasec_inference?: Record<string, number>;
  scct_calibration?: Record<string, number>;
}

export interface PhaseEvalResult {
  status: string;
  feedback?: string;
  demonstrated?: string[];
}

const PERSONAS = [
  { id: "school", title: "School Student", icon: "school", desc: "Exploring foundational horizons & career clarity" },
  { id: "college", title: "College Student", icon: "account_balance", desc: "Navigating major specialization & practical readiness" },
  { id: "professional", title: "Professional", icon: "work", desc: "Advancing senior craft and domain leadership" },
  { id: "business", title: "Business Owner", icon: "storefront", desc: "Running my own venture and growing it" },
  { id: "switcher", title: "Career Switcher", icon: "alt_route", desc: "Transitioning toward a completely new discipline" },
  { id: "lifelong", title: "Lifelong Scholar", icon: "menu_book", desc: "Pursuing rigorous, self-directed intellectual mastery" },
];

const JOURNEY_STEPS = [
  { id: 0, title: "Initiation", subtitle: "Name & Identity" },
  { id: 1, title: "Aspiration", subtitle: "Goal & Stage" },
  { id: 2, title: "Verification", subtitle: "Prove It's You" },
  { id: 3, title: "Aptitude Test", subtitle: "Aspiration Diagnostic" },
  { id: 4, title: "Evidence", subtitle: "Proof Intake" },
  { id: 5, title: "Assessment", subtitle: "Diagnostic Engine" },
  { id: 6, title: "Trajectory", subtitle: "Grounded Pathways" },
  { id: 7, title: "Roadmap", subtitle: "Active Phase" },
];

export default function GuidedJourneyPage() {
  // Current step in state machine (0 to 5)
  const [currentStep, setCurrentStep] = useState<number>(0);
  const [loading, setLoading] = useState<boolean>(false);
  const [loadingMessage, setLoadingMessage] = useState<string>("");
  const [errorMessage, setErrorMessage] = useState<string>("");

  // Persisted identity
  const [personId, setPersonId] = useState<string | null>(null);
  const [name, setName] = useState<string>("");
  const [nameTouched, setNameTouched] = useState<boolean>(false);

  // Aspiration & Stage
  const [stage, setStage] = useState<string>("college");
  const [aspiration, setAspiration] = useState<string>("");
  const [aspirationTouched, setAspirationTouched] = useState<boolean>(false);
  const [constraints, setConstraints] = useState<string>("12 hours weekly self-directed bandwidth");

  // Evidence
  const [evidenceList, setEvidenceList] = useState<EvidenceItem[]>([]);
  const [evidenceRequirements, setEvidenceRequirements] = useState<EvidenceRequirements | null>(null);
  const [domainStatus, setDomainStatus] = useState<"charted" | "uncharted" | null>(null);
  const [verificationData, setVerificationData] = useState<Record<string, unknown> | null>(null);
  const [testResult, setTestResult] = useState<TestEvaluation | null>(null);
  const [groundedAssessment, setGroundedAssessment] = useState<GroundedAssessment | null>(null);
  const [assessmentLoading, setAssessmentLoading] = useState(false);
  const [activeEvTab, setActiveEvTab] = useState<"projects" | "links" | "files">("projects");
  const [projectTitle, setProjectTitle] = useState("");
  const [projectDesc, setProjectDesc] = useState("");
  const [linkUrl, setLinkUrl] = useState("");
  const [linkLabel, setLinkLabel] = useState("");
  const fileInputRef = useRef<HTMLInputElement>(null);

  // Diagnostic Assessment Blueprint & Responses
  const [blueprint, setBlueprint] = useState<AssessmentBlueprint | null>(null);
  const [assessmentResponses, setAssessmentResponses] = useState<Record<string, string | number>>({});

  // Baseline Evaluation & Pathways
  const [evaluationResult, setEvaluationResult] = useState<EvaluationResult | null>(null);
  const [candidatePaths, setCandidatePaths] = useState<CandidatePath[]>([]);
  const [selectedPathId, setSelectedPathId] = useState<string | null>(null);

  // Active Roadmap & Evidence Gate
  const [roadmap, setRoadmap] = useState<DisclosedRoadmap | null>(null);
  const [phaseSubmissionMissionId, setPhaseSubmissionMissionId] = useState<string>("");
  const [phaseSubmissionCode, setPhaseSubmissionCode] = useState<string>("");
  const [phaseEvalResult, setPhaseEvalResult] = useState<PhaseEvalResult | null>(null);

  // Auto-rehydrate session on fresh load
  useEffect(() => {
    const rehydrate = async () => {
      if (typeof window === "undefined") return;

      try {
        setLoading(true);
        setLoadingMessage("Rehydrating your longitudinal scholar session...");
        // Backend derives identity from the Supabase JWT; no stored ID needed.
        const res = await authedFetch(`/api/orchestrate/journey/state`);

        if (res.ok) {
          const state = await res.json();
          setPersonId(state.person_id);
          setName(state.name || "");
          if (state.aspiration) setAspiration(state.aspiration);
          if (state.stage) setStage(state.stage);
          if (state.evidence) setEvidenceList(state.evidence);
          if (state.evidence_requirements) setEvidenceRequirements(state.evidence_requirements);
          if (state.grounded_assessment) setGroundedAssessment(state.grounded_assessment);
          if (state.assessment_blueprint) setBlueprint(state.assessment_blueprint);
          if (state.assessment_evaluation) setEvaluationResult(state.assessment_evaluation);
          if (state.candidate_paths && state.candidate_paths.length > 0) setCandidatePaths(state.candidate_paths);
          if (state.selected_path_id) setSelectedPathId(state.selected_path_id);
          if (state.active_roadmap) setRoadmap(state.active_roadmap);

          // Map backend step to frontend step
          if (state.active_roadmap) {
            setCurrentStep(7);
          } else if (state.candidate_paths && state.candidate_paths.length > 0) {
            setCurrentStep(6);
          } else if (state.assessment_blueprint) {
            setCurrentStep(5);
          } else if (state.evidence_requirements) {
            // Evidence requirements are issued at aspiration time; the
            // verification (step 2) and aptitude test (step 3) gates sit
            // between aspiration and evidence.
            const verified =
              typeof window !== "undefined" &&
              localStorage.getItem("pathmind_verification_complete") === "1";
            const tested =
              typeof window !== "undefined" &&
              localStorage.getItem("pathmind_test_complete") === "1";
            setCurrentStep(!verified ? 2 : !tested ? 3 : 4);
          } else if (state.aspiration) {
            setCurrentStep(2);
          } else {
            setCurrentStep(1);
          }
        }
      } catch (err) {
        console.warn("Session rehydration notice:", err);
      } finally {
        setLoading(false);
      }
    };

    rehydrate();
  }, []);

  // --------------------------------------------------------------------------
  // STEP 0: NAME COLLECTION -> IMMEDIATE CANONICAL PERSON CREATION (Req 3)
  // --------------------------------------------------------------------------
  const handleNameSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (name.trim().length < 2) return;

    setLoading(true);
    setLoadingMessage("Creating canonical scholar record in Firestore...");
    setErrorMessage("");

    try {
      const res = await authedFetch(`/api/orchestrate/journey/init`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name: name.trim() }),
      });

      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || "Failed to initialize scholar identity.");
      }

      const data = await res.json();
      setPersonId(data.person_id);
      localStorage.setItem("pathmind_person_id", data.person_id);
      localStorage.setItem("pathmind_user_name", data.name);
      if (typeof window !== "undefined") {
        window.dispatchEvent(new Event("pathmind_identity_changed"));
      }
      setCurrentStep(1);
    } catch (err: unknown) {
      const e = err as Error;
      setErrorMessage(e.message || "Failed to establish identity. Please check your connection.");
    } finally {
      setLoading(false);
    }
  };

  // --------------------------------------------------------------------------
  // STEP 1: ASPIRATION & STAGE SUBMISSION -> EVIDENCE REQUIREMENTS (Req 8, 9)
  // --------------------------------------------------------------------------
  const aspirationValidation = validateMeaningfulText(aspiration);

  const handleAspirationSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!aspirationValidation.isValid || !personId) return;

    setLoading(true);
    setLoadingMessage("Calibrating domain requirements and stage expectations with Google ADK...");
    setErrorMessage("");

    try {
      const res = await authedFetch(`/api/orchestrate/journey/aspiration`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          aspiration: aspiration.trim(),
          stage: stage,
          constraints: constraints ? [constraints.trim()] : [],
        }),
      });

      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || "Failed to record aspiration.");
      }

      const data = await res.json();
      setEvidenceRequirements(data.evidence_requirements);
      if (data.domain_status === "uncharted" || data.domain_status === "charted") {
        setDomainStatus(data.domain_status);
      }

      localStorage.setItem("pathmind_user_goal", aspiration.trim());
      localStorage.setItem("pathmind_user_identity", stage);
      setCurrentStep(2);
    } catch (err: unknown) {
      const e = err as Error;
      setErrorMessage(e.message || "Failed to record aspiration.");
    } finally {
      setLoading(false);
    }
  };

  // STEP 2: VERIFICATION COMPLETE -> EVIDENCE INTAKE
  const handleVerificationNext = (data: Record<string, unknown>) => {
    setVerificationData(data);
    if (typeof window !== "undefined") {
      try {
        localStorage.setItem("pathmind_verification_complete", "1");
      } catch {
        // storage unavailable — verification still counts for this session
      }
    }
    setCurrentStep(3);
  };

  // STEP 3: APTITUDE TEST COMPLETE -> GROUNDED ASSESSMENT -> EVIDENCE INTAKE
  // AJ's core loop: potential/gaps/path are computed AFTER the learner has
  // proven themselves (verification + test), grounded in real evidence.
  const handleTestNext = async (result: TestEvaluation) => {
    setTestResult(result);
    if (typeof window !== "undefined") {
      try {
        localStorage.setItem("pathmind_test_complete", "1");
      } catch {
        // storage unavailable — test still counts for this session
      }
    }
    // Fetch the grounded assessment (verification + test evidence)
    setAssessmentLoading(true);
    try {
      const resp = await authedFetch("/api/orchestrate/journey/grounded-assessment", {
        method: "POST",
      });
      if (resp.ok) {
        const data = await resp.json();
        setGroundedAssessment(data);
      }
    } catch {
      // assessment fetch failed — evidence step still works
    } finally {
      setAssessmentLoading(false);
    }
    setCurrentStep(4);
  };

  // --------------------------------------------------------------------------
  // STEP 4: EVIDENCE SUBMISSION -> EVALUATION & BLUEPRINT (Req 8, 9)
  // --------------------------------------------------------------------------
  const handleAddProjectEvidence = (e: React.FormEvent) => {
    e.preventDefault();
    if (!projectTitle.trim() || !projectDesc.trim()) return;

    const newItem: EvidenceItem = {
      source: "candidate_case_study",
      type: "project_description",
      name: projectTitle.trim(),
      description: projectDesc.trim(),
      confidence: "HIGH",
      timestamp: new Date().toISOString(),
    };

    setEvidenceList((prev) => [...prev, newItem]);
    setProjectTitle("");
    setProjectDesc("");
  };

  const handleAddLinkEvidence = (e: React.FormEvent) => {
    e.preventDefault();
    if (!linkUrl.trim()) return;

    const newItem: EvidenceItem = {
      source: "candidate_portfolio_link",
      type: "link",
      name: linkLabel.trim() || linkUrl.trim(),
      description: `Public URL / Portfolio: ${linkUrl.trim()}`,
      url: linkUrl.trim(),
      confidence: "HIGH",
      timestamp: new Date().toISOString(),
    };

    setEvidenceList((prev) => [...prev, newItem]);
    setLinkUrl("");
    setLinkLabel("");
  };

  const handleFileUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (!e.target.files || e.target.files.length === 0) return;
    const files = Array.from(e.target.files);
    const newItems: EvidenceItem[] = files.map((file) => ({
      source: "candidate_file_upload",
      type: "file",
      name: file.name,
      description: `Document (${(file.size / 1024).toFixed(1)} KB, type: ${file.type || "pdf/doc"})`,
      confidence: "HIGH",
      timestamp: new Date().toISOString(),
    }));

    setEvidenceList((prev) => [...prev, ...newItems]);
  };

  const handleEvidenceSubmit = async () => {
    if (!personId) return;

    setLoading(true);
    setLoadingMessage("Evaluating evidence and synthesizing domain-neutral assessment blueprint...");
    setErrorMessage("");

    try {
      const res = await authedFetch(`/api/orchestrate/journey/evidence`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ evidence: evidenceList }),
      });

      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || "Failed to process evidence.");
      }

      const data = await res.json();
      setBlueprint(data.assessment_blueprint);
      setCurrentStep(5);
    } catch (err: unknown) {
      const e = err as Error;
      setErrorMessage(e.message || "Failed to generate assessment blueprint.");
    } finally {
      setLoading(false);
    }
  };

  // --------------------------------------------------------------------------
  // STEP 4: ACTUAL ASSESSMENT SUBMISSION -> BASELINE PROFILE (Req 8, 9)
  // --------------------------------------------------------------------------
  const handleAssessmentAnswerChange = (itemId: string, val: string | number) => {
    setAssessmentResponses((prev) => ({ ...prev, [itemId]: val }));
  };

  const handleAssessmentSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!personId || !blueprint) return;

    const formattedResponses = blueprint.items.map((item) => ({
      item_id: item.item_id,
      response_value: assessmentResponses[item.item_id] ?? "Demonstrated initial foundational understanding",
    }));

    setLoading(true);
    setLoadingMessage("Objectively evaluating diagnostic answers and synthesizing baseline profile...");
    setErrorMessage("");

    try {
      const res = await authedFetch(`/api/orchestrate/journey/assessment`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ responses: formattedResponses }),
      });

      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || "Assessment evaluation failed.");
      }

      const data = await res.json();
      setEvaluationResult(data.assessment_evaluation);

      // Immediately discover grounded candidate pathways
      setLoadingMessage("Discovering transparent empirical candidate pathways...");
      const pathRes = await authedFetch(`/api/orchestrate/journey/discover-paths`, {
        method: "POST",
        headers: {},
      });

      if (!pathRes.ok) {
        throw new Error("Failed to discover candidate pathways.");
      }

      const pathData = await pathRes.json();
      setCandidatePaths(pathData.candidate_paths || []);
      setCurrentStep(6);
    } catch (err: unknown) {
      const e = err as Error;
      setErrorMessage(e.message || "Diagnostic evaluation encountered an error.");
    } finally {
      setLoading(false);
    }
  };

  // --------------------------------------------------------------------------
  // STEP 5: USER CHOICE -> PROGRESSIVE HIDDEN ROADMAP (Req 8, 10)
  // --------------------------------------------------------------------------
  const handleSelectPathway = async (pathId: string) => {
    if (!personId) return;

    setLoading(true);
    setLoadingMessage("Synthesizing multi-phase hidden roadmap with Phase 1 unlocked...");
    setErrorMessage("");
    setSelectedPathId(pathId);

    try {
      const res = await authedFetch(`/api/orchestrate/journey/select-path`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ selected_path_id: pathId }),
      });

      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || "Failed to initialize roadmap.");
      }

      const data = await res.json();
      setRoadmap(data.roadmap);
      setCurrentStep(7);
    } catch (err: unknown) {
      const e = err as Error;
      setErrorMessage(e.message || "Failed to select pathway.");
    } finally {
      setLoading(false);
    }
  };

  // --------------------------------------------------------------------------
  // STEP 6: SUBMIT PHASE EVIDENCE FOR UNLOCK GATE (Req 10)
  // --------------------------------------------------------------------------
  const handlePhaseEvidenceSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!personId || !roadmap || !roadmap.active_stage) return;

    const missionId =
      phaseSubmissionMissionId ||
      (roadmap.active_stage.missions && roadmap.active_stage.missions[0]?.mission_id) ||
      "mission_01_modular_parser";

    setLoading(true);
    setLoadingMessage("Deterministic backend validating evidence against unlock criteria (PASS/REINFORCE)...");
    setErrorMessage("");
    setPhaseEvalResult(null);

    try {
      const res = await authedFetch(`/api/orchestrate/journey/submit-phase-evidence`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          stage_id: roadmap.active_stage.stage_id,
          mission_id: missionId,
          content_payload: {
            code: phaseSubmissionCode,
            text: phaseSubmissionCode,
          },
        }),
      });

      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || "Evidence unlock verification rejected.");
      }

      const data = await res.json();
      setPhaseEvalResult(data.evaluation);
      setRoadmap(data.roadmap);
    } catch (err: unknown) {
      const e = err as Error;
      setErrorMessage(e.message || "Evidence verification failed.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex min-h-screen flex-col bg-surface">
      <TopBar scholarName={name} personId={personId} />

      <main className="flex-1 flex flex-col items-center justify-start px-4 sm:px-6 md:px-10 py-8 relative z-10 w-full max-w-5xl mx-auto space-y-8">
        
        {/* Subtle In-Journey Progress Indicator (Req 2) */}
        <div className="w-full bg-surface-container-low/80 sketch-border p-3 sm:p-4">
          <div className="flex items-center justify-between overflow-x-auto gap-2 text-xs font-label-md">
            {JOURNEY_STEPS.map((step, idx) => {
              const isCompleted = currentStep > step.id;
              const isCurrent = currentStep === step.id;

              return (
                <div
                  key={step.id}
                  className={`flex items-center gap-2 shrink-0 px-2 py-1 rounded transition-colors ${
                    isCurrent
                      ? "bg-primary-fixed/40 text-on-surface font-semibold"
                      : isCompleted
                      ? "text-primary opacity-90"
                      : "text-outline/60"
                  }`}
                >
                  <div
                    className={`w-6 h-6 rounded-full flex items-center justify-center text-xs border ${
                      isCurrent
                        ? "border-primary bg-primary text-white"
                        : isCompleted
                        ? "border-primary bg-primary/20 text-primary"
                        : "border-outline/40 bg-surface-container text-outline"
                    }`}
                  >
                    {isCompleted ? (
                      <span className="material-symbols-outlined text-sm">check</span>
                    ) : (
                      step.id + 1
                    )}
                  </div>
                  <div className="flex flex-col text-left">
                    <span className="leading-tight">{step.title}</span>
                    <span className="font-note-handwritten text-[11px] opacity-80 hidden sm:inline">
                      {step.subtitle}
                    </span>
                  </div>
                  {idx < JOURNEY_STEPS.length - 1 && (
                    <span className="material-symbols-outlined text-xs text-outline/30 ml-2 hidden md:inline">
                      chevron_right
                    </span>
                  )}
                </div>
              );
            })}
          </div>
        </div>

        {/* Global Loading Overlay */}
        {loading && (
          <div className="w-full p-8 sketch-border bg-surface-container-low/95 text-center flex flex-col items-center justify-center gap-4 animate-in fade-in">
            <div className="w-12 h-12 rounded-full border-2 border-primary bg-primary/10 flex items-center justify-center">
              <span className="material-symbols-outlined text-2xl text-primary animate-spin">
                auto_awesome
              </span>
            </div>
            <div>
              <p className="font-headline-sm text-lg text-on-surface mb-1">Reasoning & Synthesizing...</p>
              <p className="font-note-handwritten text-xl text-secondary">{loadingMessage}</p>
            </div>
          </div>
        )}

        {/* Global Error Banner */}
        {errorMessage && !loading && (
          <div className="w-full p-4 sketch-border bg-error/10 border-error/40 text-error flex items-center gap-3">
            <span className="material-symbols-outlined text-2xl shrink-0">error</span>
            <div className="flex-1 text-sm font-body-md">
              <strong>Notice: </strong>
              {errorMessage}
            </div>
            <button
              onClick={() => setErrorMessage("")}
              className="text-error hover:opacity-70 text-sm font-bold cursor-pointer"
            >
              Dismiss
            </button>
          </div>
        )}

        {/* ================================================================= */}
        {/* STEP 0: NAME COLLECTION & IMMEDIATE PERSON INITIALIZATION (Req 3) */}
        {/* ================================================================= */}
        {!loading && currentStep === 0 && (
          <motion.div
            key="step-0"
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -12 }}
            className="w-full max-w-2xl text-center space-y-6"
          >
            <div className="inline-flex h-16 w-16 items-center justify-center rounded-full border-2 border-primary bg-primary/10 text-primary mb-2">
              <span className="material-symbols-outlined text-3xl" style={{ fontVariationSettings: "'FILL' 1" }}>
                history_edu
              </span>
            </div>

            <div className="space-y-3">
              <div className="inline-flex items-center gap-2 px-4 py-1.5 sketchy-chip text-tertiary">
                <span className="font-note-handwritten text-xl font-medium">Chapter I: The Initiation</span>
              </div>
              <h1 className="font-headline-lg text-4xl sm:text-5xl text-on-surface">
                Where does your journey begin?
              </h1>
              <p className="font-note-handwritten text-2xl text-on-surface-variant max-w-md mx-auto">
                Scribe your name to establish your longitudinal scholar profile.
              </p>
            </div>

            <div className="sketch-border p-8 bg-surface-container-low/90 text-left">
              <form onSubmit={handleNameSubmit} className="space-y-6">
                <div>
                  <label className="font-label-md text-xs uppercase tracking-wider text-outline block mb-2">
                    Your Name
                  </label>
                  <input
                    type="text"
                    value={name}
                    onChange={(e) => {
                      setName(e.target.value);
                      if (!nameTouched) setNameTouched(true);
                    }}
                    placeholder="Enter your name (e.g. Arya Sharma)..."
                    className="w-full hand-drawn-input text-xl py-2 px-3"
                    autoFocus
                  />
                  {nameTouched && name.trim().length < 2 && (
                    <p className="text-xs text-error mt-2 font-body-md">
                      Please enter at least 2 characters.
                    </p>
                  )}
                </div>

                <button
                  type="submit"
                  disabled={name.trim().length < 2}
                  className={`w-full py-3.5 text-2xl flex items-center justify-center gap-3 cursor-pointer shadow-md ${
                    name.trim().length >= 2
                      ? "ink-wash-btn-primary hover:-translate-y-0.5 transition-transform"
                      : "opacity-40 cursor-not-allowed bg-surface-dim border-2 border-outline text-outline"
                  }`}
                >
                  <span>Inscribe Scholar Identity</span>
                  <span className="material-symbols-outlined text-lg">east</span>
                </button>
              </form>
            </div>
          </motion.div>
        )}

        {/* ================================================================= */}
        {/* STEP 1: ASPIRATION SCRIBING & LEARNER STAGE (Req 8, 9)             */}
        {/* ================================================================= */}
        {!loading && currentStep === 1 && (
          <motion.div
            key="step-1"
            initial={{ opacity: 0, x: 20 }}
            animate={{ opacity: 1, x: 0 }}
            exit={{ opacity: 0, x: -20 }}
            className="w-full max-w-3xl space-y-8"
          >
            <div className="text-center space-y-2">
              <span className="font-note-handwritten text-xl text-tertiary sketchy-chip px-3 py-1 inline-block">
                Chapter II: Stage &amp; Aspiration
              </span>
              <h2 className="font-headline-lg text-3xl sm:text-4xl text-on-surface">
                Anchor your discipline &amp; life stage
              </h2>
              <p className="font-body-md text-on-surface-variant max-w-md mx-auto">
                Select where you currently stand, and describe your intended mastery.
              </p>
            </div>

            {/* Persona Cards */}
            <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-3">
              {PERSONAS.map((p) => (
                <button
                  key={p.id}
                  type="button"
                  onClick={() => setStage(p.id)}
                  className={`p-4 text-left transition-all cursor-pointer flex items-start gap-3 sketch-border ${
                    stage === p.id
                      ? "bg-primary-fixed/40 border-primary shadow-md scale-[1.02]"
                      : "bg-surface-container-low/70 hover:bg-surface-container-high/60 border-outline/30"
                  }`}
                >
                  <div
                    className={`w-10 h-10 rounded-full flex items-center justify-center shrink-0 border ${
                      stage === p.id
                        ? "bg-primary text-white border-primary-container"
                        : "bg-surface-container text-secondary border-outline/30"
                    }`}
                  >
                    <span className="material-symbols-outlined text-xl">{p.icon}</span>
                  </div>
                  <div>
                    <h3 className="font-headline-sm text-base text-on-surface">{p.title}</h3>
                    <p className="font-body-md text-xs text-on-surface-variant leading-snug mt-0.5">
                      {p.desc}
                    </p>
                  </div>
                </button>
              ))}
            </div>

            {/* Aspiration Textarea */}
            <div className="sketch-border p-6 sm:p-8 bg-surface-container-low/90 space-y-4">
              <div>
                <label className="font-label-md text-xs uppercase tracking-wider text-outline block mb-1">
                  Target Discipline or Career Direction
                </label>
                <textarea
                  value={aspiration}
                  onChange={(e) => {
                    setAspiration(e.target.value);
                    if (!aspirationTouched) setAspirationTouched(true);
                  }}
                  placeholder="e.g. Master neural perception systems and LLM agent architecture, transitioning from backend engineering..."
                  className="w-full h-32 hand-drawn-input text-lg p-3 resize-none focus:outline-none"
                />
                <div className="flex justify-between items-center text-xs mt-2 text-on-surface-variant font-label-md">
                  <span>{aspiration.length} characters inscribed</span>
                  {aspirationTouched && !aspirationValidation.isValid && (
                    <span className="text-error font-body-md font-medium">
                      {aspirationValidation.message}
                    </span>
                  )}
                  {aspirationValidation.isValid && (
                    <span className="text-primary font-note-handwritten text-base flex items-center gap-1 font-semibold">
                      <span className="material-symbols-outlined text-sm">check_circle</span>
                      <span>Aspiration Grounded</span>
                    </span>
                  )}
                </div>
              </div>

              <div>
                <label className="font-label-md text-xs uppercase tracking-wider text-outline block mb-1">
                  Constraints or Weekly Bandwidth
                </label>
                <input
                  type="text"
                  value={constraints}
                  onChange={(e) => setConstraints(e.target.value)}
                  placeholder="e.g., 10-15 hours/week, working alongside full-time studies"
                  className="w-full hand-drawn-input text-base px-3 py-1.5"
                />
              </div>

              <div className="flex justify-between items-center pt-4 border-t border-outline/20">
                <button
                  type="button"
                  onClick={() => setCurrentStep(0)}
                  className="ink-wash-btn px-6 py-2 text-lg cursor-pointer"
                >
                  Back
                </button>
                <button
                  type="button"
                  disabled={!aspirationValidation.isValid}
                  onClick={handleAspirationSubmit}
                  className={`px-8 py-2.5 text-xl flex items-center gap-2 cursor-pointer ${
                    aspirationValidation.isValid
                      ? "ink-wash-btn-primary hover:-translate-y-0.5 transition-transform"
                      : "opacity-40 cursor-not-allowed bg-surface-dim border-2 border-outline text-outline"
                  }`}
                >
                  <span>Calibrate Requirements</span>
                  <span className="material-symbols-outlined text-sm">east</span>
                </button>
              </div>
            </div>
          </motion.div>
        )}

        {/* ================================================================= */}
        {/* STEP 2: IDENTITY VERIFICATION (genuine-user gate)                  */}
        {/* ================================================================= */}
        {!loading && currentStep === 2 && domainStatus === "uncharted" && (
          <div className="sketch-border p-4 bg-amber-500/10 border-amber-500/30 flex items-start gap-3 w-full max-w-3xl mb-4">
            <span className="material-symbols-outlined text-xl text-amber-600 mt-0.5">
              explore
            </span>
            <div className="space-y-1">
              <p className="font-label-lg text-on-surface">Uncharted territory</p>
              <p className="font-body-sm text-on-surface-variant">
                We don&apos;t have a verified knowledge base for &ldquo;{aspiration}&rdquo; yet.
                Your path will be built as a research draft — clearly labeled, never
                presented as verified — and it gets upgraded automatically when this
                field is verified.
              </p>
            </div>
          </div>
        )}
        {!loading && currentStep === 2 && (
          <VerificationStep
            userType={stage}
            onNext={handleVerificationNext}
            onBack={() => setCurrentStep(1)}
          />
        )}

        {/* ================================================================= */}
        {/* STEP 3: ASPIRATION APTITUDE TEST (domain-aware diagnostic)        */}
        {/* ================================================================= */}
        {!loading && currentStep === 3 && (
          <AspirationTestStep
            aspiration={aspiration}
            stage={stage}
            userType={stage}
            onNext={handleTestNext}
            onBack={() => setCurrentStep(2)}
          />
        )}

        {/* ================================================================= */}
        {/* STEP 4: EVIDENCE REQUIREMENTS & SUBMISSION (Req 8, 9, 10)         */}
        {/* ================================================================= */}
        {!loading && currentStep === 4 && (
          <motion.div
            key="step-2"
            initial={{ opacity: 0, x: 20 }}
            animate={{ opacity: 1, x: 0 }}
            exit={{ opacity: 0, x: -20 }}
            className="w-full max-w-3xl space-y-6"
          >
            {/* GROUNDED ASSESSMENT: potential/gaps/path based on verification + test */}
            {assessmentLoading && (
              <div className="sketch-border p-5 bg-surface-container-low/70 flex items-center gap-3">
                <span className="material-symbols-outlined animate-spin text-secondary">progress_activity</span>
                <p className="text-sm text-on-surface-variant">Analyzing your marks, verification and test results...</p>
              </div>
            )}
            {!assessmentLoading && groundedAssessment && groundedAssessment.potential && (
              <div className="sketch-border p-5 bg-surface-container-low/70 space-y-4">
                <div className="flex items-center gap-2 text-secondary font-headline-sm text-sm">
                  <span className="material-symbols-outlined text-base">psychology</span>
                  <span>Your potential, based on what you've proven:</span>
                </div>

                <p className="font-body-md text-sm text-on-surface leading-relaxed">
                  {groundedAssessment.potential}
                </p>

                {groundedAssessment.strengths && groundedAssessment.strengths.length > 0 && (
                  <div className="space-y-1.5">
                    <p className="font-headline-sm text-xs text-secondary uppercase tracking-wide">What your evidence shows you're good at</p>
                    <ul className="space-y-1">
                      {groundedAssessment.strengths.map((s, idx: number) => (
                        <li key={idx} className="flex gap-2 text-xs text-on-surface-variant">
                          <span className="material-symbols-outlined text-sm text-secondary shrink-0">check_circle</span>
                          <ClaimBadge claim={s} />
                        </li>
                      ))}
                    </ul>
                  </div>
                )}

                {groundedAssessment.gaps && groundedAssessment.gaps.length > 0 && (
                  <div className="space-y-1.5">
                    <p className="font-headline-sm text-xs text-tertiary uppercase tracking-wide">Where you're lacking</p>
                    <ul className="space-y-1">
                      {groundedAssessment.gaps.map((gap, idx: number) => (
                        <li key={idx} className="flex gap-2 text-xs text-on-surface-variant">
                          <span className="material-symbols-outlined text-sm text-tertiary shrink-0">priority_high</span>
                          <ClaimBadge claim={gap} />
                        </li>
                      ))}
                    </ul>
                  </div>
                )}

                {groundedAssessment.path_outline && groundedAssessment.path_outline.length > 0 && (
                  <div className="space-y-1.5">
                    <p className="font-headline-sm text-xs text-secondary uppercase tracking-wide">Your dedicated path</p>
                    <ol className="space-y-1">
                      {groundedAssessment.path_outline.map((step, idx: number) => (
                        <li key={idx} className="flex gap-2 text-xs text-on-surface-variant">
                          <span className="font-bold text-secondary shrink-0">{idx + 1}.</span>
                          <ClaimBadge claim={step} />
                        </li>
                      ))}
                    </ol>
                  </div>
                )}

                {groundedAssessment.uncertainty && groundedAssessment.uncertainty.length > 0 && (
                  <p className="text-[11px] text-on-surface-variant/70 italic">
                    Note: {groundedAssessment.uncertainty.join(" ")}
                  </p>
                )}
              </div>
            )}
            <div className="text-center space-y-2">
              <span className="font-note-handwritten text-xl text-tertiary sketchy-chip px-3 py-1 inline-block">
                Chapter IV: Grounded Evidence
              </span>
              <h2 className="font-headline-lg text-3xl sm:text-4xl text-on-surface">
                Provide proof of prior work or exploration
              </h2>
              <p className="font-body-md text-on-surface-variant max-w-lg mx-auto">
                PATHMIND evaluates real artifacts to bypass redundant topics and calibrate your baseline.
              </p>
            </div>

            {/* Immediate Aspiration Intelligence: potential, gaps, path, questions */}
            {/* Dynamic Grounded Guidance from Backend */}
            {evidenceRequirements && (
              <div className="sketch-border p-5 bg-surface-container-low/70 space-y-3">
                <div className="flex items-center gap-2 text-secondary font-headline-sm text-sm">
                  <span className="material-symbols-outlined text-base">verified</span>
                  <span>Expectations for {evidenceRequirements.domain_title}:</span>
                </div>
                <p className="font-body-md text-xs text-on-surface-variant italic">
                  {evidenceRequirements.stage_expectation}
                </p>
                <div className="grid sm:grid-cols-3 gap-2 pt-2">
                  {evidenceRequirements.recommended_evidence?.map((rec: RecommendedEvidenceItem, idx: number) => (
                    <div key={idx} className="p-2.5 rounded bg-surface-container/60 border border-outline/20 text-xs">
                      <span className="font-bold text-on-surface block mb-0.5">{rec.title}</span>
                      <p className="text-on-surface-variant/80 text-[11px] leading-tight">{rec.description}</p>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Intake Tabs */}
            <div className="sketch-border p-6 bg-surface-container-low/90 space-y-4">
              <div className="flex border-b border-outline/30 pb-2 gap-4">
                <button
                  type="button"
                  onClick={() => setActiveEvTab("projects")}
                  className={`font-label-md text-sm cursor-pointer pb-1 border-b-2 transition-all ${
                    activeEvTab === "projects" ? "border-primary text-primary font-bold" : "border-transparent text-outline"
                  }`}
                >
                  Project Writeup
                </button>
                <button
                  type="button"
                  onClick={() => setActiveEvTab("links")}
                  className={`font-label-md text-sm cursor-pointer pb-1 border-b-2 transition-all ${
                    activeEvTab === "links" ? "border-primary text-primary font-bold" : "border-transparent text-outline"
                  }`}
                >
                  Repository / Link
                </button>
                <button
                  type="button"
                  onClick={() => setActiveEvTab("files")}
                  className={`font-label-md text-sm cursor-pointer pb-1 border-b-2 transition-all ${
                    activeEvTab === "files" ? "border-primary text-primary font-bold" : "border-transparent text-outline"
                  }`}
                >
                  Document Upload
                </button>
              </div>

              {activeEvTab === "projects" && (
                <form onSubmit={handleAddProjectEvidence} className="space-y-3">
                  <input
                    type="text"
                    value={projectTitle}
                    onChange={(e) => setProjectTitle(e.target.value)}
                    placeholder="Project or Case Study Title (e.g. Distributed Data Processing Pipeline)..."
                    className="w-full hand-drawn-input text-base px-3 py-1.5"
                  />
                  <textarea
                    value={projectDesc}
                    onChange={(e) => setProjectDesc(e.target.value)}
                    placeholder="Describe your architecture, libraries used, core challenge solved, and verified results..."
                    className="w-full h-24 hand-drawn-input text-sm p-3 resize-none"
                  />
                  <button
                    type="submit"
                    disabled={!projectTitle.trim() || !projectDesc.trim()}
                    className="ink-wash-btn px-4 py-1.5 text-base cursor-pointer disabled:opacity-40"
                  >
                    + Add Project Writeup
                  </button>
                </form>
              )}

              {activeEvTab === "links" && (
                <form onSubmit={handleAddLinkEvidence} className="space-y-3">
                  <input
                    type="text"
                    value={linkLabel}
                    onChange={(e) => setLinkLabel(e.target.value)}
                    placeholder="Label (e.g. GitHub Repository or Published Paper)..."
                    className="w-full hand-drawn-input text-base px-3 py-1.5"
                  />
                  <input
                    type="url"
                    value={linkUrl}
                    onChange={(e) => setLinkUrl(e.target.value)}
                    placeholder="https://github.com/my-profile/project..."
                    className="w-full hand-drawn-input text-base px-3 py-1.5"
                  />
                  <button
                    type="submit"
                    disabled={!linkUrl.trim()}
                    className="ink-wash-btn px-4 py-1.5 text-base cursor-pointer disabled:opacity-40"
                  >
                    + Attach Verified Link
                  </button>
                </form>
              )}

              {activeEvTab === "files" && (
                <div className="space-y-3 py-2">
                  <input
                    type="file"
                    ref={fileInputRef}
                    onChange={handleFileUpload}
                    multiple
                    className="hidden"
                  />
                  <button
                    type="button"
                    onClick={() => fileInputRef.current?.click()}
                    className="w-full py-6 border-2 border-dashed border-outline/50 rounded-lg text-center hover:bg-surface-container/60 transition-colors cursor-pointer"
                  >
                    <span className="material-symbols-outlined text-3xl text-primary mb-1">upload_file</span>
                    <p className="font-headline-sm text-sm text-on-surface">Click to select PDF, documentation, or code file</p>
                    <p className="font-body-md text-xs text-on-surface-variant">Supports PDF, Markdown, Python, JSON, text</p>
                  </button>
                </div>
              )}

              {/* Attached Evidence List */}
              {evidenceList.length > 0 && (
                <div className="pt-3 border-t border-outline/20 space-y-2">
                  <span className="font-label-md text-xs uppercase text-outline block">
                    Attached Evidence ({evidenceList.length})
                  </span>
                  <div className="space-y-1.5 max-h-40 overflow-y-auto">
                    {evidenceList.map((item, idx) => (
                      <div
                        key={idx}
                        className="flex items-center justify-between p-2 rounded bg-surface-container/70 border border-outline/20 text-xs"
                      >
                        <div className="flex items-center gap-2 min-w-0">
                          <span className="material-symbols-outlined text-primary text-base">
                            {item.type === "file" ? "description" : item.type === "link" ? "link" : "code"}
                          </span>
                          <span className="font-semibold text-on-surface truncate">{item.name}</span>
                        </div>
                        <button
                          type="button"
                          onClick={() => setEvidenceList((prev) => prev.filter((_, i) => i !== idx))}
                          className="text-error hover:opacity-70 text-xs font-bold px-2 cursor-pointer"
                        >
                          Remove
                        </button>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              <div className="flex justify-between items-center pt-4 border-t border-outline/20">
                <button
                  type="button"
                  onClick={() => setCurrentStep(3)}
                  className="ink-wash-btn px-6 py-2 text-lg cursor-pointer"
                >
                  Back
                </button>
                <button
                  type="button"
                  onClick={handleEvidenceSubmit}
                  className="ink-wash-btn-primary px-8 py-2.5 text-xl flex items-center gap-2 cursor-pointer shadow-md hover:-translate-y-0.5 transition-transform"
                >
                  <span>{evidenceList.length > 0 ? "Synthesize Blueprint" : "Proceed Without Proof"}</span>
                  <span className="material-symbols-outlined text-sm">east</span>
                </button>
              </div>
            </div>
          </motion.div>
        )}

        {/* ================================================================= */}
        {/* STEP 4: DYNAMIC DIAGNOSTIC ASSESSMENT (Req 8, 9)                   */}
        {/* ================================================================= */}
        {!loading && currentStep === 5 && blueprint && (
          <motion.div
            key="step-3"
            initial={{ opacity: 0, x: 20 }}
            animate={{ opacity: 1, x: 0 }}
            exit={{ opacity: 0, x: -20 }}
            className="w-full max-w-3xl space-y-6"
          >
            <div className="text-center space-y-2">
              <span className="font-note-handwritten text-xl text-tertiary sketchy-chip px-3 py-1 inline-block">
                Chapter V: Diagnostic Calibration
              </span>
              <h2 className="font-headline-lg text-3xl sm:text-4xl text-on-surface">
                {blueprint.domain} Diagnostic
              </h2>
              <p className="font-body-md text-xs text-secondary italic">
                {blueprint.stage_calibration}
              </p>
            </div>

            <form onSubmit={handleAssessmentSubmit} className="space-y-6">
              {blueprint.items.map((item, idx) => (
                <div key={item.item_id} className="sketch-border p-6 bg-surface-container-low/90 space-y-3">
                  <div className="flex items-center justify-between">
                    <span className="font-label-md text-xs uppercase tracking-wider text-secondary">
                      Question {idx + 1}: {item.construct}
                    </span>
                  </div>

                  <p className="font-headline-sm text-lg text-on-surface leading-snug">
                    {item.prompt}
                  </p>

                  <p className="font-body-md text-xs text-on-surface-variant/90 italic">
                    <strong>Context: </strong> {item.context}
                  </p>

                  {/* Likert Scale Item */}
                  {item.type === "likert_calibration" && item.scale ? (
                    <div className="grid grid-cols-1 sm:grid-cols-5 gap-2 pt-2">
                      {item.scale.map((s) => (
                        <button
                          key={s.value}
                          type="button"
                          onClick={() => handleAssessmentAnswerChange(item.item_id, s.value)}
                          className={`p-2.5 text-xs text-left sm:text-center rounded border transition-all cursor-pointer ${
                            assessmentResponses[item.item_id] === s.value
                              ? "bg-primary text-white border-primary font-bold shadow"
                              : "bg-surface-container border-outline/30 text-on-surface hover:bg-surface-container-high"
                          }`}
                        >
                          <span className="block font-bold text-sm mb-1 sm:mb-0">{s.value}</span>
                          <span className="text-[11px] leading-tight block">{s.label.split("—")[1] || s.label}</span>
                        </button>
                      ))}
                    </div>
                  ) : (
                    /* Open Analytical or Scenario Item */
                    <textarea
                      value={assessmentResponses[item.item_id] || ""}
                      onChange={(e) => handleAssessmentAnswerChange(item.item_id, e.target.value)}
                      placeholder="Write your structured response here..."
                      className="w-full h-28 hand-drawn-input text-base p-3 resize-none focus:outline-none"
                    />
                  )}
                </div>
              ))}

              <div className="flex justify-between items-center pt-2">
                <button
                  type="button"
                  onClick={() => setCurrentStep(4)}
                  className="ink-wash-btn px-6 py-2 text-lg cursor-pointer"
                >
                  Back
                </button>
                <button
                  type="submit"
                  className="ink-wash-btn-primary px-10 py-3 text-2xl flex items-center gap-3 cursor-pointer shadow-md hover:-translate-y-0.5 transition-transform"
                >
                  <span>Evaluate Responses</span>
                  <span className="material-symbols-outlined text-lg">east</span>
                </button>
              </div>
            </form>
          </motion.div>
        )}

        {/* ================================================================= */}
        {/* STEP 5: BASELINE & CANDIDATE PATHWAYS (Req 8, 12, 13)             */}
        {/* ================================================================= */}
        {!loading && currentStep === 6 && (
          <motion.div
            key="step-4"
            initial={{ opacity: 0, x: 20 }}
            animate={{ opacity: 1, x: 0 }}
            exit={{ opacity: 0, x: -20 }}
            className="w-full max-w-4xl space-y-8"
          >
            <div className="text-center space-y-2">
              <span className="font-note-handwritten text-xl text-tertiary sketchy-chip px-3 py-1 inline-block">
                Chapter VI: Verified Baseline &amp; Trajectories
              </span>
              <h2 className="font-headline-lg text-3xl sm:text-4xl text-on-surface">
                Candidate Pathways Discovered
              </h2>
              <p className="font-body-md text-on-surface-variant max-w-md mx-auto">
                Grounded options aligned with your demonstrated competence and stated constraints.
              </p>
            </div>

            {/* Baseline Profile Summary */}
            {evaluationResult && (
              <div className="sketch-border p-6 bg-surface-container-low/90 space-y-4">
                <div className="flex flex-wrap items-center justify-between gap-2 border-b border-outline/20 pb-3">
                  <div className="flex items-center gap-2">
                    <span className="material-symbols-outlined text-primary text-2xl">verified_user</span>
                    <span className="font-headline-sm text-lg text-on-surface">Evaluated Baseline</span>
                  </div>
                  <div className="inline-flex items-center gap-2 px-3 py-1 rounded bg-secondary/15 text-secondary border border-secondary/30 text-xs font-bold">
                    <span>Depth: {evaluationResult.depth_rating}</span>
                    <span>•</span>
                    <span>Score: {(evaluationResult.competence_score * 100).toFixed(0)}%</span>
                  </div>
                </div>

                <p className="font-body-md text-sm text-on-surface-variant leading-relaxed">
                  {evaluationResult.evaluation_narrative}
                </p>

                <div className="grid sm:grid-cols-2 gap-3 text-xs pt-1">
                  <div className="p-3 rounded bg-emerald-500/10 border border-emerald-500/20 text-on-surface">
                    <strong className="text-emerald-700 dark:text-emerald-300 block mb-1">
                      Verified Strengths:
                    </strong>
                    <ul className="list-disc pl-4 space-y-0.5">
                      {evaluationResult.demonstrated_strengths?.map((s: string, i: number) => (
                        <li key={i}>{s}</li>
                      ))}
                    </ul>
                  </div>

                  <div className="p-3 rounded bg-amber-500/10 border border-amber-500/20 text-on-surface">
                    <strong className="text-amber-700 dark:text-amber-300 block mb-1">
                      Key Growth Areas (Roadmap Focus):
                    </strong>
                    <ul className="list-disc pl-4 space-y-0.5">
                      {evaluationResult.growth_areas?.map((g: string, i: number) => (
                        <li key={i}>{g}</li>
                      ))}
                    </ul>
                  </div>
                </div>
              </div>
            )}

            {/* Candidate Pathways Cards */}
            <div className="space-y-4">
              <h3 className="font-headline-sm text-xl text-on-surface">
                Choose Your Pathway (2–3 Grounded Options)
              </h3>

              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                {candidatePaths.map((path, idx) => {
                  const isSelected = selectedPathId === path.path_id;
                  return (
                  <div
                    key={path.path_id || idx}
                    className={`sketch-border p-5 bg-surface-container-low flex flex-col justify-between space-y-4 hover:translate-y-[-2px] transition-all ${
                      isSelected ? "ring-2 ring-primary border-primary" : ""
                    }`}
                  >
                    <div className="space-y-2">
                      <div className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded text-[11px] font-bold uppercase bg-primary-fixed/40 text-primary">
                        Option {idx + 1}
                      </div>
                      <h4 className="font-headline-sm text-lg text-on-surface leading-snug">
                        {path.title}
                      </h4>
                      <p className="font-body-md text-xs text-on-surface-variant line-clamp-3">
                        {path.description}
                      </p>
                    </div>

                    <div className="space-y-2 text-xs border-t border-outline/20 pt-3">
                      <div className="flex justify-between text-on-surface-variant">
                        <span>Horizon:</span>
                        <strong className="text-on-surface">{path.time_horizon_months || 12} mos</strong>
                      </div>
                      <div className="flex justify-between text-on-surface-variant">
                        <span>Risk Level:</span>
                        <strong className="text-on-surface">{path.risk_level || "Balanced"}</strong>
                      </div>
                      {path.estimated_outcomes?.compensation_range && (
                        <div className="flex justify-between text-on-surface-variant">
                          <span>Outcome:</span>
                          <strong className="text-on-surface truncate max-w-[120px]">
                            {path.estimated_outcomes.compensation_range}
                          </strong>
                        </div>
                      )}
                    </div>

                    <button
                      type="button"
                      onClick={() => handleSelectPathway(path.path_id)}
                      className="w-full ink-wash-btn-primary py-2 text-lg cursor-pointer flex items-center justify-center gap-2 shadow"
                    >
                      <span>Select Trajectory</span>
                      <span className="material-symbols-outlined text-sm">east</span>
                    </button>
                  </div>
                  );
                })}
              </div>
            </div>
          </motion.div>
        )}

        {/* ================================================================= */}
        {/* STEP 6: HIDDEN ROADMAP & EVIDENCE-GATED ACTIVE PHASE (Req 8, 10)  */}
        {/* ================================================================= */}
        {!loading && currentStep === 7 && roadmap && (
          <motion.div
            key="step-5"
            initial={{ opacity: 0, x: 20 }}
            animate={{ opacity: 1, x: 0 }}
            exit={{ opacity: 0, x: -20 }}
            className="w-full max-w-4xl space-y-8"
          >
            <div className="text-center space-y-2">
              <span className="font-note-handwritten text-xl text-tertiary sketchy-chip px-3 py-1 inline-block">
                Chapter VII: Progressive Disclosure Roadmap
              </span>
              <h2 className="font-headline-lg text-3xl sm:text-4xl text-on-surface">
                {roadmap.target_outcome}
              </h2>
              <p className="font-body-md text-on-surface-variant max-w-lg mx-auto">
                Future phases remain locked. Only verifiable evidence unlocks progression through backend gates.
              </p>
            </div>

            {/* Stage Cards (Disclosed vs Locked) */}
            <div className="space-y-4">
              {roadmap.stages.map((stageItem) => {
                const isActive = !stageItem.locked;

                return (
                  <div
                    key={stageItem.stage_id}
                    className={`sketch-border p-6 transition-all ${
                      isActive
                        ? "bg-surface-container-low shadow-md border-primary/40"
                        : "bg-surface-dim/40 opacity-75 border-outline/30"
                    }`}
                  >
                    <div className="flex flex-wrap items-center justify-between gap-3 mb-3">
                      <div className="flex items-center gap-3">
                        <div
                          className={`w-9 h-9 rounded-full flex items-center justify-center font-bold text-sm border ${
                            isActive
                              ? "bg-primary text-white border-primary-container"
                              : "bg-surface-container text-outline border-outline/30"
                          }`}
                        >
                          {stageItem.stage_number}
                        </div>
                        <div>
                          <h3 className="font-headline-sm text-xl text-on-surface">
                            {stageItem.title}
                          </h3>
                          {isActive && (
                            <span className="font-note-handwritten text-xs text-secondary block mt-0.5">
                              {stageItem.why_now}
                            </span>
                          )}
                        </div>
                      </div>

                      <div
                        className={`inline-flex items-center gap-1.5 px-3 py-1 rounded text-xs font-bold uppercase ${
                          isActive
                            ? "bg-emerald-500/15 text-emerald-700 dark:text-emerald-300 border border-emerald-500/30"
                            : "bg-outline/10 text-outline border border-outline/20"
                        }`}
                      >
                        <span className="material-symbols-outlined text-sm">
                          {isActive ? "lock_open" : "lock"}
                        </span>
                        <span>{isActive ? "Active / Disclosed" : "Locked / Evidence-Gated"}</span>
                      </div>
                    </div>

                    {/* Active Stage Full Missions */}
                    {isActive ? (
                      <div className="mt-4 space-y-3 pt-3 border-t border-outline/20">
                        <span className="font-label-md text-xs uppercase tracking-wider text-outline block">
                          Phase Milestones &amp; Missions:
                        </span>

                        <div className="grid sm:grid-cols-2 gap-3">
                          {stageItem.missions?.map((m) => {
                            const isMissionSelected = phaseSubmissionMissionId === m.mission_id;
                            return (
                            <div
                              key={m.mission_id}
                              onClick={() => setPhaseSubmissionMissionId(m.mission_id)}
                              className={`p-3.5 rounded border space-y-1.5 cursor-pointer transition-all ${
                                isMissionSelected
                                  ? "bg-primary/10 border-primary shadow-sm ring-1 ring-primary"
                                  : "bg-surface-container/60 border-outline/20 hover:border-outline/40"
                              }`}
                            >
                              <div className="flex items-center justify-between">
                                <span className="font-headline-sm text-sm text-on-surface font-semibold">
                                  {m.title}
                                </span>
                                <span className="text-[10px] uppercase font-bold px-1.5 py-0.5 rounded bg-primary/10 text-primary">
                                  {m.evidence_type}
                                </span>
                              </div>
                              <p className="font-body-md text-xs text-on-surface-variant">
                                {m.objective}
                              </p>
                            </div>
                            );
                          })}
                        </div>
                      </div>
                    ) : (
                      /* Locked Stage Preview with Protected Content Striped (Req 10) */
                      <div className="pt-2">
                        <p className="font-body-md text-xs text-outline italic flex items-center gap-1.5">
                          <span className="material-symbols-outlined text-sm">info</span>
                          <span>
                            Prerequisites: {stageItem.prerequisites?.join(", ") || "Completion of prerequisite stage"}.
                            Protected curriculum will disclose upon verified evidence submission.
                          </span>
                        </p>
                      </div>
                    )}
                  </div>
                );
              })}
            </div>

            {/* Evidence Submission Gate for Active Phase (Req 10) */}
            {roadmap.active_stage && (
              <div className="sketch-border p-6 sm:p-8 bg-surface-container-low/95 space-y-4">
                <div className="flex items-center gap-2 text-primary font-headline-sm text-lg">
                  <span className="material-symbols-outlined text-xl">fact_check</span>
                  <span>Phase Milestone Evidence Gate</span>
                </div>

                <p className="font-body-md text-xs text-on-surface-variant">
                  Submit executable code, tests, or structured case study proof.
                  The backend deterministic evaluator decides <strong>PASS</strong>, <strong>REINFORCE</strong>, or <strong>INSUFFICIENT_EVIDENCE</strong>.
                </p>

                <form onSubmit={handlePhaseEvidenceSubmit} className="space-y-4">
                  <textarea
                    value={phaseSubmissionCode}
                    onChange={(e) => setPhaseSubmissionCode(e.target.value)}
                    placeholder="Paste working Python code, test assertions, or repository URL to verify milestone..."
                    className="w-full h-32 hand-drawn-input font-mono text-xs p-3 focus:outline-none"
                    required
                  />

                  {phaseEvalResult && (
                    <div
                      className={`p-4 rounded border text-xs font-body-md ${
                        phaseEvalResult.status === "PASS"
                          ? "bg-emerald-500/10 border-emerald-500/30 text-emerald-800 dark:text-emerald-200"
                          : "bg-amber-500/10 border-amber-500/30 text-amber-800 dark:text-amber-200"
                      }`}
                    >
                      <div className="flex items-center gap-1.5 font-bold mb-1">
                        <span className="material-symbols-outlined text-base">
                          {phaseEvalResult.status === "PASS" ? "verified" : "help"}
                        </span>
                        <span>Evaluation Status: {phaseEvalResult.status}</span>
                      </div>
                      <p>{phaseEvalResult.feedback || "Evidence processed by deterministic progression loop."}</p>
                    </div>
                  )}

                  <button
                    type="submit"
                    disabled={!phaseSubmissionCode.trim()}
                    className="w-full ink-wash-btn-primary py-3 text-xl cursor-pointer flex items-center justify-center gap-2 shadow disabled:opacity-40"
                  >
                    <span className="material-symbols-outlined text-lg">upload_file</span>
                    <span>Submit Evidence for Phase Unlock</span>
                  </button>
                </form>
              </div>
            )}
          </motion.div>
        )}

      </main>
    </div>
  );
}
