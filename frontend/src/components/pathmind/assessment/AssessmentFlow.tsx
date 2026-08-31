"use client";

import { useState } from "react";
import { AnimatePresence } from "framer-motion";
import { QuestionCard } from "./QuestionCard";
import { CounselingDashboard } from "./CounselingDashboard";

// Standardized Holland RIASEC & SCCT Items for Strict Psychometric Evaluation
const QUESTIONS = [
  { 
    id: "r1", 
    section: "RIASEC: Realistic (R)", 
    text: "I enjoy building, repairing, or engineering concrete technical systems and physical/hardware components.", 
    options: [
      { value: 1, label: "1 — Strongly Dislike / Not Me" }, 
      { value: 2, label: "2 — Slight Disinterest" },
      { value: 3, label: "3 — Neutral / Ambivalent" }, 
      { value: 4, label: "4 — Moderate Interest" },
      { value: 5, label: "5 — Strongly Like & Enjoy" }
    ] 
  },
  { 
    id: "i1", 
    section: "RIASEC: Investigative (I)", 
    text: "I enjoy analyzing abstract datasets, formulating hypotheses, and solving algorithmic problems.", 
    options: [
      { value: 1, label: "1 — Strongly Dislike / Not Me" }, 
      { value: 2, label: "2 — Slight Disinterest" },
      { value: 3, label: "3 — Neutral / Ambivalent" }, 
      { value: 4, label: "4 — Moderate Interest" },
      { value: 5, label: "5 — Strongly Like & Enjoy" }
    ] 
  },
  { 
    id: "a1", 
    section: "RIASEC: Artistic (A)", 
    text: "I enjoy designing intuitive visual interfaces, creative workflows, and aesthetic human-computer experiences.", 
    options: [
      { value: 1, label: "1 — Strongly Dislike / Not Me" }, 
      { value: 2, label: "2 — Slight Disinterest" },
      { value: 3, label: "3 — Neutral / Ambivalent" }, 
      { value: 4, label: "4 — Moderate Interest" },
      { value: 5, label: "5 — Strongly Like & Enjoy" }
    ] 
  },
  { 
    id: "s1", 
    section: "RIASEC: Social (S)", 
    text: "I enjoy mentoring team members, teaching technical concepts, and collaborating to resolve people challenges.", 
    options: [
      { value: 1, label: "1 — Strongly Dislike / Not Me" }, 
      { value: 2, label: "2 — Slight Disinterest" },
      { value: 3, label: "3 — Neutral / Ambivalent" }, 
      { value: 4, label: "4 — Moderate Interest" },
      { value: 5, label: "5 — Strongly Like & Enjoy" }
    ] 
  },
  { 
    id: "e1", 
    section: "RIASEC: Enterprising (E)", 
    text: "I enjoy pitching product strategy, taking ownership of business milestones, and persuading stakeholders.", 
    options: [
      { value: 1, label: "1 — Strongly Dislike / Not Me" }, 
      { value: 2, label: "2 — Slight Disinterest" },
      { value: 3, label: "3 — Neutral / Ambivalent" }, 
      { value: 4, label: "4 — Moderate Interest" },
      { value: 5, label: "5 — Strongly Like & Enjoy" }
    ] 
  },
  { 
    id: "c1", 
    section: "RIASEC: Conventional (C)", 
    text: "I enjoy enforcing structured protocols, schema validations, and detail-oriented data governance.", 
    options: [
      { value: 1, label: "1 — Strongly Dislike / Not Me" }, 
      { value: 2, label: "2 — Slight Disinterest" },
      { value: 3, label: "3 — Neutral / Ambivalent" }, 
      { value: 4, label: "4 — Moderate Interest" },
      { value: 5, label: "5 — Strongly Like & Enjoy" }
    ] 
  },
  { 
    id: "se1", 
    section: "SCCT: Self-Efficacy", 
    text: "How confident are you in your ability to learn difficult technical foundations through disciplined practice?", 
    options: [
      { value: 1, label: "1 — Very Low Confidence" }, 
      { value: 2, label: "2 — Low Confidence" },
      { value: 3, label: "3 — Moderate Confidence" }, 
      { value: 4, label: "4 — High Confidence" },
      { value: 5, label: "5 — Extremely High Confidence" }
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
        
        // Calculate scores strictly
        const computedScores = {
          R: Number(newResponses["r1"] || 0),
          I: Number(newResponses["i1"] || 0),
          A: Number(newResponses["a1"] || 0),
          S: Number(newResponses["s1"] || 0),
          E: Number(newResponses["e1"] || 0),
          C: Number(newResponses["c1"] || 0),
          SelfEfficacy: Number(newResponses["se1"] || 0)
        };

        const res = await fetch(`${baseUrl}/api/counseling/synthesize`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            person_id: "scholar-candidate",
            goals: ["Master AI / Machine Learning and Systems Engineering"],
            constraints: ["Requires strictly grounded evidence"],
            evidence: [], // Strict: No assumed evidence provided unless uploaded by candidate
            assessment_results: [
              {
                assessment_id: "riasec-scct-comprehensive-v1",
                person_id: "scholar-candidate",
                timestamp: new Date().toISOString(),
                schema_type: "RIASEC_SCCT",
                raw_responses: newResponses,
                computed_scores: computedScores
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
            message: "The strict ADK counseling backend is initializing."
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
              <span className="font-note-handwritten text-xl font-medium">Chapter III: Strict Psychometrics</span>
            </div>
            
            <h1 className="font-headline-lg text-4xl sm:text-5xl text-on-surface mb-4">
              Evidence-Informed <br />
              <span className="text-secondary italic">Psychometric Engine</span>
            </h1>
            
            <p className="font-body-md text-lg text-on-surface-variant mb-4 leading-relaxed max-w-lg mx-auto">
              Evaluates your true Holland RIASEC interests and SCCT self-efficacy strictly without bias or flattering assumptions.
            </p>

            <div className="p-4 mb-8 sketch-border-subtle bg-surface-container-low/70 max-w-md mx-auto text-left">
              <div className="flex items-center gap-2 text-primary font-headline-sm text-base mb-1">
                <span className="material-symbols-outlined text-lg">verified_user</span>
                <span>Zero-Assumption Rule</span>
              </div>
              <p className="font-note-handwritten text-lg text-on-surface-variant leading-snug">
                The agent will not assume past project achievements unless verified by portfolio artifacts.
              </p>
            </div>
            
            <button 
              onClick={handleStart} 
              className="ink-wash-btn-primary px-10 py-3 text-2xl flex items-center gap-3 mx-auto cursor-pointer"
            >
              <span>Begin Psychometric Assessment</span>
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
            <h2 className="font-headline-lg text-3xl text-on-surface mb-2">Executing Psychometric Synthesis...</h2>
            <p className="font-note-handwritten text-2xl text-on-surface-variant">Calibrating Holland Code congruence and checking evidence gaps.</p>
          </div>
        )}

        {currentIdx === QUESTIONS.length && !isSynthesizing && profile && (
          <CounselingDashboard key="dashboard" profile={profile} />
        )}
      </AnimatePresence>
    </div>
  );
}
