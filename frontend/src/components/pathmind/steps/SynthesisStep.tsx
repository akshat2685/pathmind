"use client";

import { motion } from "framer-motion";
import { Button } from "@/components/ui/button";
import { useState, useEffect } from "react";
import { Sparkles, ArrowRight } from "lucide-react";
import { useRouter } from "next/navigation";

interface SynthesisStepProps {
  identity: string;
  goal: string;
}

export function SynthesisStep({ identity, goal }: SynthesisStepProps) {
  const [isSynthesizing, setIsSynthesizing] = useState(true);
  const router = useRouter();

  useEffect(() => {
    // Simulate ADK reasoning time
    const timer = setTimeout(() => {
      setIsSynthesizing(false);
    }, 3000);
    return () => clearTimeout(timer);
  }, []);

  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.95 }}
      animate={{ opacity: 1, scale: 1 }}
      transition={{ duration: 0.5 }}
      className="max-w-3xl mx-auto px-4 py-8"
    >
      {isSynthesizing ? (
        <div className="flex flex-col items-center justify-center min-h-[40vh] space-y-8">
          <div className="relative">
            <div className="absolute inset-0 bg-indigo-500 blur-xl opacity-30 animate-pulse rounded-full"></div>
            <div className="relative bg-white dark:bg-[#0c0c0e] p-6 rounded-full border border-slate-200 dark:border-slate-800 shadow-sm">
              <Sparkles className="w-8 h-8 text-indigo-500 animate-bounce" />
            </div>
          </div>
          <div className="text-center">
            <h2 className="text-2xl font-medium tracking-tight mb-2">Synthesizing your profile</h2>
            <p className="text-slate-500 dark:text-slate-400">Extracting context, mapping trajectories, and finding paths...</p>
          </div>
        </div>
      ) : (
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6 }}
        >
          <div className="mb-10 text-center">
            <div className="inline-flex items-center justify-center p-3 bg-emerald-500/10 text-emerald-600 rounded-full mb-6 ring-1 ring-emerald-500/20">
              <Sparkles className="w-6 h-6" />
            </div>
            <h2 className="text-3xl font-medium tracking-tight mb-3">Profile Synthesized</h2>
            <p className="text-slate-500 dark:text-slate-400">
              Here is what PATHMIND understands about you.
            </p>
          </div>

          <div className="glass-card rounded-2xl p-8 mb-10 space-y-8">
            <div>
              <h3 className="text-sm font-semibold uppercase tracking-wider text-slate-400 mb-3">Context</h3>
              <p className="text-lg text-slate-900 dark:text-slate-100 capitalize font-medium">{identity.replace("-", " ")}</p>
            </div>
            
            <div>
              <h3 className="text-sm font-semibold uppercase tracking-wider text-slate-400 mb-3">Goal</h3>
              <p className="text-lg text-slate-900 dark:text-slate-100 leading-relaxed italic border-l-2 border-indigo-500/50 pl-4">
                &quot;{goal}&quot;
              </p>
            </div>
            
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-6 pt-4 border-t border-slate-200 dark:border-slate-800">
              <div>
                <h3 className="text-sm font-semibold uppercase tracking-wider text-slate-400 mb-3">Identified Strengths</h3>
                <div className="flex flex-wrap gap-2">
                  <span className="px-3 py-1 bg-slate-100 dark:bg-slate-800 rounded-full text-sm">Self-directed</span>
                  <span className="px-3 py-1 bg-slate-100 dark:bg-slate-800 rounded-full text-sm">Ambitious</span>
                  <span className="px-3 py-1 bg-slate-100 dark:bg-slate-800 rounded-full text-sm">Analytical</span>
                </div>
              </div>
              <div>
                <h3 className="text-sm font-semibold uppercase tracking-wider text-slate-400 mb-3">Open Questions</h3>
                <p className="text-sm text-slate-600 dark:text-slate-400">We will need to evaluate your current technical foundation in upcoming stages.</p>
              </div>
            </div>
          </div>

          <div className="flex justify-center">
            <Button 
              size="lg"
              onClick={() => router.push("/")}
              className="bg-indigo-600 hover:bg-indigo-500 rounded-full px-8 gap-2 text-base shadow-[0_0_20px_-5px_rgba(99,102,241,0.4)] hover:shadow-[0_0_25px_-5px_rgba(99,102,241,0.5)]"
            >
              Enter PATHMIND
              <ArrowRight className="w-4 h-4" />
            </Button>
          </div>
        </motion.div>
      )}
    </motion.div>
  );
}
