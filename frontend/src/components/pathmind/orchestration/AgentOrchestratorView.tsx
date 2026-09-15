"use client";

import { useState, useEffect, useRef } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Send, User, Bot, Loader2, AlertTriangle } from "lucide-react";
import { ProgressiveJourney } from "@/components/pathmind/journey/ProgressiveJourney";
import { MasteryDashboard } from "@/components/pathmind/evidence/MasteryDashboard";

// Define the interface for the backend response
interface UIBlock {
  type: string;
  data: Record<string, unknown>;
}

interface AgentResponse {
  message: string;
  state: Record<string, unknown>;
  ui_blocks: UIBlock[];
}

interface Message {
  id: string;
  role: "agent" | "learner";
  text: string;
  ui_blocks?: UIBlock[];
  isError?: boolean;
}

export function AgentOrchestratorView() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [inputText, setInputText] = useState("");
  const [isTyping, setIsTyping] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, isTyping]);

  useEffect(() => {
    // Initialization: Check if we have a session. If not, create one.
    let canonicalId = localStorage.getItem("pathmind_canonical_id");
    if (!canonicalId) {
      // Generate a temporary anonymous ID to allow the agent to ask for their name
      canonicalId = "anon-" + Math.random().toString(36).substring(2, 10);
      localStorage.setItem("pathmind_canonical_id", canonicalId);
      
      // Kick off the conversation
      handleSend("INIT_NEW_SESSION", true);
    } else {
      // If we have an ID, we just ping the agent to resume
      handleSend("RESUME_SESSION", true);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const handleSend = async (text: string = inputText, isSystemPing: boolean = false) => {
    if ((!text.trim() && !isSystemPing) || isTyping) return;
    
    if (!isSystemPing) {
      const userMsg: Message = { id: `msg_${Date.now()}`, role: "learner", text };
      setMessages((prev) => [...prev, userMsg]);
      setInputText("");
    }
    
    setIsTyping(true);

    try {
      const canonicalId = localStorage.getItem("pathmind_canonical_id") || "scholar-user";
      const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL || "https://pathmind-api.onrender.com";
      
      const payload = isSystemPing && text === "INIT_NEW_SESSION" 
        ? "Hello, I am a new user. What is my first step?" 
        : (isSystemPing && text === "RESUME_SESSION" ? "Hello, I am returning. What is my current state?" : text);

      const res = await fetch(`${API_BASE}/api/agent/interact`, {
        method: "POST",
        headers: { 
          "Content-Type": "application/json", 
          "X-Person-ID": canonicalId 
        },
        body: JSON.stringify({
          message: payload,
          state: {}
        })
      });

      if (!res.ok) {
        throw new Error(`API Error: ${res.status}`);
      }

      const data: AgentResponse = await res.json();
      
      setMessages((prev) => [
        ...prev,
        {
          id: `msg_${Date.now()}`,
          role: "agent",
          text: data.message,
          ui_blocks: data.ui_blocks,
          isError: data.ui_blocks?.some(b => b.type === "ERROR")
        }
      ]);

    } catch (e: unknown) {
      console.error(e);
      const error = e as Error;
      setMessages((prev) => [
        ...prev,
        {
          id: `msg_${Date.now()}`,
          role: "agent",
          text: "I am having trouble connecting to my backend reasoning engine right now. Please try again in a moment.",
          isError: true,
          ui_blocks: [{ type: "ERROR", data: { error_code: "NETWORK_ERROR", message: error.message } }]
        }
      ]);
    } finally {
      setIsTyping(false);
    }
  };

  const renderUIBlock = (block: UIBlock) => {
    switch (block.type) {
      case "ERROR":
        return (
          <div className="mt-4 p-4 rounded-xl bg-error/10 border border-error/20 flex items-start gap-3">
            <AlertTriangle className="w-5 h-5 text-error mt-0.5 shrink-0" />
            <div className="text-sm text-error">
              {block.data?.error_code === "429_QUOTA_EXCEEDED" 
                ? "The Gemini Free Tier daily quota has been exceeded (20 requests/day). You must wait 24 hours or upgrade the API key."
                : "An unexpected error occurred."}
            </div>
          </div>
        );
      case "ROADMAP":
        return (
          <div className="mt-6 w-full max-w-4xl bg-surface-container rounded-2xl p-4 shadow-sm border border-outline/30">
             <div className="font-bold text-secondary mb-4 flex items-center gap-2"><span className="material-symbols-outlined">map</span> Your Roadmap</div>
            <ProgressiveJourney />
          </div>
        );
      case "EVIDENCE_STATUS":
      case "MASTERY":
        return (
          <div className="mt-6 w-full max-w-4xl bg-surface-container rounded-2xl p-4 shadow-sm border border-outline/30">
            <div className="font-bold text-secondary mb-4 flex items-center gap-2"><span className="material-symbols-outlined">verified</span> Mastery Dashboard</div>
            <MasteryDashboard />
          </div>
        );
      case "PATHWAYS":
      case "LEARNING_PLAN":
      case "STAGE_SELECTION":
      case "EVIDENCE_REQUEST":
      case "ASSESSMENT":
      default:
        // We will render raw data for blocks we haven't wired up components to yet
        return (
          <div className="mt-4 p-4 rounded-xl bg-surface-container border border-outline text-xs font-mono text-on-surface-variant overflow-x-auto">
            <div className="font-bold text-secondary mb-2">{block.type} BLOCK INJECTED</div>
            <pre>{JSON.stringify(block.data, null, 2)}</pre>
          </div>
        );
    }
  };

  return (
    <div className="flex flex-col h-screen bg-surface overflow-hidden relative">
      <div className="watercolor-overlay pointer-events-none z-0"></div>
      <div className="paper-texture pointer-events-none z-0"></div>

      <header className="flex justify-center items-center px-4 py-3 z-10 bg-surface/50 backdrop-blur-md border-b border-outline-variant/30">
        <div className="flex items-center gap-2">
          <span className="material-symbols-outlined text-secondary text-2xl" style={{ fontVariationSettings: "'FILL' 1" }}>
            auto_stories
          </span>
          <span className="font-headline-lg text-xl italic text-secondary tracking-tight">
            Pathmind
          </span>
        </div>
      </header>

      <main className="flex-1 w-full mx-auto flex flex-col z-10 overflow-hidden relative">
        <div className="flex-1 overflow-y-auto p-4 md:p-8 pt-6 pb-32">
          <div className="max-w-4xl mx-auto space-y-8">
            <AnimatePresence>
              {messages.map((msg) => (
                <motion.div
                  key={msg.id}
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  className={`flex ${msg.role === "agent" ? "justify-start" : "justify-end"}`}
                >
                  <div className={`flex gap-3 max-w-[95%] md:max-w-[85%] flex-col md:flex-row ${msg.role === "agent" ? "md:flex-row" : "md:flex-row-reverse"}`}>
                    <div className={`w-10 h-10 rounded-full flex items-center justify-center shrink-0 ${
                      msg.role === "agent" 
                        ? (msg.isError ? "bg-error/10 text-error border border-error/20" : "bg-primary/10 text-primary border border-primary/20")
                        : "bg-surface-container-highest text-on-surface border border-outline self-end md:self-start"
                    }`}>
                      {msg.role === "agent" ? <Bot className="w-5 h-5" /> : <User className="w-5 h-5" />}
                    </div>
                    
                    <div className={`space-y-4 ${msg.role === "agent" ? "items-start" : "items-end"} w-full`}>
                      {msg.text && (
                        <div className={`p-4 rounded-2xl text-base md:text-lg leading-relaxed ${
                          msg.role === "agent" 
                            ? (msg.isError ? "bg-error/10 border border-error/20 text-error md:rounded-tl-none" : "bg-surface-container-low border border-outline/50 text-on-surface md:rounded-tl-none")
                            : "bg-primary text-on-primary md:rounded-tr-none shadow-md"
                        }`}>
                          {msg.text}
                        </div>
                      )}

                      {msg.ui_blocks?.map((block, idx) => (
                        <div key={idx} className="w-full">
                          {renderUIBlock(block)}
                        </div>
                      ))}
                    </div>
                  </div>
                </motion.div>
              ))}
            </AnimatePresence>

            {isTyping && (
              <motion.div
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                className="flex justify-start"
              >
                <div className="flex gap-3">
                  <div className="w-10 h-10 rounded-full bg-primary/10 text-primary border border-primary/20 flex items-center justify-center">
                    <Loader2 className="w-5 h-5 animate-spin" />
                  </div>
                  <div className="bg-surface-container-low border border-outline/50 p-4 rounded-2xl rounded-tl-none flex items-center gap-2 text-sm text-on-surface-variant">
                    <span className="w-2 h-2 rounded-full bg-primary/40 animate-pulse"></span>
                    <span className="w-2 h-2 rounded-full bg-primary/40 animate-pulse delay-75"></span>
                    <span className="w-2 h-2 rounded-full bg-primary/40 animate-pulse delay-150"></span>
                  </div>
                </div>
              </motion.div>
            )}
            <div ref={messagesEndRef} className="h-4" />
          </div>
        </div>

        <div className="absolute bottom-0 left-0 right-0 bg-gradient-to-t from-surface via-surface to-transparent pt-10 pb-6 px-4 md:px-8 z-20">
          <div className="max-w-3xl mx-auto relative group">
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
              placeholder="Talk to PATHMIND..."
              disabled={isTyping}
              className="w-full bg-surface-container/80 backdrop-blur-md border-2 border-outline-variant hover:border-outline focus:border-primary rounded-3xl py-4 pl-6 pr-14 outline-none transition-all text-on-surface shadow-sm focus:shadow-md disabled:opacity-50 text-base"
            />
            <button
              onClick={() => handleSend()}
              disabled={!inputText.trim() || isTyping}
              className="absolute right-3 top-1/2 -translate-y-1/2 p-2.5 bg-primary text-on-primary rounded-full hover:bg-primary/90 hover:scale-105 active:scale-95 transition-all disabled:opacity-50 disabled:hover:scale-100 disabled:pointer-events-none shadow-sm"
            >
              <Send className="w-4 h-4 ml-0.5" />
            </button>
          </div>
          <div className="text-center mt-3 flex items-center justify-center gap-1.5 text-xs text-on-surface-variant font-label-md">
            <span className="material-symbols-outlined text-[14px]">psychology</span>
            <span>PATHMIND ADK Engine</span>
          </div>
        </div>
      </main>
    </div>
  );
}
