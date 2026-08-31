"use client";

import { useState, useEffect, useRef } from "react";
import { AnimatePresence } from "framer-motion";
import { QuestionCard } from "./QuestionCard";
import { CounselingDashboard } from "./CounselingDashboard";
import { EvidenceItem } from "@/components/pathmind/steps/EvidenceStep";

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
  
  // Real User Data from Onboarding (pulled from localStorage)
  const [userName, setUserName] = useState<string>("");
  const [userIdentity, setUserIdentity] = useState<string>("");
  const [userGoal, setUserGoal] = useState<string>("");

  // Real User Evidence State
  const [evidenceList, setEvidenceList] = useState<EvidenceItem[]>([]);
  const [showEvidenceDrawer, setShowEvidenceDrawer] = useState(false);
  const [portfolioLink, setPortfolioLink] = useState("");
  const fileInputRef = useRef<HTMLInputElement>(null);

  // Load all user data from localStorage on mount
  useEffect(() => {
    if (typeof window !== "undefined") {
      try {
        const stored = localStorage.getItem("pathmind_user_evidence");
        if (stored) setEvidenceList(JSON.parse(stored));
      } catch { /* ignore */ }
      setUserName(localStorage.getItem("pathmind_user_name") || "");
      setUserIdentity(localStorage.getItem("pathmind_user_identity") || "");
      setUserGoal(localStorage.getItem("pathmind_user_goal") || "");
    }
  }, []);

  const handleFileUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (!e.target.files || e.target.files.length === 0) return;
    const files = Array.from(e.target.files);
    const newItems: EvidenceItem[] = files.map((file) => ({
      source: "candidate_upload",
      type: "file",
      name: file.name,
      description: `Uploaded file (${(file.size / 1024).toFixed(1)} KB, type: ${file.type || "document"})`,
      confidence: "HIGH",
      timestamp: new Date().toISOString()
    }));

    const updated = [...evidenceList, ...newItems];
    setEvidenceList(updated);
    if (typeof window !== "undefined") {
      localStorage.setItem("pathmind_user_evidence", JSON.stringify(updated));
    }
  };

  const handleAddLink = (e: React.FormEvent) => {
    e.preventDefault();
    if (!portfolioLink.trim()) return;

    const newItem: EvidenceItem = {
      source: "candidate_portfolio_link",
      type: "link",
      name: portfolioLink.trim(),
      description: `Portfolio URL / Code Repository: ${portfolioLink.trim()}`,
      url: portfolioLink.trim(),
      confidence: "HIGH",
      timestamp: new Date().toISOString()
    };

    const updated = [...evidenceList, newItem];
    setEvidenceList(updated);
    setPortfolioLink("");
    if (typeof window !== "undefined") {
      localStorage.setItem("pathmind_user_evidence", JSON.stringify(updated));
    }
  };

  const handleRemoveEvidence = (idx: number) => {
    const updated = evidenceList.filter((_, i) => i !== idx);
    setEvidenceList(updated);
    if (typeof window !== "undefined") {
      localStorage.setItem("pathmind_user_evidence", JSON.stringify(updated));
    }
  };

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

        // Build dynamic user context — entirely from what the user provided
        const personId = userName ? userName.toLowerCase().replace(/\s+/g, "-") : "anonymous-scholar";
        const goals = userGoal ? [userGoal] : [];
        const constraints = userIdentity ? [`Life stage: ${userIdentity}`] : [];

        const res = await fetch(`${baseUrl}/api/counseling/synthesize`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            person_id: personId,
            goals,
            constraints,
            evidence: evidenceList, // user-supplied (empty array if none uploaded)
            assessment_results: [
              {
                assessment_id: "riasec-scct-comprehensive-v1",
                person_id: personId,
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
            code: "CONNECTION_ERROR",
            message: "We could not reach the counseling service. Please check your connection and try again."
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
              <span className="font-note-handwritten text-xl font-medium">
                {userName ? `${userName}'s Assessment` : "Psychometric Assessment"}
              </span>
            </div>
            
            <h1 className="font-headline-lg text-4xl sm:text-5xl text-on-surface mb-4">
              {userName ? `Welcome, ${userName}` : "Career Assessment"}<br />
              <span className="text-secondary italic">Let&apos;s find your path</span>
            </h1>
            
            {userGoal && (
              <div className="mb-4 px-4 py-3 sketch-border bg-surface-container-low/80 text-left">
                <span className="font-label-md text-xs uppercase tracking-wider text-outline block mb-1">Your stated goal</span>
                <p className="font-note-handwritten text-xl text-on-surface">&ldquo;{userGoal}&rdquo;</p>
              </div>
            )}

            <p className="font-body-md text-lg text-on-surface-variant mb-6 leading-relaxed max-w-lg mx-auto">
              Answer each question honestly. Your results are used to give you a personalized, evidence-grounded career assessment.
            </p>

            {/* Evidence Quick Panel */}
            <div className="mb-8 p-5 sketch-border bg-surface-container-low/90 text-left">
              <div className="flex items-center justify-between flex-wrap gap-2 mb-3">
                <span className="font-headline-sm text-base text-on-surface flex items-center gap-2">
                  <span className="material-symbols-outlined text-primary text-xl">folder_shared</span>
                  <span>Attached Evidence &amp; Portfolios ({evidenceList.length})</span>
                </span>
                <button
                  type="button"
                  onClick={() => setShowEvidenceDrawer(!showEvidenceDrawer)}
                  className="font-note-handwritten text-lg text-primary hover:underline cursor-pointer"
                >
                  {showEvidenceDrawer ? "Hide Upload Panel" : "+ Attach Portfolio / Links"}
                </button>
              </div>

              {showEvidenceDrawer && (
                <div className="pt-3 border-t border-outline-variant/30 space-y-3">
                  <input
                    type="file"
                    multiple
                    ref={fileInputRef}
                    onChange={handleFileUpload}
                    accept=".pdf,.doc,.docx,.txt,.md,.json,.zip"
                    className="hidden"
                  />
                  <div className="flex gap-2">
                    <button
                      type="button"
                      onClick={() => fileInputRef.current?.click()}
                      className="ink-wash-btn px-4 py-1.5 text-base flex items-center gap-1.5"
                    >
                      <span className="material-symbols-outlined text-sm">upload_file</span>
                      <span>Upload Files</span>
                    </button>
                  </div>
                  <form onSubmit={handleAddLink} className="flex gap-2">
                    <input
                      type="url"
                      value={portfolioLink}
                      onChange={(e) => setPortfolioLink(e.target.value)}
                      placeholder="https://github.com/... or portfolio URL"
                      className="flex-1 hand-drawn-input px-2 py-1 text-sm"
                    />
                    <button type="submit" className="ink-wash-btn-primary px-4 py-1 text-base">
                      Add Link
                    </button>
                  </form>
                </div>
              )}

              {evidenceList.length > 0 ? (
                <div className="space-y-2 mt-3 pt-2 border-t border-outline-variant/20">
                  {evidenceList.map((item, idx) => (
                    <div key={idx} className="flex items-center justify-between text-xs bg-surface-container/60 p-2 rounded">
                      <span className="truncate font-medium">{item.name}</span>
                      <button
                        type="button"
                        onClick={() => handleRemoveEvidence(idx)}
                        className="text-error ml-2 hover:underline"
                      >
                        Remove
                      </button>
                    </div>
                  ))}
                </div>
              ) : (
                <p className="font-note-handwritten text-base text-tertiary mt-1">
                  Zero evidence attached. The counseling agent will enforce strict zero-assumption policy.
                </p>
              )}
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
