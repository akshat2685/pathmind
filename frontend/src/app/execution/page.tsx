import type { Metadata } from "next";

import { ExecutionMissionView } from "@/components/pathmind/execution/ExecutionMissionView";

export const metadata: Metadata = {
  title: "Today's Plan & Progress — PATHMIND",
  description: "Daily execution missions, focused action tracking, and adaptive streak protection.",
};

export default function ExecutionPage() {
  return (
    <div className="flex min-h-screen bg-surface">
      
      <div className="flex-1 flex flex-col min-w-0 max-w-7xl mx-auto">
        <main className="flex-1 flex flex-col justify-start items-center px-6 md:px-12 pt-16 md:pt-8 pb-24 relative z-10">
          <div className="w-full max-w-6xl">
            <ExecutionMissionView />
          </div>
        </main>
      </div>
    </div>
  );
}
