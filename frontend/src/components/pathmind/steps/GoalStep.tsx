"use client";

import { motion } from "framer-motion";
import { useState } from "react";

interface GoalStepProps {
  onNext: (goal: string) => void;
  onBack: () => void;
}

// Intelligent text validation to prevent random spam / gibberish
export function validateMeaningfulText(text: string, minWords = 3, minLength = 12): { isValid: boolean; message: string } {
  const trimmed = text.trim();
  if (trimmed.length < minLength) {
    return { 
      isValid: false, 
      message: `Please enter at least ${minLength} characters describing your goals.` 
    };
  }

  const words = trimmed.split(/\s+/).filter(w => w.length > 1);
  if (words.length < minWords) {
    return { 
      isValid: false, 
      message: `Please provide a descriptive goal with at least ${minWords} words (e.g., "Master machine learning foundations and build scalable backend systems").` 
    };
  }

  // Check character diversity to block repetitive keyboard mash (e.g., "aaaaaaaaaa" or "asdfasdfasdf")
  const uniqueChars = new Set(trimmed.toLowerCase().replace(/\s+/g, "")).size;
  if (uniqueChars < 5) {
    return {
      isValid: false,
      message: "Please enter a valid, descriptive aspiration rather than repetitive characters."
    };
  }

  // Check if a single character dominates the string
  const counts: Record<string, number> = {};
  for (const c of trimmed.toLowerCase().replace(/\s+/g, "")) {
    counts[c] = (counts[c] || 0) + 1;
    if (counts[c] / trimmed.length > 0.45 && trimmed.length > 10) {
      return {
        isValid: false,
        message: "Please write a coherent description of what you wish to learn or achieve."
      };
    }
  }

  return { isValid: true, message: "Valid aspiration recorded." };
}

export function GoalStep({ onNext, onBack }: GoalStepProps) {
  const [goal, setGoal] = useState("");
  const [touched, setTouched] = useState(false);

  const validation = validateMeaningfulText(goal);

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
          Aspiration Scribing
        </span>
        <h2 className="font-headline-lg text-3xl sm:text-4xl text-on-surface mb-2">
          What are you aiming to achieve?
        </h2>
        <p className="font-body-md text-on-surface-variant">
          Please describe your target discipline, technical interests, or career direction in your own words.
        </p>
      </div>

      <div className="mb-8 relative sketch-border p-6 bg-surface-container-low/90">
        <textarea
          value={goal}
          onChange={(e) => {
            setGoal(e.target.value);
            if (!touched) setTouched(true);
          }}
          placeholder="e.g., I want to master neural systems and LLM agent architecture, transitioning from backend engineering..."
          className="w-full h-40 bg-transparent hand-drawn-input resize-none focus:outline-none placeholder:text-outline/60 text-xl leading-relaxed"
        />
        
        <div className="flex flex-wrap justify-between items-center mt-3 pt-3 border-t border-outline-variant/30 text-xs font-label-md text-on-surface-variant gap-2">
          <span>{goal.length} characters inscribed</span>
          
          {touched && !validation.isValid && (
            <span className="font-body-md text-xs text-error font-medium">
              {validation.message}
            </span>
          )}

          {validation.isValid && (
            <span className="font-note-handwritten text-base text-primary font-medium flex items-center gap-1">
              <span className="material-symbols-outlined text-sm">check_circle</span>
              <span>Aspiration Ready</span>
            </span>
          )}
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
          disabled={!validation.isValid} 
          onClick={() => onNext(goal.trim())}
          className={`px-8 py-2.5 text-xl flex items-center gap-2 cursor-pointer ${
            validation.isValid ? 'ink-wash-btn-primary' : 'opacity-40 cursor-not-allowed bg-surface-dim border-2 border-outline text-outline'
          }`}
        >
          <span>Continue</span>
          <span className="material-symbols-outlined text-sm">east</span>
        </button>
      </div>
    </motion.div>
  );
}
