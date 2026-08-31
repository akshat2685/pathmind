"use client";

import { useState } from "react";
import { AnimatePresence } from "framer-motion";
import { QuestionCard } from "./QuestionCard";
import { CounselingDashboard } from "./CounselingDashboard";

const QUESTIONS = [
  { 
    id: "r1", 
    section: "RIASEC Interests", 
    text: "I like to build, repair, or engineer complex technical systems and tools.", 
    options: [
      { value: 1, label: "Strongly Dislike" }, 
      { value: 3, label: "Neutral / Ambivalent" }, 
      { value: 5, label: "Strongly Like & Enjoy" }
    ] 
  },
  { 
    id: "i1", 
    section: "RIASEC Interests", 
    text: "I like to analyze empirical data, discover patterns, and solve abstract problems.", 
    options: [
      { value: 1, label: "Strongly Dislike" }, 
      { value: 3, label: "Neutral / Ambivalent" }, 
      { value: 5, label: "Strongly Like & Enjoy" }
    ] 
  },
  { 
    id: "se1", 
    section: "Self Efficacy", 
    text: "How confident are you that you can master a difficult new domain through consistent deliberate practice?", 
    options: [
      { value: 1, label: "Unconfident" }, 
      { value: 3, label: "Somewhat Confident" }, 
      { value: 5, label: "Extremely Confident" }
    ] 
  },
];

export function AssessmentFlow() {
  const [currentIdx, setCurrentIdx] = useState(-1);
  const [responses, setResponses] = useState<Record<string, string | number>>({});
  const [isSynthesizing, setIsSynthesizing] = useState(false);
  const [profile, setProfile] = useState<Record<string, unknown> | null>(null);

  const handleStart = () => setCurrentIdx(0);

  const handleAnswer = async (value: string | number) => {
    const q = QUESTIONS[currentIdx];
    const newResponses = { ...responses, [q.id]: value };
    setResponses(newResponses);

    if (currentIdx < QUESTIONS.length - 1) {
      setCurrentIdx(currentIdx + 1);
    } else {
      setCurrentIdx(QUESTIONS.length);
      setIsSynthesizing(true);
      
      try {
        const baseUrl = process.env.NEXT_PUBLIC_API_BASE_URL || "https://pathmind-api.onrender.com";
        const res = await fetch(`${baseUrl}/api/counseling/synthesize`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            person_id: "demo-user",
            goals: ["Explore AI / ML engineering"],
            constraints: ["Needs fully remote"],
            evidence: [
              {
                source: "student",
                type: "self_report",
                description: "Built 4 mobile apps",
                confidence: "HIGH",
                timestamp: new Date().toISOString()
              }
            ],
            assessment_results: [
              {
                assessment_id: "demo-assessment-1",
                person_id: "demo-user",
                timestamp: new Date().toISOString(),
                schema_type: "RIASEC",
                raw_responses: newResponses,
                computed_scores: {}
              }
            ]
          })
        });

        if (!res.ok) {
          throw new Error("Backend synchronization failed.");
        }

        const data = await res.json();
        setProfile(data);
      } catch (err) {
        console.error(err);
        setProfile({
          error: {
            code: "SOURCE_UNAVAILABLE",
            message: "The ADK backend is currently unavailable or initializing."
          }
        });
      } finally {
        setIsSynthesizing(false);
      }
    }
  };

  const handleBack = () => {
    if (currentIdx > 0) setCurrentIdx(currentIdx - 1);
  };

  return (
    <div className="min-h-[75vh] flex items-center justify-center relative w-full">
      <AnimatePresence mode="wait">
        {currentIdx === -1 && (
          <div key="intro" className="text-center max-w-2xl px-4 py-8">
            <div className="inline-flex items-center gap-2 px-4 py-1.5 sketchy-chip text-tertiary mb-6">
              <span className="material-symbols-outlined text-lg" style={{ fontVariationSettings: "'FILL' 1" }}>
                psychology_alt
              </span>
              <span className="font-note-handwritten text-xl font-medium">Chapter III: Evidence Counseling</span>
            </div>
            
            <h1 className="font-headline-lg text-4xl sm:text-5xl text-on-surface mb-4">
              Evidence-Informed <br />
              <span className="text-secondary italic">Counseling Engine</span>
            </h1>
            
            <p className="font-body-md text-lg text-on-surface-variant mb-10 leading-relaxed max-w-lg mx-auto">
              Gather structured psychometric signals about your interests, self-efficacy, and learning patterns to generate an AI-synthesized career profile.
            </p>
            
            <button 
              onClick={handleStart} 
              className="ink-wash-btn-primary px-10 py-3 text-2xl flex items-center gap-3 mx-auto cursor-pointer"
            >
              <span>Begin Assessment</span>
              <span className="material-symbols-outlined text-lg">east</span>
            </button>
          </div>
        )}

        {currentIdx >= 0 && currentIdx < QUESTIONS.length && (
          <QuestionCard
            key={currentIdx}
            sectionName={QUESTIONS[currentIdx].section}
            questionText={QUESTIONS[currentIdx].text}
            options={QUESTIONS[currentIdx].options}
            progress={currentIdx + 1}
            total={QUESTIONS.length}
            onAnswer={handleAnswer}
            onBack={currentIdx > 0 ? handleBack : undefined}
          />
        )}

        {currentIdx === QUESTIONS.length && isSynthesizing && (
          <div key="synthesizing" className="text-center flex flex-col items-center py-16">
            <div className="w-16 h-16 rounded-full border-2 border-primary bg-primary/10 flex items-center justify-center mb-4">
              <span className="material-symbols-outlined text-3xl text-primary animate-spin">
                progress_activity
              </span>
            </div>
            <h2 className="font-headline-lg text-3xl text-on-surface mb-2">Synthesizing Profile...</h2>
            <p className="font-note-handwritten text-2xl text-on-surface-variant">The ADK Counseling agent is evaluating evidence and psychometrics.</p>
          </div>
        )}

        {currentIdx === QUESTIONS.length && !isSynthesizing && profile && (
          <CounselingDashboard key="dashboard" profile={profile} />
        )}
      </AnimatePresence>
    </div>
  );
}
