import { AuthGate } from "@/components/auth/AuthGate";
import { OnboardingFlow } from "@/components/pathmind/OnboardingFlow";

export const metadata = {
  title: "Academic Initiation — PATHMIND College",
  description: "Configure your university engineering curriculum and study horizon.",
};

export default function OnboardingPage() {
  return (
    <AuthGate>
      <OnboardingPageInner />
    </AuthGate>
  );
}

function OnboardingPageInner() {
  return <OnboardingFlow />;
}

