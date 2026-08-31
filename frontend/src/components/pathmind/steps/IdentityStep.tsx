"use client";

import { motion } from "framer-motion";
import { Button } from "@/components/ui/button";
import { GraduationCap, Briefcase, RefreshCw, BookOpen, User } from "lucide-react";
import { useState } from "react";

interface IdentityStepProps {
  onNext: (identity: string) => void;
  onBack: () => void;
}

const personas = [
  { id: "school", title: "School Student", icon: User, desc: "Exploring future possibilities" },
  { id: "college", title: "College Student", icon: GraduationCap, desc: "Choosing a major and preparing for graduation" },
  { id: "professional", title: "Professional", icon: Briefcase, desc: "Advancing in my current career track" },
  { id: "switcher", title: "Career Switcher", icon: RefreshCw, desc: "Transitioning to a new field" },
  { id: "lifelong", title: "Lifelong Learner", icon: BookOpen, desc: "Learning for personal growth" },
];

export function IdentityStep({ onNext, onBack }: IdentityStepProps) {
  const [selected, setSelected] = useState<string | null>(null);

  const container = {
    hidden: { opacity: 0 },
    show: {
      opacity: 1,
      transition: { staggerChildren: 0.1 }
    }
  };

  const item = {
    hidden: { opacity: 0, y: 10 },
    show: { opacity: 1, y: 0, transition: { duration: 0.4 } }
  };

  return (
    <motion.div
      initial={{ opacity: 0, x: 20 }}
      animate={{ opacity: 1, x: 0 }}
      exit={{ opacity: 0, x: -20 }}
      transition={{ duration: 0.4 }}
      className="max-w-3xl mx-auto px-4 py-8"
    >
      <div className="mb-10 text-center">
        <h2 className="text-3xl font-medium tracking-tight mb-3">Who are you?</h2>
        <p className="text-slate-500 dark:text-slate-400">
          This helps PATHMIND contextualize your trajectory.
        </p>
      </div>

      <motion.div 
        variants={container} 
        initial="hidden" 
        animate="show"
        className="grid grid-cols-1 sm:grid-cols-2 gap-4 mb-12"
      >
        {personas.map((persona) => (
          <motion.button
            key={persona.id}
            variants={item}
            onClick={() => setSelected(persona.id)}
            className={`
              glass-card p-6 text-left rounded-2xl flex items-start gap-4 transition-all duration-300
              ${selected === persona.id 
                ? 'ring-2 ring-indigo-500 bg-indigo-500/10 shadow-[0_0_20px_-5px_rgba(99,102,241,0.3)]' 
                : 'hover:bg-slate-50 dark:hover:bg-slate-800/50 hover:ring-1 hover:ring-indigo-500/30'
              }
            `}
          >
            <div className={`
              p-3 rounded-xl
              ${selected === persona.id ? 'bg-indigo-500 text-white' : 'bg-slate-100 dark:bg-slate-800 text-slate-500 dark:text-slate-400'}
            `}>
              <persona.icon className="w-6 h-6" />
            </div>
            <div>
              <h3 className="font-medium text-slate-900 dark:text-white text-lg">{persona.title}</h3>
              <p className="text-sm text-slate-500 dark:text-slate-400 mt-1">{persona.desc}</p>
            </div>
          </motion.button>
        ))}
      </motion.div>

      <div className="flex justify-between items-center">
        <Button variant="ghost" onClick={onBack} className="text-slate-500">Back</Button>
        <Button 
          disabled={!selected} 
          onClick={() => selected && onNext(selected)}
          className="bg-indigo-600 hover:bg-indigo-500 min-w-[120px] rounded-full"
        >
          Continue
        </Button>
      </div>
    </motion.div>
  );
}
