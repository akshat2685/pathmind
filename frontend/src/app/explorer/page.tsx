import { CareerExplorer } from "@/components/pathmind/explorer/CareerExplorer";
import { Sidebar } from "@/components/layout/Sidebar";
import { TopBar } from "@/components/layout/TopBar";

export const metadata = {
  title: "Career Explorer — PATHMIND",
  description: "Candidate career pathway discovery, skill gap analysis, and trajectory comparison.",
};

export default function ExplorerPage() {
  return (
    <div className="flex min-h-screen bg-surface">
      <Sidebar />
      <div className="flex-1 flex flex-col min-w-0 md:ml-64 lg:ml-72">
        <TopBar />
        <main className="flex-1 flex items-start justify-center p-4 sm:p-6 md:p-10 lg:p-12 pt-16 md:pt-8 relative z-10">
          <CareerExplorer />
        </main>
      </div>
    </div>
  );
}
