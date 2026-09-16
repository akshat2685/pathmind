import { MemoryVault } from "@/components/pathmind/memory/MemoryVault";

import { TopBar } from "@/components/layout/TopBar";

export const metadata = {
  title: "Memory Subsystem Diagnostics — PATHMIND",
  description: "Internal developer/diagnostic surface to inspect proactive memory recall, provenance chains, and conflict detection.",
};

export default function MemoryPage() {
  return (
    <div className="flex min-h-screen bg-surface w-full max-w-full overflow-x-hidden">
      
      <div className="flex-1 flex flex-col min-w-0 max-w-7xl mx-auto w-full max-w-full overflow-x-hidden">
        <TopBar />
        <main className="flex-1 flex items-start justify-center p-3 sm:p-6 md:p-10 lg:p-12 pt-16 md:pt-8 relative z-10 w-full max-w-full overflow-x-hidden">
          <MemoryVault />
        </main>
      </div>
    </div>
  );
}
