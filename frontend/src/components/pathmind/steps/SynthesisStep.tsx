"use client";

import { motion } from "framer-motion";
import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { EvidenceItem } from "./EvidenceStep";

interface SynthesisStepProps {
  userName: string;
  identity: string;
  goal: string;
  evidence: EvidenceItem[];
}

const IDENTITY_LABELS: Record<string, string> = {
  school: "School Student",
  college: "College Student",
  professional: "Professional",
  switcher: "Career Switcher",
  lifelong: "Lifelong Scholar",
};

export function SynthesisStep({ userName, identity, goal, evidence }: SynthesisStepProps) {
  const [isSynthesizing, setIsSynthesizing] = useState(true);
  const router = useRouter();

  useEffect(() => {
    const timer = setTimeout(() => {
      setIsSynthesizing(false);
    }, 1600);
    return () => clearTimeout(timer);
  }, []);

  const displayName = userName || "Scholar";
  const displayIdentity = IDENTITY_LABELS[identity] || identity || "Self-Directed Scholar";

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
            <h2 className="font-headline-lg text-3xl text-on-surface mb-2">Scribing {displayName}&apos;s Profile...</h2>
            <p className="font-note-handwritten text-2xl text-on-surface-variant">Recording your goals and evidence for the counseling engine.</p>
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
            <h2 className="font-headline-lg text-3xl sm:text-4xl text-on-surface mb-1">
              Profile Scribed, {displayName}!
            </h2>
            <p className="font-note-handwritten text-2xl text-secondary">
              Your journey has been recorded.
            </p>
          </div>

          <div className="sketch-border p-8 mb-10 bg-surface-container-low space-y-6">
            <div>
              <span className="font-label-md text-xs uppercase tracking-wider text-outline mb-1 block">Name</span>
              <p className="font-headline-sm text-2xl text-on-surface">{displayName}</p>
            </div>
            
            <div className="pt-4 border-t border-outline-variant/30">
              <span className="font-label-md text-xs uppercase tracking-wider text-outline mb-1 block">Current Stage</span>
              <p className="font-headline-sm text-xl text-on-surface">{displayIdentity}</p>
            </div>

            <div className="pt-4 border-t border-outline-variant/30">
              <span className="font-label-md text-xs uppercase tracking-wider text-outline mb-1 block">Stated Goal</span>
              <p className="font-note-handwritten text-2xl text-on-surface leading-relaxed border-l-4 border-tertiary pl-4">
                &ldquo;{goal || "Exploring emerging disciplines and career pathways"}&rdquo;
              </p>
            </div>

            <div className="pt-4 border-t border-outline-variant/30">
              <span className="font-label-md text-xs uppercase tracking-wider text-outline mb-2 block">
                Attached Evidence ({evidence.length})
              </span>
              {evidence.length > 0 ? (
                <div className="space-y-2">
                  {evidence.map((item, idx) => (
                    <div key={idx} className="p-2.5 bg-surface-container/60 rounded border border-outline-variant/30 flex items-center gap-2">
                      <span className="material-symbols-outlined text-primary text-xl">
                        {item.type === "file" ? "description" : item.type === "link" ? "link" : "code"}
                      </span>
                      <span className="font-headline-sm text-sm text-on-surface">{item.name}</span>
                    </div>
                  ))}
                </div>
              ) : (
                <p className="font-note-handwritten text-lg text-tertiary">
                  No portfolio attached — the counselor will ask for relevant proof during assessment.
                </p>
              )}
            </div>
          </div>

          <div className="flex justify-center">
            <button 
              type="button"
              onClick={() => router.push("/assessment")}
              className="ink-wash-btn-primary px-10 py-3 text-2xl flex items-center gap-3 cursor-pointer"
            >
              <span>Proceed to Psychometric Assessment</span>
              <span className="material-symbols-outlined text-lg">east</span>
            </button>
          </div>
        </motion.div>
      )}
    </motion.div>
  );
}
