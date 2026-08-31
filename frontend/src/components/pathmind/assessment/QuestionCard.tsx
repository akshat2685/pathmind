"use client";

import { motion } from "framer-motion";
import { Button } from "@/components/ui/button";

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
      <div className="flex justify-between items-center mb-8 text-sm text-slate-500 font-medium">
        <span className="uppercase tracking-wider">{sectionName}</span>
        <span>{progress} of {total}</span>
      </div>

      <div className="mb-12">
        <h2 className="text-2xl sm:text-3xl font-medium tracking-tight text-slate-900 dark:text-white leading-relaxed">
          {questionText}
        </h2>
      </div>

      <div className="grid gap-3 mb-10">
        {options.map((option, i) => (
          <motion.button
            key={i}
            whileHover={{ scale: 1.01 }}
            whileTap={{ scale: 0.99 }}
            onClick={() => onAnswer(option.value)}
            className="w-full text-left p-5 rounded-2xl bg-white dark:bg-[#121214] border border-slate-200 dark:border-slate-800 hover:border-indigo-500 dark:hover:border-indigo-500 transition-all hover:shadow-[0_0_15px_-3px_rgba(99,102,241,0.2)] text-lg"
          >
            {option.label}
          </motion.button>
        ))}
      </div>

      {onBack && (
        <div className="flex justify-start">
          <Button variant="ghost" onClick={onBack} className="text-slate-500">
            Back
          </Button>
        </div>
      )}
    </motion.div>
  );
}
