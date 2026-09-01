import { ProgressiveJourney } from "@/components/pathmind/journey/ProgressiveJourney";
import { Sidebar } from "@/components/layout/Sidebar";
import { TopBar } from "@/components/layout/TopBar";

export const metadata = {
  title: "Learning Journey — PATHMIND",
  description: "Progressive milestone roadmap, evidence-gated stage unlock, and adaptive learning engine.",
};

export default function JourneyPage() {
  return (
    <div className="flex min-h-screen bg-surface">
      <Sidebar />
      <div className="flex-1 flex flex-col min-w-0 md:ml-72">
        <TopBar />
        <main className="flex-1 flex items-start justify-center p-6 md:p-12 relative z-10">
          <ProgressiveJourney />
        </main>
      </div>
    </div>
  );
}
