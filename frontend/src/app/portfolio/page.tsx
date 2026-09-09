import type { Metadata } from "next";
import { Sidebar } from "@/components/layout/Sidebar";
import { TopBar } from "@/components/layout/TopBar";
import { ArtifactPortfolioView } from "@/components/pathmind/portfolio/ArtifactPortfolioView";

export const metadata: Metadata = {
  title: "Artifacts & Evidence Portfolio — PATHMIND",
  description: "Verified code, writing, design, and analysis artifacts with provenance and tamper-evident integrity.",
};

export default function PortfolioPage() {
  return (
    <div className="flex min-h-screen bg-surface">
      <Sidebar />
      <div className="flex-1 flex flex-col min-w-0 md:ml-64 lg:ml-72">
        <TopBar />
        <main className="flex-1 flex flex-col justify-start items-center px-6 md:px-12 pt-16 md:pt-8 pb-24 relative z-10">
          <div className="w-full max-w-6xl">
            <ArtifactPortfolioView />
          </div>
        </main>
      </div>
    </div>
  );
}
