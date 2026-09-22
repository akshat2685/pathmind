"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import apiClient from "@/lib/api/client";
import { useAuth } from "@/lib/contexts/AuthContext";

export function CollegeDashboard() {
  const router = useRouter();
  const { user, signOut } = useAuth();
  const [activeTab, setActiveTab] = useState<
    "plan" | "pyq" | "assessment" | "accountability" | "memory" | "mentor"
  >("plan");

  // Core State
  const [personId, setPersonId] = useState("");
  const [userName, setUserName] = useState("");
  const [academicContext, setAcademicContext] = useState<any>(null);
  const [learningPlan, setLearningPlan] = useState<any>(null);
  const [schedule, setSchedule] = useState<any>(null);
  const [pyqData, setPyqData] = useState<any>(null);
  const [activeAssessment, setActiveAssessment] = useState<any>(null);
  const [assessmentResult, setAssessmentResult] = useState<any>(null);
  const [answers, setAnswers] = useState<Record<string, string>>({});
  const [memories, setMemories] = useState<any>({ short_term: [], long_term: [], learning_signals: [] });

  // Mentor Chat State
  const [mentorQuery, setMentorQuery] = useState("");
  const [mentorMessages, setMentorMessages] = useState<any[]>([]);
  const [chatLoading, setChatLoading] = useState(false);

  // New Commitment State
  const [newCmtTitle, setNewCmtTitle] = useState("");
  const [newCmtMinutes, setNewCmtMinutes] = useState(45);

  useEffect(() => {
    if (user) {
      setPersonId(user.id);
      setUserName(user.email?.split('@')[0] || "Scholar");
      loadAllData();
    }
  }, [user]);

  const loadAllData = async () => {
    try {
      // 1. Academic Context
      const ctxRes = await apiClient.get<any>("/api/college/academic-context");
      if (ctxRes.ok && ctxRes.data) {
        setAcademicContext(ctxRes.data);
        loadPYQs(ctxRes.data.university_id || "univ_aicte_model", ctxRes.data.subjects?.[0] || "sub_cs_dsa");
      } else {
        router.push("/onboarding");
        return;
      }

      // 2. Learning Plan
      loadCurrentPlan();

      // 3. Accountability Schedule
      loadSchedule();

      // 4. Memory Vault
      loadMemories();
    } catch (err) {
      console.error("Failed to load dashboard data", err);
    }
  };

  const loadCurrentPlan = async () => {
    try {
      const planRes = await apiClient.get<any>("/api/college/plans/current");
      if (planRes.ok) {
        setLearningPlan(planRes.data);
      }
    } catch (err) {
      console.error("Failed to load plan", err);
    }
  };

  const loadSchedule = async () => {
    try {
      const schedRes = await apiClient.get<any>("/api/college/accountability/today");
      if (schedRes.ok) {
        setSchedule(schedRes.data);
      }
    } catch (err) {
      console.error("Failed to load schedule", err);
    }
  };

  const loadPYQs = async (universityId: string, subjectId: string) => {
    try {
      const res = await apiClient.get<any>(`/api/college/pyqs?university_id=${encodeURIComponent(universityId)}&subject_id=${encodeURIComponent(subjectId)}`);
      if (res.ok) {
        setPyqData(res.data);
      }
    } catch (err) {
      console.error("Failed to load PYQs", err);
    }
  };

  const loadMemories = async () => {
    try {
      const res = await apiClient.get<any>("/api/college/memory");
      if (res.ok) {
        setMemories(res.data);
      }
    } catch (err) {
      console.error("Failed to load memories", err);
    }
  };

  const handleCompleteActivity = async (activityId: string) => {
    try {
      const res = await apiClient.post<any>(`/api/college/activities/${activityId}/complete`, {
        evidence: { self_reported_focus: 5 }
      });
      if (res.ok) {
        setLearningPlan(res.data);
        loadSchedule();
      }
    } catch (err) {
      console.error("Failed to complete activity", err);
    }
  };

  const handleGenerateAssessment = async (phase: any) => {
    try {
      const res = await apiClient.post<any>("/api/college/assessments/generate", {
        plan_id: learningPlan?.plan_id || "plan_active",
        phase_id: phase.phase_id,
        subject_id: academicContext?.subjects?.[0] || "sub_active",
        topic_title: phase.title,
      });
      if (res.ok) {
        setActiveAssessment(res.data);
        setAssessmentResult(null);
        setAnswers({});
        setActiveTab("assessment");
      }
    } catch (err) {
      console.error("Failed to generate assessment", err);
    }
  };

  const handleSubmitAssessment = async () => {
    if (!activeAssessment) return;
    try {
      const res = await apiClient.post<any>("/api/college/assessments/submit", {
        assessment_id: activeAssessment.assessment_id,
        answers: answers,
      });
      if (res.ok) {
        setAssessmentResult(res.data);
        loadMemories();
      }
    } catch (err) {
      console.error("Failed to submit assessment", err);
    }
  };

  const handleCreateCommitment = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newCmtTitle.trim()) return;
    try {
      const res = await apiClient.post<any>("/api/college/accountability/commit", {
        title: newCmtTitle,
        due_at: new Date().toISOString(),
        estimated_minutes: Number(newCmtMinutes),
      });
      if (res.ok) {
        setNewCmtTitle("");
        loadSchedule();
      }
    } catch (err) {
      console.error("Failed to create commitment", err);
    }
  };

  const handleToggleCommitment = async (cmtId: string, currentStatus: string) => {
    const nextStatus = currentStatus === "COMPLETED" ? "PLANNED" : "COMPLETED";
    try {
      await apiClient.patch<any>(`/api/college/accountability/commit/${cmtId}`, {
        status: nextStatus 
      });
      loadSchedule();
    } catch (err) {
      console.error("Failed to toggle commitment", err);
    }
  };

  const handleSendMentor = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!mentorQuery.trim()) return;
    const q = mentorQuery;
    setMentorQuery("");
    setChatLoading(true);

    const newMsgList = [...mentorMessages, { role: "user", text: q }];
    setMentorMessages(newMsgList);

    try {
      const res = await apiClient.post<any>("/api/college/agent/interact", {
        message: q, 
        session_id: "sess_dashboard" 
      });
      if (res.ok && res.data) {
        const data = res.data;
        setMentorMessages([
          ...newMsgList,
          { role: "agent", text: data.message, ui_blocks: data.ui_blocks, sources: data.sources },
        ]);
        loadMemories();
      }
    } catch (err) {
      console.error("Mentor query failed", err);
    } finally {
      setChatLoading(false);
    }
  };

  const handleLogout = async () => {
    await signOut();
  };

  const branchLabel = academicContext?.branch?.replace(/_/g, " ").replace("ENGINEER", "Engineering") || "Engineering";

  return (
    <div className="min-h-screen bg-[#f7f4e7] text-[#252321] flex flex-col justify-between font-sans">
      {/* Background Notebook Grid */}
      <div
        className="fixed inset-0 pointer-events-none opacity-80 -z-20"
        style={{
          backgroundImage:
            "linear-gradient(to right, rgba(90, 80, 70, 0.05) 1px, transparent 1px), linear-gradient(to bottom, rgba(90, 80, 70, 0.05) 1px, transparent 1px)",
          backgroundSize: "28px 28px",
        }}
      />

      {/* Top Header */}
      <header className="w-full max-w-7xl mx-auto px-6 py-4 flex items-center justify-between border-b border-[#252321]/20">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-full border-[1.75px] border-[#252321] bg-[#fdfae7] flex items-center justify-center">
            <span className="material-symbols-outlined text-[#4a654e] text-2xl">
              auto_stories
            </span>
          </div>
          <div>
            <div className="flex items-center gap-2">
              <span className="font-bold text-xl text-[#252321]">PATHMIND</span>
              <span className="text-xs px-2 py-0.5 rounded bg-[#8ba88e]/20 border border-[#8ba88e] text-[#252321] font-semibold">
                College MVP
              </span>
            </div>
            <p className="text-xs font-note-handwritten text-[#68635e]">
              Scholar: {userName} • {personId}
            </p>
          </div>
        </div>

        <div className="flex items-center gap-3">
          <Link
            href="/onboarding"
            className="text-xs px-3 py-1.5 border border-[#252321]/40 hover:border-[#252321] rounded-md font-medium"
          >
            Change Context
          </Link>
          <button
            onClick={handleLogout}
            className="text-xs px-3 py-1.5 border border-[#a65959]/40 hover:border-[#a65959] text-[#a65959] rounded-md font-medium cursor-pointer"
          >
            Exit Journal
          </button>
        </div>
      </header>

      {/* Main Content Area */}
      <main className="flex-grow max-w-7xl w-full mx-auto px-4 sm:px-6 py-6 space-y-6">
        {/* Command Center Card */}
        <section
          className="bg-[#fdfae7] p-6 rounded-lg relative overflow-hidden"
          style={{
            border: "1.75px solid #252321",
            boxShadow: "3px 4px 0px rgba(37, 35, 33, 0.9)",
          }}
        >
          <div className="flex flex-wrap items-center justify-between gap-4">
            <div className="space-y-1">
              <div className="inline-flex items-center gap-2 text-xs font-serif italic text-[#68635e]">
                <span className="w-2 h-2 rounded-full bg-[#8ba88e]"></span>
                Verified Academic Station
              </div>
              <h2 className="text-2xl sm:text-3xl font-bold text-[#252321]">
                {academicContext?.university_name || "AICTE Model Engineering College"}
              </h2>
              <div className="flex flex-wrap items-center gap-2 pt-1 text-xs">
                <span className="px-2.5 py-1 rounded bg-[#4a654e]/10 border border-[#4a654e] font-semibold text-[#4a654e]">
                  {branchLabel}
                </span>
                <span className="px-2.5 py-1 rounded bg-[#ede8d5] border border-[#252321]/30 font-medium">
                  Semester {academicContext?.semester || 3}
                </span>
                <span className="px-2.5 py-1 rounded bg-[#ede8d5] border border-[#252321]/30 font-medium">
                  Subjects: {academicContext?.subjects?.length || 0} active
                </span>
              </div>
            </div>

            {/* Exam Countdown Box */}
            <div className="bg-[#ede8d5]/80 p-4 rounded-md border border-[#252321]/30 text-center min-w-[140px]">
              <span className="text-[11px] uppercase tracking-wider font-bold text-[#68635e]">
                University Exam
              </span>
              <div className="text-3xl font-bold text-[#a65959] my-0.5">
                {schedule?.exam_days_remaining !== null && schedule?.exam_days_remaining !== undefined
                  ? `${schedule.exam_days_remaining}d`
                  : "Active"}
              </div>
              <span className="text-[11px] font-note-handwritten text-[#252321]">
                remaining in window
              </span>
            </div>
          </div>
        </section>

        {/* Tab Navigation Rail */}
        <div className="flex flex-wrap gap-2 border-b border-[#252321]/20 pb-2">
          {[
            { id: "plan", label: "Ordered Study Plan", icon: "alt_route" },
            { id: "pyq", label: "Verified PYQ Vault", icon: "history_edu" },
            { id: "assessment", label: "Checkpoint Assessment", icon: "quiz" },
            { id: "accountability", label: "Daily Trail & Schedule", icon: "event_available" },
            { id: "mentor", label: "Ask PATHMIND Mentor", icon: "smart_toy" },
          ].map((t) => (
            <button
              key={t.id}
              onClick={() => setActiveTab(t.id as any)}
              className={`px-4 py-2 rounded-md text-xs font-bold flex items-center gap-1.5 cursor-pointer transition-all ${
                activeTab === t.id
                  ? "bg-[#252321] text-[#fdfae7] shadow-[2px_2px_0px_rgba(37,35,33,0.9)]"
                  : "bg-white/50 border border-[#252321]/30 text-[#252321] hover:bg-white"
              }`}
            >
              <span className="material-symbols-outlined text-sm">{t.icon}</span>
              {t.label}
            </button>
          ))}
        </div>

        {/* TAB 1: ORDERED STUDY PLAN */}
        {activeTab === "plan" && (
          <section className="space-y-6">
            <div className="relative h-32 rounded-lg overflow-hidden border-[1.75px] border-[#252321] shadow-[3px_4px_0px_#252321] mb-6 bg-[#ede8d5]">
              <img src="/the_unfolding_map_analog_final.png" alt="Study Plan" className="absolute inset-0 w-full h-full object-cover mix-blend-multiply opacity-90" />
              <div className="absolute inset-0 bg-gradient-to-t from-[#252321]/60 to-transparent"></div>
              <div className="absolute bottom-4 left-6">
                <h3 className="text-2xl font-bold text-[#fdfae7] tracking-wide">The Unfolding Map</h3>
                <p className="text-xs font-serif italic text-[#fdfae7]/80">Your structured path forward.</p>
              </div>
            </div>
            {!learningPlan || !learningPlan.phases || learningPlan.phases.length === 0 ? (
              <div className="p-12 text-center border border-dashed border-[#252321]/30 rounded-lg bg-white/40">
                <p className="text-sm font-serif italic text-[#68635e]">
                  No study plan synthesized yet. Click to generate an ordered sequence.
                </p>
                <button
                  onClick={() => loadAllData()}
                  className="mt-3 px-5 py-2 bg-[#4a654e] text-white text-xs font-bold rounded-md"
                >
                  Generate Study Plan
                </button>
              </div>
            ) : (
              learningPlan.phases.map((phase: any, pIdx: number) => {
                const isLocked = phase.status === "LOCKED";
                return (
                  <div
                    key={phase.phase_id}
                    className={`p-6 rounded-lg bg-[#fdfae7] transition-all relative ${
                      isLocked ? "opacity-60 border border-dashed border-[#252321]/40" : "border-[1.75px] border-[#252321] shadow-[3px_4px_0px_#252321]"
                    }`}
                  >
                    <div className="flex flex-wrap items-center justify-between gap-2 border-b border-dashed border-[#252321]/20 pb-3 mb-4">
                      <div>
                        <div className="flex items-center gap-2">
                          <span className="text-xs px-2 py-0.5 rounded bg-[#4a654e] text-white font-bold">
                            Phase {phase.order}
                          </span>
                          <h3 className="font-bold text-lg text-[#252321]">{phase.title}</h3>
                        </div>
                        <p className="text-xs text-[#68635e] mt-0.5">{phase.objective}</p>
                      </div>

                      <div className="flex items-center gap-2">
                        <span
                          className={`text-xs px-2.5 py-1 rounded font-bold ${
                            phase.status === "COMPLETED"
                              ? "bg-green-100 text-green-800 border border-green-600"
                              : phase.status === "AVAILABLE"
                              ? "bg-amber-100 text-amber-800 border border-amber-600"
                              : "bg-gray-100 text-gray-600 border border-gray-400"
                          }`}
                        >
                          {phase.status}
                        </span>

                        {!isLocked && (
                          <button
                            onClick={() => handleGenerateAssessment(phase)}
                            className="px-3 py-1.5 bg-[#4a654e] text-white text-xs font-bold rounded hover:bg-[#3b523e] cursor-pointer"
                          >
                            Take Checkpoint
                          </button>
                        )}
                      </div>
                    </div>

                    {/* Phase Activities */}
                    <div className="space-y-3">
                      {phase.activities.map((act: any) => {
                        const isDone = act.status === "COMPLETED";
                        return (
                          <div
                            key={act.activity_id}
                            className={`p-4 rounded-md border flex flex-wrap items-start justify-between gap-3 ${
                              isDone
                                ? "bg-green-50/50 border-green-300"
                                : "bg-white/70 border-[#252321]/30 hover:border-[#252321]"
                            }`}
                          >
                            <div className="space-y-1 max-w-2xl">
                              <div className="flex items-center gap-2">
                                <span className="text-[10px] uppercase font-bold tracking-wider px-2 py-0.5 rounded bg-[#252321] text-white">
                                  {act.activity_type}
                                </span>
                                <h4 className="font-bold text-sm text-[#252321]">{act.title}</h4>
                                <span className="text-xs text-[#68635e] font-note-handwritten">
                                  ~{act.estimated_minutes} min
                                </span>
                              </div>
                              <p className="text-xs text-[#423e3b] leading-relaxed">{act.instructions}</p>

                              {/* Resource Reference */}
                              {act.resource && (
                                <div className="text-xs text-[#4a654e] font-medium flex items-center gap-1.5 pt-1">
                                  <span className="material-symbols-outlined text-xs">link</span>
                                  <span>{act.resource.provider}</span> •{" "}
                                  <a
                                    href={act.resource.url}
                                    target="_blank"
                                    rel="noopener noreferrer"
                                    className="underline hover:text-black"
                                  >
                                    {act.resource.title}
                                  </a>
                                </div>
                              )}

                              {/* PYQ Reference */}
                              {act.pyq_question && (
                                <div className="text-xs text-[#a65959] font-medium pt-1">
                                  <span>Authentic University Question: {act.pyq_question.marks} Marks</span>
                                </div>
                              )}
                            </div>

                            <div>
                              {!isLocked && (
                                <button
                                  onClick={() => handleCompleteActivity(act.activity_id)}
                                  className={`px-3 py-1.5 rounded text-xs font-bold transition-all cursor-pointer ${
                                    isDone
                                      ? "bg-green-600 text-white"
                                      : "bg-white border border-[#252321] hover:bg-[#252321] hover:text-white"
                                  }`}
                                >
                                  {isDone ? "✓ Completed" : "Mark Done"}
                                </button>
                              )}
                            </div>
                          </div>
                        );
                      })}
                    </div>
                  </div>
                );
              })
            )}
          </section>
        )}

        {/* TAB 2: VERIFIED PYQ VAULT */}
        {activeTab === "pyq" && (
          <section className="bg-[#fdfae7] p-6 rounded-lg border-[1.75px] border-[#252321] shadow-[3px_4px_0px_#252321] space-y-6">
            <div className="relative h-28 -mx-6 -mt-6 mb-6 rounded-t-lg overflow-hidden border-b-[1.75px] border-[#252321] bg-[#ede8d5]">
              <img src="/the_initiation_analog_final.png" alt="PYQ Vault" className="absolute inset-0 w-full h-full object-cover mix-blend-multiply opacity-90" />
              <div className="absolute inset-0 bg-gradient-to-t from-[#252321]/60 to-transparent"></div>
              <div className="absolute bottom-4 left-6">
                <h3 className="text-xl font-bold text-[#fdfae7] tracking-wide">The Initiation</h3>
                <p className="text-xs font-serif italic text-[#fdfae7]/80">Past exams demystified.</p>
              </div>
            </div>
            <div className="flex flex-wrap items-center justify-between gap-3 border-b border-dashed border-[#252321]/20 pb-4">
              <div>
                <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-[#a65959]/20 border border-[#a65959] text-xs font-medium mb-1">
                  <span className="material-symbols-outlined text-sm">verified</span>
                  Official Examination Bank
                </div>
                <h3 className="text-2xl font-bold text-[#252321]">
                  Previous Year Questions (PYQs)
                </h3>
                <p className="font-serif italic text-xs text-[#68635e]">
                  Mapped exclusively from authentic AICTE and university examination archives.
                </p>
              </div>

              {/* Subject Selector */}
              <div className="flex items-center gap-2">
                <span className="text-xs font-bold">Subject:</span>
                <select
                  onChange={(e) => loadPYQs(academicContext?.university_id || "univ_aicte_model", e.target.value)}
                  className="px-3 py-1.5 text-xs rounded border border-[#252321] bg-white"
                >
                  <option value="sub_cs_dsa">CS-301: Data Structures</option>
                  <option value="sub_me_thermo">ME-301: Thermodynamics</option>
                  <option value="sub_ee_circuits">EE-301: Circuit Analysis</option>
                  <option value="sub_ai_ml">AI-401: Machine Learning</option>
                  <option value="sub_ce_struct">CE-401: Structural Analysis</option>
                </select>
              </div>
            </div>

            {/* PYQ Results */}
            {!pyqData || pyqData.status === "PYQ_NOT_AVAILABLE" ? (
              <div className="p-8 border border-dashed border-[#a65959] rounded-md bg-[#ffdad6]/20 text-center">
                <span className="material-symbols-outlined text-3xl text-[#a65959] mb-2">
                  info
                </span>
                <h4 className="font-bold text-sm text-[#93000a]">PYQ_NOT_AVAILABLE</h4>
                <p className="text-xs text-[#68635e] mt-1 max-w-md mx-auto">
                  {pyqData?.message ||
                    "Verified previous year examination questions are currently unavailable for this subject from official repositories. No synthetic questions are substituted."}
                </p>
              </div>
            ) : (
              <div className="space-y-4">
                <div className="flex items-center justify-between text-xs text-[#68635e]">
                  <span>Exam Year: {pyqData.pyq_set.exam_year} • {pyqData.pyq_set.exam_type}</span>
                  <span className="text-[#4a654e] font-bold">Verified Tier A Repository</span>
                </div>

                <div className="space-y-3">
                  {pyqData.pyq_set.questions.map((q: any) => (
                    <div
                      key={q.question_id}
                      className="p-4 rounded-md border border-[#252321]/30 bg-white/70 space-y-2"
                    >
                      <div className="flex items-center justify-between">
                        <span className="font-bold text-sm text-[#252321]">{q.question_number}</span>
                        <span className="text-xs px-2 py-0.5 rounded bg-amber-100 border border-amber-400 font-bold">
                          {q.marks} Marks
                        </span>
                      </div>
                      <p className="text-xs text-[#252321] leading-relaxed font-mono bg-[#fdfae7] p-3 rounded border border-[#252321]/10">
                        {q.question_text}
                      </p>
                      <div className="flex flex-wrap gap-1.5 text-[10px] text-[#68635e]">
                        <span className="font-bold">Topics:</span>
                        {q.topic_ids.map((t: string) => (
                          <span key={t} className="px-2 py-0.5 rounded bg-gray-100 border border-gray-300">
                            {t}
                          </span>
                        ))}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </section>
        )}

        {/* TAB 3: CHECKPOINT ASSESSMENTS */}
        {activeTab === "assessment" && (
          <section className="bg-[#fdfae7] p-6 rounded-lg border-[1.75px] border-[#252321] shadow-[3px_4px_0px_#252321] space-y-6">
            <div className="relative h-28 -mx-6 -mt-6 mb-6 rounded-t-lg overflow-hidden border-b-[1.75px] border-[#252321] bg-[#ede8d5]">
              <img src="/the_first_step_analog_final.png" alt="Assessments" className="absolute inset-0 w-full h-full object-cover mix-blend-multiply opacity-90" />
              <div className="absolute inset-0 bg-gradient-to-t from-[#252321]/60 to-transparent"></div>
              <div className="absolute bottom-4 left-6">
                <h3 className="text-xl font-bold text-[#fdfae7] tracking-wide">The First Step</h3>
                <p className="text-xs font-serif italic text-[#fdfae7]/80">Test your mastery and resilience.</p>
              </div>
            </div>
            {!activeAssessment ? (
              <div className="p-10 text-center border border-dashed border-[#252321]/30 rounded-lg bg-white/40">
                <span className="material-symbols-outlined text-3xl text-[#4a654e] mb-2">
                  assignment
                </span>
                <h4 className="font-bold text-base text-[#252321]">No Active Checkpoint</h4>
                <p className="text-xs font-serif italic text-[#68635e] mt-1 max-w-sm mx-auto">
                  Go to the Study Plan tab and click "Take Checkpoint" on any active phase to generate diagnostic verification.
                </p>
              </div>
            ) : (
              <div className="space-y-6">
                <div className="border-b border-dashed border-[#252321]/20 pb-3">
                  <span className="text-xs px-2.5 py-1 rounded bg-[#4a654e]/10 border border-[#4a654e] text-[#4a654e] font-bold">
                    Diagnostic Checkpoint
                  </span>
                  <h3 className="text-2xl font-bold text-[#252321] mt-2">
                    {activeAssessment.title}
                  </h3>
                  <p className="text-xs font-serif italic text-[#68635e]">
                    Answer all items to evaluate mastery and unlock upcoming milestones.
                  </p>
                </div>

                {/* Question Items */}
                <div className="space-y-5">
                  {activeAssessment.questions.map((q: any, idx: number) => (
                    <div
                      key={q.question_id}
                      className="p-5 rounded-md border border-[#252321]/30 bg-white/70 space-y-3"
                    >
                      <div className="flex justify-between items-start">
                        <h4 className="font-bold text-sm text-[#252321]">
                          Item {idx + 1}. {q.question_text}
                        </h4>
                        <span className="text-xs font-note-handwritten font-bold text-[#68635e]">
                          {q.marks} Marks
                        </span>
                      </div>

                      {q.question_type === "MCQ" && q.options && (
                        <div className="space-y-2 pt-1">
                          {q.options.map((opt: string) => (
                            <label
                              key={opt}
                              className={`p-3 rounded-md border block text-xs cursor-pointer transition-all ${
                                answers[q.question_id] === opt
                                  ? "border-[#4a654e] bg-[#4a654e]/10 font-bold"
                                  : "border-[#252321]/20 hover:border-[#252321] bg-white/60"
                              }`}
                            >
                              <input
                                type="radio"
                                name={q.question_id}
                                value={opt}
                                checked={answers[q.question_id] === opt}
                                onChange={() =>
                                  setAnswers((prev) => ({ ...prev, [q.question_id]: opt }))
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
                          value={answers[q.question_id] || ""}
                          onChange={(e) =>
                            setAnswers((prev) => ({ ...prev, [q.question_id]: e.target.value }))
                          }
                          placeholder="Write your explanation or derivation steps here..."
                          className="w-full p-3 text-xs rounded border border-[#252321]/30 bg-white focus:outline-none focus:border-[#252321]"
                        />
                      )}
                    </div>
                  ))}
                </div>

                {/* Submit Assessment Button */}
                <div className="flex justify-end">
                  <button
                    onClick={handleSubmitAssessment}
                    className="px-6 py-3 bg-[#4a654e] text-white font-bold text-sm rounded-md border-2 border-[#252321] shadow-[2px_3px_0px_#252321] cursor-pointer"
                  >
                    Submit for Evaluation
                  </button>
                </div>

                {/* Evaluation Result Banner */}
                {assessmentResult && (
                  <div className="p-6 rounded-lg border-2 border-[#252321] bg-[#ede8d5] space-y-3 mt-6 shadow-[3px_4px_0px_#252321]">
                    <div className="flex items-center justify-between">
                      <h4 className="font-bold text-lg text-[#252321]">
                        Mastery Evaluation Result
                      </h4>
                      <span
                        className={`text-xs px-3 py-1 rounded font-bold uppercase ${
                          assessmentResult.mastery_status === "MASTERED"
                            ? "bg-green-700 text-white"
                            : assessmentResult.mastery_status === "PARTIALLY_MASTERED"
                            ? "bg-amber-600 text-white"
                            : "bg-red-700 text-white"
                        }`}
                      >
                        {assessmentResult.mastery_status}
                      </span>
                    </div>

                    <div className="text-3xl font-bold text-[#4a654e]">
                      {assessmentResult.score}%
                    </div>
                    <p className="text-xs text-[#252321] leading-relaxed">
                      {assessmentResult.feedback}
                    </p>
                  </div>
                )}
              </div>
            )}
          </section>
        )}

        {/* TAB 4: ACCOUNTABILITY & DAILY TRAIL */}
        {activeTab === "accountability" && (
          <section className="space-y-6">
            <div className="relative h-32 rounded-lg overflow-hidden border-[1.75px] border-[#252321] shadow-[3px_4px_0px_#252321] bg-[#ede8d5]">
              <img src="/accountability_circle_analog_final.png" alt="Accountability" className="absolute inset-0 w-full h-full object-cover mix-blend-multiply opacity-90" />
              <div className="absolute inset-0 bg-gradient-to-t from-[#252321]/60 to-transparent"></div>
              <div className="absolute bottom-4 left-6">
                <h3 className="text-2xl font-bold text-[#fdfae7] tracking-wide">Accountability Circle</h3>
                <p className="text-xs font-serif italic text-[#fdfae7]/80">Stay on track, together.</p>
              </div>
            </div>
            <div className="grid lg:grid-cols-12 gap-6">
            <div className="lg:col-span-7 bg-[#fdfae7] p-6 rounded-lg border-[1.75px] border-[#252321] shadow-[3px_4px_0px_#252321] space-y-5">
              <div className="border-b border-dashed border-[#252321]/20 pb-3 flex justify-between items-center">
                <div>
                  <h3 className="text-xl font-bold text-[#252321]">Today's Study Commitments</h3>
                  <p className="text-xs font-serif italic text-[#68635e]">
                    Track study milestones against your verified semester target.
                  </p>
                </div>
                <div className="text-xs font-bold px-3 py-1 rounded bg-[#8ba88e]/20 border border-[#8ba88e]">
                  Streak: {schedule?.streak_days || 1} Days
                </div>
              </div>

              {/* Commitments List */}
              <div className="space-y-3">
                {!schedule?.commitments || schedule.commitments.length === 0 ? (
                  <p className="text-xs font-serif italic text-[#68635e] p-4 text-center">
                    No active commitments logged for today yet.
                  </p>
                ) : (
                  schedule.commitments.map((cmt: any) => {
                    const isDone = cmt.status === "COMPLETED";
                    return (
                      <div
                        key={cmt.commitment_id}
                        onClick={() => handleToggleCommitment(cmt.commitment_id, cmt.status)}
                        className={`p-3.5 rounded-md border flex items-center justify-between cursor-pointer transition-all ${
                          isDone
                            ? "bg-green-50 border-green-300 line-through opacity-70"
                            : "bg-white/70 border-[#252321]/30 hover:border-[#252321]"
                        }`}
                      >
                        <div className="flex items-center gap-2.5">
                          <span
                            className={`w-4 h-4 rounded border flex items-center justify-center text-xs ${
                              isDone ? "bg-green-600 text-white" : "bg-white border-black"
                            }`}
                          >
                            {isDone && "✓"}
                          </span>
                          <div>
                            <h5 className="font-semibold text-xs text-[#252321]">{cmt.title}</h5>
                            <span className="text-[10px] text-[#68635e]">
                              ~{cmt.estimated_minutes} min
                            </span>
                          </div>
                        </div>
                        <span className="text-[11px] font-bold uppercase text-[#68635e]">
                          {cmt.status}
                        </span>
                      </div>
                    );
                  })
                )}
              </div>

              {/* Add Commitment Form */}
              <form onSubmit={handleCreateCommitment} className="pt-3 border-t border-dashed border-[#252321]/20 flex gap-2">
                <input
                  type="text"
                  value={newCmtTitle}
                  onChange={(e) => setNewCmtTitle(e.target.value)}
                  placeholder="e.g. Derive Euler-Bernoulli equation (45 min)"
                  className="flex-grow px-3 py-2 text-xs rounded border border-[#252321] bg-white"
                />
                <select
                  value={newCmtMinutes}
                  onChange={(e) => setNewCmtMinutes(Number(e.target.value))}
                  className="px-2 py-2 text-xs rounded border border-[#252321] bg-white"
                >
                  <option value={30}>30m</option>
                  <option value={45}>45m</option>
                  <option value={60}>60m</option>
                  <option value={90}>90m</option>
                </select>
                <button
                  type="submit"
                  className="px-4 py-2 bg-[#252321] text-white text-xs font-bold rounded cursor-pointer"
                >
                  Add
                </button>
              </form>
            </div>

            {/* Right Column: Urgency & Summary */}
            <div className="lg:col-span-5 bg-[#ede8d5] p-6 rounded-lg border-[1.75px] border-[#252321] shadow-[3px_4px_0px_#252321] space-y-4">
              <h3 className="font-bold text-base text-[#252321]">Exam Countdown &amp; Workload</h3>
              <div className="space-y-2 text-xs">
                <div className="flex justify-between py-1 border-b border-[#252321]/10">
                  <span className="text-[#68635e]">Days Remaining:</span>
                  <span className="font-bold text-[#a65959]">
                    {schedule?.exam_days_remaining ?? "Active"} Days
                  </span>
                </div>
                <div className="flex justify-between py-1 border-b border-[#252321]/10">
                  <span className="text-[#68635e]">Weekly Study Target:</span>
                  <span className="font-bold">{academicContext?.available_hours_per_week || 14} Hours</span>
                </div>
                <div className="flex justify-between py-1 border-b border-[#252321]/10">
                  <span className="text-[#68635e]">Planned Minutes Today:</span>
                  <span className="font-bold">{schedule?.total_planned_minutes || 0}m</span>
                </div>
                <div className="flex justify-between py-1">
                  <span className="text-[#68635e]">Completed Today:</span>
                  <span className="font-bold text-green-700">
                    {schedule?.total_completed_minutes || 0}m
                  </span>
                </div>
              </div>
            </div>
            </div>
          </section>
        )}



        {/* TAB 6: MENTOR DIALOGUE */}
        {activeTab === "mentor" && (
          <section className="bg-[#fdfae7] p-6 rounded-lg border-[1.75px] border-[#252321] shadow-[3px_4px_0px_#252321] space-y-5">
            <div className="border-b border-dashed border-[#252321]/20 pb-3">
              <h3 className="text-xl font-bold text-[#252321]">Engineering Academic Mentor</h3>
              <p className="font-serif italic text-xs text-[#68635e]">
                Ask questions about your syllabus, past exams, or technical concepts. Powered by Gemini reasoning and verified AICTE curriculum tools.
              </p>
            </div>

            {/* Chat Feed */}
            <div className="space-y-4 max-h-96 overflow-y-auto p-2">
              {mentorMessages.length === 0 ? (
                <div className="p-8 text-center text-xs font-serif italic text-[#68635e]">
                  "Ask me anything about your university syllabus, PYQ strategies, or derivations..."
                </div>
              ) : (
                mentorMessages.map((m, idx) => (
                  <div
                    key={idx}
                    className={`p-4 rounded-md text-xs leading-relaxed max-w-2xl ${
                      m.role === "user"
                        ? "ml-auto bg-[#4a654e] text-white"
                        : "mr-auto bg-white border border-[#252321]/30 text-[#252321] space-y-2"
                    }`}
                  >
                    <p>{m.text}</p>

                    {/* Render Structured UI blocks if returned */}
                    {m.ui_blocks && m.ui_blocks.map((block: any, bIdx: number) => (
                      <div key={bIdx} className="pt-2 border-t border-dashed border-gray-200">
                        {block.type === "PYQ_VIEW" && block.data?.pyq_set && (
                          <div className="p-3 bg-[#fdfae7] rounded border border-[#252321]/20 text-[11px] space-y-1">
                            <span className="font-bold text-[#a65959]">Verified PYQ Item:</span>
                            <p>{block.data.pyq_set.questions?.[0]?.question_text}</p>
                          </div>
                        )}
                        {block.type === "NEXT_ACTION" && (
                          <div className="text-[11px] font-bold text-[#4a654e]">
                            Recommended Action: {block.data?.label}
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                ))
              )}
              {chatLoading && (
                <div className="text-xs font-serif italic text-[#68635e]">
                  PATHMIND is analyzing verified curriculum...
                </div>
              )}
            </div>

            {/* Input Bar */}
            <form onSubmit={handleSendMentor} className="flex gap-2 pt-2 border-t border-dashed border-[#252321]/20">
              <input
                type="text"
                value={mentorQuery}
                onChange={(e) => setMentorQuery(e.target.value)}
                placeholder="Ask about your semester exam, a specific concept, or PYQs..."
                className="flex-grow px-4 py-3 rounded-md text-xs border border-[#252321] bg-white focus:outline-none"
              />
              <button
                type="submit"
                disabled={chatLoading}
                className="px-6 py-3 bg-[#252321] text-white font-bold text-xs rounded-md shadow-[2px_2px_0px_#252321] cursor-pointer"
              >
                Send
              </button>
            </form>
          </section>
        )}
      </main>

      {/* Footer */}
      <footer className="w-full max-w-7xl mx-auto px-6 py-4 text-center text-xs text-[#68635e] border-t border-[#252321]/20">
        PATHMIND College Engineering MVP • Grounded in AICTE &amp; State Technical Curricula
      </footer>
    </div>
  );
}
