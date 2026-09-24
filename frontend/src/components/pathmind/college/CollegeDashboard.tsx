"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import apiClient from "@/lib/api/client";
import { useAuth } from "@/lib/contexts/AuthContext";

/* ---------- helpers ---------- */

function fmtClock(totalSeconds?: number): string {
  if (totalSeconds === undefined || totalSeconds === null) return "—";
  const m = Math.floor(totalSeconds / 60);
  const s = Math.floor(totalSeconds % 60);
  return `${m}:${String(s).padStart(2, "0")}`;
}

function statusBadge(status?: string): string {
  switch (status) {
    case "COMPLETED":
      return "bg-green-100 text-green-800 border border-green-600";
    case "AVAILABLE":
    case "IN_PROGRESS":
      return "bg-amber-100 text-amber-800 border border-amber-600";
    default:
      return "bg-gray-100 text-gray-600 border border-gray-400";
  }
}

function masteryBadge(status?: string): string {
  switch (status) {
    case "MASTERED":
      return "bg-green-700 text-white";
    case "PARTIALLY_MASTERED":
      return "bg-amber-600 text-white";
    case "REINFORCEMENT_REQUIRED":
    case "INSUFFICIENT_EVIDENCE":
      return "bg-red-700 text-white";
    default:
      return "bg-gray-500 text-white";
  }
}

/* ---------- resource card with provenance ---------- */

function ResourceCard({ resource }: { resource: any }) {
  if (!resource) {
    return (
      <p className="text-[11px] font-serif italic text-[#68635e] pt-1">
        No verified resource attached to this activity yet — it relies on your own
        materials and the checkpoint below.
      </p>
    );
  }
  const meta = resource.learner_preference_metadata || {};
  const signals: string[] = [];
  if (meta.views !== undefined && meta.views !== null) signals.push(`${meta.views} views`);
  if (meta.likes !== undefined && meta.likes !== null) signals.push(`${meta.likes} likes`);
  if (meta.duration) signals.push(`duration ${meta.duration}`);

  return (
    <div className="pt-1.5 text-xs space-y-1.5">
      <div className="flex flex-wrap items-center gap-1.5">
        <span className="material-symbols-outlined text-xs text-[#4a654e]">link</span>
        <a
          href={resource.url}
          target="_blank"
          rel="noopener noreferrer"
          className="underline hover:text-black font-medium text-[#4a654e]"
        >
          {resource.title}
        </a>
      </div>
      <div className="flex flex-wrap items-center gap-1.5 text-[10px]">
        <span className="px-2 py-0.5 rounded bg-[#ede8d5] border border-[#252321]/30 font-semibold">
          {resource.provider}
        </span>
        {resource.source_tier && (
          <span className="px-2 py-0.5 rounded bg-[#4a654e]/10 border border-[#4a654e] font-bold text-[#4a654e]">
            Tier {resource.source_tier}
          </span>
        )}
        {resource.verification_status && (
          <span className="px-2 py-0.5 rounded bg-white border border-[#252321]/30 text-[#68635e]">
            {resource.verification_status}
          </span>
        )}
        {signals.length > 0 && (
          <span className="px-2 py-0.5 rounded bg-white border border-[#252321]/30 text-[#68635e]">
            {signals.join(" • ")}
          </span>
        )}
        {resource.estimated_minutes && (
          <span className="text-[#68635e] font-note-handwritten">
            ~{resource.estimated_minutes} min
          </span>
        )}
      </div>

      {resource.video_timestamps && resource.video_timestamps.length > 0 && (
        <div className="pt-1">
          <p className="text-[10px] font-bold uppercase tracking-wider text-[#68635e] mb-1">
            Key moments
          </p>
          <div className="space-y-0.5">
            {resource.video_timestamps.map((ts: any, i: number) => (
              <p key={i} className="text-[11px] text-[#423e3b]">
                <span className="font-mono font-bold text-[#4a654e]">
                  {fmtClock(ts.start_seconds)}–{fmtClock(ts.end_seconds)}
                </span>{" "}
                — {ts.purpose}
              </p>
            ))}
          </div>
        </div>
      )}

      {resource.document_sections && resource.document_sections.length > 0 && (
        <div className="pt-1">
          <p className="text-[10px] font-bold uppercase tracking-wider text-[#68635e] mb-1">
            Document sections
          </p>
          <div className="space-y-0.5">
            {resource.document_sections.map((ds: any, i: number) => (
              <p key={i} className="text-[11px] text-[#423e3b]">
                <span className="font-bold text-[#4a654e]">
                  pp. {ds.start_page}–{ds.end_page}
                </span>{" "}
                — {ds.section_title}
              </p>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

/* ---------- mentor ui_blocks renderer ---------- */

function UiBlock({ block }: { block: any }) {
  const type = block?.type;
  const data = block?.data || {};
  return (
    <div className="pt-2 border-t border-dashed border-gray-200 text-[11px] space-y-1">
      {type === "PYQ_VIEW" && data?.pyq_set ? (
        <div className="p-3 bg-[#fdfae7] rounded border border-[#252321]/20 space-y-1">
          <span className="font-bold text-[#a65959]">Verified PYQ Item:</span>
          <p>{data.pyq_set.questions?.[0]?.question_text || "No question text returned."}</p>
          {data.pyq_set.verification_status && (
            <p className="text-[#68635e]">Status: {data.pyq_set.verification_status}</p>
          )}
        </div>
      ) : type === "LEARNING_PLAN" ? (
        <div className="p-3 bg-[#fdfae7] rounded border border-[#252321]/20 space-y-1">
          <span className="font-bold text-[#4a654e]">Learning Plan{data.subject ? `: ${data.subject}` : ""}</span>
          {Array.isArray(data.steps) && data.steps.length > 0 ? (
            <ol className="list-decimal list-inside space-y-0.5">
              {data.steps.map((s: any, i: number) => (
                <li key={i}>{typeof s === "string" ? s : s?.title || s?.label || JSON.stringify(s)}</li>
              ))}
            </ol>
          ) : (
            <p className="text-[#68635e] italic">No steps were returned for this plan.</p>
          )}
        </div>
      ) : type === "RESOURCE_LIST" ? (
        <div className="p-3 bg-[#fdfae7] rounded border border-[#252321]/20 space-y-1.5">
          <span className="font-bold text-[#4a654e]">Resources</span>
          {Array.isArray(data.resources) && data.resources.length > 0 ? (
            data.resources.map((r: any, i: number) => (
              <div key={i} className="flex flex-col gap-0.5">
                {r.url ? (
                  <a href={r.url} target="_blank" rel="noopener noreferrer" className="underline font-medium">
                    {r.title || r.url}
                  </a>
                ) : (
                  <span className="font-medium">{r.title || "Untitled resource"}</span>
                )}
                <span className="text-[#68635e]">
                  {[r.provider, r.source_tier ? `Tier ${r.source_tier}` : null, r.verification_status]
                    .filter(Boolean)
                    .join(" • ")}
                </span>
              </div>
            ))
          ) : (
            <p className="text-[#68635e] italic">No verified resources were returned.</p>
          )}
        </div>
      ) : type === "NEXT_ACTION" ? (
        <div className="font-bold text-[#4a654e]">
          Recommended Action: {data.label || data.action || "—"}
        </div>
      ) : (
        <div className="text-[#68635e]">
          <span className="font-bold">{type || "UNKNOWN_BLOCK"}:</span>{" "}
          {data.label || data.title || data.message || "No displayable content returned."}
        </div>
      )}
    </div>
  );
}

/* ================= MAIN ================= */

export function CollegeDashboard() {
  const router = useRouter();
  const { user, signOut } = useAuth();
  const [activeTab, setActiveTab] = useState<
    "plan" | "pyq" | "assessment" | "accountability" | "mentor" | "memory"
  >("plan");

  // Core State
  const [userName, setUserName] = useState("");
  const [branch, setBranch] = useState<string>("");
  const [universityName, setUniversityName] = useState<string>("");
  const [academicContext, setAcademicContext] = useState<any>(null);
  const [learningPlan, setLearningPlan] = useState<any>(null);
  const [schedule, setSchedule] = useState<any>(null);
  const [pyqData, setPyqData] = useState<any>(null);
  const [pyqSubjects, setPyqSubjects] = useState<any[]>([]);
  const [pyqSubjectId, setPyqSubjectId] = useState<string>("");
  const [pyqError, setPyqError] = useState<string | null>(null);
  const [pyqScope, setPyqScope] = useState<"subject" | "program">("subject");
  const [pyqLevel, setPyqLevel] = useState<number>(1);
  const [activeAssessment, setActiveAssessment] = useState<any>(null);
  const [activePhaseId, setActivePhaseId] = useState<string | null>(null);
  const [assessmentResult, setAssessmentResult] = useState<any>(null);
  const [answers, setAnswers] = useState<Record<string, string>>({});
  const [actionError, setActionError] = useState<string | null>(null);
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
      setUserName(user.email?.split("@")[0] || "Scholar");
      loadAllData();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [user]);

  const loadAllData = async () => {
    try {
      // 1. Learner profile (branch lives here as supported_path)
      const profRes = await apiClient.get<any>("/api/college/profile");
      const profileBranch = profRes.ok && profRes.data ? profRes.data.supported_path : "";
      if (profileBranch) setBranch(profileBranch);

      // 2. Academic Context — without it there is nothing honest to show
      const ctxRes = await apiClient.get<any>("/api/college/academic-context");
      if (!ctxRes.ok || !ctxRes.data) {
        router.push("/onboarding");
        return;
      }
      const ctx = ctxRes.data;
      setAcademicContext(ctx);

      // 3. University display name from the verified registry (no invented names)
      if (ctx.university_id) {
        try {
          const uRes = await apiClient.get<any[]>("/api/college/universities?query=");
          if (uRes.ok && uRes.data) {
            const match = uRes.data.find((u: any) => u.university_id === ctx.university_id);
            if (match) setUniversityName(match.name);
          }
        } catch {
          /* display falls back to the id */
        }
      }

      // 4. Learning Plan, schedule, memories
      loadCurrentPlan();
      loadSchedule();
      loadMemories();

      // 5. PYQ subject options from the verified curriculum (never hardcoded ids)
      await loadPyqSubjects(ctx, profileBranch);
    } catch (err) {
      console.error("Failed to load dashboard data", err);
    }
  };

  const loadPyqSubjects = async (ctx: any, profileBranch: string) => {
    setPyqError(null);
    const univId = ctx?.university_id;
    const br = profileBranch || "";
    const sem = ctx?.semester;
    if (!univId || !br || !sem) {
      setPyqSubjects([]);
      setPyqError("PYQ lookup needs your university, branch and semester from onboarding.");
      return;
    }
    try {
      const res = await apiClient.get<any>(
        `/api/college/curriculum?university_id=${encodeURIComponent(univId)}&branch=${br}&semester=${sem}`
      );
      if (res.ok && res.data && Array.isArray(res.data.subjects) && res.data.subjects.length > 0) {
        const subs = res.data.subjects;
        setPyqSubjects(subs);
        const firstId = subs[0].subject_id;
        setPyqSubjectId(firstId);
        loadPYQs(univId, firstId);
      } else {
        setPyqSubjects([]);
        setPyqError(res.error || "No verified curriculum subjects found for PYQ lookup.");
      }
    } catch (err) {
      setPyqSubjects([]);
      setPyqError(err instanceof Error ? err.message : "Failed to load curriculum subjects.");
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

  const loadPYQs = async (
    universityId: string,
    subjectId: string,
    scope: "subject" | "program" = pyqScope,
    level: number = pyqLevel
  ) => {
    if (!universityId) return;
    setPyqError(null);
    try {
      const subj = pyqSubjects.find((s: any) => s.subject_id === subjectId);
      const params = new URLSearchParams({
        university_id: universityId,
        branch: branch || "",
        semester: String(academicContext?.semester ?? ""),
        scope,
        level: String(level),
      });
      if (subjectId) params.set("subject_id", subjectId);
      if (subj?.name) params.set("subject_name", subj.name);
      const res = await apiClient.get<any>(`/api/college/pyq/search?${params.toString()}`);
      if (res.ok) {
        setPyqData(res.data);
      } else {
        setPyqData(null);
        setPyqError(res.error || "Failed to load PYQs.");
      }
    } catch (err) {
      setPyqData(null);
      setPyqError(err instanceof Error ? err.message : "Failed to load PYQs.");
    }
  };

  const reloadPYQs = (scope: "subject" | "program", level: number) => {
    setPyqScope(scope);
    setPyqLevel(level);
    loadPYQs(academicContext?.university_id, pyqSubjectId, scope, level);
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
    setActionError(null);
    try {
      const res = await apiClient.post<any>(`/api/college/activities/${activityId}/complete`, {
        evidence: { self_reported_focus: 5 },
      });
      if (res.ok) {
        setLearningPlan(res.data);
        loadSchedule();
      } else {
        setActionError(res.error || "Could not mark the activity complete.");
      }
    } catch (err) {
      setActionError(err instanceof Error ? err.message : "Could not mark the activity complete.");
    }
  };

  const handleGenerateAssessment = async (phase: any) => {
    setActionError(null);
    if (!learningPlan?.plan_id || !phase?.phase_id) {
      setActionError("Cannot generate a checkpoint: plan or phase id is missing.");
      return;
    }
    const subjectId = academicContext?.subjects?.[0];
    if (!subjectId) {
      setActionError("Cannot generate a checkpoint: no subject is set on your academic context.");
      return;
    }
    try {
      const res = await apiClient.post<any>("/api/college/assessments/generate", {
        plan_id: learningPlan.plan_id,
        phase_id: phase.phase_id,
        subject_id: subjectId,
        topic_title: phase.title,
      });
      if (res.ok) {
        setActiveAssessment(res.data);
        setActivePhaseId(phase.phase_id);
        setAssessmentResult(null);
        setAnswers({});
        setActiveTab("assessment");
      } else {
        setActionError(res.error || "Could not generate the checkpoint assessment.");
      }
    } catch (err) {
      setActionError(err instanceof Error ? err.message : "Could not generate the checkpoint assessment.");
    }
  };

  const handleSubmitAssessment = async () => {
    if (!activeAssessment) return;
    setActionError(null);
    try {
      const res = await apiClient.post<any>("/api/college/assessments/submit", {
        assessment_id: activeAssessment.assessment_id,
        answers: answers,
      });
      if (res.ok) {
        setAssessmentResult(res.data);
        // Mastery-gated unlocks happen server-side on submit — reload so the
        // real locked/unlocked states (never client-side) are what renders.
        await loadCurrentPlan();
        loadSchedule();
        loadMemories();
      } else {
        setActionError(res.error || "Could not evaluate your submission.");
      }
    } catch (err) {
      setActionError(err instanceof Error ? err.message : "Could not evaluate your submission.");
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
        status: nextStatus,
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
        session_id: "sess_dashboard",
      });
      if (res.ok && res.data) {
        const data = res.data;
        setMentorMessages([
          ...newMsgList,
          {
            role: "agent",
            text: data.message,
            state: data.state,
            ui_blocks: data.ui_blocks,
            sources: data.sources,
          },
        ]);
        loadMemories();
      } else {
        setMentorMessages([
          ...newMsgList,
          {
            role: "agent",
            text: `The mentor could not respond: ${res.error || "unknown error"}. Your question was not answered — nothing was fabricated in its place.`,
            state: "ERROR",
            ui_blocks: [],
          },
        ]);
      }
    } catch (err) {
      setMentorMessages([
        ...newMsgList,
        {
          role: "agent",
          text: `The mentor request failed: ${err instanceof Error ? err.message : "network error"}. Please try again.`,
          state: "ERROR",
          ui_blocks: [],
        },
      ]);
    } finally {
      setChatLoading(false);
    }
  };

  const handleLogout = async () => {
    await signOut();
  };

  const branchLabel =
    branch?.replace(/_/g, " ").replace("ENGINEER", "Engineering") || "Engineering";
  const universityDisplay = universityName || academicContext?.university_id || "University not set";
  const examDays = schedule?.exam_days_remaining;
  // Phase whose checkpoint was just taken — used to narrate the mastery gate.
  const activePhase = (learningPlan?.phases || []).find((p: any) => p.phase_id === activePhaseId);
  const requiredScore = activePhase?.unlock_rule?.required_assessment_score;
  const nextPhaseUnlocked =
    assessmentResult &&
    activePhase &&
    (learningPlan?.phases || []).some(
      (p: any) => p.order === activePhase.order + 1 && p.status !== "LOCKED"
    );

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
            <p className="text-xs font-note-handwritten text-[#68635e]">Scholar: {userName}</p>
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
        {actionError && (
          <div className="p-4 rounded-md border-[1.5px] border-[#a65959] bg-[#ffdad6]/30 text-xs text-[#93000a]">
            <span className="font-bold">Action failed: </span>
            {actionError}
          </div>
        )}

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
                Academic Station
              </div>
              <h2 className="text-2xl sm:text-3xl font-bold text-[#252321]">
                {universityDisplay}
              </h2>
              <div className="flex flex-wrap items-center gap-2 pt-1 text-xs">
                <span className="px-2.5 py-1 rounded bg-[#4a654e]/10 border border-[#4a654e] font-semibold text-[#4a654e]">
                  {branchLabel}
                </span>
                <span className="px-2.5 py-1 rounded bg-[#ede8d5] border border-[#252321]/30 font-medium">
                  Semester {academicContext?.semester ?? "—"}
                </span>
                <span className="px-2.5 py-1 rounded bg-[#ede8d5] border border-[#252321]/30 font-medium">
                  Scope: {(learningPlan?.scope || "SEMESTER").replace(/_/g, " ")}
                </span>
                <span className="px-2.5 py-1 rounded bg-[#ede8d5] border border-[#252321]/30 font-medium">
                  Subjects: {academicContext?.subjects?.length ?? 0} active
                </span>
              </div>
            </div>

            {/* Exam Countdown Box */}
            <div className="bg-[#ede8d5]/80 p-4 rounded-md border border-[#252321]/30 text-center min-w-[140px]">
              <span className="text-[11px] uppercase tracking-wider font-bold text-[#68635e]">
                University Exam
              </span>
              <div className="text-3xl font-bold text-[#a65959] my-0.5">
                {examDays !== null && examDays !== undefined ? `${examDays}d` : "—"}
              </div>
              <span className="text-[11px] font-note-handwritten text-[#252321]">
                {examDays !== null && examDays !== undefined
                  ? "remaining in window"
                  : "no exam date set"}
              </span>
            </div>
          </div>
        </section>

        {/* Tab Navigation Rail */}
        <div className="flex flex-wrap gap-2 border-b border-[#252321]/20 pb-2">
          {[
            { id: "plan", label: "Ordered Study Plan", icon: "alt_route" },
            { id: "pyq", label: "PYQ Vault", icon: "history_edu" },
            { id: "assessment", label: "Checkpoint Assessment", icon: "quiz" },
            { id: "accountability", label: "Daily Trail & Schedule", icon: "event_available" },
            { id: "mentor", label: "Ask PATHMIND Mentor", icon: "smart_toy" },
            { id: "memory", label: "Memory Vault", icon: "psychology" },
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
                <p className="text-xs font-serif italic text-[#fdfae7]/80">
                  Your structured path forward. Phases unlock on demonstrated mastery — never
                  by clicking ahead.
                </p>
              </div>
            </div>
            {!learningPlan || !learningPlan.phases || learningPlan.phases.length === 0 ? (
              <div className="p-12 text-center border border-dashed border-[#252321]/30 rounded-lg bg-white/40">
                <p className="text-sm font-serif italic text-[#68635e]">
                  No study plan exists for your context yet. Generate one from onboarding, or
                  reload this page.
                </p>
                <button
                  onClick={() => loadAllData()}
                  className="mt-3 px-5 py-2 bg-[#4a654e] text-white text-xs font-bold rounded-md cursor-pointer"
                >
                  Reload Data
                </button>
              </div>
            ) : (
              learningPlan.phases.map((phase: any) => {
                const isLocked = phase.status === "LOCKED";
                const isDone = phase.status === "COMPLETED";
                const req = phase.unlock_rule?.required_assessment_score;
                return (
                  <div
                    key={phase.phase_id}
                    className={`p-6 rounded-lg bg-[#fdfae7] transition-all relative ${
                      isLocked
                        ? "opacity-60 border border-dashed border-[#252321]/40"
                        : "border-[1.75px] border-[#252321] shadow-[3px_4px_0px_#252321]"
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
                        {isLocked && (
                          <p className="text-[11px] text-[#68635e] mt-1.5 flex items-center gap-1">
                            <span className="material-symbols-outlined text-sm">lock</span>
                            Locked — complete the previous phase's checkpoint
                            {req !== undefined && req !== null
                              ? ` with at least ${req}%`
                              : " and demonstrate mastery"}
                            . Unlocking is decided server-side from your assessment results.
                          </p>
                        )}
                      </div>

                      <div className="flex items-center gap-2">
                        <span
                          className={`text-xs px-2.5 py-1 rounded font-bold ${statusBadge(phase.status)}`}
                        >
                          {phase.status}
                        </span>

                        {!isLocked && !isDone && (
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
                      {(phase.activities || []).length === 0 ? (
                        <p className="text-xs font-serif italic text-[#68635e] p-3">
                          No activities were generated for this phase.
                        </p>
                      ) : (
                        phase.activities.map((act: any) => {
                          const actDone = act.status === "COMPLETED";
                          return (
                            <div
                              key={act.activity_id}
                              className={`p-4 rounded-md border flex flex-wrap items-start justify-between gap-3 ${
                                actDone
                                  ? "bg-green-50/50 border-green-300"
                                  : "bg-white/70 border-[#252321]/30 hover:border-[#252321]"
                              }`}
                            >
                              <div className="space-y-1 max-w-2xl flex-1">
                                <div className="flex items-center gap-2 flex-wrap">
                                  <span className="text-[10px] uppercase font-bold tracking-wider px-2 py-0.5 rounded bg-[#252321] text-white">
                                    {act.activity_type}
                                  </span>
                                  <h4 className="font-bold text-sm text-[#252321]">{act.title}</h4>
                                  {act.estimated_minutes && (
                                    <span className="text-xs text-[#68635e] font-note-handwritten">
                                      ~{act.estimated_minutes} min
                                    </span>
                                  )}
                                </div>
                                <p className="text-xs text-[#423e3b] leading-relaxed">
                                  {act.instructions}
                                </p>

                                {/* Verified resource with provenance */}
                                <ResourceCard resource={act.resource} />

                                {/* PYQ Reference */}
                                {act.pyq_question && (
                                  <div className="text-xs text-[#a65959] font-medium pt-1">
                                    <span>
                                      University question reference: {act.pyq_question.marks} marks
                                    </span>
                                  </div>
                                )}
                              </div>

                              <div>
                                {!isLocked && !isDone && (
                                  <button
                                    onClick={() => handleCompleteActivity(act.activity_id)}
                                    className={`px-3 py-1.5 rounded text-xs font-bold transition-all cursor-pointer ${
                                      actDone
                                        ? "bg-green-600 text-white"
                                        : "bg-white border border-[#252321] hover:bg-[#252321] hover:text-white"
                                    }`}
                                  >
                                    {actDone ? "✓ Completed" : "Mark Done"}
                                  </button>
                                )}
                              </div>
                            </div>
                          );
                        })
                      )}
                    </div>
                  </div>
                );
              })
            )}
          </section>
        )}

        {/* TAB 2: PYQ VAULT */}
        {activeTab === "pyq" && (
          <section className="bg-[#fdfae7] p-6 rounded-lg border-[1.75px] border-[#252321] shadow-[3px_4px_0px_#252321] space-y-6">
            <div className="relative h-28 -mx-6 -mt-6 mb-6 rounded-t-lg overflow-hidden border-b-[1.75px] border-[#252321] bg-[#ede8d5]">
              <img src="/the_initiation_analog_final.png" alt="PYQ Vault" className="absolute inset-0 w-full h-full object-cover mix-blend-multiply opacity-90" />
              <div className="absolute inset-0 bg-gradient-to-t from-[#252321]/60 to-transparent"></div>
              <div className="absolute bottom-4 left-6">
                <h3 className="text-xl font-bold text-[#fdfae7] tracking-wide">The Initiation</h3>
                <p className="text-xs font-serif italic text-[#fdfae7]/80">
                  Only authentic, attributable exam questions — never invented.
                </p>
              </div>
            </div>
            <div className="flex flex-wrap items-center justify-between gap-3 border-b border-dashed border-[#252321]/20 pb-4">
              <div>
                <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-[#a65959]/20 border border-[#a65959] text-xs font-medium mb-1">
                  <span className="material-symbols-outlined text-sm">verified</span>
                  Examination Bank
                </div>
                <h3 className="text-2xl font-bold text-[#252321]">Previous Year Questions (PYQs)</h3>
                <p className="font-serif italic text-xs text-[#68635e]">
                  Drawn from official university examination archives when available.
                </p>
              </div>

              {/* Subject Selector — from verified curriculum only */}
              <div className="flex items-center gap-2">
                <span className="text-xs font-bold">Subject:</span>
                {pyqSubjects.length === 0 ? (
                  <span className="text-xs text-[#68635e] italic">No verified subjects loaded</span>
                ) : (
                  <select
                    value={pyqSubjectId}
                    onChange={(e) => {
                      setPyqSubjectId(e.target.value);
                      loadPYQs(academicContext?.university_id, e.target.value, pyqScope, pyqLevel);
                    }}
                    className="px-3 py-1.5 text-xs rounded border border-[#252321] bg-white"
                  >
                    {pyqSubjects.map((s: any) => (
                      <option key={s.subject_id} value={s.subject_id}>
                        {s.code}: {s.name}
                      </option>
                    ))}
                  </select>
                )}
              </div>
            </div>

            {/* Scope toggle: this subject only vs whole program (progressive levels) */}
            <div className="flex flex-wrap items-center gap-3">
              <div className="inline-flex rounded border border-[#252321] overflow-hidden text-xs font-bold">
                <button
                  onClick={() => reloadPYQs("subject", 1)}
                  className={`px-3 py-1.5 ${pyqScope === "subject" ? "bg-[#252321] text-[#fdfae7]" : "bg-white text-[#252321]"}`}
                >
                  This subject only
                </button>
                <button
                  onClick={() => reloadPYQs("program", 1)}
                  className={`px-3 py-1.5 ${pyqScope === "program" ? "bg-[#252321] text-[#fdfae7]" : "bg-white text-[#252321]"}`}
                >
                  Whole program
                </button>
              </div>
              {pyqScope === "program" && (
                <div className="flex items-center gap-1.5 text-xs">
                  <span className="font-bold text-[#68635e]">Level:</span>
                  {[1, 2, 3].map((l) => (
                    <button
                      key={l}
                      onClick={() => reloadPYQs("program", l)}
                      disabled={pyqData && !pyqData.has_more_levels && l > pyqLevel}
                      className={`w-7 h-7 rounded-full border border-[#252321] font-bold ${
                        pyqLevel === l ? "bg-[#a65959] text-white" : "bg-white text-[#252321]"
                      } disabled:opacity-40`}
                      title={l === 1 ? "Most recent papers" : l === 2 ? "Wider bank" : "Full archive"}
                    >
                      {l}
                    </button>
                  ))}
                  <span className="text-[#68635e] italic">
                    {pyqData?.level_label || "Level 1 — most recent papers first"}
                  </span>
                </div>
              )}
            </div>

            {/* What exactly these papers are scoped to — nothing is ever hardcoded */}
            <p className="text-[11px] text-[#68635e] italic -mt-1">
              Scoped to: {universityDisplay}
              {branch ? ` • ${branchLabel}` : ""}
              {academicContext?.semester ? ` • Semester ${academicContext.semester}` : ""}
              {pyqScope === "subject"
                ? (pyqSubjects.find((s: any) => s.subject_id === pyqSubjectId)?.name
                    ? ` • ${pyqSubjects.find((s: any) => s.subject_id === pyqSubjectId).name} only`
                    : " • pick a subject above")
                : " • all subjects of this semester, in levels"}
            </p>

            {pyqError && (
              <div className="p-4 border border-dashed border-[#a65959] rounded-md bg-[#ffdad6]/20 text-xs text-[#93000a]">
                {pyqError}
              </div>
            )}

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
            ) : pyqData.papers ? (
              <div className="space-y-4">
                <div className="flex flex-wrap items-center justify-between gap-2 text-xs text-[#68635e]">
                  <span>
                    {pyqData.level_label} • {pyqData.total_found} paper{pyqData.total_found === 1 ? "" : "s"} from official university sources
                  </span>
                  <span className="text-[#4a654e] font-bold">{pyqData.status}</span>
                </div>
                <div className="space-y-3">
                  {pyqData.papers.map((p: any) => (
                    <div
                      key={p.paper_id}
                      className="p-4 rounded-md border border-[#252321]/30 bg-white/70 space-y-2"
                    >
                      <div className="flex items-start justify-between gap-3">
                        <div>
                          <p className="font-bold text-sm text-[#252321]">{p.title}</p>
                          <p className="text-[11px] text-[#68635e] mt-1">
                            {p.year ? `Exam year: ${p.year} • ` : ""}
                            Source: {p.source_domain || "university archive"} •
                            Trust tier {p.trust_tier || "A"} •
                            {p.retrieval === "realtime" ? " found live on the official site" : " curated archive"}
                          </p>
                        </div>
                        {p.download_url && (
                          <a
                            href={p.download_url}
                            target="_blank"
                            rel="noopener noreferrer"
                            download
                            className="shrink-0 inline-flex items-center gap-1.5 px-3 py-1.5 rounded border border-[#252321] bg-[#252321] text-[#fdfae7] text-xs font-bold hover:opacity-90"
                          >
                            <span className="material-symbols-outlined text-sm">download</span>
                            Download
                          </a>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
                {pyqData.has_more_levels && (
                  <button
                    onClick={() => reloadPYQs("program", pyqLevel + 1)}
                    className="w-full py-2 rounded border border-dashed border-[#252321]/40 text-xs font-bold text-[#252321] hover:bg-white/60"
                  >
                    Unlock Level {pyqLevel + 1} — wider question bank →
                  </button>
                )}
              </div>
            ) : (
              <div className="space-y-4">
                <div className="flex flex-wrap items-center justify-between gap-2 text-xs text-[#68635e]">
                  <span>
                    Exam Year: {pyqData.pyq_set?.exam_year ?? "—"} •{" "}
                    {pyqData.pyq_set?.exam_type ?? "—"}
                  </span>
                  {pyqData.pyq_set?.verification_status && (
                    <span className="text-[#4a654e] font-bold">
                      {pyqData.pyq_set.verification_status}
                    </span>
                  )}
                </div>

                <div className="space-y-3">
                  {(pyqData.pyq_set?.questions || []).map((q: any) => (
                    <div
                      key={q.question_id}
                      className="p-4 rounded-md border border-[#252321]/30 bg-white/70 space-y-2"
                    >
                      <div className="flex items-center justify-between">
                        <span className="font-bold text-sm text-[#252321]">
                          {q.question_number}
                        </span>
                        {q.marks !== undefined && q.marks !== null && (
                          <span className="text-xs px-2 py-0.5 rounded bg-amber-100 border border-amber-400 font-bold">
                            {q.marks} Marks
                          </span>
                        )}
                      </div>
                      <p className="text-xs text-[#252321] leading-relaxed font-mono bg-[#fdfae7] p-3 rounded border border-[#252321]/10">
                        {q.question_text}
                      </p>
                      {q.topic_ids && q.topic_ids.length > 0 && (
                        <div className="flex flex-wrap gap-1.5 text-[10px] text-[#68635e]">
                          <span className="font-bold">Topics:</span>
                          {q.topic_ids.map((t: string) => (
                            <span
                              key={t}
                              className="px-2 py-0.5 rounded bg-gray-100 border border-gray-300"
                            >
                              {t}
                            </span>
                          ))}
                        </div>
                      )}
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
                <p className="text-xs font-serif italic text-[#fdfae7]/80">
                  Every phase ends with a checkpoint. Pass it to unlock what comes next.
                </p>
              </div>
            </div>
            {!activeAssessment ? (
              <div className="p-10 text-center border border-dashed border-[#252321]/30 rounded-lg bg-white/40">
                <span className="material-symbols-outlined text-3xl text-[#4a654e] mb-2">
                  assignment
                </span>
                <h4 className="font-bold text-base text-[#252321]">No Active Checkpoint</h4>
                <p className="text-xs font-serif italic text-[#68635e] mt-1 max-w-sm mx-auto">
                  Go to the Study Plan tab and click "Take Checkpoint" on an unlocked phase.
                  Assessment is what gates the next phase — finishing activities alone does not.
                </p>
              </div>
            ) : (
              <div className="space-y-6">
                <div className="border-b border-dashed border-[#252321]/20 pb-3">
                  <span className="text-xs px-2.5 py-1 rounded bg-[#4a654e]/10 border border-[#4a654e] text-[#4a654e] font-bold">
                    {activeAssessment.assessment_kind === "DIAGNOSTIC"
                      ? "Diagnostic Assessment"
                      : "Phase Checkpoint"}
                  </span>
                  <h3 className="text-2xl font-bold text-[#252321] mt-2">
                    {activeAssessment.title}
                  </h3>
                  <p className="text-xs font-serif italic text-[#68635e]">
                    {requiredScore !== undefined && requiredScore !== null
                      ? `Score at least ${requiredScore}% to unlock the next phase.`
                      : "Answer all items to evaluate mastery."}{" "}
                    Unlocking is decided server-side from your results.
                  </p>
                </div>

                {/* Question Items */}
                <div className="space-y-5">
                  {(activeAssessment.questions || []).map((q: any, idx: number) => (
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
                          {q.marks !== undefined && q.marks !== null && ` • ${q.marks} marks`}
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

                {/* Evaluation Result Banner — pass/fail, honest */}
                {assessmentResult && (
                  <div className="p-6 rounded-lg border-2 border-[#252321] bg-[#ede8d5] space-y-3 mt-6 shadow-[3px_4px_0px_#252321]">
                    <div className="flex items-center justify-between">
                      <h4 className="font-bold text-lg text-[#252321]">
                        Mastery Evaluation Result
                      </h4>
                      <span
                        className={`text-xs px-3 py-1 rounded font-bold uppercase ${masteryBadge(
                          assessmentResult.mastery_status
                        )}`}
                      >
                        {assessmentResult.mastery_status}
                      </span>
                    </div>

                    <div className="text-3xl font-bold text-[#4a654e]">
                      {assessmentResult.score !== undefined && assessmentResult.score !== null
                        ? `${Math.round(assessmentResult.score)}%`
                        : "—"}
                    </div>
                    <p className="text-xs text-[#252321] leading-relaxed">
                      {assessmentResult.feedback}
                    </p>

                    {assessmentResult.evaluation_confidence !== undefined &&
                      assessmentResult.evaluation_confidence !== null && (
                        <p className="text-[11px] text-[#68635e]">
                          Evaluation confidence:{" "}
                          {Math.round(assessmentResult.evaluation_confidence * 100)}%
                        </p>
                      )}

                    {assessmentResult.topic_results &&
                      assessmentResult.topic_results.length > 0 && (
                        <div className="pt-1">
                          <p className="text-xs font-bold uppercase tracking-wider mb-2">
                            Per-topic outcome
                          </p>
                          <div className="space-y-1.5">
                            {assessmentResult.topic_results.map((t: any, i: number) => (
                              <div
                                key={i}
                                className="flex items-center justify-between text-xs p-2 rounded border border-[#252321]/20 bg-white/60"
                              >
                                <span className="font-medium">{t.topic}</span>
                                <span className="font-bold">
                                  {t.mastery_score !== undefined && t.mastery_score !== null
                                    ? `${Math.round(t.mastery_score)}% • `
                                    : ""}
                                  {t.outcome || t.status || "—"}
                                </span>
                              </div>
                            ))}
                          </div>
                        </div>
                      )}

                    {/* Mastery gate narration — real phase state, never client-side unlock */}
                    {activePhase && (
                      <div className="pt-2 border-t border-dashed border-[#252321]/20">
                        {nextPhaseUnlocked ? (
                          <p className="text-xs font-bold text-green-800 flex items-center gap-1.5">
                            <span className="material-symbols-outlined text-sm">lock_open</span>
                            Demonstrated mastery — the next phase is now unlocked in your study
                            plan.
                          </p>
                        ) : (
                          <p className="text-xs text-[#68635e] flex items-center gap-1.5">
                            <span className="material-symbols-outlined text-sm">lock</span>
                            The next phase stays locked until a checkpoint meets the mastery
                            requirement
                            {requiredScore !== undefined && requiredScore !== null
                              ? ` (${requiredScore}%)`
                              : ""}
                            . Retake the checkpoint when ready.
                          </p>
                        )}
                      </div>
                    )}
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
                  Streak:{" "}
                  {schedule?.streak_days !== undefined && schedule?.streak_days !== null
                    ? `${schedule.streak_days} Days`
                    : "—"}
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
                    {examDays !== null && examDays !== undefined
                      ? `${examDays} Days`
                      : "No exam date set"}
                  </span>
                </div>
                <div className="flex justify-between py-1 border-b border-[#252321]/10">
                  <span className="text-[#68635e]">Weekly Study Target:</span>
                  <span className="font-bold">{academicContext?.available_hours_per_week ?? "—"} Hours</span>
                </div>
                <div className="flex justify-between py-1 border-b border-[#252321]/10">
                  <span className="text-[#68635e]">Planned Minutes Today:</span>
                  <span className="font-bold">{schedule?.total_planned_minutes ?? 0}m</span>
                </div>
                <div className="flex justify-between py-1">
                  <span className="text-[#68635e]">Completed Today:</span>
                  <span className="font-bold text-green-700">
                    {schedule?.total_completed_minutes ?? 0}m
                  </span>
                </div>
              </div>
            </div>
            </div>
          </section>
        )}

        {/* TAB 5: MENTOR DIALOGUE */}
        {activeTab === "mentor" && (
          <section className="bg-[#fdfae7] p-6 rounded-lg border-[1.75px] border-[#252321] shadow-[3px_4px_0px_#252321] space-y-5">
            <div className="border-b border-dashed border-[#252321]/20 pb-3">
              <h3 className="text-xl font-bold text-[#252321]">Engineering Academic Mentor</h3>
              <p className="font-serif italic text-xs text-[#68635e]">
                Ask questions about your syllabus, past exams, or technical concepts. The mentor
                answers from your academic context and verified curriculum — when it has no
                verified answer, it says so.
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
                    {m.state && m.role === "agent" && (
                      <span className="inline-block text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 rounded bg-[#ede8d5] border border-[#252321]/30 text-[#68635e]">
                        {m.state.replace(/_/g, " ")}
                      </span>
                    )}
                    <p>{m.text}</p>

                    {/* Render Structured UI blocks */}
                    {m.ui_blocks && m.ui_blocks.map((block: any, bIdx: number) => (
                      <UiBlock key={bIdx} block={block} />
                    ))}

                    {/* Provenance */}
                    {m.sources && m.sources.length > 0 && (
                      <div className="pt-2 border-t border-dashed border-gray-200 text-[10px] text-[#68635e]">
                        <span className="font-bold">Sources: </span>
                        {m.sources.map((s: any, sIdx: number) => (
                          <span key={sIdx}>
                            {sIdx > 0 && " • "}
                            {typeof s === "string" ? s : s?.name || s?.title || s?.url || "—"}
                          </span>
                        ))}
                      </div>
                    )}
                  </div>
                ))
              )}
              {chatLoading && (
                <div className="text-xs font-serif italic text-[#68635e]">
                  PATHMIND is consulting your academic context...
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
                className="px-6 py-3 bg-[#252321] text-white font-bold text-xs rounded-md shadow-[2px_2px_0px_#252321] cursor-pointer disabled:opacity-60"
              >
                Send
              </button>
            </form>
          </section>
        )}

        {/* TAB 6: MEMORY VAULT */}
        {activeTab === "memory" && (
          <section className="bg-[#fdfae7] p-6 rounded-lg border-[1.75px] border-[#252321] shadow-[3px_4px_0px_#252321] space-y-6">
            <div className="border-b border-dashed border-[#252321]/20 pb-3">
              <h3 className="text-xl font-bold text-[#252321]">Memory Vault</h3>
              <p className="font-serif italic text-xs text-[#68635e]">
                What PATHMIND remembers about your learning — recorded from your real
                interactions, never invented.
              </p>
            </div>

            <div className="grid md:grid-cols-3 gap-4">
              <div className="p-4 rounded-md border border-[#252321]/30 bg-white/50">
                <h4 className="font-bold text-sm mb-2 flex items-center gap-1.5">
                  <span className="material-symbols-outlined text-base text-[#4a654e]">
                    schedule
                  </span>
                  Short-Term ({memories.short_term?.length ?? 0})
                </h4>
                {!memories.short_term || memories.short_term.length === 0 ? (
                  <p className="text-xs font-serif italic text-[#68635e]">
                    No session context recorded yet.
                  </p>
                ) : (
                  <div className="space-y-2 max-h-64 overflow-y-auto">
                    {memories.short_term.map((m: any) => (
                      <p key={m.memory_id} className="text-xs p-2 rounded bg-white border border-[#252321]/20">
                        {m.content}
                      </p>
                    ))}
                  </div>
                )}
              </div>

              <div className="p-4 rounded-md border border-[#252321]/30 bg-white/50">
                <h4 className="font-bold text-sm mb-2 flex items-center gap-1.5">
                  <span className="material-symbols-outlined text-base text-[#4a654e]">
                    database
                  </span>
                  Long-Term ({memories.long_term?.length ?? 0})
                </h4>
                {!memories.long_term || memories.long_term.length === 0 ? (
                  <p className="text-xs font-serif italic text-[#68635e]">
                    No durable memories recorded yet.
                  </p>
                ) : (
                  <div className="space-y-2 max-h-64 overflow-y-auto">
                    {memories.long_term.map((m: any) => (
                      <div key={m.memory_id} className="text-xs p-2 rounded bg-white border border-[#252321]/20 space-y-1">
                        <p className="font-bold">{m.title}</p>
                        <p className="text-[#423e3b]">{m.content}</p>
                        <p className="text-[10px] text-[#68635e]">
                          {[m.memory_type, m.status, m.confidence ? `confidence ${m.confidence}` : null]
                            .filter(Boolean)
                            .join(" • ")}
                        </p>
                      </div>
                    ))}
                  </div>
                )}
              </div>

              <div className="p-4 rounded-md border border-[#252321]/30 bg-white/50">
                <h4 className="font-bold text-sm mb-2 flex items-center gap-1.5">
                  <span className="material-symbols-outlined text-base text-[#a65959]">
                    monitoring
                  </span>
                  Learning Signals ({memories.learning_signals?.length ?? 0})
                </h4>
                {!memories.learning_signals || memories.learning_signals.length === 0 ? (
                  <p className="text-xs font-serif italic text-[#68635e]">
                    No learning signals recorded yet. Signals are created when checkpoints
                    reveal reinforcement needs.
                  </p>
                ) : (
                  <div className="space-y-2 max-h-64 overflow-y-auto">
                    {memories.learning_signals.map((s: any, i: number) => (
                      <div key={s.signal_id || i} className="text-xs p-2 rounded bg-white border border-[#252321]/20 space-y-1">
                        <p className="font-bold">{s.signal_type || "Signal"}</p>
                        <p className="text-[#423e3b]">{s.content || s.description || ""}</p>
                        {s.topic && <p className="text-[10px] text-[#68635e]">Topic: {s.topic}</p>}
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>
          </section>
        )}
      </main>

      {/* Footer */}
      <footer className="w-full max-w-7xl mx-auto px-6 py-4 text-center text-xs text-[#68635e] border-t border-[#252321]/20">
        PATHMIND College Engineering MVP • Plans, unlocks and evaluations are computed
        server-side from your real data
      </footer>
    </div>
  );
}
