"use client";

import { useParams } from "next/navigation";

import { OnboardingWizard } from "@/components/onboarding/onboarding-wizard";

export default function BusinessOnboardingPage() {
  const { id } = useParams<{ id: string }>();

  return <OnboardingWizard businessId={id} />;
}
