"use client";

import { useState, useEffect, useRef } from "react";
import { AnimatePresence } from "framer-motion";
import { QuestionCard } from "./QuestionCard";
import { CounselingDashboard } from "./CounselingDashboard";
import { EvidenceItem } from "@/components/pathmind/steps/EvidenceStep";

interface AssessmentItemDef {
  id: string;
  section: string;
  construct: string;
  text: string;
  responseType: "likert" | "open" | "task";
  options?: { value: string | number; label: string }[];
  expectedCapability?: string;
}

const LIKERT_SCALE = [
  { value: 1, label: "1 — Strongly Dislike / Not Confident" },
  { value: 2, label: "2 — Slight Disinterest / Low" },
  { value: 3, label: "3 — Neutral / Moderate" },
  { value: 4, label: "4 — Interest / High Confidence" },
  { value: 5, label: "5 — Strongly Like / Very High Confidence" }
];

// Unified Standard Assessment Battery (RIASEC 12 Items + SCCT 6 Items + Observable Tasks 5 Items)
const ASSESSMENT_BATTERY: AssessmentItemDef[] = [
  // --- RIASEC: Realistic (R) ---
  {
    id: "r1",
    section: "Holland RIASEC: Realistic (R)",
    construct: "Realistic",
    text: "I like to build, repair, or maintain physical hardware, mechanisms, or concrete technical systems.",
    responseType: "likert",
    options: LIKERT_SCALE
  },
  {
    id: "r2",
    section: "Holland RIASEC: Realistic (R)",
    construct: "Realistic",
    text: "I enjoy working with tools, robotics, electronics, or hands-on engineering equipment.",
    responseType: "likert",
    options: LIKERT_SCALE
  },
  // --- RIASEC: Investigative (I) ---
  {
    id: "i1",
    section: "Holland RIASEC: Investigative (I)",
    construct: "Investigative",
    text: "I like to analyze complex datasets, formulate scientific hypotheses, and solve challenging algorithmic problems.",
    responseType: "likert",
    options: LIKERT_SCALE
  },
  {
    id: "i2",
    section: "Holland RIASEC: Investigative (I)",
    construct: "Investigative",
    text: "I enjoy conducting in-depth research, reading technical literature, and discovering how systems work beneath the surface.",
    responseType: "likert",
    options: LIKERT_SCALE
  },
  // --- RIASEC: Artistic (A) ---
  {
    id: "a1",
    section: "Holland RIASEC: Artistic (A)",
    construct: "Artistic",
    text: "I enjoy designing intuitive visual interfaces, novel user experiences, and creative digital media.",
    responseType: "likert",
    options: LIKERT_SCALE
  },
  {
    id: "a2",
    section: "Holland RIASEC: Artistic (A)",
    construct: "Artistic",
    text: "I like expressing open-ended creativity, writing expressive prose, or creating artistic concepts without rigid rules.",
    responseType: "likert",
    options: LIKERT_SCALE
  },
  // --- RIASEC: Social (S) ---
  {
    id: "s1",
    section: "Holland RIASEC: Social (S)",
    construct: "Social",
    text: "I enjoy mentoring peers, teaching complex topics clearly, and helping others achieve their goals.",
    responseType: "likert",
    options: LIKERT_SCALE
  },
  {
    id: "s2",
    section: "Holland RIASEC: Social (S)",
    construct: "Social",
    text: "I prefer collaborative group environments where interpersonal communication and team empathy are essential.",
    responseType: "likert",
    options: LIKERT_SCALE
  },
  // --- RIASEC: Enterprising (E) ---
  {
    id: "e1",
    section: "Holland RIASEC: Enterprising (E)",
    construct: "Enterprising",
    text: "I like leading initiatives, pitching product visions, and persuading stakeholders to adopt new ideas.",
    responseType: "likert",
    options: LIKERT_SCALE
  },
  {
    id: "e2",
    section: "Holland RIASEC: Enterprising (E)",
    construct: "Enterprising",
    text: "I enjoy taking calculated entrepreneurial risks, organizing teams, and driving measurable project outcomes.",
    responseType: "likert",
    options: LIKERT_SCALE
  },
  // --- RIASEC: Conventional (C) ---
  {
    id: "c1",
    section: "Holland RIASEC: Conventional (C)",
    construct: "Conventional",
    text: "I prefer structured protocols, organized data schemas, and meticulous attention to detail and accuracy.",
    responseType: "likert",
    options: LIKERT_SCALE
  },
  {
    id: "c2",
    section: "Holland RIASEC: Conventional (C)",
    construct: "Conventional",
    text: "I like establishing orderly filing, systematic documentation, and standardized quality assurance standards.",
    responseType: "likert",
    options: LIKERT_SCALE
  },
  // --- SCCT: Self-Efficacy & Outcome Expectations ---
  {
    id: "se1",
    section: "Career Beliefs: Self-Efficacy",
    construct: "Self-Efficacy",
    text: "How confident are you in your ability to master difficult technical concepts through disciplined, self-directed practice?",
    responseType: "likert",
    options: LIKERT_SCALE
  },
  {
    id: "se2",
    section: "Career Beliefs: Self-Efficacy",
    construct: "Self-Efficacy",
    text: "How confident are you that you can complete a complex, multi-week software or engineering project independently?",
    responseType: "likert",
    options: LIKERT_SCALE
  },
  {
    id: "oe1",
    section: "Career Beliefs: Outcome Expectations",
    construct: "Outcome Expectations",
    text: "How strongly do you expect your ideal career to provide intellectually stimulating problem-solving and rapid learning?",
    responseType: "likert",
    options: LIKERT_SCALE
  },
  {
    id: "oe2",
    section: "Career Beliefs: Outcome Expectations",
    construct: "Outcome Expectations",
    text: "How strongly do you expect your target career to provide creative autonomy, practical utility, and financial stability?",
    responseType: "likert",
    options: LIKERT_SCALE
  },
  {
    id: "cs1",
    section: "Career Beliefs: Contextual Supports",
    construct: "Contextual Supports",
    text: "What external supports do you currently have access to? (e.g. Mentors, school robotics lab, peer study groups, online communities)",
    responseType: "open"
  },
  {
    id: "cb1",
    section: "Career Beliefs: Contextual Barriers",
    construct: "Contextual Barriers",
    text: "What potential constraints or barriers could make your desired journey challenging? (e.g. Time limits, financial constraints, prerequisite gaps)",
    responseType: "open"
  },
  // --- Observable Learning & Reasoning Tasks ---
  {
    id: "lt_recall",
    section: "Observable Task A: Concept Recall",
    construct: "Recall",
    text: "In computing and data structures, what is the fundamental difference between a Stack and a Queue?",
    responseType: "task",
    expectedCapability: "Retrieval of core technical definitions (LIFO vs FIFO)."
  },
  {
    id: "lt_explain",
    section: "Observable Task B: Explanation",
    construct: "Explanation",
    text: "In your own words, explain why indexing a database table speeds up search queries, and what trade-off or cost it introduces.",
    responseType: "task",
    expectedCapability: "Explaining system trade-offs (search speed vs write overhead/storage)."
  },
  {
    id: "lt_apply",
    section: "Observable Task C: Application",
    construct: "Application",
    text: "You must count unique error messages in a 10GB log file on a machine with only 2GB of RAM. How would you design your processing pipeline without crashing?",
    responseType: "task",
    expectedCapability: "Applying streaming, chunked reading, generators, or hash partitioning."
  },
  {
    id: "lt_error",
    section: "Observable Task D: Error Detection",
    construct: "Error Detection",
    text: "Review this loop: `for (let i = 0; i <= array.length; i++) { console.log(array[i]); }`. What bug exists here and why?",
    responseType: "task",
    expectedCapability: "Identifying off-by-one boundary index error (`<=` instead of `<`)."
  },
  {
    id: "lt_reason",
    section: "Observable Task E: Architectural Reasoning",
    construct: "Reasoning",
    text: "Why might a product engineering team choose a monolithic architecture initially rather than starting immediately with distributed microservices?",
    responseType: "task",
    expectedCapability: "Analyzing operational complexity, network latency, and deployment velocity."
  }
];

export function AssessmentFlow() {
  const [currentIdx, setCurrentIdx] = useState(-1);
  const [responses, setResponses] = useState<Record<string, string | number>>({});
  const [isSynthesizing, setIsSynthesizing] = useState(false);
  const [profile, setProfile] = useState<Record<string, unknown> | null>(null);
  
  // Real User Data from Onboarding / LocalStorage
  const [userName, setUserName] = useState<string>("");
  const [userIdentity, setUserIdentity] = useState<string>("");
  const [userGoal, setUserGoal] = useState<string>("");

  // Real User Evidence State
  const [evidenceList, setEvidenceList] = useState<EvidenceItem[]>([]);
  const [showEvidenceDrawer, setShowEvidenceDrawer] = useState(false);
  const [portfolioLink, setPortfolioLink] = useState("");
  const fileInputRef = useRef<HTMLInputElement>(null);

  // Load all user data and saved draft on mount
  useEffect(() => {
    if (typeof window !== "undefined") {
      try {
        const stored = localStorage.getItem("pathmind_user_evidence");
        if (stored) setEvidenceList(JSON.parse(stored));
      } catch { /* ignore */ }
      
      setUserName(localStorage.getItem("pathmind_user_name") || "");
      setUserIdentity(localStorage.getItem("pathmind_user_identity") || "");
      setUserGoal(localStorage.getItem("pathmind_user_goal") || "");

      // Check for saved assessment draft
      try {
        const draft = localStorage.getItem("pathmind_assessment_draft");
        if (draft) {
          const parsed = JSON.parse(draft);
          if (parsed && typeof parsed === "object") {
            setResponses(parsed);
          }
        }
      } catch { /* ignore */ }
    }
  }, []);

  // Autosave responses to localStorage
  const saveDraft = (updatedResponses: Record<string, string | number>) => {
    if (typeof window !== "undefined") {
      localStorage.setItem("pathmind_assessment_draft", JSON.stringify(updatedResponses));
    }
  };

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
    const q = ASSESSMENT_BATTERY[currentIdx];
    const newResponses = { ...responses, [q.id]: value };
    setResponses(newResponses);
    saveDraft(newResponses);

    if (currentIdx < ASSESSMENT_BATTERY.length - 1) {
      setCurrentIdx(currentIdx + 1);
    } else {
      setCurrentIdx(ASSESSMENT_BATTERY.length);
      setIsSynthesizing(true);
      
      try {
        const baseUrl = process.env.NEXT_PUBLIC_API_BASE_URL || "https://pathmind-api.onrender.com";
        const personId = userName ? userName.toLowerCase().replace(/\s+/g, "-") : "scholar-user";
        
        // 1. Build RIASEC Result
        const riasecKeys = ["r1", "r2", "i1", "i2", "a1", "a2", "s1", "s2", "e1", "e2", "c1", "c2"];
        const riasecResp = riasecKeys.map(k => ({
          item_id: k,
          response_value: Number(newResponses[k] || 3)
        }));

        // 2. Build SCCT Result
        const scctKeys = ["se1", "se2", "oe1", "oe2", "cs1", "cb1"];
        const scctResp = scctKeys.map(k => ({
          item_id: k,
          response_value: newResponses[k] || ""
        }));

        // 3. Build Learning Tasks Result
        const learningKeys = ["lt_recall", "lt_explain", "lt_apply", "lt_error", "lt_reason"];
        const learningResp = learningKeys.map(k => ({
          item_id: k,
          response_value: newResponses[k] || ""
        }));

        const res = await fetch(`${baseUrl}/api/counseling/synthesize`, {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            "X-Person-ID": personId
          },
          body: JSON.stringify({
            person_id: personId,
            goals: userGoal ? [userGoal] : [],
            constraints: userIdentity ? [`Status: ${userIdentity}`] : [],
            evidence: evidenceList,
            assessment_results: [
              {
                assessment_id: "riasec_v1",
                raw_responses: riasecResp
              },
              {
                assessment_id: "scct_v1",
                raw_responses: scctResp
              },
              {
                assessment_id: "learning_v1",
                raw_responses: learningResp
              }
            ]
          })
        });

        if (!res.ok) {
          throw new Error("Backend synthesis failed.");
        }

        const data = await res.json();
        setProfile(data);
      } catch (err) {
        console.error(err);
        setProfile({
          error: {
            code: "SYNTHESIS_ERROR",
            message: "We encountered an issue synthesizing your profile. Please check your connection and try again."
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
            <div className="inline-flex items-center gap-2 px-4 py-1.5 sketchy-chip text-tertiary mb-6 bg-surface-container-low">
              <span className="material-symbols-outlined text-lg" style={{ fontVariationSettings: "'FILL' 1" }}>
                psychology_alt
              </span>
              <span className="font-note-handwritten text-xl font-medium">
                Evidence-Informed Counseling Engine
              </span>
            </div>
            
            <h1 className="font-headline-lg text-4xl sm:text-5xl text-on-surface mb-3">
              {userName ? `Welcome, ${userName}` : "Career & Learning Assessment"}<br />
              <span className="text-secondary italic">Grounding your path in real evidence</span>
            </h1>

            {/* Non-Clinical / Educational Guidance Disclaimer */}
            <div className="mb-6 p-4 rounded-lg bg-surface-container-low/80 border border-outline-variant/40 text-left">
              <p className="font-body-md text-xs text-on-surface-variant leading-relaxed">
                <strong>Important Note:</strong> PATHMIND is an educational counseling tool. It does <em>not</em> administer clinical psychological tests, calculate IQ scores, or make unchangeable assertions about your future. All profiles are <strong>preliminary and updateable</strong>.
              </p>
            </div>
            
            {userGoal && (
              <div className="mb-4 px-4 py-3 sketch-border bg-surface-container-low/80 text-left">
                <span className="font-label-md text-xs uppercase tracking-wider text-outline block mb-1">Your stated goal</span>
                <p className="font-note-handwritten text-xl text-on-surface">&ldquo;{userGoal}&rdquo;</p>
              </div>
            )}

            {/* Evidence & Portfolio Quick Panel */}
            <div className="mb-8 p-5 sketch-border bg-surface-container-low/90 text-left">
              <div className="flex items-center justify-between flex-wrap gap-2 mb-3">
                <span className="font-headline-sm text-base text-on-surface flex items-center gap-2">
                  <span className="material-symbols-outlined text-primary text-xl">folder_shared</span>
                  <span>Attached Portfolio &amp; Evidence ({evidenceList.length})</span>
                </span>
                <button
                  type="button"
                  onClick={() => setShowEvidenceDrawer(!showEvidenceDrawer)}
                  className="px-3 py-1.5 rounded-lg border border-outline/60 text-xs font-semibold hover:bg-surface-container text-on-surface transition-colors cursor-pointer"
                >
                  {showEvidenceDrawer ? "Hide Upload Panel" : "+ Attach Portfolio / Links (Optional)"}
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
                      className="px-3.5 py-1.5 rounded-lg border border-outline/70 text-xs font-semibold flex items-center gap-1.5 hover:bg-surface-container cursor-pointer"
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
                    <button type="submit" className="px-3.5 py-1.5 rounded-lg bg-secondary text-white font-semibold text-xs cursor-pointer">
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
                  Zero evidence attached. The counseling agent will classify claims with strict evidence-gap markers.
                </p>
              )}
            </div>
            
            {/* Primary Action */}
            <div className="flex flex-col sm:flex-row items-center justify-center gap-4">
              <button 
                onClick={handleStart} 
                className="px-8 py-3.5 min-h-[48px] rounded-2xl bg-primary text-white font-bold text-base shadow-md hover:bg-primary/90 flex items-center gap-3 cursor-pointer w-full sm:w-auto justify-center transition-all hover:-translate-y-0.5"
              >
                <span>Begin Assessment ({ASSESSMENT_BATTERY.length} Steps)</span>
                <span className="material-symbols-outlined text-lg">east</span>
              </button>
            </div>
          </div>
        )}

        {currentIdx >= 0 && currentIdx < ASSESSMENT_BATTERY.length && (
          <QuestionCard
            key={ASSESSMENT_BATTERY[currentIdx].id}
            sectionName={ASSESSMENT_BATTERY[currentIdx].section}
            questionText={ASSESSMENT_BATTERY[currentIdx].text}
            responseType={ASSESSMENT_BATTERY[currentIdx].responseType}
            options={ASSESSMENT_BATTERY[currentIdx].options}
            currentValue={responses[ASSESSMENT_BATTERY[currentIdx].id]}
            expectedCapability={ASSESSMENT_BATTERY[currentIdx].expectedCapability}
            progress={currentIdx + 1}
            total={ASSESSMENT_BATTERY.length}
            onAnswer={handleAnswer}
            onBack={currentIdx > 0 ? handleBack : undefined}
          />
        )}

        {currentIdx === ASSESSMENT_BATTERY.length && isSynthesizing && (
          <div key="synthesizing" className="text-center flex flex-col items-center py-16">
            <div className="w-16 h-16 rounded-full border-2 border-primary bg-primary/10 flex items-center justify-center mb-4">
              <span className="material-symbols-outlined text-3xl text-primary animate-spin">
                progress_activity
              </span>
            </div>
            <h2 className="font-headline-lg text-3xl text-on-surface mb-2">Executing Psychometric &amp; Evidence Synthesis...</h2>
            <p className="font-note-handwritten text-2xl text-on-surface-variant">Classifying observations, assessing Holland congruences, and detecting contradictions.</p>
          </div>
        )}

        {currentIdx === ASSESSMENT_BATTERY.length && !isSynthesizing && profile && (
          <CounselingDashboard key="dashboard" profile={profile} />
        )}
      </AnimatePresence>
    </div>
  );
}
