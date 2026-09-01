"use client";

import { useState } from "react";
import { motion } from "framer-motion";
import Link from "next/link";

interface FactItem {
  category: "OBSERVED" | "ASSESSED" | "INFERRED" | "UNKNOWN" | "RECOMMENDATION" | string;
  claim: string;
  evidence?: string[];
  confidence?: string;
  source?: string;
}

interface ContradictionItem {
  reported_preference: string;
  observed_evidence: string;
  suggested_clarification: string;
}

interface CandidateDirectionDetail {
  title: string;
  rationale: string;
  alignment: string;
  related_occupations?: string[];
  confidence?: string;
}

interface ChatMessage {
  role: "user" | "counselor";
  content: string;
  timestamp: string;
}

interface CounselingDashboardProps {
  profile: Record<string, unknown> | null; 
}

export function CounselingDashboard({ profile }: CounselingDashboardProps) {
  const [chatOpen, setChatOpen] = useState(false);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [inputMsg, setInputMsg] = useState("");
  const [isSending, setIsSending] = useState(false);

  if (!profile) return null;

  const isPreliminary = profile.is_preliminary !== false;
  const overallConfidence = String(profile.overall_confidence || "MEDIUM");
  const evidenceGaps = (profile.evidence_gaps as string[]) || [];
  const nextQuestions = (profile.next_questions as string[]) || [];
  const strengths = (profile.strengths as FactItem[]) || [];
  const capabilitySignals = (profile.capability_signals as FactItem[]) || [];
  const learningSignals = (profile.learning_signals as FactItem[]) || [];
  const candidateDirections = (profile.candidate_directions as string[]) || [];
  const candidateDetails = (profile.candidate_direction_details as CandidateDirectionDetail[]) || [];
  const contradictions = (profile.contradictions as ContradictionItem[]) || [];
  const unknowns = (profile.unknowns as string[]) || [];
  const interestVector = (profile.interest_vector as Record<string, number>) || {};

  const handleSendMessage = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!inputMsg.trim() || isSending) return;

    const userText = inputMsg.trim();
    setInputMsg("");
    const newHistory: ChatMessage[] = [
      ...messages,
      { role: "user", content: userText, timestamp: new Date().toISOString() }
    ];
    setMessages(newHistory);
    setIsSending(true);

    try {
      const baseUrl = process.env.NEXT_PUBLIC_API_BASE_URL || "https://pathmind-api.onrender.com";
      const personId = String(profile.person_id || "scholar-user");

      const res = await fetch(`${baseUrl}/api/counseling/chat`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-Person-ID": personId
        },
        body: JSON.stringify({
          person_id: personId,
          message: userText,
          history: newHistory
        })
      });

      if (!res.ok) {
        throw new Error("Chat request failed");
      }

      const reply = await res.json();
      setMessages([
        ...newHistory,
        { role: "counselor", content: reply.content, timestamp: reply.timestamp }
      ]);
    } catch {
      setMessages([
        ...newHistory,
        {
          role: "counselor",
          content: "I am having trouble connecting to the live counseling agent right now. Please try again shortly.",
          timestamp: new Date().toISOString()
        }
      ]);
    } finally {
      setIsSending(false);
    }
  };

  const getCategoryBadgeClass = (category: string) => {
    switch (category) {
      case "OBSERVED":
        return "bg-emerald-950/40 text-emerald-300 border-emerald-700/60";
      case "ASSESSED":
        return "bg-sky-950/40 text-sky-300 border-sky-700/60";
      case "INFERRED":
        return "bg-purple-950/40 text-purple-300 border-purple-700/60";
      case "UNKNOWN":
        return "bg-amber-950/40 text-amber-300 border-amber-700/60";
      case "RECOMMENDATION":
        return "bg-slate-900 text-slate-300 border-slate-700";
      default:
        return "bg-surface-container text-on-surface-variant border-outline";
    }
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      className="max-w-4xl mx-auto px-4 py-8 w-full"
    >
      {/* Top Banner: Status & Confidence */}
      <div className="mb-6 flex flex-wrap items-center justify-between gap-3 p-4 sketch-border bg-surface-container-low/95">
        <div className="flex items-center gap-3">
          <span className="material-symbols-outlined text-primary text-2xl" style={{ fontVariationSettings: "'FILL' 1" }}>
            verified_user
          </span>
          <div>
            <span className="font-headline-sm text-sm font-bold text-primary block">
              {isPreliminary ? "PRELIMINARY COUNSELING SYNTHESIS" : "ACTIVE PROFILE"}
            </span>
            <span className="font-body-md text-xs text-on-surface-variant">
              Evidence-Informed &bull; Non-Clinical &bull; Continuously Updateable
            </span>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <span className="font-body-md text-xs text-on-surface-variant">Confidence:</span>
          <span className={`px-2.5 py-1 text-xs font-bold rounded border ${
            overallConfidence === "HIGH" 
              ? "bg-emerald-900/30 text-emerald-300 border-emerald-600" 
              : overallConfidence === "MEDIUM"
              ? "bg-sky-900/30 text-sky-300 border-sky-600"
              : "bg-amber-900/30 text-amber-300 border-amber-600"
          }`}>
            {overallConfidence}
          </span>
        </div>
      </div>

      {/* Header */}
      <div className="mb-8 text-center">
        <h1 className="font-headline-lg text-3xl sm:text-4xl text-on-surface mb-2">
          Personal Learning &amp; Career Synthesis
        </h1>
        <p className="font-note-handwritten text-2xl text-on-surface-variant">
          Grounded in Holland RIASEC psychometrics, SCCT development factors, and observable tasks.
        </p>
      </div>

      {/* 1. Holland RIASEC Profile Breakdown */}
      {Object.keys(interestVector).length > 0 && (
        <div className="mb-8 p-6 sketch-border bg-surface-container-low/90">
          <div className="flex items-center justify-between mb-4 pb-2 border-b border-outline-variant/30">
            <h2 className="font-headline-sm text-xl text-on-surface flex items-center gap-2">
              <span className="material-symbols-outlined text-primary text-xl">hexagon</span>
              <span>Holland RIASEC Interest Vector</span>
            </h2>
            <span className="font-note-handwritten text-sm text-secondary">Normalized 0–100 Scale</span>
          </div>

          <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-6 gap-3">
            {[
              { key: "R", label: "Realistic", desc: "Hands-on & Systems" },
              { key: "I", label: "Investigative", desc: "Analytical & Research" },
              { key: "A", label: "Artistic", desc: "Creative & Design" },
              { key: "S", label: "Social", desc: "Mentoring & People" },
              { key: "E", label: "Enterprising", desc: "Leadership & Risk" },
              { key: "C", label: "Conventional", desc: "Structured Protocols" }
            ].map(({ key, label, desc }) => {
              const val = interestVector[key] !== undefined ? interestVector[key] : 0;
              return (
                <div key={key} className="p-3 rounded bg-surface-container/60 border border-outline-variant/30 flex flex-col items-center text-center">
                  <span className="font-headline-sm text-xs font-bold text-on-surface uppercase">{label}</span>
                  <span className="font-headline-lg text-2xl font-bold text-primary my-1">{Math.round(val)}%</span>
                  <div className="w-full bg-surface-container-high h-1.5 rounded-full overflow-hidden mb-1">
                    <div className="bg-primary h-full rounded-full transition-all duration-500" style={{ width: `${val}%` }} />
                  </div>
                  <span className="text-[10px] text-on-surface-variant font-note-handwritten">{desc}</span>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* 2. Contradiction Detection & Counselor Guidance */}
      {contradictions.length > 0 && (
        <div className="mb-8 p-6 sketch-border border-tertiary bg-tertiary-fixed/30">
          <div className="flex items-start gap-4">
            <span className="material-symbols-outlined text-tertiary text-3xl shrink-0 mt-0.5" style={{ fontVariationSettings: "'FILL' 1" }}>
              tips_and_updates
            </span>
            <div className="flex-1">
              <div className="flex items-center gap-2 mb-2">
                <h3 className="font-headline-sm text-xl text-tertiary">
                  Counselor Clarification Note (Contradiction Detected)
                </h3>
                <span className="font-note-handwritten text-xs text-tertiary sketchy-chip px-2 py-0.5 bg-surface/60">
                  Non-Judgmental Guidance
                </span>
              </div>
              <div className="space-y-1.5 text-sm text-on-surface mb-3">
                <p><strong>Reported Preference:</strong> {contradictions[0].reported_preference}</p>
                <p><strong>Observed Evidence:</strong> {contradictions[0].observed_evidence}</p>
              </div>
              <div className="p-3 bg-surface-container-low/90 rounded border-l-4 border-tertiary">
                <p className="font-note-handwritten text-xl text-on-surface-variant leading-relaxed">
                  Counselor Reflection: &ldquo;{contradictions[0].suggested_clarification}&rdquo;
                </p>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* 3. Evidence Gaps & Portfolio Request */}
      {evidenceGaps.length > 0 && (
        <div className="mb-8 p-6 sketch-border border-secondary bg-secondary-fixed/30">
          <div className="flex items-start gap-4">
            <span className="material-symbols-outlined text-secondary text-3xl shrink-0 mt-0.5" style={{ fontVariationSettings: "'FILL' 1" }}>
              fact_check
            </span>
            <div className="flex-1">
              <h3 className="font-headline-sm text-xl text-secondary mb-2">
                Areas Requiring Additional Observable Evidence
              </h3>
              <p className="font-body-md text-sm text-on-surface mb-3 leading-relaxed">
                To substantiate roadmap bypasses and accurately calibrate difficulty, please consider attaching these artifacts:
              </p>
              <div className="space-y-2 mb-4">
                {evidenceGaps.map((gap, i) => (
                  <div key={i} className="flex items-start gap-2 text-sm text-on-surface bg-surface-container-low/90 p-2.5 rounded border-l-3 border-secondary">
                    <span className="material-symbols-outlined text-secondary text-base shrink-0 mt-0.5">
                      arrow_forward
                    </span>
                    <span>{gap}</span>
                  </div>
                ))}
              </div>
              <Link
                href="/onboarding"
                className="ink-wash-btn-primary px-6 py-2 text-base inline-flex items-center gap-2"
              >
                <span className="material-symbols-outlined text-sm">upload_file</span>
                <span>Upload Repositories or Portfolio</span>
              </Link>
            </div>
          </div>
        </div>
      )}

      {/* 4. Structured Facts: Strengths & Capability Signals (with Category Badges) */}
      <div className="grid md:grid-cols-2 gap-6 mb-8">
        {/* Assessed & Observed Strengths */}
        <div className="sketch-border p-6 bg-surface-container-low/90 flex flex-col">
          <div className="flex items-center gap-2.5 mb-4 pb-3 border-b border-outline-variant/30">
            <span className="material-symbols-outlined text-primary text-2xl" style={{ fontVariationSettings: "'FILL' 1" }}>
              verified
            </span>
            <h3 className="font-headline-sm text-xl text-on-surface">
              Core Strengths &amp; Signals
            </h3>
          </div>
          <ul className="space-y-3.5 flex-1">
            {strengths.map((s, i) => (
              <li key={i} className="p-3.5 bg-surface-container/60 rounded border border-outline-variant/30">
                <div className="flex items-center justify-between gap-2 mb-1.5 flex-wrap">
                  <span className={`text-[10px] uppercase font-bold tracking-wider px-2 py-0.5 rounded border ${getCategoryBadgeClass(s.category)}`}>
                    [{s.category}]
                  </span>
                  <span className="font-note-handwritten text-xs text-on-surface-variant">
                    {s.source || "Assessment"}
                  </span>
                </div>
                <p className="font-headline-sm text-base text-on-surface font-medium mb-1">
                  {s.claim}
                </p>
                {Array.isArray(s.evidence) && s.evidence.length > 0 && (
                  <p className="font-note-handwritten text-xs text-on-surface-variant">
                    Evidence: {s.evidence.join("; ")}
                  </p>
                )}
              </li>
            ))}
          </ul>
        </div>

        {/* Observable Learning Signals */}
        <div className="sketch-border p-6 bg-surface-container-low/90 flex flex-col">
          <div className="flex items-center gap-2.5 mb-4 pb-3 border-b border-outline-variant/30">
            <span className="material-symbols-outlined text-secondary text-2xl" style={{ fontVariationSettings: "'FILL' 1" }}>
              psychology
            </span>
            <h3 className="font-headline-sm text-xl text-on-surface">
              Observable Learning Signals
            </h3>
          </div>
          <p className="font-body-md text-xs text-on-surface-variant mb-3">
            Qualitative problem decomposition and reasoning patterns (strictly non-IQ).
          </p>
          <ul className="space-y-3.5 flex-1">
            {learningSignals.map((ls, i) => (
              <li key={i} className="p-3.5 bg-surface-container/60 rounded border border-outline-variant/30">
                <div className="flex items-center justify-between gap-2 mb-1.5">
                  <span className={`text-[10px] uppercase font-bold tracking-wider px-2 py-0.5 rounded border ${getCategoryBadgeClass(ls.category)}`}>
                    [{ls.category}]
                  </span>
                </div>
                <p className="font-headline-sm text-base text-on-surface font-medium mb-1">
                  {ls.claim}
                </p>
                {Array.isArray(ls.evidence) && ls.evidence.length > 0 && (
                  <p className="font-note-handwritten text-xs text-on-surface-variant">
                    Context: {ls.evidence.join("; ")}
                  </p>
                )}
              </li>
            ))}
            {capabilitySignals.map((cs, i) => (
              <li key={`cs-${i}`} className="p-3.5 bg-surface-container/60 rounded border border-outline-variant/30">
                <div className="flex items-center justify-between gap-2 mb-1.5">
                  <span className={`text-[10px] uppercase font-bold tracking-wider px-2 py-0.5 rounded border ${getCategoryBadgeClass(cs.category)}`}>
                    [{cs.category}]
                  </span>
                </div>
                <p className="font-headline-sm text-base text-on-surface font-medium mb-1">
                  {cs.claim}
                </p>
                {Array.isArray(cs.evidence) && cs.evidence.length > 0 && (
                  <p className="font-note-handwritten text-xs text-on-surface-variant">
                    Evidence: {cs.evidence.join("; ")}
                  </p>
                )}
              </li>
            ))}
          </ul>
        </div>
      </div>

      {/* 5. Preliminary Candidate Directions */}
      <div className="mb-8 p-6 sketch-border bg-surface-container-low/90">
        <div className="flex items-center gap-2.5 mb-4 pb-3 border-b border-outline-variant/30">
          <span className="material-symbols-outlined text-tertiary text-2xl" style={{ fontVariationSettings: "'FILL' 1" }}>
            explore
          </span>
          <div>
            <h3 className="font-headline-sm text-xl text-on-surface">
              Preliminary Candidate Trajectories
            </h3>
            <span className="font-body-md text-xs text-on-surface-variant">
              Informed by psychometric congruences and external occupational taxonomy.
            </span>
          </div>
        </div>

        <div className="grid md:grid-cols-2 gap-4">
          {candidateDetails.length > 0 ? (
            candidateDetails.map((cd, i) => (
              <div key={i} className="p-4 rounded-lg bg-surface-container/50 border border-outline-variant/30">
                <div className="flex items-start justify-between gap-2 mb-2">
                  <h4 className="font-headline-sm text-base font-bold text-primary">
                    {cd.title}
                  </h4>
                  <span className="text-[10px] font-bold px-2 py-0.5 rounded bg-tertiary/20 text-tertiary border border-tertiary/40">
                    {cd.confidence} FIT
                  </span>
                </div>
                <p className="font-body-md text-sm text-on-surface mb-2">
                  {cd.rationale}
                </p>
                <div className="text-xs font-note-handwritten text-on-surface-variant">
                  <strong>Alignment:</strong> {cd.alignment}
                </div>
                {cd.related_occupations && cd.related_occupations.length > 0 && (
                  <div className="mt-2 pt-2 border-t border-outline-variant/20 text-[11px] text-secondary font-mono">
                    Occupations: {cd.related_occupations.join(", ")}
                  </div>
                )}
              </div>
            ))
          ) : (
            candidateDirections.map((dir, i) => (
              <div key={i} className="p-4 rounded-lg bg-surface-container/50 border border-outline-variant/30 flex items-center gap-3">
                <span className="material-symbols-outlined text-primary text-xl">arrow_forward</span>
                <span className="font-headline-sm text-base text-on-surface font-medium">{dir}</span>
              </div>
            ))
          )}
        </div>
      </div>

      {/* 6. Unknowns & Next Reflective Questions */}
      <div className="grid md:grid-cols-2 gap-6 mb-8">
        {unknowns.length > 0 && (
          <div className="p-5 sketch-border bg-surface-container-low/90">
            <h4 className="font-headline-sm text-base text-on-surface mb-2 flex items-center gap-2">
              <span className="material-symbols-outlined text-amber-400 text-lg">help</span>
              <span>Explicit Unknowns / Open Inquiries</span>
            </h4>
            <ul className="space-y-1.5 text-xs text-on-surface-variant font-body-md">
              {unknowns.map((u, i) => (
                <li key={i} className="flex items-start gap-1.5">
                  <span className="text-amber-400 font-bold">&bull;</span>
                  <span>{u}</span>
                </li>
              ))}
            </ul>
          </div>
        )}

        {nextQuestions.length > 0 && (
          <div className="p-5 sketch-border bg-surface-container-low/90">
            <h4 className="font-headline-sm text-base text-on-surface mb-2 flex items-center gap-2">
              <span className="material-symbols-outlined text-primary text-lg">forum</span>
              <span>Reflective Questions for Candidate</span>
            </h4>
            <ul className="space-y-1.5 text-xs text-on-surface-variant font-body-md">
              {nextQuestions.map((q, i) => (
                <li key={i} className="flex items-start gap-1.5">
                  <span className="text-primary font-bold">&bull;</span>
                  <span>{q}</span>
                </li>
              ))}
            </ul>
          </div>
        )}
      </div>

      {/* 7. Interactive ADK Counselor Conversation Drawer */}
      <div className="mb-8 p-6 sketch-border bg-surface-container-low/95">
        <div className="flex items-center justify-between mb-4 flex-wrap gap-2">
          <div className="flex items-center gap-2.5">
            <span className="material-symbols-outlined text-primary text-2xl">chat</span>
            <div>
              <h3 className="font-headline-sm text-lg text-on-surface">Interactive Counselor Dialogue</h3>
              <span className="font-note-handwritten text-xs text-on-surface-variant">Discuss findings, explore candidate directions, or clarify questions</span>
            </div>
          </div>
          <button
            type="button"
            onClick={() => setChatOpen(!chatOpen)}
            className="ink-wash-btn px-4 py-1 text-sm cursor-pointer"
          >
            {chatOpen ? "Close Dialogue" : "Open Counselor Dialogue"}
          </button>
        </div>

        {chatOpen && (
          <div className="space-y-4 pt-4 border-t border-outline-variant/30">
            <div className="max-h-64 overflow-y-auto space-y-3 p-3 bg-surface-container/50 rounded-lg border border-outline-variant/20">
              {messages.length === 0 ? (
                <p className="font-note-handwritten text-sm text-on-surface-variant text-center py-4">
                  Ask any question about your assessed interests, recommended directions, or next steps.
                </p>
              ) : (
                messages.map((m, i) => (
                  <div
                    key={i}
                    className={`p-3 rounded-lg text-sm max-w-[85%] ${
                      m.role === "user"
                        ? "ml-auto bg-primary-fixed/40 text-on-surface border border-primary/40"
                        : "mr-auto bg-surface-container-high text-on-surface border border-outline-variant/30"
                    }`}
                  >
                    <span className="text-[10px] font-bold block text-outline uppercase mb-0.5">
                      {m.role === "user" ? "You" : "Counselor"}
                    </span>
                    <p className="font-body-md leading-relaxed">{m.content}</p>
                  </div>
                ))
              )}
            </div>

            <form onSubmit={handleSendMessage} className="flex gap-2">
              <input
                type="text"
                value={inputMsg}
                onChange={(e) => setInputMsg(e.target.value)}
                placeholder="Ask your career mentor a question..."
                className="flex-1 hand-drawn-input px-3 py-2 text-sm bg-surface-container-low"
              />
              <button
                type="submit"
                disabled={!inputMsg.trim() || isSending}
                className="ink-wash-btn-primary px-5 py-2 text-sm flex items-center gap-1 disabled:opacity-50"
              >
                <span>{isSending ? "Thinking..." : "Send"}</span>
                <span className="material-symbols-outlined text-xs">send</span>
              </button>
            </form>
          </div>
        )}
      </div>

      {/* Action Footer */}
      <div className="flex flex-wrap justify-center gap-4 pt-4 border-t border-outline-variant/40">
        <Link
          href="/"
          className="ink-wash-btn px-6 py-2.5 text-lg flex items-center gap-2"
        >
          <span className="material-symbols-outlined text-sm">home</span>
          <span>Home</span>
        </Link>
        <Link
          href="/onboarding"
          className="ink-wash-btn px-6 py-2.5 text-lg flex items-center gap-2"
        >
          <span className="material-symbols-outlined text-sm">edit_note</span>
          <span>Update Portfolio</span>
        </Link>
        <Link
          href="/explorer"
          className="ink-wash-btn-primary px-8 py-2.5 text-xl flex items-center gap-2"
        >
          <span>Discover Candidate Pathways</span>
          <span className="material-symbols-outlined text-sm">alt_route</span>
        </Link>
      </div>
    </motion.div>
  );
}
