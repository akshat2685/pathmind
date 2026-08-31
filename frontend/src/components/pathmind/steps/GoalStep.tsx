"use client";

import { motion } from "framer-motion";
import { Button } from "@/components/ui/button";
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
      <div className="mb-10">
        <h2 className="text-3xl font-medium tracking-tight mb-3">What are you trying to achieve?</h2>
        <p className="text-slate-500 dark:text-slate-400">
          Be as specific or as broad as you like. We will refine this together.
        </p>
      </div>

      <div className="mb-12 relative group">
        <div className="absolute -inset-0.5 bg-gradient-to-r from-indigo-500 to-violet-500 rounded-2xl blur opacity-20 group-focus-within:opacity-40 transition duration-500"></div>
        <textarea
          value={goal}
          onChange={(e) => setGoal(e.target.value)}
          placeholder="e.g., I want to transition into UX design without going back to college, but I don't know where to start."
          className="relative w-full h-48 bg-white dark:bg-[#0c0c0e] rounded-2xl p-6 text-lg border border-slate-200 dark:border-slate-800 focus:outline-none focus:ring-2 focus:ring-indigo-500/50 resize-none text-slate-900 dark:text-slate-100 placeholder:text-slate-400 dark:placeholder:text-slate-600 transition-all shadow-sm"
        />
        <div className="absolute bottom-4 right-6 text-sm text-slate-400">
          {goal.length} chars
        </div>
      </div>

      <div className="flex justify-between items-center">
        <Button variant="ghost" onClick={onBack} className="text-slate-500">Back</Button>
        <Button 
          disabled={goal.trim().length < 5} 
          onClick={() => onNext(goal)}
          className="bg-indigo-600 hover:bg-indigo-500 min-w-[120px] rounded-full"
        >
          Continue
        </Button>
      </div>
    </motion.div>
  );
}
