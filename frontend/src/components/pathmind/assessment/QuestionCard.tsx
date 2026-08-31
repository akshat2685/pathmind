"use client";

import { motion } from "framer-motion";

interface QuestionCardProps {
  questionText: string;
  options: { value: string | number; label: string }[];
  onAnswer: (value: string | number) => void;
  onBack?: () => void;
  progress: number;
  total: number;
  sectionName: string;
}

export function QuestionCard({
  questionText,
  options,
  onAnswer,
  onBack,
  progress,
  total,
  sectionName
}: QuestionCardProps) {
  return (
    <motion.div
      key={questionText}
      initial={{ opacity: 0, x: 20 }}
      animate={{ opacity: 1, x: 0 }}
      exit={{ opacity: 0, x: -20 }}
      transition={{ duration: 0.4 }}
      className="max-w-2xl mx-auto px-4 py-8 w-full"
    >
      {/* Progress & Section Badge */}
      <div className="flex justify-between items-center mb-6 text-sm">
        <span className="font-note-handwritten text-xl text-tertiary sketchy-chip px-3 py-1">
          {sectionName}
        </span>
        <span className="font-headline-sm text-sm text-on-surface-variant font-medium">
          Node {progress} of {total}
        </span>
      </div>

      {/* Progress Ink Bar */}
      <div className="w-full bg-surface-container h-2 rounded-full mb-8 overflow-hidden border border-outline-variant/50">
        <div 
          className="bg-primary h-full transition-all duration-500 rounded-full"
          style={{ width: `${(progress / total) * 100}%` }}
        />
      </div>

      {/* Question Prompt */}
      <div className="mb-8 p-6 sketch-border bg-surface-container-low/90">
        <h2 className="font-headline-lg text-2xl sm:text-3xl text-on-surface leading-snug">
          {questionText}
        </h2>
      </div>

      {/* Likert Response Options */}
      <div className="grid gap-3.5 mb-8">
        {options.map((option, i) => (
          <button
            key={i}
            type="button"
            onClick={() => onAnswer(option.value)}
            className="w-full text-left p-4 sm:p-5 sketch-border bg-surface-container-low/70 hover:bg-primary-fixed/30 hover:border-primary transition-all duration-200 cursor-pointer flex items-center justify-between group"
          >
            <span className="font-headline-sm text-lg text-on-surface group-hover:text-primary">
              {option.label}
            </span>
            <span className="material-symbols-outlined text-outline group-hover:text-primary transition-colors text-xl">
              radio_button_unchecked
            </span>
          </button>
        ))}
      </div>

      {onBack && (
        <div className="flex justify-start">
          <button 
            type="button"
            onClick={onBack} 
            className="ink-wash-btn px-6 py-2 text-xl cursor-pointer"
          >
            Back
          </button>
        </div>
      )}
    </motion.div>
  );
}
