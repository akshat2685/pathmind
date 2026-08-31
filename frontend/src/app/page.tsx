"use client";

import { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { Sidebar } from "@/components/layout/Sidebar";
import { TopBar } from "@/components/layout/TopBar";

export default function Home() {
  const router = useRouter();
  const [curiosity, setCuriosity] = useState("");

  const suggestions = [
    "Machine Learning & Generative AI",
    "Distributed Cloud Architectures",
    "Human-Computer Interaction",
    "Data Systems & Analytics",
  ];

  const handleEmbark = (e: React.FormEvent) => {
    e.preventDefault();
    if (curiosity.trim()) {
      router.push(`/onboarding?goal=${encodeURIComponent(curiosity)}`);
    } else {
      router.push("/onboarding");
    }
  };

  return (
    <div className="flex min-h-screen bg-surface">
      <Sidebar />
      <div className="flex-1 flex flex-col min-w-0 md:ml-72">
        <TopBar />
        <main className="flex-1 flex flex-col justify-center items-center px-6 md:px-12 pt-24 md:pt-16 pb-24 relative z-10">
          <div className="w-full max-w-3xl mx-auto flex flex-col items-center">
            
            {/* Hero Prompt */}
            <div className="text-center mb-10 transform md:-translate-y-4">
              <div className="inline-flex items-center gap-2 px-4 py-1.5 sketchy-chip text-tertiary mb-6">
                <span className="material-symbols-outlined text-lg" style={{ fontVariationSettings: "'FILL' 1" }}>
                  eco
                </span>
                <span className="font-note-handwritten text-xl font-medium">Chapter I: The Initiation</span>
              </div>
              <h2 className="font-headline-lg text-4xl sm:text-5xl text-on-surface mb-4">
                Where does your journey begin?
              </h2>
              <p className="font-note-handwritten text-2xl sm:text-3xl text-on-surface-variant max-w-xl mx-auto opacity-90 leading-relaxed">
                Scribe your current curiosity. The path forms as you walk it.
              </p>
            </div>

            {/* Input Area Card */}
            <div className="w-full max-w-2xl p-8 sm:p-10 relative sketch-border bg-surface-container-low/90">
              <div className="absolute -top-4 -left-4 text-tertiary opacity-70 transform -rotate-12">
                <span className="material-symbols-outlined text-4xl" style={{ fontVariationSettings: "'FILL' 1" }}>
                  eco
                </span>
              </div>

              <form onSubmit={handleEmbark} className="flex flex-col gap-8 w-full mt-2">
                <div className="relative">
                  <input
                    type="text"
                    value={curiosity}
                    onChange={(e) => setCuriosity(e.target.value)}
                    placeholder="e.g., The origins of machine intelligence..."
                    className="w-full hand-drawn-input text-center placeholder:text-outline/60 px-4 py-2"
                  />
                </div>

                <div className="flex justify-center mt-2">
                  <button
                    type="submit"
                    className="ink-wash-btn-primary px-10 py-3 text-2xl flex items-center gap-3 cursor-pointer"
                  >
                    <span>Embark</span>
                    <span className="material-symbols-outlined text-lg">east</span>
                  </button>
                </div>
              </form>
            </div>

            {/* Suggestion Washi Tape Chips */}
            <div className="mt-8 flex flex-wrap justify-center gap-3 opacity-90">
              {suggestions.map((s, idx) => (
                <button
                  key={s}
                  type="button"
                  onClick={() => setCuriosity(s)}
                  className={`font-note-handwritten text-xl text-on-surface-variant sketchy-chip px-4 py-1.5 cursor-pointer hover:bg-surface-container-highest transition-all transform ${
                    idx % 2 === 0 ? "rotate-1 hover:rotate-0" : "-rotate-2 hover:rotate-0"
                  }`}
                >
                  {s}
                </button>
              ))}
            </div>

            {/* Quick Pathways Grid */}
            <div className="mt-16 w-full grid md:grid-cols-2 gap-6">
              <Link
                href="/onboarding"
                className="sketch-border p-6 hover:translate-y-[-2px] transition-transform bg-surface-container-low/70 block group"
              >
                <div className="flex items-start gap-4">
                  <div className="w-12 h-12 rounded-full border border-secondary flex items-center justify-center text-secondary bg-secondary/10 group-hover:scale-105 transition-transform">
                    <span className="material-symbols-outlined text-2xl">ink_pen</span>
                  </div>
                  <div>
                    <h3 className="font-headline-sm text-xl text-secondary mb-1">
                      The First Step
                    </h3>
                    <p className="font-body-md text-sm text-on-surface-variant">
                      Build your longitudinal scholar profile with aspirations and behavioral signals.
                    </p>
                  </div>
                </div>
              </Link>

              <Link
                href="/assessment"
                className="sketch-border p-6 hover:translate-y-[-2px] transition-transform bg-surface-container-low/70 block group"
              >
                <div className="flex items-start gap-4">
                  <div className="w-12 h-12 rounded-full border border-tertiary flex items-center justify-center text-tertiary bg-tertiary/10 group-hover:scale-105 transition-transform">
                    <span className="material-symbols-outlined text-2xl">psychology_alt</span>
                  </div>
                  <div>
                    <h3 className="font-headline-sm text-xl text-tertiary mb-1">
                      Counseling Engine
                    </h3>
                    <p className="font-body-md text-sm text-on-surface-variant">
                      Complete structured RIASEC/SCCT assessments synthesized by Gemini ADK reasoning.
                    </p>
                  </div>
                </div>
              </Link>
            </div>

          </div>
        </main>
      </div>
    </div>
  );
}
