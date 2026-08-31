"use client";

import { motion } from "framer-motion";
import { useState } from "react";

interface GoalStepProps {
  onNext: (goal: string) => void;
  onBack: () => void;
}

export function GoalStep({ onNext, onBack }: GoalStepProps) {
  const [goal, setGoal] = useState("");

  return (
    <motion.div
      initial={{ opacity: 0, x: 20 }}
      animate={{ opacity: 1, x: 0 }}
      exit={{ opacity: 0, x: -20 }}
      transition={{ duration: 0.4 }}
      className="max-w-2xl mx-auto px-4 py-8"
    >
      <div className="mb-8 text-center">
        <span className="font-note-handwritten text-xl text-tertiary sketchy-chip px-3 py-1 mb-2 inline-block">
          Aspiration Ink
        </span>
        <h2 className="font-headline-lg text-3xl sm:text-4xl text-on-surface mb-2">
          What are you trying to achieve?
        </h2>
        <p className="font-body-md text-on-surface-variant">
          Be as specific or as open as you like. We will refine and unfold this path together.
        </p>
      </div>

      <div className="mb-10 relative sketch-border p-6 bg-surface-container-low/90">
        <textarea
          value={goal}
          onChange={(e) => setGoal(e.target.value)}
          placeholder="e.g., I want to master neural systems and LLM agent architecture, transitioning from backend engineering..."
          className="w-full h-44 bg-transparent hand-drawn-input resize-none focus:outline-none placeholder:text-outline/60 text-xl leading-relaxed"
        />
        <div className="flex justify-between items-center mt-3 pt-3 border-t border-outline-variant/30 text-xs font-label-md text-on-surface-variant">
          <span>{goal.length} characters inscribed</span>
          <span className="font-note-handwritten text-sm text-tertiary">Fountain pen ink mode</span>
        </div>
      </div>

      <div className="flex justify-between items-center pt-4 border-t border-outline-variant/40">
        <button
          type="button"
          onClick={onBack}
          className="ink-wash-btn px-6 py-2 text-xl cursor-pointer"
        >
          Back
        </button>
        <button 
          type="button"
          disabled={goal.trim().length < 4} 
          onClick={() => onNext(goal)}
          className={`px-8 py-2.5 text-xl flex items-center gap-2 cursor-pointer ${
            goal.trim().length >= 4 ? 'ink-wash-btn-primary' : 'opacity-50 cursor-not-allowed bg-surface-dim border-2 border-outline text-outline'
          }`}
        >
          <span>Continue</span>
          <span className="material-symbols-outlined text-sm">east</span>
        </button>
      </div>
    </motion.div>
  );
}
