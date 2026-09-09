"use client";

import { Sidebar } from "@/components/layout/Sidebar";
import { TopBar } from "@/components/layout/TopBar";
import { OpportunityNavigatorView } from "@/components/pathmind/career/OpportunityNavigatorView";

export default function OpportunitiesPage() {
  return (
    <div className="flex min-h-screen bg-surface">
      <Sidebar />
      <div className="flex-1 flex flex-col min-w-0 md:ml-72">
        <TopBar />
        <main className="flex-1 flex flex-col justify-start items-center px-6 md:px-12 pt-8 pb-24 relative z-10">
          <div className="w-full max-w-6xl">
            <OpportunityNavigatorView />
          </div>
        </main>
      </div>
    </div>
  );
}
