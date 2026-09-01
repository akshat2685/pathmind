"use client";

import { useState, useEffect } from "react";
import { motion } from "framer-motion";

interface QuestionCardProps {
  questionText: string;
  responseType?: "likert" | "open" | "task";
  options?: { value: string | number; label: string }[];
  currentValue?: string | number;
  expectedCapability?: string;
  onAnswer: (value: string | number) => void;
  onBack?: () => void;
  progress: number;
  total: number;
  sectionName: string;
}

export function QuestionCard({
  questionText,
  responseType = "likert",
  options = [],
  currentValue,
  expectedCapability,
  onAnswer,
  onBack,
  progress,
  total,
  sectionName
}: QuestionCardProps) {
  const [openText, setOpenText] = useState<string>("");

  useEffect(() => {
    if (currentValue !== undefined && currentValue !== null) {
      setOpenText(String(currentValue));
    } else {
      setOpenText("");
    }
  }, [questionText, currentValue]);

  const handleOpenSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!openText.trim()) return;
    onAnswer(openText.trim());
  };

  return (
    <motion.div
      key={questionText}
      initial={{ opacity: 0, x: 20 }}
      animate={{ opacity: 1, x: 0 }}
      exit={{ opacity: 0, x: -20 }}
      transition={{ duration: 0.3 }}
      className="max-w-2xl mx-auto px-4 py-8 w-full"
    >
      {/* Progress & Section Badge */}
      <div className="flex justify-between items-center mb-4 text-sm flex-wrap gap-2">
        <span className="font-note-handwritten text-xl text-tertiary sketchy-chip px-3 py-1 bg-surface-container-low">
          {sectionName}
        </span>
        <span className="font-headline-sm text-sm text-on-surface-variant font-medium">
          Step {progress} of {total}
        </span>
      </div>

      {/* Progress Ink Bar */}
      <div className="w-full bg-surface-container h-2 rounded-full mb-6 overflow-hidden border border-outline-variant/50">
        <div 
          className="bg-primary h-full transition-all duration-500 rounded-full"
          style={{ width: `${(progress / total) * 100}%` }}
        />
      </div>

      {/* Question Prompt */}
      <div className="mb-6 p-6 sketch-border bg-surface-container-low/95 shadow-sm">
        <h2 className="font-headline-lg text-2xl sm:text-3xl text-on-surface leading-snug">
          {questionText}
        </h2>
        {expectedCapability && (
          <p className="mt-2 text-xs font-note-handwritten text-on-surface-variant italic">
            Observed Dimension: {expectedCapability}
          </p>
        )}
      </div>

      {/* Response Area: Likert vs Open/Task */}
      {responseType === "likert" && options.length > 0 ? (
        <div className="grid gap-3.5 mb-8">
          {options.map((option, i) => {
            const isSelected = currentValue !== undefined && String(currentValue) === String(option.value);
            return (
              <button
                key={i}
                type="button"
                onClick={() => onAnswer(option.value)}
                className={`w-full text-left p-4 sm:p-5 sketch-border transition-all duration-200 cursor-pointer flex items-center justify-between group ${
                  isSelected 
                    ? "bg-primary-fixed/40 border-primary" 
                    : "bg-surface-container-low/70 hover:bg-primary-fixed/20 hover:border-primary/60"
                }`}
              >
                <span className={`font-headline-sm text-base sm:text-lg ${isSelected ? "text-primary font-bold" : "text-on-surface group-hover:text-primary"}`}>
                  {option.label}
                </span>
                <span className={`material-symbols-outlined transition-colors text-xl ${isSelected ? "text-primary" : "text-outline group-hover:text-primary"}`}>
                  {isSelected ? "check_circle" : "radio_button_unchecked"}
                </span>
              </button>
            );
          })}
        </div>
      ) : (
        <form onSubmit={handleOpenSubmit} className="mb-8 space-y-4">
          <textarea
            value={openText}
            onChange={(e) => setOpenText(e.target.value)}
            placeholder="Type your explanation or response here in your own words..."
            rows={4}
            className="w-full hand-drawn-input p-4 text-base font-body-md text-on-surface bg-surface-container-low/80 border border-outline-variant focus:border-primary focus:outline-none rounded-lg"
          />
          <div className="flex justify-end">
            <button
              type="submit"
              disabled={!openText.trim()}
              className="ink-wash-btn-primary px-8 py-2 text-lg flex items-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              <span>Record Response</span>
              <span className="material-symbols-outlined text-sm">arrow_forward</span>
            </button>
          </div>
        </form>
      )}

      {/* Back Navigation */}
      {onBack && (
        <div className="flex justify-start">
          <button 
            type="button"
            onClick={onBack} 
            className="ink-wash-btn px-6 py-2 text-lg cursor-pointer flex items-center gap-1"
          >
            <span className="material-symbols-outlined text-sm">arrow_back</span>
            <span>Back</span>
          </button>
        </div>
      )}
    </motion.div>
  );
}
