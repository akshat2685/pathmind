import { AssessmentFlow } from "@/components/pathmind/assessment/AssessmentFlow";

export const metadata = {
  title: "PATHMIND - Assessment Engine",
  description: "Evidence-informed counseling assessment.",
};

export default function AssessmentPage() {
  return (
    <div className="pt-24 px-4 pb-12 w-full max-w-7xl mx-auto">
      <AssessmentFlow />
    </div>
  );
}
