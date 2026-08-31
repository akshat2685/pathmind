"use client";

import { motion } from "framer-motion";
import { useState } from "react";

interface IntroStepProps {
  onNext: (name: string) => void;
}

export function IntroStep({ onNext }: IntroStepProps) {
  const [name, setName] = useState("");
  const [touched, setTouched] = useState(false);

  const validation = name.trim().length >= 2;

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -10 }}
      transition={{ duration: 0.5, ease: "easeOut" }}
      className="flex flex-col items-center justify-center text-center max-w-2xl mx-auto px-4 py-8"
    >
      <div className="space-y-5">
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
          <span className="font-note-handwritten text-xl font-medium">Chapter I: The Initiation</span>
        </div>

        <h1 className="font-headline-lg text-4xl sm:text-5xl text-on-surface">
          Welcome to PATHMIND.<br />
          <span className="text-secondary italic">
            Let&apos;s start with your name.
          </span>
        </h1>
        
        <p className="font-body-md text-lg text-on-surface-variant max-w-lg mx-auto leading-relaxed">
          PATHMIND will scribe your longitudinal scholar profile and discover the right career trajectory — tailored entirely to you.
        </p>
      </div>

      <motion.div 
        className="mt-8 w-full max-w-md"
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ delay: 0.3, duration: 0.5 }}
      >
        <div className="mb-6 sketch-border p-5 bg-surface-container-low/90 text-left">
          <label className="font-label-md text-xs uppercase tracking-wider text-outline block mb-2">
            Your Name
          </label>
          <input
            type="text"
            value={name}
            onChange={(e) => {
              setName(e.target.value);
              if (!touched) setTouched(true);
            }}
            placeholder="Enter your name..."
            className="w-full hand-drawn-input px-2 py-1.5 text-xl"
            autoFocus
            onKeyDown={(e) => {
              if (e.key === "Enter" && validation) onNext(name.trim());
            }}
          />
          {touched && !validation && (
            <p className="text-xs text-error mt-2 font-body-md">
              Please enter at least 2 characters.
            </p>
          )}
        </div>

        <button 
          onClick={() => { if (validation) onNext(name.trim()); }}
          disabled={!validation}
          className={`w-full py-3 text-2xl flex items-center justify-center gap-3 cursor-pointer ${
            validation ? "ink-wash-btn-primary" : "opacity-40 cursor-not-allowed bg-surface-dim border-2 border-outline text-outline"
          }`}
        >
          <span>Begin My Journey</span>
          <span className="material-symbols-outlined text-lg">east</span>
        </button>
      </motion.div>
    </motion.div>
  );
}
