import type { Metadata } from "next";

import { InvitationAcceptance } from "@/components/auth/invitation-acceptance";

export const metadata: Metadata = {
  title: "Aceitar convite",
};

export default function InvitationAcceptancePage() {
  return <InvitationAcceptance />;
}
