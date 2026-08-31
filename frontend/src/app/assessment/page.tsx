import { AssessmentFlow } from "@/components/pathmind/assessment/AssessmentFlow";
import { Sidebar } from "@/components/layout/Sidebar";
import { TopBar } from "@/components/layout/TopBar";

export const metadata = {
  title: "Counseling Engine — PATHMIND",
  description: "Evidence-informed counseling and trajectory synthesis.",
};

export default function AssessmentPage() {
  return (
    <div className="flex min-h-screen bg-surface">
      <Sidebar />
      <div className="flex-1 flex flex-col min-w-0 md:ml-72">
        <TopBar />
        <main className="flex-1 flex items-center justify-center p-6 md:p-12 relative z-10">
          <div className="w-full max-w-4xl mx-auto">
            <AssessmentFlow />
          </div>
        </main>
      </div>
    </div>
  );
}
