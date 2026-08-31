"use client";

import { useState } from "react";
import { AnimatePresence } from "framer-motion";
import { Sidebar } from "@/components/layout/Sidebar";
import { TopBar } from "@/components/layout/TopBar";
import { IntroStep } from "./steps/IntroStep";
import { IdentityStep } from "./steps/IdentityStep";
import { GoalStep } from "./steps/GoalStep";
import { EvidenceStep, EvidenceItem } from "./steps/EvidenceStep";
import { SynthesisStep } from "./steps/SynthesisStep";

export function OnboardingFlow() {
  const [step, setStep] = useState(0);
  
  // State to hold collected user data
  const [identity, setIdentity] = useState<string>("");
  const [goal, setGoal] = useState<string>("");
  const [evidence, setEvidence] = useState<EvidenceItem[]>([]);

  const nextStep = () => setStep((s) => s + 1);
  const prevStep = () => setStep((s) => Math.max(0, s - 1));

  return (
    <div className="flex min-h-screen bg-surface">
      <Sidebar />
      <div className="flex-1 flex flex-col min-w-0 md:ml-72">
        <TopBar />
        <main className="flex-1 flex items-center justify-center p-6 md:p-12 relative z-10">
          <div className="w-full max-w-3xl mx-auto">
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
                  onNext={(evList) => {
                    setEvidence(evList);
                    nextStep();
                  }}
                  onBack={prevStep}
                />
              )}

              {step === 4 && (
                <SynthesisStep 
                  key="synthesis"
                  identity={identity}
                  goal={goal}
                  evidence={evidence}
                />
              )}
            </AnimatePresence>
          </div>
        </main>
      </div>
    </div>
  );
}
