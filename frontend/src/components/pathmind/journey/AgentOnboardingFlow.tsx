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

interface Message {
  id: string;
  role: "agent" | "learner";
  text: string;
  type?: "text" | "options" | "evidence_upload" | "assessment_bridge" | "pathways";
  options?: string[];
  pathways?: Pathway[];
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
  const [_learnerStage, setLearnerStage] = useState("");
  const [_evidenceProvided, setEvidenceProvided] = useState("");
  const [_selectedPath, setSelectedPath] = useState("");

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, isTyping]);

  const addAgentMessage = (text: string, type: Message["type"] = "text", options?: string[], pathways?: Pathway[]) => {
    setIsTyping(true);
    setTimeout(() => {
      setMessages((prev) => [
        ...prev,
        { id: `msg_${Date.now()}`, role: "agent", text, type, options, pathways }
      ]);
      setIsTyping(false);
    }, 800);
  };

  const handleSend = async (text: string = inputText) => {
    if (!text.trim()) return;
    
    const userMsg: Message = { id: `msg_${Date.now()}`, role: "learner", text };
    setMessages((prev) => [...prev, userMsg]);
    setInputText("");

    if (step === "NAME") {
      setLearnerName(text);
      // Generate stable canonical identity
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
      
      let evidencePrompt = "Please share any links, portfolio items, or describe any relevant experience you have.";
      
      const aspLower = learnerAspiration.toLowerCase();
      if (aspLower.includes("football") || aspLower.includes("athlete") || aspLower.includes("sport")) {
        evidencePrompt = "For a physical/performance goal like this, I need evidence of performance. Please share a link to your match statistics, a highlight video, or competition record.";
      } else if (aspLower.includes("law") || aspLower.includes("lawyer")) {
        evidencePrompt = "Please share any academic background in law, research papers, relevant competitions, or internships.";
      } else if (aspLower.includes("software") || aspLower.includes("engineer") || aspLower.includes("developer") || aspLower.includes("ai")) {
        evidencePrompt = "Please share your GitHub profile, links to live projects, or technical portfolio.";
      }

      addAgentMessage(evidencePrompt, "evidence_upload");
    }
    else if (step === "EVIDENCE") {
      setEvidenceProvided(text);
      setStep("ASSESSMENT");
      addAgentMessage(
        "Thank you. Based on your aspiration and evidence, I've selected a specific assessment to determine your baseline capability and readiness before synthesizing a path.",
        "assessment_bridge"
      );
      
      // Simulate assessment completion and moving to synthesis
      setTimeout(() => {
        setStep("SYNTHESIS");
        addAgentMessage(
          "I've synthesized the evidence and your assessment results. Here are the pathways I recommend for you.",
          "pathways",
          [],
          [
            {
              id: "path_1",
              title: `${learnerAspiration} Professional Pathway`,
              target: learnerAspiration,
              confidence: "HIGH",
              why: "Directly aligns with your stated goal and matches your current learner stage.",
              locked_phases: 5
            },
            {
              id: "path_2",
              title: "Foundational Bridge Pathway",
              target: `Foundations for ${learnerAspiration}`,
              confidence: "MEDIUM",
              why: "Recommended if you want to fortify core prerequisites before advancing.",
              locked_phases: 3
            }
          ]
        );
      }, 3500);
    }
  };

  const handlePathwaySelect = (path: Pathway) => {
    setSelectedPath(path.id);
    addAgentMessage(`Excellent choice. Let's begin the ${path.title}. I am initializing your progressive roadmap now.`);
    
    // Setup and redirect
    setTimeout(() => {
      const canonicalId = localStorage.getItem("pathmind_canonical_id") || "scholar-user";
      fetch(`${process.env.NEXT_PUBLIC_API_BASE_URL || "https://pathmind-api.onrender.com"}/api/roadmap/generate?target_outcome=${encodeURIComponent(path.target)}`, {
        method: "POST",
        headers: { "X-Person-ID": canonicalId }
      }).then(() => {
        router.push("/journey");
      }).catch((e) => {
        console.error(e);
        router.push("/journey"); // fail gracefully to local state if needed
      });
    }, 2000);
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

                    {msg.type === "pathways" && msg.pathways && (
                      <div className="flex flex-col gap-3 mt-2 w-full min-w-[280px] md:min-w-[400px]">
                        {msg.pathways.map((path) => (
                          <div key={path.id} className="p-5 rounded-2xl bg-surface border border-outline shadow-sm flex flex-col gap-3">
                            <div className="flex justify-between items-start">
                              <h3 className="font-bold text-on-surface text-base">{path.title}</h3>
                              <span className="text-[10px] px-2 py-1 bg-emerald-950 text-emerald-300 rounded-full border border-emerald-800">
                                {path.confidence} CONFIDENCE
                              </span>
                            </div>
                            <p className="text-xs text-on-surface-variant leading-relaxed">{path.why}</p>
                            <div className="text-[11px] text-on-surface-variant font-medium">
                              Phase 1 Unlocked • {path.locked_phases} Subsequent Phases Locked
                            </div>
                            <button
                              onClick={() => handlePathwaySelect(path)}
                              className="mt-2 w-full py-2.5 rounded-xl bg-primary text-on-primary text-xs font-bold hover:opacity-95 transition-all"
                            >
                              Select Pathway
                            </button>
                          </div>
                        ))}
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
          <div ref={messagesEndRef} />
        </div>
      </main>

      {/* Input Area */}
      <div className="fixed bottom-0 left-0 w-full bg-gradient-to-t from-surface via-surface to-transparent pt-10 pb-6 px-4 md:px-0 pointer-events-none">
        <div className="max-w-2xl mx-auto w-full pointer-events-auto">
          {step === "ASSESSMENT" ? (
            <div className="p-4 rounded-2xl bg-surface-container border border-outline shadow-lg flex items-center justify-center gap-3">
              <Loader2 className="w-5 h-5 text-primary animate-spin" />
              <span className="text-sm font-medium text-on-surface">Agent is running selected diagnostic assessments...</span>
            </div>
          ) : step === "SYNTHESIS" ? (
             <></>
          ) : (
            <form 
              onSubmit={(e) => { e.preventDefault(); handleSend(); }}
              className="relative flex items-center bg-surface-container-low border border-outline rounded-2xl shadow-xl overflow-hidden focus-within:ring-2 focus-within:ring-primary/50 transition-all"
            >
              <input
                type="text"
                value={inputText}
                onChange={(e) => setInputText(e.target.value)}
                placeholder={step === "EVIDENCE" ? "Paste GitHub URL, portfolio link, or describe experience..." : "Type your response..."}
                className="flex-1 bg-transparent px-6 py-4 text-sm text-on-surface placeholder:text-on-surface-variant focus:outline-none"
                disabled={isTyping}
              />
              <button
                type="submit"
                disabled={!inputText.trim() || isTyping}
                className="p-3 mr-2 rounded-xl bg-primary text-on-primary disabled:opacity-50 hover:opacity-95 transition-opacity"
              >
                <Send className="w-4 h-4" />
              </button>
            </form>
          )}
        </div>
      </div>
    </div>
  );
}
