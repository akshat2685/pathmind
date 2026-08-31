"use client";

import { motion } from "framer-motion";
import { AlertCircle, CheckCircle2, ChevronRight, Activity, Lightbulb } from "lucide-react";

interface CounselingDashboardProps {
  profile: Record<string, unknown> | null; 
}

export function CounselingDashboard({ profile }: CounselingDashboardProps) {
  
  if (!profile) return null;

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      className="max-w-4xl mx-auto px-4 py-12"
    >
      <div className="mb-10 text-center">
        <div className="inline-flex items-center justify-center p-3 bg-indigo-500/10 text-indigo-500 rounded-full mb-6">
          <Activity className="w-6 h-6" />
        </div>
        <h2 className="text-3xl font-medium tracking-tight mb-3">Your Counseling Synthesis</h2>
        <p className="text-slate-500">Based on your assessments, evidence, and stated goals.</p>
      </div>

      {Array.isArray(profile.contradictions) && profile.contradictions.length > 0 && (
        <div className="mb-8 p-6 bg-amber-500/10 border border-amber-500/20 rounded-2xl">
          <div className="flex items-start gap-4">
            <AlertCircle className="w-6 h-6 text-amber-500 shrink-0 mt-1" />
            <div>
              <h3 className="text-amber-500 font-medium text-lg mb-2">Contradiction Detected</h3>
              <p className="text-sm text-slate-700 dark:text-slate-300 mb-2">
                <strong>Stated:</strong> {String((profile.contradictions as Record<string, unknown>[])[0].reported_preference)}
              </p>
              <p className="text-sm text-slate-700 dark:text-slate-300 mb-4">
                <strong>Observed:</strong> {String((profile.contradictions as Record<string, unknown>[])[0].observed_evidence)}
              </p>
              <p className="text-sm text-slate-700 dark:text-slate-300 italic">
                {String((profile.contradictions as Record<string, unknown>[])[0].suggested_clarification)}
              </p>
            </div>
          </div>
        </div>
      )}

      <div className="grid md:grid-cols-2 gap-6 mb-8">
        <div className="glass-card rounded-2xl p-6">
          <h3 className="font-medium text-lg mb-4 flex items-center gap-2">
            <CheckCircle2 className="w-5 h-5 text-emerald-500" />
            Demonstrated Strengths
          </h3>
          <ul className="space-y-4">
            {(profile.strengths as Record<string, unknown>[])?.map((s: Record<string, unknown>, i: number) => (
              <li key={i} className="text-sm">
                <span className="font-medium text-slate-900 dark:text-white block mb-1">{String(s.claim)}</span>
                <span className="text-slate-500 text-xs uppercase bg-slate-100 dark:bg-slate-800 px-2 py-0.5 rounded mr-2">
                  {String(s.confidence)} CONFIDENCE
                </span>
              </li>
            ))}
          </ul>
        </div>

        <div className="glass-card rounded-2xl p-6">
          <h3 className="font-medium text-lg mb-4 flex items-center gap-2">
            <Lightbulb className="w-5 h-5 text-indigo-500" />
            Candidate Directions
          </h3>
          <ul className="space-y-4">
            {(profile.candidate_directions as string[])?.map((d: string, i: number) => (
              <li key={i} className="text-sm flex items-start gap-2">
                <ChevronRight className="w-4 h-4 text-indigo-500 shrink-0 mt-0.5" />
                <span className="text-slate-700 dark:text-slate-300 leading-relaxed">{d}</span>
              </li>
            ))}
          </ul>
        </div>
      </div>

    </motion.div>
  );
}
