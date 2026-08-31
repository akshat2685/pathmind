"use client";

import { motion } from "framer-motion";
import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";

interface SynthesisStepProps {
  identity: string;
  goal: string;
}

export function SynthesisStep({ identity, goal }: SynthesisStepProps) {
  const [isSynthesizing, setIsSynthesizing] = useState(true);
  const router = useRouter();

  useEffect(() => {
    const timer = setTimeout(() => {
      setIsSynthesizing(false);
    }, 2000);
    return () => clearTimeout(timer);
  }, []);

  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.98 }}
      animate={{ opacity: 1, scale: 1 }}
      transition={{ duration: 0.5 }}
      className="max-w-3xl mx-auto px-4 py-8"
    >
      {isSynthesizing ? (
        <div className="flex flex-col items-center justify-center min-h-[40vh] space-y-6 text-center">
          <div className="w-16 h-16 rounded-full border-2 border-primary bg-primary/10 flex items-center justify-center">
            <span className="material-symbols-outlined text-3xl text-primary animate-spin">
              auto_awesome
            </span>
          </div>
          <div>
            <h2 className="font-headline-lg text-3xl text-on-surface mb-2">Synthesizing Scholar Profile...</h2>
            <p className="font-note-handwritten text-2xl text-on-surface-variant">The ADK counseling reasoning agent is preparing your path.</p>
          </div>
        </div>
      ) : (
        <motion.div
          initial={{ opacity: 0, y: 15 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5 }}
        >
          <div className="mb-8 text-center">
            <div className="inline-flex items-center justify-center w-14 h-14 rounded-full bg-primary/15 text-primary border border-primary/30 mb-3">
              <span className="material-symbols-outlined text-3xl" style={{ fontVariationSettings: "'FILL' 1" }}>
                auto_stories
              </span>
            </div>
            <h2 className="font-headline-lg text-3xl sm:text-4xl text-on-surface mb-1">Scholar Profile Synthesized</h2>
            <p className="font-note-handwritten text-2xl text-secondary">
              First ink marks recorded in the journal.
            </p>
          </div>

          <div className="sketch-border p-8 mb-10 bg-surface-container-low space-y-6">
            <div>
              <span className="font-label-md text-xs uppercase tracking-wider text-outline mb-1 block">Context & Persona</span>
              <p className="font-headline-sm text-2xl text-on-surface capitalize">{identity.replace("-", " ")}</p>
            </div>
            
            <div className="pt-4 border-t border-outline-variant/30">
              <span className="font-label-md text-xs uppercase tracking-wider text-outline mb-1 block">Stated Goal</span>
              <p className="font-note-handwritten text-2xl text-on-surface leading-relaxed border-l-3 border-tertiary pl-4">
                &ldquo;{goal}&rdquo;
              </p>
            </div>
            
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-6 pt-4 border-t border-outline-variant/30">
              <div>
                <span className="font-label-md text-xs uppercase tracking-wider text-outline mb-2 block">Identified Capabilities</span>
                <div className="flex flex-wrap gap-2">
                  <span className="sketchy-chip px-3 py-1 font-note-handwritten text-lg text-primary">Autonomous Agency</span>
                  <span className="sketchy-chip px-3 py-1 font-note-handwritten text-lg text-secondary">System Reasoning</span>
                  <span className="sketchy-chip px-3 py-1 font-note-handwritten text-lg text-tertiary">Practical Artifacts</span>
                </div>
              </div>
              <div>
                <span className="font-label-md text-xs uppercase tracking-wider text-outline mb-2 block">Next Chapter</span>
                <p className="font-body-md text-sm text-on-surface-variant">
                  We invite you to take the structured evidence counseling assessment to unlock your tailored trajectory.
                </p>
              </div>
            </div>
          </div>

          <div className="flex justify-center gap-4">
            <button 
              type="button"
              onClick={() => router.push("/assessment")}
              className="ink-wash-btn-primary px-10 py-3 text-2xl flex items-center gap-3 cursor-pointer"
            >
              <span>Proceed to Assessment Engine</span>
              <span className="material-symbols-outlined text-lg">east</span>
            </button>
          </div>
        </motion.div>
      )}
    </motion.div>
  );
}
