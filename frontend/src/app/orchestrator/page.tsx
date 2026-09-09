import type { Metadata } from "next";
import { Sidebar } from "@/components/layout/Sidebar";
import { TopBar } from "@/components/layout/TopBar";
import { OrchestrationHubView } from "@/components/pathmind/orchestration/OrchestrationHubView";

export const metadata: Metadata = {
  title: "Control Tower & Agent Orchestration — PATHMIND",
  description: "Deterministic workflow router, agent capability contracts, and state change approval gates.",
};

export default function OrchestratorPage() {
  return (
    <div className="flex min-h-screen bg-surface">
      <Sidebar />
      <div className="flex-1 flex flex-col min-w-0 md:ml-64 lg:ml-72">
        <TopBar />
        <main className="flex-1 flex flex-col justify-start items-center px-6 md:px-12 pt-16 md:pt-8 pb-24 relative z-10">
          <div className="w-full max-w-6xl">
            <OrchestrationHubView />
          </div>
        </main>
      </div>
    </div>
  );
}
