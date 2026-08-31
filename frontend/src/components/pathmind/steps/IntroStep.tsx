"use client";

import { motion } from "framer-motion";

interface IntroStepProps {
  onNext: () => void;
}

export function IntroStep({ onNext }: IntroStepProps) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -10 }}
      transition={{ duration: 0.5, ease: "easeOut" }}
      className="flex flex-col items-center justify-center text-center max-w-2xl mx-auto px-4 py-8"
    >
      <div className="space-y-6">
        <motion.div
          initial={{ opacity: 0, scale: 0.95 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ delay: 0.1, duration: 0.6 }}
        >
          <div className="inline-flex h-16 w-16 items-center justify-center rounded-full border-2 border-primary bg-primary/10 text-primary mb-4">
            <span className="material-symbols-outlined text-3xl" style={{ fontVariationSettings: "'FILL' 1" }}>
              history_edu
            </span>
          </div>
        </motion.div>
        
        <div className="inline-flex items-center gap-2 px-4 py-1.5 sketchy-chip text-tertiary">
          <span className="font-note-handwritten text-xl font-medium">Chapter II: The First Step</span>
        </div>

        <h1 className="font-headline-lg text-4xl sm:text-5xl text-on-surface">
          Your learning journey <br className="hidden sm:block" />
          <span className="text-secondary italic">
            has memory.
          </span>
        </h1>
        
        <p className="font-body-md text-lg text-on-surface-variant max-w-lg mx-auto leading-relaxed">
          Welcome to PATHMIND. Let us scribe your longitudinal scholar profile and discover the right trajectory for your career.
        </p>
      </div>

      <motion.div 
        className="mt-10"
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ delay: 0.4, duration: 0.5 }}
      >
        <button 
          onClick={onNext}
          className="ink-wash-btn-primary px-10 py-3 text-2xl flex items-center gap-3 cursor-pointer"
        >
          <span>Begin Scribing</span>
          <span className="material-symbols-outlined text-lg">east</span>
        </button>
      </motion.div>
    </motion.div>
  );
}
