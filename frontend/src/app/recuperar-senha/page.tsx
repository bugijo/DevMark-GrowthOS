import type { Metadata } from "next";

import { PasswordRecoveryForm } from "@/components/auth/password-recovery-form";

export const metadata: Metadata = {
  title: "Recuperar senha",
};

export default function PasswordRecoveryPage() {
  return <PasswordRecoveryForm />;
}
