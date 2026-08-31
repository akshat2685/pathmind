"use client";

import { useState } from "react";
import { AnimatePresence } from "framer-motion";
import { IntroStep } from "./steps/IntroStep";
import { IdentityStep } from "./steps/IdentityStep";
import { GoalStep } from "./steps/GoalStep";
import { EvidenceStep } from "./steps/EvidenceStep";
import { SynthesisStep } from "./steps/SynthesisStep";

export function OnboardingFlow() {
  const [step, setStep] = useState(0);
  
  // State to hold collected user data
  const [identity, setIdentity] = useState<string>("");
  const [goal, setGoal] = useState<string>("");

  const nextStep = () => setStep((s) => s + 1);
  const prevStep = () => setStep((s) => Math.max(0, s - 1));

  return (
    <div className="min-h-screen flex items-center justify-center bg-[#fafafa] dark:bg-[#09090b] selection:bg-indigo-500/30">
      {/* Background ambient lighting */}
      <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[600px] h-[600px] bg-indigo-500/10 dark:bg-indigo-500/5 rounded-full blur-3xl pointer-events-none"></div>
      
      <div className="w-full relative z-10">
        <AnimatePresence mode="wait">
          {step === 0 && (
            <IntroStep key="intro" onNext={nextStep} />
          )}
          
          {step === 1 && (
            <IdentityStep 
              key="identity" 
              onNext={(id) => {
                setIdentity(id);
                nextStep();
              }} 
              onBack={prevStep} 
            />
          )}

          {step === 2 && (
            <GoalStep 
              key="goal"
              onNext={(g) => {
                setGoal(g);
                nextStep();
              }}
              onBack={prevStep}
            />
          )}

          {step === 3 && (
            <EvidenceStep 
              key="evidence"
              onNext={nextStep}
              onBack={prevStep}
            />
          )}

          {step === 4 && (
            <SynthesisStep 
              key="synthesis"
              identity={identity}
              goal={goal}
            />
          )}
        </AnimatePresence>
      </div>
    </div>
  );
}
