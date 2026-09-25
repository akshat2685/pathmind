"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { motion, AnimatePresence } from "framer-motion";
import apiClient from "@/lib/api/client";
import { useAuth } from "@/lib/contexts/AuthContext";

interface University {
  university_id: string;
  name: string;
  state: string;
  country?: string;
  official_domain: string;
  official_url?: string;
}

interface Subject {
  subject_id: string;
  code: string;
  name: string;
  credits: number;
}

interface DiagnosticQuestion {
  question_id: string;
  question_text: string;
  question_type: string;
  options?: string[];
  topic: string;
  marks?: number;
}

interface DiagnosticResult {
  score: number;
  normalized_score: number;
  mastery_status: string;
  topic_results: Array<{
    topic: string;
    mastery_score?: number;
    outcome?: string;
    status?: string;
  }>;
  feedback: string;
  evaluation_confidence?: number;
}

interface Baseline {
  strengths: Array<{ subject_id?: string; topic?: string; mastery_score?: number; outcome?: string }>;
  weaknesses: Array<{ subject_id?: string; topic?: string; mastery_score?: number; outcome?: string }>;
  gaps: Array<{ subject_id?: string; topic?: string; mastery_score?: number; outcome?: string }>;
  topic_count: number;
}

const BRANCHES = [
  {
    id: "COMPUTER_SCIENCE_ENGINEER",
    label: "Computer Science & Software",
    icon: "terminal",
    desc: "Algorithms, operating systems, software architecture & database engines.",
  },
  {
    id: "AI_ENGINEER",
    label: "Artificial Intelligence & ML",
    icon: "psychology",
    desc: "Mathematical optimization, neural networks, machine learning & data systems.",
  },
  {
    id: "MECHANICAL_ENGINEER",
    label: "Mechanical Engineering",
    icon: "settings",
    desc: "Thermodynamics, fluid mechanics, structural stress & manufacturing systems.",
  },
  {
    id: "ELECTRICAL_ENGINEER",
    label: "Electrical & Electronics",
    icon: "bolt",
    desc: "Electric circuits, power machines, electromagnetic theory & signal processing.",
  },
  {
    id: "CIVIL_ENGINEER",
    label: "Civil Engineering",
    icon: "foundation",
    desc: "Mechanics of materials, structural analysis, surveying & fluid dynamics.",
  },
  {
    id: "GENERAL_OTHER",
    label: "General / Other Discipline",
    icon: "explore",
    desc: "General engineering foundations and transparent multidisciplinary guidance.",
  },
];

const SCOPES = [
  {
    id: "WHOLE_PROGRAM",
    label: "Whole Program",
    icon: "account_tree",
    desc: "All semesters of your engineering program, phased unit by unit.",
  },
  {
    id: "SEMESTER",
    label: "This Semester",
    icon: "calendar_month",
    desc: "Focus on your current semester's verified subjects.",
  },
  {
    id: "SUBJECT_PART",
    label: "Subject Part",
    icon: "manage_search",
    desc: "Zoom into one subject and the specific part you need to master.",
  },
];

function fmtScore(v?: number) {
  if (v === undefined || v === null) return "—";
  return `${Math.round(v)}%`;
}

export function CollegeOnboardingFlow() {
  const router = useRouter();
  const { user } = useAuth();

  const [step, setStep] = useState(1);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // STEP 1 — Aspirations
  const [scholarName, setScholarName] = useState("");
  const [aspiration, setAspiration] = useState("");

  // STEP 2 — University
  const [universities, setUniversities] = useState<University[]>([]);
  const [searchQuery, setSearchQuery] = useState("");
  const [selectedUniversity, setSelectedUniversity] = useState<University | null>(null);
  const [semester, setSemester] = useState<number>(3);

  // STEP 3 — Diagnostic
  const [diagState, setDiagState] = useState<"intro" | "taking" | "result" | "unavailable" | "skipped">("intro");
  const [diagLoading, setDiagLoading] = useState(false);
  const [diagAssessment, setDiagAssessment] = useState<any>(null);
  const [diagAnswers, setDiagAnswers] = useState<Record<string, string>>({});
  const [diagResult, setDiagResult] = useState<DiagnosticResult | null>(null);
  const [baseline, setBaseline] = useState<Baseline | null>(null);

  // STEP 4 — Branch
  const [branch, setBranch] = useState<string | null>(null);
  const [curriculumLoading, setCurriculumLoading] = useState(false);
  const [curriculumSubjects, setCurriculumSubjects] = useState<Subject[]>([]);
  const [curriculumError, setCurriculumError] = useState<string | null>(null);

  // STEP 5 — Scope & timeline
  const [scope, setScope] = useState<string>("SEMESTER");
  const [selectedSubjectIds, setSelectedSubjectIds] = useState<string[]>([]);
  const [partSubjectId, setPartSubjectId] = useState<string>("");
  const [partDescription, setPartDescription] = useState("");
  const [examDate, setExamDate] = useState<string>("");
  const [targetScore, setTargetScore] = useState<string>("8.5");
  const [weeklyHours, setWeeklyHours] = useState<number>(14);
  const [learningStyle, setLearningStyle] = useState<string>("visual_examples");

  useEffect(() => {
    if (user && !scholarName) {
      setScholarName(user.email?.split("@")[0] || "Scholar");
    }
  }, [user]);

  // University search (explicit selection required — never auto-select)
  useEffect(() => {
    const t = setTimeout(() => fetchUniversities(searchQuery), 250);
    return () => clearTimeout(t);
  }, [searchQuery]);

  const fetchUniversities = async (q: string) => {
    try {
      const res = await apiClient.get<University[]>(
        `/api/college/universities?query=${encodeURIComponent(q)}`
      );
      if (res.ok && res.data) setUniversities(res.data);
    } catch {
      /* non-fatal: list simply stays empty */
    }
  };

  const fetchCurriculum = async (univId: string, branchId: string, sem: number) => {
    setCurriculumLoading(true);
    setCurriculumError(null);
    try {
      const res = await apiClient.get<any>(
        `/api/college/curriculum?university_id=${encodeURIComponent(univId)}&branch=${branchId}&semester=${sem}`
      );
      if (res.ok && res.data) {
        const subs: Subject[] = res.data.subjects || [];
        setCurriculumSubjects(subs);
        setSelectedSubjectIds(subs.map((s) => s.subject_id));
        if (subs.length > 0 && !partSubjectId) setPartSubjectId(subs[0].subject_id);
      } else {
        setCurriculumSubjects([]);
        setCurriculumError(res.error || "CURRICULUM_NOT_FOUND");
      }
    } catch (err) {
      setCurriculumSubjects([]);
      setCurriculumError(err instanceof Error ? err.message : "Failed to load curriculum");
    } finally {
      setCurriculumLoading(false);
    }
  };

  const handleBranchSelect = (branchId: string) => {
    setBranch(branchId);
    if (selectedUniversity) {
      fetchCurriculum(selectedUniversity.university_id, branchId, semester);
    }
  };

  // ---------- STEP 1: create learner profile ----------
  const handleAspirationsNext = async () => {
    setError(null);
    if (!scholarName.trim()) {
      setError("Please tell us your name so we can create your learner profile.");
      return;
    }
    setSubmitting(true);
    try {
      const res = await apiClient.post<any>("/api/college/profile", {
        name: scholarName.trim(),
        email: user?.email || null,
      });
      if (!res.ok) {
        setError(res.error || "Failed to create your learner profile. Please try again.");
        return;
      }
      setStep(2);
    } finally {
      setSubmitting(false);
    }
  };

  // ---------- STEP 3: diagnostic assessment ----------
  const beginDiagnostic = async () => {
    setDiagLoading(true);
    setError(null);
    try {
      const res = await apiClient.post<any>("/api/college/assessments/diagnostic", {});
      if (res.ok && res.data) {
        setDiagAssessment(res.data);
        setDiagAnswers({});
        setDiagState("taking");
      } else {
        if (res.error && res.error.includes("DIAGNOSTIC_UNAVAILABLE")) {
          setDiagState("unavailable");
        } else {
          setError(res.error || "Could not start the diagnostic assessment. Please try again.");
        }
      }
    } finally {
      setDiagLoading(false);
    }
  };

  const submitDiagnostic = async () => {
    if (!diagAssessment) return;
    setDiagLoading(true);
    setError(null);
    try {
      const res = await apiClient.post<DiagnosticResult>("/api/college/assessments/submit", {
        assessment_id: diagAssessment.assessment_id,
        answers: diagAnswers,
      });
      if (res.ok && res.data) {
        setDiagResult(res.data);
        setDiagState("result");
        // Baseline is derived from the per-topic mastery store (single source of truth).
        const base = await apiClient.get<Baseline>("/api/college/baseline");
        if (base.ok && base.data) setBaseline(base.data);
      } else {
        setError(res.error || "Could not evaluate your answers. Please try again.");
      }
    } finally {
      setDiagLoading(false);
    }
  };

  const toggleSubject = (subId: string) => {
    setSelectedSubjectIds((prev) =>
      prev.includes(subId) ? prev.filter((id) => id !== subId) : [...prev, subId]
    );
  };

  // ---------- STEP 5: finish — context + plan ----------
  const handleComplete = async () => {
    setError(null);
    if (!selectedUniversity || !branch) {
      setError("University and branch are required to build your plan.");
      return;
    }
    if (scope === "SUBJECT_PART" && !partSubjectId) {
      setError("Pick the subject you want to focus on for subject-part scope.");
      return;
    }
    setSubmitting(true);
    try {
      const univId = selectedUniversity.university_id;

      // 1. Persist branch on the learner profile
      const profRes = await apiClient.post<any>("/api/college/profile", {
        supported_path: branch,
      });
      if (!profRes.ok) {
        setError(profRes.error || "Failed to save your branch on the learner profile.");
        return;
      }

      // 2. Save academic context
      const subjects =
        scope === "SUBJECT_PART"
          ? [partSubjectId]
          : selectedSubjectIds.length > 0
          ? selectedSubjectIds
          : curriculumSubjects.map((s) => s.subject_id);
      const examWindow: Record<string, any> = {
        target_score: targetScore,
      };
      if (examDate) examWindow.start = examDate;
      if (aspiration.trim()) examWindow.aspiration = aspiration.trim();
      if (scope === "SUBJECT_PART" && partDescription.trim())
        examWindow.subject_part_focus = partDescription.trim();

      const ctxRes = await apiClient.post<any>("/api/college/academic-context", {
        university_id: univId,
        branch: branch,
        semester: semester,
        subjects: subjects,
        exam_window: examWindow,
        available_hours_per_week: weeklyHours,
        learning_style_preferences: [learningStyle],
      });
      if (!ctxRes.ok) {
        setError(ctxRes.error || "Failed to save your academic context.");
        return;
      }

      // 3. Generate the ordered learning plan at the chosen scope
      const planRes = await apiClient.post<any>("/api/college/plans/generate", {
        goal_id: `goal_${scope.toLowerCase()}`,
        target_subject_code_or_id:
          scope === "SUBJECT_PART" ? partSubjectId : selectedSubjectIds[0] || null,
        scope: scope,
      });
      if (!planRes.ok) {
        setError(planRes.error || "Failed to generate your study plan.");
        return;
      }

      // Tell the dashboard a fresh plan is ready: a one-shot banner plus an
      // explicit refresh event (covers the case where it is already mounted).
      try {
        sessionStorage.setItem("pathmind_plan_ready", "1");
      } catch {
        /* storage unavailable: banner skipped, refresh event still fires */
      }
      window.dispatchEvent(new Event("pathmind:refresh"));
      router.push("/");
    } finally {
      setSubmitting(false);
    }
  };

  const stepLabels = ["Aspirations", "University", "Diagnostic", "Branch", "Scope"];

  return (
    <div className="min-h-screen bg-[#f7f4e7] text-[#252321] flex flex-col justify-between relative overflow-x-hidden font-sans">
      {/* Background Grid */}
      <div
        className="fixed inset-0 pointer-events-none opacity-80 -z-20"
        style={{
          backgroundImage:
            "linear-gradient(to right, rgba(90, 80, 70, 0.05) 1px, transparent 1px), linear-gradient(to bottom, rgba(90, 80, 70, 0.05) 1px, transparent 1px)",
          backgroundSize: "28px 28px",
        }}
      />

      {/* Ambient Gradient */}
      <div
        className="fixed top-0 left-0 w-[550px] h-[550px] pointer-events-none -z-10 blur-2xl"
        style={{
          background:
            "radial-gradient(circle at 30% 40%, rgba(139, 168, 142, 0.35) 0%, rgba(139, 168, 142, 0.08) 55%, transparent 75%)",
        }}
      />

      {/* Header */}
      <header className="max-w-5xl w-full mx-auto px-6 py-6 flex items-center justify-between border-b border-[#252321]/20">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-full border-[1.75px] border-[#252321] bg-[#fdfae7] flex items-center justify-center">
            <span className="material-symbols-outlined text-[#4a654e] text-2xl">school</span>
          </div>
          <div>
            <h2 className="font-bold text-xl text-[#252321]">Academic Initiation</h2>
            <p className="text-xs font-note-handwritten text-[#68635e]">
              Step {step} of 5 • {stepLabels[step - 1]} • Grounding your engineering compass
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2">
          {[1, 2, 3, 4, 5].map((i) => (
            <div
              key={i}
              className={`h-2.5 rounded-full transition-all ${
                i === step ? "w-8 bg-[#4a654e]" : i < step ? "w-4 bg-[#8ba88e]" : "w-2.5 bg-[#d9d2be]"
              }`}
            />
          ))}
        </div>
      </header>

      {/* Main Form Container */}
      <main className="flex-grow flex items-center justify-center p-4 sm:p-6 md:p-10 z-10">
        <div
          className="w-full max-w-3xl bg-[#fdfae7] p-6 sm:p-10 relative"
          style={{
            border: "1.75px solid #252321",
            borderRadius: "15px 225px 15px 255px / 255px 15px 225px 15px",
            boxShadow:
              "4px 6px 0px rgba(37, 35, 33, 0.9), 12px 16px 28px rgba(70, 60, 50, 0.08)",
          }}
        >
          {error && (
            <div className="mb-5 p-4 rounded-md border-[1.5px] border-[#a65959] bg-[#ffdad6]/30 text-xs text-[#93000a]">
              <span className="font-bold">Something needs attention: </span>
              {error}
            </div>
          )}

          <AnimatePresence mode="wait">
            {/* STEP 1: ASPIRATIONS (free text) */}
            {step === 1 && (
              <motion.div
                key="step1"
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -10 }}
                className="space-y-6"
              >
                <div className="border-b border-dashed border-[#252321]/20 pb-4">
                  <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-[#8ba88e]/20 border border-[#8ba88e] text-xs font-medium mb-2">
                    <span className="material-symbols-outlined text-sm">forum</span>
                    Your Voice
                  </div>
                  <h3 className="text-2xl sm:text-3xl font-bold text-[#252321]">
                    What do you want, Scholar?
                  </h3>
                  <p className="font-serif italic text-sm text-[#68635e] mt-1">
                    In your own words — what should this term give you? PATHMIND shapes the
                    baseline diagnostic around your answer.
                  </p>
                </div>

                <div className="space-y-4">
                  <div>
                    <label className="block text-xs font-bold uppercase tracking-wider text-[#252321] mb-1.5">
                      Your Full Name
                    </label>
                    <input
                      type="text"
                      value={scholarName}
                      onChange={(e) => setScholarName(e.target.value)}
                      placeholder="e.g. Akshat Jain"
                      className="w-full px-4 py-3 rounded-md text-sm border-[1.5px] border-[#4a453f] bg-white/70 focus:bg-white focus:outline-none focus:shadow-[2px_3px_0px_#252321]"
                    />
                  </div>

                  <div>
                    <label className="block text-xs font-bold uppercase tracking-wider text-[#252321] mb-1.5">
                      Your Aspiration — free text
                    </label>
                    <textarea
                      rows={5}
                      value={aspiration}
                      onChange={(e) => setAspiration(e.target.value)}
                      placeholder="e.g. I want to clear my 3rd semester with a strong CGPA, especially in Data Structures — I keep getting stuck on tree traversals and dynamic programming."
                      className="w-full px-4 py-3 rounded-md text-sm border-[1.5px] border-[#4a453f] bg-white/70 focus:bg-white focus:outline-none focus:shadow-[2px_3px_0px_#252321] leading-relaxed"
                    />
                    <p className="text-xs font-note-handwritten text-[#68635e] mt-1">
                      Be specific if you can — subjects, weak topics, exam goals. This is stored
                      with your academic context.
                    </p>
                  </div>
                </div>

                <div className="flex justify-end pt-4 border-t border-dashed border-[#252321]/20">
                  <button
                    type="button"
                    disabled={submitting}
                    onClick={handleAspirationsNext}
                    className="px-6 py-3 bg-[#252321] hover:bg-[#383430] text-[#fdfae7] font-semibold text-sm rounded-md border-2 border-[#252321] shadow-[2px_3px_0px_rgba(37,35,33,0.9)] flex items-center gap-2 cursor-pointer disabled:opacity-60"
                  >
                    <span>{submitting ? "Creating your profile…" : "Continue to University"}</span>
                    <span>→</span>
                  </button>
                </div>
              </motion.div>
            )}

            {/* STEP 2: UNIVERSITY (+ semester) */}
            {step === 2 && (
              <motion.div
                key="step2"
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -10 }}
                className="space-y-6"
              >
                <div className="border-b border-dashed border-[#252321]/20 pb-4">
                  <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-[#8ba88e]/20 border border-[#8ba88e] text-xs font-medium mb-2">
                    <span className="material-symbols-outlined text-sm">badge</span>
                    Scholar Profile
                  </div>
                  <h3 className="text-2xl sm:text-3xl font-bold text-[#252321]">
                    Where do you study, Traveler?
                  </h3>
                  <p className="font-serif italic text-sm text-[#68635e] mt-1">
                    PATHMIND grounds all study materials in your verified university curriculum.
                  </p>
                </div>

                <div className="space-y-4">
                  <div>
                    <label className="block text-xs font-bold uppercase tracking-wider text-[#252321] mb-1.5">
                      Search Verified University / Curriculum Body
                    </label>
                    <input
                      type="text"
                      value={searchQuery}
                      onChange={(e) => setSearchQuery(e.target.value)}
                      placeholder="Type Anna, VTU, Mumbai, AKTU, or AICTE..."
                      className="w-full px-4 py-3 rounded-md text-sm border-[1.5px] border-[#4a453f] bg-white/70 focus:bg-white focus:outline-none focus:shadow-[2px_3px_0px_#252321]"
                    />
                  </div>

                  <div className="space-y-2 max-h-56 overflow-y-auto pr-1">
                    {universities.length === 0 ? (
                      <div className="p-6 border border-dashed border-[#252321]/30 rounded-md bg-white/30 text-center">
                        <p className="text-xs text-[#68635e]">
                          {searchQuery
                            ? "No universities matched that search. Try a shorter term."
                            : "Type above to search the verified university registry."}
                        </p>
                      </div>
                    ) : (
                      universities.map((u) => (
                        <div
                          key={u.university_id}
                          onClick={() => setSelectedUniversity(u)}
                          className={`p-3.5 rounded-md border-[1.5px] cursor-pointer transition-all flex items-center justify-between ${
                            selectedUniversity?.university_id === u.university_id
                              ? "border-[#4a654e] bg-[#4a654e]/10 shadow-[2px_2px_0px_#4a654e]"
                              : "border-[#252321]/30 hover:border-[#252321] bg-white/40"
                          }`}
                        >
                          <div>
                            <h4 className="font-semibold text-sm text-[#252321]">{u.name}</h4>
                            <p className="text-xs text-[#68635e]">
                              {u.state}, {u.country} • Domain: {u.official_domain}
                            </p>
                          </div>
                          {selectedUniversity?.university_id === u.university_id && (
                            <span className="material-symbols-outlined text-[#4a654e]">
                              check_circle
                            </span>
                          )}
                        </div>
                      ))
                    )}
                  </div>

                  <div>
                    <label className="block text-xs font-bold uppercase tracking-wider text-[#252321] mb-2">
                      Active Semester (B.Tech / B.E.)
                    </label>
                    <div className="flex flex-wrap gap-2">
                      {[1, 2, 3, 4, 5, 6, 7, 8].map((s) => (
                        <button
                          key={s}
                          type="button"
                          onClick={() => setSemester(s)}
                          className={`px-4 py-2 text-sm font-semibold rounded-md border-[1.5px] cursor-pointer transition-all ${
                            semester === s
                              ? "bg-[#4a654e] text-white border-[#4a654e] shadow-[2px_2px_0px_#252321]"
                              : "bg-white/60 border-[#252321]/40 text-[#252321] hover:border-[#252321]"
                          }`}
                        >
                          Sem {s}
                        </button>
                      ))}
                    </div>
                  </div>
                </div>

                <div className="flex justify-between pt-4 border-t border-dashed border-[#252321]/20">
                  <button
                    type="button"
                    onClick={() => setStep(1)}
                    className="px-5 py-2.5 border-[1.5px] border-[#252321] rounded-md text-xs font-semibold cursor-pointer"
                  >
                    ← Back
                  </button>
                  <button
                    type="button"
                    disabled={!selectedUniversity}
                    onClick={() => selectedUniversity && setStep(3)}
                    className="px-6 py-3 bg-[#252321] hover:bg-[#383430] text-[#fdfae7] font-semibold text-sm rounded-md border-2 border-[#252321] shadow-[2px_3px_0px_rgba(37,35,33,0.9)] flex items-center gap-2 cursor-pointer disabled:opacity-40"
                  >
                    <span>Continue to Diagnostic</span>
                    <span>→</span>
                  </button>
                </div>
              </motion.div>
            )}

            {/* STEP 3: DIAGNOSTIC ASSESSMENT */}
            {step === 3 && (
              <motion.div
                key="step3"
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -10 }}
                className="space-y-6"
              >
                <div className="border-b border-dashed border-[#252321]/20 pb-4">
                  <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-[#8ba88e]/20 border border-[#8ba88e] text-xs font-medium mb-2">
                    <span className="material-symbols-outlined text-sm">diagnostic</span>
                    Baseline Diagnostic
                  </div>
                  <h3 className="text-2xl sm:text-3xl font-bold text-[#252321]">
                    Measure where you stand today
                  </h3>
                  <p className="font-serif italic text-sm text-[#68635e] mt-1">
                    A short diagnostic drawn from your aspiration and branch context. Your
                    strengths, weaknesses and gaps become the baseline your plan adapts to —
                    nothing here is invented; it comes from your answers alone.
                  </p>
                </div>

                {diagState === "intro" && (
                  <div className="space-y-4">
                    <div className="p-5 rounded-md border-[1.5px] border-[#252321]/30 bg-white/50 text-sm text-[#423e3b] leading-relaxed space-y-2">
                      <p>
                        <span className="font-bold">What happens:</span> a few mixed questions are
                        generated from your profile. Answer honestly — this sets the baseline,
                        not a grade.
                      </p>
                      <p>
                        <span className="font-bold">What if generation fails:</span> the
                        diagnostic is generated live. If it is unavailable, you can continue
                        without a baseline — we will never fabricate one.
                      </p>
                    </div>
                    <div className="flex justify-end">
                      <button
                        type="button"
                        disabled={diagLoading}
                        onClick={beginDiagnostic}
                        className="px-6 py-3 bg-[#4a654e] hover:bg-[#3b523e] text-white font-semibold text-sm rounded-md border-2 border-[#252321] shadow-[2px_3px_0px_#252321] cursor-pointer disabled:opacity-60"
                      >
                        {diagLoading ? "Preparing questions…" : "Begin Baseline Diagnostic →"}
                      </button>
                    </div>
                  </div>
                )}

                {diagState === "unavailable" && (
                  <div className="space-y-4">
                    <div className="p-6 rounded-md border-[1.5px] border-dashed border-[#a65959] bg-[#ffdad6]/20 text-center">
                      <span className="material-symbols-outlined text-3xl text-[#a65959]">
                        cloud_off
                      </span>
                      <h4 className="font-bold text-sm text-[#93000a] mt-2">
                        Diagnostic unavailable right now
                      </h4>
                      <p className="text-xs text-[#68635e] mt-1 max-w-md mx-auto">
                        The diagnostic generator could not produce questions at this time
                        (DIAGNOSTIC_UNAVAILABLE). No baseline will be fabricated — you can
                        continue onboarding and take a checkpoint later from your study plan.
                      </p>
                    </div>
                    <div className="flex justify-end">
                      <button
                        type="button"
                        onClick={() => {
                          setDiagState("skipped");
                          setStep(4);
                        }}
                        className="px-6 py-3 bg-[#252321] text-[#fdfae7] font-semibold text-sm rounded-md border-2 border-[#252321] cursor-pointer"
                      >
                        Continue without baseline →
                      </button>
                    </div>
                  </div>
                )}

                {diagState === "taking" && diagAssessment && (
                  <div className="space-y-5">
                    <div className="border-b border-dashed border-[#252321]/20 pb-3">
                      <span className="text-xs px-2.5 py-1 rounded bg-[#4a654e]/10 border border-[#4a654e] text-[#4a654e] font-bold">
                        Diagnostic Assessment
                      </span>
                      <h4 className="text-xl font-bold text-[#252321] mt-2">
                        {diagAssessment.title}
                      </h4>
                      <p className="text-xs font-serif italic text-[#68635e]">
                        Answer all items — your baseline is computed from these answers only.
                      </p>
                    </div>

                    <div className="space-y-4">
                      {(diagAssessment.questions || []).map((q: DiagnosticQuestion, idx: number) => (
                        <div
                          key={q.question_id}
                          className="p-5 rounded-md border border-[#252321]/30 bg-white/70 space-y-3"
                        >
                          <div className="flex justify-between items-start gap-3">
                            <h4 className="font-bold text-sm text-[#252321]">
                              Item {idx + 1}. {q.question_text}
                            </h4>
                            <span className="text-xs font-note-handwritten font-bold text-[#68635e] shrink-0">
                              {q.topic}
                            </span>
                          </div>

                          {q.question_type === "MCQ" && q.options && (
                            <div className="space-y-2 pt-1">
                              {q.options.map((opt: string) => (
                                <label
                                  key={opt}
                                  className={`p-3 rounded-md border block text-xs cursor-pointer transition-all ${
                                    diagAnswers[q.question_id] === opt
                                      ? "border-[#4a654e] bg-[#4a654e]/10 font-bold"
                                      : "border-[#252321]/20 hover:border-[#252321] bg-white/60"
                                  }`}
                                >
                                  <input
                                    type="radio"
                                    name={q.question_id}
                                    value={opt}
                                    checked={diagAnswers[q.question_id] === opt}
                                    onChange={() =>
                                      setDiagAnswers((prev) => ({ ...prev, [q.question_id]: opt }))
                                    }
                                    className="mr-2.5 accent-[#4a654e]"
                                  />
                                  {opt}
                                </label>
                              ))}
                            </div>
                          )}

                          {q.question_type === "SHORT_ANSWER" && (
                            <textarea
                              rows={3}
                              value={diagAnswers[q.question_id] || ""}
                              onChange={(e) =>
                                setDiagAnswers((prev) => ({ ...prev, [q.question_id]: e.target.value }))
                              }
                              placeholder="Write your explanation or derivation steps here..."
                              className="w-full p-3 text-xs rounded border border-[#252321]/30 bg-white focus:outline-none focus:border-[#252321]"
                            />
                          )}
                        </div>
                      ))}
                    </div>

                    <div className="flex justify-end">
                      <button
                        type="button"
                        disabled={diagLoading}
                        onClick={submitDiagnostic}
                        className="px-6 py-3 bg-[#4a654e] text-white font-bold text-sm rounded-md border-2 border-[#252321] shadow-[2px_3px_0px_#252321] cursor-pointer disabled:opacity-60"
                      >
                        {diagLoading ? "Evaluating…" : "Submit for Evaluation"}
                      </button>
                    </div>
                  </div>
                )}

                {diagState === "result" && diagResult && (
                  <div className="space-y-5">
                    <div className="p-6 rounded-lg border-2 border-[#252321] bg-[#ede8d5] space-y-3 shadow-[3px_4px_0px_#252321]">
                      <div className="flex items-center justify-between">
                        <h4 className="font-bold text-lg text-[#252321]">Diagnostic Result</h4>
                        <span
                          className={`text-xs px-3 py-1 rounded font-bold uppercase ${
                            diagResult.mastery_status === "MASTERED"
                              ? "bg-green-700 text-white"
                              : diagResult.mastery_status === "PARTIALLY_MASTERED"
                              ? "bg-amber-600 text-white"
                              : "bg-red-700 text-white"
                          }`}
                        >
                          {diagResult.mastery_status}
                        </span>
                      </div>
                      <div className="text-3xl font-bold text-[#4a654e]">
                        {fmtScore(diagResult.score)}
                      </div>
                      <p className="text-xs text-[#252321] leading-relaxed">{diagResult.feedback}</p>
                      {diagResult.topic_results && diagResult.topic_results.length > 0 && (
                        <div className="pt-2">
                          <p className="text-xs font-bold uppercase tracking-wider mb-2">
                            Per-topic outcome
                          </p>
                          <div className="space-y-1.5">
                            {diagResult.topic_results.map((t, i) => (
                              <div
                                key={i}
                                className="flex items-center justify-between text-xs p-2 rounded border border-[#252321]/20 bg-white/60"
                              >
                                <span className="font-medium">{t.topic}</span>
                                <span className="font-bold">
                                  {fmtScore(t.mastery_score)} • {t.outcome || t.status || "—"}
                                </span>
                              </div>
                            ))}
                          </div>
                        </div>
                      )}
                    </div>

                    {/* Baseline derived from the mastery store */}
                    <div className="p-5 rounded-md border-[1.5px] border-[#252321]/30 bg-white/50 space-y-3">
                      <h4 className="font-bold text-sm text-[#252321] flex items-center gap-2">
                        <span className="material-symbols-outlined text-base text-[#4a654e]">
                          insights
                        </span>
                        Your Baseline — strengths, weaknesses, gaps
                      </h4>
                      {!baseline || baseline.topic_count === 0 ? (
                        <p className="text-xs font-serif italic text-[#68635e]">
                          No baseline data recorded yet. Complete the diagnostic above and your
                          baseline will appear here — it is never guessed.
                        </p>
                      ) : (
                        <div className="grid sm:grid-cols-3 gap-3 text-xs">
                          <div className="p-3 rounded border border-green-600/40 bg-green-50/50">
                            <p className="font-bold text-green-800 mb-1.5">
                              Strengths ({baseline.strengths.length})
                            </p>
                            {baseline.strengths.length === 0 ? (
                              <p className="text-[#68635e] italic">None yet</p>
                            ) : (
                              baseline.strengths.map((s, i) => (
                                <p key={i} className="py-0.5">
                                  {s.topic} {s.mastery_score !== undefined && `• ${fmtScore(s.mastery_score)}`}
                                </p>
                              ))
                            )}
                          </div>
                          <div className="p-3 rounded border border-amber-600/40 bg-amber-50/50">
                            <p className="font-bold text-amber-800 mb-1.5">
                              Weaknesses ({baseline.weaknesses.length})
                            </p>
                            {baseline.weaknesses.length === 0 ? (
                              <p className="text-[#68635e] italic">None yet</p>
                            ) : (
                              baseline.weaknesses.map((s, i) => (
                                <p key={i} className="py-0.5">
                                  {s.topic} {s.mastery_score !== undefined && `• ${fmtScore(s.mastery_score)}`}
                                </p>
                              ))
                            )}
                          </div>
                          <div className="p-3 rounded border border-red-600/40 bg-red-50/50">
                            <p className="font-bold text-red-800 mb-1.5">Gaps ({baseline.gaps.length})</p>
                            {baseline.gaps.length === 0 ? (
                              <p className="text-[#68635e] italic">None yet</p>
                            ) : (
                              baseline.gaps.map((s, i) => (
                                <p key={i} className="py-0.5">
                                  {s.topic} {s.mastery_score !== undefined && `• ${fmtScore(s.mastery_score)}`}
                                </p>
                              ))
                            )}
                          </div>
                        </div>
                      )}
                    </div>

                    <div className="flex justify-end">
                      <button
                        type="button"
                        onClick={() => setStep(4)}
                        className="px-6 py-3 bg-[#252321] text-[#fdfae7] font-semibold text-sm rounded-md border-2 border-[#252321] shadow-[2px_3px_0px_rgba(37,35,33,0.9)] cursor-pointer"
                      >
                        Continue to Branch →
                      </button>
                    </div>
                  </div>
                )}

                {diagState !== "taking" && diagState !== "result" && diagState !== "unavailable" && (
                  <div className="flex justify-between pt-4 border-t border-dashed border-[#252321]/20">
                    <button
                      type="button"
                      onClick={() => setStep(2)}
                      className="px-5 py-2.5 border-[1.5px] border-[#252321] rounded-md text-xs font-semibold cursor-pointer"
                    >
                      ← Back
                    </button>
                    <button
                      type="button"
                      onClick={() => {
                        setDiagState("skipped");
                        setStep(4);
                      }}
                      className="px-5 py-2.5 border-[1.5px] border-[#252321]/50 rounded-md text-xs font-semibold cursor-pointer"
                    >
                      Skip for now
                    </button>
                  </div>
                )}
                {(diagState === "taking" || diagState === "result") && (
                  <div className="flex justify-start pt-4 border-t border-dashed border-[#252321]/20">
                    <button
                      type="button"
                      onClick={() => setStep(2)}
                      className="px-5 py-2.5 border-[1.5px] border-[#252321] rounded-md text-xs font-semibold cursor-pointer"
                    >
                      ← Back
                    </button>
                  </div>
                )}
              </motion.div>
            )}

            {/* STEP 4: ENGINEERING BRANCH (exactly 5 + General/Other) */}
            {step === 4 && (
              <motion.div
                key="step4"
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -10 }}
                className="space-y-6"
              >
                <div className="border-b border-dashed border-[#252321]/20 pb-4">
                  <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-[#8ba88e]/20 border border-[#8ba88e] text-xs font-medium mb-2">
                    <span className="material-symbols-outlined text-sm">engineering</span>
                    Field of Study
                  </div>
                  <h3 className="text-2xl sm:text-3xl font-bold text-[#252321]">
                    Select Your Engineering Discipline
                  </h3>
                  <p className="font-serif italic text-sm text-[#68635e] mt-1">
                    Five deeply-supported paths — or General / Other for a graceful fallback,
                    never a refusal.
                  </p>
                </div>

                <div className="grid sm:grid-cols-2 gap-3.5">
                  {BRANCHES.map((b) => (
                    <div
                      key={b.id}
                      onClick={() => handleBranchSelect(b.id)}
                      className={`p-4 rounded-md border-[1.5px] cursor-pointer transition-all flex items-start gap-3 ${
                        branch === b.id
                          ? "border-[#4a654e] bg-[#4a654e]/10 shadow-[2px_3px_0px_#4a654e]"
                          : "border-[#252321]/30 hover:border-[#252321] bg-white/40"
                      }`}
                    >
                      <div className="w-10 h-10 rounded-full bg-[#fdfae7] border border-[#252321]/30 flex items-center justify-center shrink-0 text-[#4a654e]">
                        <span className="material-symbols-outlined text-xl">{b.icon}</span>
                      </div>
                      <div className="flex-1">
                        <h4 className="font-bold text-sm text-[#252321]">{b.label}</h4>
                        <p className="text-xs text-[#68635e] mt-0.5 leading-relaxed">{b.desc}</p>
                      </div>
                    </div>
                  ))}
                </div>

                {/* Curriculum confirmation */}
                <div className="p-4 rounded-md border border-[#252321]/20 bg-white/40 text-xs">
                  {curriculumLoading ? (
                    <p className="font-serif italic text-[#68635e]">
                      Fetching verified curriculum for your university, branch and semester…
                    </p>
                  ) : curriculumError ? (
                    <p className="text-[#93000a]">
                      <span className="font-bold">Curriculum note:</span> no verified curriculum
                      found for this university / branch / semester combination
                      ({curriculumError}). You can continue — your plan will be built from the
                      subjects you confirm in the next step.
                    </p>
                  ) : branch && curriculumSubjects.length > 0 ? (
                    <p className="text-[#4a654e]">
                      <span className="font-bold">{curriculumSubjects.length} verified subjects</span>{" "}
                      found for Semester {semester} — you will confirm them in the next step.
                    </p>
                  ) : (
                    <p className="font-serif italic text-[#68635e]">
                      Select a branch above to load the verified curriculum for{" "}
                      {selectedUniversity?.name || "your university"}.
                    </p>
                  )}
                </div>

                <div className="flex justify-between pt-4 border-t border-dashed border-[#252321]/20">
                  <button
                    type="button"
                    onClick={() => setStep(3)}
                    className="px-5 py-2.5 border-[1.5px] border-[#252321] rounded-md text-xs font-semibold cursor-pointer"
                  >
                    ← Back
                  </button>
                  <button
                    type="button"
                    disabled={!branch}
                    onClick={() => branch && setStep(5)}
                    className="px-6 py-3 bg-[#252321] hover:bg-[#383430] text-[#fdfae7] font-semibold text-sm rounded-md border-2 border-[#252321] shadow-[2px_3px_0px_rgba(37,35,33,0.9)] flex items-center gap-2 cursor-pointer disabled:opacity-40"
                  >
                    <span>Choose Study Scope</span>
                    <span>→</span>
                  </button>
                </div>
              </motion.div>
            )}

            {/* STEP 5: SCOPE + TIMELINE */}
            {step === 5 && (
              <motion.div
                key="step5"
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -10 }}
                className="space-y-6"
              >
                <div className="border-b border-dashed border-[#252321]/20 pb-4">
                  <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-[#8ba88e]/20 border border-[#8ba88e] text-xs font-medium mb-2">
                    <span className="material-symbols-outlined text-sm">flag</span>
                    Target Horizon
                  </div>
                  <h3 className="text-2xl sm:text-3xl font-bold text-[#252321]">
                    How far should your plan reach?
                  </h3>
                  <p className="font-serif italic text-sm text-[#68635e] mt-1">
                    Pick the breadth of your learning plan — the whole program, this semester,
                    or one part of one subject.
                  </p>
                </div>

                <div className="grid sm:grid-cols-3 gap-3">
                  {SCOPES.map((s) => (
                    <div
                      key={s.id}
                      onClick={() => setScope(s.id)}
                      className={`p-4 rounded-md border-[1.5px] cursor-pointer transition-all ${
                        scope === s.id
                          ? "border-[#4a654e] bg-[#4a654e]/10 shadow-[2px_3px_0px_#4a654e]"
                          : "border-[#252321]/30 hover:border-[#252321] bg-white/40"
                      }`}
                    >
                      <span className="material-symbols-outlined text-xl text-[#4a654e]">
                        {s.icon}
                      </span>
                      <h4 className="font-bold text-sm text-[#252321] mt-1">{s.label}</h4>
                      <p className="text-xs text-[#68635e] mt-0.5 leading-relaxed">{s.desc}</p>
                    </div>
                  ))}
                </div>

                {scope === "SEMESTER" && (
                  <div>
                    <label className="block text-xs font-bold uppercase tracking-wider text-[#252321] mb-2">
                      Confirm Semester {semester} Subjects
                    </label>
                    {curriculumSubjects.length === 0 ? (
                      <div className="p-5 border border-dashed border-[#252321]/30 rounded-md bg-white/30 text-center">
                        <p className="text-xs text-[#68635e]">
                          No verified subjects were returned for this combination. Your plan
                          will still be generated from your branch context — we will not invent
                          subjects.
                        </p>
                      </div>
                    ) : (
                      <div className="space-y-2 max-h-52 overflow-y-auto pr-1">
                        {curriculumSubjects.map((sub) => {
                          const isSelected = selectedSubjectIds.includes(sub.subject_id);
                          return (
                            <div
                              key={sub.subject_id}
                              onClick={() => toggleSubject(sub.subject_id)}
                              className={`p-3 rounded-md border-[1.5px] cursor-pointer flex items-center justify-between transition-all ${
                                isSelected
                                  ? "border-[#4a654e] bg-[#4a654e]/10"
                                  : "border-[#252321]/20 bg-white/40 opacity-70"
                              }`}
                            >
                              <div className="flex items-center gap-2.5">
                                <span
                                  className={`w-4 h-4 rounded border flex items-center justify-center text-xs ${
                                    isSelected
                                      ? "bg-[#4a654e] border-[#4a654e] text-white"
                                      : "border-[#252321]/50 bg-white"
                                  }`}
                                >
                                  {isSelected && "✓"}
                                </span>
                                <div>
                                  <span className="text-xs font-mono font-bold text-[#4a654e] mr-2">
                                    {sub.code}
                                  </span>
                                  <span className="text-sm font-medium text-[#252321]">
                                    {sub.name}
                                  </span>
                                </div>
                              </div>
                              <span className="text-xs text-[#68635e] font-note-handwritten">
                                {sub.credits} Credits
                              </span>
                            </div>
                          );
                        })}
                      </div>
                    )}
                  </div>
                )}

                {scope === "SUBJECT_PART" && (
                  <div className="space-y-4">
                    <div>
                      <label className="block text-xs font-bold uppercase tracking-wider text-[#252321] mb-1.5">
                        Which subject?
                      </label>
                      {curriculumSubjects.length === 0 ? (
                        <p className="text-xs text-[#93000a] p-4 border border-dashed border-[#a65959] rounded-md bg-[#ffdad6]/20">
                          No verified subjects are available for this combination, so a
                          subject-part plan cannot be built honestly. Choose another scope, or go
                          back and change your branch.
                        </p>
                      ) : (
                        <select
                          value={partSubjectId}
                          onChange={(e) => setPartSubjectId(e.target.value)}
                          className="w-full px-3.5 py-2.5 rounded-md text-sm border-[1.5px] border-[#4a453f] bg-white/70"
                        >
                          {curriculumSubjects.map((s) => (
                            <option key={s.subject_id} value={s.subject_id}>
                              {s.code} — {s.name}
                            </option>
                          ))}
                        </select>
                      )}
                    </div>
                    <div>
                      <label className="block text-xs font-bold uppercase tracking-wider text-[#252321] mb-1.5">
                        Which part of it? (free text)
                      </label>
                      <input
                        type="text"
                        value={partDescription}
                        onChange={(e) => setPartDescription(e.target.value)}
                        placeholder="e.g. Units 3–4: tree traversals and AVL rotations"
                        className="w-full px-4 py-3 rounded-md text-sm border-[1.5px] border-[#4a453f] bg-white/70 focus:bg-white focus:outline-none"
                      />
                    </div>
                  </div>
                )}

                {/* Timeline & preferences */}
                <div className="grid sm:grid-cols-2 gap-4 pt-2 border-t border-dashed border-[#252321]/20">
                  <div>
                    <label className="block text-xs font-bold uppercase tracking-wider text-[#252321] mb-1.5">
                      Target Score / CGPA
                    </label>
                    <input
                      type="text"
                      value={targetScore}
                      onChange={(e) => setTargetScore(e.target.value)}
                      placeholder="e.g. 8.5 CGPA or 80%"
                      className="w-full px-3.5 py-2.5 rounded-md text-sm border-[1.5px] border-[#4a453f] bg-white/70"
                    />
                  </div>
                  <div>
                    <label className="block text-xs font-bold uppercase tracking-wider text-[#252321] mb-1.5">
                      Expected University Exam Date
                    </label>
                    <input
                      type="date"
                      value={examDate}
                      onChange={(e) => setExamDate(e.target.value)}
                      className="w-full px-3.5 py-2.5 rounded-md text-sm border-[1.5px] border-[#4a453f] bg-white/70"
                    />
                  </div>
                  <div>
                    <label className="block text-xs font-bold uppercase tracking-wider text-[#252321] mb-1.5">
                      Available Weekly Study Hours: {weeklyHours}h
                    </label>
                    <input
                      type="range"
                      min={6}
                      max={35}
                      value={weeklyHours}
                      onChange={(e) => setWeeklyHours(Number(e.target.value))}
                      className="w-full mt-2 accent-[#4a654e]"
                    />
                  </div>
                  <div>
                    <label className="block text-xs font-bold uppercase tracking-wider text-[#252321] mb-1.5">
                      How do you learn best?
                    </label>
                    <select
                      value={learningStyle}
                      onChange={(e) => setLearningStyle(e.target.value)}
                      className="w-full px-3.5 py-2.5 rounded-md text-sm border-[1.5px] border-[#4a453f] bg-white/70"
                    >
                      <option value="visual_examples">Visual animations & worked examples first</option>
                      <option value="rigorous_derivations">Step-by-step mathematical derivations</option>
                      <option value="practice_heavy">Short videos followed by immediate numericals</option>
                      <option value="pyq_driven">Exam-oriented syllabus review & past papers</option>
                    </select>
                  </div>
                </div>

                <div className="flex justify-between pt-4 border-t border-dashed border-[#252321]/20">
                  <button
                    type="button"
                    onClick={() => setStep(4)}
                    className="px-5 py-2.5 border-[1.5px] border-[#252321] rounded-md text-xs font-semibold cursor-pointer"
                  >
                    ← Back
                  </button>
                  <button
                    type="button"
                    disabled={submitting}
                    onClick={handleComplete}
                    className="px-8 py-3.5 bg-[#4a654e] hover:bg-[#3b523e] text-white font-bold text-base rounded-md border-2 border-[#252321] shadow-[2px_3px_0px_#252321] flex items-center gap-2 cursor-pointer transition-all disabled:opacity-60"
                  >
                    <span>{submitting ? "Synthesizing Plan..." : "Embark on Study Plan"}</span>
                    <span>→</span>
                  </button>
                </div>
              </motion.div>
            )}
          </AnimatePresence>
        </div>
      </main>

      {/* Footer */}
      <footer className="w-full max-w-5xl mx-auto px-6 py-4 text-center text-xs text-[#68635e]">
        PATHMIND Living Sketchbook • Grounded in Official Curricula
      </footer>
    </div>
  );
}
