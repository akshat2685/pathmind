"use client";

import { useState, useEffect, useRef } from "react";
import { useRouter } from "next/navigation";
import { motion, AnimatePresence } from "framer-motion";
import { Send, User, Bot, Loader2 } from "lucide-react";
import { TopBar } from "@/components/layout/TopBar";

interface Pathway {
  id: string;
  title: string;
  target: string;
  confidence: string;
  why: string;
  locked_phases: number;
}

interface AssessmentItem {
  id: string;
  text: string;
  scale?: { value: number; label: string }[];
}

interface AssessmentDefinition {
  id: string;
  name: string;
  items: AssessmentItem[];
}

interface Message {
  id: string;
  role: "agent" | "learner";
  text: string;
  type?: "text" | "options" | "evidence_upload" | "assessment_bridge" | "assessment_form" | "pathways";
  options?: string[];
  pathways?: Pathway[];
  assessmentData?: AssessmentDefinition;
}

export function AgentOnboardingFlow() {
  const router = useRouter();
  const [messages, setMessages] = useState<Message[]>([
    {
      id: "msg_intro",
      role: "agent",
      text: "Hi. I'm your PATHMIND guide. What should I call you?",
      type: "text",
    }
  ]);
  const [inputText, setInputText] = useState("");
  const [step, setStep] = useState<"NAME" | "ASPIRATION" | "STAGE" | "EVIDENCE" | "ASSESSMENT" | "SYNTHESIS">("NAME");
  const [isTyping, setIsTyping] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Stored state
  const [_learnerName, setLearnerName] = useState("");
  const [learnerAspiration, setLearnerAspiration] = useState("");
  const [learnerStage, setLearnerStage] = useState("");
  const [_evidenceProvided, setEvidenceProvided] = useState("");
  
  // Assessment State
  const [currentBlueprintId, setCurrentBlueprintId] = useState("");
  const [assessmentResponses, setAssessmentResponses] = useState<Record<string, number>>({});
  const [isSubmittingAssessment, setIsSubmittingAssessment] = useState(false);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, isTyping, assessmentResponses]);

  const addAgentMessage = (text: string, type: Message["type"] = "text", options?: string[], pathways?: Pathway[], assessmentData?: AssessmentDefinition) => {
    setIsTyping(true);
    setTimeout(() => {
      setMessages((prev) => [
        ...prev,
        { id: `msg_${Date.now()}`, role: "agent", text, type, options, pathways, assessmentData }
      ]);
      setIsTyping(false);
    }, 800);
  };

  const handleSend = async (text: string = inputText) => {
    if (!text.trim() || isTyping) return;
    
    const userMsg: Message = { id: `msg_${Date.now()}`, role: "learner", text };
    setMessages((prev) => [...prev, userMsg]);
    setInputText("");

    if (step === "NAME") {
      setLearnerName(text);
      const canonicalId = text.toLowerCase().replace(/[^a-z0-9]/g, '-') + '-' + Math.random().toString(36).substring(2, 8);
      if (typeof window !== "undefined") {
        localStorage.setItem("pathmind_user_name", text);
        localStorage.setItem("pathmind_canonical_id", canonicalId);
      }
      setStep("ASPIRATION");
      addAgentMessage(`Nice to meet you, ${text}. What are you trying to become or accomplish?`);
    } 
    else if (step === "ASPIRATION") {
      setLearnerAspiration(text);
      setStep("STAGE");
      addAgentMessage(
        "Got it. Before I recommend a path, I need to understand where you're starting from.",
        "options",
        [
          "School Student",
          "College / University Student",
          "Graduate",
          "Working Professional",
          "Career Switcher",
          "Independent / Self-learning"
        ]
      );
    }
    else if (step === "STAGE") {
      setLearnerStage(text);
      setStep("EVIDENCE");
      
      const evidencePrompt = "Please share any links, portfolio items, or describe any relevant experience you have to support your aspiration.";
      addAgentMessage(evidencePrompt, "evidence_upload");
    }
    else if (step === "EVIDENCE") {
      setEvidenceProvided(text);
      setStep("ASSESSMENT");
      setIsTyping(true);
      
      try {
        const canonicalId = localStorage.getItem("pathmind_canonical_id") || "scholar-user";
        const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000";
        
        // 1. Submit Profile to get Blueprint
        const profileRes = await fetch(`${API_BASE}/api/onboarding/profile`, {
          method: "POST",
          headers: { "Content-Type": "application/json", "X-Person-ID": canonicalId },
          body: JSON.stringify({
            learner_stage: learnerStage,
            aspiration: learnerAspiration,
            evidence_summary: text
          })
        });
        
        if (!profileRes.ok) throw new Error("Failed to generate blueprint");
        const blueprint = await profileRes.json();
        setCurrentBlueprintId(blueprint.id);
        
        addAgentMessage(`Based on your stage as a ${learnerStage}, I am designing a targeted assessment to evaluate your ${blueprint.difficulty_level} capability in ${blueprint.dimensions.join(", ")}.`);

        // 2. Generate Dynamic Assessment based on Blueprint
        const assessRes = await fetch(`${API_BASE}/api/assessments/dynamic/generate`, {
          method: "POST",
          headers: { "Content-Type": "application/json", "X-Person-ID": canonicalId },
          body: JSON.stringify({ blueprint_id: blueprint.id })
        });
        
        if (!assessRes.ok) throw new Error("Failed to generate assessment");
        const assessmentDef = await assessRes.json();

        setTimeout(() => {
          setIsTyping(false);
          addAgentMessage(
            `I have generated your dynamic assessment for "${learnerAspiration}". Please answer these questions to establish your baseline.`,
            "assessment_form",
            [],
            undefined,
            assessmentDef
          );
        }, 1500);

      } catch (e) {
        console.error(e);
        setIsTyping(false);
        addAgentMessage("I encountered an error generating your assessment. Please try again.");
      }
    }
  };

  const handleSubmitAssessment = async (assessmentId: string) => {
    setIsSubmittingAssessment(true);
    try {
      const canonicalId = localStorage.getItem("pathmind_canonical_id") || "scholar-user";
      const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000";
      
      const responses = Object.entries(assessmentResponses).map(([itemId, value]) => ({
        item_id: itemId,
        response_value: value
      }));

      // Submit Assessment & Evaluate Baseline
      const submitRes = await fetch(`${API_BASE}/api/assessments/${assessmentId}/submit`, {
        method: "POST",
        headers: { "Content-Type": "application/json", "X-Person-ID": canonicalId },
        body: JSON.stringify({
          blueprint_id: currentBlueprintId,
          responses: responses
        })
      });

      if (!submitRes.ok) throw new Error("Failed to submit assessment");

      setStep("SYNTHESIS");
      addAgentMessage("Assessment complete! I am now synthesizing your personalized roadmap based on your baseline capabilities...");
      
      // Generate Roadmap
      setTimeout(() => {
        fetch(`${API_BASE}/api/roadmap/generate?target_outcome=${encodeURIComponent(learnerAspiration)}`, {
          method: "POST",
          headers: { "X-Person-ID": canonicalId }
        }).then(() => {
          router.push("/journey");
        }).catch((e) => {
          console.error(e);
          router.push("/journey");
        });
      }, 2000);
      
    } catch (e) {
      console.error(e);
      addAgentMessage("Failed to process assessment results.");
    } finally {
      setIsSubmittingAssessment(false);
    }
  };

  return (
    <div className="flex flex-col min-h-screen bg-surface">
      <TopBar />
      <main className="flex-1 max-w-3xl w-full mx-auto p-4 md:p-8 flex flex-col pt-24 pb-32">
        <div className="flex-1 space-y-6">
          <AnimatePresence>
            {messages.map((msg) => (
              <motion.div
                key={msg.id}
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                className={`flex ${msg.role === "agent" ? "justify-start" : "justify-end"}`}
              >
                <div className={`flex gap-3 max-w-[85%] ${msg.role === "agent" ? "flex-row" : "flex-row-reverse"}`}>
                  <div className={`w-10 h-10 rounded-full flex items-center justify-center shrink-0 ${
                    msg.role === "agent" ? "bg-primary/10 text-primary border border-primary/20" : "bg-surface-container-highest text-on-surface border border-outline"
                  }`}>
                    {msg.role === "agent" ? <Bot className="w-5 h-5" /> : <User className="w-5 h-5" />}
                  </div>
                  
                  <div className={`space-y-4 ${msg.role === "agent" ? "items-start" : "items-end"}`}>
                    {msg.text && (
                      <div className={`p-4 rounded-2xl text-sm leading-relaxed ${
                        msg.role === "agent" 
                          ? "bg-surface-container-low border border-outline/50 text-on-surface rounded-tl-none" 
                          : "bg-primary text-on-primary rounded-tr-none shadow-md"
                      }`}>
                        {msg.text}
                      </div>
                    )}
                    
                    {msg.type === "options" && msg.options && (
                      <div className="flex flex-wrap gap-2 mt-2">
                        {msg.options.map((opt) => (
                          <button
                            key={opt}
                            onClick={() => handleSend(opt)}
                            className="px-4 py-2 rounded-xl text-xs font-semibold bg-surface border border-outline hover:bg-primary/10 hover:border-primary/50 hover:text-primary transition-all"
                          >
                            {opt}
                          </button>
                        ))}
                      </div>
                    )}

                    {msg.type === "assessment_form" && msg.assessmentData && (
                      <div className="mt-4 p-5 rounded-2xl bg-surface border border-outline shadow-sm flex flex-col gap-6 w-full min-w-[280px] md:min-w-[500px]">
                        <h3 className="font-bold text-on-surface text-lg border-b border-outline pb-2">
                          {msg.assessmentData.name}
                        </h3>
                        <div className="space-y-6">
                          {msg.assessmentData.items.map((item, idx) => (
                            <div key={item.id} className="space-y-3">
                              <p className="text-sm text-on-surface font-medium">{idx + 1}. {item.text}</p>
                              {item.scale ? (
                                <div className="grid grid-cols-5 gap-2">
                                  {item.scale.map((opt) => (
                                    <button
                                      key={opt.value}
                                      onClick={() => setAssessmentResponses(prev => ({ ...prev, [item.id]: opt.value }))}
                                      className={`py-2 px-1 text-center rounded-lg text-[10px] font-semibold border transition-all ${
                                        assessmentResponses[item.id] === opt.value
                                          ? "bg-primary text-on-primary border-primary"
                                          : "bg-surface-container-low text-on-surface-variant border-outline hover:border-primary/50"
                                      }`}
                                    >
                                      {opt.value}
                                    </button>
                                  ))}
                                  <div className="col-span-5 flex justify-between text-[9px] text-on-surface-variant uppercase tracking-wider px-1">
                                    <span>{item.scale[0].label}</span>
                                    <span>{item.scale[item.scale.length - 1].label}</span>
                                  </div>
                                </div>
                              ) : null}
                            </div>
                          ))}
                        </div>
                        <button
                          disabled={isSubmittingAssessment || Object.keys(assessmentResponses).length !== msg.assessmentData.items.length}
                          onClick={() => handleSubmitAssessment(msg.assessmentData!.id)}
                          className="mt-4 w-full py-3 rounded-xl bg-primary text-on-primary text-sm font-bold hover:opacity-95 transition-all disabled:opacity-50 flex items-center justify-center gap-2"
                        >
                          {isSubmittingAssessment && <Loader2 className="w-4 h-4 animate-spin" />}
                          Submit Assessment
                        </button>
                      </div>
                    )}
                  </div>
                </div>
              </motion.div>
            ))}
          </AnimatePresence>

          {isTyping && (
            <div className="flex justify-start">
              <div className="flex gap-3">
                <div className="w-10 h-10 rounded-full flex items-center justify-center shrink-0 bg-primary/10 text-primary border border-primary/20">
                  <Bot className="w-5 h-5" />
                </div>
                <div className="p-4 rounded-2xl bg-surface-container-low border border-outline/50 rounded-tl-none flex items-center gap-1">
                  <motion.div animate={{ y: [0, -5, 0] }} transition={{ repeat: Infinity, duration: 0.6 }} className="w-1.5 h-1.5 bg-primary/60 rounded-full" />
                  <motion.div animate={{ y: [0, -5, 0] }} transition={{ repeat: Infinity, duration: 0.6, delay: 0.2 }} className="w-1.5 h-1.5 bg-primary/60 rounded-full" />
                  <motion.div animate={{ y: [0, -5, 0] }} transition={{ repeat: Infinity, duration: 0.6, delay: 0.4 }} className="w-1.5 h-1.5 bg-primary/60 rounded-full" />
                </div>
              </div>
            </div>
          )}
          <div ref={messagesEndRef} className="h-4" />
        </div>
      </main>

      <div className="fixed bottom-0 w-full bg-surface/80 backdrop-blur-md border-t border-outline/30 p-4">
        <div className="max-w-3xl mx-auto flex gap-3 relative">
          <input
            type="text"
            value={inputText}
            onChange={(e) => setInputText(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter" && !e.shiftKey) {
                e.preventDefault();
                handleSend();
              }
            }}
            disabled={isTyping || step === "ASSESSMENT" || step === "SYNTHESIS"}
            placeholder={
              step === "ASSESSMENT" ? "Please complete the assessment above..." :
              step === "SYNTHESIS" ? "Synthesizing your roadmap..." :
              "Type your message..."
            }
            className="flex-1 bg-surface-container-lowest border border-outline rounded-2xl px-6 py-4 text-on-surface placeholder:text-on-surface-variant focus:outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary transition-all disabled:opacity-50"
          />
          <button
            onClick={() => handleSend()}
            disabled={!inputText.trim() || isTyping || step === "ASSESSMENT" || step === "SYNTHESIS"}
            className="w-14 h-14 bg-primary text-on-primary rounded-2xl flex items-center justify-center hover:opacity-95 transition-opacity shadow-sm disabled:opacity-50"
          >
            <Send className="w-5 h-5" />
          </button>
        </div>
      </div>
    </div>
  );
}
