import { CareerLaunchpad } from "@/components/pathmind/career/CareerLaunchpad";
import { Sidebar } from "@/components/layout/Sidebar";
import { TopBar } from "@/components/layout/TopBar";

export const metadata = {
  title: "Career Readiness & Launchpad — PATHMIND",
  description: "Accountability partner, career readiness gap analysis, credential strategy, verified opportunities, and evidence-grounded tailored resume.",
};

export default function ReadinessPage() {
  return (
    <div className="flex min-h-screen bg-surface">
      <Sidebar />
      <div className="flex-1 flex flex-col min-w-0 md:ml-72">
        <TopBar />
        <main className="flex-1 flex items-start justify-center p-6 md:p-12 relative z-10">
          <CareerLaunchpad />
        </main>
      </div>
    </div>
  );
}
