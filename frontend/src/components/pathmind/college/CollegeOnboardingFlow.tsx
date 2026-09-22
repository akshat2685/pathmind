"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { motion, AnimatePresence } from "framer-motion";
import apiClient from "@/lib/api/client";
import { useAuth } from "@/lib/contexts/AuthContext";

interface University {
  university_id: string;
  name: string;
  state: string;
  country?: string;
  official_domain: string;
  official_url?: string;
}

interface Subject {
  subject_id: string;
  code: string;
  name: string;
  credits: number;
}

export function CollegeOnboardingFlow() {
  const router = useRouter();
  const [step, setStep] = useState(1);
  const [loading, setLoading] = useState(false);
  const [submitting, setSubmitting] = useState(false);

  // Form State
  const [personId, setPersonId] = useState("");
  const [scholarName, setScholarName] = useState("");
  const [universities, setUniversities] = useState<University[]>([]);
  const [searchQuery, setSearchQuery] = useState("");
  const [selectedUniversity, setSelectedUniversity] = useState<University | null>(null);

  // Engineering Branch
  const [branch, setBranch] = useState<string>("COMPUTER_SCIENCE_ENGINEER");

  // Semester & Subjects
  const [semester, setSemester] = useState<number>(3);
  const [availableSubjects, setAvailableSubjects] = useState<Subject[]>([]);
  const [selectedSubjectIds, setSelectedSubjectIds] = useState<string[]>([]);

  // Goal & Timeline
  const [goalType, setGoalType] = useState<string>("SEMESTER_EXAM");
  const [examDate, setExamDate] = useState<string>("2026-11-20");
  const [targetScore, setTargetScore] = useState<string>("8.5");
  const [weeklyHours, setWeeklyHours] = useState<number>(14);
  const [learningStyle, setLearningStyle] = useState<string>("visual_examples");

  const { user } = useAuth();

  useEffect(() => {
    if (user) {
      setPersonId(user.id);
      setScholarName(user.email?.split('@')[0] || "Scholar");
    }
  }, [user]);

  // Fetch verified universities
  useEffect(() => {
    fetchUniversities(searchQuery);
  }, [searchQuery]);

  const fetchUniversities = async (q: string) => {
    try {
      const res = await apiClient.get<any>(`/api/college/universities?query=${encodeURIComponent(q)}`);
      if (res.ok && res.data) {
        const data = res.data;
        setUniversities(data);
        if (!selectedUniversity && data.length > 0) {
          setSelectedUniversity(data[0]);
        }
      }
    } catch (err) {
      console.error("Failed to load universities", err);
    }
  };

  // Fetch curriculum when university, branch or semester changes
  useEffect(() => {
    if (selectedUniversity && branch) {
      fetchCurriculum();
    }
  }, [selectedUniversity, branch, semester]);

  const fetchCurriculum = async () => {
    setLoading(true);
    try {
      const univId = selectedUniversity?.university_id || "univ_aicte_model";
      const res = await apiClient.get<any>(
        `/api/college/curriculum?university_id=${univId}&branch=${branch}&semester=${semester}`
      );
      if (res.ok && res.data) {
        const data = res.data;
        const subs = data.subjects || [];
        setAvailableSubjects(subs);
        setSelectedSubjectIds(subs.map((s: Subject) => s.subject_id));
      }
    } catch (err) {
      console.error("Failed to load curriculum", err);
    } finally {
      setLoading(false);
    }
  };

  const toggleSubject = (subId: string) => {
    setSelectedSubjectIds((prev) =>
      prev.includes(subId) ? prev.filter((id) => id !== subId) : [...prev, subId]
    );
  };

  const handleComplete = async () => {
    setSubmitting(true);
    const univId = selectedUniversity?.university_id || "univ_aicte_model";

    try {
      // 1. Save Academic Context
      const contextPayload = {
        university_id: univId,
        branch: branch,
        semester: semester,
        subjects: selectedSubjectIds.length > 0 ? selectedSubjectIds : ["CS-301"],
        exam_window: {
          start: examDate,
          target_score: targetScore,
        },
        available_hours_per_week: weeklyHours,
        learning_style_preferences: [learningStyle],
      };

      await apiClient.post<any>("/api/college/academic-context", contextPayload);

      // 2. Generate Initial Ordered Learning Plan
      await apiClient.post<any>("/api/college/plans/generate", {
        goal_id: `goal_${goalType.toLowerCase()}`,
        target_subject_code_or_id: selectedSubjectIds[0] || null,
      });

      // Navigate to College Dashboard
      router.push("/");
    } catch (err) {
      console.error("Failed to complete onboarding", err);
      router.push("/");
    } finally {
      setSubmitting(false);
    }
  };

  const branches = [
    {
      id: "COMPUTER_SCIENCE_ENGINEER",
      label: "Computer Science & Software",
      icon: "terminal",
      desc: "Algorithms, operating systems, software architecture & database engines.",
    },
    {
      id: "AI_ENGINEER",
      label: "Artificial Intelligence & ML",
      icon: "psychology",
      desc: "Mathematical optimization, neural networks, machine learning & data systems.",
    },
    {
      id: "MECHANICAL_ENGINEER",
      label: "Mechanical Engineering",
      icon: "settings",
      desc: "Thermodynamics, fluid mechanics, structural stress & manufacturing systems.",
    },
    {
      id: "ELECTRICAL_ENGINEER",
      label: "Electrical & Electronics",
      icon: "bolt",
      desc: "Electric circuits, power machines, electromagnetic theory & signal processing.",
    },
    {
      id: "CIVIL_ENGINEER",
      label: "Civil Engineering",
      icon: "foundation",
      desc: "Mechanics of materials, structural analysis, surveying & fluid dynamics.",
    },
    {
      id: "GENERAL_OTHER",
      label: "General / Other Discipline",
      icon: "explore",
      desc: "General engineering foundations and transparent multidisciplinary guidance.",
    },
  ];

  return (
    <div className="min-h-screen bg-[#f7f4e7] text-[#252321] flex flex-col justify-between relative overflow-x-hidden font-sans">
      {/* Background Grid */}
      <div
        className="fixed inset-0 pointer-events-none opacity-80 -z-20"
        style={{
          backgroundImage:
            "linear-gradient(to right, rgba(90, 80, 70, 0.05) 1px, transparent 1px), linear-gradient(to bottom, rgba(90, 80, 70, 0.05) 1px, transparent 1px)",
          backgroundSize: "28px 28px",
        }}
      />

      {/* Ambient Gradient */}
      <div
        className="fixed top-0 left-0 w-[550px] h-[550px] pointer-events-none -z-10 blur-2xl"
        style={{
          background:
            "radial-gradient(circle at 30% 40%, rgba(139, 168, 142, 0.35) 0%, rgba(139, 168, 142, 0.08) 55%, transparent 75%)",
        }}
      />

      {/* Header */}
      <header className="max-w-5xl w-full mx-auto px-6 py-6 flex items-center justify-between border-b border-[#252321]/20">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-full border-[1.75px] border-[#252321] bg-[#fdfae7] flex items-center justify-center">
            <span className="material-symbols-outlined text-[#4a654e] text-2xl">
              school
            </span>
          </div>
          <div>
            <h2 className="font-bold text-xl text-[#252321]">Academic Initiation</h2>
            <p className="text-xs font-note-handwritten text-[#68635e]">
              Step {step} of 4 • Grounding your engineering compass
            </p>
          </div>
        </div>

        {/* Step Progress Indicators */}
        <div className="flex items-center gap-2">
          {[1, 2, 3, 4].map((i) => (
            <div
              key={i}
              className={`h-2.5 rounded-full transition-all ${
                i === step
                  ? "w-8 bg-[#4a654e]"
                  : i < step
                  ? "w-4 bg-[#8ba88e]"
                  : "w-2.5 bg-[#d9d2be]"
              }`}
            />
          ))}
        </div>
      </header>

      {/* Main Form Container */}
      <main className="flex-grow flex items-center justify-center p-4 sm:p-6 md:p-10 z-10">
        <div
          className="w-full max-w-3xl bg-[#fdfae7] p-6 sm:p-10 relative"
          style={{
            border: "1.75px solid #252321",
            borderRadius: "15px 225px 15px 255px / 255px 15px 225px 15px",
            boxShadow:
              "4px 6px 0px rgba(37, 35, 33, 0.9), 12px 16px 28px rgba(70, 60, 50, 0.08)",
          }}
        >
          <AnimatePresence mode="wait">
            {/* STEP 1: Academic Identity & University */}
            {step === 1 && (
              <motion.div
                key="step1"
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -10 }}
                className="space-y-6"
              >
                <div className="border-b border-dashed border-[#252321]/20 pb-4">
                  <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-[#8ba88e]/20 border border-[#8ba88e] text-xs font-medium mb-2">
                    <span className="material-symbols-outlined text-sm">badge</span>
                    Scholar Profile
                  </div>
                  <h3 className="text-2xl sm:text-3xl font-bold text-[#252321]">
                    Where do you study, Traveler?
                  </h3>
                  <p className="font-serif italic text-sm text-[#68635e] mt-1">
                    PATHMIND grounds all study materials in your verified university curriculum.
                  </p>
                </div>

                <div className="space-y-4">
                  <div>
                    <label className="block text-xs font-bold uppercase tracking-wider text-[#252321] mb-1.5">
                      Your Full Name
                    </label>
                    <input
                      type="text"
                      value={scholarName}
                      onChange={(e) => setScholarName(e.target.value)}
                      placeholder="e.g. Akshat Jain"
                      className="w-full px-4 py-3 rounded-md text-sm border-[1.5px] border-[#4a453f] bg-white/70 focus:bg-white focus:outline-none focus:shadow-[2px_3px_0px_#252321]"
                    />
                  </div>

                  <div>
                    <label className="block text-xs font-bold uppercase tracking-wider text-[#252321] mb-1.5">
                      Search Verified University / Curriculum Body
                    </label>
                    <input
                      type="text"
                      value={searchQuery}
                      onChange={(e) => setSearchQuery(e.target.value)}
                      placeholder="Type Anna, VTU, Mumbai, AKTU, or AICTE..."
                      className="w-full px-4 py-3 rounded-md text-sm border-[1.5px] border-[#4a453f] bg-white/70 focus:bg-white focus:outline-none focus:shadow-[2px_3px_0px_#252321]"
                    />
                  </div>

                  <div className="space-y-2 max-h-56 overflow-y-auto pr-1">
                    {universities.map((u) => (
                      <div
                        key={u.university_id}
                        onClick={() => setSelectedUniversity(u)}
                        className={`p-3.5 rounded-md border-[1.5px] cursor-pointer transition-all flex items-center justify-between ${
                          selectedUniversity?.university_id === u.university_id
                            ? "border-[#4a654e] bg-[#4a654e]/10 shadow-[2px_2px_0px_#4a654e]"
                            : "border-[#252321]/30 hover:border-[#252321] bg-white/40"
                        }`}
                      >
                        <div>
                          <h4 className="font-semibold text-sm text-[#252321]">{u.name}</h4>
                          <p className="text-xs text-[#68635e]">
                            {u.state}, {u.country} • Domain: {u.official_domain}
                          </p>
                        </div>
                        {selectedUniversity?.university_id === u.university_id && (
                          <span className="material-symbols-outlined text-[#4a654e]">
                            check_circle
                          </span>
                        )}
                      </div>
                    ))}
                  </div>
                </div>

                <div className="flex justify-end pt-4 border-t border-dashed border-[#252321]/20">
                  <button
                    type="button"
                    onClick={() => setStep(2)}
                    className="px-6 py-3 bg-[#252321] hover:bg-[#383430] text-[#fdfae7] font-semibold text-sm rounded-md border-2 border-[#252321] shadow-[2px_3px_0px_rgba(37,35,33,0.9)] flex items-center gap-2 cursor-pointer"
                  >
                    <span>Continue to Branch</span>
                    <span>→</span>
                  </button>
                </div>
              </motion.div>
            )}

            {/* STEP 2: Engineering Branch Selection */}
            {step === 2 && (
              <motion.div
                key="step2"
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -10 }}
                className="space-y-6"
              >
                <div className="border-b border-dashed border-[#252321]/20 pb-4">
                  <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-[#8ba88e]/20 border border-[#8ba88e] text-xs font-medium mb-2">
                    <span className="material-symbols-outlined text-sm">engineering</span>
                    Field of Study
                  </div>
                  <h3 className="text-2xl sm:text-3xl font-bold text-[#252321]">
                    Select Your Engineering Discipline
                  </h3>
                  <p className="font-serif italic text-sm text-[#68635e] mt-1">
                    PATHMIND provides deep knowledge coverage for 5 core engineering domains.
                  </p>
                </div>

                <div className="grid sm:grid-cols-2 gap-3.5">
                  {branches.map((b) => (
                    <div
                      key={b.id}
                      onClick={() => setBranch(b.id)}
                      className={`p-4 rounded-md border-[1.5px] cursor-pointer transition-all flex items-start gap-3 ${
                        branch === b.id
                          ? "border-[#4a654e] bg-[#4a654e]/10 shadow-[2px_3px_0px_#4a654e]"
                          : "border-[#252321]/30 hover:border-[#252321] bg-white/40"
                      }`}
                    >
                      <div className="w-10 h-10 rounded-full bg-[#fdfae7] border border-[#252321]/30 flex items-center justify-center shrink-0 text-[#4a654e]">
                        <span className="material-symbols-outlined text-xl">{b.icon}</span>
                      </div>
                      <div className="flex-1">
                        <h4 className="font-bold text-sm text-[#252321]">{b.label}</h4>
                        <p className="text-xs text-[#68635e] mt-0.5 leading-relaxed">{b.desc}</p>
                      </div>
                    </div>
                  ))}
                </div>

                <div className="flex justify-between pt-4 border-t border-dashed border-[#252321]/20">
                  <button
                    type="button"
                    onClick={() => setStep(1)}
                    className="px-5 py-2.5 border-[1.5px] border-[#252321] rounded-md text-xs font-semibold cursor-pointer"
                  >
                    ← Back
                  </button>
                  <button
                    type="button"
                    onClick={() => setStep(3)}
                    className="px-6 py-3 bg-[#252321] hover:bg-[#383430] text-[#fdfae7] font-semibold text-sm rounded-md border-2 border-[#252321] shadow-[2px_3px_0px_rgba(37,35,33,0.9)] flex items-center gap-2 cursor-pointer"
                  >
                    <span>Configure Semester</span>
                    <span>→</span>
                  </button>
                </div>
              </motion.div>
            )}

            {/* STEP 3: Semester & Subject Selection */}
            {step === 3 && (
              <motion.div
                key="step3"
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -10 }}
                className="space-y-6"
              >
                <div className="border-b border-dashed border-[#252321]/20 pb-4">
                  <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-[#8ba88e]/20 border border-[#8ba88e] text-xs font-medium mb-2">
                    <span className="material-symbols-outlined text-sm">calendar_month</span>
                    Current Curriculum
                  </div>
                  <h3 className="text-2xl sm:text-3xl font-bold text-[#252321]">
                    Which semester are you in?
                  </h3>
                  <p className="font-serif italic text-sm text-[#68635e] mt-1">
                    Select your active semester to pull verified AICTE / university subject modules.
                  </p>
                </div>

                {/* Semester Pills */}
                <div>
                  <label className="block text-xs font-bold uppercase tracking-wider text-[#252321] mb-2">
                    Active Semester (B.Tech / B.E.)
                  </label>
                  <div className="flex flex-wrap gap-2">
                    {[1, 2, 3, 4, 5, 6, 7, 8].map((s) => (
                      <button
                        key={s}
                        type="button"
                        onClick={() => setSemester(s)}
                        className={`px-4 py-2 text-sm font-semibold rounded-md border-[1.5px] cursor-pointer transition-all ${
                          semester === s
                            ? "bg-[#4a654e] text-white border-[#4a654e] shadow-[2px_2px_0px_#252321]"
                            : "bg-white/60 border-[#252321]/40 text-[#252321] hover:border-[#252321]"
                        }`}
                      >
                        Sem {s}
                      </button>
                    ))}
                  </div>
                </div>

                {/* Subjects Checkbox List */}
                <div>
                  <div className="flex justify-between items-baseline mb-2">
                    <label className="block text-xs font-bold uppercase tracking-wider text-[#252321]">
                      Verified Subjects for Semester {semester}
                    </label>
                    <span className="text-xs font-note-handwritten text-[#68635e]">
                      toggle active subjects
                    </span>
                  </div>

                  {loading ? (
                    <div className="p-8 text-center text-xs font-serif italic text-[#68635e]">
                      Fetching verified university syllabus modules...
                    </div>
                  ) : availableSubjects.length === 0 ? (
                    <div className="p-6 border border-dashed border-[#252321]/30 rounded-md bg-white/30 text-center">
                      <p className="text-xs text-[#68635e]">
                        Curriculum for {branch} is general or custom. You will still receive personalized learning activities.
                      </p>
                    </div>
                  ) : (
                    <div className="space-y-2 max-h-56 overflow-y-auto pr-1">
                      {availableSubjects.map((sub) => {
                        const isSelected = selectedSubjectIds.includes(sub.subject_id);
                        return (
                          <div
                            key={sub.subject_id}
                            onClick={() => toggleSubject(sub.subject_id)}
                            className={`p-3 rounded-md border-[1.5px] cursor-pointer flex items-center justify-between transition-all ${
                              isSelected
                                ? "border-[#4a654e] bg-[#4a654e]/10"
                                : "border-[#252321]/20 bg-white/40 opacity-70"
                            }`}
                          >
                            <div className="flex items-center gap-2.5">
                              <span
                                className={`w-4 h-4 rounded border flex items-center justify-center text-xs ${
                                  isSelected
                                    ? "bg-[#4a654e] border-[#4a654e] text-white"
                                    : "border-[#252321]/50 bg-white"
                                }`}
                              >
                                {isSelected && "✓"}
                              </span>
                              <div>
                                <span className="text-xs font-mono font-bold text-[#4a654e] mr-2">
                                  {sub.code}
                                </span>
                                <span className="text-sm font-medium text-[#252321]">{sub.name}</span>
                              </div>
                            </div>
                            <span className="text-xs text-[#68635e] font-note-handwritten">
                              {sub.credits} Credits
                            </span>
                          </div>
                        );
                      })}
                    </div>
                  )}
                </div>

                <div className="flex justify-between pt-4 border-t border-dashed border-[#252321]/20">
                  <button
                    type="button"
                    onClick={() => setStep(2)}
                    className="px-5 py-2.5 border-[1.5px] border-[#252321] rounded-md text-xs font-semibold cursor-pointer"
                  >
                    ← Back
                  </button>
                  <button
                    type="button"
                    onClick={() => setStep(4)}
                    className="px-6 py-3 bg-[#252321] hover:bg-[#383430] text-[#fdfae7] font-semibold text-sm rounded-md border-2 border-[#252321] shadow-[2px_3px_0px_rgba(37,35,33,0.9)] flex items-center gap-2 cursor-pointer"
                  >
                    <span>Set Goals &amp; Preferences</span>
                    <span>→</span>
                  </button>
                </div>
              </motion.div>
            )}

            {/* STEP 4: Goals, Timeline & Embark */}
            {step === 4 && (
              <motion.div
                key="step4"
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -10 }}
                className="space-y-6"
              >
                <div className="border-b border-dashed border-[#252321]/20 pb-4">
                  <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-[#8ba88e]/20 border border-[#8ba88e] text-xs font-medium mb-2">
                    <span className="material-symbols-outlined text-sm">flag</span>
                    Target Horizon
                  </div>
                  <h3 className="text-2xl sm:text-3xl font-bold text-[#252321]">
                    What is your core academic objective?
                  </h3>
                  <p className="font-serif italic text-sm text-[#68635e] mt-1">
                    Your learning timeline will be calculated around your exam window.
                  </p>
                </div>

                <div className="grid sm:grid-cols-2 gap-4">
                  <div>
                    <label className="block text-xs font-bold uppercase tracking-wider text-[#252321] mb-1.5">
                      Target Focus
                    </label>
                    <select
                      value={goalType}
                      onChange={(e) => setGoalType(e.target.value)}
                      className="w-full px-3.5 py-2.5 rounded-md text-sm border-[1.5px] border-[#4a453f] bg-white/70"
                    >
                      <option value="SEMESTER_EXAM">Prepare for University Semester Exams</option>
                      <option value="SINGLE_SUBJECT">Deep Focus on One Challenging Subject</option>
                      <option value="CGPA_IMPROVEMENT">Improve Cumulative Grade / CGPA</option>
                      <option value="TOPIC_MASTERY">Understand Core Concepts from First Principles</option>
                    </select>
                  </div>

                  <div>
                    <label className="block text-xs font-bold uppercase tracking-wider text-[#252321] mb-1.5">
                      Target Score / CGPA
                    </label>
                    <input
                      type="text"
                      value={targetScore}
                      onChange={(e) => setTargetScore(e.target.value)}
                      placeholder="e.g. 8.5 CGPA or 80%"
                      className="w-full px-3.5 py-2.5 rounded-md text-sm border-[1.5px] border-[#4a453f] bg-white/70"
                    />
                  </div>

                  <div>
                    <label className="block text-xs font-bold uppercase tracking-wider text-[#252321] mb-1.5">
                      Expected University Exam Date
                    </label>
                    <input
                      type="date"
                      value={examDate}
                      onChange={(e) => setExamDate(e.target.value)}
                      className="w-full px-3.5 py-2.5 rounded-md text-sm border-[1.5px] border-[#4a453f] bg-white/70"
                    />
                  </div>

                  <div>
                    <label className="block text-xs font-bold uppercase tracking-wider text-[#252321] mb-1.5">
                      Available Weekly Study Hours: {weeklyHours}h
                    </label>
                    <input
                      type="range"
                      min={6}
                      max={35}
                      value={weeklyHours}
                      onChange={(e) => setWeeklyHours(Number(e.target.value))}
                      className="w-full mt-2 accent-[#4a654e]"
                    />
                  </div>
                </div>

                <div>
                  <label className="block text-xs font-bold uppercase tracking-wider text-[#252321] mb-1.5">
                    How do you learn technical concepts best?
                  </label>
                  <div className="grid sm:grid-cols-2 gap-2.5">
                    {[
                      { id: "visual_examples", label: "Visual animations & worked examples first" },
                      { id: "rigorous_derivations", label: "Step-by-step mathematical derivations" },
                      { id: "practice_heavy", label: "Short videos followed by immediate numericals" },
                      { id: "pyq_driven", label: "Exam-oriented syllabus review & past papers" },
                    ].map((pref) => (
                      <div
                        key={pref.id}
                        onClick={() => setLearningStyle(pref.id)}
                        className={`p-3 rounded-md border-[1.5px] text-xs font-medium cursor-pointer transition-all ${
                          learningStyle === pref.id
                            ? "border-[#4a654e] bg-[#4a654e]/10 font-bold"
                            : "border-[#252321]/30 bg-white/40 hover:border-[#252321]"
                        }`}
                      >
                        {pref.label}
                      </div>
                    ))}
                  </div>
                </div>

                <div className="flex justify-between pt-4 border-t border-dashed border-[#252321]/20">
                  <button
                    type="button"
                    onClick={() => setStep(3)}
                    className="px-5 py-2.5 border-[1.5px] border-[#252321] rounded-md text-xs font-semibold cursor-pointer"
                  >
                    ← Back
                  </button>
                  <button
                    type="button"
                    disabled={submitting}
                    onClick={handleComplete}
                    className="px-8 py-3.5 bg-[#4a654e] hover:bg-[#3b523e] text-white font-bold text-base rounded-md border-2 border-[#252321] shadow-[2px_3px_0px_#252321] flex items-center gap-2 cursor-pointer transition-all"
                  >
                    <span>{submitting ? "Synthesizing Plan..." : "Embark on Study Plan"}</span>
                    <span>→</span>
                  </button>
                </div>
              </motion.div>
            )}
          </AnimatePresence>
        </div>
      </main>

      {/* Footer */}
      <footer className="w-full max-w-5xl mx-auto px-6 py-4 text-center text-xs text-[#68635e]">
        PATHMIND Living Sketchbook • Grounded in Official Curricula
      </footer>
    </div>
  );
}
