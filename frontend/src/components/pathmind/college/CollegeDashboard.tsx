"use client";

import { useState, useEffect, useRef } from "react";
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

// Resource hunts already attempted in this browser session. Persisted in
// sessionStorage so leaving and returning to the dashboard (or remounting
// it) never restarts the auto-research cascade from phase 1 — that repeat
// churn was a big part of the post-onboarding lag.
const HUNT_STORAGE_KEY = "pathmind.attemptedResourceHunts";

function readAttemptedHunts(): string[] {
  try {
    const raw = sessionStorage.getItem(HUNT_STORAGE_KEY);
    const parsed = raw ? JSON.parse(raw) : [];
    return Array.isArray(parsed)
      ? parsed.filter((x) => typeof x === "string")
      : [];
  } catch {
    return [];
  }
}

function persistAttemptedHunts(attempted: Set<string>) {
  try {
    sessionStorage.setItem(
      HUNT_STORAGE_KEY,
      JSON.stringify([...attempted].slice(-32))
    );
  } catch {
    /* storage unavailable (private mode) — hunts stay per-mount */
  }
}

// phase_id format: phase_{plan_id}_{subject_id}_s{semester}_u{unit}
function subjectIdFromPhaseId(phaseId: string, planId: string): string | null {
  const m = /^phase_(.*)_s\d+_u\d+$/.exec(phaseId || "");
  if (!m) return null;
  const prefix = `${planId}_`;
  return m[1].startsWith(prefix) ? m[1].slice(prefix.length) || null : null;
}

/* ---------- exam-lens path helpers (Direction B) ---------- */

// Resource lanes persisted by the research pipeline on each resource's
// quality_signals (PR #47 spec, PR #49 persistence). Chips render only
// for lanes actually present in the learner's plan data — never faked.
const LANE_STYLE: Record<string, { label: string; cls: string }> = {
  ONE_SHOT: {
    label: "▶ One-shot",
    cls: "bg-[#4a654e] text-[#fdfae7] border-[#3b523e]",
  },
  PYQ: { label: "PYQ", cls: "bg-[#a65959] text-[#fdfae7] border-[#7c3f3f]" },
  IMPORTANT_QUESTIONS: {
    label: "Important questions",
    cls: "bg-[#ede8d5] text-[#252321] border-[#252321]",
  },
  NOTES: {
    label: "Notes",
    cls: "bg-[#ede8d5] text-[#252321] border-[#252321]",
  },
};

function phaseStats(phase: any) {
  const acts = phase?.activities || [];
  const done = acts.filter((a: any) => a.status === "COMPLETED").length;
  const pct = acts.length ? Math.round((done / acts.length) * 100) : 0;
  const laneSet = new Set<string>();
  let hindi = false;
  let pyqMarks = 0;
  for (const a of acts) {
    const lane = a?.resource?.quality_signals?.lane;
    if (typeof lane === "string" && lane) laneSet.add(lane);
    if (
      a?.resource?.resource_type === "VIDEO" &&
      /hindi/i.test(a?.resource?.title || "")
    )
      hindi = true;
    if (typeof a?.pyq_question?.marks === "number") pyqMarks += a.pyq_question.marks;
    if (a?.activity_type === "SOLVE_PYQ") laneSet.add("PYQ");
  }
  const lanes = [...laneSet];
  return {
    total: acts.length,
    done,
    pct,
    lanes,
    hindi,
    pyqMarks,
    highYield: laneSet.has("IMPORTANT_QUESTIONS") || pyqMarks >= 10,
  };
}

function unitNumberOf(phase: any): number {
  const m = /_u(\d+)$/.exec(phase?.phase_id || "");
  if (m) return parseInt(m[1], 10);
  return typeof phase?.order === "number" ? phase.order : 0;
}

/* ---------- resource card with provenance ---------- */

function ResourceCard({ resource }: { resource: any }) {
  if (!resource) {
    return (
      <p className="text-[11px] font-serif italic text-[#68635e] pt-1">
        No video or notes linked for this topic yet. PathMind keeps searching
        for verified material automatically — till then, use your class notes
        and the steps below.
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
  // Current level (plan phase / unit title) the vault is biased toward;
  // set when arriving from a path phase, cleared on manual subject change.
  const [pyqTopic, setPyqTopic] = useState<string>("");
  const [pyqLoading, setPyqLoading] = useState(false);
  // True once the learner picks a PYQ subject manually — until then the
  // vault follows the plan's current phase.
  const pyqSubjectTouched = useRef(false);
  // Identical in-flight vault query (the mount sequence can ask twice:
  // subject list first, then the plan-follow effect). One network search
  // per distinct query is enough.
  const pyqInFlight = useRef<string>("");
  const [activeAssessment, setActiveAssessment] = useState<any>(null);
  const [activePhaseId, setActivePhaseId] = useState<string | null>(null);
  const [assessmentResult, setAssessmentResult] = useState<any>(null);
  const [answers, setAnswers] = useState<Record<string, string>>({});
  const [submittingAssessment, setSubmittingAssessment] = useState(false);
  const [actionError, setActionError] = useState<string | null>(null);
  const [enrichingPhaseId, setEnrichingPhaseId] = useState<string | null>(null);
  // Activity ids with a Mark-Done request in flight (optimistic UI lock).
  const [completingIds, setCompletingIds] = useState<Set<string>>(new Set());
  // Phase currently being researched for verified resources on load.
  const [resourceHuntPhaseId, setResourceHuntPhaseId] = useState<string | null>(null);
  // Phases we already tried to research this session — one hunt per phase,
  // never a loop (the research result is cached server-side for everyone).
  const attemptedResourcePhases = useRef<Set<string>>(new Set());
  const [memories, setMemories] = useState<any>({ short_term: [], long_term: [], learning_signals: [] });

  // Mentor Chat State
  const [mentorQuery, setMentorQuery] = useState("");
  const [mentorMessages, setMentorMessages] = useState<any[]>([]);
  const [chatLoading, setChatLoading] = useState(false);

  // New Commitment State
  const [newCmtTitle, setNewCmtTitle] = useState("");
  const [newCmtMinutes, setNewCmtMinutes] = useState(45);

  // Data-loading UX: never show a stale "not set" screen while loading,
  // and never fail silently — a failed fetch gets an explicit retry banner.
  const [dataLoading, setDataLoading] = useState(true);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [toast, setToast] = useState<string | null>(null);
  const [loggingOut, setLoggingOut] = useState(false);

  useEffect(() => {
    if (user) {
      setUserName(user.email?.split("@")[0] || "Scholar");
      loadAllData();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [user]);

  // Refresh when a plan is generated elsewhere (e.g. onboarding Step 5):
  // the dashboard may already be mounted, so an event beats navigation.
  useEffect(() => {
    const onRefresh = () => loadAllData();
    window.addEventListener("pathmind:refresh", onRefresh);
    return () => window.removeEventListener("pathmind:refresh", onRefresh);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // One-shot success banner after a fresh plan generation (set by Step 5).
  useEffect(() => {
    try {
      if (sessionStorage.getItem("pathmind_plan_ready") === "1") {
        sessionStorage.removeItem("pathmind_plan_ready");
        setToast("Your study plan is ready — phases unlock as you demonstrate mastery.");
      }
    } catch {
      /* storage unavailable: skip banner */
    }
  }, []);

  // Auto-dismiss toasts.
  useEffect(() => {
    if (!toast) return;
    const t = setTimeout(() => setToast(null), 4000);
    return () => clearTimeout(t);
  }, [toast]);

  const loadAllData = async (retrying = false) => {
    setLoadError(null);
    setDataLoading(true);
    try {
      // 1. Learner profile (branch lives here as supported_path)
      const profRes = await apiClient.get<any>("/api/college/profile");
      const profileBranch = profRes.ok && profRes.data ? profRes.data.supported_path : "";
      if (profileBranch) setBranch(profileBranch);

      // 2. Academic Context — without it there is nothing honest to show
      const ctxRes = await apiClient.get<any>("/api/college/academic-context");
      if (!ctxRes.ok) {
        // An auth failure (401) means the session is gone — expired or
        // revoked. Redirect to /login via the router instead of showing an
        // error banner. Non-auth errors still get the banner below.
        if (ctxRes.status === 401) {
          router.push("/login");
          return;
        }
        // A transient failure (e.g. token refresh race on first load) gets
        // one retry; a hard failure gets an explicit banner, never a stale
        // "not set" screen.
        if (!retrying) {
          await new Promise((r) => setTimeout(r, 1200));
          return loadAllData(true);
        }
        setLoadError(ctxRes.error || "Could not load your academic context.");
        return;
      }
      if (!ctxRes.data) {
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
      if (!retrying) {
        await new Promise((r) => setTimeout(r, 1200));
        return loadAllData(true);
      }
      setLoadError(err instanceof Error ? err.message : "Failed to load dashboard data.");
    } finally {
      setDataLoading(false);
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
        // Skip the state write when nothing actually changed: a fresh
        // object identity on every fetch re-rendered the whole plan
        // tree and re-fired the auto-research effect, which is what
        // made the dashboard feel laggy after onboarding.
        setLearningPlan((prev: any) =>
          prev && JSON.stringify(prev) === JSON.stringify(planRes.data)
            ? prev
            : planRes.data
        );
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
    level: number = pyqLevel,
    topic: string = pyqTopic
  ) => {
    if (!universityId) return;
    // The mount sequence can issue the same query twice (subject list,
    // then the plan-follow effect) — one search per distinct query.
    const queryKey = `${universityId}|${subjectId}|${scope}|${level}|${topic}`;
    if (pyqInFlight.current === queryKey) return;
    pyqInFlight.current = queryKey;
    setPyqError(null);
    setPyqLoading(true);
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
      // University paper archives are filed by subject CODE (e.g. 7CS4-01);
      // without it the search only ever tries the subject name.
      if (subj?.code) params.set("subject_code", subj.code);
      // The learner's current level (plan phase / unit) biases retrieval
      // toward that unit's papers.
      if (topic) params.set("topic", topic);
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
    } finally {
      if (pyqInFlight.current === queryKey) pyqInFlight.current = "";
      setPyqLoading(false);
    }
  };

  const reloadPYQs = (scope: "subject" | "program", level: number) => {
    setPyqScope(scope);
    setPyqLevel(level);
    loadPYQs(academicContext?.university_id, pyqSubjectId, scope, level);
  };

  // Path → vault: a phase's "Solve Previous-Year Questions" step opens the
  // PYQ Vault scoped to that phase's subject and level (unit), starting at
  // the most recent papers.
  const openPyqForPhase = (phase: any) => {
    const sid = subjectIdFromPhaseId(phase.phase_id, learningPlan.plan_id);
    const unit = String(phase.title || "").replace(/^[^:]+:\s*/, "");
    pyqSubjectTouched.current = true;
    setPyqTopic(unit);
    if (sid) {
      setPyqSubjectId(sid);
      setPyqScope("subject");
      setPyqLevel(1);
      loadPYQs(academicContext?.university_id, sid, "subject", 1, unit);
    }
    setActiveTab("pyq");
  };

  // Until the learner picks a PYQ subject manually, the vault follows the
  // plan: it opens on the current phase's subject and level rather than
  // the first subject in the curriculum list.
  useEffect(() => {
    if (pyqSubjectTouched.current) return;
    if (!learningPlan?.phases?.length || pyqSubjects.length === 0) return;
    const current =
      learningPlan.phases.find(
        (p: any) => p.status === "IN_PROGRESS" || p.status === "AVAILABLE"
      ) || learningPlan.phases[0];
    const sid = subjectIdFromPhaseId(current.phase_id, learningPlan.plan_id);
    if (!sid || sid === pyqSubjectId) return;
    const unit = String(current.title || "").replace(/^[^:]+:\s*/, "");
    setPyqSubjectId(sid);
    setPyqTopic(unit);
    loadPYQs(academicContext?.university_id, sid, "subject", 1, unit);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [learningPlan, pyqSubjects]);

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
    if (completingIds.has(activityId)) return;
    // Optimistic flip: the old flow re-saved the whole plan server-side and
    // then refetched everything, which made every click feel stuck. Flip
    // locally at once; the server now persists just the touched phase and
    // returns the authoritative plan.
    setCompletingIds((prev) => new Set(prev).add(activityId));
    setLearningPlan((prev: any) => {
      if (!prev?.phases) return prev;
      return {
        ...prev,
        phases: prev.phases.map((p: any) => ({
          ...p,
          activities: (p.activities || []).map((a: any) =>
            a.activity_id === activityId
              ? { ...a, status: "COMPLETED", completed_at: new Date().toISOString() }
              : a
          ),
        })),
      };
    });
    try {
      const res = await apiClient.post<any>(`/api/college/activities/${activityId}/complete`, {
        evidence: { self_reported_focus: 5 },
      });
      if (res.ok) {
        setLearningPlan(res.data);
        setToast("Activity marked complete. Demonstrate mastery in the checkpoint to unlock the next phase.");
      } else {
        setActionError(res.error || "Could not mark the activity complete.");
        loadCurrentPlan(); // reconcile with server truth after a failed save
      }
    } catch (err) {
      setActionError(err instanceof Error ? err.message : "Could not mark the activity complete.");
      loadCurrentPlan();
    } finally {
      setCompletingIds((prev) => {
        const next = new Set(prev);
        next.delete(activityId);
        return next;
      });
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

  // On-demand AI enrichment for tail phases of large plans: large
  // (whole-program) plans ship tail phases with the deterministic static
  // activity sequence so generation fits the serverless window. This
  // upgrades one phase to AI-personalized activities in a single call.
  const handleEnrichPhase = async (phase: any) => {
    setActionError(null);
    if (!learningPlan?.plan_id || !phase?.phase_id) {
      setActionError("Cannot personalize: plan or phase id is missing.");
      return;
    }
    setEnrichingPhaseId(phase.phase_id);
    try {
      const res = await apiClient.post<any>(
        `/api/college/plans/${learningPlan.plan_id}/phases/${phase.phase_id}/activities/enrich`,
        {}
      );
      if (res.ok) {
        setToast("Phase personalized with AI — activities updated.");
        loadAllData();
      } else {
        setActionError(res.error || "Could not personalize this phase right now.");
      }
    } catch (err) {
      setActionError(err instanceof Error ? err.message : "Could not personalize this phase right now.");
    } finally {
      setEnrichingPhaseId(null);
    }
  };

  // Restore this session's already-attempted hunts before the cascade
  // below runs, so a remount never restarts it from phase 1.
  useEffect(() => {
    readAttemptedHunts().forEach((id) =>
      attemptedResourcePhases.current.add(id)
    );
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Resource research on load: every phase that is missing a learning link —
  // a WATCH/READ activity with no verified resource, or no WATCH/READ slot
  // at all — gets researched one phase at a time, in plan order, LOCKED
  // phases included, so the whole path shows a link for every topic rather
  // than only the phase the learner is on. Results are cached server-side
  // as VERIFIED rows shared by every learner, so this is a once-per-topic
  // cost; the plan reload then links them via attach-on-read. Bounded per
  // session so one long plan cannot burn the shared search quotas in a
  // single sitting — the next visit picks up where this one stopped.
  useEffect(() => {
    if (!learningPlan?.phases || resourceHuntPhaseId) return;
    if (attemptedResourcePhases.current.size >= 8) return;
    const phase = learningPlan.phases.find((p: any) => {
      if (p.status === "COMPLETED") return false;
      if (attemptedResourcePhases.current.has(p.phase_id)) return false;
      const slots = (p.activities || []).filter(
        (a: any) => a.activity_type === "WATCH" || a.activity_type === "READ"
      );
      const hasWatch = slots.some((a: any) => a.activity_type === "WATCH");
      const hasRead = slots.some((a: any) => a.activity_type === "READ");
      return !hasWatch || !hasRead || slots.some((a: any) => !a.resource);
    });
    if (!phase) return;
    // Mark attempted before any early return below so one unparseable or
    // unfillable phase can never stall the cascade for the phases after it.
    attemptedResourcePhases.current.add(phase.phase_id);
    persistAttemptedHunts(attemptedResourcePhases.current);
    const subjectId = subjectIdFromPhaseId(phase.phase_id, learningPlan.plan_id);
    if (!subjectId) return;
    setResourceHuntPhaseId(phase.phase_id);
    const subj = pyqSubjects.find((s: any) => s.subject_id === subjectId);
    const topic = String(phase.title || "").replace(/^[^:]+:\s*/, "");
    (async () => {
      try {
        const res = await apiClient.post<any>("/api/college/resources/enrich", {
          subject_id: subjectId,
          topic,
          subject_name: subj?.name,
          time_budget_seconds: 30,
        });
        // Refetch the plan ONLY when the hunt actually added material.
        // Refetching after every hunt (even empty ones) re-rendered the
        // whole plan tree up to 8 times back-to-back — the post-diagnose
        // lag. An empty hunt changes nothing the plan read would show.
        if (res.ok && ((res.data as any)?.resources_added ?? 0) > 0) {
          loadCurrentPlan();
        }
      } catch {
        /* Research failure stays silent here: activities keep their
           how-to-learn steps and the Personalize button can retry. */
      } finally {
        setResourceHuntPhaseId(null);
      }
    })();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [learningPlan, pyqSubjects]);

  const handleSubmitAssessment = async () => {
    if (!activeAssessment || submittingAssessment) return;
    setActionError(null);
    // Lock the button while a submission is in flight: a burst of duplicate
    // submits writes duplicate learning signals for a single attempt.
    setSubmittingAssessment(true);
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
    } finally {
      setSubmittingAssessment(false);
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
        const text = (data.message || "").trim();
        setMentorMessages([
          ...newMsgList,
          text
            ? {
                role: "agent",
                text,
                state: data.state,
                ui_blocks: data.ui_blocks,
                sources: data.sources,
              }
            : {
                // Never render an empty bubble: say so honestly instead.
                role: "agent",
                text: "The mentor returned an empty reply — nothing was fabricated in its place. Please try asking again.",
                state: "ERROR",
                ui_blocks: [],
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
    setLoggingOut(true);
    try {
      await signOut();
    } finally {
      setLoggingOut(false);
    }
  };

  const branchLabel =
    branch?.replace(/_/g, " ").replace("ENGINEER", "Engineering") || "Engineering";
  const universityDisplay = dataLoading
    ? "Loading your academic station…"
    : (universityName || academicContext?.university_id || "University not set");
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

  /* ----- exam-lens derived data (Direction B path view) ----- */
  const planPhases = [...(learningPlan?.phases || [])].sort(
    (a: any, b: any) => (a.order ?? 0) - (b.order ?? 0)
  );
  const currentPhase = planPhases.find(
    (p: any) => p.status === "AVAILABLE" || p.status === "IN_PROGRESS"
  );
  const totalActsAll = planPhases.reduce(
    (n: number, p: any) => n + (p.activities?.length || 0),
    0
  );
  const doneActsAll = planPhases.reduce(
    (n: number, p: any) =>
      n + (p.activities || []).filter((a: any) => a.status === "COMPLETED").length,
    0
  );
  const overallPct = totalActsAll
    ? Math.round((doneActsAll / totalActsAll) * 100)
    : 0;
  const phasesLeft = planPhases.filter((p: any) => p.status !== "COMPLETED").length;
  const subjectNameOf = (sid: string | null): string => {
    if (!sid) return "General";
    const s = (pyqSubjects || []).find((x: any) => x.subject_id === sid);
    return s ? `${s.code} · ${s.name}` : sid;
  };
  const subjectGroups: { sid: string | null; phases: any[] }[] = [];
  for (const p of planPhases) {
    const sid = learningPlan
      ? subjectIdFromPhaseId(p.phase_id, learningPlan.plan_id)
      : null;
    let g = subjectGroups.find((x) => x.sid === sid);
    if (!g) {
      g = { sid, phases: [] };
      subjectGroups.push(g);
    }
    g.phases.push(p);
  }
  const groupStats = (g: { phases: any[] }) => {
    let total = 0,
      done = 0,
      pyqMarks = 0;
    for (const p of g.phases) {
      const s = phaseStats(p);
      total += s.total;
      done += s.done;
      pyqMarks += s.pyqMarks;
    }
    return { total, done, pyqMarks, pct: total ? Math.round((done / total) * 100) : 0 };
  };
  const focusPhase = currentPhase;
  const focusAct = focusPhase
    ? (focusPhase.activities || []).find((a: any) => a.status !== "COMPLETED")
    : null;
  const heaviestPhase = planPhases.reduce((best: any, p: any) => {
    const m = phaseStats(p).pyqMarks;
    return m > (best ? phaseStats(best).pyqMarks : -1) ? p : best;
  }, null);
  const heaviestMarks = heaviestPhase ? phaseStats(heaviestPhase).pyqMarks : 0;
  const weakestGroup =
    subjectGroups
      .filter((g) => groupStats(g).pct < 100)
      .sort((a, b) => groupStats(a).pct - groupStats(b).pct)[0] || null;

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
            disabled={loggingOut}
            className="text-xs px-3 py-1.5 border border-[#a65959]/40 hover:border-[#a65959] text-[#a65959] rounded-md font-medium cursor-pointer disabled:opacity-60"
          >
            {loggingOut ? "Exiting…" : "Exit Journal"}
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

        {loadError && (
          <div className="p-4 rounded-md border-[1.5px] border-[#a65959] bg-[#ffdad6]/30 text-xs text-[#93000a] flex items-center justify-between gap-3">
            <span>
              <span className="font-bold">Couldn&apos;t load your data: </span>
              {loadError}
            </span>
            <button
              onClick={() => loadAllData()}
              className="shrink-0 px-4 py-1.5 bg-[#a65959] text-white font-bold rounded-md cursor-pointer"
            >
              Retry
            </button>
          </div>
        )}

        {toast && (
          <div className="fixed bottom-6 left-1/2 -translate-x-1/2 z-50 px-5 py-3 bg-[#252321] text-[#fdfae7] text-sm font-semibold rounded-md shadow-[3px_4px_0px_rgba(37,35,33,0.4)] max-w-[90vw] text-center">
            {toast}
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

                {/* TAB 1: ORDERED STUDY PLAN — exam-lens path (Direction B).
            This view is what the learner sees AFTER "Generate Path":
            units as exam cards (marks weight, resource lanes, checkpoint
            gates), a verdict + today's-focus rail on desktop. The
            pre-generation empty state below is intentionally unchanged. */}
        {activeTab === "plan" && (
          <section className="space-y-6">
            {/* Exam board */}
            <div className="relative overflow-hidden rounded-lg bg-[#252321] text-[#fdfae7] border-[1.75px] border-[#252321] shadow-[3px_4px_0px_rgba(37,35,33,0.9)] p-6">
              <div
                className="absolute inset-0 opacity-[0.13] pointer-events-none"
                style={{
                  backgroundImage:
                    "repeating-linear-gradient(-45deg, transparent 0 10px, #fdfae7 10px 11px)",
                }}
              />
              <div className="relative">
                <div className="text-2xl sm:text-[32px] leading-tight font-bold">
                  {examDays !== null && examDays !== undefined ? (
                    <>
                      <span className="text-[#ffb3ab]">{examDays} days</span> to the end-term
                    </>
                  ) : (
                    "Your path, exam-first"
                  )}
                </div>
                <p className="font-serif italic text-[13.5px] text-[#fdfae7]/75 mt-1.5">
                  {universityDisplay}
                  {academicContext?.semester ? ` · Semester ${academicContext.semester}` : ""}
                  {` · ${planPhases.length} units across ${subjectGroups.length || 1} subject${subjectGroups.length === 1 ? "" : "s"}`}
                  {learningPlan?.scope
                    ? ` · paced for ${(learningPlan.scope || "").replace(/_/g, " ").toLowerCase()}`
                    : ""}
                </p>
                <div className="flex flex-wrap gap-2 mt-3.5">
                  {currentPhase ? (
                    <span className="text-[10.5px] font-sans font-bold tracking-[0.12em] uppercase border-[1.5px] border-[#a65959] bg-[#a65959] text-[#fdfae7] rounded-full px-3 py-[5px]">
                      Unit {unitNumberOf(currentPhase)} in progress
                    </span>
                  ) : planPhases.length > 0 ? (
                    <span className="text-[10.5px] font-sans font-bold tracking-[0.12em] uppercase border-[1.5px] border-[#fdfae7] text-[#fdfae7] rounded-full px-3 py-[5px]">
                      All units cleared
                    </span>
                  ) : null}
                  <span className="text-[10.5px] font-sans font-bold tracking-[0.12em] uppercase border-[1.5px] border-[#fdfae7] text-[#fdfae7] rounded-full px-3 py-[5px]">
                    {overallPct}% of path done
                  </span>
                  {currentPhase?.unlock_rule?.required_assessment_score !== undefined &&
                  currentPhase?.unlock_rule?.required_assessment_score !== null ? (
                    <span className="text-[10.5px] font-sans font-bold tracking-[0.12em] uppercase border-[1.5px] border-[#fdfae7] text-[#fdfae7] rounded-full px-3 py-[5px]">
                      Checkpoint pass mark {currentPhase.unlock_rule.required_assessment_score}%
                    </span>
                  ) : null}
                </div>
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
              <div className="grid gap-6 lg:grid-cols-[minmax(0,1fr)_320px] items-start">
                {/* Main column: subjects → unit cards → checkpoint gates */}
                <div className="space-y-8 min-w-0">
                  {subjectGroups.map((g) => {
                    const gs = groupStats(g);
                    return (
                      <div key={g.sid || "general"} className="space-y-4">
                        {subjectGroups.length > 1 && (
                          <div className="flex flex-wrap items-baseline justify-between gap-2">
                            <h4 className="font-bold text-lg text-[#252321]">
                              {subjectNameOf(g.sid)}
                            </h4>
                            <span className="text-[11px] font-sans font-bold tracking-[0.14em] uppercase text-[#68635e]">
                              {g.phases.length} units · {gs.pct}% done
                            </span>
                          </div>
                        )}
                        {g.phases.map((phase: any) => {
                          const isLocked = phase.status === "LOCKED";
                          const isDone = phase.status === "COMPLETED";
                          const isCurrent =
                            currentPhase && phase.phase_id === currentPhase.phase_id;
                          const req = phase.unlock_rule?.required_assessment_score;
                          const stats = phaseStats(phase);
                          const barA = isDone ? "#4a654e" : "#a65959";
                          const barB = isDone ? "#5d7a60" : "#b76e6e";
                          return (
                            <div key={phase.phase_id} className="space-y-3">
                              <div
                                id={`phase-${phase.phase_id}`}
                                className={`p-5 sm:p-6 rounded-lg bg-[#fdfae7] transition-all relative scroll-mt-6 ${
                                  isLocked
                                    ? "opacity-75 border-[1.5px] border-dashed border-[#252321]/40"
                                    : isCurrent
                                      ? "border-[1.75px] border-[#a65959] shadow-[3px_4px_0px_#a65959]"
                                      : "border-[1.75px] border-[#252321] shadow-[3px_4px_0px_#252321]"
                                }`}
                              >
                                <div className="flex gap-4">
                                  {/* Unit seal */}
                                  <div
                                    className={`w-[54px] h-[54px] sm:w-[60px] sm:h-[60px] shrink-0 rounded-full border-2 flex items-center justify-center font-sans font-extrabold text-[20px] ${
                                      isDone
                                        ? "bg-[#4a654e] text-[#fdfae7] border-[#3b523e]"
                                        : isCurrent
                                          ? "bg-[#a65959] text-[#fdfae7] border-[#7c3f3f]"
                                          : isLocked
                                            ? "bg-[#ede8d5] text-[#68635e] border-dashed border-[#252321]/40"
                                            : "bg-[#fdfae7] text-[#252321] border-[#252321]"
                                    }`}
                                    style={{
                                      boxShadow: isDone
                                        ? "inset 0 0 0 3px #4a654e, inset 0 0 0 5px #fdfae7"
                                        : isCurrent
                                          ? "inset 0 0 0 3px #a65959, inset 0 0 0 5px #fdfae7"
                                          : "inset 0 0 0 3px #fdfae7, inset 0 0 0 5px rgba(37,35,33,0.55)",
                                    }}
                                  >
                                    {isDone ? (
                                      "✓"
                                    ) : isLocked ? (
                                      <span className="material-symbols-outlined text-[22px]">
                                        lock
                                      </span>
                                    ) : (
                                      unitNumberOf(phase)
                                    )}
                                  </div>

                                  <div className="flex-1 min-w-0">
                                    <div className="flex flex-wrap items-start justify-between gap-2">
                                      <div className="min-w-0">
                                        <div className="flex items-center gap-2.5 flex-wrap">
                                          <h3 className="font-bold text-lg text-[#252321]">
                                            {phase.title}
                                          </h3>
                                          {stats.highYield && (
                                            <span className="inline-block font-sans font-extrabold text-[10px] tracking-[0.16em] uppercase text-[#a65959] border-[2.5px] border-double border-[#a65959] rounded-md px-2 py-[3px] -rotate-[5deg] bg-[#a65959]/5">
                                              High-yield
                                            </span>
                                          )}
                                        </div>
                                        <p className="text-xs text-[#68635e] mt-0.5 font-serif italic">
                                          {phase.objective}
                                        </p>
                                        {resourceHuntPhaseId === phase.phase_id && (
                                          <p className="text-[11px] text-[#4a654e] mt-1.5 flex items-center gap-1">
                                            <span className="material-symbols-outlined text-sm animate-pulse">
                                              travel_explore
                                            </span>
                                            Finding verified videos &amp; notes for this phase…
                                          </p>
                                        )}
                                        {isLocked && (
                                          <p className="text-[11px] text-[#68635e] mt-1.5 flex items-center gap-1">
                                            <span className="material-symbols-outlined text-sm">
                                              lock
                                            </span>
                                            Locked — complete the previous phase&apos;s checkpoint
                                            {req !== undefined && req !== null
                                              ? ` with at least ${req}%`
                                              : " and demonstrate mastery"}
                                            . Unlocking is decided server-side from your assessment
                                            results.
                                          </p>
                                        )}
                                      </div>

                                      <div className="flex items-center gap-2 shrink-0">
                                        <span
                                          className={`text-xs px-2.5 py-1 rounded font-bold ${statusBadge(phase.status)}`}
                                        >
                                          {phase.status}
                                        </span>
                                        {!phase.ai_enriched && (
                                          <button
                                            onClick={() => handleEnrichPhase(phase)}
                                            disabled={enrichingPhaseId === phase.phase_id}
                                            className="px-3 py-1.5 bg-[#252321] text-[#fdfae7] text-xs font-bold rounded hover:opacity-85 cursor-pointer disabled:opacity-60"
                                            title="Upgrade this phase's activities to an AI-personalized sequence"
                                          >
                                            {enrichingPhaseId === phase.phase_id
                                              ? "Personalizing…"
                                              : "✨ Personalize with AI"}
                                          </button>
                                        )}
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

                                    {/* Progress — hatched bar, real completion */}
                                    <div className="mt-4 h-[11px] rounded-full border-[1.5px] border-[#252321] bg-[#ede8d5] overflow-hidden">
                                      <div
                                        className="h-full rounded-full"
                                        style={{
                                          width: `${stats.pct}%`,
                                          backgroundImage: `repeating-linear-gradient(-55deg, ${barA} 0 6px, ${barB} 6px 12px)`,
                                        }}
                                      />
                                    </div>
                                    <div className="flex flex-wrap justify-between gap-2 mt-1.5">
                                      <span className="text-[11px] font-sans font-bold tracking-[0.08em] uppercase text-[#68635e]">
                                        {stats.pyqMarks > 0
                                          ? `${stats.pyqMarks} PYQ marks linked`
                                          : `${stats.total} activities`}
                                      </span>
                                      <span
                                        className={`text-[11px] font-sans font-bold tracking-[0.08em] uppercase ${isCurrent ? "text-[#a65959]" : "text-[#68635e]"}`}
                                      >
                                        {stats.pct}% done · {stats.done}/{stats.total}
                                      </span>
                                    </div>

                                    {/* Resource lanes — from persisted quality_signals */}
                                    {stats.lanes.length > 0 && (
                                      <div className="flex flex-wrap items-center gap-2 mt-3">
                                        {stats.lanes.map((lane: string) => {
                                          const cfg = LANE_STYLE[lane] || {
                                            label: lane.replace(/_/g, " "),
                                            cls: "bg-[#ede8d5] text-[#252321] border-[#252321]",
                                          };
                                          let label = cfg.label;
                                          if (lane === "ONE_SHOT" && stats.hindi)
                                            label += " · Hindi";
                                          if (lane === "PYQ" && stats.pyqMarks > 0)
                                            label += ` · ${stats.pyqMarks} marks`;
                                          return (
                                            <span
                                              key={lane}
                                              className={`inline-block font-sans text-[9.5px] font-extrabold tracking-[0.14em] uppercase px-2 py-[3px] rounded border-[1.5px] ${cfg.cls}`}
                                            >
                                              {label}
                                            </span>
                                          );
                                        })}
                                      </div>
                                    )}
                                  </div>
                                </div>

                                <div className="mt-5">
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
                                  ? "bg-[#4a654e]/5 border-[#4a654e]/40"
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

                                {/* How to learn this — the method, not just the material */}
                                {Array.isArray(act.learn_steps) && act.learn_steps.length > 0 && (
                                  <div className="pt-1.5">
                                    <p className="text-[10px] font-bold uppercase tracking-wider text-[#68635e] mb-1">
                                      How to learn this
                                    </p>
                                    <ol className="list-decimal list-inside space-y-0.5">
                                      {act.learn_steps.map((s: string, i: number) => (
                                        <li key={i} className="text-[11px] text-[#423e3b] leading-relaxed">
                                          {s}
                                        </li>
                                      ))}
                                    </ol>
                                  </div>
                                )}

                                {/* PYQ Reference */}
                                {act.pyq_question && (
                                  <div className="text-xs text-[#a65959] font-medium pt-1">
                                    <span>
                                      University question reference: {act.pyq_question.marks} marks
                                    </span>
                                  </div>
                                )}
                              </div>

                              <div className="flex flex-col items-end gap-2">
                                {act.activity_type === "SOLVE_PYQ" && !isLocked && (
                                  <button
                                    onClick={() => openPyqForPhase(phase)}
                                    className="px-3 py-1.5 rounded text-xs font-bold bg-[#a65959] text-white hover:opacity-90 cursor-pointer whitespace-nowrap"
                                  >
                                    Open PYQ Vault for this level →
                                  </button>
                                )}
                                {!isLocked && !isDone && (
                                  <button
                                    onClick={() => handleCompleteActivity(act.activity_id)}
                                    disabled={completingIds.has(act.activity_id)}
                                    className={`px-3 py-1.5 rounded text-xs font-bold transition-all cursor-pointer disabled:opacity-60 ${
                                      actDone
                                        ? "bg-[#4a654e] text-white"
                                        : "bg-white border border-[#252321] hover:bg-[#252321] hover:text-white"
                                    }`}
                                  >
                                    {completingIds.has(act.activity_id)
                                      ? "Saving…"
                                      : actDone
                                        ? "✓ Completed"
                                        : "Mark Done"}
                                  </button>
                                )}
                              </div>
                            </div>
                          );
                        })
                      )}
                    </div>
                                </div>
                              </div>

                              {/* Checkpoint gate */}
                              <div className="flex items-center gap-3 px-4 py-3 rounded-lg border-[1.5px] border-dashed border-[#252321]/50 bg-[#ede8d5]/50">
                                <span className="material-symbols-outlined text-[19px] text-[#252321]">
                                  flag
                                </span>
                                <p className="text-[13px] font-serif italic text-[#423e3b]">
                                  {isDone ? (
                                    <>
                                      <b className="not-italic font-sans text-[13px]">
                                        Checkpoint cleared:
                                      </b>{" "}
                                      {phase.title} is signed off — the next unit is open.
                                    </>
                                  ) : isLocked ? (
                                    <>
                                      <b className="not-italic font-sans text-[13px]">
                                        Checkpoint gate:
                                      </b>{" "}
                                      opens once the previous unit&apos;s checkpoint is passed.
                                    </>
                                  ) : (
                                    <>
                                      <b className="not-italic font-sans text-[13px]">
                                        Checkpoint:
                                      </b>{" "}
                                      pass {phase.title}&apos;s exam-readiness
                                      {req !== undefined && req !== null ? (
                                        <>
                                          {" "}
                                          with at least{" "}
                                          <b className="not-italic font-sans">{req}%</b>
                                        </>
                                      ) : (
                                        ""
                                      )}{" "}
                                      to unlock the next unit.
                                    </>
                                  )}
                                </p>
                              </div>
                            </div>
                          );
                        })}
                      </div>
                    );
                  })}
                </div>

                {/* Right rail: verdict · today's focus · breakdown */}
                <aside className="space-y-5">
                  <div className="relative p-[18px] rounded-lg bg-[#fffdf4] border-[1.5px] border-[#252321] shadow-[3px_4px_0px_#252321]">
                    <span className="absolute right-3.5 -top-3 -rotate-[4deg] font-note-handwritten text-[17px] text-[#a65959] bg-[#fffdf4] px-1">
                      PathMind&apos;s read of your paper →
                    </span>
                    <div className="space-y-2.5 text-[14.5px] leading-relaxed text-[#252321] pt-1">
                      <p>
                        <b>
                          {doneActsAll} of {totalActsAll} activities
                        </b>{" "}
                        done. <b>{phasesLeft} unit{phasesLeft === 1 ? "" : "s"}</b> still to
                        clear
                        {examDays !== null && examDays !== undefined ? (
                          <>
                            {" "}
                            with <b>{examDays} days</b> to the paper
                          </>
                        ) : (
                          ""
                        )}
                        .
                      </p>
                      {heaviestPhase && heaviestMarks > 0 && heaviestPhase.status !== "COMPLETED" && (
                        <p>
                          <b>{heaviestPhase.title}</b> carries{" "}
                          <b className="text-[#3b523e]">{heaviestMarks} PYQ marks</b> in your
                          plan — the heaviest unit here. Clear it early.
                        </p>
                      )}
                      {weakestGroup && subjectGroups.length > 1 && (
                        <p>
                          <b>{subjectNameOf(weakestGroup.sid)}</b> is your least-covered subject
                          so far ({groupStats(weakestGroup).pct}% done) — don&apos;t let it slide.
                        </p>
                      )}
                    </div>
                  </div>

                  {focusPhase && focusAct && (
                    <div className="p-[18px] rounded-lg bg-[#fffdf4] border-[1.5px] border-[#252321] shadow-[3px_4px_0px_#252321]">
                      <span className="text-[10px] font-sans font-bold tracking-[0.2em] uppercase text-[#68635e]">
                        Today&apos;s focus
                        {focusAct.estimated_minutes
                          ? ` · ~${focusAct.estimated_minutes} min`
                          : ""}
                      </span>
                      <h4 className="font-bold text-[17px] leading-snug mt-2">{focusAct.title}</h4>
                      <p className="text-xs font-serif italic text-[#68635e] mt-0.5">
                        {focusPhase.title}
                      </p>
                      <div className="h-3 rounded-full border-[1.5px] border-[#252321] bg-[#ede8d5] overflow-hidden my-3.5">
                        <div
                          className="h-full bg-[#4a654e]"
                          style={{ width: `${phaseStats(focusPhase).pct}%` }}
                        />
                      </div>
                      <button
                        onClick={() =>
                          document
                            .getElementById(`phase-${focusPhase.phase_id}`)
                            ?.scrollIntoView({ behavior: "smooth", block: "start" })
                        }
                        className="w-full px-4 py-2.5 bg-[#4a654e] text-[#fdfae7] text-sm font-sans font-bold rounded-[10px] border-[1.5px] border-[#3b523e] shadow-[3px_3px_0px_#3b523e] cursor-pointer hover:opacity-90"
                      >
                        Continue this unit →
                      </button>
                      <span className="block font-note-handwritten text-[16.5px] text-[#3b523e] mt-3">
                        one unit a day keeps the backlog away
                      </span>
                    </div>
                  )}

                  <div className="p-[18px] rounded-lg bg-[#fdfae7] border-[1.5px] border-[#252321] shadow-[3px_4px_0px_#252321]">
                    <span className="text-[10px] font-sans font-bold tracking-[0.2em] uppercase text-[#68635e]">
                      Plan breakdown
                    </span>
                    <h5 className="font-bold text-[15px] mt-1 mb-3">
                      Where your effort (and PYQ marks) sit
                    </h5>
                    <div className="space-y-3.5">
                      {subjectGroups.map((g) => {
                        const gs = groupStats(g);
                        return (
                          <div key={g.sid || "general"}>
                            <div className="flex justify-between gap-2 text-[12.5px] mb-1">
                              <b className="truncate">{subjectNameOf(g.sid)}</b>
                              <span className="text-[10.5px] font-sans font-bold tracking-[0.08em] uppercase text-[#68635e] shrink-0">
                                {gs.pct}%{gs.pyqMarks > 0 ? ` · ${gs.pyqMarks} PYQ marks` : ""}
                              </span>
                            </div>
                            <div className="h-[11px] rounded-full border-[1.5px] border-[#252321] bg-[#ede8d5] overflow-hidden">
                              <div
                                className="h-full rounded-full"
                                style={{
                                  width: `${gs.pct}%`,
                                  backgroundImage:
                                    "repeating-linear-gradient(-55deg, #4a654e 0 6px, #5d7a60 6px 12px)",
                                }}
                              />
                            </div>
                          </div>
                        );
                      })}
                    </div>
                  </div>
                </aside>
              </div>
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
                  Real papers from the university's official archive and
                  public exam archives — never invented.
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
                      pyqSubjectTouched.current = true;
                      setPyqTopic("");
                      setPyqSubjectId(e.target.value);
                      loadPYQs(academicContext?.university_id, e.target.value, pyqScope, pyqLevel, "");
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
              {/* Level window: recent papers first, older ones unlock —
                  applies to both scopes, never the whole archive at once */}
              <div className="flex items-center gap-1.5 text-xs">
                <span className="font-bold text-[#68635e]">Level:</span>
                {[1, 2, 3].map((l) => (
                  <button
                    key={l}
                    onClick={() => reloadPYQs(pyqScope, l)}
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
              {pyqScope === "subject" && pyqTopic
                ? ` • Your current level: ${pyqTopic}`
                : ""}
            </p>

            {pyqError && (
              <div className="p-4 border border-dashed border-[#a65959] rounded-md bg-[#ffdad6]/20 text-xs text-[#93000a]">
                {pyqError}
              </div>
            )}

            {/* PYQ Results */}
            {pyqLoading && (!pyqData || pyqData.status === "PYQ_NOT_AVAILABLE") ? (
              <div className="p-8 border border-dashed border-[#252321]/30 rounded-md bg-white/50 text-center">
                <span className="material-symbols-outlined text-3xl text-[#68635e] mb-2 animate-pulse">
                  hourglass_top
                </span>
                <h4 className="font-bold text-sm text-[#252321]">Searching the archives…</h4>
                <p className="text-xs text-[#68635e] mt-1 max-w-md mx-auto">
                  Looking for real papers on the university's official site and
                  public exam archives. This can take up to half a minute.
                </p>
              </div>
            ) : !pyqData || pyqData.status === "PYQ_NOT_AVAILABLE" ? (
              <div className="p-8 border border-dashed border-[#a65959] rounded-md bg-[#ffdad6]/20 text-center">
                <span className="material-symbols-outlined text-3xl text-[#a65959] mb-2">
                  info
                </span>
                <h4 className="font-bold text-sm text-[#93000a]">PYQ_NOT_AVAILABLE</h4>
                <p className="text-xs text-[#68635e] mt-1 max-w-md mx-auto">
                  {pyqData?.message ||
                    "Verified previous year examination questions are currently unavailable for this subject from official repositories. No synthetic questions are substituted."}
                </p>
                {pyqData?.has_more_levels && (
                  <button
                    onClick={() => reloadPYQs(pyqScope, pyqLevel + 1)}
                    className="mt-3 px-3 py-1.5 rounded border border-[#252321] bg-[#252321] text-[#fdfae7] text-xs font-bold hover:opacity-90"
                  >
                    Unlock Level {pyqLevel + 1} — older papers →
                  </button>
                )}
              </div>
            ) : pyqData.papers ? (
              <div className="space-y-4">
                <div className="flex flex-wrap items-center justify-between gap-2 text-xs text-[#68635e]">
                  <span>
                    {pyqData.level_label} • {pyqData.total_found} paper{pyqData.total_found === 1 ? "" : "s"} found
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
                            {p.source_kind === "archive"
                              ? " public exam archive — a mirror, not the university's own site; cross-check with the official paper"
                              : p.retrieval === "realtime"
                                ? " found live on the official site"
                                : " curated archive"}
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
                    onClick={() => reloadPYQs(pyqScope, pyqLevel + 1)}
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
                      ? "Exam Readiness Check"
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
                          {(answers[q.question_id] || "").trim() !== "" && (
                            <span className="ml-2 text-[#4a654e]">✓ Answered</span>
                          )}
                        </span>
                      </div>

                      {q.question_type === "MCQ" && q.options && (
                        <div className="space-y-2 pt-1">
                          {q.options.map((opt: string) => (
                            <button
                              type="button"
                              key={opt}
                              aria-pressed={answers[q.question_id] === opt}
                              onClick={() =>
                                setAnswers((prev) => ({ ...prev, [q.question_id]: opt }))
                              }
                              className={`p-3 rounded-md border flex w-full items-start gap-2.5 text-left text-xs cursor-pointer transition-all ${
                                answers[q.question_id] === opt
                                  ? "border-[#4a654e] bg-[#4a654e]/10 font-bold"
                                  : "border-[#252321]/20 hover:border-[#252321] bg-white/60"
                              }`}
                            >
                              <span
                                aria-hidden="true"
                                className={`shrink-0 leading-none ${
                                  answers[q.question_id] === opt
                                    ? "text-[#4a654e]"
                                    : "text-[#68635e]"
                                }`}
                              >
                                {answers[q.question_id] === opt ? "●" : "○"}
                              </span>
                              <span>{opt}</span>
                            </button>
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
                <div className="flex items-center justify-between gap-3">
                  <span className="text-xs font-bold text-[#68635e]">
                    Answered{" "}
                    {
                      (activeAssessment.questions || []).filter(
                        (q: any) => (answers[q.question_id] || "").trim() !== ""
                      ).length
                    }{" "}
                    of {(activeAssessment.questions || []).length}
                  </span>
                  <button
                    onClick={handleSubmitAssessment}
                    disabled={submittingAssessment}
                    className="px-6 py-3 bg-[#4a654e] text-white font-bold text-sm rounded-md border-2 border-[#252321] shadow-[2px_3px_0px_#252321] cursor-pointer disabled:cursor-wait disabled:opacity-60"
                  >
                    {submittingAssessment ? "Evaluating…" : "Submit for Evaluation"}
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
