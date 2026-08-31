"use client";

import { motion } from "framer-motion";
import Link from "next/link";

interface CounselingDashboardProps {
  profile: Record<string, unknown> | null; 
}

export function CounselingDashboard({ profile }: CounselingDashboardProps) {
  if (!profile) return null;

  const evidenceGaps = (profile.evidence_gaps as string[]) || [];
  const nextQuestions = (profile.next_questions as string[]) || [];
  const strengths = (profile.strengths as Record<string, unknown>[]) || [];
  const interestPatterns = (profile.interest_patterns as Record<string, unknown>[]) || [];
  const candidateDirections = (profile.candidate_directions as string[]) || [];
  const contradictions = (profile.contradictions as Record<string, unknown>[]) || [];

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
            psychology
          </span>
        </div>
        <h2 className="font-headline-lg text-3xl sm:text-4xl text-on-surface mb-2">
          Your Personalized Career &amp; Psychometric Profile
        </h2>
        <p className="font-note-handwritten text-2xl text-on-surface-variant">
          Carefully evaluated across Holland RIASEC dimensions and self-efficacy foundations.
        </p>
      </div>

      {/* Error Fallback Banner */}
      {Boolean(profile.error) && (
        <div className="mb-8 p-6 sketch-border border-secondary bg-secondary-fixed/30">
          <div className="flex items-start gap-4">
            <span className="material-symbols-outlined text-secondary text-3xl shrink-0 mt-0.5">
              info
            </span>
            <div>
              <h3 className="font-headline-sm text-lg text-secondary mb-1">
                Assessment In Progress
              </h3>
              <p className="font-body-md text-sm text-on-surface mb-2">
                We are currently processing your answers. Please ensure your assessment answers are complete, or try submitting again in a moment.
              </p>
            </div>
          </div>
        </div>
      )}

      {!profile.error && (
        <>
          {/* POLITE PORTFOLIO & EVIDENCE REQUEST BANNER */}
          {evidenceGaps.length > 0 && (
            <div className="mb-8 p-6 sketch-border border-secondary bg-secondary-fixed/40">
              <div className="flex items-start gap-4">
                <span className="material-symbols-outlined text-secondary text-3xl shrink-0 mt-0.5" style={{ fontVariationSettings: "'FILL' 1" }}>
                  fact_check
                </span>
                <div className="flex-1">
                  <div className="flex items-center justify-between flex-wrap gap-2 mb-2">
                    <h3 className="font-headline-sm text-xl text-secondary">
                      Portfolio &amp; Project Experience Request
                    </h3>
                    <span className="font-note-handwritten text-base text-secondary sketchy-chip px-3 py-0.5 bg-surface/80">
                      Help us substantiate your roadmap
                    </span>
                  </div>
                  <p className="font-body-md text-sm text-on-surface mb-3 leading-relaxed">
                    To help us give you the most accurate and actionable recommendations, please consider sharing links to your project portfolio, code repositories, or course transcripts.
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
                    className="ink-wash-btn-primary px-6 py-2 text-lg inline-flex items-center gap-2"
                  >
                    <span className="material-symbols-outlined text-sm">upload_file</span>
                    <span>Upload Portfolio or Repositories</span>
                  </Link>
                </div>
              </div>
            </div>
          )}

          {/* POLITE CONTRADICTION / MENTOR ADVICE */}
          {contradictions.length > 0 && (
            <div className="mb-8 p-6 sketch-border border-tertiary bg-tertiary-fixed/40">
              <div className="flex items-start gap-4">
                <span className="material-symbols-outlined text-tertiary text-3xl shrink-0 mt-0.5" style={{ fontVariationSettings: "'FILL' 1" }}>
                  tips_and_updates
                </span>
                <div>
                  <div className="flex items-center gap-2 mb-2">
                    <h3 className="font-headline-sm text-xl text-tertiary">
                      Counselor Guidance on Aspirations &amp; Profile Fit
                    </h3>
                    <span className="font-note-handwritten text-base text-tertiary sketchy-chip px-2 py-0.5">
                      Career Alignment Note
                    </span>
                  </div>
                  <p className="font-body-md text-sm text-on-surface mb-1.5">
                    <strong>Stated Goal:</strong> &ldquo;{String(contradictions[0].reported_preference)}&rdquo;
                  </p>
                  <p className="font-body-md text-sm text-on-surface mb-3">
                    <strong>Psychometric Indicator:</strong> &ldquo;{String(contradictions[0].observed_evidence)}&rdquo;
                  </p>
                  <div className="p-3 bg-surface-container-low/90 rounded border-l-4 border-tertiary">
                    <p className="font-note-handwritten text-xl text-on-surface-variant leading-relaxed">
                      Counselor Advice: {String(contradictions[0].suggested_clarification)}
                    </p>
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* TWO COLUMN GRID: Assessed Strengths vs Recommended Directions */}
          <div className="grid md:grid-cols-2 gap-6 mb-8">
            
            {/* Assessed Strengths & Interests */}
            <div className="sketch-border p-6 bg-surface-container-low/90 flex flex-col">
              <div className="flex items-center gap-2.5 mb-4 pb-3 border-b border-outline-variant/30">
                <span className="material-symbols-outlined text-primary text-2xl" style={{ fontVariationSettings: "'FILL' 1" }}>
                  verified
                </span>
                <h3 className="font-headline-sm text-xl text-on-surface">
                  Core Strengths &amp; Interests
                </h3>
              </div>
              <ul className="space-y-3.5 flex-1">
                {strengths.map((s, i) => (
                  <li key={i} className="p-3 bg-surface-container/60 rounded border border-outline-variant/30">
                    <div className="flex items-center justify-between gap-2 mb-1">
                      <span className="font-headline-sm text-base text-on-surface font-medium">
                        {String(s.claim)}
                      </span>
                      <span className={`font-note-handwritten text-xs px-2 py-0.5 rounded border ${
                        String(s.confidence) === 'HIGH' ? 'bg-primary-fixed text-primary border-primary' :
                        'bg-surface-container-high text-on-surface-variant border-outline'
                      }`}>
                        {String(s.confidence) === 'HIGH' ? 'Verified Fit' : 'Emerging'}
                      </span>
                    </div>
                    {Array.isArray(s.evidence) && s.evidence.length > 0 && (
                      <p className="font-note-handwritten text-sm text-on-surface-variant">
                        Context: {s.evidence.join(", ")}
                      </p>
                    )}
                  </li>
                ))}
                {interestPatterns.map((ip, i) => (
                  <li key={`ip-${i}`} className="p-3 bg-surface-container/60 rounded border border-outline-variant/30">
                    <span className="font-headline-sm text-base text-on-surface block mb-1">
                      {String(ip.claim)}
                    </span>
                    <span className="font-note-handwritten text-xs text-secondary sketchy-chip px-2 py-0.5">
                      Holland Interest Match
                    </span>
                  </li>
                ))}
              </ul>
            </div>

            {/* Recommended Future Directions */}
            <div className="sketch-border p-6 bg-surface-container-low/90 flex flex-col">
              <div className="flex items-center gap-2.5 mb-4 pb-3 border-b border-outline-variant/30">
                <span className="material-symbols-outlined text-tertiary text-2xl" style={{ fontVariationSettings: "'FILL' 1" }}>
                  explore
                </span>
                <h3 className="font-headline-sm text-xl text-on-surface">
                  Recommended Learning Pathways
                </h3>
              </div>
              <p className="font-body-md text-xs text-on-surface-variant mb-3">
                Tailored pathways to explore based on your measured personality traits and learning style.
              </p>
              <ul className="space-y-3 flex-1">
                {candidateDirections.map((d, i) => (
                  <li key={i} className="flex items-start gap-2.5 p-3 rounded bg-surface-container/40 border border-outline-variant/20">
                    <span className="material-symbols-outlined text-tertiary text-lg shrink-0 mt-0.5">
                      arrow_forward_ios
                    </span>
                    <span className="font-body-md text-sm text-on-surface leading-snug">
                      {d}
                    </span>
                  </li>
                ))}
              </ul>
            </div>

          </div>

          {/* NEXT QUESTIONS & GUIDANCE */}
          {nextQuestions.length > 0 && (
            <div className="mb-8 p-6 sketch-border bg-surface-container-low/90">
              <h3 className="font-headline-sm text-lg text-on-surface mb-3 flex items-center gap-2">
                <span className="material-symbols-outlined text-primary text-xl">help_outline</span>
                <span>Recommended Questions for Further Reflection</span>
              </h3>
              <ul className="space-y-2">
                {nextQuestions.map((q, i) => (
                  <li key={i} className="flex items-start gap-2 text-sm text-on-surface-variant font-body-md">
                    <span className="text-primary font-bold">•</span>
                    <span>{q}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}

        </>
      )}

      {/* Action Footer */}
      <div className="flex flex-wrap justify-center gap-4 pt-4 border-t border-outline-variant/40">
        <Link
          href="/"
          className="ink-wash-btn px-8 py-2.5 text-xl flex items-center gap-2"
        >
          <span className="material-symbols-outlined text-sm">home</span>
          <span>Home</span>
        </Link>
        <Link
          href="/onboarding"
          className="ink-wash-btn-primary px-8 py-2.5 text-xl flex items-center gap-2"
        >
          <span>Update Portfolio &amp; Goals</span>
          <span className="material-symbols-outlined text-sm">edit_note</span>
        </Link>
      </div>

    </motion.div>
  );
}
