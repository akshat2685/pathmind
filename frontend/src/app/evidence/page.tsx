import { MasteryDashboard } from "@/components/pathmind/evidence/MasteryDashboard";
import { Sidebar } from "@/components/layout/Sidebar";
import { TopBar } from "@/components/layout/TopBar";

export const metadata = {
  title: "Evidence & Mastery — PATHMIND",
  description: "Evidence-based skill verification, mastery state audits, prerequisite gating, and evaluation disputes.",
};

export default function EvidencePage() {
  return (
    <div className="flex min-h-screen bg-surface">
      <Sidebar />
      <div className="flex-1 flex flex-col min-w-0 md:ml-72">
        <TopBar />
        <main className="flex-1 flex items-start justify-center p-6 md:p-12 relative z-10">
          <MasteryDashboard />
        </main>
      </div>
    </div>
  );
}
