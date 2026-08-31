"use client";

import { useState } from "react";
import { AnimatePresence } from "framer-motion";
import { QuestionCard } from "./QuestionCard";
import { CounselingDashboard } from "./CounselingDashboard";
import { Loader2 } from "lucide-react";

// Mocking the questions for the frontend MVP demo
const QUESTIONS = [
  { id: "r1", section: "RIASEC Interests", text: "I like to build, repair, or maintain things.", options: [{value: 1, label: "Strongly Dislike"}, {value: 3, label: "Neutral"}, {value: 5, label: "Strongly Like"}] },
  { id: "i1", section: "RIASEC Interests", text: "I like to analyze data and solve complex problems.", options: [{value: 1, label: "Strongly Dislike"}, {value: 3, label: "Neutral"}, {value: 5, label: "Strongly Like"}] },
  { id: "se1", section: "Self Efficacy", text: "How confident are you that you can learn a difficult subject if you practice consistently?", options: [{value: 1, label: "Not Confident"}, {value: 3, label: "Somewhat Confident"}, {value: 5, label: "Very Confident"}] },
];

export function AssessmentFlow() {
  const [currentIdx, setCurrentIdx] = useState(-1); // -1 = Intro
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
      // Done with questions, trigger synthesis
      setCurrentIdx(QUESTIONS.length);
      setIsSynthesizing(true);
      
      try {
        const baseUrl = process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000";
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
            message: "The ADK backend is currently unavailable."
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
    <div className="min-h-[80vh] flex items-center justify-center relative">
      <AnimatePresence mode="wait">
        {currentIdx === -1 && (
          <div key="intro" className="text-center max-w-2xl px-4">
            <h1 className="text-4xl font-medium tracking-tight mb-4">Evidence-Informed Counseling</h1>
            <p className="text-lg text-slate-500 mb-8">
              Let&apos;s gather some structured signals about your interests, self-efficacy, and learning patterns.
            </p>
            <button onClick={handleStart} className="px-8 py-3 bg-indigo-600 hover:bg-indigo-500 text-white rounded-full font-medium transition-all shadow-[0_0_20px_-5px_rgba(99,102,241,0.4)]">
              Begin Assessment
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
          <div key="synthesizing" className="text-center flex flex-col items-center">
            <Loader2 className="w-10 h-10 text-indigo-500 animate-spin mb-4" />
            <h2 className="text-2xl font-medium">Synthesizing Profile...</h2>
            <p className="text-slate-500 mt-2">The ADK Counseling agent is evaluating evidence.</p>
          </div>
        )}

        {currentIdx === QUESTIONS.length && !isSynthesizing && profile && (
          <CounselingDashboard key="dashboard" profile={profile} />
        )}
      </AnimatePresence>
    </div>
  );
}
