"use client";

import { motion } from "framer-motion";
import { useState } from "react";

interface IdentityStepProps {
  onNext: (identity: string) => void;
  onBack: () => void;
}

const personas = [
  { id: "school", title: "School Student", icon: "school", desc: "Exploring future horizons and possibilities" },
  { id: "college", title: "College Student", icon: "account_balance", desc: "Choosing a major and preparing for graduation" },
  { id: "professional", title: "Professional", icon: "work", desc: "Advancing within my current field and craft" },
  { id: "switcher", title: "Career Switcher", icon: "alt_route", desc: "Transitioning toward a completely new discipline" },
  { id: "lifelong", title: "Lifelong Scholar", icon: "menu_book", desc: "Pursuing self-directed intellectual mastery" },
];

export function IdentityStep({ onNext, onBack }: IdentityStepProps) {
  const [selected, setSelected] = useState<string | null>(null);

  return (
    <motion.div
      initial={{ opacity: 0, x: 20 }}
      animate={{ opacity: 1, x: 0 }}
      exit={{ opacity: 0, x: -20 }}
      transition={{ duration: 0.4 }}
      className="max-w-3xl mx-auto px-4 py-8"
    >
      <div className="mb-8 text-center">
        <span className="font-note-handwritten text-xl text-tertiary sketchy-chip px-3 py-1 mb-2 inline-block">
          Identity Calibration
        </span>
        <h2 className="font-headline-lg text-3xl sm:text-4xl text-on-surface mb-2">Who are you?</h2>
        <p className="font-body-md text-on-surface-variant max-w-md mx-auto">
          This anchors your learning companion to your current life stage.
        </p>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 mb-10">
        {personas.map((persona) => (
          <button
            key={persona.id}
            type="button"
            onClick={() => setSelected(persona.id)}
            className={`
              p-5 text-left transition-all duration-200 cursor-pointer flex items-start gap-4 sketch-border
              ${selected === persona.id 
                ? 'bg-primary-fixed/40 border-primary shadow-md scale-[1.02]' 
                : 'bg-surface-container-low/70 hover:bg-surface-container-high/60 border-[#424842]'
              }
            `}
          >
            <div className={`
              w-12 h-12 rounded-full flex items-center justify-center shrink-0 border
              ${selected === persona.id 
                ? 'bg-primary text-white border-primary-container' 
                : 'bg-surface-container text-secondary border-outline/30'}
            `}>
              <span className="material-symbols-outlined text-2xl">{persona.icon}</span>
            </div>
            <div>
              <h3 className="font-headline-sm text-lg text-on-surface mb-1">{persona.title}</h3>
              <p className="font-body-md text-sm text-on-surface-variant leading-snug">{persona.desc}</p>
            </div>
          </button>
        ))}
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
          disabled={!selected} 
          onClick={() => selected && onNext(selected)}
          className={`px-8 py-2.5 text-xl flex items-center gap-2 cursor-pointer ${
            selected ? 'ink-wash-btn-primary' : 'opacity-50 cursor-not-allowed bg-surface-dim border-2 border-outline text-outline'
          }`}
        >
          <span>Continue</span>
          <span className="material-symbols-outlined text-sm">east</span>
        </button>
      </div>
    </motion.div>
  );
}
