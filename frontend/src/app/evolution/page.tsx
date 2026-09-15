import type { Metadata } from "next";

import { PersonalEvolutionView } from "@/components/pathmind/evolution/PersonalEvolutionView";

export const metadata: Metadata = {
  title: "Personal Evolution & Longitudinal State — PATHMIND",
  description: "Longitudinal cognitive model, mastery evolution milestones, and developmental progression analytics.",
};

export default function EvolutionPage() {
  return (
    <div className="flex min-h-screen bg-surface">
      
      <div className="flex-1 flex flex-col min-w-0 max-w-7xl mx-auto">
        <main className="flex-1 flex flex-col justify-start items-center px-6 md:px-12 pt-16 md:pt-8 pb-24 relative z-10">
          <PersonalEvolutionView />
        </main>
      </div>
    </div>
  );
}
