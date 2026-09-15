import { MasteryDashboard } from "@/components/pathmind/evidence/MasteryDashboard";


export const metadata = {
  title: "Evidence & Mastery — PATHMIND",
  description: "Evidence-based skill verification, mastery state audits, prerequisite gating, and evaluation disputes.",
};

export default function EvidencePage() {
  return (
    <div className="flex min-h-screen bg-surface">
      
      <div className="flex-1 flex flex-col min-w-0 max-w-7xl mx-auto">
        <main className="flex-1 flex items-start justify-center p-4 sm:p-6 md:p-10 lg:p-12 pt-16 md:pt-8 relative z-10">
          <MasteryDashboard />
        </main>
      </div>
    </div>
  );
}
