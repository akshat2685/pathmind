"use client";

import { motion } from "framer-motion";
import Link from "next/link";

interface CounselingDashboardProps {
  profile: Record<string, unknown> | null; 
}

export function CounselingDashboard({ profile }: CounselingDashboardProps) {
  if (!profile) return null;

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      className="max-w-4xl mx-auto px-4 py-8 w-full"
    >
      {/* Header */}
      <div className="mb-8 text-center">
        <div className="inline-flex items-center justify-center w-16 h-16 rounded-full bg-primary/15 text-primary border border-primary/30 mb-3">
          <span className="material-symbols-outlined text-3xl" style={{ fontVariationSettings: "'FILL' 1" }}>
            psychology_alt
          </span>
        </div>
        <h2 className="font-headline-lg text-3xl sm:text-4xl text-on-surface mb-2">
          Your Counseling Synthesis
        </h2>
        <p className="font-note-handwritten text-2xl text-on-surface-variant">
          Informed by structured psychometrics, observable evidence, and Gemini ADK reasoning.
        </p>
      </div>

      {/* Error Fallback Banner */}
      {Boolean(profile.error) && (
        <div className="mb-8 p-6 sketch-border border-error bg-error-container/40">
          <div className="flex items-start gap-4">
            <span className="material-symbols-outlined text-error text-3xl shrink-0 mt-0.5">
              error
            </span>
            <div>
              <h3 className="font-headline-sm text-lg text-error mb-1">
                Synthesis Fallback: {String((profile.error as Record<string, unknown>)?.code || "UNAVAILABLE")}
              </h3>
              <p className="font-body-md text-sm text-on-surface-variant mb-2">
                {String((profile.error as Record<string, unknown>)?.message || "ADK reasoning engine currently offline.")}
              </p>
              <p className="font-note-handwritten text-lg text-tertiary">
                Using local cached longitudinal insights for your session.
              </p>
            </div>
          </div>
        </div>
      )}

      {!profile.error && (
        <>
          {/* Contradiction Callout (Handwritten Margin Note) */}
          {Array.isArray(profile.contradictions) && profile.contradictions.length > 0 && (
            <div className="mb-8 p-6 sketch-border border-secondary bg-secondary-fixed/40">
              <div className="flex items-start gap-4">
                <span className="material-symbols-outlined text-secondary text-3xl shrink-0 mt-0.5" style={{ fontVariationSettings: "'FILL' 1" }}>
                  warning
                </span>
                <div>
                  <div className="flex items-center gap-2 mb-2">
                    <h3 className="font-headline-sm text-xl text-secondary">
                      Cognitive Contradiction Observed
                    </h3>
                    <span className="font-note-handwritten text-base text-tertiary sketchy-chip px-2 py-0.5">
                      Marginalia note
                    </span>
                  </div>
                  <p className="font-body-md text-sm text-on-surface mb-1.5">
                    <strong>Reported Preference:</strong> &ldquo;{String((profile.contradictions as Record<string, unknown>[])[0].reported_preference)}&rdquo;
                  </p>
                  <p className="font-body-md text-sm text-on-surface mb-3">
                    <strong>Observable Evidence:</strong> &ldquo;{String((profile.contradictions as Record<string, unknown>[])[0].observed_evidence)}&rdquo;
                  </p>
                  <div className="p-3 bg-surface-container-low/90 rounded border-l-4 border-secondary">
                    <p className="font-note-handwritten text-xl text-on-surface-variant italic">
                      Mentor Suggestion: {String((profile.contradictions as Record<string, unknown>[])[0].suggested_clarification)}
                    </p>
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* Demonstrated Strengths & Candidate Directions Grid */}
          <div className="grid md:grid-cols-2 gap-6 mb-8">
            
            {/* Strengths Card */}
            <div className="sketch-border p-6 bg-surface-container-low/90 flex flex-col">
              <div className="flex items-center gap-2.5 mb-4 pb-3 border-b border-outline-variant/30">
                <span className="material-symbols-outlined text-primary text-2xl" style={{ fontVariationSettings: "'FILL' 1" }}>
                  check_circle
                </span>
                <h3 className="font-headline-sm text-xl text-on-surface">
                  Demonstrated Strengths
                </h3>
              </div>
              <ul className="space-y-4 flex-1">
                {(profile.strengths as Record<string, unknown>[])?.map((s: Record<string, unknown>, i: number) => (
                  <li key={i} className="p-3 bg-surface-container/50 rounded border border-outline-variant/30">
                    <span className="font-headline-sm text-base text-on-surface block mb-1">
                      {String(s.claim)}
                    </span>
                    <span className="font-note-handwritten text-sm text-primary sketchy-chip px-2 py-0.5 inline-block">
                      {String(s.confidence)} Confidence
                    </span>
                  </li>
                ))}
              </ul>
            </div>

            {/* Candidate Directions Card */}
            <div className="sketch-border p-6 bg-surface-container-low/90 flex flex-col">
              <div className="flex items-center gap-2.5 mb-4 pb-3 border-b border-outline-variant/30">
                <span className="material-symbols-outlined text-tertiary text-2xl" style={{ fontVariationSettings: "'FILL' 1" }}>
                  explore
                </span>
                <h3 className="font-headline-sm text-xl text-on-surface">
                  Candidate Trajectories
                </h3>
              </div>
              <ul className="space-y-3 flex-1">
                {(profile.candidate_directions as string[])?.map((d: string, i: number) => (
                  <li key={i} className="flex items-start gap-2 p-2.5 rounded hover:bg-surface-container/40 transition-colors">
                    <span className="material-symbols-outlined text-tertiary text-lg shrink-0 mt-0.5">
                      arrow_forward_ios
                    </span>
                    <span className="font-body-md text-base text-on-surface leading-snug">
                      {d}
                    </span>
                  </li>
                ))}
              </ul>
            </div>

          </div>
        </>
      )}

      {/* Action Footer */}
      <div className="flex flex-wrap justify-center gap-4 pt-4 border-t border-outline-variant/40">
        <Link
          href="/"
          className="ink-wash-btn px-8 py-2.5 text-xl flex items-center gap-2"
        >
          <span className="material-symbols-outlined text-sm">home</span>
          <span>The Initiation</span>
        </Link>
        <Link
          href="/onboarding"
          className="ink-wash-btn-primary px-8 py-2.5 text-xl flex items-center gap-2"
        >
          <span>Update Scholar Identity</span>
          <span className="material-symbols-outlined text-sm">edit</span>
        </Link>
      </div>

    </motion.div>
  );
}
